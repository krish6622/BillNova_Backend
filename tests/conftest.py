"""Shared pytest fixtures.

Tests run against an in-memory SQLite database (dialect-agnostic models make this
possible), so CI needs no Postgres. The real Postgres/Neon schema is exercised by
the Alembic migration in deployment.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.main import create_app
from app.models import *  # noqa: F401,F403 — register all tables on Base.metadata
from seeds.seed_plans import seed


@pytest.fixture
def engine():
    eng = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(eng)
    yield eng
    Base.metadata.drop_all(eng)


@pytest.fixture
def db_session(engine):
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    session = TestingSession()
    seed(session)  # subscription plans
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(engine):
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    seeder = TestingSession()
    seed(seeder)  # subscription plans
    seeder.close()

    def override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c


# ---- helpers -------------------------------------------------------------

OWNER = {
    "business_name": "Sri Textiles",
    "owner_name": "Ravi",
    "mobile": "9876543210",
    "email": "ravi@shop.in",
    "password": "supersecret1",
    "gst_number": "33ABCDE1234F1Z5",
}


def register(client, **overrides):
    payload = {**OWNER, **overrides}
    return client.post("/api/auth/register", json=payload)


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}
