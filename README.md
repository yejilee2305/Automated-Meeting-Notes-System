# Automated Meeting Notes System

A system that takes audio/video recordings, transcribes them, extracts action items and key points, and delivers summaries via email or Slack.

## Current Status: Phase 1 (Foundation)

The API currently accepts and stores audio/video files. Transcription and summarization features are coming in future phases.

## Quick Start

```bash
# create virtual environment
python -m venv venv
source venv/bin/activate  # on Windows: venv\Scripts\activate

# install dependencies
pip install -r requirements.txt

# run the server
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`

## API Endpoints

### Health Check
```
GET /health
```
Returns the service status. Good for monitoring.

### Upload File
```
POST /api/upload
```
Upload an audio or video file. Supported formats: mp3, mp4, wav, m4a, webm, ogg, mpeg, aac

### Get File Info
```
GET /api/files/{file_id}
```
Check if a file exists and get its details.

## Running Tests

```bash
pytest -v
```

## Linting

```bash
ruff check app/ tests/
```

## Tech Stack

- **Backend**: Python + FastAPI
- **AI/ML**: OpenAI Whisper API + GPT-4 (coming soon)
- **Database**: PostgreSQL (coming soon)
- **File Storage**: Local for now, AWS S3 planned
