"""
Vision analysis of a single extracted frame via Google Gemini.

Image inputs
------------
We send the JPEG bytes as an inline `Part` with mime_type image/jpeg.
Gemini "sees" that one still — not the whole video.

Structured outputs
------------------
`GenerateContentConfig(response_mime_type="application/json",
response_json_schema=...)` asks Gemini to return JSON matching our schema.

Validation
----------
We parse the JSON and validate with Pydantic (enum, confidence 0–1, text).
Missing keys / API failures raise errors — we never invent a successful
observation.
"""

from __future__ import annotations

import json
from enum import Enum
from pathlib import Path

from google.genai import types
from pydantic import BaseModel, Field, field_validator

from app.services.gemini_client import (
    GeminiAPIError,
    GeminiConfigError,
    get_gemini_client,
    get_gemini_model,
    raise_from_gemini_error,
)

# Re-export config error name used by the frames router.
VisionConfigError = GeminiConfigError
VisionAPIError = GeminiAPIError


class BehaviorLabel(str, Enum):
    eating = "eating"
    resting = "resting"
    walking = "walking"
    swimming = "swimming"
    climbing = "climbing"
    playing = "playing"
    not_visible = "not_visible"
    unknown = "unknown"


class BehaviorAnalysisResult(BaseModel):
    """Schema the vision model must return (structured JSON)."""

    behavior: BehaviorLabel
    animals_seen: list[str] = Field(
        default_factory=list,
        description=(
            "Visible animals/organisms in this frame (common names). "
            "Empty if none are clearly visible. Do not invent species."
        ),
    )
    description: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="Short description of what is visible in this single frame.",
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Model estimate only — not a calibrated scientific probability.",
    )
    visible_evidence: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="Concrete visual cues in the image that support the label.",
    )

    @field_validator("description", "visible_evidence")
    @classmethod
    def strip_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Text fields must not be empty.")
        return cleaned

    @field_validator("animals_seen")
    @classmethod
    def clean_animals(cls, value: list[str]) -> list[str]:
        cleaned: list[str] = []
        for item in value:
            name = (item or "").strip()
            if name and name not in cleaned:
                cleaned.append(name)
        return cleaned[:20]


SYSTEM_INSTRUCTIONS = """
You are a careful wildlife / camera observation assistant.

You receive ONE still image from a camera (land, zoo, or ocean). Rules:
1. Only describe what is actually visible in this single frame.
2. Never invent behaviors, animals, or details that are not clearly visible.
3. List animals_seen as common names of organisms clearly visible
   (fish, crabs, sea stars, birds, mammals, etc.). Use [] if none.
4. Prefer cautious labels (e.g. "bivalves", "small crustaceans") when
   species is unclear — do not guess rare species.
5. If the scene is dark, empty water, or no organism is clear, use behavior
   "not_visible" or "unknown" and animals_seen [].
6. A single frame cannot establish how long an action lasted.
7. confidence is your rough estimate between 0 and 1, not a scientific probability.
8. visible_evidence must list concrete visual cues from the image.
9. Choose exactly one behavior from:
   eating, resting, walking, swimming, climbing, playing, not_visible, unknown.
""".strip()


def _read_image_bytes(image_path: Path) -> tuple[bytes, str]:
    if not image_path.is_file():
        raise VisionAPIError(f"Frame image missing on disk: {image_path.name}")
    raw = image_path.read_bytes()
    if not raw:
        raise VisionAPIError("Frame image file is empty.")
    suffix = image_path.suffix.lower()
    mime = "image/jpeg" if suffix in {".jpg", ".jpeg"} else "image/png"
    return raw, mime


def analyze_frame_image(image_path: Path) -> BehaviorAnalysisResult:
    """
    Send one frame to Gemini and return validated structured JSON.
    """
    try:
        client = get_gemini_client()
    except GeminiConfigError:
        raise

    image_bytes, mime_type = _read_image_bytes(image_path)
    user_prompt = (
        "Analyze this camera still. List every animal/organism clearly visible "
        "in animals_seen (common names only; empty list if none). "
        "Classify behavior when an animal is visible; otherwise use not_visible "
        "or unknown. Do not invent life that is not in the image."
    )

    schema = BehaviorAnalysisResult.model_json_schema()

    try:
        response = client.models.generate_content(
            model=get_gemini_model(),
            contents=[
                types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                user_prompt,
            ],
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTIONS,
                response_mime_type="application/json",
                response_json_schema=schema,
            ),
        )
    except Exception as exc:
        raise_from_gemini_error(exc)

    raw_text = (response.text or "").strip()
    if not raw_text:
        raise VisionAPIError(
            "Gemini returned empty output. No observation was saved."
        )

    try:
        payload = json.loads(raw_text)
        return BehaviorAnalysisResult.model_validate(payload)
    except Exception as exc:
        raise VisionAPIError(
            f"Vision output failed validation: {exc}. No observation was saved."
        ) from exc
