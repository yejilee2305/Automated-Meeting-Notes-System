import io
from unittest.mock import AsyncMock, patch

import pytest


@pytest.fixture
def mock_openai():
    """Mock the OpenAI client so we don't make real API calls."""
    with patch("app.services.transcription.AsyncOpenAI") as mock:
        client = AsyncMock()
        client.audio.transcriptions.create = AsyncMock(
            return_value="This is a test transcription."
        )
        mock.return_value = client
        yield client


def test_upload_creates_transcription_record(client, temp_upload_dir, sample_audio_content):
    """Uploading a file should create a pending transcription record."""
    response = client.post(
        "/api/upload",
        files={"file": ("meeting.mp3", io.BytesIO(sample_audio_content), "audio/mpeg")}
    )

    assert response.status_code == 200
    file_id = response.json()["file_id"]

    # check the status endpoint
    status_response = client.get(f"/api/transcribe/{file_id}/status")
    assert status_response.status_code == 200

    data = status_response.json()
    assert data["status"] == "pending"
    assert data["progress"] == 0


def test_list_transcriptions(client, temp_upload_dir, sample_audio_content):
    """Should list all transcription jobs."""
    # upload a couple files
    for i in range(2):
        client.post(
            "/api/upload",
            files={"file": (f"meeting{i}.mp3", io.BytesIO(sample_audio_content), "audio/mpeg")}
        )

    response = client.get("/api/transcriptions")
    assert response.status_code == 200

    data = response.json()
    assert data["count"] >= 2


def test_list_transcriptions_filter_by_status(client, temp_upload_dir, sample_audio_content):
    """Should filter transcriptions by status."""
    # upload a file (creates pending transcription)
    client.post(
        "/api/upload",
        files={"file": ("test.mp3", io.BytesIO(sample_audio_content), "audio/mpeg")}
    )

    # filter for pending
    response = client.get("/api/transcriptions?status=pending")
    assert response.status_code == 200
    data = response.json()
    assert all(t["status"] == "pending" for t in data["transcriptions"])


def test_list_transcriptions_invalid_status(client, temp_upload_dir):
    """Invalid status filter should return an error."""
    response = client.get("/api/transcriptions?status=invalid")
    assert response.status_code == 400
    data = response.json()
    msg = data.get("message", data.get("detail", ""))
    assert "Invalid status" in msg


def test_transcription_status_not_found(client, temp_upload_dir):
    """Asking for status of non-existent file should 404."""
    response = client.get("/api/transcribe/fake-file-id/status")
    assert response.status_code == 404


def test_start_transcription_not_found(client, temp_upload_dir):
    """Starting transcription for non-existent file should 404."""
    response = client.post("/api/transcribe/fake-file-id")
    assert response.status_code == 404
