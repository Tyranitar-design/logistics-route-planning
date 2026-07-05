## Overview

Seven bounded sub-systems layered on the existing case service. Each preserves the truth contract (`data_source`, `distance_source`, `path_source`, `authenticity_level`, `fallback_reason`, `solver`) and degrades transparently when providers/solvers are unavailable.

## Orchard Time-Series + Forecast

- `_load_orchards` is enriched to read columns 9..100 (92 daily boxes per orchard, headers verified against the 6/1–8/31 date row).
- Forecast is deterministic and explainable: per-orchard moving average, linear trend, and a 7-day week-seasonality index. It does NOT claim to be a trained ML model; `model_stage="deterministic_baseline"` and an optional hook delegates to `shipment_prediction_service` when available.
- Harvest-wave planner groups forecast volume into waves that respect the 3-5 day freshness window (peach at 8 成熟, 30℃), reporting wave date, estimated boxes, and a readiness gate.

## Multimodal Air Transport

- Freight airports (27 entries, `needs_geocoding`) are resolved via the existing geocoding pipeline (Amap/Tianditu → local city-centroid fallback) and cached in `case_food_geocoding_cache`.
- A multimodal plan links orchard → vehicle → origin airport (硕放/奔牛, both near orchards) → aircraft (B747-8F, 135t, 426 km/h, 1.17 元/kg) → destination freight airport → vehicle/drone → consumer cluster.
- Modes compared: `pure_road`, `air_plus_road`, `air_plus_drone`. Each mode reports cost, duration, carbon, freshness risk, and feasibility with explicit fallback reasons. Air is feasible only when the destination is far enough that the airport handling overhead is amortized.

## Freshness Decay + VRPTW

- Freshness model: `freshness_score = 1 - decay`, where `decay = k_temp × max(0, temp_c - 4) × hours + k_shock × transfers` (cold-chain k_temp ≈ 0, ambient 30℃ uses the case-stated 3-5 day shelf life to calibrate k). Outputs a 0-1 score and a `freshness_risk`.
- VRPTW: dispatch gains optional `time_window_hours` (default 48) and `freshness_window_days` (default 4). Orders that cannot be served within the hard window are reported as `unassigned` with reason, never silently dropped.
- Solver ladder: greedy VRPTW baseline → OR-Tools VRPTW when available → exact MILP readiness-only. Hard constraints always owned by the solver layer.

## Map Visualization

- A Leaflet map is added to the GIS network tab, rendering orchards, facilities, B-stores, origin/freight airports, and C-end cluster centroids.
- Markers are colored by `authenticity_level` (A green / B amber / C grey). Route preview polylines overlay on the map and link to the existing route-compare table.

## Real Road Distance For Last-Mile

- Last-mile cluster distance is upgraded from Haversine to Amap/Tianditu driving distance, reusing the existing distance-matrix adapters with sync node caps.
- Per-pair provenance (`distance_source`, `path_source`, `authenticity_level`, `fallback_reason`) is preserved; Haversine remains the explicit fallback.

## Traceability

- A trace code is generated deterministically per cluster/wave (e.g. `FSC-TRACE-{orchard}-{wave}-{cluster}-{checksum}`) and mapped to a chain of stages: harvest → pack → transport → sign, each with timestamp, location, and handler placeholder.
- `GET /api/cases/food-supply/trace/{code}` returns the chain; persisted only to `case_food_scenarios`-style case tables when explicitly confirmed.

## Scenario Comparison

- Existing `case_food_scenarios` rows are listed and compared on cost/carbon/time/freshness/service-level; the recommended scenario is chosen among feasible ones with a stated reason.
- Default `persist:false`; the comparison never mutates production facts.

## API Boundary

- New endpoints under `/api/cases/food-supply`:
  - `GET /orchards/timeseries`, `GET /orchards/forecast`
  - `POST /optimize/multimodal`
  - `POST /optimize/dispatch-fresh` (VRPTW)
  - `POST /optimize/last-mile` upgraded with real road distance
  - `GET /trace/{code}`, `POST /trace/issue`
  - `GET /scenarios`, `POST /scenarios/compare`
- Every response keeps the truth contract; write endpoints default to `persist:false`.
