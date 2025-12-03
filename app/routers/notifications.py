import json

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.database import get_db
from app.models import SummaryStatus, Transcription
from app.services.notifications import (
    NotificationError,
    send_email,
    send_slack,
)

router = APIRouter(tags=["notifications"])


class EmailRequest(BaseModel):
    email: EmailStr
    subject: str | None = None


class SlackRequest(BaseModel):
    webhook_url: str | None = None  # optional, uses default if not provided


async def get_summary_data(file_id: str, db: AsyncSession) -> tuple[dict, str]:
    """
    Get the summary data for a file. Returns (summary_dict, filename).
    Raises HTTPException if not found or not ready.
    """
    result = await db.execute(
        select(Transcription)
        .options(joinedload(Transcription.summary))
        .where(Transcription.file_id == file_id)
    )
    transcription = result.scalar_one_or_none()

    if not transcription:
        raise HTTPException(status_code=404, detail="File not found")

    if not transcription.summary:
        raise HTTPException(
            status_code=400,
            detail="Summary not generated yet. Please run summarization first."
        )

    if transcription.summary.status != SummaryStatus.completed:
        raise HTTPException(
            status_code=400,
            detail=f"Summary is {transcription.summary.status.value}. Wait for completion."
        )

    # parse the JSON fields
    summary_data = {
        "summary": json.loads(transcription.summary.summary_text or "[]"),
        "action_items": json.loads(transcription.summary.action_items or "[]"),
        "key_decisions": json.loads(transcription.summary.key_decisions or "[]"),
        "follow_up_questions": json.loads(transcription.summary.follow_up_questions or "[]"),
    }

    return summary_data, transcription.original_filename


@router.post("/notify/{file_id}/email")
async def send_email_notification(
    file_id: str,
    request: EmailRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Send meeting notes to an email address.

    Requires RESEND_API_KEY to be configured in .env
    """
    summary_data, filename = await get_summary_data(file_id, db)

    try:
        result = await send_email(
            to_email=request.email,
            summary_data=summary_data,
            filename=filename,
            subject=request.subject
        )
        return {
            "message": "Email sent successfully",
            "email": request.email,
            **result
        }

    except NotificationError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/notify/{file_id}/slack")
async def send_slack_notification(
    file_id: str,
    request: SlackRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Send meeting notes to a Slack channel via webhook.

    Uses the configured SLACK_WEBHOOK_URL or a custom webhook_url in the request.
    """
    summary_data, filename = await get_summary_data(file_id, db)

    try:
        result = await send_slack(
            summary_data=summary_data,
            filename=filename,
            webhook_url=request.webhook_url
        )
        return {
            "message": "Sent to Slack successfully",
            **result
        }

    except NotificationError as e:
        raise HTTPException(status_code=400, detail=str(e))
