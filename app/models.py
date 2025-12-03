import enum
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def utcnow():
    """Get current UTC time. Using this instead of deprecated datetime.utcnow()."""
    return datetime.now(timezone.utc)


class TranscriptionStatus(enum.Enum):
    """Tracks where a transcription is in the pipeline."""
    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class SummaryStatus(enum.Enum):
    """Tracks where a summary is in the pipeline."""
    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class Transcription(Base):
    """
    Stores info about uploaded files and their transcriptions.
    One record per uploaded file.
    """
    __tablename__ = "transcriptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    file_id: Mapped[str] = mapped_column(String(36), unique=True, index=True)
    original_filename: Mapped[str] = mapped_column(String(255))
    file_path: Mapped[str] = mapped_column(String(512))
    file_size_mb: Mapped[float] = mapped_column(Float)

    # transcription results
    status: Mapped[TranscriptionStatus] = mapped_column(
        Enum(TranscriptionStatus),
        default=TranscriptionStatus.pending
    )
    transcript_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # progress tracking - what percentage is done
    progress: Mapped[int] = mapped_column(Integer, default=0)

    # timing info
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # how long the audio file is in seconds
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)

    # relationship to summary
    summary: Mapped["MeetingSummary | None"] = relationship(
        "MeetingSummary", back_populates="transcription", uselist=False
    )


class MeetingSummary(Base):
    """
    Stores the GPT-4 generated summary for a transcription.
    Each transcription can have one summary.
    """
    __tablename__ = "meeting_summaries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    transcription_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("transcriptions.id"), unique=True
    )

    # summary status
    status: Mapped[SummaryStatus] = mapped_column(
        Enum(SummaryStatus),
        default=SummaryStatus.pending
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # the actual summary content - stored as JSON string
    summary_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    action_items: Mapped[str | None] = mapped_column(Text, nullable=True)
    key_decisions: Mapped[str | None] = mapped_column(Text, nullable=True)
    follow_up_questions: Mapped[str | None] = mapped_column(Text, nullable=True)

    # timing
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # relationship back to transcription
    transcription: Mapped["Transcription"] = relationship(
        "Transcription", back_populates="summary"
    )
