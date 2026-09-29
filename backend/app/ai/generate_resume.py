"""RAG resume generation: rewrite real accomplishments for one specific job.

The model is never asked "write a resume". It is given a numbered list of the
candidate's *verified* accomplishments and asked to rephrase selected ones for
this job. That distinction is the whole design — it can only reword facts that
already exist.

Three independent layers stop invention, because prompts alone are not a
guarantee:

1. **Retrieval** — only real KB chunks ever enter the context window.
2. **Prompt** — explicit "use only these facts, omit rather than invent, cite the
   id you used".
3. **Validation** — every produced bullet must cite a real chunk id, and every
   number in a bullet must already appear in the chunk it cites. A bullet that
   fails is dropped, not shipped. Invented metrics ("improved performance by
   40%") are the single most dangerous resume hallucination, so they are checked
   mechanically rather than trusted.
"""
import logging
import re
from collections import Counter, defaultdict

from app.ai.llm import fits_context, generate_json
from app.ai.sections import (
    EXPERIENCE,
    EXPERIENCE_MAX,
    JOB_BULLET_CAP_DEFAULT,
    JOB_BULLET_CAPS,
    MAX_TOTAL,
    quota_for,
    recency,
    section_for,
)
from app.db.models import KBChunk

log = logging.getLogger(__name__)

# Kept as the number quoted to the model, not as a hard stop on the output.
# Sections are budgeted individually in `_validate_bullets`, because a single
# global cap applied in arrival order let eight Experience bullets use the whole
# resume and leave Projects, Education and Certifications printing nothing.
MAX_BULLETS = MAX_TOTAL

# ONE job per call. Asking a small model for summary + skills + bullets in a
# single schema makes it answer the easy parts and silently drop the hard one,
# so rewriting bullets — the only genuinely generative task here — gets the whole
# call and the smallest schema that can express the answer.
_SYSTEM = """You rewrite a candidate's REAL accomplishments as resume bullets for one specific job.

You are given the candidate's complete record. Your job is selection and phrasing, not invention.

SELECTION
- Read every numbered accomplishment before choosing. The best evidence for this job is often not the first one listed.
- Include every accomplishment that is relevant to this job, strongest first. Leave out only what is clearly irrelevant.
- Give the most recent role the most bullets (typically 3-6); older or shorter roles 1-3 each.
- Aim for 8-14 bullets in total when the record supports it. Never write two bullets from the same accomplishment.
- You need not cover every role: anything you leave out is still printed, in the candidate's own words, after your bullets for that role.

PHRASING
- Start with a strong past-tense verb. One sentence, max 30 words.
- Lead with the outcome or the thing built, then how.
- Where the accomplishment genuinely supports it, use the job's own words for the same thing: if it says "RESTful APIs" and the accomplishment says "REST services", write "RESTful APIs". Matching the job's vocabulary is how automated screeners find you.

TRUTH
- Use ONLY the numbered accomplishments provided. Never invent experience, employers, technologies or metrics.
- Every bullet MUST include "source_id": the number of the accomplishment it came from.
- Never introduce a number, percentage or metric that is not already in that accomplishment.
- Never claim a skill the job wants but the accomplishments do not show.
- Never add scale or outcome words ("thousands of users", "significantly", "improved performance") that the accomplishment does not state.

Respond with JSON in exactly this shape:
{"bullets":[{"source_id":1,"text":"Built X using Y, serving Z users"},{"source_id":3,"text":"..."}]}"""


