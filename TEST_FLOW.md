# Manual Test Flow — Sprint 1 + Document Import

Test every feature built so far, one by one. Tests 1–5 and 12 work **without** the
LLM. Tests 6–11 (document import) need `llama3.2:3b` downloaded.

---

## 0. Start everything (3 terminals)

**Terminal A — Ollama:**

There is no database to start: the app uses a SQLite file (`data/jobsearch.db`)
created by `alembic upgrade head`. Confirm the model is ready:
```bash
ollama list
```
✅ Expect `llama3.2:3b` in the list. If it's missing, run `ollama pull llama3.2:3b` —
you can still do Tests 1–5 and 12 while it downloads.

**Terminal B — backend (:8000):**
```bash
cd backend && ./.venv/Scripts/python.exe -m uvicorn app.main:app --reload --port 8000
```
✅ Expect `Uvicorn running on http://127.0.0.1:8000`.

**Terminal C — frontend (:3000):**
```bash
cd web && npm run dev
```
✅ Expect `Ready` and http://localhost:3000.

---

## 1. Backend health & API surface  (no LLM)
- Open http://localhost:8000/health → `{"status":"ok","db":"reachable"}`
- Open http://localhost:8000/docs → Swagger lists `/kb/items`, `/kb/chunks`,
  `/kb/chunks/bulk`, `/kb/parse`, `/kb/search`, `/profile`.
- **Verifies:** API is up, DB reachable, all routes registered.

## 2. Frontend loads  (no LLM)
- http://localhost:3000 → Home with an "Open Knowledge Base" button.
- Top nav shows **Home · Knowledge Base · Import**.
- **Verifies:** frontend serves, navigation works.

## 3. Knowledge Base — manual entry  (no LLM)
- Go to **Knowledge Base**. In "Add a career item": Type `project`,
  Title `Portfolio website`.
- Accomplishment 1: `Built a personal portfolio in Next.js deployed on Vercel`,
  Technologies `Next.js, Vercel`, Skills `frontend`, Impact `500 monthly visitors`.
- Click **+ Add accomplishment**, add a second one, then **Save to Knowledge Base**.
- ✅ Toast "Added N chunk(s)"; the count at the top increases; new chunks show in
  "Stored chunks" with type/tech badges.
- **Verifies:** manual entry, one-chunk-per-accomplishment, embed + store, list refresh.

## 4. Semantic search  (no LLM — the core Sprint 1 feature)
- In "Try semantic search", type `frontend web developer` → **Search**.
- ✅ Ranked results with similarity scores; your portfolio chunk near the top even
  though the wording differs.
- Now search `marine biology research` → scores should be clearly lower.
- **Verifies:** embeddings + cosine retrieval *by meaning*, not keywords.

## 5. Delete a chunk  (no LLM)
- Click **Delete** on any stored chunk.
- ✅ Toast "Deleted"; it disappears; count decreases.
- **Verifies:** delete endpoint + refresh.

## 6. Document Import — happy path  (needs LLM)
- Nav → **Import**. Choose a file — use `resources/sample_resume.txt` (or your own
  resume: pdf / docx / txt / md). Set the kind dropdown to `resume`.
- Click **Parse documents**.
- ✅ "Parsing… (local LLM, may take a bit)"; after ~10–60s, toast "Parsed N chunk(s)"
  and a **Review proposed chunks** list appears with editable fields.
- 🔎 **Most important check:** every proposed chunk is **truthful** — only facts that
  were in the document. Nothing invented (no fake metrics/employers).
- **Verifies:** upload → text extraction → LLM structuring → proposals (NOT saved yet).

## 7. Review & edit  (needs LLM output from Test 6)
- Edit a proposed chunk (reword the accomplishment, add/remove a technology).
- Click **Remove chunk** on one you don't want.
- ✅ Edits reflect live; removed chunk disappears.
- **Verifies:** human-in-the-loop review before anything is saved.

