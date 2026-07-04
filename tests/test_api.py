"""End-to-end API tests covering the security-critical flows.

These are the same checks that scripts/smoke_test.py performs, but
broken into individual pytest cases so failures are easier to triage.
"""

from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_health_is_public(client):
    r = await client.get("/api/v1/health")
    assert r.status_code == 200
    assert r.json()["status"] == "healthy"


@pytest.mark.asyncio
async def test_users_listing_requires_auth(client):
    r = await client.get("/api/v1/users")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_user_lookup_requires_auth(client):
    r = await client.get("/api/v1/user/someone")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_login_with_wrong_credentials_returns_401(client):
    r = await client.post(
        "/api/v1/login",
        data={"username": "nobody", "password": "WrongPassword123!"},
    )
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_401_response_has_private_no_store_cache_control(client):
    r = await client.post(
        "/api/v1/login",
        data={"username": "nobody", "password": "WrongPassword123!"},
    )
    cache_control = r.headers.get("cache-control", "")
    assert "private" in cache_control.lower()
    assert "no-store" in cache_control.lower()


@pytest.mark.asyncio
async def test_register_then_login_then_me(client, registered_user, auth_token):
    # /user/me/ returns the registered user
    r = await client.get(
        "/api/v1/user/me/",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert r.status_code == 200
    assert r.json()["username"] == registered_user["username"]


@pytest.mark.asyncio
async def test_authenticated_response_has_private_cache_control(client, auth_token):
    r = await client.get(
        "/api/v1/user/me/",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    cache_control = r.headers.get("cache-control", "")
    assert "private" in cache_control.lower(), cache_control


@pytest.mark.asyncio
async def test_non_admin_cannot_list_users(client, auth_token):
    r = await client.get("/api/v1/users", headers={"Authorization": f"Bearer {auth_token}"})
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_execute_command_endpoint_is_gone(client, auth_token):
    r = await client.post(
        "/api/v1/security-agents/agent-1/execute-command",
        json={"command": "ls"},
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_register_command_endpoint_exists(client, auth_token):
    # The agent does not exist yet, so we expect 404 not 201. The point of
    # this test is to assert that the /command path itself is wired up.
    r = await client.post(
        "/api/v1/security-agents/agent-1/command",
        json={"command": "ls"},
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert r.status_code == 404  # agent not found, but the route exists
    # If the route did not exist we would get 404 with {"detail":"Not Found"}.
    # The route handler's 404 returns a different message.
    assert r.json()["detail"] == "Security agent not found"


@pytest.mark.asyncio
async def test_logout_blacklists_access_token(client, registered_user):
    # Login to get an access token and a refresh-token cookie.
    r = await client.post(
        "/api/v1/login",
        data={
            "username": registered_user["username"],
            "password": registered_user["password"],
        },
    )
    assert r.status_code == 200, r.text
    access_token = r.json()["access_token"]
    refresh_cookie = r.cookies.get("refresh_token")
    assert refresh_cookie, "login response must set a refresh_token cookie"

    # Logout with both the Authorization header and the refresh cookie.
    client.cookies.set("refresh_token", refresh_cookie)
    try:
        r2 = await client.post(
            "/api/v1/logout",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert r2.status_code in (200, 204), r2.text
    finally:
        client.cookies.clear()

    # Reusing the access token should now fail because it is blacklisted.
    r3 = await client.get(
        "/api/v1/user/me/",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert r3.status_code == 401


@pytest.mark.asyncio
async def test_docs_available_in_local_env(client):
    r = await client.get("/docs")
    assert r.status_code == 200
