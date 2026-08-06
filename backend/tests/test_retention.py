"""Generated resumes must not outlive their TTL.

These run against a real (in-memory) database rather than mocks, because the
thing worth testing is the query and the delete, not that a fake was called.
That is only possible now the schema is SQLite - it used to need a Postgres
server with pgvector just to instantiate the models.
"""
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.db.models import Job, Resume
from app.db.retention import purge_expired_resumes
from app.db.session import Base


@pytest.fixture
def db():
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    with sessionmaker(bind=engine, expire_on_commit=False)() as session:
        session.add(Job(id=1, source="greenhouse", external_id="x", company="C", title="T"))
        session.commit()
        yield session


def _resume(db, minutes_old: float, **kwargs) -> Resume:
    resume = Resume(
        job_id=1,
        created_at=datetime.now(UTC) - timedelta(minutes=minutes_old),
        **kwargs,
    )
    db.add(resume)
    db.commit()
    return resume


def test_a_resume_past_its_ttl_is_deleted(db) -> None:
    _resume(db, minutes_old=settings.resume_ttl_minutes + 1)
    assert purge_expired_resumes(db) == 1
    assert db.scalars(select(Resume)).all() == []


def test_a_fresh_resume_is_kept(db) -> None:
    _resume(db, minutes_old=1)
    assert purge_expired_resumes(db) == 0
    assert len(db.scalars(select(Resume)).all()) == 1


def test_the_latex_document_goes_too(db) -> None:
    """The Overleaf path is the reason this exists: those documents are the
    user's whole resume, and keeping copies of them indefinitely is the thing
    being avoided."""
    _resume(db, minutes_old=settings.resume_ttl_minutes + 1, latex=r"\documentclass{article}")
    purge_expired_resumes(db)
    assert db.scalars(select(Resume)).all() == []


def test_the_pdf_on_disk_is_deleted_with_the_row(db, tmp_path) -> None:
    """An orphaned file would outlive the record pointing at it and never be
    cleaned up by anything."""
    pdf = tmp_path / "resume_1.pdf"
    pdf.write_bytes(b"%PDF-1.4")
    _resume(db, minutes_old=settings.resume_ttl_minutes + 1, pdf_path=str(pdf))

    purge_expired_resumes(db)
    assert not pdf.exists()


def test_a_missing_pdf_does_not_block_the_delete(db, tmp_path) -> None:
    """If the file is already gone the row still has to go, or it is retried
    forever and the resume is served from a path that does not exist."""
    _resume(db, minutes_old=settings.resume_ttl_minutes + 1, pdf_path=str(tmp_path / "gone.pdf"))
    assert purge_expired_resumes(db) == 1
    assert db.scalars(select(Resume)).all() == []


def test_naive_timestamps_do_not_break_expiry(db) -> None:
    """SQLite hands back naive datetimes where Postgres returns aware ones.
    Comparing the two raises TypeError, which inside the sweeper thread would
    silently stop every future purge."""
    resume = _resume(db, minutes_old=settings.resume_ttl_minutes + 1)
    resume.created_at = resume.created_at.replace(tzinfo=None)
    db.commit()

    assert purge_expired_resumes(db) == 1
