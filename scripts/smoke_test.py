"""Functional smoke test for the refactored secure-agent-orchestrator app.

Run with:
    ENVIRONMENT=local SECRET_KEY=$(python -c "import secrets;print(secrets.token_urlsafe(32))") \
    ADMIN_PASSWORD="StrongTestAdminPass123!" \
    venv/bin/python scripts/smoke_test.py
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# Make the project root importable when running `python scripts/smoke_test.py`.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient

from src.app.main import app


async def main() -> int:
    failures: list[str] = []

    async with LifespanManager(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            # --- health -------------------------------------------------------
            r = await c.get("/api/v1/health")
            print(f"GET  /api/v1/health                       -> {r.status_code} {r.text[:120]}")
            if r.status_code != 200:
                failures.append("health check failed")

            # --- unauthenticated access to /users should be 401 ---------------
            r = await c.get("/api/v1/users")
            print(f"GET  /api/v1/users (no auth)              -> {r.status_code} {r.text[:120]}")
            if r.status_code != 401:
                failures.append(f"GET /api/v1/users without auth returned {r.status_code}, expected 401")

            # --- unauthenticated access to /user/{username} should be 401 -----
            r = await c.get("/api/v1/user/admin")
            print(f"GET  /api/v1/user/admin (no auth)         -> {r.status_code} {r.text[:120]}")
            if r.status_code != 401:
                failures.append(f"GET /api/v1/user/admin without auth returned {r.status_code}, expected 401")

            # --- login with wrong creds should be 401 -------------------------
            r = await c.post(
                "/api/v1/login",
                data={"username": "admin", "password": "WrongPassword123!"},
            )
            print(f"POST /api/v1/login (wrong creds)          -> {r.status_code} {r.text[:120]}")
            if r.status_code != 401:
                failures.append(f"POST /api/v1/login with wrong creds returned {r.status_code}, expected 401")

            # --- cache-control on 401 should be private, no-store -------------
            cache_ctrl = r.headers.get("cache-control", "")
            print(f"     cache-control on 401                 -> {cache_ctrl!r}")
            if "private" not in cache_ctrl.lower() and "no-store" not in cache_ctrl.lower():
                failures.append(f"cache-control on 401 was {cache_ctrl!r}, expected private, no-store")

            # --- register a new user ------------------------------------------
            r = await c.post(
                "/api/v1/user",
                json={
                    "name": "Test User",
                    "username": "testuser",
                    "email": "test@example.com",
                    "password": "StrongTestPassword123!",
                },
            )
            print(f"POST /api/v1/user (register)             -> {r.status_code} {r.text[:120]}")
            if r.status_code != 201:
                failures.append(f"register returned {r.status_code}, expected 201")

            # --- login as the new user ----------------------------------------
            r = await c.post(
                "/api/v1/login",
                data={"username": "testuser", "password": "StrongTestPassword123!"},
            )
            print(f"POST /api/v1/login (valid creds)         -> {r.status_code} {r.text[:120]}")
            if r.status_code != 200:
                failures.append(f"login with valid creds returned {r.status_code}, expected 200")
                return _report(failures)

            token = r.json().get("access_token")
            if not token:
                failures.append("login response missing access_token")
                return _report(failures)

            auth = {"Authorization": f"Bearer {token}"}

            # --- cache-control on authenticated request should be private -----
            r = await c.get("/api/v1/user/me/", headers=auth)
            cache_ctrl_authed = r.headers.get("cache-control", "")
            print(f"GET  /api/v1/user/me/ (authed)           -> {r.status_code} cache={cache_ctrl_authed!r}")
            if r.status_code != 200:
                failures.append(f"GET /api/v1/user/me/ returned {r.status_code}, expected 200")
            if "private" not in cache_ctrl_authed.lower():
                failures.append(
                    f"cache-control on authed request was {cache_ctrl_authed!r}, expected private"
                )

            # --- list users still requires admin (403 for non-admin) ----------
            r = await c.get("/api/v1/users", headers=auth)
            print(f"GET  /api/v1/users (non-admin)           -> {r.status_code} {r.text[:120]}")
            if r.status_code != 403:
                failures.append(
                    f"GET /api/v1/users as non-admin returned {r.status_code}, expected 403"
                )

            # --- /execute-command should be gone (replaced by /command) -------
            r = await c.post(
                "/api/v1/security-agents/agent-1/execute-command",
                json={"command": "ls"},
                headers=auth,
            )
            print(f"POST .../execute-command (deprecated)    -> {r.status_code} {r.text[:120]}")
            if r.status_code != 404:
                failures.append(
                    f"POST /execute-command returned {r.status_code}, expected 404 (endpoint removed)"
                )

            # --- /docs should be available in LOCAL ---------------------------
            r = await c.get("/docs")
            print(f"GET  /docs (LOCAL env)                   -> {r.status_code}")
            if r.status_code != 200:
                failures.append(f"GET /docs in LOCAL returned {r.status_code}, expected 200")

    return _report(failures)


def _report(failures: list[str]) -> int:
    print()
    if not failures:
        print("ALL SMOKE TESTS PASSED")
        return 0
    print(f"SMOKE TEST FAILURES ({len(failures)}):")
    for f in failures:
        print(f"  - {f}")
    return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
