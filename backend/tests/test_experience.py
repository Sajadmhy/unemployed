"""Reading the years requirement out of the description text.

This runs on every job, including the ones the LLM tier never reaches, so it is
the only thing standing between a fresher and a list full of 8-year roles.
Phrasings below are taken from real postings in the job pool.
"""
import pytest

from app.ingestion.experience import required_years


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        # --- real phrasings from ingested jobs ---
        ("REQUIRED SKILLS AND EXPERIENCE: - 5-7+ years in technical customer-facing roles", 5),
        ("8+ years of experience building distributed systems", 8),
        ("Minimum 3 years of experience with Python", 3),
        ("At least 2 years of professional software development experience", 2),
        ("3 to 5 years of experience in data engineering", 3),
        ("10+ yrs experience in enterprise support", 10),
        # --- ranges count as their lower bound ---
        ("0-2 years of experience", 0),
        ("1-3 years of experience preferred", 1),
        # --- the highest bar wins across several mentions ---
        ("5+ years of experience overall. 2+ years working with Python.", 5),
        # --- silence is not a rejection ---
        ("We are looking for a passionate engineer to join our team.", None),
        ("Fresh graduates are encouraged to apply.", None),
        ("", None),
        (None, None),
        # --- numbers that are not requirements ---
        ("Our platform has served customers for the past 10 years.", None),
        ("The company was founded 12 years ago.", None),
    ],
)
def test_required_years(text: str, expected: int | None) -> None:
    assert required_years(text) == expected


def test_fresher_range_survives_a_strict_limit() -> None:
    """A 0-2 posting must stay visible when max_years is 1."""
    assert (required_years("0-2 years of experience") or 0) <= 1


def test_senior_posting_is_caught_even_without_the_word_experience() -> None:
    """The leak that started this: years stated without the word "experience"."""
    assert required_years("5-7+ years in technical customer-facing roles") == 5
