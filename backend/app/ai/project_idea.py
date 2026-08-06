"""A portfolio project worth building for one specific job.

For a fresher, shipping something relevant to the company's product is the
strongest available signal — stronger than another resume line, because it is
evidence rather than a claim. Attached to an outreach message, it is also the
thing most likely to get a reply.

Two properties decide whether this feature is useful or noise:

* **Specific to the company.** "Build a todo app with React" impresses nobody.
  The idea must reference what this company actually does and what the role
  actually asks for.
* **Aimed at a real gap.** The point is to build what the candidate *cannot yet
  evidence*. Those gaps are computed deterministically — the required skills the
  knowledge base has no proof of — and handed to the model rather than guessed
  by it.

Generic output is rejected outright: a shortlist of stock project names is
cheaper and more reliable to check than trying to prompt the tendency away.
"""
import re

from app.ai.llm import generate_json
from app.ai.match import _in_candidate, _norm

# Ideas so overused they signal nothing. If the model returns one, reject it.
_GENERIC = (
    "todo app", "to-do app", "todo list", "task manager", "weather app",
    "calculator", "tic tac toe", "tic-tac-toe", "blog platform", "e-commerce site",
    "portfolio website", "chat app", "url shortener", "notes app", "quiz app",
    "expense tracker", "library management", "student management", "crud app",
    "netflix clone", "twitter clone", "instagram clone", "uber clone",
)

_SYSTEM = """You design ONE portfolio project a candidate can build to stand out for a specific job.

Requirements:
- It must be obviously connected to what THIS company does and what THIS role needs.
- It must exercise the listed skill gaps — that is the point of building it.
- It must be finishable by one person in under two weeks. Scope accordingly.
- Be concrete: name the actual thing being built, not a category.
- Never suggest generic student projects (todo app, weather app, clones, CRUD demos).

Respond as JSON:
{"title":"","problem":"","what_to_build":"","why_it_impresses":"","tech_stack":[],"scope":"e.g. 1 week"}

- problem: the real-world problem it solves, in this company's domain (1-2 sentences).
- what_to_build: concrete components and behaviour (2-4 sentences).
- why_it_impresses: why someone hiring for THIS role would care (1-2 sentences)."""


def skill_gaps(requirements: dict, candidate) -> list[str]:
    """Required/preferred skills this job wants that the KB cannot evidence.

    Computed, not asked: the same containment check the matching engine uses, so
    "the gaps" means exactly what "missing" means everywhere else in the product.
    """
    wanted = list(requirements.get("required_skills", [])) + list(
        requirements.get("preferred_skills", [])
    )
    gaps: list[str] = []
    for skill in wanted:
        name = str(skill).strip()
        if name and not _in_candidate(_norm(name), candidate):
            if name.lower() not in {g.lower() for g in gaps}:
                gaps.append(name)
    return gaps[:8]


def generate(job, requirements: dict, gaps: list[str], strengths: list[str]) -> dict | None:
    """Propose one tailored project. Returns None if the idea is too generic."""
    prompt = (
        f"COMPANY: {job.company}\n"
        f"ROLE: {job.title}\n"
        f"WHAT THE ROLE ASKS FOR: {', '.join(requirements.get('required_skills', [])) or 'not specified'}\n"
        f"WHAT THE COMPANY DOES (from the posting):\n{(job.description or '')[:1200]}\n\n"
        f"SKILLS THE CANDIDATE CANNOT YET SHOW: {', '.join(gaps) or 'none — pick the most role-relevant depth'}\n"
        f"WHAT THE CANDIDATE ALREADY KNOWS: {', '.join(strengths[:12]) or 'general software engineering'}\n\n"
        "Design one project that closes those gaps and is clearly about this company's domain."
    )

    try:
        raw = generate_json(_SYSTEM, prompt, timeout=300, max_tokens=1200)
    except Exception:  # noqa: BLE001 - a failed idea is not worth crashing the request
        return None

    idea = _normalize(raw, gaps)
    if idea is None or _is_generic(idea):
        return None
    return idea


def _is_generic(idea: dict) -> bool:
    """Reject stock student projects, whatever the prompt asked for."""
    haystack = f"{idea['title']} {idea['what_to_build']}".lower()
    return any(phrase in haystack for phrase in _GENERIC)


def _normalize(raw, gaps: list[str]) -> dict | None:
    if not isinstance(raw, dict):
        return None
    title = _text(raw.get("title"), 300)
    build = _text(raw.get("what_to_build"), 2000)
    if not title or not build:
        return None
    return {
        "title": title,
        "problem": _text(raw.get("problem"), 2000),
        "what_to_build": build,
        "why_it_impresses": _text(raw.get("why_it_impresses"), 2000),
        "tech_stack": [t for t in (_text(x, 80) for x in (raw.get("tech_stack") or [])) if t][:12],
        "covers_gaps": gaps,
        "scope": _text(raw.get("scope"), 120) or "about 1 week",
    }


def _text(value, limit: int) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    return "" if text.lower() in {"null", "none", "n/a"} else text[:limit]
