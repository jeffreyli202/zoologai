"""
Import public Lincoln Park Zoo–area observations from iNaturalist and
transform them into ZooLog animals, observations, and hourly journals.

Source: https://api.inaturalist.org (public, attribution required).
We do not invent behaviors — when iNaturalist has no activity cue, behavior
is stored as "unknown" with the real taxon / place / observation id as evidence.

Run from apps/api (venv active):

    python -m scripts.seed_zoo_inat
"""

from __future__ import annotations

import json
import re
import sys
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

API_ROOT = Path(__file__).resolve().parents[1]
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from sqlalchemy import select

from app.database import SessionLocal
from app.models import Animal, DailyJournal, Observation

INAT_BASE = "https://api.inaturalist.org/v1/observations"
# Lincoln Park Zoo approx. center (public park / zoo grounds).
LPZ_LAT = 41.921
LPZ_LNG = -87.633
USER_AGENT = "ZooLogAI/0.1 (local demo seed; contact=local-dev)"

BEHAVIOR_CUES: list[tuple[str, str]] = [
    (r"\b(eat|eating|feed|feeding|forag)\w*\b", "eating"),
    (r"\b(swim|swimming|diving|dive)\w*\b", "swimming"),
    (r"\b(climb|climbing)\w*\b", "climbing"),
    (r"\b(play|playing|wrestl)\w*\b", "playing"),
    (r"\b(walk|walking|run|running|mov)\w*\b", "walking"),
    (r"\b(rest|resting|sleep|sleeping|perch|sit|sitting|lie|lying)\w*\b", "resting"),
]


