"""
Seed the database with one example animal (Amur Carp — fish demo profile).

Run from apps/api (with the venv active):

    python -m scripts.seed
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure apps/api is on sys.path when run as a module or script.
API_ROOT = Path(__file__).resolve().parents[1]
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from sqlalchemy import select

from app.database import SessionLocal
from app.models import Animal


EXAMPLE_ANIMAL = {
    "name": "Amur Carp",
    "species": "Cyprinus rubrofuscus",
    "description": (
        "Example fish profile for local development. Hourly journals are only "
        "written when this fish is actually observed — empty/not_visible frames "
        "do not create a journal."
    ),
}


def seed() -> None:
    db = SessionLocal()
    try:
        existing = db.scalar(
            select(Animal).where(
                Animal.name == EXAMPLE_ANIMAL["name"],
                Animal.species == EXAMPLE_ANIMAL["species"],
            )
        )
        if existing is not None:
            print(f"Seed animal already exists (id={existing.id}): {existing.name}")
            return

        animal = Animal(**EXAMPLE_ANIMAL)
        db.add(animal)
        db.commit()
        db.refresh(animal)
        print(f"Created seed animal (id={animal.id}): {animal.name} ({animal.species})")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
