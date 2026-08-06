"""Copy an existing Postgres database into the new SQLite file.

Only needed once, by people who ran this app before it moved off Postgres.
A fresh install has nothing to migrate and should never run this.

    python -m app.db.migrate_from_postgres
    python -m app.db.migrate_from_postgres --from postgresql+psycopg://user:pw@host/db

Rows are read with raw SQL rather than through the ORM on purpose: the models
now describe the *SQLite* schema, so loading a Postgres `vector` column through
them would try to read a string as packed float32 bytes and produce silent
garbage. Raw SQL hands back the text form, which is parsed explicitly below.
"""
import argparse
import json
import sys

from sqlalchemy import create_engine, text

from app.config import settings
from app.db import models
from app.db.session import SessionLocal

DEFAULT_SOURCE = "postgresql+psycopg://jobsearch:jobsearch@localhost:5432/jobsearch"

# Parents before children: every table here is inserted after the ones it points
# at, so foreign keys hold at every step (SQLite enforces them - see session.py).
TABLES: list[tuple[str, type]] = [
    ("candidate_profile", models.CandidateProfile),
    ("preferences", models.Preferences),
    ("companies", models.Company),
    ("resume_templates", models.ResumeTemplate),
    ("kb_chunks", models.KBChunk),
    ("jobs", models.Job),
    ("job_requirements", models.JobRequirements),
    ("job_embeddings", models.JobEmbedding),
    ("matches", models.Match),
    ("resumes", models.Resume),
    ("applications", models.Application),
    ("contacts", models.Contact),
    ("project_ideas", models.ProjectIdea),
    ("pipeline_runs", models.PipelineRun),
    ("ingestion_runs", models.IngestionRun),
]

# Columns that were pgvector and are now packed bytes.
VECTOR_COLUMNS = {"embedding"}


def _to_vector(value) -> list[float] | None:
    """pgvector renders as '[0.1,0.2,...]' over raw SQL; the ORM wants a list."""
    if value is None:
        return None
    if isinstance(value, (list, tuple)):
        return [float(v) for v in value]
    return [float(part) for part in str(value).strip("[]").split(",") if part.strip()]


def _to_json(value):
    """JSONB arrives decoded, but a plain json/text column may still be a string."""
    if isinstance(value, (str, bytes)):
        try:
            return json.loads(value)
        except (ValueError, TypeError):
            return value
    return value


def copy_all(source_url: str) -> dict[str, int]:
    src = create_engine(source_url, future=True)
    counts: dict[str, int] = {}

    with src.connect() as conn, SessionLocal() as dest:
        for table, model in TABLES:
            columns = {c.name: c for c in model.__table__.columns}
            rows = conn.execute(text(f"SELECT * FROM {table}")).mappings().all()

            for row in rows:
                values = {}
                for name, raw in row.items():
                    column = columns.get(name)
                    if column is None:
                        continue  # a column this version of the app dropped
                    if name in VECTOR_COLUMNS:
                        values[name] = _to_vector(raw)
                    elif column.type.__class__.__name__ == "JSON":
                        values[name] = _to_json(raw)
                    else:
                        values[name] = raw
                dest.merge(model(**values))

            dest.commit()
            counts[table] = len(rows)
            print(f"  {table:20s} {len(rows):6d}")

    # No id-sequence fixup is needed afterwards. An Integer primary key becomes
    # `INTEGER PRIMARY KEY` in SQLite, which is an alias for the rowid, and the
    # next insert gets MAX(id) + 1 for free. (Only AUTOINCREMENT keeps a
    # separate counter in sqlite_sequence, and nothing here uses it.)
    return counts


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--from", dest="source", default=DEFAULT_SOURCE)
    args = parser.parse_args()

    if not settings.database_url.startswith("sqlite"):
        print(
            "The destination is not SQLite. DATABASE_URL is set to a Postgres\n"
            "URL, so this would copy Postgres onto itself. Remove DATABASE_URL\n"
            "from .env and run this again.",
            file=sys.stderr,
        )
        return 1

    print(f"from: {args.source}")
    print(f"to:   {settings.database_url}\n")
    try:
        copy_all(args.source)
    except Exception as exc:
        print(f"\nMigration failed: {exc}", file=sys.stderr)
        print("Nothing was removed from Postgres - it is safe to retry.", file=sys.stderr)
        return 1

    print("\nDone. Postgres was not modified; delete the container when you're happy.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