def _fetch(params: dict) -> dict:
    query = urllib.parse.urlencode(params, doseq=True)
    req = urllib.request.Request(
        f"{INAT_BASE}?{query}",
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_lpz_batches() -> list[dict]:
    """Captive vertebrates + free-ranging vertebrates on zoo grounds."""
    common = {
        "lat": LPZ_LAT,
        "lng": LPZ_LNG,
        "radius": 1,
        "per_page": 100,
        "order": "desc",
        "order_by": "observed_on",
        "photos": "true",
    }
    captive = _fetch(
        {
            **common,
            "captive": "true",
            "taxon_id": 1,  # Animalia
        }
    )
    wild = _fetch(
        {
            **common,
            "captive": "false",
            "iconic_taxa[]": ["Mammalia", "Aves", "Reptilia", "Amphibia"],
            "quality_grade": "research",
        }
    )
    by_id: dict[int, dict] = {}
    for batch in (captive.get("results") or [], wild.get("results") or []):
        for item in batch:
            oid = item.get("id")
            if oid is not None:
                by_id[int(oid)] = item
    return list(by_id.values())


def _common_name(taxon: dict | None) -> str | None:
    if not taxon:
        return None
    name = (taxon.get("preferred_common_name") or "").strip()
    return name or None


def _scientific_name(taxon: dict | None) -> str | None:
    if not taxon:
        return None
    name = (taxon.get("name") or "").strip()
    return name or None


def _parse_observed_at(item: dict) -> datetime | None:
    raw = item.get("time_observed_at") or item.get("observed_on")
    if not raw:
        return None
    text = str(raw).strip()
    try:
        if "T" in text:
            # iNat returns e.g. 2026-10-18T15:22:03-05:00
            dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
            return dt.astimezone(timezone.utc)
        # Date only — noon UTC so the hour bucket is stable.
        day = datetime.fromisoformat(text).date()
        return datetime(day.year, day.month, day.day, 12, 0, tzinfo=timezone.utc)
    except ValueError:
        return None


def infer_behavior(description: str | None) -> str:
    """Map free-text notes to our enum; default unknown (never invent)."""
    text = (description or "").lower()
    if not text:
        return "unknown"
    for pattern, label in BEHAVIOR_CUES:
        if re.search(pattern, text, flags=re.IGNORECASE):
            return label
    return "unknown"


def transform_record(item: dict) -> dict | None:
    taxon = item.get("taxon") or {}
    common = _common_name(taxon)
    scientific = _scientific_name(taxon)
    if not common or not scientific:
        return None
    # Skip ultra-generic ranks.
    if common.lower() in {"animals", "birds", "mammals", "plants"}:
        return None
    observed_at = _parse_observed_at(item)
    if observed_at is None:
        return None

    inat_id = int(item["id"])
    place = (item.get("place_guess") or "Lincoln Park Zoo area").strip()
    desc = (item.get("description") or "").strip()
    captive = bool(item.get("captive"))
    grade = item.get("quality_grade") or "casual"
    photo_url = None
    photos = item.get("photos") or []
    if photos:
        photo_url = photos[0].get("url") or photos[0].get("original_url")

    behavior = infer_behavior(desc)
    evidence_bits = [
        f"iNaturalist observation #{inat_id}",
        f"place: {place}",
        f"captive={captive}",
        f"quality_grade={grade}",
        f"taxon: {scientific}",
    ]
    if photo_url:
        evidence_bits.append(f"photo: {photo_url}")

    description = (
        f"{'Captive' if captive else 'Free-ranging'} {common} recorded near "
        f"Lincoln Park Zoo ({place})."
    )
    if desc:
        description = f"{description} Observer note: {desc[:400]}"

    confidence = 0.78 if grade == "research" else 0.55

    return {
        "inat_id": inat_id,
        "animal_name": common[:100],
        "species": scientific[:100],
        "animal_description": (
            f"{common} ({scientific}). Profile built from public iNaturalist "
            f"records around Lincoln Park Zoo, Chicago."
        ),
        "observed_at": observed_at,
        "behavior": behavior,
        "description": description[:2000],
        "visible_evidence": "; ".join(evidence_bits)[:2000],
        "confidence": confidence,
        "captive": captive,
    }


def assemble_hourly_journal(
    animal_name: str, species: str, day, hour: int, rows: list[Observation]
) -> str:
    ids = [str(o.id) for o in rows]
    facts = []
    for o in rows:
        facts.append(
            f"- [{o.observed_at.isoformat()}] behavior={o.behavior}; "
            f"{(o.description or '')[:180]}"
        )
    facts_block = "\n".join(facts)
    return (
        f"## Overview\n"
        f"Hourly record for {animal_name} ({species}) on {day.isoformat()} "
        f"{hour:02d}:00–{hour:02d}:59 UTC, assembled from imported iNaturalist "
        f"observations. No behaviors were invented beyond keyword cues in "
        f"observer notes (otherwise unknown).\n\n"
        f"## Observed behaviors\n"
        f"{', '.join(sorted({o.behavior for o in rows}))}\n\n"
        f"## Notable events\n"
        f"{len(rows)} imported sighting(s) in this UTC hour.\n\n"
        f"## Observed facts\n"
        f"{facts_block}\n\n"
        f"## Possible interpretations\n"
        f"_These are tentative and not confirmed by direct evidence alone._\n"
        f"Public community sightings near a zoo may include free-ranging wildlife "
        f"and captive animals photographed by visitors; treat labels as "
        f"presence/activity samples, not a continuous welfare log.\n\n"
        f"## Supporting observation IDs\n"
        f"{', '.join(ids)}"
    )


def seed(limit_animals: int = 25, limit_observations: int = 120) -> None:
    print("Fetching Lincoln Park Zoo-area observations from iNaturalist...")
    raw = fetch_lpz_batches()
    transformed = []
    for item in raw:
        row = transform_record(item)
        if row is not None:
            transformed.append(row)

    # Prefer captive zoo collection animals, then fill with free-ranging.
    captive_rows = [r for r in transformed if r["captive"]]
    wild_rows = [r for r in transformed if not r["captive"]]
    ordered = captive_rows + wild_rows

    # Cap species count (most frequent first among selected rows).
    species_counts: dict[str, int] = defaultdict(int)
    for r in ordered:
        species_counts[r["species"]] += 1
    top_species = {
        s
        for s, _ in sorted(species_counts.items(), key=lambda kv: (-kv[1], kv[0]))[
            :limit_animals
        ]
    }
    selected = [r for r in ordered if r["species"] in top_species][:limit_observations]
    print(
        f"Transformed {len(transformed)} usable rows -> "
        f"seeding {len(selected)} observations across {len(top_species)} species."
    )

    db = SessionLocal()
    try:
        animal_by_species: dict[str, Animal] = {}
        for r in selected:
            sp = r["species"]
            if sp in animal_by_species:
                continue
            existing = db.scalar(
                select(Animal).where(
                    Animal.name == r["animal_name"],
                    Animal.species == sp,
                )
            )
            if existing is not None:
                animal_by_species[sp] = existing
                continue
            animal = Animal(
                name=r["animal_name"],
                species=sp,
                description=r["animal_description"],
            )
            db.add(animal)
            db.flush()
            animal_by_species[sp] = animal
            print(f"  animal id={animal.id} {animal.name} ({animal.species})")

        db.commit()

        # Idempotent-ish: skip if evidence already cites this iNat id.
        existing_evidence = {
            (o.visible_evidence or "")
            for o in db.scalars(select(Observation)).all()
        }
        created_obs: list[Observation] = []
        for r in selected:
            marker = f"iNaturalist observation #{r['inat_id']}"
            if any(marker in ev for ev in existing_evidence):
                continue
            animal = animal_by_species[r["species"]]
            obs = Observation(
                animal_id=animal.id,
                observed_at=r["observed_at"],
                video_timestamp_seconds=0.0,
                behavior=r["behavior"],
                description=r["description"],
                visible_evidence=r["visible_evidence"],
                confidence=r["confidence"],
            )
            db.add(obs)
            created_obs.append(obs)
            existing_evidence.add(r["visible_evidence"])

        db.commit()
        for o in created_obs:
            db.refresh(o)
        print(f"Created {len(created_obs)} observations.")

        # Hourly journals from newly created observations (facts only).
        buckets: dict[tuple[int, object, int], list[Observation]] = defaultdict(list)
        for o in created_obs:
            dt = o.observed_at
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            dt = dt.astimezone(timezone.utc)
            buckets[(o.animal_id, dt.date(), dt.hour)].append(o)

        journals_created = 0
        for (animal_id, day, hour), rows in buckets.items():
            existing = db.scalar(
                select(DailyJournal).where(
                    DailyJournal.animal_id == animal_id,
                    DailyJournal.date == day,
                    DailyJournal.hour == hour,
                )
            )
            if existing is not None:
                continue
            animal = db.get(Animal, animal_id)
            if animal is None:
                continue
            content = assemble_hourly_journal(
                animal.name, animal.species, day, hour, rows
            )
            db.add(
                DailyJournal(
                    animal_id=animal_id,
                    date=day,
                    hour=hour,
                    content=content,
                    source_observation_ids=json.dumps([o.id for o in rows]),
                    updated_at=datetime.now(timezone.utc),
                )
            )
            journals_created += 1
        db.commit()
        print(f"Created {journals_created} hourly journals.")
        print("Done. Attribution: observations © iNaturalist contributors.")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
