# Changelog

All notable changes to this project will be documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
and the project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] — 2026-07-04

### Security

- **BREAKING:** `SECRET_KEY` is now required in every environment. The
  config validator rejects the literal `"secret-key"` placeholder and
  any value shorter than 32 characters. Generate one with
  `python -c "import secrets; print(secrets.token_urlsafe(32))"`.
- **BREAKING:** `ADMIN_PASSWORD` is now required in every environment.
  The validator rejects the literal `"!Ch4ng3Th1sP4ssW0rd!"` placeholder
  and any value shorter than 12 characters.
- **BREAKING:** `CORS_ORIGINS`, `CORS_METHODS`, and `CORS_HEADERS` no
  longer default to `"*"`. The validator rejects `"*"` in non-LOCAL
  environments. `allow_credentials` is only enabled when the origins
  list does not contain `"*"`.
- bcrypt now runs in a thread pool (`anyio.to_thread.run_sync`) so it
  does not block the event loop during login or registration.
- Passwords are pre-hashed with SHA-256 before bcrypt to prevent silent
  truncation of passwords longer than 72 bytes.
- `authenticate_user` runs a dummy bcrypt verification when the username
  does not exist, so the response time does not leak user existence.
- `Cache-Control: private, no-store` is now set on any response to a
  request that carried an `Authorization` header, and on any error
  response. Previously every response was `public, max-age=60`.
- The `POST /api/v1/user` password field now has an explicit
  `field_validator` enforcing one lowercase, one uppercase, one digit,
  one special character, and 8–128 chars. The previous regex
  `^.{8,}|[0-9]+|[A-Z]+|[a-z]+|[^a-zA-Z0-9]+$` accepted `"a"` as valid.
- `GET /api/v1/users` now requires superuser. `GET /api/v1/user/{username}`
  now requires authentication. Both were previously public.
- `CRUDAdmin` is now disabled by default and paired with a localhost-only
  IP allowlist when enabled. It previously defaulted to on with no
  allowlist.
- The Dockerfile now ships a `.dockerignore` that excludes `.env`, `.git`,
  `__pycache__`, the local SQLite database, tests, and scripts from the
  build context.
- `requirements.txt` and `requirements-dev.txt` are now split. The
  production Docker image no longer ships `ruff`, `mypy`, `pytest`, or
  other dev tools.
- `python-multipart` lower bound bumped to `>=0.0.18` to dodge the
  known CVE in older 0.0.x releases.

### Removed

- **BREAKING:** The `POST /security-agents/{id}/execute-command`
  endpoint is gone. It was a fake: `asyncio.sleep(5)` followed by a
  hardcoded `"Command executed successfully"` result. The background
  task also captured a request-scoped `AsyncSession` that was already
  closed by the time the task woke up, so tasks stayed in `PENDING`
  forever. Replaced by `POST /security-agents/{id}/command`, a
  registry-only endpoint that creates a `CommandTask` row in `PENDING`
  state and explicitly does not execute anything.
- **BREAKING:** The `RateLimiter` stub (`core/utils/rate_limit.py`) is
  removed. It always returned `False`, was never wired to any router,
  and was advertised in the README as a feature.
- **BREAKING:** The `cache()` decorator (`core/utils/cache.py`) is
  removed. Its docstring literally said "does nothing". It was
  advertised in the README as "Redis caching".
- **BREAKING:** The `Post` model, `crud_posts`, `posts.py` router, and
  `schemas/post.py` are removed. They were inherited from a
  social-media starter template and had no purpose in a security agent
  orchestrator.
- **BREAKING:** The `RateLimit` model, `crud_rate_limit`,
  `rate_limits.py` router, and `schemas/rate_limit.py` are removed.
  They were a dead config: nothing in the runtime read the rows.
- **BREAKING:** `PostgresSettings` and `MySQLSettings` are removed from
  `config.py`. The runtime has always used SQLite; the Postgres and
  MySQL settings blocks were dead code advertised as "multi-DB support".
- **BREAKING:** The `RedisCacheSettings`, `RedisQueueSettings`, and
  `RedisRateLimiterSettings` blocks are removed from `config.py`.
- `profile_image_url` column removed from the `User` model. It was
  inherited from a social-media starter template.
- `cache_exceptions.py` removed (only used by the removed `cache.py`).
- `uuid>=1.30` PyPI dependency removed (the stdlib `uuid` module is
  what the code actually imports).

### Added

- `tests/` directory with 29 pytest tests covering config validators,
  password complexity, bcrypt pre-hash boundary, and the security-critical
  API flows (auth, registration, login, logout, cache-control,
  execute-command removal, RBAC).
- `scripts/smoke_test.py` — a single-process end-to-end smoke test.
- `.github/workflows/ci.yml` — CI pipeline running ruff, pytest with
  coverage, pip-audit security scan, and a Docker build smoke test.
- `.dockerignore` — excludes `.env`, `.git`, `__pycache__`, the local
  SQLite database, tests, and scripts from the build context.
- `SECURITY.md`, `CONTRIBUTING.md`, `CHANGELOG.md`.
- `requirements-dev.txt` for dev dependencies.
- `[tool.pytest.ini_options]`, `[tool.coverage.run]`,
  `[tool.coverage.report]`, `[tool.mypy]` blocks in `pyproject.toml`.
- The lifespan now calls `await engine.dispose()` on shutdown so
  worker reloads do not leak SQLAlchemy async sockets.
- `docs_url`, `redoc_url`, and `openapi_url` are now fully disabled in
  PRODUCTION (previously they were gated behind superuser auth but
  still mounted).

### Changed

- `pyproject.toml` version bumped from `0.1.0` to `0.2.0` to reflect
  the breaking changes.
- `render.yaml` CORS_ORIGINS changed from `["*"]` to the explicit demo
  URL. The validator would have rejected `*` in staging anyway.
- `Dockerfile` `COPY` tightened from `COPY . .` to `COPY src ./src`
  and `COPY alembic.ini ./alembic.ini`.
- `mccabe` max-complexity reduced from 24 to 15.
- README rewritten. All fabricated claims removed ("100% secure",
  "Production Ready", "99.9% uptime", "1000+ concurrent agents",
  "Rate limited", "Redis caching", "Sub-100ms command execution",
  "Enterprise-grade security"). Replaced with honest descriptions of
  what the service actually does and does not do.

### Fixed

- `src/scripts/create_first_tier.py` was broken at import time: it
  imported `config` (a python-decouple pattern) from a module that
  only exports `settings`. Now uses `settings` directly.
- `src/scripts/create_first_superuser.py` imported
  `sqlalchemy.dialects.postgresql.UUID` (the runtime is SQLite),
  redeclared the user table by hand with a `Table()` construct that
  included the now-removed `profile_image_url` column, and used the
  deprecated `asyncio.get_event_loop()`. Now uses the `User` ORM model
  directly, `asyncio.run()`, and `get_password_hash_async`.
- `core/security.py` `blacklist_token` and `blacklist_tokens` no
  longer crash with `JWTError` when called with an already-expired
  token (the common case at logout if the access token is past its
  30-minute window).
- `core/security.py` `create_access_token` / `create_refresh_token`
  now use `datetime.now(timezone.utc)` consistently instead of mixing
  `datetime.now(UTC).replace(tzinfo=None)`.
- `client_cache_middleware.py` no longer sets `Cache-Control: public`
  on authenticated responses.

## [0.1.0] — 2026-06-30

Initial public release. Subsequently found to contain eight critical
security issues and eleven fabricated README claims; see 0.2.0 above.
