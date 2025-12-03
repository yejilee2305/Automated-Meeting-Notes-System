# Automated Meeting Notes System

A system that takes audio/video recordings, transcribes them, extracts action items and key points, and delivers summaries via email or Slack.

## Current Status: Phase 4 (UI)

Full-featured web interface with drag-and-drop uploads, real-time progress tracking, and copy-to-clipboard functionality. Mobile responsive.

## Quick Start

```bash
# create virtual environment
python -m venv venv
source venv/bin/activate  # on Windows: venv\Scripts\activate

# install dependencies
pip install -r requirements.txt

# set your OpenAI API key
export OPENAI_API_KEY="your-key-here"

# run the server
uvicorn app.main:app --reload
```

Open `http://localhost:8000` in your browser to use the web interface.

## Features

- **Drag & drop** file upload
- **Real-time progress** tracking with visual steps
- **AI-powered summarization** extracts:
  - Meeting summary (3-5 bullet points)
  - Action items with owners
  - Key decisions
  - Follow-up questions
- **Copy to clipboard** for easy sharing
- **Mobile responsive** design

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

### Start Transcription
```
POST /api/transcribe/{file_id}
```
Start transcribing an uploaded file. Runs in the background.

### Check Transcription Status
```
GET /api/transcribe/{file_id}/status
```
Get the current status and progress. Returns the transcript when complete.

### List Transcriptions
```
GET /api/transcriptions
GET /api/transcriptions?status=completed
```
List all transcription jobs. Optionally filter by status.

### Start Summarization
```
POST /api/summarize/{file_id}
```
Generate a summary from a completed transcription. Uses GPT-4 to extract:
- Meeting summary (3-5 bullet points)
- Action items with owners
- Key decisions
- Follow-up questions

### Check Summary Status
```
GET /api/summarize/{file_id}/status
```
Get the summary status. Returns full structured summary when complete.

### List Summaries
```
GET /api/summaries
GET /api/summaries?status=completed
```
List all summary jobs. Optionally filter by status.

## Configuration

Create a `.env` file with:
```
OPENAI_API_KEY=your-key-here
```

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
- **Frontend**: Jinja2 templates + vanilla JavaScript
- **AI/ML**: OpenAI Whisper API (transcription), GPT-4 Turbo (summarization)
- **Database**: SQLite (dev), PostgreSQL (production)
- **File Storage**: Local for now, AWS S3 planned
