## Purpose

Provide a real fresh-food supply-chain optimization case inside the logistics command center, with isolated data, GIS visibility, dispatch optimization, scenario comparison, and Agent explanation.

## ADDED Requirements

### Requirement: Case data is isolated and auditable

The system SHALL import the peach supply-chain Excel case into dedicated `case_food_*` tables without mutating production shipment/order/vehicle facts.

#### Scenario: Import is validated

- GIVEN the case Excel folder is present
- WHEN `/api/cases/food-supply/import/validate` is called
- THEN the response SHALL report orchard, facility, B-store, B2B demand, C2C demand, vehicle, and drone counts
- AND include source/diagnostic metadata
- AND, when import is applied, report PostGIS geometry materialization status without failing non-PostgreSQL test runtimes.

### Requirement: GIS network is explainable

The system SHALL expose a case network graph with nodes, edges, distance/path source, authenticity level, and fallback reason.

#### Scenario: Network is requested

- GIVEN case data is imported or readable from Excel
- WHEN `/api/cases/food-supply/network` is called
- THEN the response SHALL include orchards, facilities, stores, airports, and baseline edges
- AND SHALL NOT describe Haversine/local baseline paths as real provider navigation.

### Requirement: Dispatch is capacity-safe

The system SHALL produce a bounded dispatch preview over B-end demand and case vehicle resources.

#### Scenario: Dispatch wave is previewed

- GIVEN a small B-end demand wave
- WHEN `/api/cases/food-supply/optimize/dispatch` is called with `persist:false`
- THEN the response SHALL include assigned and unassigned orders
- AND `capacity_violations` SHALL be zero for assigned plans
- AND no production orders or vehicles SHALL be mutated.

### Requirement: Solver comparison is explicit

The system SHALL compare case-ready baseline algorithms with optional advanced solver readiness without implying unavailable solvers have executed.

#### Scenario: Solver comparison is requested

- GIVEN a bounded case demand wave
- WHEN `/api/cases/food-supply/optimize/solver-compare` is called
- THEN the response SHALL include dispatch, network-design, Pareto, and optional Gurobi/CPLEX/OR-Tools/pymoo/RL shadow rows
- AND each row SHALL include provider status, deployability, metrics, and fallback/boundary metadata
- AND RL rows SHALL remain shadow-only.

### Requirement: Vue case console renders the full MVP

The frontend SHALL provide `/cases/food-supply` as an authenticated command-center page.

#### Scenario: User opens the case page

- GIVEN the Vue app is running and the user is logged in
- WHEN the user opens `/cases/food-supply`
- THEN the page SHALL show overview, GIS network, math model, dispatch, scenario comparison, and Agent explanation views.