def generate(profile, job, requirements: dict, chunks: list[KBChunk]) -> dict:
    """Generate a tailored resume. Returns bullets already validated for truthfulness.

    Every job in the candidate's experience is printed. The model only decides
    which accomplishments are worth rewording for this posting and in what order;
    a job it found nothing relevant in is printed with its own words, unchanged.
    """
    if not chunks:
        return {"summary": "", "skills": [], "bullets": [], "rejected": []}

    everything = list(chunks)  # ranked, and complete: the window trim below must not lose a job

    # The whole knowledge base goes into one call, and a knowledge base has no
    # size limit. Past the context window Ollama drops the front of the prompt
    # without saying so, which reads as the model having ignored the earliest
    # half of a career. Dropping the least relevant chunks ourselves is worse
    # than sending everything and better than being silently truncated: the
    # chunks arrive ranked, so what goes is what mattered least to this job.
    chunks = _fit_to_window(job, requirements, chunks)

    prompt = _build_prompt(job, requirements, chunks)
    raw = generate_json(_SYSTEM, prompt, timeout=300, max_tokens=2000)

    by_id = {i + 1: chunk for i, chunk in enumerate(chunks)}
    validated, rejected = _validate_bullets(raw.get("bullets"), by_id)
    bullets = _assemble(validated, everything)
    skills = select_skills(requirements, everything)

    return {
        "summary": write_profile(job, requirements, bullets, skills),
        "skills": skills,
        "bullets": bullets,
        "rejected": rejected,
    }


def _job_key(chunk: KBChunk) -> tuple:
    """Chunks of one job share an employer and dates; without them, the title."""
    company = (chunk.company or "").strip().lower()
    dates = (chunk.date_range or "").strip().lower()
    return (company, dates) if company or dates else (((chunk.title or "").strip().lower()),)


def _bullet(chunk: KBChunk, text: str, meta: dict) -> dict:
    return {
        "text": text,
        "source_chunk_ids": [chunk.id],
        "section": EXPERIENCE,
        "title": meta["title"],
        "context": chunk.context,
        "company": meta["company"],
        "date_range": meta["date_range"],
    }


def _commonest(group: list[KBChunk], field: str) -> str:
    values = [(getattr(c, field) or "").strip() for c in group]
    values = [v for v in values if v]
    return Counter(values).most_common(1)[0][0] if values else ""


def _assemble(validated: list[dict], everything: list[KBChunk]) -> list[dict]:
    """Experience gets every job; the other sections keep what the model chose.

    Within a job: the accomplishments the model reworded for this posting come
    first, in the order it ranked them, then the rest in retrieval order and in
    the candidate's own words. A job with nothing relevant is therefore printed
    as written. Jobs stay in date order (the renderer sorts them); this only
    decides how many bullets each may take, newest job most.

    Those reworded bullets already passed the truthfulness checks. The rest are
    the candidate's own text, which needs none.
    """
    others = [b for b in validated if b["section"] != EXPERIENCE]
    reworded = {b["source_chunk_ids"][0]: (rank, b) for rank, b in enumerate(validated)
                if b["section"] == EXPERIENCE}

    jobs: dict[tuple, list[KBChunk]] = {}
    for c in everything:
        if section_for(c.type) == EXPERIENCE and (c.type or "").lower() != "skill":
            jobs.setdefault(_job_key(c), []).append(c)

    def when(group: list[KBChunk]):
        dated = [recency(c.date_range or "") for c in group]
        return max((d for d in dated if d), default=(0, 0, 0, 0))

    ordered = sorted(jobs.values(), key=when, reverse=True)

    lists: list[list[dict]] = []
    for position, group in enumerate(ordered):
        cap = JOB_BULLET_CAPS[position] if position < len(JOB_BULLET_CAPS) else JOB_BULLET_CAP_DEFAULT
        # One heading per job: the commonest title/dates among its accomplishments.
        meta = {f: _commonest(group, f) for f in ("title", "company", "date_range")}
        relevant = sorted((reworded[c.id] for c in group if c.id in reworded), key=lambda rb: rb[0])
        first = [{**b, **meta} for _, b in relevant]
        rest = [_bullet(c, c.accomplishment.strip(), meta) for c in group
                if c.id not in reworded and (c.accomplishment or "").strip()]
        lists.append((first + rest)[:cap])

    # Older jobs give up bullets first when the page would overflow; none loses its last.
    while sum(len(l) for l in lists) > EXPERIENCE_MAX:
        for l in reversed(lists):
            if len(l) > 1:
                l.pop()
                break
        else:
            break

    return [b for l in lists for b in l] + others