## 8. Save reviewed chunks  (needs LLM output from Test 6)
- Click **Save all to Knowledge Base**.
- ✅ Toast "Saved N chunk(s)"; you land on **Knowledge Base**; imported chunks are in
  "Stored chunks"; count increased.
- **Verifies:** bulk embed + store of reviewed chunks.

## 9. Search the imported data  (needs Test 8)
- On Knowledge Base, semantic-search a role matching your imported experience
  (e.g. `backend engineer building APIs`).
- ✅ Imported chunks surface with scores.
- **Verifies:** imported data is embedded and retrievable end-to-end.

## 10. Multi-file import + kinds  (needs LLM)
- On **Import**, select **multiple** files at once (e.g. the sample resume + any
  `.txt` about your projects). Give each a different kind. **Parse documents**.
- ✅ Chunks from all files appear together in the review list.
- **Verifies:** multi-file handling, per-file kind hint, per-file isolation.

## 11. Edge cases
- Upload an image (e.g. a `.png`) and Parse → ✅ error toast
  "Unsupported file type: .png …". (Mix it with a valid file → the valid one still parses.)
- Click **Search** with an empty box → ✅ nothing happens (guarded).
- Parse a document with no career content → ✅ toast "No accomplishments found".
- **Verifies:** error handling and input guards.

## 12. Profile API (optional, no LLM — no UI yet)
```bash
curl http://localhost:8000/profile
```
```bash
curl -X PUT http://localhost:8000/profile -H "Content-Type: application/json" -d "{\"name\":\"Ananya\",\"email\":\"a@x.com\"}"
```
- ✅ GET returns a profile row; PUT updates and echoes it back.
- **Verifies:** profile storage (used later for the resume header).

---

---

# Sprint 2 — Job Ingestion

## 13. Run the ingestion pipeline  (no LLM)
```bash
cd backend && ./.venv/Scripts/python.exe -m app.ingestion.run
```
- ✅ A per-company table prints (seen / new / upd / exp / status), ending with
  `N new job(s); 0 source(s) failed.`
- **Verifies:** all connectors fetch and normalize real jobs.

## 14. Idempotency — the key property
- Run the exact same command again.
- ✅ Second run reports **new = 0** (and expired = 0). Re-running never duplicates.
- **Verifies:** identity is `(source, external_id)`; the pipeline is safe to re-run.

## 15. Browse jobs in the UI
- Open http://localhost:3000/jobs
- ✅ Header shows `N active roles from M companies`; rows show title, company,
  location, source, age, `remote` badges, and a working **Open** link.
- Type in the filter box (e.g. `engineer`) → list narrows.
- **Verifies:** jobs API + UI.

## 16. Ingestion observability
- Click **Show ingestion runs**.
- ✅ One row per company with seen/new/expired counts and an `ok` badge.
- **Verifies:** every run is auditable — the first place to look when jobs vanish.

## 17. India relevance filter
```bash
cd backend && ./.venv/Scripts/python.exe -m pytest tests/ -q
```
- ✅ 11 passed.
- Spot-check the UI: locations should be Indian cities or India-eligible remote —
  no "London" / "San Francisco" / "US East" roles.
- **Verifies:** only jobs an India-based candidate can actually apply to are stored.

## 18. Failure isolation — one dead board must not kill the run
Temporarily add a fake company to `backend/app/connectors/registry.py` inside `COMPANIES`:
```python
Company("greenhouse", "this-token-does-not-exist", "BrokenCo"),
```
Run ingestion again.
- ✅ `BrokenCo` row shows `FAILED: Client error '404 ...'`, **every other company still
  reports `ok`**, and the summary ends `... 1 source(s) failed.`
- ✅ Your existing jobs are untouched (a failed fetch never expires jobs).
- **Now delete that line again.**
- **Verifies:** per-connector isolation + safe expiry — the two properties that keep a
  daily pipeline trustworthy.

---

