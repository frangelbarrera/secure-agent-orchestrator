# Secure Agent Orchestrator

[![CI](https://github.com/frangelbarrera/secure-agent-orchestrator/actions/workflows/ci.yml/badge.svg)](https://github.com/frangelbarrera/secure-agent-orchestrator/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-009688.svg)](https://fastapi.tiangolo.com/)

> **Status: early-stage.** This is a FastAPI control plane for registering
> security agents and their command tasks. It is **not** a SOAR: there is no
> command execution, no agent pull/push protocol, no sandboxing, no
> heartbeat. See the [What this is not](#what-this-is-not) section before
> deploying it anywhere.

## What this is

A small, audited FastAPI service that:

- Authenticates users with JWT (access + refresh) backed by a database
  token blacklist so logout actually invalidates tokens.
- Registers security agents as rows in a SQLite database.
- Records command tasks against those agents in `PENDING` state, with
  per-task status tracking (`PENDING`, `RUNNING`, `COMPLETED`, `ERROR`).
- Exposes a paginated, role-aware REST API for the above.
- Ships with a CRUDAdmin interface (disabled by default) for managing
  `User` and `Tier` rows from a browser.

The service is intentionally small. The codebase is ~2200 lines of
Python, plus tests, plus a Dockerfile and a Render Blueprint.

## Screenshots

The following screenshots were captured from a local instance running
with `ENVIRONMENT=local` and a freshly generated `SECRET_KEY`. They
show the actual UI and API responses, not mockups. Each screenshot was
verified by a vision model before being accepted; any capture that
showed a server error, a blank page, or content that did not match its
stated purpose was discarded and re-captured.

### Swagger UI (`/docs`)

Interactive API documentation. In `local` it is public; in `staging`
it requires superuser auth; in `production` it is disabled entirely.

![Swagger UI](docs/screenshots/01-swagger-ui.png)

### ReDoc (`/redoc`)

Alternative read-only documentation renderer.

![ReDoc UI](docs/screenshots/02-redoc-ui.png)

### Health endpoint (`GET /api/v1/health`)

Public liveness probe, no auth required.

![Health endpoint](docs/screenshots/03-health-endpoint.png)

### OpenAPI schema (`/openapi.json`)

The full OpenAPI 3.1 schema exposed as JSON.

![OpenAPI schema](docs/screenshots/04-openapi-schema.png)

### 401 on unauthenticated `GET /api/v1/users`

The user listing endpoint requires superuser auth. An unauthenticated
request gets a 401 with `Cache-Control: private, no-store` — a
defense-in-depth measure that prevents a CDN or shared proxy from
serving the 401 response to a different user.

![401 on /users](docs/screenshots/05-401-unauthorized.png)

### Functional smoke test

The `scripts/smoke_test.py` script exercises the security-critical
flows end-to-end. All 10 checks pass.

![Smoke test output](docs/screenshots/06-smoke-test.png)

### Test & coverage report

29 pytest tests covering config validators, password complexity, bcrypt
pre-hash boundary, and the security-critical API flows. 73% line
coverage of `src/app`; the critical modules (config, security,
middleware, models, schemas, db) are at 90–100%.

![Test & coverage report](docs/screenshots/07-test-coverage.png)

## What this is not

- **Not a SOAR.** The `/security-agents/{id}/command` endpoint records
  a task; it does **not** execute it. There is no subprocess, no SSH,
  no agent pull/push protocol. Picking up recorded tasks and acting on
  them is out of scope for this control plane.
- **Not production-hardened.** Although the security audit found and
  fixed eight critical issues, the test suite is small, there is no
  observability (no metrics, no tracing, no structured logging), and
  the database is SQLite-on-disk with no WAL or replication.
- **Not multi-database.** SQLite only. The Postgres and MySQL settings
  blocks that previous versions of this repo advertised were dead code
  and have been removed.
- **Not distributed.** Single process, single SQLite file. Do not put
  multiple workers behind a load balancer against the same SQLite file
  without WAL mode and careful testing.

## Quick start

```bash
# Clone
git clone https://github.com/frangelbarrera/secure-agent-orchestrator.git
cd secure-agent-orchestrator

# Create a virtualenv and install runtime + dev dependencies
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt

# Configure environment. SECRET_KEY and ADMIN_PASSWORD are required in
# every environment; the config validator will refuse to start without
# strong values. Generate a SECRET_KEY with:
python -c "import secrets; print(secrets.token_urlsafe(32))"

cp .env.example .env
# Edit .env: set SECRET_KEY and ADMIN_PASSWORD to real values.

# Run the API (LOCAL env, so /docs is public)
uvicorn src.app.main:app --reload
```

The interactive API documentation is at `http://localhost:8000/docs`.

## Functional smoke test

A single-process end-to-end smoke test exercises the most security-relevant
behaviors (401 on unauthenticated user listing, 403 for non-admin,
`Cache-Control: private, no-store` on authed responses, register + login
flow, 404 on the removed `/execute-command` path).

```bash
ENVIRONMENT=local \
  SECRET_KEY=$(python -c "import secrets;print(secrets.token_urlsafe(32))") \
  ADMIN_PASSWORD="StrongTestAdminPass123!" \
  python scripts/smoke_test.py
```

Expected output: `ALL SMOKE TESTS PASSED`.

## Configuration

All configuration is via environment variables (or a `.env` file at the
project root). The full template is in [`.env.example`](.env.example).

| Variable | Required | Default | Notes |
|---|---|---|---|
| `ENVIRONMENT` | yes | `local` | One of `local`, `staging`, `production`. Controls docs exposure and validator strictness. |
| `SECRET_KEY` | yes | (none) | JWT signing key. Validator rejects the literal `"secret-key"` placeholder and any value < 32 chars. Generate with `python -c "import secrets; print(secrets.token_urlsafe(32))"`. |
| `ADMIN_NAME`, `ADMIN_EMAIL`, `ADMIN_USERNAME`, `ADMIN_PASSWORD` | yes | (placeholder) | First superuser bootstrap. `ADMIN_PASSWORD` validator rejects the literal `"!Ch4ng3Th1sP4ssW0rd!"` placeholder and any value < 12 chars. |
| `SQLITE_URI` | no | `./sql_app.db` | SQLite file path. |
| `CORS_ORIGINS` | no | `["http://localhost:3000", "http://localhost:8000"]` | Explicit origins only. `*` is rejected in non-LOCAL environments. |
| `CORS_METHODS` | no | explicit list | `*` is rejected in non-LOCAL. |
| `CORS_HEADERS` | no | explicit list | `*` is rejected in non-LOCAL. |
| `CRUD_ADMIN_ENABLED` | no | `false` | Set to `true` to mount the CRUDAdmin UI at `/admin`. Pair with `CRUD_ADMIN_ALLOWED_IPS_LIST`. |
| `CRUD_ADMIN_ALLOWED_IPS_LIST` | no | `["127.0.0.1", "::1"]` | IP allowlist for the admin UI. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | no | `30` | JWT access token TTL. |
| `REFRESH_TOKEN_EXPIRE_DAYS` | no | `7` | JWT refresh token TTL (stored in HttpOnly cookie). |

### Environment semantics

| Environment | `/docs` | `/openapi.json` | CORS `*` allowed | CRUDAdmin default |
|---|---|---|---|---|
| `local` | public | public | yes (with `allow_credentials=False`) | off |
| `staging` | superuser-only | superuser-only | no | off |
| `production` | disabled | disabled | no | off |

## API surface

All endpoints are prefixed with `/api/v1`.

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/health` | none | Liveness probe. |
| `POST` | `/login` | none | Exchange username + password for an access token. Refresh token set in HttpOnly cookie. |
| `POST` | `/refresh` | refresh cookie | Exchange a refresh token for a new access token. |
| `POST` | `/logout` | access token | Blacklist the access and refresh tokens. |
| `POST` | `/user` | none | Register a new user. Password must satisfy the complexity validator. |
| `GET` | `/users` | superuser | Paginated user list. |
| `GET` | `/user/me/` | access token | Current user profile. |
| `GET` | `/user/{username}` | access token | Lookup another user by username. |
| `PATCH` | `/user/{username}` | access token (self) | Update profile. |
| `DELETE` | `/user/{username}` | access token (self) | Soft-delete. |
| `DELETE` | `/db_user/{username}` | superuser | Hard-delete. |
| `GET` | `/user/{username}/tier` | none | Public tier lookup. |
| `PATCH` | `/user/{username}/tier` | superuser | Assign tier. |
| `GET` | `/security-agents/` | access token | List registered agents. |
| `POST` | `/security-agents/{id}/command` | access token | Register a command task against an agent. **Does not execute.** |
| `GET` | `/security-agents/{id}/task-status/{task_id}` | access token | Lookup task status. |

## Security model

- **JWT** (`HS256`) with separate access (30 min) and refresh (7 day) tokens.
- **Refresh token rotation** is not implemented; the refresh endpoint
  issues a new access token without invalidating the refresh token.
- **Token blacklist** is database-backed. On logout, both the access and
  refresh tokens are inserted into the blacklist with their natural
  expiry. `verify_token` checks the blacklist before accepting any token.
- **bcrypt** with SHA-256 pre-hashing. bcrypt silently truncates inputs
  at 72 bytes; we pre-hash with SHA-256 (32-byte digest) so any-length
  passwords are protected. bcrypt runs in a thread pool so it does not
  block the event loop.
- **CORS** defaults to an explicit localhost allowlist. `*` is rejected
  in non-LOCAL environments. `allow_credentials` is only enabled when
  the origins list does not contain `*`.
- **Cache-Control** is `private, no-store` on any response to a request
  that carried an `Authorization` header, and on any error response.
  Public responses (health, public listings) get `public, max-age=60`.
  This prevents a CDN or shared proxy from serving one user's
  authenticated response to another.
- **Password complexity** is enforced by a `field_validator` on
  `UserCreate.password`: at least one lowercase, one uppercase, one
  digit, one special character, 8–128 chars.
- **Timing oracle**: `authenticate_user` runs a dummy bcrypt
  verification against a fixed invalid hash when the username does not
  exist, so the response time does not leak user existence.

### Known limitations

- No rate limiting. The previous `RateLimiter` was a stub that always
  returned `False`; it has been removed. The `POST /login` and
  `POST /user` endpoints are not protected against brute force. Put a
  rate limiter (Cloudflare, nginx, or a real Redis-backed limiter) in
  front of the service if you expose it publicly.
- No CSRF protection on cookie-based endpoints. The refresh token is
  set with `SameSite=Lax`, which mitigates the most common CSRF vector
  but is not a complete defense.
- SQLite only. Foreign keys are not enforced at the driver level
  (`PRAGMA foreign_keys=ON` is not set). Soft-delete is implemented
  per-model via `is_deleted`, but not consistently across all models.
- No structured logging. The `logging` module is used directly; output
  is plain text, not JSON.

## Testing

```bash
# Run unit + smoke tests
pytest

# With coverage
pytest --cov=src/app --cov-report=term-missing
```

The test suite lives in `tests/` and `scripts/smoke_test.py`. The smoke
test is also runnable standalone (see [Functional smoke test](#functional-smoke-test)).

## Deployment

### Render

The [`render.yaml`](render.yaml) Blueprint describes a single web service
on the free tier. SECRET_KEY and ADMIN_PASSWORD are generated at first
deploy. CORS is set to the demo URL only.

```bash
# From the Render dashboard, create a new Blueprint and point it at
# this repository. Render will read render.yaml and provision the service.
```

### Docker

```bash
docker build -t secure-agent-orchestrator .
docker run --rm -p 8000:8000 \
  -e ENVIRONMENT=production \
  -e SECRET_KEY=$(python -c "import secrets;print(secrets.token_urlsafe(32))") \
  -e ADMIN_PASSWORD="StrongAdminPassword123!" \
  -e CORS_ORIGINS='["https://your-frontend.example.com"]' \
  secure-agent-orchestrator
```

The image runs as a non-root user (`appuser`, uid 1000), includes a
`HEALTHCHECK` against `/api/v1/health`, and excludes dev dependencies
from the final stage.

## Project structure

```
src/
├── app/
│   ├── admin/           # CRUDAdmin integration (disabled by default)
│   ├── api/
│   │   ├── dependencies.py    # get_current_user, get_current_superuser
│   │   └── v1/
│   │       ├── health.py
│   │       ├── login.py       # /login, /refresh
│   │       ├── logout.py      # /logout (blacklist)
│   │       ├── users.py       # /user, /users
│   │       ├── security_agents.py  # /security-agents, /command
│   │       └── tiers.py
│   ├── core/
│   │   ├── config.py    # pydantic-settings with validators
│   │   ├── security.py  # JWT, bcrypt, blacklist helpers
│   │   ├── setup.py     # app factory, lifespan, middleware
│   │   ├── db/          # async engine, Base, token_blacklist CRUD
│   │   └── exceptions/  # HTTP exception classes
│   ├── crud/            # one FastCRUD module per model
│   ├── models/          # SQLAlchemy 2.0 MappedAsDataclass models
│   ├── schemas/         # pydantic v2 schemas
│   ├── middleware/      # ClientCacheMiddleware
│   └── main.py          # app instance
├── migrations/          # Alembic (env.py only; no migration files yet)
└── scripts/
    ├── create_first_superuser.py
    └── create_first_tier.py
scripts/
└── smoke_test.py        # end-to-end functional test
tests/
└── test_*.py            # unit tests
```

## Audit history

This repository underwent a full security audit in July 2026. The audit
found and fixed eight critical issues, including hardcoded JWT secret and
admin password defaults, CORS `*` + credentials, a stub rate limiter
shipped as a feature, a no-op cache decorator shipped as a feature, a
fake `/execute-command` endpoint with a broken background task, and
publicly readable user listings. The full audit worklog is available on
request. See [`CHANGELOG.md`](CHANGELOG.md) for the version history.

## Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md). In short: do not open pull
requests that weaken security, do not reintroduce `*` to CORS, do not
ship features that are not wired up, and do not make quantitative claims
in the README without evidence.

## License

MIT. See [`LICENSE`](LICENSE).
