# Threat model and operational limits

The primary risks are unauthorized agent registration, broken authorization, JWT misuse, command execution, secret exposure, replay, and resource exhaustion. Documentation and tests should map each risk to a control and evidence.

The project should be treated as early-stage until deployment-specific authentication, authorization, isolation, rate limiting, audit logging, and secret-management controls have been reviewed. Never place production secrets in examples, logs, fixtures, or CI.
