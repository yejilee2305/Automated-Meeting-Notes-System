from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Transcription, TranscriptionStatus
from app.services.transcription import transcription_service

router = APIRouter(tags=["transcription"])


# keep track of running jobs so we don't start duplicates
running_jobs: set[str] = set()


async def process_transcription(file_id: str):
    """
    Background task that runs the actual transcription.
    Uses its own db session since background tasks outlive the request.
    """
    from app.database import async_session

    async with async_session() as db:
        try:
            result = await db.execute(
                select(Transcription).where(Transcription.file_id == file_id)
            )
            transcription = result.scalar_one_or_none()

            if not transcription:
                return

            await transcription_service.transcribe_file(
                transcription.file_path,
                db,
                file_id
            )
        finally:
            # always remove from running jobs when done
            running_jobs.discard(file_id)


@router.post("/transcribe/{file_id}")
async def start_transcription(
    file_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    Start transcribing an uploaded file.

    This kicks off a background job - use the status endpoint
    to check progress. Returns immediately so you're not waiting
    around for long audio files.
    """
    # find the transcription record
    result = await db.execute(
        select(Transcription).where(Transcription.file_id == file_id)
    )
    transcription = result.scalar_one_or_none()

    if not transcription:
        raise HTTPException(status_code=404, detail="File not found")

    # don't start if already running or completed
    if file_id in running_jobs:
        raise HTTPException(status_code=400, detail="Transcription already in progress")

    if transcription.status == TranscriptionStatus.completed:
        raise HTTPException(status_code=400, detail="File already transcribed")

    # mark as running and kick off the job
    running_jobs.add(file_id)
    background_tasks.add_task(process_transcription, file_id)

    return {
        "message": "Transcription started",
        "file_id": file_id,
        "status": "processing"
    }


@router.get("/transcribe/{file_id}/status")
async def get_transcription_status(
    file_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Check the status of a transcription job.

    Poll this endpoint to track progress. Once complete,
    the transcript will be included in the response.
    """
    result = await db.execute(
        select(Transcription).where(Transcription.file_id == file_id)
    )
    transcription = result.scalar_one_or_none()

    if not transcription:
        raise HTTPException(status_code=404, detail="File not found")

    response = {
        "file_id": file_id,
        "status": transcription.status.value,
        "progress": transcription.progress,
        "original_filename": transcription.original_filename,
    }

    # add extra info based on status
    if transcription.status == TranscriptionStatus.completed:
        response["transcript"] = transcription.transcript_text
        response["duration_seconds"] = transcription.duration_seconds
        response["completed_at"] = transcription.completed_at.isoformat() if transcription.completed_at else None

    elif transcription.status == TranscriptionStatus.failed:
        response["error"] = transcription.error_message

    return response


@router.get("/transcriptions")
async def list_transcriptions(
    db: AsyncSession = Depends(get_db),
    status: str | None = None
):
    """
    List all transcription jobs.

    Optionally filter by status: pending, processing, completed, failed
    """
    query = select(Transcription).order_by(Transcription.created_at.desc())

    if status:
        try:
            status_enum = TranscriptionStatus(status)
            query = query.where(Transcription.status == status_enum)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status. Use: {[s.value for s in TranscriptionStatus]}"
            )

    result = await db.execute(query)
    transcriptions = result.scalars().all()

    return {
        "count": len(transcriptions),
        "transcriptions": [
            {
                "file_id": t.file_id,
                "original_filename": t.original_filename,
                "status": t.status.value,
                "progress": t.progress,
                "created_at": t.created_at.isoformat(),
            }
            for t in transcriptions
        ]
    }
