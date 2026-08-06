"""Database engine, session factory, and the declarative Base.

All ORM models inherit from `Base`. `get_db` is a FastAPI dependency that yields
a session per request and always closes it.

The database is SQLite: one file, on the user's own machine, for one user. That
needs three deliberate settings, because the app *does* have two writers — the
API thread serving the browser, and the pipeline thread fetching and scoring
jobs for tens of minutes. SQLite handles that fine, but only if configured for
it, and the failure mode otherwise is an "database is locked" error in the
middle of a long fetch. See `_configure_sqlite`.
"""
from collections.abc import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings

_is_sqlite = settings.database_url.startswith("sqlite")

if _is_sqlite:
    engine = create_engine(
        settings.database_url,
        future=True,
        # SQLAlchemy's default would refuse to reuse a connection across
        # threads, and the pipeline runs in one. Safe here because SQLAlchemy's
        # pool hands any single connection to one thread at a time.
        connect_args={"check_same_thread": False},
    )
else:
    # `pool_pre_ping` quietly checks a connection is alive before using it, so a
    # server restart during dev doesn't hand us a dead connection. Kept so a
    # Postgres URL still works for anyone who prefers one.
    engine = create_engine(settings.database_url, pool_pre_ping=True, future=True)


@event.listens_for(engine, "connect")
def _configure_sqlite(dbapi_connection, _record) -> None:
    """PRAGMAs that make concurrent reads and writes actually work.

    These have to be set per connection - SQLite does not persist most of them
    in the file - so this hooks every new pooled connection rather than running
    once at startup.
    """
    if not _is_sqlite:
        return
    cursor = dbapi_connection.cursor()
    # WAL lets readers carry on while a writer holds the write lock. Without it
    # the whole database locks for the duration of every write, and the browser
    # would freeze whenever the pipeline saved a batch of jobs.
    cursor.execute("PRAGMA journal_mode=WAL")
    # Wait for a busy lock instead of failing instantly. The pipeline writes in
    # bursts; a request landing mid-burst should queue for a moment, not 500.
    cursor.execute("PRAGMA busy_timeout=10000")
    # NORMAL is the documented companion to WAL: durable across application
    # crashes, and only at risk in an OS-level crash or power loss. The content
    # here is refetchable job listings, not something worth an fsync per commit.
    cursor.execute("PRAGMA synchronous=NORMAL")
    # SQLite does not enforce foreign keys unless asked, and the schema relies
    # on ON DELETE CASCADE to clean up matches, resumes and contacts with a job.
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    """Base class for all ORM models."""


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency: yields a DB session, guarantees it is closed."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
