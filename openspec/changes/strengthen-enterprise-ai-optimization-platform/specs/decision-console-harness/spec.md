## Purpose

Give future agents and users a repeatable control-tower view and a smoke harness for the enterprise AI/optimization upgrade.

## Requirements

### Requirement: Decision console surfaces enterprise readiness

The Vue decision console SHALL show optimization/AI runtime readiness alongside existing prediction, anomaly, dispatch, and solver signals.

#### Scenario: Capabilities endpoint responds

- GIVEN `/api/optimization/capabilities` returns capability rows
- WHEN the decision console loads
- THEN it SHALL show available/degraded counts
- AND show fallback reasons for degraded solver/AI capabilities.

### Requirement: Smoke harness is repeatable

The repository SHALL include a focused smoke harness for local or server verification.

#### Scenario: Backend URL is provided

- GIVEN a backend base URL and optional auth token
- WHEN the harness runs
- THEN it SHALL request readiness, capability health, dispatch health, dispatch preview, and dispatch smart endpoints
- AND print a compact JSON summary without secret values.

### Requirement: Memory records key milestones

The project SHALL record durable implementation facts and verification evidence in `.codex/memory`.

#### Scenario: A key phase is completed

- GIVEN code or harness verification has completed
- WHEN the work is handed off
- THEN `MEMORY.md` or `WORKLOG.md` SHALL describe the stable facts and commands without passwords, keys, or license contents.
