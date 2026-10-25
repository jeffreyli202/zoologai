"""
Behavioral analytics over real Observation / Frame rows.

Aggregation rules (important):
- Counts are of *recorded samples* (sparse frame analyses), never continuous time.
- Never convert sample counts into "% of the animal's day".
- A day/hour with zero observations means *no samples*, not proven inactivity.
- Missing frame analyses (frames without Observation) are reported as missing data.
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone

from google.genai import types
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Animal, Frame, Observation, Video
from app.schemas.analytics import (
    AggregationMeta,
    BehaviorAnalyticsResponse,
    BehaviorCount,
    CoverageStats,
    DayBehaviorSnapshot,
    DayCompareResponse,
    DayCount,
    HourCount,
    TimelinePoint,
    WeeklySummaryResponse,
)
from app.services.gemini_client import (
    GeminiAPIError,
    GeminiConfigError,
    get_gemini_client,
    get_gemini_model,
    raise_from_gemini_error,
)

AGGREGATION_EXPLANATION = (
    "Counts are tallies of saved Observation rows (one per analyzed frame), "
    "grouped by UTC calendar day or UTC hour of observed_at. "
    "These are sparse samples from uploaded video — not continuous monitoring. "
    "Do not read a count as the share of an animal's entire day. "
    "Days or hours with zero observations mean no samples were recorded "
    "(unknown activity), not that the animal was inactive."
)

COMPARE_EXPLANATION = (
    "Each day shows how many recorded observation samples fell on that UTC date, "
    "split by behavior label. Sample sizes may differ; unequal totals do not imply "
    "more or less activity in real life — only more or fewer analyzed frames."
)


def _day_bounds(day: date) -> tuple[datetime, datetime]:
    start = datetime(day.year, day.month, day.day, tzinfo=timezone.utc)
    end = datetime(
        day.year, day.month, day.day, 23, 59, 59, 999999, tzinfo=timezone.utc
    )
    return start, end


def _range_bounds(start_date: date, end_date: date) -> tuple[datetime, datetime]:
    start, _ = _day_bounds(start_date)
    _, end = _day_bounds(end_date)
    return start, end


def _ensure_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _behavior_counts(counter: Counter[str]) -> list[BehaviorCount]:
    return [
        BehaviorCount(behavior=behavior, count=count)
        for behavior, count in sorted(counter.items(), key=lambda x: (-x[1], x[0]))
    ]


def _load_observations(
    db: Session,
    *,
    animal_id: int | None,
    start_date: date,
    end_date: date,
) -> list[Observation]:
    start, end = _range_bounds(start_date, end_date)
    stmt = (
        select(Observation)
        .where(Observation.observed_at >= start, Observation.observed_at <= end)
        .order_by(Observation.observed_at.asc(), Observation.id.asc())
    )
    if animal_id is not None:
        stmt = stmt.where(Observation.animal_id == animal_id)
    return list(db.scalars(stmt).all())


def _frames_in_range(
    db: Session,
    *,
    animal_id: int | None,
    start_date: date,
    end_date: date,
) -> list[Frame]:
    """Frames whose parent video belongs to the animal and created_at is in range."""
    start, end = _range_bounds(start_date, end_date)
    stmt = (
        select(Frame)
        .join(Video, Frame.video_id == Video.id)
        .where(Frame.created_at >= start, Frame.created_at <= end)
    )
    if animal_id is not None:
        stmt = stmt.where(Video.animal_id == animal_id)
    return list(db.scalars(stmt).all())


def build_behavior_analytics(
    db: Session,
    *,
    animal_id: int | None,
    start_date: date,
    end_date: date,
) -> BehaviorAnalyticsResponse:
    if end_date < start_date:
        raise ValueError("end_date must be on or after start_date.")

    animal_name: str | None = None
    if animal_id is not None:
        animal = db.get(Animal, animal_id)
        if animal is None:
            raise LookupError(f"Animal with id {animal_id} was not found.")
        animal_name = animal.name

    observations = _load_observations(
        db, animal_id=animal_id, start_date=start_date, end_date=end_date
    )
    frames = _frames_in_range(
        db, animal_id=animal_id, start_date=start_date, end_date=end_date
    )

    # Missing analysis = extracted frames in the window with no Observation row.
    observed_frame_ids = {
        row
        for row in db.scalars(select(Observation.frame_id)).all()
    }
    missing_analyses = sum(1 for frame in frames if frame.id not in observed_frame_ids)
    frames_in_range = len(frames)

    by_behavior = _behavior_counts(Counter(obs.behavior for obs in observations))

    # --- by day ---
    day_counters: dict[date, Counter[str]] = defaultdict(Counter)
    for obs in observations:
        day = _ensure_utc(obs.observed_at).date()
        day_counters[day][obs.behavior] += 1

    by_day: list[DayCount] = []
    cursor = start_date
    while cursor <= end_date:
        counter = day_counters.get(cursor, Counter())
        by_day.append(
            DayCount(
                date=cursor,
                count=sum(counter.values()),
                by_behavior=_behavior_counts(counter),
            )
        )
        cursor += timedelta(days=1)

    # --- by hour (UTC) across the whole range ---
    hour_counters: dict[int, Counter[str]] = defaultdict(Counter)
    for obs in observations:
        hour = _ensure_utc(obs.observed_at).hour
        hour_counters[hour][obs.behavior] += 1

    by_hour = [
        HourCount(
            hour=hour,
            count=sum(hour_counters[hour].values()) if hour in hour_counters else 0,
            by_behavior=_behavior_counts(hour_counters.get(hour, Counter())),
        )
        for hour in range(24)
    ]

    timeline = [
        TimelinePoint(
            observation_id=obs.id,
            observed_at=_ensure_utc(obs.observed_at),
            behavior=obs.behavior,
            confidence=obs.confidence,
            video_timestamp_seconds=obs.video_timestamp_seconds,
            description=obs.description,
            visible_evidence=obs.visible_evidence,
            video_id=obs.video_id,
            frame_id=obs.frame_id,
        )
        for obs in observations
    ]

    days_in_range = (end_date - start_date).days + 1
    days_with_samples = sum(1 for d in by_day if d.count > 0)
    days_with_no_samples = days_in_range - days_with_samples

    # Hours with samples: among days that had at least one sample, how many of the
    # 24 UTC hours ever received a sample in the whole range (not "inactive hours").
    hours_with_samples = sum(1 for h in by_hour if h.count > 0)
    hours_with_no_samples = 24 - hours_with_samples

    coverage = CoverageStats(
        frames_in_range=frames_in_range,
        observations_in_range=len(observations),
        missing_frame_analyses=missing_analyses,
        days_in_range=days_in_range,
        days_with_samples=days_with_samples,
        days_with_no_samples=days_with_no_samples,
        hours_with_samples=hours_with_samples,
        hours_with_no_samples_among_sampled_days=hours_with_no_samples,
        note=(
            "Coverage describes sampled frames and calendar slots with recorded "
            "observations only. Days/hours with no samples are missing data — "
            "not evidence the animal was resting or inactive. "
            "Never treat sample counts as a percentage of a full day."
        ),
    )

    return BehaviorAnalyticsResponse(
        meta=AggregationMeta(
            animal_id=animal_id,
            animal_name=animal_name,
            start_date=start_date,
            end_date=end_date,
            total_observations=len(observations),
            explanation=AGGREGATION_EXPLANATION,
        ),
        by_behavior=by_behavior,
        by_day=by_day,
        by_hour=by_hour,
        timeline=timeline,
        coverage=coverage,
    )


def build_day_compare(
    db: Session,
    *,
    animal_id: int,
    day_a: date,
    day_b: date,
) -> DayCompareResponse:
    animal = db.get(Animal, animal_id)
    if animal is None:
        raise LookupError(f"Animal with id {animal_id} was not found.")

    def snapshot(day: date) -> DayBehaviorSnapshot:
        rows = _load_observations(db, animal_id=animal_id, start_date=day, end_date=day)
        counter = Counter(obs.behavior for obs in rows)
        return DayBehaviorSnapshot(
            date=day,
            total_observations=len(rows),
            by_behavior=_behavior_counts(counter),
            note=(
                f"{len(rows)} recorded sample(s) on {day.isoformat()} (UTC). "
                "Zero samples means missing data, not proven inactivity."
            ),
        )

    return DayCompareResponse(
        animal_id=animal.id,
        animal_name=animal.name,
        day_a=snapshot(day_a),
        day_b=snapshot(day_b),
        explanation=COMPARE_EXPLANATION,
    )


class WeeklySummaryDraft(BaseModel):
    summary: str = Field(..., min_length=1, max_length=6000)

    @field_validator("summary")
    @classmethod
    def strip_summary(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Summary must not be empty.")
        return cleaned


WEEKLY_INSTRUCTIONS = """
You write a cautious weekly behavioral summary for ZooLog AI keepers.

