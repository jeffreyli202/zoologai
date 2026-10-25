"""
Lightweight in-process scheduler for local camera monitoring.

Scheduling
----------
A daemon thread wakes every `monitor_scheduler_tick_seconds` (default 30s),
loads CameraSource rows with status=running whose next_run_at is due, and runs
one monitor tick each. Interval spacing is enforced via next_run_at on the row.

Persistent job state
--------------------
start/stop, next_run_at, counters, and logs live in SQLite. The thread itself is
not durable — it is memory-only.

Rate limits
-----------
- User interval (default 15 minutes), floored by min_monitor_interval_minutes.
- HTTP timeout + max image bytes on snapshot fetches.
- Duplicate image hashes are skipped (no extra vision calls).

When the backend stops
----------------------
The scheduler thread dies with the process. DB rows keep status=running so a
restart can resume them (see resume_running_sources_on_startup). Missed ticks
while down are not backfilled — the next due run happens after restart.
"""

from __future__ import annotations

import logging
import threading
from datetime import datetime, timezone

from sqlalchemy import select

from app.config import get_settings
from app.database import SessionLocal
from app.models import CameraSource
from app.services.camera_monitor import add_monitoring_log, run_monitor_tick

logger = logging.getLogger("zoologai.scheduler")

_stop_event = threading.Event()
_thread: threading.Thread | None = None
_lock = threading.Lock()


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def is_scheduler_running() -> bool:
    return _thread is not None and _thread.is_alive() and not _stop_event.is_set()


def resume_running_sources_on_startup() -> None:
    """If sources were left running when the API last exited, make them due soon."""
    db = SessionLocal()
    try:
        sources = list(
            db.scalars(
                select(CameraSource).where(CameraSource.status == "running")
            ).all()
        )
        now = _utc_now()
        for source in sources:
            source.next_run_at = now
            source.updated_at = now
            add_monitoring_log(
                db,
                camera_source_id=source.id,
                level="info",
                event="scheduler",
                message="API restarted; resuming running monitor (next tick soon).",
            )
            db.add(source)
        if sources:
            db.commit()
            logger.info("Resumed %s running camera source(s).", len(sources))
    finally:
        db.close()


def _scheduler_loop() -> None:
    settings = get_settings()
    tick = max(5, int(settings.monitor_scheduler_tick_seconds))
    logger.info("Camera monitor scheduler started (tick=%ss).", tick)

    while True:
        db = SessionLocal()
        try:
            now = _utc_now()
            # SQLite often returns naive datetimes — compare in Python with UTC.
            candidates = list(
                db.scalars(
                    select(CameraSource).where(CameraSource.status == "running")
                ).all()
            )
            due_ids: list[int] = []
            for source in candidates:
                next_run = source.next_run_at
                if next_run is None:
                    continue
                if next_run.tzinfo is None:
                    next_run = next_run.replace(tzinfo=timezone.utc)
                if next_run <= now:
                    due_ids.append(source.id)
        finally:
            db.close()

        for source_id in due_ids:
            db = SessionLocal()
            try:
                run_monitor_tick(db, source_id)
            except Exception:
                logger.exception(
                    "Unhandled error running monitor for source %s", source_id
                )
            finally:
                db.close()

        if _stop_event.wait(timeout=tick):
            break

    logger.info("Camera monitor scheduler stopped.")


def start_scheduler() -> None:
    global _thread
    with _lock:
        if _thread is not None and _thread.is_alive():
            return
        _stop_event.clear()
        resume_running_sources_on_startup()
        _thread = threading.Thread(
            target=_scheduler_loop,
            name="zoologai-camera-scheduler",
            daemon=True,
        )
        _thread.start()


def stop_scheduler() -> None:
    global _thread
    with _lock:
        _stop_event.set()
        thread = _thread
        _thread = None
    if thread is not None:
        thread.join(timeout=5)
