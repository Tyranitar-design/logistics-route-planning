## Why

The food supply-chain case now has 11/11 backend capabilities and 42 passing tests, but the operator console has three pain points that block real demonstration:

1. **Crowded single-page UI**: every capability (overview / GIS / C-end / drone / forecast / multimodal / freshness / trace / scenario / agent) is a tab inside one giant `FoodSupplyChainCaseView.vue` (~1500 lines). Tabs overflow, panels render partially, and the page does not feel like the existing big-data platform's multi-page experience.
2. **"No data" at runtime**: backend API smoke proves every endpoint returns data, but operators see empty panels because the Flask backend on :5000 is not running (or the dev proxy points elsewhere). There is no startup guarantee, no health gate, and no auto-import/auto-geocode on first screen.
3. **Visualization gaps**: the case statement asks for algorithm solving animation, forecast curves, a real map, full math models, and a logistics network/layout diagram. Today the console only has tables + a small ECharts topology + a Leaflet tab; there is no solver animation, no forecast curve chart, no LaTeX math model, no network-design diagram.

## What Changes

- Refactor the case module from one giant Vue page into a **multi-page console** under `/cases/food-supply/*` with a shared layout and one focused child route per capability (overview, gis, forecast, dispatch, multimodal, freshness, trace, scenarios, agent), mirroring the big-data platform pattern.
- Add a **startup guarantee + data warmup**: a single dev/prod launch script boots Flask on :5000, runs `apply_import` + `geocode_case_regions` once, and the frontend health-gates on `/api/ready` before rendering child routes; every child page auto-loads its own data on mount.
- Upgrade **map visualization to Amap JS API** (real Chinese road map + satellite + traffic) while keeping Leaflet as fallback, with markers for orchards / facilities / stores / airports / C-end clusters and route polylines.
- Add **rich per-capability visualization**: OR-Tools/Gurobi solver animation (step-by-step route construction), forecast curve chart (deterministic vs lightgbm vs optuna), full math model (VRPTW/CFLP via KaTeX), logistics network-design graph (ECharts graph), and warehouse-layout diagram.
- Make authenticity visibly upgrade: when geocoding cache has A-level rows, the truth strip shows A and the map markers turn green; the current default C-level strip is only shown when cache is genuinely empty.

## Capabilities

### New Capabilities

- `food-supply-case-console-multi-page`: Multi-page case console with shared layout, per-capability child routes, startup guarantee, and rich visualization (solver animation, forecast curves, Amap map, math models, network/layout diagrams).

### Modified Capabilities

- None. Backend endpoints stay unchanged; this change is a frontend architecture + visualization layer plus an operational launch script.

## Impact

- Frontend: new `FoodSupplyCaseLayout.vue` parent + ~9 child views under `views/case/`; router nested routes; `api/foodSupplyCase.js` unchanged; new composables for solver animation and warmup.
- Backend: no API contract changes; new `scripts/launch_case_console.ps1` / `.py` to boot Flask + warm data; `geocode_case_regions` already in place.
- Data: reuses existing `case_food_*` tables and `case_food_geocoding_cache`; no production facts touched.
- Dependencies: reuses installed `leaflet@1.9.4`, `echarts`, adds Amap JS API via dynamic script (no npm), optional `katex` for math rendering (install on demand).
- Security: Amap browser key loaded from `VITE_AMAP_KEY`; no server keys or secrets in frontend.
