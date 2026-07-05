## Why

The food supply-chain case now has C-end geography and drone last-mile, but three case-critical capabilities are still missing or under-built:

1. **Forecast**: The orchard workbook carries 92 days of daily shipment volume per orchard (6/1–8/31, ~3.26M boxes total) that the importer currently throws away. The case statement centers on a 6–8 month peach season, so a season-aware forecast and harvest-wave plan are the highest-value unused asset.
2. **Multimodal air**: The case explicitly requires “陆运、空运”. Aircraft (B747-8F, 135t payload, 426 km/h) and 27 freight airports are imported but never enter any solver; only vehicle + drone are optimized today.
3. **Freshness + time windows**: The case requires “8 成熟、30℃ 保存 3-5 天、时效 48 小时”. Freshness is a linear `distance/800` approximation and dispatch has no time-window hard constraint, so the case cannot demonstrate freshness-safe VRPTW.

The mid-value items (map visualization, real road distance, traceability, scenario comparison) compound the value of the three core capabilities.

## What Changes

- Add a 92-day orchard time-series layer with a deterministic forecast (moving average + trend + week-seasonality) and a harvest-wave planner that respects the 3-5 day freshness window.
- Add an air-transport multimodal planner: orchard → vehicle → origin airport → aircraft → freight airport → vehicle/drone → consumer, comparing pure-road, air+road, and air+drone modes with explicit cost/time/carbon/freshness objectives.
- Add a freshness-decay model (time × temperature × shock) and upgrade dispatch to VRPTW with a 48h hard time window, replacing the linear approximation.
- Add Leaflet map visualization of orchards, facilities, stores, airports, freight airports, and cluster centroids with authenticity-colored markers and route overlay.
- Upgrade last-mile cluster distance from Haversine to real Amap/Tianditu road distance with per-pair provenance.
- Add an end-to-end traceability chain (harvest → pack → transport → sign) with a deterministic trace code and lookup API.
- Add scenario persistence and horizontal comparison (cost/carbon/time/freshness) with a recommended scenario.

## Capabilities

### New Capabilities

- `food-supply-orchard-forecast-multimodal-freshness`: Season-aware orchard forecast, air multimodal transport, freshness-safe VRPTW, map visualization, real road distance, traceability, and scenario comparison for the isolated food supply-chain case.

### Modified Capabilities

- None. Existing capabilities remain valid; this change adds new bounded endpoints on top of `/api/cases/food-supply`.

## Impact

- Backend: `food_supply_case_service.py`, `food_supply_case.py` models/routes, focused tests, smoke harness.
- Frontend: `FoodSupplyChainCaseView.vue`, `api/foodSupplyCase.js` — forecast panel, multimodal panel, freshness dispatch panel, Leaflet map, traceability panel, scenario comparison panel.
- Data: may write only `case_food_*` tables (scenarios, geocoding cache, traceability). No mutation to `shipment_facts`, `orders`, `vehicles`, or raw production facts.
- Dependencies: reuses existing providers (Amap/Tianditu geocode + distance matrix), optional OR-Tools VRPTW, and existing Leaflet/ECharts frontend stack; degrades transparently when unavailable.
- Security: no API keys, DB passwords, SSH secrets, solver license values, or provider tokens are read, returned, logged, or stored.
