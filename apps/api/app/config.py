from functools import lru_cache
from typing import Optional

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

    # Local private video storage (relative to process cwd when running uvicorn).
    upload_dir: str = "./uploads/videos"

    # Extracted JPEG frames: uploads/frames/video_{id}/…
    frame_dir: str = "./uploads/frames"

    # 100 MB hard limit for uploaded videos.
    max_upload_bytes: int = 100 * 1024 * 1024

    # Sample one frame every N seconds of source video.
    frame_interval_seconds: float = 15.0

    # Cap how many stills we keep per video (keeps storage + future AI cost down).
    max_frames_per_video: int = 12

    # Longest edge for resized frames (width or height).
    frame_max_dimension: int = 1280

    # Google Gemini — keep the secret in backend .env only (never NEXT_PUBLIC_).
    gemini_api_key: Optional[str] = None
    gemini_model: str = "gemini-3.5-flash-lite"

    # Cap how many new Gemini calls one "Analyze Video" job may make.
    max_ai_calls_per_video_job: int = 12

    # Camera monitoring (authorized snapshot URLs or local sample folders).
    camera_capture_dir: str = "./uploads/camera_captures"
    # Scheduler wake interval (seconds) — checks which sources are due.
    monitor_scheduler_tick_seconds: int = 30
    # Floor for user-configured poll interval (minutes).
    min_monitor_interval_minutes: int = 1
    # Default poll interval when creating a source.
    default_monitor_interval_minutes: int = 15
    # HTTP snapshot fetch limits.
    monitor_fetch_timeout_seconds: float = 20.0
    monitor_max_image_bytes: int = 8 * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()
