from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import text

from app.api.routes import router
from app.core.config import get_settings
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.models import *  # noqa: F401,F403 - register metadata
from app.services.journal import ensure_journal_head

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    with engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        Base.metadata.create_all(bind=conn)
    with SessionLocal() as db:
        ensure_journal_head(db)
        db.commit()
    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "Local-first API for a personal, evidence-based, temporal Cognitive Digital Twin. "
        "The Twin models the subject; it does not define the subject."
    ),
    lifespan=lifespan,
)
app.include_router(router, prefix="/api/v1")


@app.get("/")
def root() -> dict:
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs",
        "principle": "The Twin models the person; it does not define the person.",
    }
