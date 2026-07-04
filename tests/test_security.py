"""Security-focused tests for the auth core.

These exercise the bugs that were fixed in the security refactor:
- The config validator must reject the known-insecure SECRET_KEY and
  ADMIN_PASSWORD placeholders.
- The password complexity validator must reject weak passwords.
- bcrypt verify must be True for the right password and False for a
  wrong one, and must work for passwords longer than 72 bytes (the
  bcrypt truncation boundary).
"""
from __future__ import annotations

import importlib
import os
import secrets

import pytest


def _reload_config():
    """Force a fresh import of src.app.core.config so env var changes
    take effect for the validator under test."""
    import src.app.core.config as cfg

    return importlib.reload(cfg)


def test_secret_key_validator_rejects_placeholder(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "secret-key")
    with pytest.raises(Exception, match="known-insecure placeholder"):
        _reload_config()


def test_secret_key_validator_rejects_short(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "short")
    with pytest.raises(Exception, match="32 characters"):
        _reload_config()


def test_secret_key_validator_accepts_strong(monkeypatch):
    strong = secrets.token_urlsafe(32)
    monkeypatch.setenv("SECRET_KEY", strong)
    cfg = _reload_config()
    assert cfg.settings.SECRET_KEY.get_secret_value() == strong


def test_admin_password_validator_rejects_placeholder(monkeypatch):
    monkeypatch.setenv("ADMIN_PASSWORD", "!Ch4ng3Th1sP4ssW0rd!")
    with pytest.raises(Exception, match="known-insecure placeholder"):
        _reload_config()


def test_admin_password_validator_rejects_short(monkeypatch):
    monkeypatch.setenv("ADMIN_PASSWORD", "short")
    with pytest.raises(Exception, match="12 characters"):
        _reload_config()


def test_cors_validator_rejects_wildcard_in_production(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("CORS_ORIGINS", '["*"]')
    with pytest.raises(Exception, match="cannot contain '\\*'"):
        _reload_config()


def test_cors_validator_accepts_explicit_in_production(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("CORS_ORIGINS", '["https://example.com"]')
    cfg = _reload_config()
    assert cfg.settings.CORS_ORIGINS == ["https://example.com"]


# --- password complexity --------------------------------------------------


@pytest.mark.parametrize(
    "password",
    [
        "a",                # too short, missing everything
        "abcdefgh",         # no upper, no digit, no special
        "ABCDEFGH",         # no lower, no digit, no special
        "abcdEFGH",         # no digit, no special
        "abcdEFG1",         # no special
        "abcdEFG!",         # no digit
    ],
)
def test_password_complexity_rejects_weak(password):
    """The UserCreate validator must reject passwords missing any of the
    four required character categories."""
    from pydantic import ValidationError

    from src.app.schemas.user import UserCreate

    with pytest.raises((ValidationError, ValueError)):
        UserCreate(
            name="Test User",
            username="weakpwd",
            email="weak@example.com",
            password=password,
        )


@pytest.mark.parametrize(
    "password",
    [
        "StrongTestPassword123!",  # all four categories
        "An0ther!Valid*Password",
        "P@ssw0rdWithLotsOfChars",
    ],
)
def test_password_complexity_accepts_strong(password):
    from src.app.schemas.user import UserCreate

    user = UserCreate(
        name="Test User",
        username="testuser",
        email="test@example.com",
        password=password,
    )
    assert user.password == password


# --- bcrypt pre-hash boundary --------------------------------------------


@pytest.mark.asyncio
async def test_bcrypt_handles_passwords_longer_than_72_bytes():
    """bcrypt truncates at 72 bytes. Our pre-hash with SHA-256 prevents that."""
    from src.app.core.security import get_password_hash_async, verify_password

    long_password = "a" * 200 + "A1!"  # 203 chars, well over 72 bytes
    hashed = await get_password_hash_async(long_password)
    assert await verify_password(long_password, hashed) is True
    assert await verify_password(long_password + "x", hashed) is False
