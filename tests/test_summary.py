import io

from app.services.summarization import chunk_transcript, merge_summaries


def test_summary_status_not_started(client, temp_upload_dir, sample_audio_content):
    """Checking summary status before requesting should say not started."""
    # upload a file
    upload_response = client.post(
        "/api/upload",
        files={"file": ("meeting.mp3", io.BytesIO(sample_audio_content), "audio/mpeg")}
    )
    file_id = upload_response.json()["file_id"]

    # check summary status before starting
    response = client.get(f"/api/summarize/{file_id}/status")
    assert response.status_code == 200
    assert response.json()["status"] == "not_started"


def test_summarize_requires_completed_transcription(client, temp_upload_dir, sample_audio_content):
    """Can't summarize until transcription is done."""
    # upload a file (transcription will be pending)
    upload_response = client.post(
        "/api/upload",
        files={"file": ("meeting.mp3", io.BytesIO(sample_audio_content), "audio/mpeg")}
    )
    file_id = upload_response.json()["file_id"]

    # try to summarize
    response = client.post(f"/api/summarize/{file_id}")
    assert response.status_code == 400
    data = response.json()
    msg = data.get("message", data.get("detail", "")).lower()
    assert "completed" in msg


def test_summarize_not_found(client, temp_upload_dir):
    """Summarizing non-existent file should 404."""
    response = client.post("/api/summarize/fake-file-id")
    assert response.status_code == 404


def test_summary_status_not_found(client, temp_upload_dir):
    """Checking status for non-existent file should 404."""
    response = client.get("/api/summarize/fake-file-id/status")
    assert response.status_code == 404


def test_list_summaries_empty(client, temp_upload_dir):
    """Listing summaries when none exist should return empty list."""
    response = client.get("/api/summaries")
    assert response.status_code == 200
    assert response.json()["count"] == 0


def test_list_summaries_invalid_status(client, temp_upload_dir):
    """Invalid status filter should return error."""
    response = client.get("/api/summaries?status=invalid")
    assert response.status_code == 400
    data = response.json()
    msg = data.get("message", data.get("detail", ""))
    assert "Invalid status" in msg


# unit tests for helper functions

def test_chunk_transcript_short():
    """Short transcripts shouldn't be chunked."""
    transcript = "This is a short meeting."
    chunks = chunk_transcript(transcript)
    assert len(chunks) == 1
    assert chunks[0] == transcript


def test_chunk_transcript_long():
    """Long transcripts should be split into chunks."""
    # create a transcript longer than max
    transcript = "Hello world. " * 10000  # ~130k chars
    chunks = chunk_transcript(transcript, max_chars=50000)
    assert len(chunks) > 1
    # make sure we got all the content
    combined = " ".join(chunks)
    assert "Hello world" in combined


def test_merge_summaries_single():
    """Single summary should pass through unchanged."""
    summary = {
        "summary": ["point 1"],
        "action_items": [{"task": "do something", "owner": "Alice"}],
        "key_decisions": ["decision 1"],
        "follow_up_questions": ["question 1"]
    }
    merged = merge_summaries([summary])
    assert merged == summary


def test_merge_summaries_deduplication():
    """Merging should deduplicate identical items."""
    summaries = [
        {
            "summary": ["point 1", "point 2"],
            "action_items": [{"task": "task A", "owner": "Alice"}],
            "key_decisions": ["decision 1"],
            "follow_up_questions": []
        },
        {
            "summary": ["point 2", "point 3"],  # point 2 is a duplicate
            "action_items": [{"task": "task A", "owner": "Bob"}],  # same task, different owner
            "key_decisions": ["decision 1", "decision 2"],  # decision 1 is duplicate
            "follow_up_questions": ["question 1"]
        }
    ]

    merged = merge_summaries(summaries)

    # should have 3 unique summary points
    assert len(merged["summary"]) == 3
    # should have 1 unique action item (deduped by task)
    assert len(merged["action_items"]) == 1
    # should have 2 unique decisions
    assert len(merged["key_decisions"]) == 2
    # should have 1 question
    assert len(merged["follow_up_questions"]) == 1
