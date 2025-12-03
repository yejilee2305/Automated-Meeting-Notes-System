import json

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.database import get_db
from app.models import MeetingSummary, SummaryStatus, Transcription, TranscriptionStatus
from app.services.summarization import summarization_service

router = APIRouter(tags=["summary"])

# track running jobs to prevent duplicates
running_jobs: set[str] = set()


async def process_summary(file_id: str):
    """Background task that runs the summarization."""
    from app.database import async_session

    async with async_session() as db:
        try:
            await summarization_service.summarize_transcript(db, file_id)
        finally:
            running_jobs.discard(file_id)


@router.post("/summarize/{file_id}")
async def start_summarization(
    file_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    Generate a summary for a completed transcription.

    This uses GPT-4 to extract:
    - Meeting summary (3-5 bullet points)
    - Action items with owners
    - Key decisions
    - Follow-up questions

    The summary is generated in the background - poll the status endpoint.
    """
    # get the transcription with its summary if it exists
    result = await db.execute(
        select(Transcription)
        .options(joinedload(Transcription.summary))
        .where(Transcription.file_id == file_id)
    )
    transcription = result.scalar_one_or_none()

    if not transcription:
        raise HTTPException(status_code=404, detail="Transcription not found")

    if transcription.status != TranscriptionStatus.completed:
        raise HTTPException(
            status_code=400,
            detail="Transcription must be completed before summarizing"
        )

    if file_id in running_jobs:
        raise HTTPException(status_code=400, detail="Summarization already in progress")

    if transcription.summary and transcription.summary.status == SummaryStatus.completed:
        raise HTTPException(status_code=400, detail="Summary already exists")

    # kick off the background job
    running_jobs.add(file_id)
    background_tasks.add_task(process_summary, file_id)

    return {
        "message": "Summarization started",
        "file_id": file_id,
        "status": "processing"
    }


@router.get("/summarize/{file_id}/status")
async def get_summary_status(
    file_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Check the status of a summarization job.

    When complete, returns the full summary with all extracted information.
    """
    result = await db.execute(
        select(Transcription)
        .options(joinedload(Transcription.summary))
        .where(Transcription.file_id == file_id)
    )
    transcription = result.scalar_one_or_none()

    if not transcription:
        raise HTTPException(status_code=404, detail="Transcription not found")

    if not transcription.summary:
        return {
            "file_id": file_id,
            "status": "not_started",
            "message": "Summary has not been requested yet"
        }

    summary = transcription.summary
    response = {
        "file_id": file_id,
        "status": summary.status.value,
        "original_filename": transcription.original_filename,
    }

    if summary.status == SummaryStatus.completed:
        # parse the JSON strings back into objects
        response["summary"] = json.loads(summary.summary_text) if summary.summary_text else []
        response["action_items"] = json.loads(summary.action_items) if summary.action_items else []
        response["key_decisions"] = json.loads(summary.key_decisions) if summary.key_decisions else []
        response["follow_up_questions"] = json.loads(
            summary.follow_up_questions
        ) if summary.follow_up_questions else []
        response["completed_at"] = summary.completed_at.isoformat() if summary.completed_at else None

    elif summary.status == SummaryStatus.failed:
        response["error"] = summary.error_message

    return response


@router.get("/summaries")
async def list_summaries(
    db: AsyncSession = Depends(get_db),
    status: str | None = None
):
    """
    List all meeting summaries.

    Optionally filter by status: pending, processing, completed, failed
    """
    query = (
        select(MeetingSummary)
        .options(joinedload(MeetingSummary.transcription))
        .order_by(MeetingSummary.created_at.desc())
    )

    if status:
        try:
            status_enum = SummaryStatus(status)
            query = query.where(MeetingSummary.status == status_enum)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status. Use: {[s.value for s in SummaryStatus]}"
            )

    result = await db.execute(query)
    summaries = result.scalars().all()

    return {
        "count": len(summaries),
        "summaries": [
            {
                "file_id": s.transcription.file_id,
                "original_filename": s.transcription.original_filename,
                "status": s.status.value,
                "created_at": s.created_at.isoformat(),
                "completed_at": s.completed_at.isoformat() if s.completed_at else None,
            }
            for s in summaries
        ]
    }
