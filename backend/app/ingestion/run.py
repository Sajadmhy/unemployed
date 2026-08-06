"""CLI entry point: `python -m app.ingestion.run`

This is the one command that refreshes the job list. It prints a per-company
summary so a failing board is obvious at a glance.
"""
import logging

from app.db.session import SessionLocal
from app.ingestion.pipeline import run_ingestion


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    with SessionLocal() as db:
        runs = run_ingestion(db)

    print(f"\n{'company':<16}{'source':<12}{'seen':>6}{'new':>6}{'upd':>6}{'exp':>6}  status")
    for r in runs:
        status = "ok" if r.ok else f"FAILED: {(r.error or '')[:60]}"
        print(
            f"{r.company:<16}{r.source:<12}{r.jobs_seen:>6}{r.jobs_new:>6}"
            f"{r.jobs_updated:>6}{r.jobs_expired:>6}  {status}"
        )
    total_new = sum(r.jobs_new for r in runs)
    failed = sum(1 for r in runs if not r.ok)
    print(f"\n{total_new} new job(s); {failed} source(s) failed.")


if __name__ == "__main__":
    main()
