## Purpose

Add season-aware orchard forecasting, air multimodal transport, freshness-safe VRPTW, map visualization, real road distance, traceability, and scenario comparison to the peach supply-chain case, directly addressing the case statement’s 6–8 month season, “陆运、空运”, “8 成熟 30℃ 3-5 天”, and “时效 48 小时” requirements.

## ADDED Requirements

### Requirement: Orchard season forecast is explainable and bounded

The system SHALL read the 92-day daily orchard volume and produce a deterministic forecast with explicit model stage and freshness-aware harvest waves.

#### Scenario: Forecast is requested

- GIVEN the orchard workbook is present
- WHEN `/api/cases/food-supply/orchards/forecast` is called
- THEN the response SHALL include per-orchard daily series summary, forecast points, `model_stage`, and harvest waves
- AND each wave SHALL respect the configured freshness window
- AND the response SHALL include the truth contract with `raw_fact_mutation:false`.

### Requirement: Multimodal air transport is feasibility-aware

The system SHALL compare pure-road, air+road, and air+drone multimodal plans and SHALL mark air modes infeasible when distance or payload thresholds are not met.

#### Scenario: Multimodal plan is requested

- GIVEN orchard, aircraft, origin and freight airports, and consumer clusters are available
- WHEN `/api/cases/food-supply/optimize/multimodal` is called with `persist:false`
- THEN the response SHALL include `pure_road`, `air_plus_road`, and `air_plus_drone` mode rows
- AND each row SHALL include cost, duration, carbon, freshness risk, feasibility, and fallback reason
- AND `constraint_validation` SHALL report payload, range, and airport-handling violations.

### Requirement: Freshness-safe VRPTW enforces the time window

The system SHALL evaluate dispatch under a freshness-decay model and a hard time window, and SHALL report orders that cannot be served within the window as unassigned.

#### Scenario: Freshness dispatch is requested

- GIVEN a bounded B-end demand wave and a configured time window
- WHEN `/api/cases/food-supply/optimize/dispatch-fresh` is called
- THEN the response SHALL include freshness scores per plan and `constraint_validation.time_window_violations`
- AND orders outside the window SHALL be listed as unassigned with an explicit reason
- AND no production orders or vehicles SHALL be mutated.

### Requirement: Last-mile distance provenance is real-road when available

The system SHALL upgrade last-mile cluster distance from Haversine to real Amap/Tianditu driving distance when available, with per-pair provenance and transparent fallback.

#### Scenario: Real-road distance is requested

- GIVEN last-mile is called with `distance_mode=amap`
- WHEN Amap driving distance succeeds
- THEN the response SHALL report `distance_source=amap_driving` and `authenticity_level=A` for resolved pairs
- AND failed pairs SHALL fall back to Haversine with an explicit `fallback_reason`.

### Requirement: Traceability chain is deterministic and lookupable

The system SHALL issue a deterministic trace code per wave/cluster and expose the harvest-pack-transport-sign chain via lookup.

#### Scenario: Trace code is looked up

- GIVEN a trace code has been issued
- WHEN `/api/cases/food-supply/trace/{code}` is called
- THEN the response SHALL return the chain stages with timestamps and locations
- AND the response SHALL include the truth contract.

### Requirement: Scenario comparison recommends only feasible scenarios

The system SHALL list and compare persisted case scenarios on cost, carbon, time, freshness, and service level, and SHALL recommend only among feasible scenarios.

#### Scenario: Scenarios are compared

- GIVEN multiple persisted case scenarios exist
- WHEN `/api/cases/food-supply/scenarios/compare` is called
- THEN the response SHALL include a comparison table and a `recommended_scenario`
- AND the recommended scenario SHALL be feasible with a stated `recommendation_reason`.
