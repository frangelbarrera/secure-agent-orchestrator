# Contributing

Pull requests are welcome. Please read the rules below before opening one.

## Non-negotiable rules

1. **Do not weaken security.** Any PR that removes a config validator,
   relaxes a password rule, widens CORS, or disables the token blacklist
   will be rejected.
2. **Do not ship features that are not wired up.** If you add a module,
   it must be imported and called somewhere. Dead code will be removed.
3. **Do not make quantitative claims in the README without evidence.**
   "1000+ concurrent agents", "99.9% uptime", "100% secure" — these
   were removed from the previous README because they were fabricated.
   Do not bring them back without load tests, monitoring, and a security
   audit to back them up.
4. **Do not add the `*` wildcard to CORS_ORIGINS.** The validator
   rejects it in non-LOCAL environments; do not work around it.
5. **Do not add `cache()` decorators or `RateLimiter` stubs.** Both
   were removed because they were no-ops. If you need caching or rate
   limiting, implement them for real (with Redis, memory, or a CDN) and
   add tests.

## Workflow

1. Fork the repo and create a feature branch from `main`.
2. Write tests for any new behavior. The test suite lives in `tests/`
   and uses pytest + pytest-asyncio + httpx. Run it locally:
   ```bash
   pytest --cov=src/app --cov-report=term-missing
   ```
3. Make sure ruff passes:
   ```bash
   ruff check src tests scripts
   ruff format --check src tests scripts
   ```
4. Make sure the smoke test passes:
   ```bash
   ENVIRONMENT=local \
     SECRET_KEY=$(python -c "import secrets;print(secrets.token_urlsafe(32))") \
     ADMIN_PASSWORD="StrongTestAdminPass123!" \
     python scripts/smoke_test.py
   ```
5. Open a PR. The CI workflow will run lint, tests, security scan
   (pip-audit), and a Docker build smoke test. All must pass.

## Commit message conventions

Follow the conventional-commits style:

```
<type>(<scope>): <subject>

<body>
```

Where `type` is one of: `feat`, `fix`, `security`, `chore`, `docs`,
`refactor`, `test`. `scope` is the affected module (e.g. `config`,
`api`, `core`). Examples:

```
security(config): require strong SECRET_KEY and ADMIN_PASSWORD
fix(api): require auth on GET /users
chore(infra): split runtime/dev requirements
docs(readme): rewrite honestly
```

## Code style

- Python 3.11+. Use modern syntax (`X | None` instead of `Optional[X]`).
- SQLAlchemy 2.0 `Mapped` / `mapped_column` style for models.
- pydantic v2 `BaseModel` with `ConfigDict` for schemas.
- `async def` everywhere in the API layer; blocking calls (bcrypt,
  file I/O) must run in `anyio.to_thread.run_sync`.
- Max line length: 120.
- Docstrings: numpy convention.

## Adding a new endpoint

1. Define the pydantic schema in `src/app/schemas/<resource>.py`.
2. Add the route in `src/app/api/v1/<resource>.py`. Use
   `Depends(get_current_user)` or `Depends(get_current_superuser)` for
   auth.
3. Register the router in `src/app/api/v1/__init__.py`.
4. Add tests in `tests/test_<resource>.py`. At minimum:
   - Happy path.
   - Unauthenticated request returns 401.
   - Forbidden request (wrong role) returns 403.
   - Input validation rejects malformed payloads.
5. Update the API table in `README.md`.
