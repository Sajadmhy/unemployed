"""Application status: the user's own progress through the funnel.

Deliberately dumb storage. The value is that yesterday's decisions survive today's
re-ingest, so the daily list is "what's left to do" rather than the same 25 jobs
every morning.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import Application, Job
from app.db.session import get_db
from app.schemas import ApplicationIn

router = APIRouter(prefix="/applications", tags=["applications"])

STATUSES = ("todo", "resume_ready", "applied", "outreach_sent", "closed")


@router.get("")
def list_applications(db: Session = Depends(get_db)) -> list[dict]:
    rows = db.execute(
        select(Application, Job).join(Job, Application.job_id == Job.id)
    ).all()
    return [
        {
            "job_id": a.job_id,
            "status": a.status,
            "notes": a.notes,
            "updated_at": a.updated_at.isoformat(),
            "title": j.title,
            "company": j.company,
        }
        for a, j in rows
    ]


@router.get("/stats")
def stats(db: Session = Depends(get_db)) -> dict:
    counts = dict(
        db.execute(
            select(Application.status, func.count()).group_by(Application.status)
        ).all()
    )
    return {status: counts.get(status, 0) for status in STATUSES}


@router.put("/{job_id}")
def set_status(job_id: int, data: ApplicationIn, db: Session = Depends(get_db)) -> dict:
    if data.status not in STATUSES:
        raise HTTPException(status_code=422, detail=f"status must be one of {STATUSES}")
    if db.get(Job, job_id) is None:
        raise HTTPException(status_code=404, detail="job not found")

    app_row = db.get(Application, job_id) or Application(job_id=job_id)
    app_row.status = data.status
    app_row.notes = data.notes
    db.add(app_row)
    db.commit()
    db.refresh(app_row)
    return {
        "job_id": app_row.job_id,
        "status": app_row.status,
        "notes": app_row.notes,
        "updated_at": app_row.updated_at.isoformat(),
    }