# Sprint 3 — Extraction + Matching

## 19. Score the jobs (the slow, resumable step)
```bash
cd backend && ./.venv/Scripts/python.exe -m app.ingestion.enrich --limit 5
```
- ✅ Prints `extracted=5 (new LLM calls) cached=0 scored=5 filtered=N (senior titles, no LLM used)`
- Each extraction takes ~25s on CPU. Drop `--limit` to process everything.
- **Verifies:** the LLM only runs on jobs a fresher could actually take.

## 20. Resumability — never pay twice
- Run the **same command again**.
- ✅ Now reports `extracted=0  cached=5` — previously-extracted jobs are reused.
- **Verifies:** work is cached by `content_hash`; re-running is cheap.

## 21. Ranked matches + the "why"
- Open http://localhost:3000/matches
- ✅ Jobs sorted by score (0–100) with company, location, **Why?** and **Apply**.
- Click **Why?** on any row → per-feature bars (Required skills / Semantic fit /
  Preferred skills / Keyword overlap), each with its weight, plus
  **You have** / **Missing** skill badges and extraction confidence.
- **Verifies:** every score is explainable — no black box.

## 22. Hard filters are visible, not silent
- Click **Show filtered**.
- ✅ Filtered jobs appear with a reason badge (`senior title`, `requires 8+ years`,
  `senior-level role`).
- **Verifies:** "why is this job not in my list?" is always answerable.

## 23. Matching engine unit tests
```bash
cd backend && ./.venv/Scripts/python.exe -m pytest tests/ -q
```
- ✅ 52 passed — covers weights summing to 1, skill aliases (Postgres→PostgreSQL),
  the weighted-sum math, and the rule that a *low-confidence* extraction must never
  hard-filter a job.

---

# Sprint 4 — RAG Resume Generation

## 24. Fill your profile (required first)
- Open http://localhost:3000/profile
- Enter name, email, phone, location, GitHub/LinkedIn, and **Education**. Save.
- ✅ Toast "Profile saved". This is the resume header — it is **never** AI-generated.

## 25. Generate a tailored resume
- **Matches** → click **Open** on any job → **Generate tailored resume**.
- ✅ After ~40s: a Skills line, bullets grouped by Experience/Projects, and an
  **ATS check** panel.
- **Verifies:** hybrid retrieval → grounded generation → validation → PDF, end to end.

## 26. Traceability — the honesty guarantee
- Under each bullet, click **from: &lt;source&gt;**.
- ✅ The original KB accomplishment expands beneath it.
- 🔎 **Key check:** every bullet is a rewording of a real accomplishment. Nothing on
  the page should be an experience you don't have.
- **Verifies:** each bullet is bound to the chunk id it came from.

## 27. ATS report
- ✅ Badges show **Parses cleanly**, **1 page**, **Keyword coverage N%**.
- Missing required skills are listed as *"Not evidenced in your KB (never faked)"* —
  the app reports gaps instead of inventing them.
- If the model ever produces an untraceable bullet or an invented metric, it appears
  under **Rejected by truthfulness validation** and never reaches the resume.

## 28. Download the PDF
- Click **Download PDF**.
- ✅ Opens a single-page, single-column PDF. Select text in a viewer and copy it —
  it must be **real selectable text**, not an image. That is what an ATS reads.

## 29. Truthfulness + retrieval unit tests
```bash
cd backend && ./.venv/Scripts/python.exe -m pytest tests/ -q
```
- ✅ 61 passed — includes bullets rejected for citing no source, bullets rejected for
  inventing metrics ("improved latency by 40%"), skills never claimed unless the KB
  evidences them, and RRF fusion ranking.

---

# Sprint 5 — The Daily Loop

## 30. Home is now "Apply today"
- Open http://localhost:3000/
- ✅ Ranked roles with score, **Why?**, **Generate**, and a **status dropdown** each.
- **Verifies:** the home page answers only the four questions and nothing else.

