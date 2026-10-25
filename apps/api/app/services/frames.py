"""
Extract still frames from uploaded videos with OpenCV.

FPS (frames per second)
-----------------------
A video is a sequence of images. FPS is how many of those images play each
second. A 30 FPS clip shows 30 pictures every second.

Why sample instead of analyzing every frame?
--------------------------------------------
A 3-minute video at 30 FPS has 3 × 60 × 30 = 5,400 frames. Sending all of them
to an AI model would be slow and expensive. Sampling one frame every 15 seconds
(and capping at 12) gives a sparse timeline that is usually enough to spot
visible behaviors later — far cheaper than full-video analysis.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import cv2

from app.config import get_settings
from app.services.storage import get_upload_root


class FrameExtractionError(ValueError):
    """Raised when a video cannot be opened or no frames can be read."""


@dataclass(frozen=True)
class ExtractedFrame:
    frame_index: int
    timestamp_seconds: float
    filename: str
    absolute_path: Path


def get_frame_root() -> Path:
    settings = get_settings()
    root = Path(settings.frame_dir).resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def video_frame_dir(video_id: int) -> Path:
    path = get_frame_root() / f"video_{video_id}"
    path.mkdir(parents=True, exist_ok=True)
    # Stay inside frame root (path traversal defense).
    if not str(path.resolve()).startswith(str(get_frame_root())):
        raise FrameExtractionError("Refusing to write frames outside the frame directory.")
    return path.resolve()


def resolve_video_path(stored_filename: str) -> Path:
    path = (get_upload_root() / stored_filename).resolve()
    upload_root = get_upload_root()
    if not str(path).startswith(str(upload_root)):
        raise FrameExtractionError("Video path escapes the upload directory.")
    if not path.is_file():
        raise FrameExtractionError(f"Video file is missing on disk: {stored_filename}")
    return path


def resolve_frame_path(video_id: int, stored_filename: str) -> Path:
    """Resolve a frame JPEG path and ensure it stays under the frames root."""
    basename = Path(stored_filename.replace("\\", "/")).name
    path = (video_frame_dir(video_id) / basename).resolve()
    if not str(path).startswith(str(get_frame_root())):
        raise FrameExtractionError("Frame path escapes the frame directory.")
    if not path.is_file():
        raise FrameExtractionError(f"Frame image is missing on disk: {basename}")
    return path



def _resize_frame(frame, max_dimension: int):
    height, width = frame.shape[:2]
    longest = max(height, width)
    if longest <= max_dimension:
        return frame
    scale = max_dimension / float(longest)
    new_size = (int(width * scale), int(height * scale))
    return cv2.resize(frame, new_size, interpolation=cv2.INTER_AREA)


def _planned_timestamps(duration_seconds: float, interval: float, max_frames: int) -> list[float]:
    """Build timestamps at 0, interval, 2*interval, … within the video, capped."""
    if duration_seconds <= 0:
        return [0.0]

    timestamps: list[float] = []
    t = 0.0
    # Use a tiny epsilon so the last sample can sit just before the end.
    end = max(duration_seconds - 0.05, 0.0)
    while len(timestamps) < max_frames and t <= end + 1e-6:
        timestamps.append(round(min(t, end), 3))
        t += interval

    if not timestamps:
        timestamps = [0.0]
    return timestamps


def extract_frames_for_video(video_id: int, stored_filename: str) -> list[ExtractedFrame]:
    """
    Read a video from local storage and write JPEG frames to disk.

    Returns metadata for each saved frame (does not touch the database).
    """
    settings = get_settings()
    video_path = resolve_video_path(stored_filename)
    out_dir = video_frame_dir(video_id)

    capture = cv2.VideoCapture(str(video_path))
    if not capture.isOpened():
        capture.release()
        raise FrameExtractionError(
            "Could not open video. The file may be corrupted or an unsupported codec."
        )

    try:
        fps = float(capture.get(cv2.CAP_PROP_FPS) or 0.0)
        frame_count = float(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0.0)
        if fps > 0 and frame_count > 0:
            duration = frame_count / fps
        else:
            # Fallback: seek near the end to estimate duration.
            capture.set(cv2.CAP_PROP_POS_AVI_RATIO, 1.0)
            duration_ms = float(capture.get(cv2.CAP_PROP_POS_MSEC) or 0.0)
            duration = max(duration_ms / 1000.0, 0.0)
            capture.set(cv2.CAP_PROP_POS_FRAMES, 0)

        timestamps = _planned_timestamps(
            duration_seconds=duration,
            interval=settings.frame_interval_seconds,
            max_frames=settings.max_frames_per_video,
        )

        extracted: list[ExtractedFrame] = []
        for index, timestamp in enumerate(timestamps):
            capture.set(cv2.CAP_PROP_POS_MSEC, timestamp * 1000.0)
            ok, frame = capture.read()
            if not ok or frame is None:
                # Try nearest frame by frame index if msec seek failed.
                if fps > 0:
                    capture.set(cv2.CAP_PROP_POS_FRAMES, max(int(timestamp * fps), 0))
                    ok, frame = capture.read()
            if not ok or frame is None:
                continue

            resized = _resize_frame(frame, settings.frame_max_dimension)
            filename = f"frame_{index:02d}_{timestamp:.3f}s.jpg"
            absolute = out_dir / filename
            if not cv2.imwrite(str(absolute), resized):
                raise FrameExtractionError(f"Failed to write frame image: {filename}")

            extracted.append(
                ExtractedFrame(
                    frame_index=index,
                    timestamp_seconds=timestamp,
                    filename=filename,
                    absolute_path=absolute,
                )
            )

        if not extracted:
            raise FrameExtractionError(
                "No frames could be read from this video. It may be empty or corrupted."
            )

        return extracted
    finally:
        capture.release()
