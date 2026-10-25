"""Frame vision-analysis endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import Frame, Observation, Video
from app.schemas.observation import AnalyzeFrameResponse, ObservationRead
from app.services.frames import FrameExtractionError, resolve_frame_path
from app.services.vision import VisionAPIError, VisionConfigError, analyze_frame_image

router = APIRouter(prefix="/frames", tags=["frames"])


def _to_observation_read(obs: Observation) -> ObservationRead:
    return ObservationRead.model_validate(obs)


@router.post(
    "/{frame_id}/analyze",
    response_model=AnalyzeFrameResponse,
    summary="Analyze one frame with a vision model (idempotent per frame)",
)
def analyze_frame(frame_id: int, db: Session = Depends(get_db)) -> AnalyzeFrameResponse:
    """
    Send a single extracted frame to Gemini vision and save an Observation.

    If this frame already has an observation, return it without calling the API
    again (cost-safe + idempotent).
    """
    frame = db.scalars(
        select(Frame)
        .where(Frame.id == frame_id)
        .options(joinedload(Frame.video).joinedload(Video.animal))
    ).unique().first()

    if frame is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Frame with id {frame_id} was not found.",
        )

    existing = db.scalar(
        select(Observation).where(Observation.frame_id == frame_id)
    )
    if existing is not None:
        return AnalyzeFrameResponse(
            reused=True,
            detail="Observation already exists for this frame. Returning saved result.",
            observation=_to_observation_read(existing),
        )

    video = frame.video
    if video is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Frame is not linked to a video.",
        )

    try:
        image_path = resolve_frame_path(frame.video_id, frame.filename)
    except FrameExtractionError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    try:
        result = analyze_frame_image(image_path)
    except VisionConfigError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except VisionAPIError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc

    observation = Observation(
        animal_id=video.animal_id,
        video_id=video.id,
        frame_id=frame.id,
        video_timestamp_seconds=frame.timestamp_seconds,
        behavior=result.behavior.value,
        description=result.description,
        visible_evidence=result.visible_evidence,
        confidence=result.confidence,
    )
    db.add(observation)
    db.commit()
    db.refresh(observation)

    return AnalyzeFrameResponse(
        reused=False,
        detail="Frame analyzed and observation saved.",
        observation=_to_observation_read(observation),
    )


@router.get(
    "/{frame_id}/observation",
    response_model=ObservationRead,
    summary="Get the saved observation for a frame (if any)",
)
def get_frame_observation(frame_id: int, db: Session = Depends(get_db)) -> ObservationRead:
    frame = db.get(Frame, frame_id)
    if frame is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Frame with id {frame_id} was not found.",
        )

    observation = db.scalar(
        select(Observation).where(Observation.frame_id == frame_id)
    )
    if observation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No observation has been saved for this frame yet.",
        )
    return _to_observation_read(observation)
