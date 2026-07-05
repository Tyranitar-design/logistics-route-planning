## 0. SDD

- [ ] 0.1 Create OpenSpec proposal/design/tasks/spec delta for the multi-page case console.
- [ ] 0.2 Spec delta covers multi-page layout, warmup, Amap map, solver animation, forecast curves, math models, network/layout diagrams.

## 1. Startup Guarantee & Data Warmup

- [ ] 1.1 `scripts/launch_case_console.ps1`: boot Flask :5000 + wait `/api/ready` + `import/apply` + `geocode-regions` + print summary.
- [ ] 1.2 Verify smoke: with backend down, frontend shows launch-command panel (no empty tabs); with backend up, all child pages have data.

## 2. Route & Layout Refactor

- [ ] 2.1 Add nested routes `/cases/food-supply/*` (overview/gis/forecast/dispatch/multimodal/freshness/trace/scenarios/agent).
- [ ] 2.2 `FoodSupplyCaseLayout.vue` parent: inner sub-nav + truth strip + KPI strip + `<router-view>` + health gate.
- [ ] 2.3 Move existing panels into focused child views under `views/case/`; keep the old single page as a redirect to overview.

## 3. Per-Capability Visualization

- [ ] 3.1 `gis`: Amap JS API map (authenticity-colored markers + route polylines) + ECharts network graph; Leaflet fallback.
- [ ] 3.2 `forecast`: 92-day history + forecast curves (deterministic/lightgbm/optuna toggle) + harvest-wave bands.
- [ ] 3.3 `dispatch` + `freshness`: solver animation (route construction tick) + VRPTW/freshness math model (KaTeX) + time-window Gantt.
- [ ] 3.4 `multimodal`: three-mode comparison + air-route diagram + CFLP math model.
- [ ] 3.5 `trace`: chain timeline; `scenarios`: comparison + recommended.

## 4. Truth Visibility

- [ ] 4.1 Truth strip reflects real authenticity (A when cache hit, C only when empty); map markers color accordingly.

## 5. Verification & Memory

- [ ] 5.1 Backend pytest still 42 passed (no API change).
- [ ] 5.2 Frontend build passes; per-page smoke via playwright or manual.
- [ ] 5.3 OpenSpec strict validation.
- [ ] 5.4 Update `.codex/memory/WORKLOG.md` and `.shared-memory` memory.
