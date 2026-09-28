"""FastAPI application entrypoint.

Headless: a knowledge base of your experience, and `POST /tailor` to turn a job
posting into a resume PDF tailored to it.
"""
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api import jobs, kb, profile, resumes, tailor
from app.db.retention import start_sweeper
from app.db.session import get_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Generated resumes expire (see app.db.retention). The sweeper is what makes
    # that true while the app sits idle, rather than only when a request lands.
    start_sweeper()
    yield


app = FastAPI(title="Resume tailor", version="0.1.0", lifespan=lifespan)

app.include_router(kb.router)
app.include_router(jobs.router)
app.include_router(resumes.router)
app.include_router(profile.router)
app.include_router(tailor.router)


@app.get("/health")
def health(db: Session = Depends(get_db)) -> dict:
    """Liveness + DB connectivity check."""
    db.execute(text("SELECT 1"))
    return {"status": "ok", "db": "reachable"}
