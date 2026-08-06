"""The daily run: ingest, then two-tier score.

    python -m app.worker.scheduler          # run once, now
    python -m app.worker.scheduler --daily  # run every day at DAILY_HOUR

Kept in one place so the scheduled job and a manual run are provably the same
code — a scheduler that drifts from what you tested by hand is worse than none.
"""
import argparse
import logging
import time
from datetime import datetime, timedelta

from app.db.session import SessionLocal
from app.ingestion.enrich import enrich
from app.ingestion.pipeline import run_ingestion

log = logging.getLogger(__name__)

# Early morning: boards have posted overnight and the machine is usually idle.
DAILY_HOUR = 7


def run_once(top: int) -> None:
    with SessionLocal() as db:
        runs = run_ingestion(db)
        new = sum(r.jobs_new for r in runs)
        failed = sum(1 for r in runs if not r.ok)
        log.info("ingested: %s new job(s), %s source(s) failed", new, failed)

        counts = enrich(db, top=top)
        log.info(
            "scored: %s filtered, %s estimated, %s extracted",
            counts["filtered"], counts["estimated"], counts["extracted"],
        )


def _seconds_until_next_run() -> float:
    now = datetime.now()
    target = now.replace(hour=DAILY_HOUR, minute=0, second=0, microsecond=0)
    if target <= now:
        target += timedelta(days=1)
    return (target - now).total_seconds()


def main() -> None:
    parser = argparse.ArgumentParser(description="Daily ingest + score.")
    parser.add_argument("--daily", action="store_true", help="keep running, once a day")
    parser.add_argument("--top", type=int, default=100, help="jobs given full LLM extraction")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    if not args.daily:
        run_once(args.top)
        return

    while True:
        delay = _seconds_until_next_run()
        log.info("next run in %.1f hours", delay / 3600)
        time.sleep(delay)
        try:
            run_once(args.top)
        except Exception:  # noqa: BLE001 - one bad night must not kill the loop
            log.exception("daily run failed; will try again tomorrow")


if __name__ == "__main__":
    main()