## 31. Status tracking survives re-ingest
- Set a job's status to **Applied**.
- Re-run ingestion: `cd backend && ./.venv/Scripts/python.exe -m app.ingestion.run`
- Reload the home page. ✅ The status is still **Applied**, and with *Hide completed*
  on (the default) that job no longer clutters today's list.
- **Verifies:** your own state lives in `applications` and is never overwritten by the
  pipeline — the daily list becomes "what's left", not the same 25 jobs every morning.

## 32. Edit a resume bullet
- Open any job with a generated resume → **Edit**.
- Reword a bullet, remove one, tweak the skills line → **Save & re-check**.
- ✅ Toast "Saved — PDF and ATS check regenerated"; the ATS panel and PDF both update.
- 🔎 Check: bullets you edited still show their **from: &lt;source&gt;** link.
- **Verifies:** you control the wording; layout stays code-owned so an edit cannot
  break ATS parseability, and provenance survives editing.

## 33. Paste a job description
- Nav → **Paste JD**. Fill title, company, and paste a full description → **Score this job**.
- ✅ After ~30s you land on the job page with a score, extracted requirements, and the
  option to generate a resume — identical to an auto-discovered job.
- Paste the *same* JD again → ✅ it reuses the same job instead of duplicating.
- **Verifies:** the second entry point joins the same pipeline.

## 34. The full daily loop, end to end
1. Home → pick the top role → **Why?** to sanity-check the fit
2. **Generate** → review bullets and their sources → **Edit** anything clumsy
3. **Download PDF**
4. **Open application** → apply on the company site
5. Set status → **Applied**
- ✅ Reload home: that job is gone from today's list.
- **Verifies:** Sprint 5 DoD — a real job hunt run entirely from the browser.

---

# Filtering — fresher + role family

## 35. Review your filters
- Open http://localhost:3000/settings
- ✅ Four role families (all on), max years = 1, seniority = intern + entry.
- **Verifies:** thresholds are data you control, not constants in code.

## 36. Filters actually drive the list
- Untick **DevOps / SRE / Cloud** → **Save & re-score**.
- ✅ Toast reports counts, and SRE roles disappear from home within seconds.
- Tick it back on → **Save & re-score** → they return.
- **Verifies:** re-scoring reuses cached extractions — seconds, zero LLM calls.

## 37. Nothing disappears silently
- Go to **All matches** → **Show filtered**.
- ✅ Every filtered job shows a reason: `not a target role (other)`,
  `senior title`, `requires 7+ years`, `senior-level role`.
- **Verifies:** "why is this job not in my list?" is always answerable.

## 38. Classifier + filter unit tests
```bash
cd backend && ./.venv/Scripts/python.exe -m pytest tests/ -q
```
- ✅ 99 passed. Includes ~30 **real titles** from your own job pool, covering the
  traps: "GTM Engineer", "Customer Success Engineer", "Product Solution Engineer"
  and "Service Delivery Engineer" are *not* software roles, while
  "Service Delivery Engineer, SRE" is; "Associate Manager, Data Privacy" is not
  data engineering; "Intermediate Backend Engineer" is mid-level.

---

# Company discovery + two-tier scoring

## 39. Discover company job boards
```bash
cd backend && ./.venv/Scripts/python.exe -m app.ingestion.discover
```
- ✅ Probes ~430 seed companies across Greenhouse, Lever, Ashby and SmartRecruiters,
  printing each hit, then writes `app/connectors/discovered.json`.
- Re-running only probes companies not already found (cached). Use `--refresh` to
  re-check everything, `--limit N` for a quick sample.
- 🔎 A board is only kept if it actually returns **India-relevant** jobs — slugs
  collide across vendors, so this is what stops a same-named US startup sneaking in.

## 40. Ingest from every discovered board
```bash
cd backend && ./.venv/Scripts/python.exe -m app.ingestion.run
```
- ✅ One row per company; the registry now comes from `discovered.json` rather than
  a hardcoded list.

