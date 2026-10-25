from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field


class BehaviorCount(BaseModel):
    behavior: str
    count: int


class DayCount(BaseModel):
    date: date
    count: int
    by_behavior: list[BehaviorCount] = Field(default_factory=list)


class HourCount(BaseModel):
    hour: int = Field(..., ge=0, le=23, description="UTC hour 0–23")
    count: int
    by_behavior: list[BehaviorCount] = Field(default_factory=list)


class TimelinePoint(BaseModel):
    observation_id: int
    observed_at: datetime
    behavior: str
    confidence: Optional[float] = None
    video_timestamp_seconds: float
    description: Optional[str] = None
    visible_evidence: Optional[str] = None
    # Null when the observation came from a live camera capture (not a video frame).
    video_id: Optional[int] = None
    frame_id: Optional[int] = None
    camera_source_id: Optional[int] = None
    camera_capture_id: Optional[int] = None


class CoverageStats(BaseModel):
    """
    Coverage of *sampled* data only — never a claim about the animal's full day.

    missing_frame_analyses: extracted frames in range with no Observation row.
    days_with_no_samples / hours_with_no_samples: calendar slots with zero
    observation rows (unknown activity, not proven inactivity).
    """

    frames_in_range: int
    observations_in_range: int
    missing_frame_analyses: int
    days_in_range: int
    days_with_samples: int
    days_with_no_samples: int
    hours_with_samples: int
    hours_with_no_samples_among_sampled_days: int
    note: str


class AggregationMeta(BaseModel):
    animal_id: Optional[int] = None
    animal_name: Optional[str] = None
    start_date: date
    end_date: date
    total_observations: int
    explanation: str


class BehaviorAnalyticsResponse(BaseModel):
    meta: AggregationMeta
    by_behavior: list[BehaviorCount]
    by_day: list[DayCount]
    by_hour: list[HourCount]
    timeline: list[TimelinePoint]
    coverage: CoverageStats


class DayBehaviorSnapshot(BaseModel):
    date: date
    total_observations: int
    by_behavior: list[BehaviorCount]
    note: str


class DayCompareResponse(BaseModel):
    animal_id: int
    animal_name: Optional[str] = None
    day_a: DayBehaviorSnapshot
    day_b: DayBehaviorSnapshot
    explanation: str


class WeeklySummaryRequest(BaseModel):
    animal_id: int = Field(..., ge=1)
    # Inclusive start of the 7-day window (UTC calendar dates).
    week_start: date


class WeeklySummaryResponse(BaseModel):
    animal_id: int
    animal_name: Optional[str] = None
    week_start: date
    week_end: date
    observation_count: int
    source_observation_ids: list[int] = Field(default_factory=list)
    summary: str
    detail: str
