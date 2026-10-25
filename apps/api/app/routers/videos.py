"""
Video upload, list, and frame-extraction endpoints.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.config import get_settings
from app.database import get_db
from app.models import Animal, Frame, Video
from app.schemas import ExtractFramesResponse, FrameRead, VideoRead, VideoUploadResponse
from app.schemas.video import VideoAnalysisStatus
from app.services.frames import (
    FrameExtractionError,
    extract_frames_for_video,
    get_frame_root,
    video_frame_dir,
)
from app.services.storage import UploadValidationError, save_video_upload
from app.services.video_analysis import start_video_analysis_job

router = APIRouter(prefix="/videos", tags=["videos"])


def _to_video_read(video: Video) -> VideoRead:
    return VideoRead(
        id=video.id,
        animal_id=video.animal_id,
        animal_name=video.animal.name if video.animal else None,
        filename=video.filename,
        original_filename=video.original_filename,
        size_bytes=video.size_bytes,
        status=video.status,
        uploaded_at=video.uploaded_at,
        analysis_progress=getattr(video, "analysis_progress", 0) or 0,
        analysis_message=getattr(video, "analysis_message", None),
        analysis_error=getattr(video, "analysis_error", None),
        analysis_frames_total=getattr(video, "analysis_frames_total", 0) or 0,
        analysis_frames_done=getattr(video, "analysis_frames_done", 0) or 0,
        analysis_ai_calls=getattr(video, "analysis_ai_calls", 0) or 0,
        analysis_started_at=getattr(video, "analysis_started_at", None),
        analysis_finished_at=getattr(video, "analysis_finished_at", None),
    )


def _to_analysis_status(video: Video, detail: str = "") -> VideoAnalysisStatus:
    settings = get_settings()
    return VideoAnalysisStatus(
        video_id=video.id,
        status=video.status,
        progress=video.analysis_progress or 0,
        message=video.analysis_message,
        error=video.analysis_error,
        frames_total=video.analysis_frames_total or 0,
        frames_done=video.analysis_frames_done or 0,
        ai_calls=video.analysis_ai_calls or 0,
        max_ai_calls=settings.max_ai_calls_per_video_job,
        started_at=video.analysis_started_at,
        finished_at=video.analysis_finished_at,
        detail=detail,
    )


def _to_frame_read(frame: Frame) -> FrameRead:
    return FrameRead(
        id=frame.id,
        video_id=frame.video_id,
        filename=frame.filename,
        timestamp_seconds=frame.timestamp_seconds,
        frame_index=frame.frame_index,
        created_at=frame.created_at,
        image_url=f"/videos/{frame.video_id}/frames/{frame.id}/image",
    )


def _list_frames_for_video(db: Session, video_id: int) -> list[Frame]:
    return list(
        db.scalars(
            select(Frame)
            .where(Frame.video_id == video_id)
            .order_by(Frame.frame_index.asc())
        ).all()
    )


@router.post(
    "/upload",
    response_model=VideoUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a video for an animal",
)
async def upload_video(
    animal_id: int = Form(..., description="ID of the animal this video belongs to"),
    file: UploadFile = File(..., description="MP4, MOV, or WebM video (max 100 MB)"),
    db: Session = Depends(get_db),
) -> VideoUploadResponse:
    animal = db.get(Animal, animal_id)
    if animal is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Animal with id {animal_id} was not found.",
        )

    try:
        stored_filename, original_basename, size_bytes = await save_video_upload(file)
    except UploadValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    finally:
        await file.close()

    video = Video(
        animal_id=animal.id,
        filename=stored_filename,
        original_filename=original_basename,
        size_bytes=size_bytes,
        status="uploaded",
    )
    db.add(video)
    db.commit()
    db.refresh(video)
    video.animal = animal

    payload = _to_video_read(video)
    return VideoUploadResponse(**payload.model_dump(), detail="Video uploaded successfully.")


@router.get(
    "",
    response_model=list[VideoRead],
    summary="List uploaded videos",
)
def list_videos(db: Session = Depends(get_db)) -> list[VideoRead]:
    videos = db.scalars(
        select(Video)
        .options(joinedload(Video.animal))
        .order_by(Video.uploaded_at.desc())
    ).unique().all()
    return [_to_video_read(video) for video in videos]


@router.post(
    "/{video_id}/analyze",
    response_model=VideoAnalysisStatus,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Start full video analysis job (extract + AI) in the background",
)
def analyze_video(
    video_id: int,
    force: bool = Query(
        default=False,
        description="If true, restart analysis even when status is completed.",
    ),
    db: Session = Depends(get_db),
) -> VideoAnalysisStatus:
    """
    Kick off extract-frames + per-frame vision analysis without blocking HTTP.

    Duplicate protection: while status is pending/processing, returns 409.
    Retry: call again after failed (or with force=true after completed).
    """
    video = db.get(Video, video_id)
    if video is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Video with id {video_id} was not found.",
        )

    if video.status in {"pending", "processing"}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Analysis is already running for this video. Poll GET /videos/{id}/analysis.",
        )

    if video.status == "completed" and not force:
        return _to_analysis_status(
            video,
            detail="Analysis already completed. Pass force=true to run again.",
        )

    video.status = "pending"
    video.analysis_progress = 0
    video.analysis_message = "Queued for analysis…"
    video.analysis_error = None
    video.analysis_frames_done = 0
    video.analysis_ai_calls = 0
    video.analysis_finished_at = None
    db.add(video)
    db.commit()
    db.refresh(video)

    start_video_analysis_job(video.id)

    return _to_analysis_status(
        video,
        detail="Analysis job accepted. Poll GET /videos/{id}/analysis for progress.",
    )


@router.get(
    "/{video_id}/analysis",
    response_model=VideoAnalysisStatus,
    summary="Poll video analysis progress",
)
def get_video_analysis(video_id: int, db: Session = Depends(get_db)) -> VideoAnalysisStatus:
    video = db.get(Video, video_id)
    if video is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Video with id {video_id} was not found.",
        )
    return _to_analysis_status(video, detail="Current analysis status.")


@router.post(
    "/{video_id}/extract-frames",
    response_model=ExtractFramesResponse,
    summary="Extract sampled frames from a video (idempotent)",
)
def extract_frames(video_id: int, db: Session = Depends(get_db)) -> ExtractFramesResponse:
    """
    Sample one frame every 15 seconds (max 12).

    Idempotent: if frames already exist for this video, return them and do not
    write duplicates.
    """
    video = db.get(Video, video_id)
    if video is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Video with id {video_id} was not found.",
        )

    existing = _list_frames_for_video(db, video_id)
    if existing:
        return ExtractFramesResponse(
            video_id=video_id,
            reused=True,
            detail=f"Frames already extracted ({len(existing)}). Returning existing rows.",
            frames=[_to_frame_read(frame) for frame in existing],
        )

    try:
        extracted = extract_frames_for_video(video_id, video.filename)
    except FrameExtractionError as exc:
        video.status = "extraction_failed"
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except Exception as exc:  # pragma: no cover - unexpected OpenCV/OS errors
        video.status = "extraction_failed"
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Frame extraction failed unexpectedly: {exc}",
        ) from exc

    try:
        for item in extracted:
            db.add(
                Frame(
                    video_id=video.id,
                    filename=item.filename,
                    timestamp_seconds=item.timestamp_seconds,
                    frame_index=item.frame_index,
                )
            )
        video.status = "frames_extracted"
        db.commit()
    except Exception:
        db.rollback()
        # Best-effort cleanup of files written for this failed insert.
        frame_dir = video_frame_dir(video_id)
        for item in extracted:
            path = frame_dir / item.filename
            if path.exists():
                path.unlink(missing_ok=True)
        failed = db.get(Video, video_id)
        if failed is not None:
            failed.status = "extraction_failed"
            db.commit()
        raise

    frames = _list_frames_for_video(db, video_id)
    return ExtractFramesResponse(
        video_id=video_id,
        reused=False,
        detail=f"Extracted {len(frames)} frame(s).",
        frames=[_to_frame_read(frame) for frame in frames],
    )


@router.get(
    "/{video_id}/frames",
    response_model=list[FrameRead],
    summary="List extracted frames for a video",
)
def list_video_frames(video_id: int, db: Session = Depends(get_db)) -> list[FrameRead]:
    video = db.get(Video, video_id)
    if video is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Video with id {video_id} was not found.",
        )
    return [_to_frame_read(frame) for frame in _list_frames_for_video(db, video_id)]


@router.get(
    "/{video_id}/frames/{frame_id}/image",
    summary="Serve one extracted frame JPEG",
    responses={200: {"content": {"image/jpeg": {}}}},
)
def get_frame_image(
    video_id: int,
    frame_id: int,
    db: Session = Depends(get_db),
) -> FileResponse:
    frame = db.get(Frame, frame_id)
    if frame is None or frame.video_id != video_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Frame was not found for this video.",
        )

    path = (video_frame_dir(video_id) / frame.filename).resolve()
    frame_root = get_frame_root()
    if not str(path).startswith(str(frame_root)) or not path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Frame image file is missing on disk.",
        )

    return FileResponse(path, media_type="image/jpeg", filename=frame.filename)
