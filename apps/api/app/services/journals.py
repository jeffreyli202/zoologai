"""
Generate observation journals from saved Observation rows using Gemini.

Default bucket is one UTC hour. Persistent memory: observations and journals
live in SQLite — the agent reloads Observation rows for the animal and period,
then summarizes only those facts.
"""

from __future__ import annotations

import json
from datetime import date
from typing import Optional

from google.genai import types
from pydantic import BaseModel, Field, field_validator

from app.services.gemini_client import (
    GeminiAPIError,
    GeminiConfigError,
    get_gemini_client,
    get_gemini_model,
    raise_from_gemini_error,
)

# Frames where nothing was seen — never enough on their own for a new journal.
NOT_OBSERVED_BEHAVIORS = frozenset({"not_visible"})

_FISH_HINTS = (
    "fish",
    "carp",
    "cyprinus",
    "salmon",
    "trout",
    "bass",
    "shark",
    "ray",
    "eel",
    "tuna",
    "cod",
    "goldfish",
    "koi",
    "goby",
    "grouper",
    "snapper",
    "halibut",
    "flounder",
    "anchovy",
    "herring",
    "mackerel",
    "sturgeon",
    "pike",
    "perch",
    "catfish",
    "tilapia",
)


def is_fish_animal(*, name: str = "", species: str = "") -> bool:
    text = f"{name} {species}".lower()
    return any(hint in text for hint in _FISH_HINTS)


def _obs_behavior(obs: object) -> str:
    if isinstance(obs, dict):
        return str(obs.get("behavior") or "").strip().lower()
    return str(getattr(obs, "behavior", "") or "").strip().lower()


def filter_sightings_for_journal(
    observations: list,
    *,
    animal_name: str = "",
    animal_species: str = "",
) -> list:
    """
    Drop not_visible rows before journal generation.

    For fish: if nothing was actually observed (only dark / empty frames),
    return [] so callers skip creating a journal.
    """
    sightings = [
        obs for obs in observations if _obs_behavior(obs) not in NOT_OBSERVED_BEHAVIORS
    ]
    if is_fish_animal(name=animal_name, species=animal_species):
        return sightings
    # Non-fish: still require at least one real sighting for a new journal.
    return sightings


class JournalDraft(BaseModel):
    """Structured journal sections validated before we assemble saved text."""

    overview: str = Field(..., min_length=1, max_length=2000)
    observed_behaviors: str = Field(..., min_length=1, max_length=3000)
    notable_events: str = Field(..., min_length=1, max_length=3000)
    observed_facts: str = Field(
        ...,
        min_length=1,
        max_length=3000,
        description="Strict restatement of recorded observation facts only.",
    )
    possible_interpretations: str = Field(
        ...,
        min_length=1,
        max_length=3000,
        description="Clearly tentative readings; must not be phrased as facts.",
    )
    supporting_observation_ids: list[int] = Field(default_factory=list)

    @field_validator(
        "overview",
        "observed_behaviors",
        "notable_events",
        "observed_facts",
        "possible_interpretations",
    )
    @classmethod
    def strip_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Journal section must not be empty.")
        return cleaned


JOURNAL_INSTRUCTIONS = """
You write engaging but scientifically cautious camera observation journals.

Tone: warm and readable, never sensational. Prefer plain language.

Required sections (return JSON matching the schema):
- overview: short summary for this time window grounded only in the records
- observed_behaviors: behaviors that appear in the records (group/list clearly)
- notable_events: anything noteworthy that is still supported by the records
- observed_facts: only restated recorded facts (behavior, evidence, timestamps,
  animals_seen when present)
- possible_interpretations: optional cautious readings — label uncertainty;
  never present these as confirmed
- supporting_observation_ids: IDs from the input list that you actually used

Hard rules:
1. Use ONLY the observation records provided. Do not invent animals, behaviors,
   times, or events that are not in the data.
2. If evidence is thin, say so. Prefer "not enough evidence" over guessing.
3. Confidence values are rough model estimates, not scientific probabilities.
4. A single frame cannot prove how long a behavior lasted — avoid duration claims.
5. Clearly separate facts from interpretations in the dedicated fields.
6. supporting_observation_ids must be a subset of the provided observation IDs.
7. If most frames are not_visible / unknown / dark, say visibility was limited.
8. For an hourly journal, stay scoped to that single hour — do not invent a full day.
""".strip()


