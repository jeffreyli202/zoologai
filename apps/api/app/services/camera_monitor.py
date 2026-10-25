"""
Authorized camera monitoring: live still / snapshot / local sample → vision → Observation.

Rules:
- snapshot_url, live_stream (direct media), or local_folder.
- access_authorized must be true (operator confirms permission).
- No HTML scraping or bypassing stream protections.
- Duplicate image bytes (SHA-256) are skipped.
- observed_at uses the real capture/retrieval timestamp.
"""

from __future__ import annotations

import hashlib
import json
import logging
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import SessionLocal
from app.models import (
    Animal,
    CameraCapture,
    CameraSource,
    DailyJournal,
    MonitoringLog,
    Observation,
)
from app.services.gemini_client import GeminiAPIError, GeminiConfigError
from app.services.journals import filter_sightings_for_journal, generate_daily_journal
from app.services.live_capture import LiveCaptureError, capture_live_still
from app.services.vision import (
    BehaviorLabel,
    VisionAPIError,
    VisionConfigError,
    analyze_frame_image,
)

logger = logging.getLogger("zoologai.camera_monitor")

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _capture_root() -> Path:
    root = Path(get_settings().camera_capture_dir).resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def _source_capture_dir(source_id: int) -> Path:
    path = _capture_root() / f"source_{source_id}"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _content_hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def add_monitoring_log(
    db: Session,
    *,
    camera_source_id: int,
    level: str,
    event: str,
    message: str,
    detail: str | None = None,
) -> None:
    db.add(
        MonitoringLog(
            camera_source_id=camera_source_id,
            level=level,
            event=event,
            message=message,
            detail=detail,
        )
    )
    log_fn = logger.error if level == "error" else logger.info
    log_fn(
        "camera_source=%s event=%s level=%s message=%s",
        camera_source_id,
        event,
        level,
        message,
    )


def _list_local_images(folder: Path) -> list[Path]:
    if not folder.is_dir():
        raise RuntimeError(f"Local folder not found: {folder}")
    files = [
        p
        for p in sorted(folder.iterdir())
        if p.is_file() and p.suffix.lower() in IMAGE_SUFFIXES
    ]
    if not files:
        raise RuntimeError(f"No sample images in folder: {folder}")
    return files


def _fetch_local_folder(source: CameraSource) -> tuple[bytes, str, int]:
    folder = Path(source.local_folder_path or "").expanduser()
    if not folder.is_absolute():
        # Resolve relative to API process cwd (apps/api when running uvicorn there).
        folder = (Path.cwd() / folder).resolve()
    else:
        folder = folder.resolve()

    files = _list_local_images(folder)
    index = source.local_folder_index % len(files)
    path = files[index]
    data = path.read_bytes()
    if not data:
        raise RuntimeError(f"Sample image is empty: {path.name}")
    settings = get_settings()
    if len(data) > settings.monitor_max_image_bytes:
        raise RuntimeError(f"Sample image too large: {path.name}")
    return data, path.suffix.lower() or ".jpg", index


def _hour_start(dt: datetime) -> datetime:
    dt = dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)
    dt = dt.astimezone(timezone.utc)
    return dt.replace(minute=0, second=0, microsecond=0)


def resolve_or_create_animal(db: Session, label: str) -> Animal:
    """Match an existing animal by name (case-insensitive) or create one."""
    name = " ".join(label.split()).strip()[:100]
    if not name:
        raise ValueError("Empty animal label")
    existing = db.scalar(
        select(Animal).where(func.lower(Animal.name) == name.lower())
    )
    if existing is not None:
        return existing
    animal = Animal(
        name=name,
        species=name,
        description=(
            f"Auto-created from camera vision when the model listed "
            f"“{name}” in animals_seen."
        ),
    )
    db.add(animal)
    db.flush()
    return animal


