"""Every job is printed; the relevant bullets lead; jobs keep date order; the
profile is one plain paragraph built only from real facts."""
from types import SimpleNamespace

import pdfplumber
import pytest

from app.ai import generate_resume as g
from app.ai import pdf as pdfmod


def chunk(cid, title, company, dates, text, ctype="experience", tech=()):
    return SimpleNamespace(id=cid, type=ctype, title=title, company=company, date_range=dates,
                           accomplishment=text, impact=None, context=None,
                           technologies=list(tech), skills=[])


def bullets_of(result, company):
    return [b["text"] for b in result if b.get("company") == company]


@pytest.fixture
def career():
    # Retrieval order: most relevant to the posting first.
    return [
        chunk(1, "Full-Stack Developer", "Paiger", "Feb 2023 - Present", "Built GraphQL APIs for candidate search"),
        chunk(2, "Full-Stack Developer", "Paiger", "Feb 2023 - Present", "Migrated the extension to TypeScript"),
        chunk(3, "Full-Stack Developer", "Paiger", "Feb 2023 - Present", "Owned the CV template system"),
        chunk(4, "Front-End Developer", "Classeh", "Nov 2022 - Feb 2023", "Worked with a team of frontend developers"),
        chunk(5, "Front-End Developer", "Lolo Co", "Jul 2022 - Nov 2022", "Built a responsive website with Strapi.io"),
    ]


# ---- nothing is dropped ------------------------------------------------------
def test_a_job_with_nothing_relevant_is_printed_as_written(career):
    validated = [  # the model only found Paiger relevant
        {"text": "Built GraphQL APIs for candidate search at scale", "source_chunk_ids": [1],
         "section": "Experience", "title": "Full-Stack Developer", "context": None,
         "company": "Paiger", "date_range": "Feb 2023 - Present"},
    ]
    out = g._assemble(validated, career)
    assert bullets_of(out, "Classeh") == ["Worked with a team of frontend developers"]
    assert bullets_of(out, "Lolo Co") == ["Built a responsive website with Strapi.io"]


def test_no_relevant_bullets_at_all_still_gives_every_job(career):
    out = g._assemble([], career)
    assert {b["company"] for b in out} == {"Paiger", "Classeh", "Lolo Co"}
    assert bullets_of(out, "Lolo Co") == ["Built a responsive website with Strapi.io"]


def test_a_rejected_rewrite_falls_back_to_the_original_words(career):
    # e.g. the model invented a number, so _validate_bullets refused its version
    out = g._assemble([], career)
    assert "Built GraphQL APIs for candidate search" in bullets_of(out, "Paiger")


# ---- order inside a job ------------------------------------------------------
def test_relevant_first_in_the_models_order_then_the_rest(career):
    def v(cid, text):
        return {"text": text, "source_chunk_ids": [cid], "section": "Experience",
                "title": "Full-Stack Developer", "context": None, "company": "Paiger",
                "date_range": "Feb 2023 - Present"}
    out = g._assemble([v(3, "Owned the CV template system end to end"), v(1, "Built GraphQL APIs")], career)
    assert bullets_of(out, "Paiger") == [
        "Owned the CV template system end to end",   # model ranked it first
        "Built GraphQL APIs",
        "Migrated the extension to TypeScript",       # not relevant: as written, after
    ]


def test_jobs_are_capped_but_never_below_one_and_newest_gets_most():
    many = [chunk(i, "Dev", "Paiger", "Feb 2023 - Present", f"Did thing {i}") for i in range(1, 30)]
    older = [chunk(100 + i, "Dev", f"Old{i}", f"20{10 + i} - 20{11 + i}", f"Old work {i}") for i in range(6)]
    out = g._assemble([], many + older)
    assert len(bullets_of(out, "Paiger")) == 9
    assert all(len(bullets_of(out, f"Old{i}")) == 1 for i in range(6))
    assert sum(1 for b in out if b["section"] == "Experience") <= 16


def test_a_jobs_heading_is_consistent_across_its_bullets():
    a = chunk(1, "Full-Stack Developer", "Paiger", "Feb 2023 - Present", "One")
    b = chunk(2, "Recruiter Workflows", "Paiger", "Feb 2023 - Present", "Two")
    c = chunk(3, "Full-Stack Developer", "Paiger", "Feb 2023 - Present", "Three")
    out = g._assemble([], [a, b, c])
    assert {x["title"] for x in out} == {"Full-Stack Developer"}


