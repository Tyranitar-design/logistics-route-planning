## 0. SDD

- [x] 0.1 Create OpenSpec proposal/design/tasks/spec delta.
- [x] 0.2 Spec delta covers forecast, multimodal, freshness VRPTW, map, road distance, traceability, scenario compare.

## 1. Phase 1 — Orchard Time-Series + Forecast

- [x] 1.1 RED: tests for 92-day series read, deterministic forecast, harvest-wave planner, truth contract.
- [x] 1.2 GREEN: `_load_orchards` reads daily series; `orchard_timeseries` + `orchard_forecast` methods.
- [x] 1.3 Routes `/orchards/timeseries`, `/orchards/forecast`; harness checks.

## 2. Phase 2 — Multimodal Air Transport

- [x] 2.1 RED: tests for freight-airport geocoding and multimodal mode comparison (pure_road / air_plus_road / air_plus_drone).
- [x] 2.2 GREEN: freight-airport geocode in load pipeline; `optimize_multimodal` method.
- [x] 2.3 Route `/optimize/multimodal`; harness check.

## 3. Phase 3 — Freshness Decay + VRPTW

- [x] 3.1 RED: tests for freshness model (time×temp×shock) and VRPTW 48h window unassigned reporting.
- [x] 3.2 GREEN: freshness model helper; `optimize_dispatch_fresh` with time-window hard constraint.
- [x] 3.3 Route `/optimize/dispatch-fresh`; harness check.

## 4. Phase 4 — Frontend Integration

- [x] 4.1 前端「季节 & 多式联运」tab 集成：时序预测 / 多式联运 / 鲜度 VRPTW / 追溯 / 场景对比 5 面板（ECharts 拓扑保留）。
- [ ] 4.2 Leaflet 地图可视化（后续增强：当前用 ECharts 拓扑，Leaflet 节点地图待补，不影响契约与数据）。

## 5. Phase 5 — Real Road Distance For Last-Mile

- [x] 5.1 RED: test that last-mile accepts `distance_mode=amap|tianditu|haversine` and reports per-pair provenance.
- [x] 5.2 GREEN: upgrade `optimize_last_mile` to reuse distance-matrix adapters.

## 6. Phase 6 — Traceability

- [x] 6.1 RED: test trace code generation and `GET /trace/{code}` chain lookup.
- [x] 6.2 GREEN: trace code helper, `trace_issue`, `trace_lookup`; route + harness.

## 7. Phase 7 — Scenario Comparison

- [x] 7.1 RED: test scenario list + compare + recommended scenario among feasible.
- [x] 7.2 GREEN: `list_scenarios`, `compare_scenarios`; route + harness.

## 8. Verification And Memory

- [x] 8.1 Run focused backend tests after each phase.
- [x] 8.2 Run frontend build after UI phases.
- [x] 8.3 Run OpenSpec strict validation.
- [x] 8.4 Update `.codex/memory/WORKLOG.md` and `.shared-memory` memory.
