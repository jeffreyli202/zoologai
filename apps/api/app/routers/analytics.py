"""Behavioral analytics endpoints over real Observation rows."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.analytics import (
    BehaviorAnalyticsResponse,
    DayCompareResponse,
    WeeklySummaryRequest,
    WeeklySummaryResponse,
)
from app.services.analytics import (
    build_behavior_analytics,
    build_day_compare,
    generate_weekly_summary,
)
from app.services.gemini_client import GeminiAPIError, GeminiConfigError

router = APIRouter(prefix="/analytics", tags=["analytics"])


def _default_range() -> tuple[date, date]:
    end = datetime.now(timezone.utc).date()
    start = end - timedelta(days=6)
    return start, end


@router.get(
    "/behaviors",
    response_model=BehaviorAnalyticsResponse,
    summary="Observation counts by behavior, day, hour + timeline + coverage",
)
def get_behavior_analytics(
    animal_id: int | None = Query(default=None, ge=1),
    start_date: date | None = Query(
        default=None, description="UTC start date (inclusive)."
    ),
    end_date: date | None = Query(
        default=None, description="UTC end date (inclusive)."
    ),
    db: Session = Depends(get_db),
) -> BehaviorAnalyticsResponse:
    default_start, default_end = _default_range()
    start = start_date or default_start
    end = end_date or default_end

    try:
        return build_behavior_analytics(
            db, animal_id=animal_id, start_date=start, end_date=end
        )
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc


@router.get(
    "/compare-days",
    response_model=DayCompareResponse,
    summary="Compare recorded behavior sample counts between two UTC days",
)
def compare_days(
    animal_id: int = Query(..., ge=1),
    day_a: date = Query(..., description="First UTC calendar day"),
    day_b: date = Query(..., description="Second UTC calendar day"),
    db: Session = Depends(get_db),
) -> DayCompareResponse:
    try:
        return build_day_compare(db, animal_id=animal_id, day_a=day_a, day_b=day_b)
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc


@router.post(
    "/weekly-summary",
    response_model=WeeklySummaryResponse,
    summary="AI weekly summary from recorded observations only",
)
def weekly_summary(
    payload: WeeklySummaryRequest,
    db: Session = Depends(get_db),
) -> WeeklySummaryResponse:
    try:
        return generate_weekly_summary(
            db, animal_id=payload.animal_id, week_start=payload.week_start
        )
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except GeminiConfigError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc
    except GeminiAPIError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)
        ) from exc
