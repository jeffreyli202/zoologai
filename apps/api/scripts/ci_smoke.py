"""
Lightweight CI smoke checks (no live Gemini / OpenCV capture).

Run from apps/api with dependencies installed:
  python scripts/ci_smoke.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# Allow `python scripts/ci_smoke.py` from apps/api (script dir is not on PYTHONPATH).
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


def main() -> int:
    from app.main import app

    assert app.title, "FastAPI app missing title"

    # Prefer OpenAPI paths — FastAPI 0.149+ nests routers as _IncludedRouter.
    paths = set(app.openapi().get("paths", {}).keys())

    required = {
        "/health",
        "/animals",
        "/videos",
        "/observations",
        "/journals",
        "/analytics/behaviors",
        "/cameras",
    }
    missing = sorted(required - paths)
    if missing:
        print("Missing expected routes:", ", ".join(missing), file=sys.stderr)
        return 1

    print(f"OK — {len(paths)} OpenAPI paths; required endpoints present.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
