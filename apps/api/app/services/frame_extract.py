"""
Extract still frames from an authorized live URL into uploads/extracted_frames/.

Operator must confirm access_authorized. Platform live pages (YouTube /
Explore.org) are resolved with yt-dlp first, then OpenCV grabs JPEGs.
"""

from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from app.config import get_settings
from app.services.live_capture import LiveCaptureError, capture_live_still
from app.services.stream_resolve import looks_like_platform_live_page, resolve_media_url


def _extract_root() -> Path:
    settings = get_settings()
    root = Path(settings.camera_capture_dir).resolve().parent / "extracted_frames"
    root.mkdir(parents=True, exist_ok=True)
    return root


def extract_live_frames(
    *,
    url: str,
    count: int = 4,
    interval_seconds: float = 5.0,
    access_authorized: bool = False,
    label: str | None = None,
) -> dict:
    """
    Grab `count` stills from an authorized live source.

    Returns job metadata + per-frame paths and public API image paths.
    """
    if not access_authorized:
        raise LiveCaptureError(
            "access_authorized must be true. Only extract frames from sources "
            "you are explicitly permitted to poll."
        )
    if count < 1 or count > 24:
        raise LiveCaptureError("count must be between 1 and 24.")
    if interval_seconds < 0 or interval_seconds > 300:
        raise LiveCaptureError("interval_seconds must be between 0 and 300.")

    source_url = url.strip()
    resolved = resolve_media_url(source_url)
    used_resolve = looks_like_platform_live_page(source_url) or (
        resolved != source_url
    )

    job_id = uuid.uuid4().hex[:12]
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    safe_label = "".join(
        ch if ch.isalnum() or ch in "-_" else "_"
        for ch in (label or "live").strip()
    )[:40] or "live"
    job_dir = _extract_root() / f"{safe_label}_{stamp}_{job_id}"
    job_dir.mkdir(parents=True, exist_ok=True)

    frames: list[dict] = []
    for index in range(count):
        if index > 0 and interval_seconds > 0:
            time.sleep(interval_seconds)
            # Re-resolve platform URLs periodically — HLS tokens expire.
            if looks_like_platform_live_page(source_url):
                resolved = resolve_media_url(source_url)

        data, ext = capture_live_still(resolved, prefer_stream=True)
        filename = f"frame_{index:03d}{ext or '.jpg'}"
        path = job_dir / filename
        path.write_bytes(data)
        frames.append(
            {
                "index": index,
                "filename": filename,
                "byte_size": len(data),
                "path": str(path),
                "image_url": f"/cameras/extracted/{job_dir.name}/{filename}",
            }
        )

    return {
        "job_id": job_id,
        "job_dir": job_dir.name,
        "source_url": source_url,
        "resolved_media": used_resolve,
        "frame_count": len(frames),
        "interval_seconds": interval_seconds,
        "frames": frames,
        "detail": (
            f"Extracted {len(frames)} frame(s) from authorized live source"
            + (" (platform URL resolved via yt-dlp)." if used_resolve else ".")
        ),
    }
