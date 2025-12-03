from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # App info
    app_name: str = "Meeting Notes API"
    debug: bool = False

    # File upload settings
    upload_dir: str = "uploads"
    max_file_size_mb: int = 500  # most meeting recordings are under 500MB

    # Allowed file extensions for audio/video
    # we support common formats that Whisper can handle
    allowed_extensions: set = {
        ".mp3", ".mp4", ".wav", ".m4a",
        ".webm", ".ogg", ".mpeg", ".aac"
    }

    # OpenAI settings
    openai_api_key: str = ""

    # Whisper has a 25MB limit per request, so we chunk larger files
    whisper_chunk_duration_minutes: int = 10

    # Database
    database_url: str = "sqlite+aiosqlite:///./meeting_notes.db"

    # Email settings (Resend)
    resend_api_key: str = ""
    email_from: str = "Meeting Notes <notes@yourdomain.com>"

    # Slack settings
    slack_webhook_url: str = ""

    # Rate limiting
    rate_limit_per_minute: int = 10

    model_config = SettingsConfigDict(env_file=".env")


# single instance we'll use throughout the app
settings = Settings()
