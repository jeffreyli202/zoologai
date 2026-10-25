"""
Capture one still from an authorized live media URL.

Allowed inputs (operator must confirm permission):
- Direct image snapshot URLs (image/jpeg, image/png, …)
- Direct motion JPEG / HTTP camera streams
- Direct HLS (.m3u8) or other URLs OpenCV/FFmpeg can open without auth bypass
- Authorized YouTube / Explore.org live pages (resolved via yt-dlp to a media URL)

Not allowed / not implemented:
- Scraping arbitrary zoo HTML player pages
- Bypassing logins, tokens, DRM, or paywalled streams
"""

from __future__ import annotations

import logging
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import cv2
import numpy as np

from app.config import get_settings

logger = logging.getLogger("zoologai.live_capture")

BLOCKED_HTML_HINTS = (
    "text/html",
    "application/xhtml",
    "text/xml",
)


class LiveCaptureError(RuntimeError):
    """Raised when a live/snapshot URL cannot yield a usable frame."""


def _looks_like_image_url(url: str) -> bool:
    path = url.split("?", 1)[0].lower()
    return path.endswith((".jpg", ".jpeg", ".png", ".webp", ".bmp"))


def _looks_like_stream_url(url: str) -> bool:
    path = url.split("?", 1)[0].lower()
    return (
        path.endswith((".m3u8", ".mp4", ".mjpg", ".mjpeg"))
        or "mjpg" in path
        or "mjpeg" in path
        or url.lower().startswith("rtsp://")
        or url.lower().startswith("rtsps://")
    )


def fetch_image_bytes(url: str) -> tuple[bytes, str]:
    """HTTP GET a direct image. Rejects HTML pages."""
    settings = get_settings()
    request = Request(
        url,
        headers={
            "User-Agent": "ZooLogAI-Monitor/0.1 (authorized live animal cam)",
            "Accept": "image/*,*/*;q=0.8",
        },
        method="GET",
    )
    try:
        with urlopen(request, timeout=settings.monitor_fetch_timeout_seconds) as resp:
            content_type = (resp.headers.get("Content-Type") or "").lower()
            data = resp.read(settings.monitor_max_image_bytes + 1)
    except HTTPError as exc:
        raise LiveCaptureError(f"HTTP {exc.code}: {exc.reason}") from exc
    except URLError as exc:
        raise LiveCaptureError(f"Request failed: {exc.reason}") from exc
    except TimeoutError as exc:
        raise LiveCaptureError("Request timed out.") from exc

    if any(hint in content_type for hint in BLOCKED_HTML_HINTS):
        raise LiveCaptureError(
            "URL returned an HTML page, not a media stream or image. "
            "Paste a direct snapshot/HLS/MJPEG/RTSP URL you are allowed to use — "
            "not a zoo website page."
        )
    if len(data) > settings.monitor_max_image_bytes:
        raise LiveCaptureError("Image exceeds configured max size.")
    if not data:
        raise LiveCaptureError("Empty response.")

    # Heuristic: HTML often starts with <! or <html even with wrong content-type.
    head = data[:200].lstrip().lower()
    if head.startswith(b"<!doctype") or head.startswith(b"<html"):
        raise LiveCaptureError(
            "Response looks like an HTML page. Use a direct media URL, not a webpage."
        )

    if "png" in content_type or data[:8] == b"\x89PNG\r\n\x1a\n":
        ext = ".png"
    elif "webp" in content_type:
        ext = ".webp"
    else:
        ext = ".jpg"
    return data, ext


def grab_frame_from_stream(url: str) -> tuple[bytes, str]:
    """
    Open an authorized live URL with OpenCV and encode one JPEG frame.
    """
    settings = get_settings()
    # CAP_FFMPEG helps with HLS/HTTP when available in the OpenCV build.
    capture = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
    if not capture.isOpened():
        capture = cv2.VideoCapture(url)
    if not capture.isOpened():
        raise LiveCaptureError(
            "Could not open live media URL. Need a direct stream "
            "(MJPEG / HLS .m3u8 / RTSP / MP4) that permits automated access."
        )

    try:
        # Discard a couple of buffered frames so we get a fresher still.
        frame = None
        for _ in range(5):
            ok, candidate = capture.read()
            if ok and candidate is not None:
                frame = candidate
        if frame is None:
            raise LiveCaptureError("Opened the stream but could not read a frame.")

        # Bound longest edge roughly like video frames (keeps Gemini cost down).
        max_dim = settings.frame_max_dimension
        height, width = frame.shape[:2]
        longest = max(height, width)
        if longest > max_dim:
            scale = max_dim / float(longest)
            frame = cv2.resize(
                frame,
                (int(width * scale), int(height * scale)),
                interpolation=cv2.INTER_AREA,
            )

        ok, encoded = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
        if not ok:
            raise LiveCaptureError("Failed to encode captured frame as JPEG.")
        data = encoded.tobytes()
        if len(data) > settings.monitor_max_image_bytes:
            raise LiveCaptureError("Encoded frame exceeds max image size.")
        return data, ".jpg"
    finally:
        capture.release()


def capture_live_still(url: str, *, prefer_stream: bool = False) -> tuple[bytes, str]:
    """
    Return (jpeg_or_image_bytes, extension) from an authorized live source URL.
    """
    url = url.strip()
    if not (
        url.startswith("http://")
        or url.startswith("https://")
        or url.startswith("rtsp://")
        or url.startswith("rtsps://")
    ):
        raise LiveCaptureError(
            "URL must be http(s) or rtsp(s). Webpage paths without a direct "
            "media endpoint are not supported."
        )

    # Authorized YouTube / Explore.org live pages → temporary media URL.
    from app.services.stream_resolve import (
        looks_like_platform_live_page,
        resolve_media_url,
    )

    open_url = url
    if looks_like_platform_live_page(url):
        open_url = resolve_media_url(url)
        prefer_stream = True

    if prefer_stream or _looks_like_stream_url(open_url):
        try:
            return grab_frame_from_stream(open_url)
        except LiveCaptureError:
            # Fall through to image GET for hybrid endpoints.
            if prefer_stream and not _looks_like_image_url(open_url):
                raise

    if _looks_like_image_url(open_url) or not prefer_stream:
        try:
            return fetch_image_bytes(open_url)
        except LiveCaptureError as image_exc:
            message = str(image_exc).lower()
            # Never fall through to stream open for HTML / webpage responses.
            if "html" in message or "webpage" in message:
                # Platform pages should already be resolved; otherwise fail clearly.
                if looks_like_platform_live_page(url):
                    raise LiveCaptureError(
                        "Resolved live page still returned HTML. The stream may "
                        "be offline or blocked."
                    ) from image_exc
                raise
            if prefer_stream or _looks_like_stream_url(open_url):
                raise
            # Last resort: extension-less camera endpoints that still serve video.
            logger.info("Image fetch failed (%s); trying as live stream.", image_exc)
            return grab_frame_from_stream(open_url)

    return grab_frame_from_stream(open_url)


def probe_live_url(url: str, *, prefer_stream: bool = False) -> dict:
    """Test that a URL yields a frame without saving anything."""
    data, ext = capture_live_still(url, prefer_stream=prefer_stream)
    # Cheap sanity check: decode if image-like
    arr = np.frombuffer(data, dtype=np.uint8)
    decoded = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if decoded is None:
        raise LiveCaptureError("Captured bytes could not be decoded as an image.")
    height, width = decoded.shape[:2]
    return {
        "ok": True,
        "byte_size": len(data),
        "extension": ext,
        "width": int(width),
        "height": int(height),
        "detail": "Live still captured successfully from authorized media URL.",
    }
