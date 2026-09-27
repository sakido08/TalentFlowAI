"""Use SQLite and an isolated in-memory database for API tests."""

import os
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Make test temp files live under the repo so they are writable in restricted Windows environments.
TEMP_ROOT = Path(__file__).resolve().parent.parent / ".pytest_tmp"
TEMP_ROOT.mkdir(exist_ok=True)
for env_name in ("TMPDIR", "TEMP", "TMP"):
    os.environ[env_name] = str(TEMP_ROOT)
tempfile.tempdir = str(TEMP_ROOT)

# Keep the app's startup engine on SQLite in tests even if a developer has PostgreSQL in .env.
os.environ["DATABASE_URL"] = "sqlite:///./talentflow-test-startup.db"

from backend.database import Base, get_db
from backend.main import app


@pytest.fixture
def client():
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSession = sessionmaker(bind=test_engine, autoflush=False, expire_on_commit=False)
    Base.metadata.create_all(test_engine)

    def override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    Base.metadata.drop_all(test_engine)
    test_engine.dispose()