## 41. Two-tier scoring
```bash
cd backend && ./.venv/Scripts/python.exe -m app.ingestion.enrich --top 100
```
- ✅ Prints `filtered=… estimated=… extracted=… cached=…`
- **Tier 1** (no LLM): filters, then embeds and ranks *every* surviving job on
  semantic + keyword fit — milliseconds each.
- **Tier 2** (LLM): full requirement extraction for only the top `--top` jobs.
- **Verifies:** thousands of jobs stay tractable. Extracting everything would take
  days; extracting the best hundred takes ~40 minutes.

## 42. Estimated vs full scores are labelled
- On home, jobs scored by tier 1 only carry an **estimated** badge.
- ✅ Their score is renormalised over the two available features, so it is a fair
  estimate on the same 0–1 scale — not artificially low from two missing terms.
- **Verifies:** the UI never passes off a partial score as a complete one.

## 43. Experience filtering works on EVERY job
```bash
cd backend && ./.venv/Scripts/python.exe -m pytest tests/test_experience.py -q
```
- ✅ 17 passed.
- The years requirement is read straight out of the description with a regex, so it
  applies to every job — not only the ~100 that reach the LLM tier.
- Rules: a range counts as its **lower bound** ("0-2 years" stays, "3-5" goes); several
  mentions take the **highest** bar; a posting that states no years is **kept** and
  judged on its title.
- In the UI, no visible job should ask for more than your **Filters → max years**.
  Check a few by opening them and reading the description.

## 44. Location filter — India / remote only
- On home, check the location of every visible job.
- ✅ All are Indian cities, "Remote", or "Remote - India". No "San Francisco, CA",
  "New York, NY" or "North America".
- 🔎 A job listing several regions *including* India still shows — India wins first,
  so "Chennai, TN, India" survives the US-state pattern.

---

# Sprint 6 — Outreach + preferences

## 45. Add your college
- **Profile** → fill **College name only** (e.g. "VIT Vellore") → Save.
- ✅ Needed for alumni search; without it the alumni row is omitted rather than
  searching for nothing.

## 46. Find people to contact
- Open any job → scroll to **Who to reach out to** → **Find people**.
- ✅ After ~30s you get up to 5 rows: alumni, recruiters, engineering managers/VPs,
  people already in the role, founders.
- Click **Search →** on any row: it opens a Google query scoped to
  `site:linkedin.com/in` for that company and category. **Nothing is scraped** —
  you do the looking, which keeps your LinkedIn account safe.

## 47. Drafts are grounded in your real work
- Click **Draft** on a row.
- ✅ A short message referencing something you actually built (from your KB).
- 🔎 Check it never claims experience you don't have — same grounding rule as resumes.
- Edit it, **Copy message**, set status (todo → found → contacted → replied), **Save**.

## 48. Preferred locations shape ranking (softly)
- **Filters** → set **Preferred locations** (e.g. "Bengaluru, Hyderabad") → **Save & re-score**.
- ✅ Jobs in those cities rank higher, but nothing disappears — a great role in
  another city is still worth seeing. Uncheck **Remote roles are fine** to push
  remote jobs down.
- **Verifies:** `preference_fit` is the 5th scoring feature; weights still sum to 1.

---

# Sprint 7 — Project ideas, eval, deploy

## 49. Score is visible on the job page
- Open any job from **Apply today**.
- ✅ The fit score sits beside the title (e.g. `Field Security Engineer 62`), with an
  **estimated** badge if it hasn't had full extraction, and the feature breakdown below.
- 🔎 At estimated tier only the features actually used are listed — a feature that
  wasn't measured is omitted rather than shown as "0%", which would read as a
  zero score instead of "not measured yet".

