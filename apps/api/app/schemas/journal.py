from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class JournalGenerateRequest(BaseModel):
    animal_id: int = Field(..., ge=1)
    # Defaults to today (UTC calendar date) when omitted by the client.
    journal_date: Optional[date] = None
    # UTC hour 0–23 for an hourly journal. Omit or -1 for a full-day summary.
    hour: Optional[int] = Field(default=None, ge=-1, le=23)
    # When true, overwrite an existing journal for this animal/date/hour.
    force: bool = False

    @field_validator("hour")
    @classmethod
    def normalize_hour(cls, value: Optional[int]) -> Optional[int]:
        if value is None or value == -1:
            return None
        return value


class DailyJournalRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    animal_id: int
    animal_name: Optional[str] = None
    date: date
    # UTC hour 0–23, or -1 for a legacy / full-day journal.
    hour: int = -1
    content: str
    source_observation_ids: list[int] = Field(default_factory=list)
    created_at: datetime
    updated_at: Optional[datetime] = None


class JournalGenerateResponse(BaseModel):
    reused: bool = Field(
        description="True when an existing journal was returned without regenerating."
    )
    regenerated: bool = Field(
        default=False,
        description="True when an existing journal was overwritten with force=true.",
    )
    detail: str
    journal: DailyJournalRead
    observation_count: int = 0


class JournalEligibilityResponse(BaseModel):
    """Lets the UI show an empty state before calling the model."""

    animal_id: int
    journal_date: date
    hour: Optional[int] = None
    observation_count: int
    observation_ids: list[int] = Field(default_factory=list)
    has_journal: bool = False
    journal_id: Optional[int] = None
    detail: str
