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

    model_config = SettingsConfigDict(env_prefix="IBIS_", env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./ibis.db"
    environment: str = "dev"
    allow_origins: list[str] = ["http://localhost:5173"]
    secret_key: str = "dev-secret-change-me"
    access_token_expire_minutes: int = 60 * 24
    public_base_url: str = "http://localhost:8000"
    upload_dir: str = "./uploads"
    upload_max_bytes: int = 100 * 1024 * 1024
    storage_limit_bytes: int = 5 * 1024 * 1024 * 1024
    fetch_video_titles: bool = True


@lru_cache
def get_settings() -> Settings:
    """Load application settings.

    Returns:
        Settings: Loaded settings instance.
    """

    return Settings()
