"""
Shared test fixtures for the Timetable LLM backend.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app

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
