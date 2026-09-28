"""ORM models: the candidate profile, knowledge-base chunks, jobs and resumes.

A KB chunk is ONE accomplishment with enough context to stand on its own. This
is the atomic unit we embed and later retrieve against a job description.
"""
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.config import settings
from app.db.session import Base
from app.db.types import Embedding, JSONColumn, StringList


class CandidateProfile(Base):
    """The single owner of this knowledge base (one row)."""

    __tablename__ = "candidate_profile"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), default="")
    email: Mapped[str] = mapped_column(String(200), default="")
    phone: Mapped[str] = mapped_column(String(50), default="")
    location: Mapped[str] = mapped_column(String(200), default="")
    # e.g. {"github": "...", "linkedin": "...", "portfolio": "..."}
    links: Mapped[dict] = mapped_column(JSONColumn, default=dict)
    summary: Mapped[str] = mapped_column(Text, default="")
    # Free text, e.g. "B.Tech Computer Science, VIT Vellore, 2022-2026 | CGPA 8.6".
    # A fresher resume is incomplete without it, and it is never LLM-generated.
    education: Mapped[str] = mapped_column(Text, default="")
    # Just the institution name, e.g. "VIT Vellore". Stored separately because
    # alumni outreach searches on it, and parsing it back out of the free-text
    # education line would be guesswork.
    college: Mapped[str] = mapped_column(String(200), default="")


class KBChunk(Base):
    """One accomplishment + its context, plus its embedding vector."""

    __tablename__ = "kb_chunks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # project | experience | leadership | achievement | skill | certification
    #   | education
    # Free text rather than an enum on purpose: adding a kind is a code change,
    # not a migration, and app/ai/parse.py owns the list that is accepted.
    type: Mapped[str] = mapped_column(String(40))
    title: Mapped[str] = mapped_column(String(300))
    context: Mapped[str | None] = mapped_column(String(300), nullable=True)
    company: Mapped[str | None] = mapped_column(String(200), nullable=True)
    date_range: Mapped[str | None] = mapped_column(String(100), nullable=True)

    accomplishment: Mapped[str] = mapped_column(Text)
    technologies: Mapped[list[str]] = mapped_column(StringList, default=list)
    skills: Mapped[list[str]] = mapped_column(StringList, default=list)
    impact: Mapped[str | None] = mapped_column(Text, nullable=True)

    embedding: Mapped[list[float]] = mapped_column(Embedding(settings.embedding_dim))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Job(Base):
    """One job posting, normalized to a common schema across all sources.

    Identity is (source, external_id) — that is what makes re-running the
    ingestion idempotent. `fingerprint` catches the same role appearing on two
    different boards. `last_seen` drives expiry: a job the source stopped
    listing is marked expired rather than deleted, so history is preserved.
    """

    __tablename__ = "jobs"
    __table_args__ = (
        UniqueConstraint("source", "external_id", name="uq_jobs_source_external_id"),
        Index("ix_jobs_status_posted_at", "status", "posted_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    source: Mapped[str] = mapped_column(String(40))  # greenhouse | lever
    external_id: Mapped[str] = mapped_column(String(200))

    company: Mapped[str] = mapped_column(String(200))
    title: Mapped[str] = mapped_column(String(400))
    location: Mapped[str] = mapped_column(String(300), default="")
    remote: Mapped[bool] = mapped_column(Boolean, default=False)
    description: Mapped[str] = mapped_column(Text, default="")
    apply_url: Mapped[str] = mapped_column(String(1000), default="")

    posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    first_seen: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    last_seen: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    status: Mapped[str] = mapped_column(String(20), default="active")  # active | expired
    # sha256(title + description): lets us skip work when nothing actually changed.
    content_hash: Mapped[str] = mapped_column(String(64), default="")
    # sha256(normalized company + title): cross-source duplicate detection.
    fingerprint: Mapped[str] = mapped_column(String(64), default="", index=True)


class JobRequirements(Base):
    """What a job actually asks for, extracted from its description by the LLM.

    `source_hash` is the job's content_hash at extraction time. If the posting
    text changes the hash changes and we re-extract; otherwise we never pay the
    ~25s LLM cost for this job again.
    """

    __tablename__ = "job_requirements"

    job_id: Mapped[int] = mapped_column(
        ForeignKey("jobs.id", ondelete="CASCADE"), primary_key=True
    )
    required_skills: Mapped[list[str]] = mapped_column(StringList, default=list)
    preferred_skills: Mapped[list[str]] = mapped_column(StringList, default=list)
    responsibilities: Mapped[list[str]] = mapped_column(StringList, default=list)

    seniority: Mapped[str] = mapped_column(String(40), default="")  # intern|entry|mid|senior|lead
    min_years: Mapped[int] = mapped_column(Integer, default=0)

    # 0..1 — how much we trust this extraction. Low confidence must never
    # silently hard-filter a job; it flags it instead.
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    source_hash: Mapped[str] = mapped_column(String(64), default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Resume(Base):
    """A tailored resume generated for one job.

    `bullets` stores each bullet WITH the KB chunk ids it came from. That link is
    the product's honesty guarantee: any line on the page can be traced back to a
    verified accomplishment, and anything untraceable never gets written.
    """

    __tablename__ = "resumes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), index=True)

    headline: Mapped[str] = mapped_column(String(300), default="")
    summary: Mapped[str] = mapped_column(Text, default="")
    skills: Mapped[list[str]] = mapped_column(StringList, default=list)
    # [{section, title, context, date_range, text, source_chunk_ids: [int]}]
    bullets: Mapped[list] = mapped_column(JSONColumn, default=list)

    # {keyword_coverage, matched, missing, parse_ok, warnings[]}
    ats_report: Mapped[dict] = mapped_column(JSONColumn, default=dict)
    pdf_path: Mapped[str] = mapped_column(String(500), default="")
    # Left over from LaTeX template tailoring, which is gone. Kept because the
    # column is NOT NULL in existing databases.
    latex: Mapped[str] = mapped_column(Text, default="")
    edited: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