def _maybe_generate_journal(db: Session, source: CameraSource) -> None:
    """
    After each monitor tick, journal every animal that this camera actually
    sighted in each completed UTC hour (no journal when nothing was seen).
    """
    now = _utc_now()
    latest_complete = _hour_start(now) - timedelta(hours=1)

    if source.last_journal_hour_at is not None:
        last = source.last_journal_hour_at
        if last.tzinfo is None:
            last = last.replace(tzinfo=timezone.utc)
        cursor = _hour_start(last) + timedelta(hours=1)
    else:
        lookback_hours = max(24, int(source.observation_window_hours or 24))
        cursor = latest_complete - timedelta(hours=lookback_hours - 1)

    while cursor <= latest_complete:
        hour = cursor.hour
        day = cursor.date()
        start = cursor
        end = cursor + timedelta(hours=1) - timedelta(microseconds=1)
        label = f"{day.isoformat()} {hour:02d}:00 UTC"

        animal_ids = list(
            db.scalars(
                select(Observation.animal_id)
                .where(
                    Observation.camera_source_id == source.id,
                    Observation.observed_at >= start,
                    Observation.observed_at <= end,
                    Observation.behavior != BehaviorLabel.not_visible.value,
                )
                .distinct()
            ).all()
        )

        if not animal_ids:
            source.last_journal_hour_at = cursor
            add_monitoring_log(
                db,
                camera_source_id=source.id,
                level="info",
                event="journal",
                message=(
                    f"No animals observed on this camera in {label}; "
                    "skipped hourly journals."
                ),
            )
            cursor += timedelta(hours=1)
            continue

        for animal_id in animal_ids:
            animal = db.get(Animal, animal_id)
            if animal is None:
                continue

            existing = db.scalar(
                select(DailyJournal).where(
                    DailyJournal.animal_id == animal.id,
                    DailyJournal.date == day,
                    DailyJournal.hour == hour,
                )
            )
            if existing is not None:
                continue

            observations = list(
                db.scalars(
                    select(Observation)
                    .where(
                        Observation.animal_id == animal.id,
                        Observation.observed_at >= start,
                        Observation.observed_at <= end,
                    )
                    .order_by(Observation.observed_at.asc(), Observation.id.asc())
                ).all()
            )
            sightings = filter_sightings_for_journal(
                observations,
                animal_name=animal.name,
                animal_species=animal.species,
            )
            if not sightings:
                continue

            payload = [
                {
                    "id": obs.id,
                    "behavior": obs.behavior,
                    "description": obs.description,
                    "visible_evidence": obs.visible_evidence,
                    "confidence": obs.confidence,
                    "video_timestamp_seconds": obs.video_timestamp_seconds,
                    "observed_at": (
                        obs.observed_at.isoformat() if obs.observed_at else None
                    ),
                }
                for obs in sightings
            ]

            try:
                content, source_ids = generate_daily_journal(
                    animal_name=animal.name,
                    animal_species=animal.species,
                    journal_date=day,
                    observations=payload,
                    hour=hour,
                )
            except (GeminiConfigError, GeminiAPIError, Exception) as exc:
                add_monitoring_log(
                    db,
                    camera_source_id=source.id,
                    level="error",
                    event="journal",
                    message=f"Hourly journal failed for {animal.name} in {label}.",
                    detail=str(exc),
                )
                source.error_count = (source.error_count or 0) + 1
                return

            db.add(
                DailyJournal(
                    animal_id=animal.id,
                    date=day,
                    hour=hour,
                    content=content,
                    source_observation_ids=json.dumps(source_ids),
                    updated_at=_utc_now(),
                )
            )
            source.last_journal_date = day
            add_monitoring_log(
                db,
                camera_source_id=source.id,
                level="info",
                event="journal",
                message=f"Hourly journal saved for {animal.name} ({label}).",
                detail=f"observation_ids={source_ids}",
            )

        source.last_journal_hour_at = cursor
        cursor += timedelta(hours=1)


