from __future__ import annotations

from datetime import date, datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, ForeignKey, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.animal import Animal


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class DailyJournal(Base):
    __tablename__ = "daily_journals"
    __table_args__ = (
        # One journal entry per animal per calendar day.
        UniqueConstraint("animal_id", "date", name="uq_daily_journals_animal_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    animal_id: Mapped[int] = mapped_column(ForeignKey("animals.id"), nullable=False, index=True)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utc_now,
    )

    animal: Mapped[Animal] = relationship(back_populates="daily_journals")
