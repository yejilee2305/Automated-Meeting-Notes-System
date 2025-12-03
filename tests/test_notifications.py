"""Tests for notification endpoints (email and Slack)."""

import asyncio
import json
from unittest.mock import AsyncMock, patch

import pytest


@pytest.fixture
def file_with_summary(client, temp_upload_dir, sample_audio_content):
    """
    Create a file with a completed summary for notification tests.
    We need to set up the database records directly since we're not
    actually running Whisper/GPT-4.
    """
    from io import BytesIO

    # upload a file first
    files = {"file": ("test.mp3", BytesIO(sample_audio_content), "audio/mpeg")}
    response = client.post("/api/upload", files=files)
    assert response.status_code == 200, f"Upload failed: {response.json()}"
    file_id = response.json()["file_id"]

    # now manually create the transcription and summary records
    from sqlalchemy import select

    from app.database import async_session
    from app.models import MeetingSummary, SummaryStatus, Transcription, TranscriptionStatus

    async def setup_records():
        async with async_session() as db:
            # get the transcription
            result = await db.execute(
                select(Transcription).where(Transcription.file_id == file_id)
            )
            transcription = result.scalar_one()

            # update it to completed
            transcription.status = TranscriptionStatus.completed
            transcription.transcript_text = "This is a test transcript."

            # create a summary
            summary = MeetingSummary(
                transcription_id=transcription.id,
                status=SummaryStatus.completed,
                summary_text=json.dumps(["Point 1", "Point 2"]),
                action_items=json.dumps([
                    {"task": "Task 1", "owner": "Alice"},
                    {"task": "Task 2", "owner": None}
                ]),
                key_decisions=json.dumps(["Decision 1"]),
                follow_up_questions=json.dumps(["Question 1"]),
            )
            db.add(summary)
            await db.commit()

    asyncio.new_event_loop().run_until_complete(setup_records())

    return file_id


class TestEmailNotification:
    """Tests for the email notification endpoint."""

    def test_send_email_no_api_key(self, client, file_with_summary):
        """Should fail gracefully when RESEND_API_KEY is not configured."""
        from app.config import settings

        original_key = settings.resend_api_key
        settings.resend_api_key = ""

        try:
            response = client.post(
                f"/api/notify/{file_with_summary}/email",
                json={"email": "test@example.com"}
            )
            assert response.status_code == 400
            data = response.json()
            # custom error handler returns 'message' not 'detail'
            msg = data.get("message", data.get("detail", "")).lower()
            assert "not configured" in msg or "api key" in msg
        finally:
            settings.resend_api_key = original_key

    def test_send_email_invalid_email(self, client, file_with_summary):
        """Should reject invalid email addresses."""
        response = client.post(
            f"/api/notify/{file_with_summary}/email",
            json={"email": "not-an-email"}
        )
        assert response.status_code == 422  # validation error

    def test_send_email_missing_email(self, client, file_with_summary):
        """Should require email field."""
        response = client.post(
            f"/api/notify/{file_with_summary}/email",
            json={}
        )
        assert response.status_code == 422

    def test_send_email_file_not_found(self, client, temp_upload_dir):
        """Should return 404 for non-existent file."""
        response = client.post(
            "/api/notify/nonexistent-id/email",
            json={"email": "test@example.com"}
        )
        assert response.status_code == 404

    def test_send_email_no_summary(self, client, temp_upload_dir, sample_audio_content):
        """Should fail if file has no summary yet."""
        from io import BytesIO

        # upload file but don't create summary
        files = {"file": ("test.mp3", BytesIO(sample_audio_content), "audio/mpeg")}
        response = client.post("/api/upload", files=files)
        assert response.status_code == 200, f"Upload failed: {response.json()}"
        file_id = response.json()["file_id"]

        response = client.post(
            f"/api/notify/{file_id}/email",
            json={"email": "test@example.com"}
        )
        assert response.status_code == 400
        msg = response.json().get("message", response.json().get("detail", "")).lower()
        assert "summary" in msg

    @patch("app.services.notifications.resend.Emails.send")
    def test_send_email_success(self, mock_send, client, file_with_summary):
        """Should successfully send email when configured."""
        from app.config import settings

        original_key = settings.resend_api_key
        settings.resend_api_key = "test-api-key"

        mock_send.return_value = {"id": "email-123"}

        try:
            response = client.post(
                f"/api/notify/{file_with_summary}/email",
                json={"email": "test@example.com"}
            )
            assert response.status_code == 200
            data = response.json()
            assert data["message"] == "Email sent successfully"
            assert data["email"] == "test@example.com"
            assert data["success"] is True

            # verify the email was sent with correct params
            mock_send.assert_called_once()
            call_args = mock_send.call_args[0][0]
            assert call_args["to"] == ["test@example.com"]
            assert "test.mp3" in call_args["subject"]
        finally:
            settings.resend_api_key = original_key

    @patch("app.services.notifications.resend.Emails.send")
    def test_send_email_with_custom_subject(self, mock_send, client, file_with_summary):
        """Should use custom subject when provided."""
        from app.config import settings

        original_key = settings.resend_api_key
        settings.resend_api_key = "test-api-key"

        mock_send.return_value = {"id": "email-456"}

        try:
            response = client.post(
                f"/api/notify/{file_with_summary}/email",
                json={"email": "test@example.com", "subject": "Custom Subject"}
            )
            assert response.status_code == 200

            call_args = mock_send.call_args[0][0]
            assert call_args["subject"] == "Custom Subject"
        finally:
            settings.resend_api_key = original_key


