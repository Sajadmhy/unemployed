"""Long documents are split, not truncated.

The old behaviour cut a document at 12k characters, which on a real CV meant the
second half of someone's career silently never reached the model.
"""
from app.ai.parse import _SEGMENT_CHARS, segment


def test_a_short_document_is_one_segment() -> None:
    assert segment("Built a payments API.") == ["Built a payments API."]


def test_an_empty_document_is_no_segments() -> None:
    assert segment("   \n\n  ") == []


def test_a_long_document_is_split_and_nothing_is_lost() -> None:
    paragraphs = [f"Accomplishment {i}: " + "x" * 900 for i in range(40)]
    text = "\n\n".join(paragraphs)

    segments = segment(text)

    assert len(segments) > 1, "a 36k-character CV must not go in one call"
    assert all(len(s) <= _SEGMENT_CHARS for s in segments)
    # Every paragraph survives somewhere — the point of the change.
    joined = "\n\n".join(segments)
    for i in range(40):
        assert f"Accomplishment {i}:" in joined


def test_splits_fall_between_paragraphs() -> None:
    """Cutting mid-bullet would hand the model half an accomplishment."""
    text = "\n\n".join(f"Bullet {i}: " + "y" * 3000 for i in range(10))
    for piece in segment(text):
        assert piece.startswith("Bullet ")
        assert not piece.endswith("\n")


def test_windows_line_endings_still_split() -> None:
    """A .txt uploaded from Windows arrives as CRLF; splitting on "\\n\\n" alone
    matches nothing and the whole document goes to the model in one call."""
    text = "\r\n\r\n".join(f"Accomplishment {i}: " + "z" * 900 for i in range(30))
    segments = segment(text)
    assert len(segments) > 1
    assert all(len(s) <= _SEGMENT_CHARS for s in segments)


def test_text_with_no_blank_lines_still_splits() -> None:
    """PDF extraction often returns single newlines only."""
    text = "\n".join(f"Line {i}: " + "w" * 500 for i in range(60))
    segments = segment(text)
    assert len(segments) > 1
    assert all(len(s) <= _SEGMENT_CHARS for s in segments)


def test_text_with_no_seam_at_all_is_still_cut_to_size() -> None:
    """One unbroken 40k-character blob must not be sent whole."""
    segments = segment("q" * 40_000)
    assert len(segments) == 4
    assert all(len(s) <= _SEGMENT_CHARS for s in segments)


# ---- tolerant of small-model output shapes ----------------------------------
import pytest  # noqa: E402

from app.ai import parse as _p  # noqa: E402


@pytest.mark.parametrize("output", [
    {"chunks": [{"type": "experience", "title": "Dev", "accomplishment": "Built X"}]},
    [{"type": "experience", "title": "Dev", "accomplishment": "Built X"}],
    {"experience": [{"title": "Dev", "description": "Built X"}]},
    {"type": "experience", "title": "Dev", "description": "Built X"},
    {"chunks": [{"title": "Dev", "accomplishments": ["Built X", "Shipped Y"]}]},
])
def test_odd_shapes_still_yield_chunks(monkeypatch, output):
    monkeypatch.setattr(_p, "generate_json", lambda *a, **k: output)
    chunks = _p.parse_to_chunks("Experience\nDev at Acme\nBuilt X")
    assert chunks and chunks[0]["accomplishment"] == "Built X"
    assert chunks[0]["title"] == "Dev"


def test_nothing_usable_is_empty(monkeypatch):
    monkeypatch.setattr(_p, "generate_json", lambda *a, **k: {"note": "no idea"})
    assert _p.parse_to_chunks("some text here") == []


def test_features_built_at_a_job_are_experience_under_the_role(monkeypatch):
    out = {"chunks": [
        {"type": "project", "title": "Recruiter Workflows", "company": "Paiger",
         "date_range": "Feb 2023 - Present", "accomplishment": "Built recruiter workflows"},
        {"type": "project", "title": "Chrome Extension", "company": "Paiger",
         "date_range": "Feb 2023 - Present", "accomplishment": "Built a Chrome extension"},
        {"type": "experience", "title": "Full-Stack Developer", "company": "Paiger",
         "date_range": "Feb 2023 - Present", "accomplishment": "Designed AI CV features"},
        {"type": "project", "title": "My Blog", "company": None, "date_range": "2021",
         "accomplishment": "Wrote a blog engine"},
    ]}
    monkeypatch.setattr(_p, "generate_json", lambda *a, **k: out)
    chunks = _p.parse_to_chunks("Experience\nFull-Stack Developer Paiger")
    paiger = [c for c in chunks if c["company"] == "Paiger"]
    assert {c["type"] for c in paiger} == {"experience"}
    assert {c["title"] for c in paiger} == {"Full-Stack Developer"}
    assert paiger[0]["context"] == "Recruiter Workflows"
    blog = next(c for c in chunks if c["title"] == "My Blog")
    assert blog["type"] == "project"
