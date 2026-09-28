"""Resume endpoints: generate a tailored resume for a job, then download it.

Generation is on demand, never batch: it costs LLM time and, more importantly,
every resume is meant to be reviewed by a human before it is sent anywhere.
"""
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai import ats, pdf
from app.ai.generate_resume import generate
from app.ai.retrieve import retrieve_all
from app.db.models import CandidateProfile, Job, JobRequirements, Resume
from app.db.retention import purge_expired_resumes
from app.db.session import get_db

router = APIRouter(prefix="/resumes", tags=["resumes"])

GENERATED_DIR = Path(__file__).resolve().parents[2] / "generated"


@router.post("/generate/{job_id}")
def generate_resume(job_id: int, db: Session = Depends(get_db)) -> dict:
    """Retrieve -> generate -> validate -> render. Returns the stored resume."""
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")

    profile = db.scalar(select(CandidateProfile))
    if profile is None or not profile.name:
        raise HTTPException(
            status_code=400,
            detail="Add your profile (name, email) before generating a resume.",
        )

    requirements = _requirements_for(db, job_id)
    # The whole knowledge base, most relevant first: the model should choose the
    # best evidence from everything the candidate has done, not from a top-8 slice.
    chunks = retrieve_all(db, job.title, requirements)
    if not chunks:
        raise HTTPException(
            status_code=400, detail="Knowledge base is empty — import your experience first."
        )

    result = generate(profile, job, requirements, chunks)
    if not result["bullets"]:
        raise HTTPException(
            status_code=422,
            detail="No bullet survived truthfulness validation. Try again or enrich your KB.",
        )

    report = ats.keyword_coverage(result, requirements)
    resume = Resume(
        job_id=job_id,
        headline=job.title,
        summary=result["summary"],
        skills=result["skills"],
        bullets=result["bullets"],
    )
    db.add(resume)
    db.commit()
    db.refresh(resume)

    pdf_path = GENERATED_DIR / f"resume_{resume.id}.pdf"
    pdf.render(profile, result, pdf_path)
    report.update(ats.check_pdf(pdf_path.read_bytes(), profile, result))
    report["rejected_bullets"] = result["rejected"]

    resume.pdf_path = str(pdf_path)
    resume.ats_report = report
    db.commit()
    db.refresh(resume)
    return _as_dict(resume, db)


@router.get("/{resume_id}/pdf")
def download_pdf(resume_id: int, db: Session = Depends(get_db)) -> FileResponse:
    purge_expired_resumes(db)
    resume = db.get(Resume, resume_id)
    if resume is None or not resume.pdf_path or not Path(resume.pdf_path).exists():
        raise HTTPException(status_code=404, detail="pdf not found")
    return FileResponse(
        resume.pdf_path, media_type="application/pdf", filename=f"resume_{resume_id}.pdf"
    )


def _requirements_for(db: Session, job_id: int) -> dict:
    """Extracted requirements for a job, or empty ones if it was never enriched."""
    row = db.get(JobRequirements, job_id)
    if row is None:
        return {"required_skills": [], "preferred_skills": [], "responsibilities": []}
    return {
        "required_skills": list(row.required_skills or []),
        "preferred_skills": list(row.preferred_skills or []),
        "responsibilities": list(row.responsibilities or []),
    }


def _as_dict(resume: Resume, db: Session) -> dict:
    """Attach the source accomplishment text so the UI can prove each bullet."""
    from app.db.models import KBChunk

    ids = {i for b in resume.bullets for i in b.get("source_chunk_ids", [])}
    sources = {
        c.id: {"title": c.title, "accomplishment": c.accomplishment}
        for c in db.scalars(select(KBChunk).where(KBChunk.id.in_(ids)))
    } if ids else {}

    return {
        "id": resume.id,
        "job_id": resume.job_id,
        "headline": resume.headline,
        "summary": resume.summary,
        "skills": list(resume.skills or []),
        "bullets": list(resume.bullets or []),
        "ats_report": dict(resume.ats_report or {}),
        "sources": sources,
        "created_at": resume.created_at.isoformat(),
    }