# The profile paragraph. Its own call, for the same reason the bullets have theirs.
_PROFILE_SYSTEM = """You write the profile paragraph at the top of a resume, for one specific job.

Write it the way the candidate would on a good day: plain, specific, a little understated.

FORMAT
- One paragraph of 2 or 3 sentences, 40 to 65 words. No line breaks, bullets or headings.
- No "I", no name, no "he", "she" or "they".
- Open with the role the candidate actually holds or held, for example "Full-stack developer ...".
- Then say what they work on, naming two or three concrete things from the facts: a product, a kind of system, the main technologies.
- Close by tying that work to what this job needs, only where the facts support it.

STYLE (this is what keeps it from sounding machine-written)
- Ordinary words and short sentences. Concrete nouns, not adjectives.
- Never use: passionate, driven, dynamic, results-oriented, results-driven, seasoned, track record, cutting-edge, innovative, leverage, spearhead, robust, seamless, synergy, dedicated, motivated, detail-oriented, eager, thrive, fast-paced, well-versed, adept, skilled in, expertise, deep understanding, wide range, proficient.
- No dashes. No "not just X but Y". No run of three adjectives.
- Do not name the company hiring, and do not say the candidate is applying.

TRUTH
- Use only the facts given. Never invent employers, technologies, numbers, achievements or scale.
- Do not state a number of years of experience.
- Do not claim a skill the job asks for that the facts do not show.

Respond with JSON in exactly this shape: {"profile": "..."}"""

_PROFILE_BANNED = re.compile(
    r"passionate|driven|dynamic|results[- ]?(?:oriented|driven)|seasoned|track record|cutting[- ]edge|"
    r"innovative|leverag|spearhead|robust|seamless|synerg|dedicated|motivated|detail[- ]oriented|eager|"
    r"thrive|fast[- ]paced|well[- ]versed|adept|skilled in|expertise|deep understanding|wide range|"
    r"proficient|not just|\bI\b|\bI'm\b|\bmy\b|\bhe\b|\bshe\b|\bthey\b|applying",
    re.IGNORECASE,
)


def write_profile(job, requirements: dict, bullets: list[dict], skills: list[str]) -> str:
    """One short, plain paragraph about the candidate, aimed at this job.

    Built only from what is already on the resume and the posting, and checked
    mechanically afterwards: no figure that is not in those facts, no stock
    résumé phrases, one paragraph of sensible length. If two attempts fail the
    checks, a one-line factual profile is used instead of shipping a bad one.
    """
    jobs = []
    for b in bullets:
        if b["section"] == EXPERIENCE and (b["title"], b["company"], b["date_range"]) not in jobs:
            jobs.append((b["title"], b["company"], b["date_range"]))
    if not jobs:
        return ""
    title, company, dates = jobs[0]

    facts = [
        f"Current or most recent role: {title}" + (f" at {company}" if company else "")
        + (f" ({dates})" if dates else ""),
    ]
    if len(jobs) > 1:
        facts.append("Earlier roles: " + "; ".join(
            f"{t}" + (f" at {c}" if c else "") for t, c, _ in jobs[1:4]))
    if skills:
        facts.append("Main technologies: " + ", ".join(skills[:10]))
    facts.append("Work on the resume:")
    facts += [f"- {b['text']}" for b in bullets[:8]]
    description = " ".join((getattr(job, "description", "") or "").split())[:700]
    prompt = "\n".join([
        f"JOB: {job.title}",
        f"Required skills: {', '.join(requirements.get('required_skills', [])) or 'not specified'}",
        f"Responsibilities: {'; '.join(requirements.get('responsibilities', [])[:5]) or 'not specified'}",
        f"Posting excerpt: {description}" if description else "",
        "",
        "CANDIDATE FACTS (the only facts you may use):",
        *facts,
    ])

    allowed_numbers = set(_numbers(" ".join(facts)))
    problem = ""
    for attempt in range(2):
        note = f"\n\nYour last attempt was rejected: {problem}. Rewrite it." if problem else ""
        try:
            raw = generate_json(_PROFILE_SYSTEM, prompt + note, timeout=120, max_tokens=300)
        except Exception as e:  # noqa: BLE001 - the resume is still worth sending without it
            log.warning("profile call failed: %s", e)
            break
        text = _tidy_profile(str(raw.get("profile") or "") if isinstance(raw, dict) else "")
        problem = _profile_problem(text, allowed_numbers)
        if not problem:
            return text
        log.info("profile attempt %d rejected: %s", attempt + 1, problem)

    log.warning("using the plain profile; last problem: %s", problem)
    return _plain_profile(title, company, skills)


