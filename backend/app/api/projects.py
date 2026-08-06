"""Project-idea endpoints: what to build to stand out for one job."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.match import CandidateIndex
from app.ai.project_idea import generate, skill_gaps
from app.db.models import Job, JobRequirements, KBChunk, ProjectIdea
from app.db.session import get_db

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("/{job_id}")
def latest(job_id: int, db: Session = Depends(get_db)) -> dict | None:
    idea = db.scalar(
        select(ProjectIdea)
        .where(ProjectIdea.job_id == job_id)
        .order_by(ProjectIdea.created_at.desc())
    )
    return _as_dict(idea) if idea else None


@router.post("/{job_id}/generate")
def create(job_id: int, db: Session = Depends(get_db)) -> dict:
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")

    chunks = list(db.scalars(select(KBChunk)))
    if not chunks:
        raise HTTPException(status_code=400, detail="import your experience first")
    candidate = CandidateIndex(chunks)

    row = db.get(JobRequirements, job_id)
    requirements = {
        "required_skills": list(row.required_skills or []) if row else [],
        "preferred_skills": list(row.preferred_skills or []) if row else [],
    }
    gaps = skill_gaps(requirements, candidate)
    strengths = sorted({t for c in chunks for t in (c.technologies or [])})

    idea = generate(job, requirements, gaps, strengths)
    if idea is None:
        raise HTTPException(
            status_code=422,
            detail="Could not produce a sufficiently specific idea — try again.",
        )

    stored = ProjectIdea(job_id=job_id, **idea)
    db.add(stored)
    db.commit()
    db.refresh(stored)
    return _as_dict(stored)


def _as_dict(idea: ProjectIdea) -> dict:
    return {
        "id": idea.id,
        "job_id": idea.job_id,
        "title": idea.title,
        "problem": idea.problem,
        "what_to_build": idea.what_to_build,
        "why_it_impresses": idea.why_it_impresses,
        "tech_stack": list(idea.tech_stack or []),
        "covers_gaps": list(idea.covers_gaps or []),
        "scope": idea.scope,
    }
