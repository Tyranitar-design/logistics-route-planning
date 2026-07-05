## Why

The logistics command center needs a stable enterprise demo path: Vue dispatch must be usable, map/provider degradation must be explainable, and real PostgreSQL `shipment_facts` smoke evidence must remain visible. The newly installed optimization, machine learning, geospatial, and reinforcement learning libraries should strengthen the platform without making normal Flask/Vue startup depend on every heavy runtime.

## What Changes

- Make the Vue dispatch page reliable and clickable, including `/dispatch/preview` and `/dispatch/smart` smoke coverage.
- Move browser map keys out of hardcoded Vite config and into safe environment configuration; provider health must report configured/degraded status with explicit fallback reasons.
- Add an optional capability probe layer for Gurobi, CPLEX/docplex, OR-Tools, pymoo, Torch/SB3, Optuna, LightGBM, Transformers, and geospatial packages.
- Surface capability status in the decision console and solver APIs without exposing license or key contents.
- Keep DQN/PPO/Fitted-Q as shadow/rerank only; solver validation remains the hard-constraint owner.
- Add a focused smoke harness and memory/worklog updates for future handoff.

## Capabilities

### New Capabilities

- `enterprise-dispatch-readiness`: Vue dispatch, PostgreSQL readiness, and provider truth metadata needed for reliable demos.
- `optional-ai-optimization-capabilities`: Optional optimization/ML/RL/geospatial runtime probing and safe solver integration status.
- `decision-console-harness`: Enterprise decision console status aggregation plus repeatable local smoke harness evidence.

### Modified Capabilities

- None. The repository currently has no archived base specs under `openspec/specs/`.

## Impact

- Backend: `backend/app/routes/optimization.py`, `backend/app/routes/health.py`, optimization engine solver registration, optional capability service, tests, and smoke harness scripts.
- Frontend: Vue dispatch route, Vite env key handling, decision console, and optimization API wrapper.
- Documentation: OpenSpec change artifacts, memory/worklog updates, and safe env examples.
- Security: no secrets, API keys, PostgreSQL passwords, SSH keys, or license contents are read into artifacts or returned by API responses.
