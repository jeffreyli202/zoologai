from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.camera_source import CameraSource


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class MonitoringLog(Base):
    """Append-only log of monitor ticks: fetch failures, skips, processing errors."""

    __tablename__ = "monitoring_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    camera_source_id: Mapped[int] = mapped_column(
        ForeignKey("camera_sources.id"), nullable=False, index=True
    )
    # info | skip | error
    level: Mapped[str] = mapped_column(String(20), nullable=False, default="info")
    # fetch | skip_duplicate | analyze | journal | scheduler
    event: Mapped[str] = mapped_column(String(40), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    detail: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utc_now, index=True
    )

    camera_source: Mapped[CameraSource] = relationship(back_populates="logs")
