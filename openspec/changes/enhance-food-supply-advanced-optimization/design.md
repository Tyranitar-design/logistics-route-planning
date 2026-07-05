## Overview

This change keeps the food case bounded and demo-safe while introducing real advanced optimization execution where the local runtime supports it. The public API remains under `/api/cases/food-supply`; advanced solvers are selected by `solver_mode` / `matrix_mode` / `algorithm_family` parameters and always return truth metadata.

## Solver Boundary

- Hard constraints stay in the solver layer: capacity, demand uniqueness, facility capacity/throughput, bounded customer counts, and no production-table mutation.
- Gurobi and CPLEX/docplex are exact MILP candidates for bounded network design. The implementation must cap customers/facilities and return `execution_mode=exact_milp` only when an exact solver actually executes.
- OR-Tools and pyVRP are dispatch candidates. OR-Tools handles bounded CVRP through the routing solver; pyVRP handles bounded CVRP through a small hybrid genetic adapter. If either adapter cannot execute, fallback must be explicit.
- Particle swarm is a metaheuristic comparison family for route ordering/facility assignment. It must report iteration count, best objective, and constraint validation.
- pymoo NSGA is the Pareto search engine for cost/carbon/freshness/service tradeoffs. If pymoo is unavailable or the case is too small, deterministic fallback remains acceptable but must be labeled.

## Road Matrix Boundary

- Matrix modes: `postgis`, `haversine`, `osm`, `amap`, `tianditu`, and `auto`.
- `postgis`/`haversine` are local baselines and must not be labeled as real navigation paths.
- `osm` should use a local GraphML/cache or explicitly enabled OSMnx network fetch. If no graph can be built without network/cache, it returns degraded rows with `OSM_GRAPH_UNAVAILABLE`.
- `amap`/`tianditu` use existing provider services when explicitly requested, with small synchronous node caps. Missing keys, DNS/provider failures, or row failures return degraded metadata and per-row Haversine fallback.
- Persisted matrix writes touch only `case_food_distance_matrix`.

## API Shape

- Existing endpoints are enhanced rather than replaced:
  - `POST /api/cases/food-supply/distance-matrix/build`
  - `GET /api/cases/food-supply/osm-cache/status`
  - `POST /api/cases/food-supply/osm-cache/build`
  - `POST /api/cases/food-supply/routes/preview`
  - `POST /api/cases/food-supply/optimize/network-design`
  - `POST /api/cases/food-supply/optimize/dispatch`
  - `POST /api/cases/food-supply/optimize/pareto`
  - `POST /api/cases/food-supply/optimize/solver-compare`
- Responses include `solver`, `solver_family`, `execution_mode`, `data_source`, `distance_source`, `path_source`, `authenticity_level`, `fallback_reason`, `diagnostics`, and `constraint_validation`.

## Route Geometry Boundary

- Route preview is a bounded visual aid for the food case GIS tab. It returns WGS84 polylines and provenance, but never mutates case facts.
- OSM GraphML caches may be true OSMnx GraphML (`cache_kind=osm_graphml`) or demo-safe case baseline GraphML (`cache_kind=case_baseline_graphml`). Baseline GraphML must be labeled as a local baseline, not true OSM navigation.
- Provider previews use existing Amap/Tianditu services when explicitly requested; provider fallback polylines remain visible but must carry degraded status and fallback reason.
- Frontend geometry preview must keep the source label, authenticity level, distance source, path source, and fallback reason visible without relying on hover.

## Implementation Sequence

1. Add tests for advanced solver contracts and degradation metadata.
2. Add runtime capability helpers inside the food case service, reusing existing optional capability patterns where possible.
3. Implement exact MILP network design with Gurobi first and docplex/CPLEX fallback, bounded by payload limits.
4. Implement OR-Tools bounded CVRP dispatch, pyVRP bounded CVRP dispatch, and PSO comparison fallback.
5. Implement pymoo NSGA Pareto search for bounded decision variables.
6. Add GraphML cache status/build and route preview contracts.
7. Add Vue GIS geometry preview once backend contracts are stable.
8. Extend harness and memory after verification.

## Non-Goals

- No full 20k C-end address-by-address real navigation in this change.
- No automatic business writeback from advanced solvers.
- No direct RL/DQN/PPO control of dispatch.
- No secret management changes and no provider key exposure.
