"""
Resolve an authorized public live URL to something OpenCV/FFmpeg can open.

Use only when the operator confirms permission (access_authorized).
Supports:
- Direct media already usable by OpenCV (returned unchanged)
- YouTube / Explore.org-style live pages via yt-dlp → temporary HLS/HTTP media URL

Does not bypass logins, DRM, or paywalled streams.
"""

from __future__ import annotations

import logging
from urllib.parse import urlparse

from app.services.live_capture import LiveCaptureError

logger = logging.getLogger("zoologai.stream_resolve")

PLATFORM_HOST_HINTS = (
    "youtube.com",
    "youtu.be",
    "youtube-nocookie.com",
    "explore.org",
    "www.explore.org",
)


def looks_like_platform_live_page(url: str) -> bool:
    try:
        host = (urlparse(url).hostname or "").lower()
    except Exception:
        return False
    if not host:
        return False
    return any(host == h or host.endswith("." + h) for h in PLATFORM_HOST_HINTS)


def resolve_media_url(url: str) -> str:
    """
    Return a direct media URL OpenCV can open.

    For YouTube / Explore live pages, uses yt-dlp (operator must already have
    permission). Direct .m3u8 / RTSP / image URLs pass through unchanged.
    """
    url = url.strip()
    if not url:
        raise LiveCaptureError("URL is empty.")

    path = url.split("?", 1)[0].lower()
    if (
        path.endswith((".m3u8", ".mp4", ".mjpg", ".mjpeg", ".jpg", ".jpeg", ".png", ".webp"))
        or url.lower().startswith("rtsp://")
        or url.lower().startswith("rtsps://")
    ):
        return url

    if not looks_like_platform_live_page(url):
        # Leave as-is for extension-less camera endpoints; OpenCV may still open them.
        return url

    try:
        import yt_dlp  # type: ignore
    except ImportError as exc:
        raise LiveCaptureError(
            "yt-dlp is required to resolve YouTube / Explore.org live pages. "
            "Install backend deps (pip install -r requirements.txt)."
        ) from exc

    # Do not pass a restrictive `format` — live YouTube often only exposes
    # separate HLS video renditions; we pick a video URL from formats below.
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "noplaylist": True,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
    except Exception as exc:
        raise LiveCaptureError(
            f"Could not resolve authorized live page to a media URL: {exc}"
        ) from exc

    if not info:
        raise LiveCaptureError("yt-dlp returned no stream info for this URL.")

    # Prefer an explicit URL on the top-level entry.
    direct = info.get("url")
    if isinstance(direct, str) and direct.startswith(("http://", "https://")):
        logger.info("Resolved platform live page to media URL (top-level).")
        return direct

    # Otherwise pick from formats list.
    formats = info.get("formats") or []
    candidates: list[dict] = []
    for fmt in formats:
        media_url = fmt.get("url")
        if not isinstance(media_url, str):
            continue
        if not media_url.startswith(("http://", "https://")):
            continue
        protocol = str(fmt.get("protocol") or "")
        ext = str(fmt.get("ext") or "")
        vcodec = str(fmt.get("vcodec") or "none")
        if vcodec == "none":
            continue
        score = 0
        if "m3u8" in protocol or ext == "m3u8":
            score += 30
        if ext in {"mp4", "mpegts"}:
            score += 20
        height = fmt.get("height") or 0
        try:
            score += min(int(height), 1080) // 10
        except (TypeError, ValueError):
            pass
        candidates.append({"url": media_url, "score": score})

    if not candidates:
        raise LiveCaptureError(
            "No video media URL found for this live page. "
            "Confirm the stream is live and access is permitted."
        )

    candidates.sort(key=lambda item: item["score"], reverse=True)
    logger.info("Resolved platform live page to media URL (format pick).")
    return candidates[0]["url"]
