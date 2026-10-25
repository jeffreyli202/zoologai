from __future__ import annotations

from datetime import date, datetime, timezone
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Date, DateTime, ForeignKey, Integer, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.animal import Animal


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class DailyJournal(Base):
    """
    Observation journal for one animal over a time bucket.

    Primary mode: one entry per UTC hour (hour 0–23).
    Legacy whole-day summaries use hour=-1.
    """

    __tablename__ = "daily_journals"
    __table_args__ = (
        UniqueConstraint(
            "animal_id", "date", "hour", name="uq_daily_journals_animal_date_hour"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    animal_id: Mapped[int] = mapped_column(ForeignKey("animals.id"), nullable=False, index=True)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    # UTC hour 0–23 for hourly journals; -1 = legacy full-day summary.
    hour: Mapped[int] = mapped_column(Integer, nullable=False, default=-1)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    # JSON array of Observation.id values used to write this entry (traceability).
    source_observation_ids: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utc_now,
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    animal: Mapped[Animal] = relationship(back_populates="daily_journals")
