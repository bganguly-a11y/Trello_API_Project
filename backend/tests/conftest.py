"""Shared pytest fixtures for unit and integration tests."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app


# ---------------------------------------------------------------------------
# Database setup — one in-memory SQLite per test session
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def test_engine():
    """Create a fresh in-memory SQLite engine for the entire test session."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    engine.dispose()


@pytest.fixture(scope="session")
def _session_factory(test_engine):
    return sessionmaker(bind=test_engine, autocommit=False, autoflush=False)


@pytest.fixture()
def db_session(_session_factory):
    """Yield a DB session; roll back after each test to keep tests isolated."""
    session = _session_factory()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


# ---------------------------------------------------------------------------
# HTTP client — overrides get_db to use the test DB
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def client(test_engine, _session_factory):
    """TestClient with get_db overridden to the in-memory test DB."""
    def override_get_db():
        db = _session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def _register(client, email, password="secret123", name="Test User"):
    r = client.post("/auth/register", json={
        "email": email, "password": password, "name": name,
    })
    assert r.status_code == 201, r.text
    return r.json()


def _login(client, email, password="secret123"):
    r = client.post("/auth/login",
                    data={"username": email, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def auth(token: str) -> dict:
    """Return Authorization header dict."""
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Pre-baked user fixtures  (session-scoped — registered once per run)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def alice_token(client):
    _register(client, "alice_fix@example.com", name="Alice")
    return _login(client, "alice_fix@example.com")


@pytest.fixture(scope="session")
def bob_token(client):
    _register(client, "bob_fix@example.com", name="Bob")
    return _login(client, "bob_fix@example.com")
