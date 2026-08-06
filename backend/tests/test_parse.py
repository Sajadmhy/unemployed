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
