"""FastAPI application entry point for Talentflow AI."""

from dotenv import load_dotenv

# Load local environment settings before importing modules that create the DB engine.
load_dotenv()

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import models  # noqa: F401 - register database tables before create_all
from .database import Base, engine
from .routes import admin, auth, candidates, dashboard, jobs, matching, resumes

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # For this small prototype, create_all keeps first-time setup straightforward.
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="Talentflow AI", description="Resume extraction and candidate matching prototype", lifespan=lifespan)
app.include_router(auth.router, prefix="/api")
app.include_router(resumes.router, prefix="/api")
app.include_router(candidates.router, prefix="/api")
app.include_router(jobs.router, prefix="/api")
app.include_router(matching.router, prefix="/api")
app.include_router(admin.router, prefix="/api")
app.include_router(dashboard.router, prefix="/api")
app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


@app.get("/", include_in_schema=False)
def frontend():
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/health", include_in_schema=False)
def health():
    return {"status": "ok"}
