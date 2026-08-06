"""How many years of experience does this posting actually demand?

The number is written in the job description in plain text — "5-7+ years in
technical customer-facing roles". There is no reason to spend ~25s of LLM time
discovering a figure a regex finds in microseconds, and crucially the regex runs
on *every* job, not just the hundred the expensive tier can afford.

That matters because the previous design only knew a job's experience
requirement after LLM extraction, so jobs that never reached the expensive tier
were shown unfiltered — senior roles at the top of a fresher's list.

Rules (chosen deliberately):

* **A range counts as its lower bound.** "3-5 years" means you need 3, so a
  "0-2 years" posting stays visible while "3-5" does not.
* **Multiple mentions take the highest bar.** A posting asking "5+ years overall"
  and "2+ years with Python" requires 5.
* **Silence is not a rejection.** Most genuine fresher postings never state
  years; those return None and are judged on title alone.
"""
import re

# "5 years", "5+ yrs", "3-5 years", "3 to 5 years"
_YEARS = r"(\d{1,2})\s*(?:\+|(?:\s*(?:-|–|—|to)\s*(\d{1,2})))?\s*\+?\s*(?:years?|yrs?)"

# The mention must sit near language that makes it a *requirement*, otherwise
# "our platform has served users for 10 years" would read as a demand.
_CONTEXT = (
    r"experience|exp\b|working|worked|building|built|developing|developed|"
    r"professional|industry|background|track record|hands[\s-]?on|"
    r"in (?:a |an )?(?:similar|related|technical)|as an?\b|of\b|in\b|with\b"
)

_PATTERNS = [
    # "<n> years ... <context>"   e.g. "5-7+ years in technical roles"
    re.compile(rf"{_YEARS}[^.\n]{{0,50}}?(?:{_CONTEXT})", re.IGNORECASE),
    # "<context> ... <n> years"   e.g. "experience: 5+ years"
    re.compile(rf"(?:experience|minimum|at least|requires?|must have)[^.\n]{{0,40}}?{_YEARS}",
               re.IGNORECASE),
]

# Phrases that make a nearby number historical rather than a requirement.
_NOT_A_REQUIREMENT = re.compile(
    r"(?:past|last|next|previous|recent|over the|within the|for the)\s*$"
    r"|(?:ago|founded|since|history|anniversary)",
    re.IGNORECASE,
)


def required_years(text: str) -> int | None:
    """Highest stated experience bar in the text, or None if none is stated."""
    if not text:
        return None

    bars: list[int] = []
    for pattern in _PATTERNS:
        for match in pattern.finditer(text):
            preceding = text[max(0, match.start() - 25) : match.start()]
            if _NOT_A_REQUIREMENT.search(preceding):
                continue
            low = _first_int(match.groups())
            if low is not None and low <= 20:
                bars.append(low)
    return max(bars) if bars else None


def _first_int(groups) -> int | None:
    """The lower bound of the match — the first captured number."""
    for value in groups:
        if value is not None:
            return int(value)
    return None
