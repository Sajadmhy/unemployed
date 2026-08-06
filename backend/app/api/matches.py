"""Ranked matches: the "what should I apply to today?" endpoint.

Filtered-out jobs are still queryable (`include_filtered=true`) because "why is
this job not in my list?" is a question the user is entitled to an answer to.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import Application, Job, JobRequirements, Match
from app.db.session import get_db
from app.schemas import JobOut, MatchOut

router = APIRouter(prefix="/matches", tags=["matches"])


@router.get("", response_model=list[MatchOut])
def list_matches(
    limit: int = 25,
    include_filtered: bool = False,
    min_score: float = 0.0,
    db: Session = Depends(get_db),
) -> list[dict]:
    """Top jobs by fit score, best first."""
    stmt = (
        select(Match, Job, Application.status)
        .join(Job, Match.job_id == Job.id)
        .outerjoin(Application, Application.job_id == Job.id)
        .where(Job.status == "active", Match.score >= min_score)
        .order_by(Match.score.desc())
        .limit(limit)
    )
    if not include_filtered:
        stmt = stmt.where(Match.hard_filtered.is_(False))

    return [
        {
            "job": JobOut.model_validate(job).model_dump(),
            "status": status or "todo",
            "tier": m.tier,
            "score": m.score,
            "f_semantic": m.f_semantic,
            "f_keyword": m.f_keyword,
            "f_required_cov": m.f_required_cov,
            "f_preferred_cov": m.f_preferred_cov,
            "f_preference_fit": m.f_preference_fit,
            "confidence": m.confidence,
            "hard_filtered": m.hard_filtered,
            "filter_reason": m.filter_reason,
            "why": m.why or {},
        }
        for m, job, status in db.execute(stmt).all()
    ]


@router.get("/stats")
def match_stats(db: Session = Depends(get_db)) -> dict:
    """How much of the active job pool has been scored, and how much survived."""
    active = db.scalar(
        select(func.count()).select_from(Job).where(Job.status == "active")
    )
    scored = db.scalar(
        select(func.count())
        .select_from(Match)
        .join(Job, Match.job_id == Job.id)
        .where(Job.status == "active")
    )
    filtered = db.scalar(
        select(func.count())
        .select_from(Match)
        .join(Job, Match.job_id == Job.id)
        .where(Job.status == "active", Match.hard_filtered.is_(True))
    )
    return {
        "active": active or 0,
        "scored": scored or 0,
        "filtered": filtered or 0,
        "rankable": (scored or 0) - (filtered or 0),
    }


@router.get("/{job_id}")
def match_detail(job_id: int, db: Session = Depends(get_db)) -> dict:
    """Score breakdown plus the extracted requirements for one job."""
    match = db.get(Match, job_id)
    job = db.get(Job, job_id)
    if match is None or job is None:
        raise HTTPException(status_code=404, detail="no match for this job")
    requirements = db.get(JobRequirements, job_id)
    return {
        "job": JobOut.model_validate(job).model_dump(),
        "score": match.score,
        "tier": match.tier,
        "f_semantic": match.f_semantic,
        "f_keyword": match.f_keyword,
        "f_required_cov": match.f_required_cov,
        "f_preferred_cov": match.f_preferred_cov,
        "f_preference_fit": match.f_preference_fit,
        "confidence": match.confidence,
        "hard_filtered": match.hard_filtered,
        "filter_reason": match.filter_reason,
        "why": match.why or {},
        "requirements": {
            "required_skills": list(requirements.required_skills or []) if requirements else [],
            "preferred_skills": list(requirements.preferred_skills or []) if requirements else [],
            "responsibilities": list(requirements.responsibilities or []) if requirements else [],
            "seniority": requirements.seniority if requirements else "",
            "min_years": requirements.min_years if requirements else 0,
        },
    }
