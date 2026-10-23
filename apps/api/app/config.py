from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """App settings loaded from environment variables / .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # SQLite file stored under apps/api/ by default (relative to process cwd).
    database_url: str = "sqlite:///./zoologai.db"


@lru_cache
def get_settings() -> Settings:
    return Settings()
