## Overview

The module is implemented as a case-study bounded context. It uses deterministic baselines first so the demo remains stable, while keeping solver and AI interfaces explicit enough for Gurobi/CPLEX/OR-Tools/pymoo/DQN shadow upgrades.

## Data Boundary

- Case data comes from `案例一：食品供应链仓配优化(1)` Excel files.
- Tables are prefixed `case_food_` and include nodes, demands, resources, distance matrix, and scenarios.
- C-end consumer demand is aggregated by date and region in v1; exact address geocoding is a later enhancement.
- Coordinates are WGS84 lon/lat plus SRID/WKT metadata. PostgreSQL/PostGIS runtime materializes `case_food_nodes.geom geometry(Point,4326)` and `ix_case_food_nodes_geom`; SQLite/testing runtimes report a transparent skipped/degraded status.

## API Boundary

- Public prefix: `/api/cases/food-supply`.
- Write APIs default to preview/dry-run. Persisted writes only touch `case_food_*` scenario/import tables.
- All route/optimization responses include `data_source`, `distance_source`, `path_source`, `authenticity_level`, `fallback_reason`, and `solver`.

## Optimization Strategy

- V1 network design uses a greedy CFLP-style baseline over real case nodes and demand.
- V1 dispatch uses a capacity-safe greedy wave over B-end demand and case vehicle resources.
- V1 Pareto uses deterministic comparison points for cost, carbon, freshness risk, and service level.
- Exact MILP/VRP and pymoo/AI/RL enhancements plug into the same endpoint contracts in later phases.

## UX Strategy

- The Vue page is an operational console, not a landing page.
- It shows KPI cards, truth metadata, GIS/network graph, mathematical model text, dispatch table, Pareto chart, and Agent advice.
- Empty/degraded states explain missing import, provider fallback, solver readiness, and Agent key status.
