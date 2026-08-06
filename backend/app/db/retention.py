"""Generated resumes are temporary by design.

A tailored resume is a *derivative* of two things the app already stores
permanently — the knowledge base and the job — so keeping it is storing the
same information twice. That matters most for the LaTeX path: those documents
are the user's own Overleaf template with their whole career written into it,
and holding copies of that indefinitely is the kind of thing a local-first tool
should be careful about. Regenerating costs one LLM call and always reflects
the *current* knowledge base, which a stale stored copy does not.

So resumes expire. The PDF on disk goes with the row: an orphaned file in
`generated/` would outlive the record pointing at it and never be cleaned up.

Expiry is enforced two ways on purpose:

* a sweeper thread, so a resume left open in a tab still goes away on time
  rather than living until whenever the next request happens to arrive;
* a purge before every read, so nothing expired can ever be served even if
  the sweeper is wedged or the process was asleep.
"""
import logging
import threading
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.db.models import Resume
from app.db.session import SessionLocal

log = logging.getLogger(__name__)

# How often the sweeper wakes. Well under the TTL so the real lifetime of a
# resume is close to the configured one rather than up to double it.
SWEEP_SECONDS = 60


def _cutoff() -> datetime:
    return datetime.now(UTC) - timedelta(minutes=settings.resume_ttl_minutes)


def _created_at_utc(resume: Resume) -> datetime:
    """`created_at` as an aware UTC datetime.

    SQLite has no native timestamp type and hands back naive datetimes where
    Postgres returns aware ones. Comparing the two raises TypeError, which
    inside a sweeper thread would silently kill expiry, so normalise instead of
    assuming either backend.
    """
    created = resume.created_at
    if created.tzinfo is None:
        return created.replace(tzinfo=UTC)
    return created.astimezone(UTC)


def purge_expired_resumes(db: Session) -> int:
    """Delete resumes past their TTL, and the PDFs they own. Returns the count."""
    cutoff = _cutoff()
    expired = [r for r in db.scalars(select(Resume)) if _created_at_utc(r) < cutoff]

    for resume in expired:
        if resume.pdf_path:
            try:
                Path(resume.pdf_path).unlink(missing_ok=True)
            except OSError as exc:
                # A locked or already-removed file must not stop the row being
                # deleted - the database record is the thing that matters, and
                # a stray PDF is retried on the next sweep anyway.
                log.warning("could not delete %s: %s", resume.pdf_path, exc)
        db.delete(resume)

    if expired:
        db.commit()
        log.info("purged %d expired resume(s)", len(expired))
    return len(expired)


def start_sweeper() -> threading.Thread:
    """Run `purge_expired_resumes` forever, in the background.

    A daemon thread so it never holds up shutdown, and it owns its own session
    per pass rather than a long-lived one — a session held open for the life of
    the process would keep a read transaction alive and, on SQLite, block
    checkpointing.
    """

    def loop() -> None:
        while True:
            try:
                with SessionLocal() as db:
                    purge_expired_resumes(db)
            except Exception:
                # Never let one bad pass kill the thread; the next one retries.
                log.exception("resume sweep failed")
            threading.Event().wait(SWEEP_SECONDS)

    thread = threading.Thread(target=loop, name="resume-sweeper", daemon=True)
    thread.start()
    return thread