def test_the_pdf_keeps_jobs_newest_first_whatever_the_relevance_order(career, tmp_path):
    out = g._assemble([], career)
    profile = SimpleNamespace(name="A B", email="a@b.c", phone="", location="", links={}, education="")
    path = pdfmod.render(profile, {"summary": "", "skills": [], "bullets": out}, tmp_path / "r.pdf")
    text = pdfplumber.open(path).pages[0].extract_text()
    assert text.index("Paiger") < text.index("Classeh") < text.index("Lolo Co")


# ---- the profile paragraph -----------------------------------------------------
JOB = SimpleNamespace(title="Full-Stack Engineer", company="Brightlane",
                      description="We build hiring tools with React and Node.js.")
REQ = {"required_skills": ["React", "Node.js"], "responsibilities": ["Build hiring tools"]}
BUL = [{"section": "Experience", "title": "Full-Stack Developer", "company": "Paiger",
        "date_range": "Feb 2023 - Present", "text": "Built GraphQL APIs for candidate search"}]
GOOD = ("Full-stack developer working on a recruitment SaaS at Paiger. Builds GraphQL APIs in Node.js "
        "and the React-style client on top, including AI features for CVs. That is close to the "
        "hiring tools this role covers.")


def test_a_clean_profile_is_used(monkeypatch):
    monkeypatch.setattr(g, "generate_json", lambda *a, **k: {"profile": GOOD})
    assert g.write_profile(JOB, REQ, BUL, ["React", "Node.js"]) == GOOD


def test_stock_phrases_are_rejected_then_retried(monkeypatch):
    replies = iter([{"profile": "Passionate full-stack developer at Paiger building GraphQL APIs in Node.js and a React-style client for a recruitment SaaS, including AI features for CVs, which is close to the hiring tools this role covers."},
                    {"profile": GOOD}])
    seen = []
    def fake(system, prompt, **k):
        seen.append(prompt)
        return next(replies)
    monkeypatch.setattr(g, "generate_json", fake)
    assert g.write_profile(JOB, REQ, BUL, ["React"]) == GOOD
    assert "rejected" in seen[1] and "Passionate" in seen[1]


def test_invented_years_are_refused_and_a_plain_line_is_used_instead(monkeypatch):
    bad = {"profile": "Full-stack developer with 5 years of experience building GraphQL APIs in Node.js for a recruitment product used by many teams."}
    monkeypatch.setattr(g, "generate_json", lambda *a, **k: bad)
    out = g.write_profile(JOB, REQ, BUL, ["GraphQL", "Node.js"])
    assert out == "Full-Stack Developer at Paiger, working with GraphQL, Node.js."
    assert "5" not in out


def test_dashes_become_commas_and_it_stays_one_paragraph(monkeypatch):
    text = GOOD.replace("Paiger. Builds", "Paiger — builds").replace(". That", ".\n\nThat")
    monkeypatch.setattr(g, "generate_json", lambda *a, **k: {"profile": text})
    out = g.write_profile(JOB, REQ, BUL, ["React"])
    assert "—" not in out and "\n" not in out


def test_a_failing_model_still_gives_the_plain_profile(monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("down")
    monkeypatch.setattr(g, "generate_json", boom)
    assert g.write_profile(JOB, REQ, BUL, ["React"]).startswith("Full-Stack Developer at Paiger")


def test_no_experience_means_no_profile(monkeypatch):
    monkeypatch.setattr(g, "generate_json", lambda *a, **k: {"profile": GOOD})
    assert g.write_profile(JOB, REQ, [], []) == ""


def test_the_pdf_heading_is_profile(tmp_path):
    profile = SimpleNamespace(name="A B", email="a@b.c", phone="", location="", links={}, education="")
    path = pdfmod.render(profile, {"summary": GOOD, "skills": ["React"], "bullets": []}, tmp_path / "r.pdf")
    text = pdfplumber.open(path).pages[0].extract_text()
    assert "PROFILE" in text and "Full-stack developer working" in text
    assert text.index("PROFILE") < text.index("SKILLS")
