## Overview

This change stabilizes the current Vue + Flask + PostgreSQL system before adding optional advanced capabilities. The implementation keeps the production path small and predictable: normal pages use lightweight health/status APIs, while heavy AI/RL/optimization tasks stay behind explicit probes, background jobs, or bounded demos.

## Architecture

### P0: Dispatch And Provider Readiness

- Vue dispatch remains the primary UI at `/dispatch`.
- `/api/dispatch/health`, `/api/dispatch/waves`, `/api/dispatch/preview`, and `/api/dispatch/smart` are the smoke target chain.
- Vite map configuration reads `VITE_AMAP_KEY` / `VITE_AMAP_SECURITY_KEY` from environment files instead of hardcoded values.
- Backend provider key resolution reports only boolean/source metadata, never key values.

### P1: Optional Capability Layer

- Add one backend service responsible for safe runtime probing.
- Capability rows include:
  - import availability and version where safe,
  - runtime role (`exact_solver`, `multi_objective`, `rl_shadow`, `forecasting`, `geospatial`),
  - provider status (`ok`, `degraded`, `missing`, `not_configured`),
  - fallback reason and recommended fallback.
- Gurobi remains probed by the existing Gurobi capability service.
- CPLEX/docplex is introduced as a capability and bounded MILP readiness signal first; it must not replace current solver paths unless explicitly requested.
- Torch/SB3 and DQN/PPO stay shadow-only. Their status can inform policy jobs and decision console readiness, but cannot apply dispatch assignments.
- pymoo continues to power multi-objective/NSGA paths through the existing solver engine.

### P2: Decision Console And Harness

- Vue decision console reads the optional capability endpoint and displays enterprise readiness cards.
- A local smoke harness verifies:
  - `/api/ready`,
  - `/api/optimization/capabilities`,
  - `/api/dispatch/health`,
  - `/api/dispatch/preview`,
  - `/api/dispatch/smart`.
- Memory files record stable facts, verification commands, and known caveats.

## Data And Truth Boundaries

- PostgreSQL `shipment_facts` remains the primary real order source.
- `orders` remains compatibility-only unless explicitly requested.
- Provider degradation is allowed only with explicit `fallback_reason`.
- RL policy output is advisory only; hard constraints remain solver-owned.
- License/key/password values are never logged, committed, or returned.

## Failure Modes

- If CPLEX/docplex/Gurobi/OR-Tools/pymoo/Torch/SB3/Optuna/LightGBM/Transformers/geospatial packages are missing, API returns `success:true` with degraded capability rows.
- If map keys are not configured, provider health returns key status and actionable fallback reason.
- If PostgreSQL is not connected, `/api/ready` must make the SQLite/empty fallback visible.

## Verification

- Frontend build passes.
- Focused backend tests pass.
- Capability probe returns safe statuses.
- Real PostgreSQL smoke shows `shipment_facts=50000` when the correct local environment is injected.
- Dispatch preview and smart dispatch return usable JSON under the same authenticated backend session.
