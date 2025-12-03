import asyncio
from datetime import datetime, timezone

from openai import APIError, AsyncOpenAI, RateLimitError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models import Transcription, TranscriptionStatus
from app.services.audio import chunk_audio_file, cleanup_chunks, get_audio_duration


class TranscriptionService:
    """Handles all the Whisper API interactions."""

    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)

    async def transcribe_chunk(self, chunk_path: str) -> str:
        """
        Send a single audio chunk to Whisper and get the text back.
        Includes retry logic for rate limits.
        """
        max_retries = 3
        retry_delay = 5  # seconds

        for attempt in range(max_retries):
            try:
                with open(chunk_path, "rb") as audio_file:
                    response = await self.client.audio.transcriptions.create(
                        model="whisper-1",
                        file=audio_file,
                        response_format="text"
                    )
                return response

            except RateLimitError:
                # back off and retry
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay * (attempt + 1))
                else:
                    raise

            except APIError as e:
                # log it and re-raise for the caller to handle
                raise Exception(f"Whisper API error: {str(e)}")

    async def transcribe_file(
        self,
        file_path: str,
        db: AsyncSession,
        file_id: str
    ) -> str:
        """
        Transcribe an audio file, handling chunking for long files.
        Updates progress in the database as we go.
        """
        # get the transcription record
        result = await db.execute(
            select(Transcription).where(Transcription.file_id == file_id)
        )
        transcription = result.scalar_one()

        try:
            # mark as processing
            transcription.status = TranscriptionStatus.processing
            transcription.progress = 0
            await db.commit()

            # figure out how long the audio is
            duration = get_audio_duration(file_path)
            transcription.duration_seconds = duration
            await db.commit()

            # split into chunks if needed
            chunks = chunk_audio_file(file_path)
            total_chunks = len(chunks)
            transcripts = []

            for i, chunk_path in enumerate(chunks):
                # transcribe this chunk
                text = await self.transcribe_chunk(chunk_path)
                transcripts.append(text)

                # update progress
                progress = int(((i + 1) / total_chunks) * 100)
                transcription.progress = progress
                await db.commit()

            # clean up temp files
            if len(chunks) > 1:
                cleanup_chunks(chunks)

            # combine all the chunks into one transcript
            full_transcript = " ".join(transcripts)

            # save the result
            transcription.transcript_text = full_transcript
            transcription.status = TranscriptionStatus.completed
            transcription.progress = 100
            transcription.completed_at = datetime.now(timezone.utc)
            await db.commit()

            return full_transcript

        except Exception as e:
            # something went wrong - save the error
            transcription.status = TranscriptionStatus.failed
            transcription.error_message = str(e)
            await db.commit()
            raise


# singleton instance
transcription_service = TranscriptionService()
