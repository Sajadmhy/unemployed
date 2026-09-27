from fastapi.testclient import TestClient

from app.api import tailor as t
from app.db.models import Resume
from app.main import app


def _fake_pipeline(monkeypatch, tmp_path, seen):
    pdf = tmp_path / "r.pdf"
    pdf.write_bytes(b"%PDF-1.4 fake")

    def fake_job(data, db):
        seen["job"] = data
        return {"job_id": 1, "score": 0.5, "filtered": False}

    def fake_resume(job_id, fmt, db):
        return {"id": 7}

    class FakeRow:
        pdf_path = str(pdf)

    monkeypatch.setattr(t, "create_manual_job", fake_job)
    monkeypatch.setattr(t, "generate_resume", fake_resume)
    monkeypatch.setattr(t, "_guess_title_company",
                        lambda text: {"title": "Backend Dev", "known_title": "Backend Dev", "company": "Acme"})

    from sqlalchemy.orm import Session
    monkeypatch.setattr(Session, "get", lambda self, model, pk: FakeRow() if model is Resume else None)
    monkeypatch.setattr(Session, "scalar", lambda self, stmt: type("P", (), {"name": "Sajad Mahyaei"})())


def test_text_in_pdf_out(monkeypatch, tmp_path):
    seen = {}
    _fake_pipeline(monkeypatch, tmp_path, seen)
    r = TestClient(app).post("/tailor", json={"text": "We are hiring a Python backend developer. " * 5})
    assert r.status_code == 200, r.text
    assert r.headers["content-type"] == "application/pdf"
    assert r.content.startswith(b"%PDF")
    assert "Sajad%20Mahyaei%20-%20Backend%20Dev.pdf" in r.headers["content-disposition"]
    assert seen["job"].title == "Backend Dev" and seen["job"].company == "Acme"


def test_short_message_with_link_is_fetched(monkeypatch, tmp_path):
    seen = {}
    _fake_pipeline(monkeypatch, tmp_path, seen)
    monkeypatch.setattr(t, "_fetch", lambda url: "Job text from " + url + " " + "x" * 300)
    r = TestClient(app).post("/tailor", json={"text": "look https://jobs.example.com/42 pls"})
    assert r.status_code == 200, r.text
    assert seen["job"].apply_url == "https://jobs.example.com/42"
    assert seen["job"].description.startswith("Job text from https://jobs.example.com/42")


def test_linkedin_is_refused_clearly(monkeypatch, tmp_path):
    _fake_pipeline(monkeypatch, tmp_path, {})
    r = TestClient(app).post("/tailor", json={"url": "https://www.linkedin.com/jobs/view/1"})
    assert r.status_code == 422
    assert "Paste the job text" in r.json()["detail"]


def test_too_short(monkeypatch, tmp_path):
    _fake_pipeline(monkeypatch, tmp_path, {})
    r = TestClient(app).post("/tailor", json={"text": "hi"})
    assert r.status_code == 422


def test_strip_page():
    html = "<html><head><style>a{}</style><script>x()</script></head><body><h1>Dev</h1><p>Do things &amp; stuff</p></body></html>"
    out = t.strip_html(t._DROP_BLOCKS.sub(" ", html))
    assert "x()" not in out and "Dev" in out and "Do things & stuff" in out


def test_pdf_filename():
    assert t.pdf_filename("Sajad Mahyaei", "Full-Stack Engineer (React/Node)") == \
        "Sajad Mahyaei - Full-Stack Engineer (React Node).pdf"
    assert t.pdf_filename("Sajad Mahyaei", "") == "Sajad Mahyaei - Software Engineer.pdf"
    assert t.pdf_filename("", "Dev") == "Resume - Dev.pdf"