Rules:
1. Use ONLY the observation records and aggregate counts provided.
2. Never invent behaviors, times, or events.
3. Never describe sample counts as a percentage of an animal's entire day.
4. Days or hours with no samples mean missing data — not inactivity.
5. Separate clear recorded patterns from tentative interpretations.
6. Keep the tone engaging but scientifically cautious.
7. Mention that data comes from sparse video frame samples.
""".strip()


def generate_weekly_summary(
    db: Session,
    *,
    animal_id: int,
    week_start: date,
) -> WeeklySummaryResponse:
    animal = db.get(Animal, animal_id)
    if animal is None:
        raise LookupError(f"Animal with id {animal_id} was not found.")

    week_end = week_start + timedelta(days=6)
    analytics = build_behavior_analytics(
        db,
        animal_id=animal_id,
        start_date=week_start,
        end_date=week_end,
    )

    if analytics.meta.total_observations == 0:
        raise ValueError(
            f"No observations for {animal.name} between "
            f"{week_start.isoformat()} and {week_end.isoformat()}. "
            "Nothing was invented."
        )

    source_ids = [point.observation_id for point in analytics.timeline]

    payload = {
        "animal_name": animal.name,
        "species": animal.species,
        "week_start": week_start.isoformat(),
        "week_end": week_end.isoformat(),
        "total_observations": analytics.meta.total_observations,
        "by_behavior": [c.model_dump() for c in analytics.by_behavior],
        "by_day": [
            {
                "date": d.date.isoformat(),
                "count": d.count,
                "by_behavior": [b.model_dump() for b in d.by_behavior],
            }
            for d in analytics.by_day
        ],
        "coverage": analytics.coverage.model_dump(),
        "aggregation_note": analytics.meta.explanation,
        "observations": [
            {
                "id": p.observation_id,
                "observed_at": p.observed_at.isoformat(),
                "behavior": p.behavior,
                "confidence": p.confidence,
                "description": p.description,
                "visible_evidence": p.visible_evidence,
            }
            for p in analytics.timeline
        ],
    }

    try:
        client = get_gemini_client()
    except GeminiConfigError:
        raise

    prompt = (
        "Write a weekly behavioral summary using only this recorded data. "
        "Do not treat missing days as inactivity.\n\n"
        f"{json.dumps(payload, ensure_ascii=True, indent=2)}"
    )

    try:
        response = client.models.generate_content(
            model=get_gemini_model(),
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=WEEKLY_INSTRUCTIONS,
                response_mime_type="application/json",
                response_json_schema=WeeklySummaryDraft.model_json_schema(),
            ),
        )
    except Exception as exc:
        raise_from_gemini_error(exc)

    raw = (response.text or "").strip()
    if not raw:
        raise GeminiAPIError("Gemini returned empty weekly summary.")

    try:
        draft = WeeklySummaryDraft.model_validate(json.loads(raw))
    except Exception as exc:
        raise GeminiAPIError(
            f"Weekly summary failed validation: {exc}. Nothing was saved."
        ) from exc

    return WeeklySummaryResponse(
        animal_id=animal.id,
        animal_name=animal.name,
        week_start=week_start,
        week_end=week_end,
        observation_count=analytics.meta.total_observations,
        source_observation_ids=source_ids,
        summary=draft.summary,
        detail="Weekly summary generated from recorded observations only.",
    )
