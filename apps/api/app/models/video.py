from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.animal import Animal
    from app.models.observation import Observation


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Video(Base):
    __tablename__ = "videos"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    # Foreign key: this video belongs to exactly one animal.
    animal_id: Mapped[int] = mapped_column(ForeignKey("animals.id"), nullable=False, index=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    # e.g. pending | processing | ready | failed (AI pipeline will use these later)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utc_now,
    )

    animal: Mapped[Animal] = relationship(back_populates="videos")
    observations: Mapped[list[Observation]] = relationship(back_populates="video")
