## Why

The logistics platform needs a real, bounded case-study module that demonstrates GIS, MIS, optimization, dispatch, and AI/Agent decision support on a fresh-food supply-chain problem. The provided peach case contains orchards, warehouses, B-end stores, C-end demand, airports, vehicles, and drones, but it must remain isolated from production `shipment_facts` and order tables.

## What Changes

- Add an isolated food supply-chain case module backed by dedicated case tables.
- Import and audit the Excel case data, preserving source files, WGS84 coordinates, demand aggregation, and data-quality diagnostics.
- Expose `/api/cases/food-supply/*` APIs for summary, import validation/application, network graph, distance matrix, network design, dispatch, Pareto comparison, scenario records, and Agent explanation.
- Add a Vue case page at `/cases/food-supply` with six command-center views: overview, GIS network, math model, dispatch, scenario comparison, and Agent explanation.
- Extend the enterprise smoke harness and project memory so future agents can verify and resume the case module safely.

## Impact

- Backend: case models, service, routes, app registration, focused tests, smoke harness.
- Frontend: route/menu/API/page for the food supply-chain case.
- Data: new `case_food_*` tables only; no mutation to `shipment_facts`, `orders`, `vehicles`, or raw production facts.
- Security: no API keys, DB passwords, SSH secrets, or solver license values are stored or returned.
