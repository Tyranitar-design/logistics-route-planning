## 1. SDD / Contract Tests

- [x] 1.1 Create OpenSpec proposal/design/tasks/spec delta for advanced food-supply optimization.
- [x] 1.2 Add backend tests for exact MILP network-design contract and fallback metadata.
- [x] 1.3 Add backend tests for OR-Tools VRP dispatch contract, PSO comparison, and pyVRP readiness.
- [x] 1.4 Add backend tests for pymoo NSGA Pareto contract and deterministic fallback.
- [x] 1.5 Add backend tests for distance matrix provider modes and provenance metadata.

## 2. Backend Advanced Solvers

- [x] 2.1 Add runtime solver capability summary for food-case advanced optimization.
- [x] 2.2 Implement bounded Gurobi/CPLEX MILP network design with clear fallback.
- [x] 2.3 Implement bounded OR-Tools CVRP dispatch and constraint validation.
- [x] 2.4 Implement PSO-style metaheuristic route/facility comparison.
- [x] 2.5 Implement pymoo NSGA multi-objective Pareto search.
- [x] 2.6 Extend solver comparison rows to distinguish executed solvers from readiness-only rows.

## 3. Road Matrix And Provider Authenticity

- [x] 3.1 Add `matrix_mode` handling for postgis/haversine/osm/amap/tianditu/auto.
- [x] 3.2 Persist matrix rows only to `case_food_distance_matrix` when confirmed.
- [x] 3.3 Return per-row `distance_source`, `path_source`, `authenticity_level`, and `fallback_reason`.

## 4. Frontend And Harness

- [x] 4.1 Surface advanced solver mode, execution mode, and degradation reason in `/cases/food-supply`.
- [x] 4.2 Extend `enterprise_smoke_harness.py` with advanced matrix, MILP, VRP, and Pareto checks.
- [x] 4.3 Update `.codex/memory/WORKLOG.md` after verified milestones.

## 5. Verification

- [x] 5.1 Run OpenSpec strict validation.
- [x] 5.2 Run focused backend tests.
- [x] 5.3 Run frontend build after UI updates.
- [x] 5.4 Run local HTTP harness.

## 6. Phase 2 Real Road Matrix And pyVRP

- [x] 6.1 Add contract tests for mocked Amap/Tianditu distance matrix success and explicit provider failure fallback.
- [x] 6.2 Add contract tests for OSMnx graph-backed matrix rows with `osm_network` provenance.
- [x] 6.3 Add contract tests for executable `solver_mode=pyvrp` dispatch and advanced solver comparison row.
- [x] 6.4 Implement bounded provider matrix adapters with per-pair provenance and sync-call node caps.
- [x] 6.5 Implement OSM graph/cache adapter with no-network default and explicit graph-cache fallback.
- [x] 6.6 Implement bounded pyVRP CVRP adapter with hard-constraint validation.
- [x] 6.7 Re-run OpenSpec validation, focused tests, frontend build if UI changes, and HTTP harness.

## 7. Phase 3 GraphML Cache And Route Geometry Preview

- [x] 7.1 Add contract tests for OSM GraphML cache status/build responses without requiring network or secrets.
- [x] 7.2 Add contract tests for `/routes/preview` returning provider/OSM/local polyline geometry and provenance.
- [x] 7.3 Implement GraphML cache helpers with explicit `osm_graphml` vs `case_baseline_graphml` authenticity metadata.
- [x] 7.4 Implement bounded route preview API for `osm`, `amap`, `tianditu`, `haversine`, and `auto`.
- [x] 7.5 Add Vue API wrappers and a food-case GIS route preview panel with geometry, source labels, and degradation display.
- [x] 7.6 Extend harness with GraphML cache status and route preview checks.
- [x] 7.7 Re-run OpenSpec validation, focused backend tests, frontend build, and route-preview smoke/browser checks.

## 8. Phase 4 Route Provider Comparison

- [x] 8.1 Add contract tests for `/routes/compare` returning bounded multi-provider route rows and recommendation metadata.
- [x] 8.2 Implement route comparison service for `amap`, `tianditu`, `osm`, and local baseline with explicit provenance.
- [x] 8.3 Add Vue API wrapper and GIS comparison table with selectable route overlay.
- [x] 8.4 Extend harness with route comparison checks.
- [x] 8.5 Re-run OpenSpec validation, focused backend tests, frontend build, and smoke checks.

## 9. Phase 5 Route Comparison Explainability

- [x] 9.1 Add route comparison summary metrics for geometry count, best distance, and recommendation reason.
- [x] 9.2 Add contract coverage for the new summary metrics.
- [x] 9.3 Add Vue metric strip and recommendation rationale in the GIS route comparison panel.
- [x] 9.4 Re-run focused backend tests, frontend build, and smoke checks.

## 10. Phase 6 Route Quality Scoring

- [x] 10.1 Add route-level quality score and score breakdown for provider status, authenticity, geometry, fallback, and relative distance.
- [x] 10.2 Add route comparison summary metrics for recommended score, best quality score, and average quality score.
- [x] 10.3 Add Vue score cards and table score column for provider comparison.
- [x] 10.4 Re-run focused backend tests, frontend build, and smoke checks.

## 11. Phase 7 Route Compare History And PostgreSQL Smoke

- [x] 11.1 Add `case_food_route_comparisons` model for route comparison cache/history isolated from production facts.
- [x] 11.2 Add `persist/use_cache/cache_ttl_hours` support to `/routes/compare` with cache hit metadata.
- [x] 11.3 Add `/routes/compare/history` API and backend contract tests.
- [x] 11.4 Add Vue route comparison history panel and cache status display.
- [x] 11.5 Extend enterprise smoke harness with route history check.
- [x] 11.6 Re-run focused backend tests, frontend build, OpenSpec validation, and real PostgreSQL 50k production smoke.
