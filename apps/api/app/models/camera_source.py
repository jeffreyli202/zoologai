from __future__ import annotations

from datetime import date, datetime, timezone
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.animal import Animal
    from app.models.camera_capture import CameraCapture
    from app.models.monitoring_log import MonitoringLog


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class CameraSource(Base):
    """
    An authorized live media URL, snapshot URL, or local sample folder.

    Users must set access_authorized=True only when they have permission to
    poll the URL. Zoo website scraping / protected streams are not supported.
    """

    __tablename__ = "camera_sources"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    # Optional: cameras discover animals via vision (animals_seen), then journal them.
    animal_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("animals.id"), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    # snapshot_url | live_stream | local_folder
    source_type: Mapped[str] = mapped_column(String(40), nullable=False)
    # Direct image or live media URL (HLS / MJPEG / RTSP / snapshot).
    snapshot_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    local_folder_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    # Explicit confirmation that automated access is permitted.
    access_authorized: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # How often to poll (minutes). Default 15.
    interval_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=15)
    # After this many hours in a UTC day window, attempt daily journal once.
    observation_window_hours: Mapped[int] = mapped_column(Integer, nullable=False, default=24)
    # stopped | running | error
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="stopped")
    last_run_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    next_run_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    last_image_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    # For local_folder: next file index in sorted listing.
    local_folder_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_journal_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    # Last UTC hour bucket for which an hourly journal was written (start of hour).
    last_journal_hour_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    capture_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    skip_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utc_now
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    animal: Mapped[Optional[Animal]] = relationship(back_populates="camera_sources")
    captures: Mapped[list[CameraCapture]] = relationship(
        back_populates="camera_source",
        cascade="all, delete-orphan",
    )
    logs: Mapped[list[MonitoringLog]] = relationship(
        back_populates="camera_source",
        cascade="all, delete-orphan",
    )