def _tidy_profile(text: str) -> str:
    text = re.sub(r"\s*[\u2013\u2014]\s*", ", ", " ".join(text.split()))
    return text.strip().strip('"').strip()


def _profile_problem(text: str, allowed_numbers: set[str]) -> str:
    words = len(text.split())
    if not 30 <= words <= 75:
        return f"it has {words} words; aim for 40 to 65"
    banned = _PROFILE_BANNED.search(text)
    if banned:
        return f'it contains "{banned.group(0)}", which is not allowed'
    invented = [n for n in _numbers(text) if n not in allowed_numbers]
    if invented:
        return f"it states {', '.join(invented)}, which is not in the facts"
    return ""


def _plain_profile(title: str, company: str, skills: list[str]) -> str:
    role = f"{title} at {company}" if company else title
    tech = ", ".join(skills[:4])
    return f"{role}" + (f", working with {tech}." if tech else ".")


def select_skills(requirements: dict, chunks: list[KBChunk], limit: int = 18) -> list[str]:
    """The skills section, computed rather than generated.

    It is exactly "what this job asks for" ∩ "what the KB actually evidences",
    required first. Deterministic, so it can never claim a skill the candidate
    does not have, and it always speaks the JD's vocabulary.
    """
    evidence = _norm(
        " ".join(
            f"{c.title} {c.accomplishment} {c.impact or ''} "
            f"{' '.join(c.technologies or [])} {' '.join(c.skills or [])}"
            for c in chunks
        )
    )

    selected: list[str] = []
    for skill in list(requirements.get("required_skills", [])) + list(
        requirements.get("preferred_skills", [])
    ):
        name = str(skill).strip()
        if name and _evidenced(name, evidence) and _skill_key(name) not in {_skill_key(s) for s in selected}:
            selected.append(name)

    # Top up with the candidate's own strongest technologies so the section is
    # never near-empty just because the JD listed few skills.
    for chunk in chunks:
        for tech in chunk.technologies or []:
            name = str(tech).strip()
            if len(selected) >= limit:
                break
            if name and _skill_key(name) not in {_skill_key(s) for s in selected}:
                selected.append(name)
    return selected[:limit]


def _skill_key(name: str) -> str:
    """"React" and "React.js", "Node" and "Node.js": one skill, printed once."""
    return re.sub(r"[^a-z0-9+#]", "", re.sub(r"\.?js$", "", name.strip().lower()))


def _evidenced(name: str, evidence: str) -> bool:
    term = _norm(name)
    if not term:
        return False
    return re.search(rf"(?<![a-z0-9]){re.escape(term)}(?![a-z0-9])", evidence) is not None


