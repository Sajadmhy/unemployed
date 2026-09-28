"""Job endpoint: add a posting the user found, ready to tailor a resume to."""
import hashlib
import logging
from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.extract import extract_requirements
from app.db.models import Job, JobRequirements
from app.db.session import get_db
from app.schemas import ManualJobIn

log = logging.getLogger(__name__)
router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("/manual", status_code=201)
def create_manual_job(data: ManualJobIn, db: Session = Depends(get_db)) -> dict:
    """Add a job the user found elsewhere and extract its requirements.

    The requirements are what the resume is tailored to. Runs the LLM inline
    (~30s on a local model).
    """
    external_id = hashlib.sha256(
        f"{data.company}|{data.title}|{data.description[:500]}".encode()
    ).hexdigest()[:32]

    job = db.scalar(
        select(Job).where(Job.source == "manual", Job.external_id == external_id)
    )
    if job is None:
        job = Job(
            source="manual",
            external_id=external_id,
            company=data.company.strip(),
            title=data.title.strip(),
            location=data.location.strip(),
            remote="remote" in f"{data.location} {data.title}".lower(),
            description=data.description.strip(),
            apply_url=data.apply_url.strip(),
            posted_at=datetime.now(UTC),
            content_hash=hashlib.sha256(
                f"{data.title}\n{data.description}".encode()
            ).hexdigest(),
        )
        db.add(job)
        db.commit()
        db.refresh(job)

    _extract_requirements(db, job)
    return {"job_id": job.id}


def _extract_requirements(db: Session, job: Job) -> None:
    """Extract requirements, reusing a previous run when the posting is unchanged."""
    row = db.get(JobRequirements, job.id)
    if row is not None and row.source_hash == job.content_hash:
        return

    log.info("extracting: %s | %s", job.company, job.title[:60])
    data = extract_requirements(job.title, job.description)

    if row is None:
        row = JobRequirements(job_id=job.id)
        db.add(row)
    row.required_skills = data["required_skills"]
    row.preferred_skills = data["preferred_skills"]
    row.responsibilities = data["responsibilities"]
    row.seniority = data["seniority"]
    row.min_years = data["min_years"]
    row.confidence = data["confidence"]
    row.source_hash = job.content_hash
    db.commit()
