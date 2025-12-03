import io

from app.config import settings


def test_upload_valid_audio_file(client, temp_upload_dir, sample_audio_content):
    """Should successfully upload an mp3 file."""
    response = client.post(
        "/api/upload",
        files={"file": ("meeting.mp3", io.BytesIO(sample_audio_content), "audio/mpeg")}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "File uploaded successfully"
    assert "file_id" in data
    assert data["original_filename"] == "meeting.mp3"


def test_upload_various_formats(client, temp_upload_dir, sample_audio_content):
    """We should accept all the common audio/video formats."""
    formats = [
        ("test.mp3", "audio/mpeg"),
        ("test.wav", "audio/wav"),
        ("test.mp4", "video/mp4"),
        ("test.m4a", "audio/m4a"),
        ("test.webm", "video/webm"),
    ]

    for filename, content_type in formats:
        response = client.post(
            "/api/upload",
            files={"file": (filename, io.BytesIO(sample_audio_content), content_type)}
        )
        assert response.status_code == 200, f"Failed for {filename}"


def test_upload_rejects_unsupported_format(client, temp_upload_dir):
    """Don't let people upload random file types."""
    response = client.post(
        "/api/upload",
        files={"file": ("document.pdf", io.BytesIO(b"pdf content"), "application/pdf")}
    )

    assert response.status_code == 400
    assert "not allowed" in response.json()["detail"].lower()


def test_upload_rejects_oversized_file(client, temp_upload_dir):
    """
    Files over the size limit should be rejected.
    We set a small limit for testing purposes.
    """
    # temporarily set a tiny limit
    original_limit = settings.max_file_size_mb
    settings.max_file_size_mb = 0.001  # ~1KB

    try:
        # create content larger than the limit
        big_content = b"x" * 10000  # ~10KB

        response = client.post(
            "/api/upload",
            files={"file": ("big.mp3", io.BytesIO(big_content), "audio/mpeg")}
        )

        assert response.status_code == 400
        assert "too large" in response.json()["detail"].lower()
    finally:
        settings.max_file_size_mb = original_limit


def test_upload_creates_unique_ids(client, temp_upload_dir, sample_audio_content):
    """Each upload should get its own unique ID."""
    file_ids = []

    for i in range(3):
        response = client.post(
            "/api/upload",
            files={"file": (f"meeting{i}.mp3", io.BytesIO(sample_audio_content), "audio/mpeg")}
        )
        assert response.status_code == 200
        file_ids.append(response.json()["file_id"])

    # all IDs should be different
    assert len(set(file_ids)) == 3


def test_get_file_info(client, temp_upload_dir, sample_audio_content):
    """Should be able to retrieve info about uploaded files."""
    # first upload a file
    upload_response = client.post(
        "/api/upload",
        files={"file": ("meeting.mp3", io.BytesIO(sample_audio_content), "audio/mpeg")}
    )
    file_id = upload_response.json()["file_id"]

    # now fetch its info
    info_response = client.get(f"/api/files/{file_id}")

    assert info_response.status_code == 200
    data = info_response.json()
    assert data["file_id"] == file_id
    assert data["exists"] is True


def test_get_file_info_not_found(client, temp_upload_dir):
    """Asking for a non-existent file should 404."""
    response = client.get("/api/files/does-not-exist-12345")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()
