"""Create a short synthetic MP4 for local frame-extraction tests."""

from __future__ import annotations

import sys
from pathlib import Path

import cv2
import numpy as np

API_ROOT = Path(__file__).resolve().parents[1]
OUT = API_ROOT / "uploads" / "videos" / "_sample_extract.mp4"


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fps = 10
    width, height = 320, 240
    # 50 seconds → expect frames at 0,15,30,45 (4 frames under the 12 cap)
    seconds = 50
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(OUT), fourcc, fps, (width, height))
    if not writer.isOpened():
        print("Could not open VideoWriter", file=sys.stderr)
        sys.exit(1)

    total = seconds * fps
    for i in range(total):
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        # Color shifts over time so sampled frames look different.
        frame[:, :] = ((i * 3) % 255, 60, 120)
        cv2.putText(
            frame,
            f"t={i / fps:.1f}s",
            (40, 120),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (255, 255, 255),
            2,
        )
        writer.write(frame)
    writer.release()
    print(f"Wrote {OUT} ({seconds}s @ {fps} FPS)")


if __name__ == "__main__":
    main()