def _fit_to_window(job, requirements: dict, chunks: list[KBChunk]) -> list[KBChunk]:
    """Trim the tail of the ranked list until the prompt fits the context window.

    Halving rather than dropping one at a time: this is a loop over string
    building, and a knowledge base large enough to overflow is large enough that
    one-by-one would rebuild the prompt hundreds of times.
    """
    kept = list(chunks)
    while kept and not fits_context(_SYSTEM, _build_prompt(job, requirements, kept), 2000):
        if len(kept) == 1:
            break  # one enormous chunk. Send it and let the model see what fits.
        kept = kept[: max(1, len(kept) // 2)]
    return kept


def _build_prompt(job, requirements: dict, chunks: list[KBChunk]) -> str:
    lines = [
        f"TARGET JOB: {job.title} at {job.company}",
        f"Required skills: {', '.join(requirements.get('required_skills', [])) or 'not specified'}",
        f"Preferred skills: {', '.join(requirements.get('preferred_skills', [])) or 'not specified'}",
        "",
        "CANDIDATE'S VERIFIED ACCOMPLISHMENTS (the only facts you may use):",
    ]
    for i, chunk in enumerate(chunks, start=1):
        context = " | ".join(
            part for part in [chunk.company, chunk.date_range, chunk.context] if part
        )
        tech = ", ".join(chunk.technologies or [])
        lines.append(f"\n[{i}] {chunk.title}" + (f" ({context})" if context else ""))
        lines.append(f"    {chunk.accomplishment}")
        if tech:
            lines.append(f"    Technologies: {tech}")
        if chunk.impact:
            lines.append(f"    Impact: {chunk.impact}")
    lines.append(
        f"\nWrite at most {MAX_BULLETS} bullets, most relevant first, each citing its source_id."
    )
    return "\n".join(lines)


def _validate_bullets(raw_bullets, by_id: dict[int, KBChunk]) -> tuple[list[dict], list[dict]]:
    """Keep only bullets that trace to a real chunk and invent no new numbers."""
    kept: list[dict] = []
    rejected: list[dict] = []
    used: dict[str, int] = defaultdict(int)
    cited: set[int] = set()
    if not isinstance(raw_bullets, list):
        return kept, rejected

    for item in raw_bullets:
        if not isinstance(item, dict):
            continue
        text = str(item.get("text") or "").strip()
        source_id = _as_int(item.get("source_id"))
        if not text:
            continue

        chunk = by_id.get(source_id)
        if chunk is None:
            rejected.append({"text": text, "reason": "cites no valid source accomplishment"})
            continue
        # A skills-list line is evidence for the Skills section, not a bullet:
        # it has no section of its own and would otherwise print under Projects.
        if (chunk.type or "").lower() == "skill":
            continue
        # One accomplishment, one bullet. A model stuck in a loop cites the same
        # source over and over; the first (strongest-ranked) phrasing stands.
        if source_id in cited:
            continue
        cited.add(source_id)

        invented = _invented_numbers(text, chunk)
        if invented:
            rejected.append(
                {"text": text, "reason": f"invented metric(s) not in source: {', '.join(invented)}"}
            )
            continue

        section = section_for(chunk.type)
        # Budgeted per section rather than globally. Bullets arrive strongest
        # first, so a full section drops its weakest candidates and every other
        # section still gets to print.
        if section != EXPERIENCE and used[section] >= quota_for(section):
            continue

        used[section] += 1
        kept.append(
            {
                "text": text,
                "source_chunk_ids": [chunk.id],
                "section": section,
                "title": chunk.title,
                "context": chunk.context,
                "company": chunk.company,
                "date_range": chunk.date_range,
            }
        )
    return kept, rejected


def _invented_numbers(text: str, chunk: KBChunk) -> list[str]:
    """Any figure in the bullet must already exist in its source accomplishment."""
    source = " ".join(
        [chunk.accomplishment or "", chunk.impact or "", chunk.title or "",
         " ".join(chunk.technologies or [])]
    )
    source_numbers = set(_numbers(source))
    return [n for n in _numbers(text) if n not in source_numbers]


def _numbers(text: str) -> list[str]:
    """Digit groups, ignoring those glued to words (python3, s3, ipv6)."""
    return re.findall(r"(?<![A-Za-z])(\d[\d,.]*)", text or "")


def _as_int(value) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return -1


def _norm(text: str) -> str:
    """Collapse whitespace runs so multi-word skills match across line breaks."""
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9+#. ]+", " ", (text or "").lower())).strip()
