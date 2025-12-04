# Automated Meeting Notes System

An AI-powered application that transforms audio/video recordings into structured meeting notes with action items, key decisions, and follow-up questions. Delivers summaries via email or Slack.

![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)
![Tests](https://img.shields.io/badge/Tests-44%20passing-brightgreen.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

## Features

- **Drag & drop** file upload with real-time progress tracking
- **AI transcription** using OpenAI Whisper API
- **Smart summarization** using GPT-4 Turbo extracts:
  - Meeting summary (3-5 key points)
  - Action items with assigned owners
  - Key decisions made
  - Follow-up questions
- **Share via email** (Resend) or **Slack** webhooks
- **Rate limiting** to prevent abuse
- **Mobile responsive** design
- **Copy to clipboard** for easy sharing

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Frontend                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │ Upload Zone │  │  Progress   │  │    Results Display      │  │
│  │ (drag/drop) │  │   Tracker   │  │ (summary, actions, etc) │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      FastAPI Backend                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────────┐ │
│  │  Upload  │  │Transcribe│  │Summarize │  │  Notifications   │ │
│  │  Router  │  │  Router  │  │  Router  │  │     Router       │ │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────────┬─────────┘ │
│       │             │             │                  │           │
│  ┌────▼─────────────▼─────────────▼──────────────────▼─────────┐│
│  │                    Service Layer                             ││
│  │  ┌─────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────┐ ││
│  │  │  Audio  │  │Transcription│  │Summarization│  │ Notify  │ ││
│  │  │ Service │  │   Service   │  │   Service   │  │ Service │ ││
│  │  └────┬────┘  └──────┬──────┘  └──────┬──────┘  └────┬────┘ ││
│  └───────┼──────────────┼────────────────┼──────────────┼──────┘│
│          │              │                │              │        │
│          │         ┌────▼────┐      ┌────▼────┐    ┌────▼────┐  │
│          │         │ OpenAI  │      │ OpenAI  │    │ Resend/ │  │
│          │         │ Whisper │      │ GPT-4   │    │  Slack  │  │
│          │         └─────────┘      └─────────┘    └─────────┘  │
│          │                                                       │
│     ┌────▼────────────────────────────────────────────────────┐ │
│     │              SQLite Database (async)                     │ │
│     │  ┌──────────────────┐  ┌───────────────────────────┐    │ │
│     │  │  Transcriptions  │  │    Meeting Summaries      │    │ │
│     │  └──────────────────┘  └───────────────────────────┘    │ │
│     └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

## Tech Stack

| Layer | Technology |
|-------|------------|
| **Backend** | Python 3.11+, FastAPI, SQLAlchemy (async) |
| **Frontend** | Jinja2 templates, vanilla JavaScript |
| **AI/ML** | OpenAI Whisper API, GPT-4 Turbo |
| **Database** | SQLite + aiosqlite (dev), PostgreSQL (prod) |
| **Email** | Resend API |
| **Notifications** | Slack Webhooks |
| **Rate Limiting** | slowapi |
| **Testing** | pytest, pytest-asyncio |

## Quick Start

### Prerequisites

- Python 3.11 or higher
- OpenAI API key
- (Optional) Resend API key for email
- (Optional) Slack webhook URL

### Local Development

```bash
# Clone the repository
git clone https://github.com/yourusername/automated-meeting-notes.git
cd automated-meeting-notes

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your API keys

# Run the server
uvicorn app.main:app --reload
```

Open `http://localhost:8000` in your browser.

### Using Docker

```bash
# Build and run
docker build -t meeting-notes .
docker run -p 8000:8000 --env-file .env meeting-notes

# Or use docker-compose
docker-compose up
```

## Environment Variables

Create a `.env` file in the project root:

```bash
# Required
OPENAI_API_KEY=sk-your-openai-api-key

# Optional - Email notifications
RESEND_API_KEY=re_your-resend-api-key
EMAIL_FROM=Meeting Notes <notes@yourdomain.com>

# Optional - Slack notifications
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/xxx/yyy/zzz

# Optional - Configuration
DEBUG=false
MAX_FILE_SIZE_MB=500
RATE_LIMIT_PER_MINUTE=10
DATABASE_URL=sqlite+aiosqlite:///./meeting_notes.db
```

## API Endpoints

### Health Check
```
GET /health
```
Returns service status. Use for monitoring/load balancers.

### File Upload
```
POST /api/upload
Content-Type: multipart/form-data

Supported formats: mp3, mp4, wav, m4a, webm, ogg, mpeg, aac
Max size: 500MB (configurable)
```

### Transcription
```
POST /api/transcribe/{file_id}     # Start transcription
GET  /api/transcribe/{file_id}/status  # Check status/progress
GET  /api/transcriptions           # List all transcriptions
GET  /api/transcriptions?status=completed  # Filter by status
```

### Summarization
```
POST /api/summarize/{file_id}      # Start summarization
GET  /api/summarize/{file_id}/status   # Check status
GET  /api/summaries                # List all summaries
```

### Notifications
```
POST /api/notify/{file_id}/email   # Send via email
     Body: {"email": "user@example.com", "subject": "Optional subject"}

POST /api/notify/{file_id}/slack   # Send to Slack
     Body: {"webhook_url": "https://hooks.slack.com/..."} (optional)
```

## Project Structure

```
automated-meeting-notes/
├── app/
│   ├── main.py              # FastAPI app entry point
│   ├── config.py            # Settings and configuration
│   ├── database.py          # SQLAlchemy async setup
│   ├── models.py            # Database models
│   ├── errors.py            # Custom error handlers
│   ├── rate_limit.py        # Rate limiting config
│   ├── routers/
│   │   ├── health.py        # Health check endpoint
│   │   ├── upload.py        # File upload handling
│   │   ├── transcription.py # Whisper integration
│   │   ├── summary.py       # GPT-4 summarization
│   │   ├── notifications.py # Email/Slack delivery
│   │   └── frontend.py      # Web UI routes
│   ├── services/
│   │   ├── audio.py         # Audio processing
│   │   ├── transcription.py # OpenAI Whisper service
│   │   ├── summarization.py # GPT-4 service
│   │   └── notifications.py # Email/Slack services
│   ├── templates/
│   │   └── index.html       # Main web UI
│   └── static/
│       ├── css/style.css    # Styles
│       └── js/app.js        # Frontend logic
├── tests/
│   ├── conftest.py          # Test fixtures
│   ├── test_health.py
│   ├── test_upload.py
│   ├── test_transcription.py
│   ├── test_summary.py
│   ├── test_notifications.py
│   └── test_frontend.py
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── .env.example
└── README.md
```

## Running Tests

```bash
# Run all tests
pytest -v

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_notifications.py -v
```

## Deployment

### Railway

1. Connect your GitHub repository to Railway
2. Add environment variables in Railway dashboard
3. Railway auto-detects Python and deploys

### Fly.io

```bash
# Install flyctl
curl -L https://fly.io/install.sh | sh

# Login and launch
fly auth login
fly launch

# Set secrets
fly secrets set OPENAI_API_KEY=sk-xxx
fly secrets set RESEND_API_KEY=re_xxx

# Deploy
fly deploy
```

### Vercel (Frontend Only)

If deploying frontend separately:

```bash
vercel --prod
```

## Tech Decisions & Trade-offs

### Why FastAPI?
- Async support for handling concurrent transcription jobs
- Automatic OpenAPI documentation
- Type hints and validation with Pydantic
- Background tasks for long-running operations

### Why SQLite for Development?
- Zero configuration needed
- Good enough for single-instance deployment
- Easy migration to PostgreSQL for production

### Why Vanilla JavaScript?
- No build step required
- Smaller bundle size
- Simpler deployment
- Sufficient for the UI complexity

### Audio Chunking Strategy
- OpenAI Whisper has a 25MB limit per request
- Long audio files are chunked by duration (10 min segments)
- Transcripts are concatenated in order

### GPT-4 for Summarization
- Better at understanding context than GPT-3.5
- JSON response format ensures structured output
- Token limits handled via chunking + merging

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests (`pytest -v`)
5. Run linting (`ruff check .`)
6. Commit (`git commit -m 'Add amazing feature'`)
7. Push (`git push origin feature/amazing-feature`)
8. Open a Pull Request

## License

MIT License - see [LICENSE](LICENSE) for details.

## Acknowledgments

- [OpenAI](https://openai.com) for Whisper and GPT-4 APIs
- [FastAPI](https://fastapi.tiangolo.com) for the excellent framework
- [Resend](https://resend.com) for email delivery
