"""
End-to-end video analysis job (extract frames → analyze with Gemini).

Runs in a background thread so HTTP requests stay fast. Progress is written to
the Video row for the frontend to poll.

Why not block the HTTP request?
-------------------------------
Frame extraction + many vision API calls can take minutes. Holding the HTTP
connection open that long wastes server workers, risks client timeouts, and
prevents the UI from showing live progress. Instead we return 202 Accepted
quickly and let the client poll status.
"""

from __future__ import annotations

import threading
from datetime import datetime, timezone

from sqlalchemy import select

from app.config import get_settings
from app.database import SessionLocal
from app.models import Frame, Observation, Video
from app.services.frames import FrameExtractionError, extract_frames_for_video, resolve_frame_path
from app.services.gemini_client import GeminiAPIError, GeminiConfigError
from app.services.vision import analyze_frame_image

# In-process lock so two threads cannot start the same video twice.
_job_locks: dict[int, threading.Lock] = {}
_job_locks_guard = threading.Lock()


def _lock_for(video_id: int) -> threading.Lock:
    with _job_locks_guard:
        if video_id not in _job_locks:
            _job_locks[video_id] = threading.Lock()
        return _job_locks[video_id]


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _update_video(db, video: Video, **fields) -> None:
    for key, value in fields.items():
        setattr(video, key, value)
    db.add(video)
    db.commit()
    db.refresh(video)


def run_video_analysis_job(video_id: int) -> None:
    """
    Background worker: extract frames if needed, then analyze up to
    MAX_AI_CALLS_PER_VIDEO_JOB frames that lack observations.
    """
    lock = _lock_for(video_id)
    if not lock.acquire(blocking=False):
        return

    db = SessionLocal()
    try:
        video = db.get(Video, video_id)
        if video is None:
            return

        settings = get_settings()
        max_ai_calls = settings.max_ai_calls_per_video_job

        _update_video(
            db,
            video,
            status="processing",
            analysis_progress=5,
            analysis_message="Starting analysis…",
            analysis_error=None,
            analysis_started_at=_utc_now(),
            analysis_finished_at=None,
            analysis_frames_done=0,
            analysis_ai_calls=0,
            analysis_frames_total=0,
        )

        # --- Step 1: ensure frames exist ---
        frames = list(
            db.scalars(
                select(Frame)
                .where(Frame.video_id == video_id)
                .order_by(Frame.frame_index.asc())
            ).all()
        )

        if not frames:
            _update_video(
                db,
                video,
                analysis_progress=15,
                analysis_message="Extracting frames…",
            )
            try:
                extracted = extract_frames_for_video(video_id, video.filename)
            except FrameExtractionError as exc:
                _update_video(
                    db,
                    video,
                    status="failed",
                    analysis_progress=100,
                    analysis_message="Frame extraction failed.",
                    analysis_error=str(exc),
                    analysis_finished_at=_utc_now(),
                )
                return

            for item in extracted:
                db.add(
                    Frame(
                        video_id=video.id,
                        filename=item.filename,
                        timestamp_seconds=item.timestamp_seconds,
                        frame_index=item.frame_index,
                    )
                )
            db.commit()
            frames = list(
                db.scalars(
                    select(Frame)
                    .where(Frame.video_id == video_id)
                    .order_by(Frame.frame_index.asc())
                ).all()
            )

        if not frames:
            _update_video(
                db,
                video,
                status="failed",
                analysis_progress=100,
                analysis_message="No frames available to analyze.",
                analysis_error="Frame extraction produced no frames.",
                analysis_finished_at=_utc_now(),
            )
            return

        total = len(frames)
        _update_video(
            db,
            video,
            analysis_progress=30,
            analysis_message="Frames ready. Analyzing with vision model…",
            analysis_frames_total=total,
        )

        # --- Step 2: analyze frames (skip ones that already have observations) ---
        ai_calls = 0
        done = 0
        skipped_existing = 0
        skipped_cap = 0

        for frame in frames:
            existing = db.scalar(
                select(Observation).where(Observation.frame_id == frame.id)
            )
            if existing is not None:
                skipped_existing += 1
                done += 1
                progress = 30 + int(70 * (done / total))
                _update_video(
                    db,
                    video,
                    analysis_progress=min(progress, 99),
                    analysis_frames_done=done,
                    analysis_message=(
                        f"Frame {done}/{total}: observation already saved (skipped AI)."
                    ),
                )
                continue

            if ai_calls >= max_ai_calls:
                skipped_cap += 1
                done += 1
                progress = 30 + int(70 * (done / total))
                _update_video(
                    db,
                    video,
                    analysis_progress=min(progress, 99),
                    analysis_frames_done=done,
                    analysis_message=(
                        f"Frame {done}/{total}: skipped (AI call cap {max_ai_calls})."
                    ),
                )
                continue

            _update_video(
                db,
                video,
                analysis_message=f"Analyzing frame {frame.frame_index + 1}/{total}…",
            )

            try:
                image_path = resolve_frame_path(frame.video_id, frame.filename)
                result = analyze_frame_image(image_path)
            except (GeminiConfigError, GeminiAPIError, FrameExtractionError) as exc:
                _update_video(
                    db,
                    video,
                    status="failed",
                    analysis_progress=100,
                    analysis_message="Analysis failed.",
                    analysis_error=str(exc),
                    analysis_ai_calls=ai_calls,
                    analysis_frames_done=done,
                    analysis_finished_at=_utc_now(),
                )
                return
            except Exception as exc:
                _update_video(
                    db,
                    video,
                    status="failed",
                    analysis_progress=100,
                    analysis_message="Analysis failed unexpectedly.",
                    analysis_error=str(exc),
                    analysis_ai_calls=ai_calls,
                    analysis_frames_done=done,
                    analysis_finished_at=_utc_now(),
                )
                return

            existing_again = db.scalar(
                select(Observation).where(Observation.frame_id == frame.id)
            )
            if existing_again is None:
                db.add(
                    Observation(
                        animal_id=video.animal_id,
                        video_id=video.id,
                        frame_id=frame.id,
                        video_timestamp_seconds=frame.timestamp_seconds,
                        behavior=result.behavior.value,
                        description=result.description,
                        visible_evidence=result.visible_evidence,
                        confidence=result.confidence,
                    )
                )
                db.commit()

            ai_calls += 1
            done += 1
            progress = 30 + int(70 * (done / total))
            _update_video(
                db,
                video,
                analysis_progress=min(progress, 99),
                analysis_frames_done=done,
                analysis_ai_calls=ai_calls,
                analysis_message=(
                    f"Analyzed {done}/{total} frames ({ai_calls} AI call(s))."
                ),
            )

        summary = (
            f"Completed. {ai_calls} AI call(s) used (max {max_ai_calls}). "
            f"{skipped_existing} already saved"
        )
        if skipped_cap:
            summary += f", {skipped_cap} skipped by AI cap"
        summary += "."

        _update_video(
            db,
            video,
            status="completed",
            analysis_progress=100,
            analysis_frames_done=total,
            analysis_ai_calls=ai_calls,
            analysis_message=summary,
            analysis_error=None,
            analysis_finished_at=_utc_now(),
        )
    finally:
        db.close()
        lock.release()


def start_video_analysis_job(video_id: int) -> None:
    """Fire-and-forget local background thread (no external queue)."""
    thread = threading.Thread(
        target=run_video_analysis_job,
        args=(video_id,),
        name=f"video-analysis-{video_id}",
        daemon=True,
    )
    thread.start()
