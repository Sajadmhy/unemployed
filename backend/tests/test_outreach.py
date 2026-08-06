"""Outreach search construction.

No network, no scraping — the whole feature is building a good query and letting
the user run it, so the query is what gets tested.
"""
from types import SimpleNamespace
from urllib.parse import unquote_plus

import pytest

from app.ai.match import preference_fit
from app.ai.outreach import _role_keywords, build_contacts


def job(company: str = "Atlan", title: str = "Software Engineer") -> SimpleNamespace:
    return SimpleNamespace(company=company, title=title)


def profile(college: str = "VIT Vellore") -> SimpleNamespace:
    return SimpleNamespace(college=college, name="Candidate")


def test_all_five_categories_when_a_college_is_known() -> None:
    contacts = build_contacts(job(), profile())
    assert [c["category"] for c in contacts] == [
        "alumni",
        "recruiter",
        "eng_leader",
        "same_role",
        "founder",
    ]


def test_alumni_is_skipped_without_a_college() -> None:
    """No college means no alumni query — better to omit than to search garbage."""
    categories = [c["category"] for c in build_contacts(job(), profile(college=""))]
    assert "alumni" not in categories
    assert len(categories) == 4


def test_queries_are_scoped_to_linkedin_profiles_and_the_company() -> None:
    for contact in build_contacts(job(company="Razorpay"), profile()):
        query = unquote_plus(contact["search_url"])
        assert "site:linkedin.com/in" in query
        assert "Razorpay" in query


def test_alumni_query_includes_the_college() -> None:
    alumni = build_contacts(job(), profile("VIT Vellore"))[0]
    assert "VIT Vellore" in unquote_plus(alumni["search_url"])


@pytest.mark.parametrize(
    ("title", "expected"),
    [
        ("Software Engineer II - Backend (Platform)", "Software Engineer"),
        ("Senior Data Engineer, Analytics", "Senior Data Engineer"),
        ("SDE Intern", "SDE Intern"),
        ("Backend Engineer (Remote)", "Backend Engineer"),
    ],
)
def test_role_keywords_strips_levels_and_qualifiers(title: str, expected: str) -> None:
    assert _role_keywords(title) == expected


# ---- preference_fit ---------------------------------------------------------
def pjob(location: str, remote: bool = False) -> SimpleNamespace:
    return SimpleNamespace(location=location, remote=remote)


def test_preference_fit_is_neutral_without_preferences() -> None:
    """Someone who never opened settings must not be penalised."""
    assert preference_fit(pjob("Bengaluru, India"), None) == 0.5


def test_preferred_city_outranks_another_indian_city() -> None:
    prefs = SimpleNamespace(preferred_locations=["Bengaluru"], remote_ok=True)
    assert preference_fit(pjob("Bengaluru, India"), prefs) == 1.0
    assert preference_fit(pjob("Chennai, India"), prefs) == 0.4


def test_remote_respects_the_remote_flag() -> None:
    yes = SimpleNamespace(preferred_locations=["Bengaluru"], remote_ok=True)
    no = SimpleNamespace(preferred_locations=["Bengaluru"], remote_ok=False)
    assert preference_fit(pjob("Remote - India", remote=True), yes) == 1.0
    assert preference_fit(pjob("Remote - India", remote=True), no) == 0.3
