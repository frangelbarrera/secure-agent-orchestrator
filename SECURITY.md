# Security Policy

## Supported versions

Only the latest release on `main` is supported. There are no backport
branches.

## Reporting a vulnerability

If you find a security issue, **please do not open a public GitHub
issue**. Instead, email the maintainer at
`frangelrcbarrera@gmail.com` with:

1. A description of the issue and its impact.
2. A minimal reproduction (curl commands, code snippet, or a repo).
3. Your assessment of severity and any suggested fix.

You should receive a first response within 72 hours. If you do not,
please follow up. We will coordinate disclosure with you and credit
your work in the release notes unless you prefer to remain anonymous.

Please do not test against the public Render demo. Spin up a local
instance with a strong `SECRET_KEY` and `ADMIN_PASSWORD` instead:

```bash
docker build -t secure-agent-orchestrator .
docker run --rm -p 8000:8000 \
  -e ENVIRONMENT=local \
  -e SECRET_KEY=$(python -c "import secrets;print(secrets.token_urlsafe(32))") \
  -e ADMIN_PASSWORD="StrongLocalAdminPassword123!" \
  secure-agent-orchestrator
```

## Threat model

This service is a control plane. It is **not** a SOAR and does not
execute commands. The threat model assumes:

- The service is reachable over HTTPS, terminated by a reverse proxy
  (Render, nginx, Caddy). The app itself does not enforce HTTPS.
- The database is a single SQLite file on the same host. There is no
  network-attacker model for the database.
- The frontend, if any, is served from a different origin and uses
  the explicit CORS allowlist.
- An attacker can read the source code (it is open source) and craft
  arbitrary JWTs, but cannot sign them without the `SECRET_KEY`.

## What is in scope

- Authentication (JWT, bcrypt, blacklist).
- Authorization (RBAC: user vs superuser).
- Input validation (pydantic schemas, config validators).
- Secrets handling (no secrets in logs, no secrets in image layers).
- CORS and cache-control headers.

## What is out of scope

- Network-level attacks (DDoS, TLS downgrade). Use a CDN or WAF.
- Physical access to the host.
- Compromise of the `SECRET_KEY` itself. If the key leaks, all tokens
  signed by it are forgeable. Rotate the key and invalidate all
  outstanding tokens.
- Rate limiting. The service does not implement rate limiting. Put a
  rate limiter in front of it if you expose it publicly.

## Audit history

A full security audit was performed in July 2026. It found and fixed
eight critical issues, including hardcoded JWT secret and admin password
defaults, CORS `*` + credentials, a stub rate limiter shipped as a
feature, a no-op cache decorator shipped as a feature, a fake
`/execute-command` endpoint with a broken background task, and publicly
readable user listings. The audit worklog is available on request.
