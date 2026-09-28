"""Pydantic request/response models for the API boundary."""
from datetime import datetime

from pydantic import BaseModel, Field


# ---- Knowledge base ----------------------------------------------------------
class AccomplishmentIn(BaseModel):
    """One achievement. Becomes exactly one KB chunk."""

    text: str = Field(min_length=3)
    technologies: list[str] = []
    skills: list[str] = []
    impact: str | None = None


class KBItemIn(BaseModel):
    """A project/experience/etc. Its accomplishments are split into chunks."""

    type: str
    title: str
    context: str | None = None
    company: str | None = None
    date_range: str | None = None
    accomplishments: list[AccomplishmentIn] = Field(min_length=1)


class KBChunkOut(BaseModel):
    id: int
    type: str
    title: str
    context: str | None
    company: str | None
    date_range: str | None
    accomplishment: str
    technologies: list[str]
    skills: list[str]
    impact: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class SearchResult(KBChunkOut):
    similarity: float


class ChunkIn(BaseModel):
    """A single chunk — the shape of a parsed proposal AND a reviewed save."""

    type: str = "experience"
    title: str
    context: str | None = None
    company: str | None = None
    date_range: str | None = None
    accomplishment: str = Field(min_length=1)
    technologies: list[str] = []
    skills: list[str] = []
    impact: str | None = None


# ---- Jobs --------------------------------------------------------------------
class ManualJobIn(BaseModel):
    """A job the user found themselves and pasted in."""

    title: str = Field(min_length=2)
    company: str = Field(min_length=1)
    description: str = Field(min_length=50)
    location: str = ""
    apply_url: str = ""


# ---- Profile -----------------------------------------------------------------
class ProfileIn(BaseModel):
    name: str = ""
    email: str = ""
    phone: str = ""
    location: str = ""
    links: dict[str, str] = {}
    summary: str = ""
    education: str = ""
    college: str = ""


class ProfileOut(ProfileIn):
    id: int
    model_config = {"from_attributes": True}