def assemble_journal_content(draft: JournalDraft) -> str:
    """Turn structured model output into readable saved text."""
    ids = ", ".join(str(i) for i in draft.supporting_observation_ids) or "none"
    return (
        "## Overview\n"
        f"{draft.overview}\n\n"
        "## Observed behaviors\n"
        f"{draft.observed_behaviors}\n\n"
        "## Notable events\n"
        f"{draft.notable_events}\n\n"
        "## Observed facts\n"
        f"{draft.observed_facts}\n\n"
        "## Possible interpretations\n"
        "_These are tentative and not confirmed by direct evidence alone._\n"
        f"{draft.possible_interpretations}\n\n"
        "## Supporting observation IDs\n"
        f"{ids}"
    )


def generate_daily_journal(
    *,
    animal_name: str,
    animal_species: str,
    journal_date: date,
    observations: list[dict],
    hour: Optional[int] = None,
) -> tuple[str, list[int]]:
    """
    Call Gemini with observation records; return (content text, observation ids).

    hour: UTC hour 0–23 for an hourly journal; None/-1 for a full-day summary.
    """
    if not observations:
        raise GeminiAPIError(
            "No observations were provided for this period. "
            "Capture or analyze frames first, then generate a journal."
        )

    allowed_ids = {int(item["id"]) for item in observations if "id" in item}
    is_hourly = hour is not None and 0 <= hour <= 23

    try:
        client = get_gemini_client()
    except GeminiConfigError:
        raise

    period = {
        "animal_name": animal_name,
        "species": animal_species,
        "date": journal_date.isoformat(),
        "observations": observations,
    }
    if is_hourly:
        period["hour_utc"] = hour
        period["period"] = f"{journal_date.isoformat()} {hour:02d}:00–{hour:02d}:59 UTC"
        prompt_lead = (
            "Write an hourly camera journal for this single UTC hour using only "
            "these observation records."
        )
    else:
        period["period"] = f"full day {journal_date.isoformat()} UTC"
        prompt_lead = (
            "Write the daily journal for this animal using only these observation "
            "records."
        )

    facts = json.dumps(period, ensure_ascii=True, indent=2)
    prompt = (
        f"{prompt_lead} Preserve supporting observation IDs for traceability."
        f"\n\n{facts}"
    )

    schema = JournalDraft.model_json_schema()

    try:
        response = client.models.generate_content(
            model=get_gemini_model(),
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=JOURNAL_INSTRUCTIONS,
                response_mime_type="application/json",
                response_json_schema=schema,
            ),
        )
    except Exception as exc:
        raise_from_gemini_error(exc)

    raw_text = (response.text or "").strip()
    if not raw_text:
        raise GeminiAPIError("Gemini returned empty journal output.")

    try:
        payload = json.loads(raw_text)
        draft = JournalDraft.model_validate(payload)
    except Exception as exc:
        raise GeminiAPIError(
            f"Journal output failed validation: {exc}. Nothing was saved."
        ) from exc

    # Never trust invented IDs — keep only those that exist in the DB payload.
    used_ids = sorted(
        {oid for oid in draft.supporting_observation_ids if oid in allowed_ids}
    )
    if not used_ids:
        used_ids = sorted(allowed_ids)

    draft = draft.model_copy(update={"supporting_observation_ids": used_ids})
    return assemble_journal_content(draft), used_ids


# Backwards-compatible name used by older imports/tests.
def generate_daily_journal_text(
    *,
    animal_name: str,
    animal_species: str,
    journal_date: date,
    observations: list[dict],
    hour: Optional[int] = None,
) -> str:
    content, _ids = generate_daily_journal(
        animal_name=animal_name,
        animal_species=animal_species,
        journal_date=journal_date,
        observations=observations,
        hour=hour,
    )
    return content
