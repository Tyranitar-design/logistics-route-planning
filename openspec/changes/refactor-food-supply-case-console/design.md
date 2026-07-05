## Overview

Split the case console into a shared layout + 9 focused child pages, add a startup/warmup guarantee so panels never render empty, and replace the current tables-only UI with rich, per-capability visualization. Backend contracts are unchanged; this is a frontend + ops change.

## Route & Layout Architecture

- Parent route `/cases/food-supply` renders `FoodSupplyCaseLayout.vue` (sidebar sub-nav + truth strip + KPI strip + `<router-view>`).
- Child routes (nested):
  - `` (overview) — case KPIs, data audit, truth strip, geocoding readiness
  - `gis` — Amap map (orchards/facilities/stores/airports/clusters + route polylines) + network topology
  - `forecast` — 92-day time-series chart + deterministic/lightgbm/optuna forecast curves + harvest waves
  - `dispatch` — solver animation (OR-Tools/pyVRP route construction) + dispatch table + VRPTW math model
  - `multimodal` — pure_road / air+road / air+drone comparison + air-route diagram
  - `freshness` — freshness-decay curve (temp × time) + VRPTW dispatch + time-window Gantt
  - `trace` — trace-code issue + chain timeline (harvest→pack→transport→sign)
  - `scenarios` — scenario list + horizontal comparison + recommended scenario
  - `agent` — Agent explain drawer (MiniMax-M3)
- Sidebar lives in `Layout.vue` (existing main shell) and links to `/cases/food-supply`; the case layout has its own inner sub-nav.

## Data Warmup & Startup Guarantee

- `scripts/launch_case_console.ps1`: starts Flask on :5000 with `.env.local`, waits for `/api/ready`, then calls `POST /api/cases/food-supply/import/apply {persist:true}` and `POST /api/cases/food-supply/c2c/geocode-regions {persist:true}` once, printing a readiness summary. This guarantees the dev/prod backend has imported case data + A-level geocoding cache before the frontend loads.
- `FoodSupplyCaseLayout.vue` `onMounted`: calls `/api/ready`; if backend unreachable, renders a friendly "后端未启动" panel with the launch command instead of empty tabs.
- Each child view `onMounted` loads its own data (no dependency on the old single-page `loadAll` firehose).

## Visualization Plan

- **Amap map** (`gis`): dynamic-load Amap JS API with `VITE_AMAP_KEY`; markers colored by `authenticity_level` (A green / B amber / C grey); route polylines from `/routes/preview` and `/optimize/last-mile`; switch base layers (road / satellite / traffic). Leaflet remains a fallback if Amap key missing.
- **Solver animation** (`dispatch`, `freshness`): OR-Tools/pyVRP route construction animated step-by-step on the topology/map (one vehicle route drawn per ~400ms tick) using the existing solver response `plans[].stops`.
- **Forecast curves** (`forecast`): ECharts line chart of the 92-day history + 14-day forecast overlay; toggle between `deterministic` / `lightgbm` / `optuna` series; harvest-wave bands shaded.
- **Math models** (`dispatch`, `multimodal`): KaTeX render of VRPTW (min total time s.t. capacity + time-window + flow conservation) and CFLP (facility open + assignment) formulations, side-by-side with the solver result.
- **Network-design diagram** (`gis`, `multimodal`): ECharts `graph` of orchard → facility → airport → cluster with edge width = flow volume, node color = authenticity.
- **Warehouse-layout diagram** (`gis`): ECharts scatter of facility nodes with throughput/area radius, candidate vs selected (from `optimize/network-design`).

## Truth & Authenticity Visibility

- Truth strip in the layout reads the most recent response's `authenticity_level`, `distance_source`, `path_source`, `fallback_reason`.
- When `case_food_geocoding_cache` has A-level rows for the visible clusters, the strip shows A and map markers turn green; the C-level strip only appears when the cache is genuinely empty (not by default).

## UX Strategy

- Operators get a focused, big-data-platform-style experience: one capability per page, each with its own hero KPIs + main visualization + supporting table.
- Every page degrades gracefully: if Amap/solver/KaTeX unavailable, show the table + explicit fallback label; if backend down, show the launch-command panel.
