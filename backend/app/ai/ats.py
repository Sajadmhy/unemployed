"""ATS checks: does this resume survive a machine, and does it speak the JD's words?

Two concrete, checkable properties — not a fake "ATS score out of 100". There is
no universal ATS scoring standard, so any tool claiming one is guessing.

1. **Parseability** — we extract text back out of our own PDF and confirm the
   name, section headings and skills are still there. This is exactly what a real
   ATS does first, so a failure here is a real failure.
2. **Vocabulary alignment** — recruiters search their ATS for the JD's literal
   terms. If the JD says "React" and the resume says "front-end frameworks", the
   resume never surfaces. We report which required terms are present and which
   are missing, and never fabricate the missing ones.
"""
import io
import re

import pdfplumber

REQUIRED_SECTIONS = ("SKILLS", "EDUCATION")


def keyword_coverage(resume: dict, requirements: dict) -> dict:
    """Which of the job's stated skills actually appear in the resume text."""
    text = _norm(_resume_text(resume))
    required = list(requirements.get("required_skills", []))
    preferred = list(requirements.get("preferred_skills", []))

    matched = [s for s in required if _contains(text, _norm(s))]
    missing = [s for s in required if s not in matched]
    matched_pref = [s for s in preferred if _contains(text, _norm(s))]

    return {
        "required_matched": matched,
        "required_missing": missing,
        "preferred_matched": matched_pref,
        "coverage": round(len(matched) / len(required), 3) if required else None,
    }


def check_pdf(pdf_bytes: bytes, profile, resume: dict) -> dict:
    """Round-trip the PDF through a text extractor, the way an ATS would."""
    warnings: list[str] = []
    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            pages = pdf.pages
            page_count = len(pages)
            text = "\n".join(page.extract_text() or "" for page in pages)
    except Exception as e:  # noqa: BLE001 - a broken PDF is itself the finding
        return {"parse_ok": False, "page_count": 0, "warnings": [f"PDF unreadable: {e}"]}

    if not text.strip():
        warnings.append("No text extracted — the PDF is not machine readable")
    if page_count > 1:
        warnings.append(f"{page_count} pages — trim content to fit one page")

    upper = text.upper()
    for section in REQUIRED_SECTIONS:
        if section not in upper:
            warnings.append(f"Missing standard section heading: {section.title()}")

    if profile.name and profile.name.lower() not in text.lower():
        warnings.append("Candidate name did not survive text extraction")

    normalized = _norm(text)
    lost = [s for s in resume.get("skills", []) if not _contains(normalized, _norm(s))]
    if lost:
        warnings.append(f"Skills not extractable: {', '.join(lost[:5])}")

    return {
        "parse_ok": bool(text.strip()) and page_count == 1 and not lost,
        "page_count": page_count,
        "extracted_chars": len(text),
        "warnings": warnings,
    }


def _resume_text(resume: dict) -> str:
    parts = [resume.get("summary", ""), " ".join(resume.get("skills", []))]
    parts += [b.get("text", "") for b in resume.get("bullets", [])]
    parts += [b.get("title", "") or "" for b in resume.get("bullets", [])]
    return " ".join(parts)


def _contains(haystack: str, term: str) -> bool:
    if not term:
        return False
    return re.search(rf"(?<![a-z0-9]){re.escape(term)}(?![a-z0-9])", haystack) is not None


def _norm(text: str) -> str:
    """Whitespace runs collapse to one space so a skill split across a line
    wrap ("GitHub / Jira /\\nSlack APIs") still matches its single-line form."""
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9+#. ]+", " ", (text or "").lower())).strip()
