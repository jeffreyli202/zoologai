"""List saved observation rows (video frames + camera captures)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import Observation
from app.schemas.observation import ObservationRead

router = APIRouter(prefix="/observations", tags=["observations"])


class ObservationStats(BaseModel):
    total: int
    distinct_behaviors: int


def _to_observation_read(obs: Observation) -> ObservationRead:
    animal_name = obs.animal.name if getattr(obs, "animal", None) else None
    return ObservationRead(
        id=obs.id,
        animal_id=obs.animal_id,
        animal_name=animal_name,
        video_id=obs.video_id,
        frame_id=obs.frame_id,
        camera_source_id=obs.camera_source_id,
        camera_capture_id=obs.camera_capture_id,
        observed_at=obs.observed_at,
        video_timestamp_seconds=obs.video_timestamp_seconds,
        behavior=obs.behavior,
        description=obs.description,
        visible_evidence=obs.visible_evidence,
        confidence=obs.confidence,
    )


@router.get(
    "/stats",
    response_model=ObservationStats,
    summary="Observation totals for dashboard cards",
)
def observation_stats(
    animal_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
) -> ObservationStats:
    count_stmt = select(func.count()).select_from(Observation)
    behavior_stmt = select(func.count(func.distinct(Observation.behavior)))
    if animal_id is not None:
        count_stmt = count_stmt.where(Observation.animal_id == animal_id)
        behavior_stmt = behavior_stmt.where(Observation.animal_id == animal_id)
    total = int(db.scalar(count_stmt) or 0)
    distinct = int(db.scalar(behavior_stmt) or 0)
    return ObservationStats(total=total, distinct_behaviors=distinct)


@router.get(
    "",
    response_model=list[ObservationRead],
    summary="List observations (newest first)",
)
def list_observations(
    animal_id: int | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> list[ObservationRead]:
    stmt = (
        select(Observation)
        .options(joinedload(Observation.animal))
        .order_by(Observation.observed_at.desc(), Observation.id.desc())
        .limit(limit)
    )
    if animal_id is not None:
        stmt = stmt.where(Observation.animal_id == animal_id)
    rows = db.scalars(stmt).unique().all()
    return [_to_observation_read(obs) for obs in rows]
