"""
Extract stills from an authorized live URL (CLI).

Examples:

    python -m scripts.extract_live_frames --url "https://www.youtube.com/watch?v=VIDEO" --count 4
    python -m scripts.extract_live_frames --url "https://explore.org/livecams/..." --label utopia --count 6
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

API_ROOT = Path(__file__).resolve().parents[1]
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from app.services.frame_extract import extract_live_frames
from app.services.live_capture import LiveCaptureError


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", required=True, help="Authorized live / media URL")
    parser.add_argument("--count", type=int, default=4)
    parser.add_argument("--interval", type=float, default=5.0, help="Seconds between frames")
    parser.add_argument("--label", default=None, help="Folder label prefix")
    parser.add_argument(
        "--authorized",
        action="store_true",
        help="Confirm you have permission to poll this source",
    )
    args = parser.parse_args()
    if not args.authorized:
        print("Pass --authorized to confirm permission.", file=sys.stderr)
        sys.exit(2)
    try:
        result = extract_live_frames(
            url=args.url,
            count=args.count,
            interval_seconds=args.interval,
            access_authorized=True,
            label=args.label,
        )
    except LiveCaptureError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
