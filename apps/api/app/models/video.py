from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.animal import Animal
    from app.models.frame import Frame
    from app.models.observation import Observation


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Video(Base):
    __tablename__ = "videos"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    # Foreign key: this video belongs to exactly one animal.
    animal_id: Mapped[int] = mapped_column(ForeignKey("animals.id"), nullable=False, index=True)
    # Safe name on disk (UUID + extension) — never use this as a user-facing label alone.
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    # Original basename from the client (display only; not used for disk paths).
    original_filename: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    size_bytes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    # Workflow: uploaded | pending | processing | completed | failed
    # (legacy values like frames_extracted may still appear on older rows)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="uploaded")
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utc_now,
    )

    # Full-video analysis job progress (polled by the frontend).
    analysis_progress: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    analysis_message: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    analysis_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    analysis_frames_total: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    analysis_frames_done: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    analysis_ai_calls: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    analysis_started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    analysis_finished_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    animal: Mapped[Animal] = relationship(back_populates="videos")
    observations: Mapped[list[Observation]] = relationship(back_populates="video")
    frames: Mapped[list[Frame]] = relationship(
        back_populates="video",
        cascade="all, delete-orphan",
    )
