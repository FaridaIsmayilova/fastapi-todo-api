# tests/conftest.py
import os
from contextlib import contextmanager

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database import Base, get_db

# Ensure JWT envs exist for tests
os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("ALGORITHM", "HS256")
os.environ.setdefault("ACCESS_TOKEN_EXPIRE_MINUTES", "1440")

# In-memory SQLite shared across threads
engine = create_engine(
    "sqlite+pysqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

# Create tables on the test engine
Base.metadata.create_all(bind=engine)

# Disable lifespan so app.main doesn't run create_all on your Postgres engine
@contextmanager
def _noop_lifespan(_app):
    yield
app.router.lifespan_context = _noop_lifespan

# Override get_db to use the test session
def _override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = _override_get_db

# ---------- Fixtures ----------

@pytest.fixture()
def client():
    return TestClient(app)

@pytest.fixture()
def create_user_and_token(client):
    def _make(username: str, password: str = "StrongPass1"):
        # Register
        r = client.post("/auth/register", json={
            "first_name": "Test",
            "last_name": "User",
            "username": username,
            "password": password,
        })
        assert r.status_code in (200, 400), r.text  # 400 if username exists

        # Login (OAuth2 form)
        r = client.post("/auth/login", data={"username": username, "password": password})
        assert r.status_code == 200, r.text
        token = r.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}
    return _make

@pytest.fixture()
def owner_headers(create_user_and_token):
    return create_user_and_token("owner_user")

@pytest.fixture()
def other_headers(create_user_and_token):
    return create_user_and_token("other_user")

@pytest.fixture()
def create_task(client, owner_headers):
    def _make(title="Buy milk", desc="2L milk", status="New", headers=None):
        h = headers or owner_headers
        r = client.post("/tasks", json={
            "title": title,
            "description": desc,
            "status": status
        }, headers=h)
        assert r.status_code in (200, 201), r.text
        return r.json()
    return _make
