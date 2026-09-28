# Resume tailor

Send it a job posting and get back a one-page resume PDF tailored to that job,
written only from work you have really done.

A trimmed fork of [Maan-Teckwani/unemployed](https://github.com/Maan-Teckwani/unemployed),
cut down to the headless resume tailoring. The job finding, scoring, outreach,
roadmap, web UI and landing site are gone. It runs next to
[telegram-job-alerts](https://github.com/Sajadmhy/telegram-job-alerts), which
calls `POST /tailor` from Telegram.

## How it works

1. **Knowledge base.** Your experience is stored as "chunks": one
   accomplishment each, with its role, dates, technologies and impact.
2. **Read the job.** The posting (text, or a link to it) goes to the LLM,
   which pulls out the required skills, preferred skills and responsibilities.
3. **Write the resume.** Every chunk is ranked against the job by meaning
   (embeddings) and by exact terms. The model then writes bullets from them in
   the job's own vocabulary. A bullet that can't be traced to a real chunk, or
   that invents a number, is rejected before it reaches the page.
4. **Render.** You get a single-column, ATS-parseable PDF. The app checks it by
   extracting the text back out of the PDF.

## Setup

**macOS / Linux**
```bash
./run.sh
```

The script checks for Python 3.10+ and Ollama and pulls a model that fits your
memory. It then builds `backend/.venv`, creates the SQLite database at
`data/jobsearch.db` and starts the API on **http://localhost:8000**. The first
run takes a while because PyTorch is large. Every later run skips straight to
starting.

<details>
<summary>Running it by hand instead</summary>

```bash
cd backend && python3 -m venv .venv && .venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m alembic upgrade head
.venv/bin/python -m uvicorn app.main:app --port 8000
```
</details>

### Using a hosted model

Everything runs locally by default. To make it much faster, point it at any
OpenAI-compatible endpoint in `.env` at the repo root. Groq, for example:

```bash
LLM_BASE_URL=https://api.groq.com/openai/v1
LLM_API_KEY=...
LLM_MODEL=openai/gpt-oss-120b
LLM_REASONING_EFFORT=low
```

With a hosted model, the job description and your knowledge base text are sent
to that provider. See `.env.example` for the other options. On slow hardware
with a local model, set `LLM_TIMEOUT_SCALE=3` so the model's timeouts stretch
to match.

## Use

**Once**, set your profile and load your experience from an existing resume:

```bash
python3 tools/import_resume.py --resume ~/cv.pdf --name "Your Name" --email you@example.com \
    --link github=https://github.com/you
```

To add items by hand, write them as a JSON list and load them. Near-duplicates
from the same employer are shown and replaced once you confirm:

```bash
python3 tools/add_experience.py items.json
```

**Then, per job**, send the posting (text, or a link to it) and get the
tailored PDF back:

```bash
curl -X POST http://localhost:8000/tailor -H 'Content-Type: application/json' \
     -d '{"text": "<the job post>"}' -o resume.pdf --max-time 1200
# or: -d '{"url": "https://boards.greenhouse.io/acme/jobs/123"}'
```

The title and company are read from the post when you don't pass them. The
file is named `<Your Name> - <Job title>.pdf`. LinkedIn and other pages that
need a login or JavaScript can't be fetched, so paste their text instead.

The other endpoints (knowledge base, profile, resumes) are listed at
http://localhost:8000/docs.

## Checking it still works

```bash
cd backend && .venv/bin/python -m pytest tests/ -q
```

## How it's built

| | |
|---|---|
| Backend | FastAPI · SQLAlchemy · Alembic |
| Database | SQLite (one file, `data/jobsearch.db`) |
| Embeddings | `bge-small-en-v1.5` (384-dim, local) |
| LLM | Ollama (`llama3.2:3b`, or `llama3.2:1b` under 15 GB of RAM), or any OpenAI-compatible API |
| PDF | fpdf2 |

**Resumes expire.** Generated resumes and their PDFs are deleted ten minutes
after they are made (`RESUME_TTL_MINUTES`). They are derived from the
knowledge base and the job, both of which are kept, so regenerating one
reflects your *current* knowledge base. See
[`app/db/retention.py`](backend/app/db/retention.py).

**Back up** by copying `data/jobsearch.db`. That one file holds everything.
