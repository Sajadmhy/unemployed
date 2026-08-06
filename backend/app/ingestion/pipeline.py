"""The daily ingestion pipeline: fetch -> filter -> dedupe -> upsert -> expire.

Three properties matter more than speed here:

* **Idempotent** — re-running changes nothing. Identity is (source, external_id),
  so a second run updates rows instead of inserting duplicates.
* **Isolated** — each company is fetched in its own try/except and gets its own
  `ingestion_runs` row. One dead board cannot abort the others.
* **Safe expiry** — jobs are only expired after a *successful* fetch. If a board
  errors we keep what we have, instead of wrongly marking everything gone.
"""
import hashlib
import logging
import re
from collections.abc import Callable
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.connectors.base import RawJob
from app.connectors.registry import CONNECTORS, Company, load_companies
from app.db.models import IngestionRun, Job, Preferences
from app.ingestion.relevance import DEFAULT_REGION, is_relevant

log = logging.getLogger(__name__)


def run_ingestion(
    db: Session,
    companies: list[Company] | None = None,
    on_progress: Callable[[int, int, str], None] | None = None,
) -> list[IngestionRun]:
    """Ingest every configured company. Returns one audit row per company.

    `on_progress(done, total, message)` lets the UI show which company is being
    fetched. It is optional so the CLI keeps working untouched.
    """
    preferences = db.scalar(select(Preferences))
    region = getattr(preferences, "region", None) or DEFAULT_REGION

    targets = companies if companies is not None else load_companies(db)
    runs = []
    for index, company in enumerate(targets, start=1):
        if on_progress:
            on_progress(index - 1, len(targets), f"Fetching {company.name}")
        runs.append(_ingest_company(db, company, region))
    if on_progress:
        on_progress(len(targets), len(targets), "Done")
    return runs


def _ingest_company(db: Session, company: Company, region: str) -> IngestionRun:
    run = IngestionRun(source=company.source, company=company.name)
    db.add(run)
    db.commit()

    try:
        raw_jobs = CONNECTORS[company.source](company.token, company.name, region)
    except Exception as e:  # noqa: BLE001 - isolate this source, keep the run going
        log.warning("ingest failed for %s/%s: %s", company.source, company.token, e)
        run.ok, run.error, run.finished_at = False, str(e)[:2000], _now()
        db.commit()
        return run

    relevant = [j for j in raw_jobs if is_relevant(j.location, j.remote, j.title, region)]
    seen_ids = []
    for raw in relevant:
        created = _upsert(db, raw)
        seen_ids.append(raw.external_id)
        run.jobs_new += int(created)
        run.jobs_updated += int(not created)

    run.jobs_seen = len(relevant)
    run.jobs_expired = _expire_missing(db, company, seen_ids)
    run.finished_at = _now()
    db.commit()
    return run


def _upsert(db: Session, raw: RawJob) -> bool:
    """Insert or refresh one job. Returns True if it was newly created."""
    existing = db.scalar(
        select(Job).where(Job.source == raw.source, Job.external_id == raw.external_id)
    )
    content_hash = _sha(f"{raw.title}\n{raw.description}")

    if existing is None:
        # Cross-source duplicate: the same role already came from another board.
        fingerprint = _sha(f"{_norm(raw.company)}|{_norm(raw.title)}")
        if db.scalar(select(Job).where(Job.fingerprint == fingerprint)) is not None:
            return False
        db.add(
            Job(
                source=raw.source,
                external_id=raw.external_id[:200],
                company=_fit(raw.company, 200),
                title=_fit(raw.title, 400),
                location=_fit(raw.location, 300),
                remote=raw.remote,
                description=raw.description,
                apply_url=_fit(raw.apply_url, 1000),
                posted_at=raw.posted_at,
                content_hash=content_hash,
                fingerprint=fingerprint,
            )
        )
        db.commit()
        return True

    existing.last_seen = _now()
    existing.status = "active"  # a job that reappears is live again
    if existing.content_hash != content_hash:  # incremental: only touch real changes
        existing.title = _fit(raw.title, 400)
        existing.description = raw.description
        existing.location = _fit(raw.location, 300)
        existing.remote = raw.remote
        existing.apply_url = _fit(raw.apply_url, 1000)
        existing.content_hash = content_hash
    db.commit()
    return False


def _expire_missing(db: Session, company: Company, seen_ids: list[str]) -> int:
    """Mark active jobs from this company that the source no longer lists."""
    stale = db.scalars(
        select(Job).where(
            Job.source == company.source,
            Job.company == company.name,
            Job.status == "active",
            Job.external_id.notin_(seen_ids) if seen_ids else True,
        )
    ).all()
    for job in stale:
        job.status = "expired"
    db.commit()
    return len(stale)


def _fit(text: str, limit: int) -> str:
    """Trim a field to its column width.

    Real boards break assumptions: New Relic lists 20+ cities in one `location`
    string, which is past VARCHAR(300) and aborted a whole ingestion run. The
    pipeline truncates centrally so one verbose source cannot take down others.
    """
    return (text or "")[:limit]


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _norm(text: str) -> str:
    """Loose normalization so trivial formatting differences still match."""
    return re.sub(r"[^a-z0-9]+", " ", (text or "").lower()).strip()


def _now() -> datetime:
    return datetime.now(UTC)