## 50. Suggest a project to build
- On a job → **Build something for them** → **Suggest a project**.
- ✅ After ~40s: a specific project with problem, what to build, why it lands, and scope.
- 🔎 It should name something tied to *that company's* product. Generic student
  projects (todo app, weather app, clones) are rejected outright and you'll be asked
  to try again.
- **closes gap:** badges mark skills the role wants that your KB can't yet prove.

## 51. Evaluate the whole pipeline
```bash
cd backend && ./.venv/Scripts/python.exe -m app.eval.run
```
- ✅ Prints coverage, extraction quality, filter precision and resume truthfulness,
  ending in `PASS: 0 filter leak(s)`.
- **Verifies:** quality is measured, not asserted. Run it after any prompt or filter
  change — a change that helps extraction can easily loosen filtering.

## 52. One-command deploy
```bash
docker compose --profile app up -d
```
- ✅ Starts ollama, api (migrations run automatically), worker (daily
  ingest + score) and web, all sharing the SQLite file on the `appdata` volume.
- ✅ http://localhost:3000 and http://localhost:8000/health both respond.
- For day-to-day development use `run.ps1` / `run.sh` instead — no containers
  at all, and hot reload on both the backend and the frontend.

---

# Generalization — any region, any company

## 53. Pick your region
- **Filters** → **Where can you work?** → choose your region (India, US, UK, Europe,
  Canada, Australia, Singapore, or *Anywhere*).
- ✅ Saving stores it; jobs outside that region are dropped at the next fetch:
  ```bash
  python -m app.ingestion.run
  ```
- 🔎 The rule is symmetric: every region lists its own places, and every *other*
  region's places count as foreign. A posting naming several regions including
  yours is kept — "Chennai, TN, India" survives even though ", TN" is a US pattern.
- **Anywhere** disables location filtering entirely.

## 54. Add any company by name
- **Filters** → **Companies** → type a name (try `Canva`, `Vanta`, `Airbnb`) → **Search**.
- ✅ Within ~10s it reports which platform hosts them and how many jobs match your
  region — or says no public board was found.
- **Add** starts tracking them; the next fetch pulls their jobs.
- ✅ A company already tracked is labelled rather than duplicated.
- 🔎 A board is only accepted if it has jobs **in your region**. Slugs collide across
  vendors (Ashby's `navi` is a US startup, not the Indian neobank) — this is the check
  that stops the wrong company being added.

## 55. Remove a company
- Click **remove** next to any tracked company.
- ✅ It disappears from the list. Jobs already ingested are left alone; they age out
  through normal expiry.

## Re-score after editing your Knowledge Base
Matching is cheap and deterministic, so re-run enrich after adding KB chunks — it
reuses cached extractions and only recomputes scores:
```bash
cd backend && ./.venv/Scripts/python.exe -m app.ingestion.enrich
```

## Reset the jobs table (optional — to watch a fresh ingest)
```bash
sqlite3 data/jobsearch.db "DELETE FROM jobs; DELETE FROM ingestion_runs;"
```

## Reset the KB (optional, to test from a clean slate)
```bash
sqlite3 data/jobsearch.db "DELETE FROM kb_chunks;"
```

## Troubleshooting
- **Import does nothing / errors about model:** run `ollama list` and check that
  `llama3.2:3b` is there; `ollama pull llama3.2:3b` if not.
- **`404 ... /api/chat` or "model not found":** the backend is talking to the wrong
  Ollama. Development uses the **native** install on `11434` (`curl http://localhost:11434/api/tags`).
  The `--profile app` container publishes `11435` instead, deliberately, so the two
  never shadow each other — if you're on that path, `OLLAMA_URL` has to say 11435.
- **`Internal Server Error` on /health:** the database file is missing or was
  never migrated. Run `alembic upgrade head` from `backend/`.
- **A page intermittently 500s** (`Unexpected end of JSON input`): stop the frontend,
  delete `web/.next`, run `npm run dev` again (corrupted dev cache).
- **First KB action is slow:** the embedding model (~130 MB) loads once, then it's cached.
