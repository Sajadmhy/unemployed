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