def run_monitor_tick(db: Session, source_id: int) -> None:
    """
    One scheduled capture for a camera source. Safe to call from the scheduler.
    """
    source = db.get(CameraSource, source_id)
    if source is None or source.status != "running":
        return

    now = _utc_now()
    settings = get_settings()
    interval = max(
        settings.min_monitor_interval_minutes,
        source.interval_minutes or settings.default_monitor_interval_minutes,
    )

    try:
        if not source.access_authorized:
            raise RuntimeError(
                "access_authorized is false — refusing to poll. "
                "Only monitor sources you are permitted to access."
            )

        if source.source_type in {"snapshot_url", "live_stream"}:
            if not source.snapshot_url:
                raise RuntimeError("Media URL is missing.")
            try:
                data, ext = capture_live_still(
                    source.snapshot_url,
                    prefer_stream=(source.source_type == "live_stream"),
                )
            except LiveCaptureError as exc:
                raise RuntimeError(str(exc)) from exc
            folder_index = source.local_folder_index
        elif source.source_type == "local_folder":
            data, ext, folder_index = _fetch_local_folder(source)
        else:
            raise RuntimeError(f"Unsupported source_type: {source.source_type}")

        digest = _content_hash(data)
        captured_at = now

        # Duplicate vs last hash or any prior capture for this source.
        if source.last_image_hash == digest:
            source.skip_count = (source.skip_count or 0) + 1
            source.last_run_at = now
            source.next_run_at = now + timedelta(minutes=interval)
            source.last_error = None
            source.updated_at = now
            add_monitoring_log(
                db,
                camera_source_id=source.id,
                level="skip",
                event="skip_duplicate",
                message="Skipped duplicate image (matches last capture hash).",
                detail=digest[:16],
            )
            db.add(source)
            db.commit()
            return

        existing_capture = db.scalar(
            select(CameraCapture).where(
                CameraCapture.camera_source_id == source.id,
                CameraCapture.content_hash == digest,
            )
        )
        if existing_capture is not None:
            source.skip_count = (source.skip_count or 0) + 1
            source.last_image_hash = digest
            source.last_run_at = now
            source.next_run_at = now + timedelta(minutes=interval)
            source.last_error = None
            source.updated_at = now
            add_monitoring_log(
                db,
                camera_source_id=source.id,
                level="skip",
                event="skip_duplicate",
                message="Skipped duplicate image (hash already stored for this source).",
                detail=f"capture_id={existing_capture.id}",
            )
            db.add(source)
            db.commit()
            return

        filename = f"{captured_at.strftime('%Y%m%dT%H%M%SZ')}_{uuid.uuid4().hex[:8]}{ext}"
        dest = _source_capture_dir(source.id) / filename
        dest.write_bytes(data)

        capture = CameraCapture(
            camera_source_id=source.id,
            filename=filename,
            content_hash=digest,
            captured_at=captured_at,
            status="captured",
        )
        db.add(capture)
        # Commit before the (slow) vision call so HTTP start/stop is not blocked.
        source_type = source.source_type
        db.flush()
        capture_id = capture.id
        db.commit()
        db.close()

        vision_error: str | None = None
        result = None
        try:
            result = analyze_frame_image(dest)
        except (VisionConfigError, VisionAPIError) as exc:
            vision_error = str(exc)

        db = SessionLocal()
        try:
            source = db.get(CameraSource, source_id)
            capture = db.get(CameraCapture, capture_id)
            if source is None or capture is None:
                return

            if vision_error is not None or result is None:
                capture.status = "failed"
                capture.error_message = vision_error or "Vision analysis failed."
                source.error_count = (source.error_count or 0) + 1
                source.last_error = vision_error
                source.last_run_at = now
                source.next_run_at = now + timedelta(minutes=interval)
                # Do not set last_image_hash — allow retry after transient API errors.
                # Local folder still advances so one bad sample does not block the queue.
                if source_type == "local_folder":
                    source.local_folder_index = folder_index + 1
                source.updated_at = now
                add_monitoring_log(
                    db,
                    camera_source_id=source.id,
                    level="error",
                    event="analyze",
                    message="Vision analysis failed.",
                    detail=vision_error,
                )
                db.add(source)
                db.commit()
                return

            labels = [
                " ".join(str(label).split()).strip()
                for label in (result.animals_seen or [])
                if str(label).strip()
            ]
            # Dedupe case-insensitively while preserving first spelling.
            seen_keys: set[str] = set()
            unique_labels: list[str] = []
            for label in labels:
                key = label.lower()
                if key in seen_keys:
                    continue
                seen_keys.add(key)
                unique_labels.append(label)

            created_for: list[str] = []
            if (
                result.behavior != BehaviorLabel.not_visible
                and unique_labels
            ):
                for label in unique_labels:
                    animal = resolve_or_create_animal(db, label)
                    db.add(
                        Observation(
                            animal_id=animal.id,
                            video_id=None,
                            frame_id=None,
                            camera_source_id=source.id,
                            camera_capture_id=capture.id,
                            observed_at=captured_at,
                            video_timestamp_seconds=0.0,
                            behavior=result.behavior.value,
                            description=result.description,
                            visible_evidence=result.visible_evidence,
                            confidence=result.confidence,
                        )
                    )
                    created_for.append(animal.name)

            capture.status = "analyzed"
            source.capture_count = (source.capture_count or 0) + 1
            source.last_image_hash = digest
            source.last_run_at = now
            source.next_run_at = now + timedelta(minutes=interval)
            source.last_error = None
            if source_type == "local_folder":
                source.local_folder_index = folder_index + 1
            source.updated_at = now

            if created_for:
                message = (
                    f"Captured and analyzed ({result.behavior.value}); "
                    f"animals: {', '.join(created_for)}."
                )
            else:
                message = (
                    f"Captured and analyzed ({result.behavior.value}); "
                    "no animals identified — no observation/journal rows."
                )
            add_monitoring_log(
                db,
                camera_source_id=source.id,
                level="info",
                event="analyze",
                message=message,
                detail=f"capture_id={capture.id} hash={digest[:16]}",
            )
            db.add(source)
            db.commit()
        finally:
            db.close()

        # Journal generation is separate so it cannot lock monitor controls.
        journal_db = SessionLocal()
        try:
            source = journal_db.get(CameraSource, source_id)
            if source is not None:
                _maybe_generate_journal(journal_db, source)
                journal_db.add(source)
                journal_db.commit()
        finally:
            journal_db.close()
        return

    except Exception as exc:
        try:
            if not db.is_active:
                db = SessionLocal()
        except Exception:
            db = SessionLocal()
        try:
            source = db.get(CameraSource, source_id)
            if source is None:
                return
            source.error_count = (source.error_count or 0) + 1
            source.last_error = str(exc)
            source.last_run_at = now
            source.next_run_at = now + timedelta(minutes=interval)
            source.updated_at = now
            if (
                "access_authorized" in str(exc).lower()
                or "unsupported source" in str(exc).lower()
            ):
                source.status = "error"
            add_monitoring_log(
                db,
                camera_source_id=source.id,
                level="error",
                event="fetch",
                message="Monitor tick failed.",
                detail=str(exc),
            )
            db.add(source)
            db.commit()
        finally:
            logger.exception("Monitor tick failed for source %s", source_id)


def start_camera_source(db: Session, source: CameraSource) -> CameraSource:
    if not source.access_authorized:
        raise ValueError(
            "Cannot start: access_authorized is false. "
            "Confirm you have permission to poll this source."
        )
    settings = get_settings()
    interval = max(
        settings.min_monitor_interval_minutes,
        source.interval_minutes or settings.default_monitor_interval_minutes,
    )
    now = _utc_now()
    source.status = "running"
    source.last_error = None
    source.next_run_at = now  # due immediately on next scheduler tick
    source.updated_at = now
    source.interval_minutes = interval
    add_monitoring_log(
        db,
        camera_source_id=source.id,
        level="info",
        event="scheduler",
        message=f"Monitoring started (interval={interval} min).",
    )
    db.add(source)
    db.commit()
    db.refresh(source)
    return source


def stop_camera_source(db: Session, source: CameraSource) -> CameraSource:
    now = _utc_now()
    source.status = "stopped"
    source.next_run_at = None
    source.updated_at = now
    add_monitoring_log(
        db,
        camera_source_id=source.id,
        level="info",
        event="scheduler",
        message="Monitoring stopped.",
    )
    db.add(source)
    db.commit()
    db.refresh(source)
    return source
