"""Authorized camera source CRUD + monitoring start/stop/status."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from sqlalchemy import select, update
from sqlalchemy.orm import Session, joinedload

from app.config import get_settings
from app.database import get_db
from app.models import Animal, CameraSource, MonitoringLog, Observation
from app.schemas.camera import (
    CameraMonitorActionResponse,
    CameraMonitorStatus,
    CameraProbeRequest,
    CameraProbeResponse,
    CameraSourceCreate,
    CameraSourceRead,
    CameraSourceUpdate,
    ExtractedFrameRead,
    FrameExtractRequest,
    FrameExtractResponse,
    MonitoringLogRead,
)
from app.services.camera_monitor import start_camera_source, stop_camera_source
from app.services.frame_extract import extract_live_frames
from app.services.live_capture import LiveCaptureError, probe_live_url
from app.services.scheduler import is_scheduler_running

router = APIRouter(prefix="/cameras", tags=["cameras"])


def _extracted_root() -> Path:
    settings = get_settings()
    return Path(settings.camera_capture_dir).resolve().parent / "extracted_frames"


def _to_read(source: CameraSource) -> CameraSourceRead:
    return CameraSourceRead(
        id=source.id,
        animal_id=source.animal_id,
        animal_name=source.animal.name if source.animal else None,
        name=source.name,
        source_type=source.source_type,
        snapshot_url=source.snapshot_url,
        local_folder_path=source.local_folder_path,
        access_authorized=source.access_authorized,
        interval_minutes=source.interval_minutes,
        observation_window_hours=source.observation_window_hours,
        status=source.status,
        last_run_at=source.last_run_at,
        next_run_at=source.next_run_at,
        last_error=source.last_error,
        last_image_hash=source.last_image_hash,
        local_folder_index=source.local_folder_index,
        last_journal_date=source.last_journal_date,
        last_journal_hour_at=source.last_journal_hour_at,
        capture_count=source.capture_count,
        skip_count=source.skip_count,
        error_count=source.error_count,
        created_at=source.created_at,
        updated_at=source.updated_at,
    )


@router.get("", response_model=list[CameraSourceRead], summary="List camera sources")
def list_cameras(db: Session = Depends(get_db)) -> list[CameraSourceRead]:
    sources = db.scalars(
        select(CameraSource)
        .options(joinedload(CameraSource.animal))
        .order_by(CameraSource.id.desc())
    ).unique().all()
    return [_to_read(s) for s in sources]


@router.post(
    "/probe",
    response_model=CameraProbeResponse,
    summary="Test an authorized live/snapshot URL (does not save)",
)
def probe_camera(payload: CameraProbeRequest) -> CameraProbeResponse:
    """
    Grab one still from an authorized media URL (direct HLS/RTSP/image, or
    YouTube / Explore.org live pages resolved when access is confirmed).
    """
    try:
        result = probe_live_url(
            payload.url, prefer_stream=payload.prefer_stream
        )
    except LiveCaptureError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    return CameraProbeResponse(**result)


@router.post(
    "/extract-frames",
    response_model=FrameExtractResponse,
    summary="Extract stills from an authorized live URL",
)
def extract_frames(payload: FrameExtractRequest) -> FrameExtractResponse:
    """
    Pull N JPEG stills (with optional spacing) from a live source you are
    permitted to poll. Saves under uploads/extracted_frames/.
    """
    try:
        result = extract_live_frames(
            url=payload.url,
            count=payload.count,
            interval_seconds=payload.interval_seconds,
            access_authorized=payload.access_authorized,
            label=payload.label,
        )
    except LiveCaptureError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    frames = [
        ExtractedFrameRead(
            index=item["index"],
            filename=item["filename"],
            byte_size=item["byte_size"],
            image_url=item["image_url"],
        )
        for item in result["frames"]
    ]
    return FrameExtractResponse(
        job_id=result["job_id"],
        job_dir=result["job_dir"],
        source_url=result["source_url"],
        resolved_media=result["resolved_media"],
        frame_count=result["frame_count"],
        interval_seconds=result["interval_seconds"],
        frames=frames,
        detail=result["detail"],
    )


@router.get(
    "/extracted/{job_dir}/{filename}",
    summary="Serve one extracted live still",
)
def get_extracted_frame(job_dir: str, filename: str) -> FileResponse:
    if "/" in job_dir or "\\" in job_dir or ".." in job_dir:
        raise HTTPException(status_code=400, detail="Invalid job_dir.")
    if "/" in filename or "\\" in filename or ".." in filename:
        raise HTTPException(status_code=400, detail="Invalid filename.")
    path = (_extracted_root() / job_dir / filename).resolve()
    root = _extracted_root().resolve()
    if not str(path).startswith(str(root)) or not path.is_file():
        raise HTTPException(status_code=404, detail="Extracted frame not found.")
    media = "image/jpeg"
    if path.suffix.lower() == ".png":
        media = "image/png"
    elif path.suffix.lower() == ".webp":
        media = "image/webp"
    return FileResponse(path, media_type=media, filename=filename)


@router.post(
    "",
    response_model=CameraSourceRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create an authorized camera / local sample source",
)
def create_camera(
    payload: CameraSourceCreate, db: Session = Depends(get_db)
) -> CameraSourceRead:
    # animal_id is optional — vision discovers animals from each still.
    animal = None
    if payload.animal_id is not None:
        animal = db.get(Animal, payload.animal_id)
        if animal is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Animal with id {payload.animal_id} was not found.",
            )

    settings = get_settings()
    interval = max(
        settings.min_monitor_interval_minutes,
        payload.interval_minutes,
    )
    # YouTube / Explore-style live pages: poll every 5 minutes by default.
    from app.services.stream_resolve import looks_like_platform_live_page

    if payload.snapshot_url and looks_like_platform_live_page(payload.snapshot_url):
        interval = max(settings.min_monitor_interval_minutes, 5)

    source = CameraSource(
        animal_id=animal.id if animal else None,
        name=payload.name,
        source_type=payload.source_type,
        snapshot_url=payload.snapshot_url,
        local_folder_path=payload.local_folder_path,
        access_authorized=payload.access_authorized,
        interval_minutes=interval,
        observation_window_hours=payload.observation_window_hours,
        status="stopped",
    )
    db.add(source)
    db.commit()
    db.refresh(source)
    if animal is not None:
        source.animal = animal
    return _to_read(source)


@router.get(
    "/{camera_id}",
    response_model=CameraSourceRead,
    summary="Get one camera source",
)
def get_camera(camera_id: int, db: Session = Depends(get_db)) -> CameraSourceRead:
    source = db.scalars(
        select(CameraSource)
        .where(CameraSource.id == camera_id)
        .options(joinedload(CameraSource.animal))
    ).unique().first()
    if source is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Camera source {camera_id} was not found.",
        )
    return _to_read(source)


@router.patch(
    "/{camera_id}",
    response_model=CameraSourceRead,
    summary="Update camera source settings",
)
def update_camera(
    camera_id: int,
    payload: CameraSourceUpdate,
    db: Session = Depends(get_db),
) -> CameraSourceRead:
    source = db.scalars(
        select(CameraSource)
        .where(CameraSource.id == camera_id)
        .options(joinedload(CameraSource.animal))
    ).unique().first()
    if source is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Camera source {camera_id} was not found.",
        )

    data = payload.model_dump(exclude_unset=True)
    settings = get_settings()
    if "interval_minutes" in data and data["interval_minutes"] is not None:
        data["interval_minutes"] = max(
            settings.min_monitor_interval_minutes,
            data["interval_minutes"],
        )
    for key, value in data.items():
        setattr(source, key, value)

    db.add(source)
    db.commit()
    db.refresh(source)
    return _to_read(source)


@router.delete(
    "/{camera_id}",
    status_code=status.HTTP_200_OK,
    summary="Remove a camera source",
)
def delete_camera(
    camera_id: int, db: Session = Depends(get_db)
) -> dict:
    """
    Stop monitoring if needed, detach observations from this camera, then
    delete the source (captures + logs cascade). Animal journals/observations
    are kept.
    """
    source = db.get(CameraSource, camera_id)
    if source is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Camera source {camera_id} was not found.",
        )

    name = source.name
    if source.status == "running":
        stop_camera_source(db, source)
        source = db.get(CameraSource, camera_id)
        if source is None:
            return {"detail": f"Removed camera “{name}”.", "id": camera_id}

    # Keep sighting history; clear FKs so SQLite allows delete.
    db.execute(
        update(Observation)
        .where(Observation.camera_source_id == camera_id)
        .values(camera_source_id=None, camera_capture_id=None)
    )
    db.delete(source)
    db.commit()
    return {"detail": f"Removed camera “{name}”.", "id": camera_id}


@router.post(
    "/{camera_id}/start",
    response_model=CameraMonitorActionResponse,
    summary="Start monitoring this camera source",
)
def start_monitor(
    camera_id: int, db: Session = Depends(get_db)
) -> CameraMonitorActionResponse:
    source = db.scalars(
        select(CameraSource)
        .where(CameraSource.id == camera_id)
        .options(joinedload(CameraSource.animal))
    ).unique().first()
    if source is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Camera source {camera_id} was not found.",
        )
    try:
        source = start_camera_source(db, source)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    source = db.scalars(
        select(CameraSource)
        .where(CameraSource.id == camera_id)
        .options(joinedload(CameraSource.animal))
    ).unique().first()
    assert source is not None
    return CameraMonitorActionResponse(
        camera=_to_read(source),
        detail=(
            "Monitoring started. The in-process scheduler will poll on the "
            f"configured interval ({source.interval_minutes} min)."
        ),
    )


@router.post(
    "/{camera_id}/stop",
    response_model=CameraMonitorActionResponse,
    summary="Stop monitoring this camera source",
)
def stop_monitor(
    camera_id: int, db: Session = Depends(get_db)
) -> CameraMonitorActionResponse:
    source = db.scalars(
        select(CameraSource)
        .where(CameraSource.id == camera_id)
        .options(joinedload(CameraSource.animal))
    ).unique().first()
    if source is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Camera source {camera_id} was not found.",
        )
    source = stop_camera_source(db, source)
    source = db.scalars(
        select(CameraSource)
        .where(CameraSource.id == camera_id)
        .options(joinedload(CameraSource.animal))
    ).unique().first()
    assert source is not None
    return CameraMonitorActionResponse(
        camera=_to_read(source),
        detail="Monitoring stopped.",
    )


@router.get(
    "/{camera_id}/status",
    response_model=CameraMonitorStatus,
    summary="Monitoring status + recent logs",
)
def monitor_status(
    camera_id: int,
    log_limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> CameraMonitorStatus:
    source = db.get(CameraSource, camera_id)
    if source is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Camera source {camera_id} was not found.",
        )
    logs = list(
        db.scalars(
            select(MonitoringLog)
            .where(MonitoringLog.camera_source_id == camera_id)
            .order_by(MonitoringLog.created_at.desc(), MonitoringLog.id.desc())
            .limit(log_limit)
        ).all()
    )
    return CameraMonitorStatus(
        camera_source_id=source.id,
        status=source.status,
        last_run_at=source.last_run_at,
        next_run_at=source.next_run_at,
        last_error=source.last_error,
        capture_count=source.capture_count,
        skip_count=source.skip_count,
        error_count=source.error_count,
        scheduler_running=is_scheduler_running(),
        detail=(
            "Persistent state is stored in SQLite. The scheduler thread runs "
            "only while this API process is up."
        ),
        recent_logs=[MonitoringLogRead.model_validate(log) for log in logs],
    )
