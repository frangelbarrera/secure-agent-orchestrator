"""Shared pytest fixtures for the secure-agent-orchestrator test suite.

Each test gets a fresh in-memory SQLite database, a running app lifespan
(so tables are created), and an httpx AsyncClient pointed at the app via
ASGITransport.
"""
from __future__ import annotations

import asyncio
import os
import secrets
import sys
from collections.abc import AsyncIterator
from pathlib import Path

# Make `src` importable when pytest is invoked from the repo root.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Force a deterministic, strong SECRET_KEY and ADMIN_PASSWORD for tests.
# These are read at import time by src.app.core.config, so they must be
# set before any test module imports the app.
os.environ.setdefault("ENVIRONMENT", "local")
os.environ.setdefault("SECRET_KEY", secrets.token_urlsafe(32))
os.environ.setdefault("ADMIN_PASSWORD", "StrongTestAdminPass123!")
os.environ.setdefault("SQLITE_URI", ":memory:")

import pytest
from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient

from src.app.main import app


@pytest.fixture(scope="session")
def event_loop():
    """Single event loop for the whole test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
async def client() -> AsyncIterator[AsyncClient]:
    """An httpx AsyncClient with the app lifespan running.

    Each test gets a fresh in-memory SQLite database (because the app
    instance is module-level, the engine is shared; but the lifespan
    recreate_tables fixture below wipes it between tests).
    """
    async with LifespanManager(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            yield c


@pytest.fixture(scope="function", autouse=True)
async def recreate_tables():
    """Drop and recreate all tables before each test for isolation."""
    from src.app.core.db.database import Base, async_engine

    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)


@pytest.fixture
def strong_password() -> str:
    return "StrongTestPassword123!"


@pytest.fixture
async def registered_user(client: AsyncClient, strong_password: str) -> dict:
    """Register a non-admin user and return their credentials."""
    payload = {
        "name": "Test User",
        "username": "testuser",
        "email": "test@example.com",
        "password": strong_password,
    }
    r = await client.post("/api/v1/user", json=payload)
    assert r.status_code == 201, r.text
    return {"username": "testuser", "password": strong_password, "email": "test@example.com"}


@pytest.fixture
async def auth_token(client: AsyncClient, registered_user: dict) -> str:
    """Log in as the registered user and return an access token."""
    r = await client.post(
        "/api/v1/login",
        data={"username": registered_user["username"], "password": registered_user["password"]},
    )
    assert r.status_code == 200, r.text
    return r.json()["access_token"]
