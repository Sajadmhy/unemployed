"""Manage which companies' job boards are read.

Search is live: a name is turned into candidate board slugs and probed against
all four ATS platforms, so any company with a public board can be added — the
seed list is a starting point, not a limit.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.connectors.registry import CONNECTORS
from app.db.models import Company, Job, Preferences
from app.db.session import get_db
from app.ingestion.discover import find_company
from app.ingestion.relevance import DEFAULT_REGION
from app.schemas import CompanyIn

router = APIRouter(prefix="/companies", tags=["companies"])


@router.get("")
def list_companies(db: Session = Depends(get_db)) -> list[dict]:
    """Tracked companies, with how many active jobs each has contributed."""
    counts = dict(
        db.execute(
            select(Job.company, func.count())
            .where(Job.status == "active")
            .group_by(Job.company)
        ).all()
    )
    rows = db.scalars(select(Company).order_by(Company.name))
    return [
        {
            "id": c.id,
            "source": c.source,
            "token": c.token,
            "name": c.name,
            "enabled": c.enabled,
            "matched_jobs": c.matched_jobs,
            "active_jobs": counts.get(c.name, 0),
        }
        for c in rows
    ]


@router.get("/search")
def search(name: str, db: Session = Depends(get_db)) -> dict:
    """Look for a company's public job board across all supported platforms."""
    if len(name.strip()) < 2:
        raise HTTPException(status_code=422, detail="enter at least 2 characters")

    preferences = db.scalar(select(Preferences))
    region = getattr(preferences, "region", None) or DEFAULT_REGION

    found = find_company(name.strip(), region)
    if found is None:
        return {"found": False, "name": name.strip()}

    already = db.scalar(
        select(Company).where(
            Company.source == found["source"], Company.token == found["token"]
        )
    )
    return {"found": True, **found, "already_tracked": already is not None}


@router.post("", status_code=201)
def add_company(data: CompanyIn, db: Session = Depends(get_db)) -> dict:
    if data.source not in CONNECTORS:
        raise HTTPException(status_code=422, detail=f"unknown source: {data.source}")

    existing = db.scalar(
        select(Company).where(Company.source == data.source, Company.token == data.token)
    )
    if existing is not None:
        # Re-adding a company the user previously removed simply re-enables it.
        existing.enabled = True
        db.commit()
        return {"id": existing.id, "name": existing.name, "re_enabled": True}

    company = Company(
        source=data.source,
        token=data.token,
        name=data.name or data.token,
        matched_jobs=data.matched_jobs,
    )
    db.add(company)
    db.commit()
    db.refresh(company)
    return {"id": company.id, "name": company.name, "re_enabled": False}


@router.delete("/{company_id}", status_code=204)
def remove_company(company_id: int, db: Session = Depends(get_db)) -> None:
    """Stop tracking a company. Jobs already ingested are left alone."""
    company = db.get(Company, company_id)
    if company is None:
        raise HTTPException(status_code=404, detail="company not found")
    db.delete(company)
    db.commit()
