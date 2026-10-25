"""
Hourly (and optional full-day) journals from saved observations (Gemini).

The database is the agent's persistent memory: Observation rows are the facts;
DailyJournal rows are the saved summaries. Generation always reloads facts from
SQLite for the selected animal and period — it does not invent a journal when
that period has no observations.
"""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import Animal, DailyJournal, Observation
from app.schemas.journal import (
    DailyJournalRead,
    JournalEligibilityResponse,
    JournalGenerateRequest,
    JournalGenerateResponse,
)
from app.services.gemini_client import GeminiAPIError, GeminiConfigError
from app.services.journals import filter_sightings_for_journal, generate_daily_journal

router = APIRouter(prefix="/journals", tags=["journals"])

# Stored hour for full-day / legacy journals (unique with animal_id + date).
FULL_DAY_HOUR = -1


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_source_ids(raw: str | None) -> list[int]:
    if not raw:
        return []
    try:
        data = json.loads(raw)
        if isinstance(data, list):
            return [int(x) for x in data]
    except (json.JSONDecodeError, TypeError, ValueError):
        pass
    return []


def _to_journal_read(
    journal: DailyJournal, animal_name: str | None = None
) -> DailyJournalRead:
    return DailyJournalRead(
        id=journal.id,
        animal_id=journal.animal_id,
        animal_name=animal_name
        or (journal.animal.name if getattr(journal, "animal", None) else None),
        date=journal.date,
        hour=getattr(journal, "hour", FULL_DAY_HOUR),
        content=journal.content,
        source_observation_ids=_parse_source_ids(journal.source_observation_ids),
        created_at=journal.created_at,
        updated_at=journal.updated_at,
    )


def _period_bounds(
    journal_date: date, hour: int | None
) -> tuple[datetime, datetime]:
    if hour is not None and 0 <= hour <= 23:
        start = datetime(
            journal_date.year,
            journal_date.month,
            journal_date.day,
            hour,
            tzinfo=timezone.utc,
        )
        end = start + timedelta(hours=1) - timedelta(microseconds=1)
        return start, end
    start = datetime(
        journal_date.year,
        journal_date.month,
        journal_date.day,
        tzinfo=timezone.utc,
    )
    end = datetime(
        journal_date.year,
        journal_date.month,
        journal_date.day,
        23,
        59,
        59,
        999999,
        tzinfo=timezone.utc,
    )
    return start, end


def _observations_for_period(
    db: Session, animal_id: int, journal_date: date, hour: int | None
) -> list[Observation]:
    start, end = _period_bounds(journal_date, hour)
    return list(
        db.scalars(
            select(Observation)
            .where(
                Observation.animal_id == animal_id,
                Observation.observed_at >= start,
                Observation.observed_at <= end,
            )
            .order_by(Observation.observed_at.asc(), Observation.id.asc())
        ).all()
    )


def _observation_payload(observations: list[Observation]) -> list[dict]:
    return [
        {
            "id": obs.id,
            "behavior": obs.behavior,
            "description": obs.description,
            "visible_evidence": obs.visible_evidence,
            "confidence": obs.confidence,
            "video_timestamp_seconds": obs.video_timestamp_seconds,
            "observed_at": obs.observed_at.isoformat() if obs.observed_at else None,
        }
        for obs in observations
    ]


def _storage_hour(hour: int | None) -> int:
    if hour is not None and 0 <= hour <= 23:
        return hour
    return FULL_DAY_HOUR


def _period_label(journal_date: date, hour: int | None) -> str:
    if hour is not None and 0 <= hour <= 23:
        return f"{journal_date.isoformat()} {hour:02d}:00–{hour:02d}:59 UTC"
    return f"{journal_date.isoformat()} (full day UTC)"


@router.get(
    "",
    response_model=list[DailyJournalRead],
    summary="List past journals",
)
def list_journals(
    animal_id: int | None = Query(default=None),
    journal_date: date | None = Query(
        default=None,
        description="Optional UTC calendar date filter (YYYY-MM-DD).",
    ),
    hour: int | None = Query(
        default=None,
        ge=-1,
        le=23,
        description="Optional UTC hour filter (0–23, or -1 for full-day).",
    ),
    db: Session = Depends(get_db),
) -> list[DailyJournalRead]:
    stmt = (
        select(DailyJournal)
        .options(joinedload(DailyJournal.animal))
        .order_by(
            DailyJournal.date.desc(),
            DailyJournal.hour.desc(),
            DailyJournal.id.desc(),
        )
    )
    if animal_id is not None:
        stmt = stmt.where(DailyJournal.animal_id == animal_id)
    if journal_date is not None:
        stmt = stmt.where(DailyJournal.date == journal_date)
    if hour is not None:
        stmt = stmt.where(DailyJournal.hour == hour)
    journals = db.scalars(stmt).unique().all()
    return [_to_journal_read(j) for j in journals]


