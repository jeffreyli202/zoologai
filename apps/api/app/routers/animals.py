from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Animal
from app.schemas import AnimalCreate, AnimalRead, AnimalUpdate

router = APIRouter(prefix="/animals", tags=["animals"])


@router.post(
    "",
    response_model=AnimalRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create an animal",
)
def create_animal(payload: AnimalCreate, db: Session = Depends(get_db)) -> Animal:
    animal = Animal(
        name=payload.name.strip(),
        species=payload.species.strip(),
        description=payload.description.strip() if payload.description else None,
    )
    db.add(animal)
    db.commit()
    db.refresh(animal)
    return animal


@router.get(
    "",
    response_model=list[AnimalRead],
    summary="List animals",
)
def list_animals(db: Session = Depends(get_db)) -> list[Animal]:
    return list(db.scalars(select(Animal).order_by(Animal.id.asc())).all())


@router.get(
    "/{animal_id}",
    response_model=AnimalRead,
    summary="Get one animal",
)
def get_animal(animal_id: int, db: Session = Depends(get_db)) -> Animal:
    animal = db.get(Animal, animal_id)
    if animal is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Animal with id {animal_id} was not found.",
        )
    return animal


@router.patch(
    "/{animal_id}",
    response_model=AnimalRead,
    summary="Update an animal",
)
def update_animal(
    animal_id: int,
    payload: AnimalUpdate,
    db: Session = Depends(get_db),
) -> Animal:
    animal = db.get(Animal, animal_id)
    if animal is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Animal with id {animal_id} was not found.",
        )

    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields provided to update.",
        )

    for field, value in updates.items():
        if isinstance(value, str):
            value = value.strip()
        setattr(animal, field, value)

    db.commit()
    db.refresh(animal)
    return animal


@router.delete(
    "/{animal_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an animal",
)
def delete_animal(animal_id: int, db: Session = Depends(get_db)) -> Response:
    animal = db.get(Animal, animal_id)
    if animal is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Animal with id {animal_id} was not found.",
        )

    db.delete(animal)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
