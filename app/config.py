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

    model_config = SettingsConfigDict(env_file=".env")


# single instance we'll use throughout the app
settings = Settings()
