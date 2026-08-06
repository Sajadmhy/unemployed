"""Outreach endpoints: who to contact about a job, and a draft to send them.

Generation is on demand (it costs one LLM call) and idempotent — asking twice
returns the stored contacts rather than duplicating them.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.outreach import build_contacts, draft_messages
from app.ai.retrieve import retrieve
from app.db.models import CandidateProfile, Contact, Job, JobRequirements
from app.db.session import get_db
from app.schemas import ContactUpdateIn

router = APIRouter(prefix="/outreach", tags=["outreach"])

STATUSES = ("todo", "found", "contacted", "replied")


@router.get("/{job_id}")
def list_contacts(job_id: int, db: Session = Depends(get_db)) -> list[dict]:
    rows = db.scalars(
        select(Contact).where(Contact.job_id == job_id).order_by(Contact.id)
    )
    return [_as_dict(c) for c in rows]


@router.post("/{job_id}/generate")
def generate(job_id: int, db: Session = Depends(get_db)) -> list[dict]:
    """Build the search links, then draft a grounded message for each."""
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    profile = db.scalar(select(CandidateProfile))
    if profile is None:
        raise HTTPException(status_code=400, detail="add your profile first")

    existing = {c.category: c for c in db.scalars(select(Contact).where(Contact.job_id == job_id))}
    plans = build_contacts(job, profile)

    # Search links are free and deterministic, so they are always refreshed.
    contacts: list[Contact] = []
    for plan in plans:
        row = existing.get(plan["category"]) or Contact(
            job_id=job_id, category=plan["category"]
        )
        row.label = plan["label"]
        row.search_url = plan["search_url"]
        db.add(row)
        contacts.append(row)
    db.commit()

    # Drafts cost an LLM call, so only write the ones that are still empty.
    needed = [c.category for c in contacts if not c.draft]
    if needed:
        requirements = db.get(JobRequirements, job_id)
        chunks = retrieve(
            db,
            job.title,
            {
                "required_skills": list(requirements.required_skills or []) if requirements else [],
                "preferred_skills": list(requirements.preferred_skills or []) if requirements else [],
                "responsibilities": list(requirements.responsibilities or []) if requirements else [],
            },
            k=5,
        )
        messages = draft_messages(job, profile, chunks, needed)
        for contact in contacts:
            if contact.category in messages:
                contact.draft = messages[contact.category]
        db.commit()

    for contact in contacts:
        db.refresh(contact)
    return [_as_dict(c) for c in contacts]


@router.put("/contact/{contact_id}")
def update_contact(
    contact_id: int, data: ContactUpdateIn, db: Session = Depends(get_db)
) -> dict:
    """Log who you found and where the conversation got to."""
    contact = db.get(Contact, contact_id)
    if contact is None:
        raise HTTPException(status_code=404, detail="contact not found")
    if data.status not in STATUSES:
        raise HTTPException(status_code=422, detail=f"status must be one of {STATUSES}")

    contact.name = data.name
    contact.profile_url = data.profile_url
    contact.status = data.status
    contact.notes = data.notes
    if data.draft:
        contact.draft = data.draft
    db.commit()
    db.refresh(contact)
    return _as_dict(contact)


def _as_dict(c: Contact) -> dict:
    return {
        "id": c.id,
        "job_id": c.job_id,
        "category": c.category,
        "label": c.label,
        "search_url": c.search_url,
        "draft": c.draft,
        "name": c.name,
        "profile_url": c.profile_url,
        "status": c.status,
        "notes": c.notes,
    }
