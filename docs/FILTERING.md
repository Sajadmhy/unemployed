# Design: Fresher + Role-Family Filtering

**Status:** planned — to be built immediately after Sprint 5.
**Why:** the candidate is a fresher (0 years) targeting software/AI roles. Today the
system blocks obvious senior titles but still surfaces mid-level engineering roles
and non-engineering roles entirely outside the target domain.

## The problem, measured

Snapshot of the top-ranked visible matches before this work:

| Score | Title | Extracted | Should be? |
|---|---|---|---|
| 0.55 | Product Solution Engineer | mid, 2 yrs | filtered (mid) |
| 0.53 | Growth StratOps Associate | entry, 0 yrs | filtered (not engineering) |
| 0.35 | Analyst, Credit Risk Management | mid, 0 yrs | filtered (not engineering) |
| 0.29 | Intermediate Fullstack Engineer | mid, 0 yrs | filtered ("Intermediate" = mid) |
| 0.24 | Customer Experience Specialist | entry, 0 yrs | filtered (not engineering) |

Three distinct gaps:

1. **"Intermediate" is unrecognised.** GitLab (and others) use it to mean mid-level.
2. **`seniority == "mid"` is not blocked.** The hard filter only rejects `senior`/`lead`.
3. **No job-function filter exists at all.** Nothing knows the candidate is an engineer,
   so Growth/Risk/Support roles compete for the top of the list.

## Decisions (agreed with the user)

| Question | Decision |
|---|---|
| Seniority cutoff | **Strict: 0–1 year.** Allow `intern`/`entry` only; block `mid`, `senior`, `lead`, and "Intermediate" titles. |
| Role families kept | **Software Engineering · AI/ML/Data Science · Data/Analytics Engineering · DevOps/SRE/Cloud.** Everything else filtered. |
| Filtered jobs | **Hidden by default, revealed via "Show filtered"** with a reason. Preserves "why is this missing?" |
| Configuration | **UI settings page**, backed by a `preferences` table — this also supplies the `preference_fit` matching feature deferred from Sprint 3. |

## Implementation

### 1. `preferences` table (single row, like `candidate_profile`)

```
max_years            int      default 1
allowed_seniority    text[]   default {intern, entry}
role_families        text[]   default {software, ai_ml, data, devops}
locations            text[]   -- Sprint 6 (preference_fit)
remote_ok            bool     -- Sprint 6
```

Filter thresholds become **data, not constants**, so tuning needs no code change.

### 2. `app/ingestion/role_family.py` — deterministic classifier, NOT an LLM

`classify(title) -> "software" | "ai_ml" | "data" | "devops" | "other"`

Keyword sets per family, matched on the title with word boundaries:

- **software**: engineer, developer, sde, backend, frontend, fullstack, android, ios, mobile, platform, systems, software
- **ai_ml**: ml, machine learning, ai, deep learning, nlp, llm, computer vision, data scientist, research engineer
- **data**: data engineer, analytics engineer, business intelligence, data platform, etl
- **devops**: devops, sre, site reliability, infrastructure, cloud, platform reliability, kubernetes

Ambiguity rule: check `ai_ml` → `data` → `devops` → `software` (most specific first), so
"ML Platform Engineer" lands in `ai_ml`, not `software`.

**Why not an LLM:** ~25s per job versus ~0ms, and titles are formulaic enough that keywords
are highly reliable. Deterministic also means free, explainable, and unit-testable — same
reasoning as the existing seniority pre-filter.

**Known limitation to accept:** a title like "Associate, Technology" is genuinely ambiguous.
It falls to `other` and is filtered. Since filtered jobs stay visible behind the toggle,
a miss is recoverable rather than invisible.

### 3. Extend `app/ingestion/seniority.py`

Add to the mid/senior term set: `intermediate`, `mid`, `mid-level`, `experienced`, `ii`,
`iii` (already), `2`, `3`. Keep the existing precedence (hard-senior > fresher signal >
soft-senior > level marker).

Add `MID_LEVELS = {"mid"}` handling in `match.py`'s hard filter so `seniority == "mid"`
is rejected under the strict setting.

### 4. `app/ai/match.py` — filters read preferences

`_hard_filter` gains, in order:

1. `role family not in preferences.role_families` → `"not a target role (growth)"`
2. `not is_fresher_friendly(title)` → `"senior title"` *(existing)*
3. confidence ≥ 0.5 and `min_years > preferences.max_years` → `"requires N+ years"` *(existing, threshold now from prefs)*
4. confidence ≥ 0.5 and `seniority not in preferences.allowed_seniority` → `"mid-level role"`

Low-confidence extractions still never hard-filter (existing rule preserved) — that is the
"Strict, but keep unclear ones" behaviour, applied to the extraction-derived rules only.

### 5. Skip filtered jobs before the LLM

`enrich.py` already skips extraction for non-fresher titles. Extend that to also skip
non-target role families, cutting more LLM time out of every run.

### 6. UI: `/settings`

Toggles for role families, a max-years number input, seniority checkboxes, and a
**"Re-score jobs"** button (matching is cheap and deterministic, so re-scoring after a
preference change takes seconds and needs no LLM).

## Verification

- Unit tests: `role_family.classify` over ~20 real titles from the DB, including the
  ambiguous ones; `is_fresher_friendly` gains "Intermediate Backend Engineer" → False.
- Integration: re-score and assert the five leaking rows above are all filtered, each with
  the correct reason.
- Regression: assert genuine fresher engineering roles (e.g. "Software Engineer",
  "SDE Intern", "Graduate Engineer Trainee") remain visible.
- Expect the visible pool to shrink substantially; that is the intent (precision over volume).
