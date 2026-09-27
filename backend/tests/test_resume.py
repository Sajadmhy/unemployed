"""The truthfulness guarantees are the product's core promise, so the validator
gets tested harder than anything else: a bullet that cannot be traced to a real
accomplishment, or that invents a metric, must never reach the page."""
from types import SimpleNamespace

import pytest

from app.ai.ats import keyword_coverage
from app.ai.generate_resume import _invented_numbers, _validate_bullets, select_skills
from app.ai.retrieve import _fuse


def chunk(chunk_id: int, title: str, accomplishment: str, technologies=(), impact=None):
    return SimpleNamespace(
        id=chunk_id,
        type="project",
        title=title,
        accomplishment=accomplishment,
        impact=impact,
        context=None,
        company=None,
        date_range=None,
        technologies=list(technologies),
        skills=[],
    )


@pytest.fixture
def chunks():
    return [
        chunk(
            10,
            "Chat app",
            "Built a WebSocket backend handling 200 concurrent users",
            technologies=["Python", "FastAPI"],
            impact="Used by 3 clubs",
        ),
        chunk(11, "Portfolio", "Built a personal site", technologies=["Next.js"]),
    ]


# ---- Traceability: a bullet must cite a real accomplishment ------------------
def test_bullet_without_valid_source_is_rejected(chunks) -> None:
    by_id = {1: chunks[0], 2: chunks[1]}
    kept, rejected = _validate_bullets(
        [{"source_id": 99, "text": "Led a team of 12 engineers"}], by_id
    )
    assert kept == []
    assert "no valid source" in rejected[0]["reason"]


def test_valid_bullet_is_kept_with_its_chunk_id(chunks) -> None:
    by_id = {1: chunks[0]}
    kept, rejected = _validate_bullets(
        [{"source_id": 1, "text": "Built a realtime backend serving 200 users"}], by_id
    )
    assert rejected == []
    assert kept[0]["source_chunk_ids"] == [10]
    assert kept[0]["section"] == "Projects"


# ---- The dangerous one: invented metrics ------------------------------------
def test_invented_metric_is_rejected(chunks) -> None:
    by_id = {1: chunks[0]}
    kept, rejected = _validate_bullets(
        [{"source_id": 1, "text": "Improved latency by 40% for 5000 users"}], by_id
    )
    assert kept == []
    assert "invented metric" in rejected[0]["reason"]


def test_numbers_present_in_source_are_allowed(chunks) -> None:
    assert _invented_numbers("Handled 200 concurrent users", chunks[0]) == []
    assert _invented_numbers("Used by 3 clubs", chunks[0]) == []
    assert _invented_numbers("Served 9000 users", chunks[0]) == ["9000"]


def test_numbers_inside_words_are_not_metrics(chunks) -> None:
    """python3 / S3 / OAuth2 are names, not invented statistics."""
    c = chunk(1, "API", "Built services on S3 with python3 and OAuth2")
    assert _invented_numbers("Built services on S3 using python3 and OAuth2", c) == []


# ---- Skills are computed, never generated -----------------------------------
def test_skills_are_jd_terms_evidenced_by_the_kb(chunks) -> None:
    skills = select_skills(
        {"required_skills": ["Python", "Kubernetes"], "preferred_skills": ["FastAPI"]},
        chunks,
    )
    assert "Python" in skills and "FastAPI" in skills
    assert "Kubernetes" not in skills  # not in the KB -> never claimed


# ---- Reciprocal Rank Fusion --------------------------------------------------
def test_rrf_rewards_chunks_found_by_both_retrievers(chunks) -> None:
    a, b = chunks[0], chunks[1]
    # b is 2nd in the vector list but 1st lexically; a is 1st then absent.
    fused = _fuse([a, b], [b])
    assert fused[0] is b


# ---- ATS keyword coverage ----------------------------------------------------
def test_keyword_coverage_reports_missing_terms() -> None:
    resume = {
        "summary": "",
        "skills": ["Python"],
        "bullets": [{"text": "Built a FastAPI service", "title": "API"}],
    }
    report = keyword_coverage(resume, {"required_skills": ["Python", "Kubernetes"]})
    assert report["required_matched"] == ["Python"]
    assert report["required_missing"] == ["Kubernetes"]
    assert report["coverage"] == 0.5


def test_multiword_skill_matches_across_a_line_wrap() -> None:
    """PDF text extraction wraps lines; a skill split across one must still match."""
    resume = {
        "summary": "",
        "skills": [],
        "bullets": [{"text": "Integrated GitHub / Jira /\nSlack APIs", "title": "Alfred"}],
    }
    report = keyword_coverage(resume, {"required_skills": ["GitHub / Jira / Slack APIs"]})
    assert report["required_missing"] == []


# ---- entry order and headings in the PDF ------------------------------------
import pdfplumber  # noqa: E402

from app.ai import pdf as _pdf  # noqa: E402


def test_recency_parses_common_formats():
    assert _pdf._recency("Feb 2023 - Present") == (9999, 12, 2023, 2)
    assert _pdf._recency("Jul 2022 – Nov 2022") == (2022, 11, 2022, 7)
    assert _pdf._recency("2019-2021") == (2021, 0, 2019, 0)
    assert _pdf._recency("03/2020 - 05/2021") == (2021, 5, 2020, 3)
    assert _pdf._recency("") is None


def test_experience_prints_newest_first_and_employer_once(tmp_path):
    class P:
        name, email, phone, location, links, education = "A", "a@b.c", "", "", {}, ""

    def b(title, company, dates, text):
        return {"text": text, "section": "Experience", "title": title,
                "company": company, "date_range": dates}

    resume = {"skills": [], "bullets": [  # relevance order, as the model returns it
        b("Full-Stack Developer Paiger", "Paiger", "Feb 2023 - Present", "Built workflows"),
        b("Front-End Developer", "Lolo Co", "Jul 2022 - Nov 2022", "Built site"),
        b("Front-End Developer", "Classeh", "Nov 2022 - Feb 2023", "Worked with team"),
        b("Apprentice", "100 Devs", "May 2022 - Jul 2022", "Contributed"),
    ]}
    out = _pdf.render(P(), resume, tmp_path / "r.pdf")
    text = pdfplumber.open(out).pages[0].extract_text()
    positions = [text.index(c) for c in ("Paiger |", "Classeh", "Lolo Co", "100 Devs")]
    assert positions == sorted(positions)
    assert "Full-Stack Developer Paiger" not in text and "Full-Stack Developer" in text


def test_pdf_text_has_no_question_marks_for_unicode_hyphens():
    assert _pdf._safe("Front‑End, full‐stack, a b, x​y") == "Front-End, full-stack, a b, xy"


def test_skills_listed_once_across_js_suffix():
    from app.ai.generate_resume import _skill_key
    assert _skill_key("React") == _skill_key("React.js") == _skill_key("ReactJS".replace("JS", ".js"))
    assert _skill_key("Node.js") == _skill_key("node")
    assert _skill_key("C#") != _skill_key("C++")