@router.get(
    "/eligibility",
    response_model=JournalEligibilityResponse,
    summary="Check whether a period has observations (for empty-state UI)",
)
def journal_eligibility(
    animal_id: int = Query(..., ge=1),
    journal_date: date | None = Query(default=None),
    hour: int | None = Query(
        default=None,
        ge=0,
        le=23,
        description="UTC hour 0–23. Omit for a full-day check.",
    ),
    db: Session = Depends(get_db),
) -> JournalEligibilityResponse:
    animal = db.get(Animal, animal_id)
    if animal is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Animal with id {animal_id} was not found.",
        )

    day = journal_date or datetime.now(timezone.utc).date()
    observations = _observations_for_period(db, animal.id, day, hour)
    sightings = filter_sightings_for_journal(
        observations,
        animal_name=animal.name,
        animal_species=animal.species,
    )
    stored_hour = _storage_hour(hour)
    existing = db.scalar(
        select(DailyJournal).where(
            DailyJournal.animal_id == animal.id,
            DailyJournal.date == day,
            DailyJournal.hour == stored_hour,
        )
    )

    label = _period_label(day, hour)
    count = len(sightings)
    skipped = len(observations) - count
    if count == 0:
        if skipped:
            detail = (
                f"{animal.name} was not observed in {label} "
                f"({skipped} empty/not_visible frame(s)). No journal will be created."
            )
        else:
            detail = (
                f"No saved observations for {animal.name} in {label}. "
                "Capture or analyze frames for that period before generating a journal."
            )
    else:
        detail = (
            f"{count} sighting(s) available for {animal.name} in {label}."
            + (f" ({skipped} not_visible frame(s) ignored.)" if skipped else "")
        )

    return JournalEligibilityResponse(
        animal_id=animal.id,
        journal_date=day,
        hour=hour,
        observation_count=count,
        observation_ids=[o.id for o in sightings],
        has_journal=existing is not None,
        journal_id=existing.id if existing else None,
        detail=detail,
    )


@router.post(
    "/generate",
    response_model=JournalGenerateResponse,
    summary="Generate or regenerate a journal from observations",
)
def generate_journal(
    payload: JournalGenerateRequest,
    db: Session = Depends(get_db),
) -> JournalGenerateResponse:
    animal = db.get(Animal, payload.animal_id)
    if animal is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Animal with id {payload.animal_id} was not found.",
        )

    journal_date = payload.journal_date or datetime.now(timezone.utc).date()
    hour = payload.hour
    stored_hour = _storage_hour(hour)
    label = _period_label(journal_date, hour)

    existing = db.scalar(
        select(DailyJournal).where(
            DailyJournal.animal_id == animal.id,
            DailyJournal.date == journal_date,
            DailyJournal.hour == stored_hour,
        )
    )
    if existing is not None and not payload.force:
        existing.animal = animal
        return JournalGenerateResponse(
            reused=True,
            regenerated=False,
            detail=(
                f"Journal already exists for {label}. "
                "Pass force=true to regenerate from current observations."
            ),
            journal=_to_journal_read(existing, animal.name),
            observation_count=len(_parse_source_ids(existing.source_observation_ids)),
        )

    observations = _observations_for_period(db, animal.id, journal_date, hour)
    sightings = filter_sightings_for_journal(
        observations,
        animal_name=animal.name,
        animal_species=animal.species,
    )
    if not sightings:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                f"{animal.name} was not observed in {label}"
                + (
                    f" ({len(observations)} not_visible/empty frame(s))"
                    if observations
                    else ""
                )
                + ". No journal created."
            ),
        )

    try:
        content, source_ids = generate_daily_journal(
            animal_name=animal.name,
            animal_species=animal.species,
            journal_date=journal_date,
            observations=_observation_payload(sightings),
            hour=hour,
        )
    except GeminiConfigError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except GeminiAPIError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc

    ids_json = json.dumps(source_ids)
    kind = "Hourly" if hour is not None else "Daily"

    if existing is not None:
        existing.content = content
        existing.source_observation_ids = ids_json
        existing.hour = stored_hour
        existing.updated_at = _utc_now()
        db.add(existing)
        db.commit()
        db.refresh(existing)
        return JournalGenerateResponse(
            reused=False,
            regenerated=True,
            detail=f"{kind} journal regenerated from current observations and saved.",
            journal=_to_journal_read(existing, animal.name),
            observation_count=len(sightings),
        )

    journal = DailyJournal(
        animal_id=animal.id,
        date=journal_date,
        hour=stored_hour,
        content=content,
        source_observation_ids=ids_json,
        updated_at=_utc_now(),
    )
    db.add(journal)
    db.commit()
    db.refresh(journal)

    return JournalGenerateResponse(
        reused=False,
        regenerated=False,
        detail=f"{kind} journal generated and saved.",
        journal=_to_journal_read(journal, animal.name),
        observation_count=len(sightings),
    )
