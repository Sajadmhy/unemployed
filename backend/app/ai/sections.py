"""Which resume section each kind of accomplishment belongs under.

One table, because there used to be two and they disagreed. `generate_resume`
folded certifications into "Achievements" while `latex` treated them as a
first-class section with its own rules, so the same knowledge base produced a
different shape depending on which renderer you asked for. Worse, `skill` chunks
matched neither list and fell through a bare `return "Projects"`, which is how
somebody's skills ended up printed as a project.

The order here is the order sections are printed in, and it is the conventional
one: what you did, then what you built, then what you were given, then what you
know, then where you studied. Parsers look for these exact words, which is the
other reason the list is fixed in code rather than written by a model.
"""

import re

EXPERIENCE = "Experience"
PROJECTS = "Projects"
ACHIEVEMENTS = "Achievements"
CERTIFICATIONS = "Certifications"
EDUCATION = "Education"

# Chunk type -> section heading.
_BY_TYPE: dict[str, str] = {
    "experience": EXPERIENCE,
    "leadership": EXPERIENCE,
    "project": PROJECTS,
    "achievement": ACHIEVEMENTS,
    "certification": CERTIFICATIONS,
    "education": EDUCATION,
}

# Printed in this order when present. "Skills" is not here: it is computed from
# the job description rather than written as bullets, so pdf.py places it itself.
ORDER: tuple[str, ...] = (EXPERIENCE, PROJECTS, ACHIEVEMENTS, CERTIFICATIONS, EDUCATION)

# How many bullets each section may contribute.
#
# This replaces a single cap of eight across the whole resume, which was applied
# in the order the model happened to return things. Eight bullets could all land
# in Experience, and every other section then rendered empty and vanished, since
# a heading is only printed when it has something under it. A per-section budget
# is the difference between a short resume and a resume missing its projects.
#
# Education and certifications are facts rather than prose, so they are allowed
# more entries and shorter ones.
QUOTAS: dict[str, int] = {
    EXPERIENCE: 8,
    PROJECTS: 5,
    ACHIEVEMENTS: 4,
    CERTIFICATIONS: 5,
    EDUCATION: 4,
}

# Experience is budgeted per job, not per section, because every job the
# candidate has held must appear: a job whose bullets do not match the posting is
# still a job. Newest first, so the current role gets the most room.
JOB_BULLET_CAPS: tuple[int, ...] = (9, 4, 3)
JOB_BULLET_CAP_DEFAULT = 2
# Keeps the page to about one sheet however long the career is; older jobs give
# up bullets first, and none goes below one.
EXPERIENCE_MAX = 16

# The most bullets any one resume can carry. A backstop for the pathological
# case where every section fills its quota on a one page document.
MAX_TOTAL = 20


def section_for(chunk_type: str | None) -> str:
    """The section this chunk type prints under.

    An unknown type is a project, which is the honest default for "something the
    candidate did that we cannot place" and the only one of these headings that
    does not assert an employer, a credential or a degree.
    """
    return _BY_TYPE.get((chunk_type or "").lower().strip(), PROJECTS)


def quota_for(section: str) -> int:
    return QUOTAS.get(section, 4)


_MONTHS = {m: i for i, m in enumerate(
    ("jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"), 1)}
_PRESENT = re.compile(r"\b(present|current|now|today|ongoing)\b", re.I)
_DATE = re.compile(r"(?:\b([A-Za-z]{3})[a-z]*\.?\s+)?\b((?:19|20)\d{2})\b|\b(\d{1,2})/((?:19|20)\d{2})\b")


def recency(dates: str) -> tuple[int, int, int, int] | None:
    """(end year, end month, start year, start month) for sorting; None if undated."""
    points = []
    for mon, year, num_mon, num_year in _DATE.findall(dates or ""):
        if year:
            points.append((int(year), _MONTHS.get(mon[:3].lower(), 0) if mon else 0))
        else:
            points.append((int(num_year), int(num_mon)))
    if not points:
        return None
    start = points[0]
    end = (9999, 12) if _PRESENT.search(dates) else points[-1]
    return (*end, *start)
