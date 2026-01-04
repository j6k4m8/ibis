"""Application configuration."""

from __future__ import annotations

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings loaded from environment variables.

    Attributes:
        database_url: Database connection string.
        environment: Runtime environment name.
        allow_origins: Allowed CORS origins.
    """

    model_config = SettingsConfigDict(
        env_prefix="IBIS_", env_file=".env", extra="ignore"
    )

    database_url: str = "sqlite:///./ibis.db"
    environment: str = "dev"
    allow_origins: list[str] = ["http://localhost:5173"]
    secret_key: str = "dev-secret-change-me"
    access_token_expire_minutes: int = 60 * 24
    public_base_url: str = "http://localhost:8000"
    upload_dir: str = "./uploads"
    upload_max_bytes: int = 1000 * 1024 * 1024  # 1GB
    keep_raw_uploads: bool = False
    storage_limit_bytes: int = 10 * 1024 * 1024 * 1024  # 10GB
    fetch_video_titles: bool = True
    processing_enabled: bool = False
    transcode_enabled: bool = True
    transcription_enabled: bool = True
    ffmpeg_path: str = "ffmpeg"
    ffprobe_path: str = "ffprobe"
    ytdlp_path: str = "yt-dlp"
    whisper_path: str = "whisper"
    whisper_model: str = "base"
    whisper_language: str = "en"
    worker_poll_interval_seconds: int = 5


@lru_cache
def get_settings() -> Settings:
    """Load application settings.

    Returns:
        Settings: Loaded settings instance.
    """

    return Settings()
