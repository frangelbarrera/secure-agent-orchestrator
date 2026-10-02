**Maintainer:** Frangel Raúl Crespo Barrera
**Last verified:** 2026-10-02
**Scope:** agent registration, JWT authentication, authorization, command execution, secrets, replay, and resource exhaustion.

| Field | Current record |
|---|---|
| Status | Threats documented; controls require deployment-specific verification. |
| Evidence | `src/`, `tests/test_api.py`, `tests/test_security.py`, `pyproject.toml`, `.env.example`, `.github/workflows/ci.yml`. |
| Verification | `pytest -q`; inspect JWT, authorization, command and secret paths before deployment. |
| Owner | Repository owner; deployment operator owns production configuration. |
| Limitations | README, CI, and this model do not make the project production-hardened or compliant. |

The project is early-stage until authentication, authorization, worker isolation, rate limiting, audit logging, and secret management have been reviewed for the actual deployment. Never place production secrets in examples, logs, fixtures, or CI.
