"""Measure the AI pipeline against the live database.

    python -m app.eval.run

"It feels better" is not a claim you can defend in a design review, and prompt
edits regress quietly — a change that improves extraction can easily loosen
filtering. This prints a small set of numbers that make both visible.

Everything here is measured against real ingested data rather than a fixture, so
the numbers describe the system as it actually runs today.
"""
from sqlalchemy import func, select

from app.ai.match import DEFAULT_ROLE_FAMILIES, CandidateIndex
from app.db.models import Job, JobRequirements, KBChunk, Match, Preferences, Resume
from app.db.session import SessionLocal
from app.ingestion.experience import required_years
from app.ingestion.role_family import classify
from app.ingestion.seniority import is_fresher_friendly


def extraction_quality(db) -> dict:
    """Did the LLM produce usable requirements, and how often did it fail?"""
    rows = list(db.scalars(select(JobRequirements)))
    if not rows:
        return {"extracted": 0}
    with_required = sum(1 for r in rows if r.required_skills)
    failed = sum(1 for r in rows if r.confidence == 0.0)
    return {
        "extracted": len(rows),
        "with_required_skills": _pct(with_required, len(rows)),
        "mean_confidence": round(sum(r.confidence for r in rows) / len(rows), 3),
        "hard_failures": failed,
    }


def filter_precision(db) -> dict:
    """Does anything visible violate the filters it is supposed to obey?

    These are the leaks a user notices immediately: a senior role, an off-domain
    role, or one demanding years they do not have.

    "Off-domain" means whatever the user did not tick, not a fixed list of
    technical families — a design student's design roles are not leaks.
    """
    visible = db.execute(
        select(Match, Job)
        .join(Job, Match.job_id == Job.id)
        .where(Match.hard_filtered.is_(False), Job.status == "active")
    ).all()
    if not visible:
        return {"visible": 0}

    preferences = db.scalar(select(Preferences))
    families = set(getattr(preferences, "role_families", None) or DEFAULT_ROLE_FAMILIES)

    too_senior = [j.title for _, j in visible if not is_fresher_friendly(j.title)]
    off_domain = [j.title for _, j in visible if classify(j.title) not in families]
    too_many_years = [
        f"{j.title} ({required_years(j.description)}y)"
        for _, j in visible
        if (required_years(j.description) or 0) > 1
    ]
    return {
        "visible": len(visible),
        "leaks_senior_title": len(too_senior),
        "leaks_off_domain": len(off_domain),
        "leaks_too_many_years": len(too_many_years),
        "examples": (too_senior + off_domain + too_many_years)[:5],
    }


def resume_truthfulness(db) -> dict:
    """Every resume bullet must trace to a knowledge-base chunk."""
    resumes = list(db.scalars(select(Resume)))
    if not resumes:
        return {"resumes": 0}
    valid_ids = {c.id for c in db.scalars(select(KBChunk))}

    bullets = [b for r in resumes for b in (r.bullets or [])]
    traceable = [
        b for b in bullets
        if b.get("source_chunk_ids") and all(i in valid_ids for i in b["source_chunk_ids"])
    ]

    # Only resumes rendered into our own PDF have an ATS report to speak of.
    rendered = [r for r in resumes if not r.latex]
    ats_ok = sum(1 for r in rendered if (r.ats_report or {}).get("parse_ok"))

    # For the LaTeX path the equivalent question is how much of the document the
    # validator let through: a prompt regression shows up here as a collapse.
    sections = [
        s for r in resumes for s in (r.ats_report or {}).get("latex_sections", [])
    ]
    return {
        "resumes": len(resumes),
        "bullets": len(bullets),
        "traceable_bullets": _pct(len(traceable), len(bullets)),
        "ats_parse_ok": _pct(ats_ok, len(rendered)),
        "latex_sections_rewritten": _pct(
            sum(1 for s in sections if s["rewritten"]), len(sections)
        ),
    }


def coverage(db) -> dict:
    """How much of the funnel actually reaches the user."""
    active = db.scalar(select(func.count()).select_from(Job).where(Job.status == "active")) or 0
    scored = db.scalar(select(func.count()).select_from(Match)) or 0
    full = db.scalar(select(func.count()).select_from(Match).where(Match.tier == "full")) or 0
    kb = db.scalar(select(func.count()).select_from(KBChunk)) or 0
    companies = db.scalar(
        select(func.count(func.distinct(Job.company))).where(Job.status == "active")
    ) or 0
    return {
        "kb_chunks": kb,
        "active_jobs": active,
        "companies": companies,
        "scored": scored,
        "fully_extracted": full,
    }


def _pct(part: int, whole: int) -> str:
    return f"{part}/{whole} ({round(100 * part / whole)}%)" if whole else "n/a"


def main() -> None:
    with SessionLocal() as db:
        chunks = list(db.scalars(select(KBChunk)))
        if not chunks:
            raise SystemExit("Knowledge base is empty — nothing to evaluate.")
        CandidateIndex(chunks)  # fails loudly if embeddings are malformed

        sections = {
            "COVERAGE": coverage(db),
            "EXTRACTION": extraction_quality(db),
            "FILTER PRECISION": filter_precision(db),
            "RESUME TRUTHFULNESS": resume_truthfulness(db),
        }

    for name, values in sections.items():
        print(f"\n{name}")
        for key, value in values.items():
            print(f"  {key:24} {value}")

    leaks = sum(
        v for k, v in sections["FILTER PRECISION"].items() if k.startswith("leaks_")
    )
    print(f"\n{'PASS' if leaks == 0 else 'FAIL'}: {leaks} filter leak(s)")


if __name__ == "__main__":
    main()
