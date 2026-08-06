"""This filter decides which jobs are worth an expensive LLM call, so its
false-negatives cost us real opportunities."""
import pytest

from app.ingestion.seniority import is_fresher_friendly


@pytest.mark.parametrize(
    ("title", "expected"),
    [
        # Clearly open to a fresher
        ("Software Engineer", True),
        ("Backend Engineer", True),
        ("SDE Intern", True),
        ("Software Engineering Intern - Summer 2026", True),
        ("Graduate Engineer Trainee", True),
        ("Junior Data Analyst", True),
        ("Associate Product Manager", True),  # explicit entry-level track
        ("Software Engineer I", True),
        # Clearly senior
        ("Senior Software Engineer", False),
        ("Sr. Backend Engineer", False),
        ("Staff Engineer, Platform", False),
        ("Principal Data Scientist", False),
        ("Engineering Manager", False),
        ("Director of Engineering", False),
        ("Head of Product", False),
        ("Solutions Architect", False),
        ("Software Engineer II", False),
        ("Backend Engineer III", False),
        # "Intermediate" reads junior but means mid-level.
        ("Intermediate Backend Engineer - Analytics", False),
        ("Intermediate Fullstack Engineer - Data Products", False),
        ("Mid-Level Software Engineer", False),
        # Word-boundary traps
        ("Managed Services Engineer", True),  # "Managed" is not "Manager"
        ("Leadership Development Program Analyst", True),  # "Leadership" != "Lead"
    ],
)
def test_is_fresher_friendly(title: str, expected: bool) -> None:
    assert is_fresher_friendly(title) is expected
