## Why

The food supply-chain case already imports the peach Excel workbooks and solves a bounded network/dispatch MVP, but two case assets are still under-used:

1. The C-end consumer workbook has 22,259 real recipient addresses with no coordinates. Today `_load_c2c_demands` only aggregates them by `(date, region)`, so the case cannot show last-mile geography, real C-end coverage, or consumer-level dispatch — exactly the part of the case that mentions freshness, traceability, and the low-altitude economy.
2. The drone workbook (`载重 10kg / 续航 20km / 速度 14m·s / 400 元·次`) is loaded into `resources.drones` but never appears in any solver. The case statement explicitly asks for drone + vehicle multi-resource delivery under cost and carbon objectives.

This change adds a bounded, provenance-safe C-end geocoding layer and a drone last-mile optimization layer on top of the existing `/api/cases/food-supply` bounded context, plus performance hardening so 22k rows cannot destabilize the demo.

## What Changes

- Add a bounded C-end geocoding pipeline that turns recipient addresses into WGS84 coordinates with explicit provider provenance (Amap / Tianditu / local region-centroid fallback) and a dedicated `case_food_geocoding_cache` table.
- Aggregate C-end demand to bounded region centroids so 22,259 rows become a small, stable set of consumer clusters without losing the address dimension or faking coordinates.
- Add a drone last-mile optimization endpoint that compares drone vs vehicle vs hybrid last-mile delivery under payload, range, freshness, cost, and carbon objectives, reusing the case drone and vehicle resources.
- Harden performance: cache Excel parsing at the process level, cap geocoding batch size, cache provider geocoding results by address hash, and never recompute the full 22k aggregation per request.
- Extend the API, focused tests, enterprise smoke harness, Vue case console, and project memory so future agents can verify C-end geography, drone feasibility, and degradation behavior without network or secrets.

## Capabilities

### New Capabilities

- `food-supply-c2c-geocoding-and-drone-lastmile`: Bounded C-end address geocoding, region clustering, drone last-mile optimization, and performance hardening for the isolated food supply-chain case.

### Modified Capabilities

- None. The existing `food-supply-chain-case` and `food-supply-advanced-optimization` capabilities remain valid; this change adds a new bounded context on top of `/api/cases/food-supply`.

## Impact

- Backend: `food_supply_case_service.py`, `food_supply_case.py` models, `food_supply_case.py` routes, focused tests, smoke harness.
- Frontend: `FoodSupplyChainCaseView.vue`, `api/foodSupplyCase.js` — new C-end geography panel and drone last-mile comparison panel.
- Data: new `case_food_geocoding_cache` table only; C-end rows may be persisted to `case_food_demands` with enriched coordinates when explicitly confirmed. No mutation to `shipment_facts`, `orders`, `vehicles`, or raw production facts.
- Dependencies: reuses existing optional providers (`amap_service.geocode`, `tianditu_service.geocode`) and existing local Haversine baseline; degrades transparently when providers or network are unavailable.
- Security: no API keys, DB passwords, SSH secrets, solver license values, or provider tokens are read, returned, logged, or stored. Provider responses are cached as coordinates and provenance only.
