"""One call for scripts and bots: a job description in, a tailored resume PDF out.

The web UI walks through the same steps one screen at a time (add the job,
look at the score, generate, download). A Telegram bot or a curl command has
no screens, so this chains them:

    POST /tailor  {"text": "<job post>"}            -> application/pdf
    POST /tailor  {"url": "https://.../jobs/123"}    -> application/pdf

It is slow on purpose-built hardware and slower on a Pi — two LLM calls, a
few minutes on a CPU — so clients should allow a long timeout.
"""
import logging
import re

import httpx
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.ai.llm import generate_json
from app.api.jobs import create_manual_job
from app.api.resumes import generate_resume
from app.connectors.base import HEADERS, strip_html
from app.db.models import Resume
from app.db.session import get_db
from app.schemas import ManualJobIn

log = logging.getLogger(__name__)
router = APIRouter(tags=["tailor"])

_MIN_CHARS = 50
_MAX_CHARS = 12000
_URL_RE = re.compile(r"https?://[^\s<>\"')\]]+")
# Sites that only render the posting with JavaScript or behind a login. Fetching
# them returns a shell with no job text, so say so instead of feeding the model
# a cookie banner.
_UNREADABLE = ("linkedin.com", "t.me", "telegram.me", "indeed.com", "glassdoor.")
_DROP_BLOCKS = re.compile(r"<(script|style|noscript|svg|nav|footer|header)\b.*?</\1>", re.S | re.I)


class TailorIn(BaseModel):
    text: str = ""
    url: str = ""
    title: str = ""
    company: str = ""


@router.post("/tailor", response_class=FileResponse)
def tailor(data: TailorIn, db: Session = Depends(get_db)) -> FileResponse:
    text = data.text.strip()
    url = data.url.strip()
    if not url and len(text) < 300:
        # A short message that is mostly a link: the posting is behind the link.
        found = _URL_RE.search(text)
        if found:
            url = found.group(0)
    if url and len(text) < 300:
        text = _fetch(url)
    if len(text) < _MIN_CHARS:
        raise HTTPException(422, "Not enough job description text. Paste the posting itself.")
    text = text[:_MAX_CHARS]

    title, company = data.title.strip(), data.company.strip()
    if not title or not company:
        guess = _guess_title_company(text)
        title = title or guess["title"]
        company = company or guess["company"]

    step = "reading the job"
    try:
        job = create_manual_job(
            ManualJobIn(title=title, company=company, description=text, apply_url=url), db
        )
        step = "writing the resume"
        resume = generate_resume(job["job_id"], "pdf", db)
    except HTTPException:
        raise
    except Exception as e:  # noqa: BLE001 - a bot can only show what we tell it
        log.exception("tailor failed while %s", step)
        raise HTTPException(500, f"Failed while {step}: {type(e).__name__}: {e}"[:600]) from e
    row = db.get(Resume, resume["id"])
    if row is None or not row.pdf_path:
        raise HTTPException(500, "Resume was generated but the PDF is missing.")

    safe = re.sub(r"[^A-Za-z0-9]+", "_", f"{company}_{title}").strip("_")[:60] or "resume"
    return FileResponse(
        row.pdf_path,
        media_type="application/pdf",
        filename=f"resume_{safe}.pdf",
        headers={"X-Job-Title": _ascii(title), "X-Company": _ascii(company),
                 "X-Match-Score": str(job.get("score", ""))},
    )


def _fetch(url: str) -> str:
    if any(host in url.lower() for host in _UNREADABLE):
        raise HTTPException(
            422, "That site can't be read without a login or a browser. Paste the job text instead."
        )
    try:
        resp = httpx.get(url, headers=HEADERS, timeout=30, follow_redirects=True)
        resp.raise_for_status()
    except httpx.HTTPError as e:
        raise HTTPException(422, f"Couldn't open that link ({e}). Paste the job text instead.") from e
    body = resp.text
    if "html" in resp.headers.get("content-type", ""):
        body = strip_html(_DROP_BLOCKS.sub(" ", body))
    if len(body) < 200:
        raise HTTPException(
            422, "That page has almost no text (it probably needs JavaScript). Paste the job text instead."
        )
    return body


_GUESS_SYSTEM = """You read a job posting and return JSON: {"title": ..., "company": ...}.
title: the job title as written, e.g. "Senior Backend Engineer". company: the hiring
company's name. Use "" for anything the posting does not say. No other keys."""


def _guess_title_company(text: str) -> dict:
    try:
        raw = generate_json(_GUESS_SYSTEM, text[:3000], max_tokens=80)
    except Exception as e:  # noqa: BLE001 - only a guess; fall back below
        log.warning("title/company guess failed: %s", e)
        raw = {}
    title = str(raw.get("title") or "").strip()[:120]
    company = str(raw.get("company") or "").strip()[:120]
    if len(title) < 2:
        first = next((ln.strip() for ln in text.splitlines() if len(ln.strip()) >= 2), "Software Developer")
        title = first[:80]
    return {"title": title, "company": company or "Unknown company"}


def _ascii(s: str) -> str:
    return s.encode("ascii", "ignore").decode()[:120]
