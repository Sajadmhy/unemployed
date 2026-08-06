"""Turn a free-text job description into structured requirements.

This is the one place an LLM is genuinely the right tool: job descriptions are
unstructured prose written by hundreds of different people, and we need the same
five fields out of every one of them.

Two guardrails matter here:

* **Validate, don't trust.** The model's JSON is normalized and range-checked
  before it touches the database.
* **Confidence is measured, not asked.** We never ask the model how sure it is
  (models are cheerfully overconfident). We score the *output*: an extraction
  that produced no required skills is self-evidently weak, and a weak extraction
  is never allowed to silently filter a job out.
"""
import re

from app.ai.llm import generate_json

# Enough of the posting to cover requirements without paying for boilerplate.
_MAX_CHARS = 6000

SENIORITY_LEVELS = ("intern", "entry", "mid", "senior", "lead")

_SYSTEM = """You extract structured requirements from a job description.

Definitions (follow exactly):
- required_skills: concrete technologies, languages, tools or domains the posting
  states are REQUIRED ("must have", "requirements", "you have"). Skills only —
  never soft skills like "communication" or "teamwork".
- preferred_skills: concrete skills framed as optional ("nice to have", "bonus",
  "preferred", "plus").
- responsibilities: short phrases describing what the person will do (max 6).
- seniority: exactly one of intern, entry, mid, senior, lead.
- min_years: minimum years of experience required as an integer. Use 0 if the
  posting does not state one.

Use only what the posting says. Do not invent requirements. If a field is not
stated, return an empty list or 0.

Respond as JSON:
{"required_skills":[],"preferred_skills":[],"responsibilities":[],"seniority":"","min_years":0}"""

_RETRY_HINT = (
    "\n\nYour previous answer was not valid. Return ONLY the JSON object with "
    "exactly those five keys."
)


def extract_requirements(title: str, description: str) -> dict:
    """Extract requirements for one job. Retries once, then degrades gracefully."""
    prompt = f"Job title: {title}\n\nJob description:\n{description.strip()[:_MAX_CHARS]}"

    for attempt in range(2):
        try:
            raw = generate_json(_SYSTEM + (_RETRY_HINT if attempt else ""), prompt)
            return _normalize(raw, title)
        except Exception:  # noqa: BLE001 - malformed JSON or transport hiccup
            if attempt:  # second failure: return an explicitly untrusted result
                return _empty()
    return _empty()


def _normalize(raw: dict, title: str) -> dict:
    """Coerce the model's output into our exact shape, then score it."""
    if not isinstance(raw, dict):
        raise ValueError("expected a JSON object")

    required = _skills(raw.get("required_skills"))
    preferred = _skills(raw.get("preferred_skills"))
    responsibilities = _skills(raw.get("responsibilities"), limit=6, max_len=200)

    seniority = str(raw.get("seniority", "")).lower().strip()
    if seniority not in SENIORITY_LEVELS:
        seniority = _seniority_from_title(title)

    min_years = _years(raw.get("min_years"))

    result = {
        "required_skills": required,
        "preferred_skills": preferred,
        "responsibilities": responsibilities,
        "seniority": seniority,
        "min_years": min_years,
    }
    result["confidence"] = _confidence(result)
    return result


def _skills(value, limit: int = 25, max_len: int = 80) -> list[str]:
    """Clean a list field: strings only, trimmed, deduped, capped."""
    if not isinstance(value, list):
        return []
    seen, out = set(), []
    for item in value:
        text = str(item).strip().strip(".,;")
        if not text or len(text) > max_len or text.lower() in {"null", "none", "n/a"}:
            continue
        key = text.lower()
        if key not in seen:
            seen.add(key)
            out.append(text)
        if len(out) >= limit:
            break
    return out


def _years(value) -> int:
    """Accept 3, "3", "3+", "3-5 years"; anything unparseable means 0."""
    if isinstance(value, bool):
        return 0
    if isinstance(value, (int, float)):
        return max(0, min(int(value), 20))
    match = re.search(r"\d+", str(value or ""))
    return max(0, min(int(match.group()), 20)) if match else 0


def _seniority_from_title(title: str) -> str:
    """Fallback when the model returns an unknown level."""
    text = (title or "").lower()
    if re.search(r"\b(intern|internship)\b", text):
        return "intern"
    if re.search(r"\b(senior|sr\.?|staff|principal)\b", text):
        return "senior"
    if re.search(r"\b(lead|manager|director|head)\b", text):
        return "lead"
    if re.search(r"\b(junior|jr\.?|graduate|trainee|associate|entry)\b", text):
        return "entry"
    return "mid"


def _confidence(result: dict) -> float:
    """Score the extraction itself — no self-reported confidence."""
    score = 1.0
    if not result["required_skills"]:
        score -= 0.4  # the field matching depends on most
    if not result["responsibilities"]:
        score -= 0.2
    if not result["preferred_skills"]:
        score -= 0.1
    return round(max(0.0, score), 2)


def _empty() -> dict:
    """Extraction failed: zero confidence, so nothing downstream trusts it."""
    return {
        "required_skills": [],
        "preferred_skills": [],
        "responsibilities": [],
        "seniority": "",
        "min_years": 0,
        "confidence": 0.0,
    }
