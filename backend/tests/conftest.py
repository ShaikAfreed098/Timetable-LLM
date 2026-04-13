"""
Shared test fixtures for the Timetable LLM backend.
Uses SQLite so tests run without a MySQL server.
"""
import os
import sys

# ── Set env BEFORE any app module is imported ──────────────────────────────────
# This must happen before pydantic-settings reads the .env file via Settings().
os.environ["DATABASE_URL"] = "sqlite:///./test_timetable.db"

# Force a fresh import of app modules so they use the patched env var
for mod in list(sys.modules.keys()):
    if mod.startswith("app"):
        del sys.modules[mod]

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from app.database import Base, get_db  # noqa: E402
from app.main import app               # noqa: E402

TEST_DATABASE_URL = "sqlite:///./test_timetable.db"

engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="session", autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def db():
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client(db):
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def auth_headers(client):
    """Register + login as super_admin and return auth headers."""
    client.post(
        "/api/auth/register",
        json={
            "username": "testadmin",
            "email": "testadmin@example.com",
            "password": "testpass123",
            "role": "super_admin",
        },
    )
    resp = client.post(
        "/api/auth/token",
        data={"username": "testadmin", "password": "testpass123"},
    )
    token = resp.json().get("access_token", "")
    return {"Authorization": f"Bearer {token}"}
