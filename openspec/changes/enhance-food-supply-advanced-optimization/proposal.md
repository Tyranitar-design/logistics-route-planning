## Why

The food supply-chain case now has a stable MVP, but its optimization core is still mostly deterministic baselines. The next step is to prove higher-quality operations research capability on the bounded case: exact MILP for network design, VRP heuristics/metaheuristics for dispatch, real road-matrix provenance, and real Pareto search instead of placeholder points.

## What Changes

- Add an advanced optimization layer for the food supply-chain case that can run bounded Gurobi/CPLEX MILP network design when available, with deterministic fallback when not available.
- Upgrade case dispatch from one-order-per-route greedy assignment to bounded VRP-style planning with OR-Tools and pyVRP execution, particle-swarm style metaheuristic comparison, and capacity/duplicate-assignment validation.
- Upgrade Pareto comparison from fixed deterministic points to pymoo NSGA-backed multi-objective search when available, while preserving a stable fallback.
- Extend distance matrix building with explicit provider modes for PostGIS/Haversine, OSM, Amap, and Tianditu; provider/OSM modes should execute when safely configured and every matrix entry must expose provenance and fallback reason.
- Extend API, tests, smoke harness, and memory so future agents can verify solver quality, route authenticity, and degradation behavior.

## Capabilities

### New Capabilities

- `food-supply-advanced-optimization`: Advanced solver, road-matrix, VRP, metaheuristic, and Pareto behavior for the isolated food supply-chain case.

### Modified Capabilities

- None. The existing MVP capability remains valid; this change adds an advanced layer on top of the `/api/cases/food-supply` bounded context.

## Impact

- Backend: `food_supply_case_service.py`, route payload contracts, optional solver/runtime integration, tests, smoke harness.
- Frontend: food case console should surface solver family, execution mode, route authenticity, constraint validation, and Pareto/solver comparison quality signals.
- Data: may write only `case_food_distance_matrix` and `case_food_scenarios` when explicitly confirmed; no production facts are mutated.
- Dependencies: uses existing optional local libraries (`gurobipy`, `docplex`, `ortools`, `pyvrp`, `pymoo`, `osmnx`, geospatial stack) when present and degrades transparently when unavailable.
- Security: no API keys, DB passwords, SSH secrets, or solver license contents are read, returned, logged, or stored.
