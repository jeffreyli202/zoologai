from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.animal import Animal
    from app.models.video import Video


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Observation(Base):
    __tablename__ = "observations"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    animal_id: Mapped[int] = mapped_column(ForeignKey("animals.id"), nullable=False, index=True)
    video_id: Mapped[int] = mapped_column(ForeignKey("videos.id"), nullable=False, index=True)
    observed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utc_now,
    )
    # Seconds into the video where the behavior was seen.
    video_timestamp_seconds: Mapped[float] = mapped_column(Float, nullable=False)
    behavior: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # Model confidence score, typically 0.0–1.0
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    animal: Mapped[Animal] = relationship(back_populates="observations")
    video: Mapped[Video] = relationship(back_populates="observations")
