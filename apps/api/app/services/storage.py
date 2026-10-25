"""
Local video storage helpers.

Security goals:
- Never trust the client filename for the on-disk path (blocks path traversal).
- Only allow known extensions / content types.
- Enforce a max byte size while streaming to disk.
"""

from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import UploadFile

from app.config import get_settings

# Extension → accepted Content-Type values (browsers vary a bit for MOV).
ALLOWED_VIDEO_TYPES: dict[str, set[str]] = {
    ".mp4": {"video/mp4"},
    ".mov": {"video/quicktime", "video/mov"},
    ".webm": {"video/webm"},
}

CHUNK_SIZE = 1024 * 1024  # 1 MB


class UploadValidationError(ValueError):
    """Raised when an upload fails validation (type, size, empty file, etc.)."""


def get_upload_root() -> Path:
    settings = get_settings()
    root = Path(settings.upload_dir).resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def _extension_for_upload(filename: str | None, content_type: str | None) -> str:
    """
    Decide a safe extension from the *basename* only (no directories),
    then cross-check against Content-Type.
    """
    if not filename or not filename.strip():
        raise UploadValidationError("Missing file name.")

    # Path traversal defense: ignore any directory parts the client sends.
    # e.g. "../../evil.mp4" → "evil.mp4"
    basename = Path(filename.replace("\\", "/")).name
    if not basename or basename in {".", ".."}:
        raise UploadValidationError("Unsafe file name.")

    ext = Path(basename).suffix.lower()
    if ext not in ALLOWED_VIDEO_TYPES:
        raise UploadValidationError(
            "Unsupported file type. Allowed: MP4, MOV, WebM."
        )

    normalized_type = (content_type or "").split(";")[0].strip().lower()
    allowed_types = ALLOWED_VIDEO_TYPES[ext]
    # Some browsers send application/octet-stream; still require a valid extension.
    if normalized_type and normalized_type not in allowed_types | {
        "application/octet-stream"
    }:
        raise UploadValidationError(
            f"Content-Type '{normalized_type}' does not match an allowed video type."
        )

    return ext


async def save_video_upload(upload: UploadFile) -> tuple[str, str, int]:
    """
    Stream the upload to disk under a generated safe name.

    Returns (stored_filename, original_basename, size_bytes).
    """
    settings = get_settings()
    max_bytes = settings.max_upload_bytes

    ext = _extension_for_upload(upload.filename, upload.content_type)
    original_basename = Path((upload.filename or "video").replace("\\", "/")).name

    # Safe generated name — UUID only, never user input in the path.
    stored_filename = f"{uuid.uuid4().hex}{ext}"
    destination = get_upload_root() / stored_filename

    # Extra belt-and-suspenders: ensure resolved path stays inside upload root.
    upload_root = get_upload_root()
    if not str(destination.resolve()).startswith(str(upload_root)):
        raise UploadValidationError("Refusing to write outside the upload directory.")

    size = 0
    try:
        with destination.open("wb") as out:
            while True:
                chunk = await upload.read(CHUNK_SIZE)
                if not chunk:
                    break
                size += len(chunk)
                if size > max_bytes:
                    raise UploadValidationError(
                        f"File exceeds the {max_bytes // (1024 * 1024)} MB limit."
                    )
                out.write(chunk)
    except Exception:
        if destination.exists():
            destination.unlink(missing_ok=True)
        raise

    if size == 0:
        destination.unlink(missing_ok=True)
        raise UploadValidationError("Uploaded file is empty.")

    return stored_filename, original_basename, size
