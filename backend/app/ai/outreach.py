"""Who to contact about a job, and what to say.

**No scraping.** LinkedIn forbids it and enforces with account bans, so the tool
never fetches a profile. It builds a precise search *query* for each category of
person worth contacting, and the user opens it and does the looking. That keeps
the account safe, costs nothing, and — because the boolean queries are better
than what most people type by hand — is genuinely faster than doing it manually.

Referrals convert far better than cold applications, which is why this sits
beside resume generation rather than behind it.

Drafts are grounded the same way resumes are: the model may only use the
candidate's real accomplishments, and a draft that invents a credential is worse
than no draft at all.
"""
import re
from urllib.parse import quote_plus

from app.ai.llm import generate_json

# Google indexes LinkedIn profiles, so a site: query finds people without
# needing to be logged in or to hit LinkedIn's own search rate limits.
_GOOGLE = "https://www.google.com/search?q={q}"
_LINKEDIN = "https://www.linkedin.com/search/results/people/?keywords={q}"

CATEGORIES = ("alumni", "same_role", "eng_leader", "recruiter", "founder")


def build_contacts(job, profile) -> list[dict]:
    """One targeted search per category of person worth reaching out to."""
    company = (job.company or "").strip()
    role = _role_keywords(job.title)
    college = (getattr(profile, "college", "") or "").strip()

    plans = [
        (
            "recruiter",
            "Recruiters / talent team",
            f'"{company}" (recruiter OR "talent acquisition" OR "technical recruiter") India',
        ),
        (
            "eng_leader",
            "Engineering managers / VPs",
            f'"{company}" ("engineering manager" OR "director of engineering" OR "VP engineering") India',
        ),
        (
            "same_role",
            f"People doing this role ({role})",
            f'"{company}" "{role}" India',
        ),
        (
            "founder",
            "Founders / leadership",
            f'"{company}" (founder OR "co-founder" OR CTO)',
        ),
    ]
    if college:
        plans.insert(
            0,
            (
                "alumni",
                f"Alumni from {college}",
                f'"{company}" "{college}"',
            ),
        )

    return [
        {
            "category": category,
            "label": label,
            "search_url": _GOOGLE.format(q=quote_plus(f"site:linkedin.com/in {query}")),
            "linkedin_url": _LINKEDIN.format(q=quote_plus(_plain(query))),
        }
        for category, label, query in plans
    ]


_SYSTEM = """You write short, specific outreach messages for a job seeker.

You are writing AS THE CANDIDATE, in the first person, to a stranger.

Rules:
- Use ONLY the candidate facts provided. Never invent experience, employers, metrics or skills.
- The listed accomplishments are things the CANDIDATE built. Always refer to them as your
  own work ("I built X"). Never describe them as the recipient's or their team's work.
- Under 60 words. No flattery, no "I hope this finds you well", no "passionate".
- Reference one concrete thing you built that is relevant to this company.
- End with a specific, low-friction ask.
- Plain text. No subject line, no signature.

Respond as JSON: {"messages":{"<category>":"<message>"}} using exactly the categories given."""

_TONE = {
    "alumni": "a fellow alumnus of the same college — mention the shared college naturally",
    "same_role": "someone already doing this role — mention what you built, then ask what "
                 "their day-to-day looks like",
    "eng_leader": "an engineering manager or VP — lead with what the candidate built",
    "recruiter": "a recruiter — state interest in the specific role directly",
    "founder": "a founder or CTO at a startup — be brief and product-focused",
}


def draft_messages(job, profile, chunks, categories: list[str]) -> dict[str, str]:
    """Grounded opening messages, one per category."""
    if not chunks or not categories:
        return {}

    facts = "\n".join(
        f"- {c.title}: {c.accomplishment}" + (f" (Impact: {c.impact})" if c.impact else "")
        for c in chunks[:5]
    )
    wanted = "\n".join(f"- {c}: writing to {_TONE[c]}" for c in categories if c in _TONE)
    prompt = (
        f"CANDIDATE: {profile.name or 'the candidate'}"
        + (f", student at {profile.college}" if getattr(profile, "college", "") else "")
        + f"\n\nCANDIDATE'S REAL ACCOMPLISHMENTS (the only facts you may use):\n{facts}"
        f"\n\nTARGET: {job.title} at {job.company}"
        f"\n\nWrite one message for each of these recipients:\n{wanted}"
    )

    try:
        raw = generate_json(_SYSTEM, prompt, timeout=240, max_tokens=1200)
    except Exception:  # noqa: BLE001 - drafts are optional; links still work
        return {}

    messages = raw.get("messages")
    if not isinstance(messages, dict):
        return {}
    return {
        category: str(text).strip()[:800]
        for category, text in messages.items()
        if category in categories and str(text).strip()
    }


def _role_keywords(title: str) -> str:
    """Strip the noise a title search does not need."""
    cleaned = re.sub(r"[\(\[].*?[\)\]]", " ", title or "")
    cleaned = re.sub(r"\b(i{1,3}|iv|v|\d+)\b", " ", cleaned, flags=re.IGNORECASE)
    cleaned = re.split(r"[-–—,|]", cleaned)[0]
    return re.sub(r"\s+", " ", cleaned).strip() or (title or "").strip()


def _plain(query: str) -> str:
    """LinkedIn's own search does not handle boolean operators well."""
    return re.sub(r"\s+", " ", re.sub(r'["()]|\bOR\b', " ", query)).strip()
