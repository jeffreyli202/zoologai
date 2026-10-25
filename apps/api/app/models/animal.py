from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.camera_source import CameraSource
    from app.models.daily_journal import DailyJournal
    from app.models.observation import Observation
    from app.models.video import Video


class Animal(Base):
    __tablename__ = "animals"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    species: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships let you navigate Animal -> related rows in Python.
    videos: Mapped[list[Video]] = relationship(back_populates="animal")
    observations: Mapped[list[Observation]] = relationship(back_populates="animal")
    daily_journals: Mapped[list[DailyJournal]] = relationship(back_populates="animal")
    camera_sources: Mapped[list[CameraSource]] = relationship(back_populates="animal")
