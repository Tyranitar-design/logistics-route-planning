## 1. P0 Stabilization

- [x] 1.1 Remove hardcoded browser map keys from Vite config and add safe env examples.
- [x] 1.2 Verify and fix Vue dispatch dynamic import/clickability issues.
- [x] 1.3 Keep `/api/ready` PostgreSQL fact visibility and provider degradation reasons explicit.
- [x] 1.4 Smoke `/api/dispatch/health`, `/api/dispatch/preview`, and `/api/dispatch/smart`.

## 2. P1 Optional Capability Integration

- [x] 2.1 Add safe optional capability service for Gurobi, CPLEX/docplex, OR-Tools, pymoo, Torch/SB3, Optuna, LightGBM, Transformers, and geospatial packages.
- [x] 2.2 Expose `/api/optimization/capabilities` and include statuses in `/api/optimization/solvers`.
- [x] 2.3 Fix DRL-VRP registration so Torch-backed shadow capability is not silently hidden.
- [x] 2.4 Add backend tests for capability probing and shadow boundary metadata.

## 3. P2 Console, Harness, And Memory

- [x] 3.1 Surface optional runtime readiness in the Vue decision console.
- [x] 3.2 Add a focused smoke harness script for readiness/capability/dispatch endpoints.
- [x] 3.3 Run focused backend tests and frontend build.
- [x] 3.4 Update `.codex/memory/MEMORY.md` and `.codex/memory/WORKLOG.md` with implementation evidence.
