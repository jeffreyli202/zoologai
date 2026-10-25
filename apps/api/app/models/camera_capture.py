from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.camera_source import CameraSource
    from app.models.observation import Observation


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class CameraCapture(Base):
    """One retrieved snapshot stored for monitoring (deduped by content hash)."""

    __tablename__ = "camera_captures"
    __table_args__ = (
        UniqueConstraint(
            "camera_source_id",
            "content_hash",
            name="uq_camera_captures_source_hash",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    camera_source_id: Mapped[int] = mapped_column(
        ForeignKey("camera_sources.id"), nullable=False, index=True
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    # Real capture / retrieval time (not "now" when analyzed later).
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    # captured | skipped_duplicate | analyzed | failed
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="captured")
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utc_now
    )

    camera_source: Mapped[CameraSource] = relationship(back_populates="captures")
    observations: Mapped[list[Observation]] = relationship(back_populates="camera_capture")
