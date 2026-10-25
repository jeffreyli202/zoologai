from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, Float, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.animal import Animal
    from app.models.camera_capture import CameraCapture
    from app.models.camera_source import CameraSource
    from app.models.frame import Frame
    from app.models.video import Video


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Observation(Base):
    """
    A behavior label from vision analysis of one still (video frame or camera capture).

    Unique frame_id / camera_capture_id keep re-analyze calls idempotent.
    """

    __tablename__ = "observations"
    __table_args__ = (
        UniqueConstraint("frame_id", name="uq_observations_frame_id"),
        # One row per animal identified in a camera still (multi-animal frames OK).
        UniqueConstraint(
            "camera_capture_id",
            "animal_id",
            name="uq_observations_capture_animal",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    animal_id: Mapped[int] = mapped_column(ForeignKey("animals.id"), nullable=False, index=True)
    # Video-frame path (nullable when from live/local camera monitoring).
    video_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("videos.id"), nullable=True, index=True
    )
    frame_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("frames.id"), nullable=True, index=True
    )
    camera_source_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("camera_sources.id"), nullable=True, index=True
    )
    camera_capture_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("camera_captures.id"), nullable=True, index=True
    )
    observed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utc_now,
    )
    # Seconds into the video where the behavior was seen (0 for live snapshots).
    video_timestamp_seconds: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    behavior: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # What was visibly present in the frame that supports the label.
    visible_evidence: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # Model confidence estimate 0.0–1.0 (not a calibrated scientific probability).
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    animal: Mapped[Animal] = relationship(back_populates="observations")
    video: Mapped[Optional[Video]] = relationship(back_populates="observations")
    frame: Mapped[Optional[Frame]] = relationship(back_populates="observations")
    camera_source: Mapped[Optional[CameraSource]] = relationship()
    camera_capture: Mapped[Optional[CameraCapture]] = relationship(
        back_populates="observations"
    )