class TestSlackNotification:
    """Tests for the Slack notification endpoint."""

    def test_send_slack_no_webhook(self, client, file_with_summary):
        """Should fail when no webhook is configured or provided."""
        from app.config import settings

        original_url = settings.slack_webhook_url
        settings.slack_webhook_url = ""

        try:
            response = client.post(
                f"/api/notify/{file_with_summary}/slack",
                json={}
            )
            assert response.status_code == 400
            msg = response.json().get("message", response.json().get("detail", "")).lower()
            assert "not configured" in msg
        finally:
            settings.slack_webhook_url = original_url

    def test_send_slack_file_not_found(self, client, temp_upload_dir):
        """Should return 404 for non-existent file."""
        response = client.post(
            "/api/notify/nonexistent-id/slack",
            json={}
        )
        assert response.status_code == 404

    def test_send_slack_no_summary(self, client, temp_upload_dir, sample_audio_content):
        """Should fail if file has no summary yet."""
        from io import BytesIO

        files = {"file": ("test.mp3", BytesIO(sample_audio_content), "audio/mpeg")}
        response = client.post("/api/upload", files=files)
        assert response.status_code == 200, f"Upload failed: {response.json()}"
        file_id = response.json()["file_id"]

        response = client.post(
            f"/api/notify/{file_id}/slack",
            json={}
        )
        assert response.status_code == 400
        msg = response.json().get("message", response.json().get("detail", "")).lower()
        assert "summary" in msg

    @patch("app.services.notifications.httpx.AsyncClient")
    def test_send_slack_with_custom_webhook(self, mock_client_class, client, file_with_summary):
        """Should use custom webhook URL when provided."""
        # mock the async client
        mock_client = AsyncMock()
        mock_response = AsyncMock()
        mock_response.raise_for_status = lambda: None
        mock_client.post.return_value = mock_response
        mock_client_class.return_value.__aenter__.return_value = mock_client

        custom_webhook = "https://hooks.slack.com/custom/webhook"

        response = client.post(
            f"/api/notify/{file_with_summary}/slack",
            json={"webhook_url": custom_webhook}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Sent to Slack successfully"
        assert data["success"] is True

        # verify the custom webhook was used
        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        assert call_args[0][0] == custom_webhook

    @patch("app.services.notifications.httpx.AsyncClient")
    def test_send_slack_with_default_webhook(self, mock_client_class, client, file_with_summary):
        """Should use default webhook from settings."""
        from app.config import settings

        original_url = settings.slack_webhook_url
        settings.slack_webhook_url = "https://hooks.slack.com/default/webhook"

        mock_client = AsyncMock()
        mock_response = AsyncMock()
        mock_response.raise_for_status = lambda: None
        mock_client.post.return_value = mock_response
        mock_client_class.return_value.__aenter__.return_value = mock_client

        try:
            response = client.post(
                f"/api/notify/{file_with_summary}/slack",
                json={}
            )
            assert response.status_code == 200

            # verify the default webhook was used
            call_args = mock_client.post.call_args
            assert call_args[0][0] == "https://hooks.slack.com/default/webhook"
        finally:
            settings.slack_webhook_url = original_url


class TestNotificationFormatting:
    """Tests for notification content formatting."""

    def test_format_summary_for_text(self):
        """Test plain text formatting of summary."""
        from app.services.notifications import format_summary_for_text

        summary_data = {
            "summary": ["Point 1", "Point 2"],
            "action_items": [
                {"task": "Do thing", "owner": "Alice"},
                {"task": "Other thing", "owner": None}
            ],
            "key_decisions": ["Decided X"],
            "follow_up_questions": ["Question?"],
        }

        text = format_summary_for_text(summary_data, "test.mp3")

        assert "Meeting Notes: test.mp3" in text
        assert "Summary" in text
        assert "Point 1" in text
        assert "Action Items" in text
        assert "Do thing" in text
        assert "Alice" in text
        assert "Key Decisions" in text
        assert "Decided X" in text
        assert "Follow-up Questions" in text
        assert "Question?" in text

    def test_format_summary_for_html(self):
        """Test HTML formatting of summary."""
        from app.services.notifications import format_summary_for_html

        summary_data = {
            "summary": ["Point 1"],
            "action_items": [{"task": "Do thing", "owner": "Bob"}],
            "key_decisions": [],
            "follow_up_questions": [],
        }

        html = format_summary_for_html(summary_data, "meeting.mp4")

        assert "<html>" in html
        assert "Meeting Notes: meeting.mp4" in html
        assert "<h2>Summary</h2>" in html
        assert "Point 1" in html
        assert "<h2>Action Items</h2>" in html
        assert "Do thing" in html
        assert "Bob" in html
        # should not have sections for empty lists
        assert "Key Decisions" not in html

    def test_format_empty_summary(self):
        """Test formatting with empty summary data."""
        from app.services.notifications import format_summary_for_text

        summary_data = {
            "summary": [],
            "action_items": [],
            "key_decisions": [],
            "follow_up_questions": [],
        }

        text = format_summary_for_text(summary_data, "empty.mp3")

        assert "Meeting Notes: empty.mp3" in text
        # shouldn't have section headers for empty sections
        assert "Summary" not in text or "- " not in text.split("Summary")[1].split("\n")[0]
