import json
from datetime import datetime, timezone

from openai import APIError, AsyncOpenAI, RateLimitError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models import MeetingSummary, SummaryStatus, Transcription, TranscriptionStatus

# GPT-4 has different context windows, we'll use a safe limit
# gpt-4-turbo can handle 128k tokens, but we'll be conservative
MAX_TRANSCRIPT_CHARS = 100000  # roughly 25k tokens


SUMMARY_SYSTEM_PROMPT = """You are an expert meeting notes assistant. Your job is to analyze meeting transcripts and extract key information in a structured format.

Be concise but comprehensive. Focus on actionable information."""


SUMMARY_USER_PROMPT = """Please analyze this meeting transcript and provide:

1. **Summary** (3-5 bullet points capturing the main topics discussed)
2. **Action Items** (tasks that need to be done, with owners if mentioned)
3. **Key Decisions** (any decisions that were made during the meeting)
4. **Follow-up Questions** (unresolved questions or topics that need further discussion)

Respond in JSON format exactly like this:
{{
    "summary": ["bullet point 1", "bullet point 2", ...],
    "action_items": [
        {{"task": "description", "owner": "person name or null if not specified"}},
        ...
    ],
    "key_decisions": ["decision 1", "decision 2", ...],
    "follow_up_questions": ["question 1", "question 2", ...]
}}

If any section has no items, use an empty array [].

TRANSCRIPT:
{transcript}"""


def chunk_transcript(transcript: str, max_chars: int = MAX_TRANSCRIPT_CHARS) -> list[str]:
    """
    Split a long transcript into chunks that fit within token limits.
    Tries to split on paragraph boundaries when possible.
    """
    if len(transcript) <= max_chars:
        return [transcript]

    chunks = []
    remaining = transcript

    while remaining:
        if len(remaining) <= max_chars:
            chunks.append(remaining)
            break

        # try to find a good break point (paragraph or sentence)
        chunk = remaining[:max_chars]
        break_point = chunk.rfind("\n\n")

        if break_point == -1 or break_point < max_chars // 2:
            break_point = chunk.rfind(". ")

        if break_point == -1 or break_point < max_chars // 2:
            break_point = max_chars

        chunks.append(remaining[:break_point + 1].strip())
        remaining = remaining[break_point + 1:].strip()

    return chunks


def merge_summaries(summaries: list[dict]) -> dict:
    """
    Combine multiple chunk summaries into one.
    Deduplicates similar items where possible.
    """
    merged = {
        "summary": [],
        "action_items": [],
        "key_decisions": [],
        "follow_up_questions": []
    }

    for summary in summaries:
        merged["summary"].extend(summary.get("summary", []))
        merged["action_items"].extend(summary.get("action_items", []))
        merged["key_decisions"].extend(summary.get("key_decisions", []))
        merged["follow_up_questions"].extend(summary.get("follow_up_questions", []))

    # simple deduplication for string lists
    merged["summary"] = list(dict.fromkeys(merged["summary"]))
    merged["key_decisions"] = list(dict.fromkeys(merged["key_decisions"]))
    merged["follow_up_questions"] = list(dict.fromkeys(merged["follow_up_questions"]))

    # dedupe action items by task description
    seen_tasks = set()
    unique_actions = []
    for item in merged["action_items"]:
        task = item.get("task", "")
        if task not in seen_tasks:
            seen_tasks.add(task)
            unique_actions.append(item)
    merged["action_items"] = unique_actions

    return merged


class SummarizationService:
    """Handles GPT-4 summarization of meeting transcripts."""

    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)

    async def summarize_chunk(self, transcript_chunk: str) -> dict:
        """
        Send a transcript chunk to GPT-4 and get structured summary back.
        """
        try:
            response = await self.client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[
                    {"role": "system", "content": SUMMARY_SYSTEM_PROMPT},
                    {"role": "user", "content": SUMMARY_USER_PROMPT.format(
                        transcript=transcript_chunk
                    )}
                ],
                response_format={"type": "json_object"},
                temperature=0.3,  # lower temp for more consistent output
            )

            content = response.choices[0].message.content
            return json.loads(content)

        except RateLimitError:
            raise Exception("Rate limited by OpenAI. Please try again in a moment.")
        except APIError as e:
            raise Exception(f"OpenAI API error: {str(e)}")
        except json.JSONDecodeError:
            raise Exception("Failed to parse GPT response as JSON")

    async def summarize_transcript(
        self,
        db: AsyncSession,
        file_id: str
    ) -> dict:
        """
        Generate a full summary for a transcription.
        Handles long transcripts by chunking and merging.
        """
        # get the transcription
        result = await db.execute(
            select(Transcription).where(Transcription.file_id == file_id)
        )
        transcription = result.scalar_one_or_none()

        if not transcription:
            raise Exception("Transcription not found")

        if transcription.status != TranscriptionStatus.completed:
            raise Exception("Transcription not completed yet")

        if not transcription.transcript_text:
            raise Exception("No transcript text available")

        # create or get existing summary record
        if transcription.summary:
            summary_record = transcription.summary
        else:
            summary_record = MeetingSummary(transcription_id=transcription.id)
            db.add(summary_record)

        try:
            summary_record.status = SummaryStatus.processing
            await db.commit()

            # chunk the transcript if needed
            chunks = chunk_transcript(transcription.transcript_text)
            chunk_summaries = []

            for chunk in chunks:
                chunk_summary = await self.summarize_chunk(chunk)
                chunk_summaries.append(chunk_summary)

            # merge if we had multiple chunks
            if len(chunk_summaries) == 1:
                final_summary = chunk_summaries[0]
            else:
                final_summary = merge_summaries(chunk_summaries)

            # save the results
            summary_record.summary_text = json.dumps(final_summary.get("summary", []))
            summary_record.action_items = json.dumps(final_summary.get("action_items", []))
            summary_record.key_decisions = json.dumps(final_summary.get("key_decisions", []))
            summary_record.follow_up_questions = json.dumps(
                final_summary.get("follow_up_questions", [])
            )
            summary_record.status = SummaryStatus.completed
            summary_record.completed_at = datetime.now(timezone.utc)
            await db.commit()

            return final_summary

        except Exception as e:
            summary_record.status = SummaryStatus.failed
            summary_record.error_message = str(e)
            await db.commit()
            raise


# singleton instance
summarization_service = SummarizationService()
