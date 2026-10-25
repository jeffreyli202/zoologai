from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.observation import Observation
    from app.models.video import Video


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Frame(Base):
    """
    One still image sampled from a video at a known timestamp.

    Idempotency: (video_id, frame_index) is unique so repeated extractions
    cannot insert the same slot twice.
    """

    __tablename__ = "frames"
    __table_args__ = (
        UniqueConstraint("video_id", "frame_index", name="uq_frames_video_frame_index"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    video_id: Mapped[int] = mapped_column(ForeignKey("videos.id"), nullable=False, index=True)
    # Safe on-disk basename under uploads/frames/video_{id}/
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    # Position in the source video (seconds from start).
    timestamp_seconds: Mapped[float] = mapped_column(Float, nullable=False)
    # 0-based order among extracted frames for this video.
    frame_index: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utc_now,
    )

    video: Mapped[Video] = relationship(back_populates="frames")
    observations: Mapped[list[Observation]] = relationship(back_populates="frame")
