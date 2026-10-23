from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class AnimalCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, examples=["Mara"])
    species: str = Field(..., min_length=1, max_length=100, examples=["Panthera leo"])
    description: Optional[str] = Field(
        default=None,
        max_length=5000,
        examples=["Adult lioness in the savannah enclosure."],
    )


class AnimalUpdate(BaseModel):
    """All fields optional — only send what you want to change."""

    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    species: Optional[str] = Field(default=None, min_length=1, max_length=100)
    description: Optional[str] = Field(default=None, max_length=5000)


class AnimalRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    species: str
    description: Optional[str] = None
