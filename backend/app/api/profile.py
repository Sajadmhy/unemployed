"""Candidate profile: a single-row identity for the KB owner.

Kept minimal in Sprint 1 — a resume needs an owner (name/contact) later. GET
returns the row (creating an empty one on first call); PUT updates it.
"""
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import CandidateProfile
from app.db.session import get_db
from app.schemas import ProfileIn, ProfileOut

router = APIRouter(prefix="/profile", tags=["profile"])


def _get_or_create(db: Session) -> CandidateProfile:
    profile = db.scalar(select(CandidateProfile).limit(1))
    if profile is None:
        profile = CandidateProfile()
        db.add(profile)
        db.commit()
        db.refresh(profile)
    return profile


@router.get("", response_model=ProfileOut)
def get_profile(db: Session = Depends(get_db)) -> CandidateProfile:
    return _get_or_create(db)


@router.put("", response_model=ProfileOut)
def update_profile(data: ProfileIn, db: Session = Depends(get_db)) -> CandidateProfile:
    profile = _get_or_create(db)
    for field, value in data.model_dump().items():
        setattr(profile, field, value)
    db.commit()
    db.refresh(profile)
    return profile
