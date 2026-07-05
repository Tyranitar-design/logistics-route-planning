## Purpose

Provide bounded, provenance-safe C-end consumer geography and drone last-mile optimization for the peach supply-chain case, so the case can demonstrate last-mile coverage, real recipient clusters, and multi-resource (drone + vehicle) delivery under cost, carbon, freshness, and service-level objectives without mutating production facts or faking coordinates.

## ADDED Requirements

### Requirement: C-end addresses are geocoded with explicit provenance

The system SHALL resolve C-end recipient addresses into WGS84 coordinates using Amap or Tianditu geocoding when available, with a deterministic local region-centroid fallback, and SHALL never invent coordinates for unmatched addresses.

#### Scenario: Geocoding is requested with a bounded batch

- GIVEN the C-end workbook is present and a bounded geocode limit is supplied
- WHEN `/api/cases/food-supply/c2c/geocode` is called with `persist:false`
- THEN the response SHALL report `resolved`, `cached`, `needs_geocoding`, and `requested` counts
- AND each resolved row SHALL include `longitude`, `latitude`, `distance_source`, `path_source`, `authenticity_level`, and `fallback_reason`
- AND rows without a real provider match SHALL be marked `needs_geocoding:true` with `authenticity_level:C` rather than assigned an invented coordinate.

#### Scenario: Provider result is cached

- GIVEN a previous geocode call persisted a provider result for an address hash
- WHEN `/api/cases/food-supply/c2c/geocode` is called again with `use_cache:true`
- THEN the response SHALL report `cache_status:hit`
- AND SHALL NOT require a new provider call for that address
- AND SHALL preserve the original `distance_source`, `path_source`, and `authenticity_level`.

### Requirement: C-end demand is clustered to bounded region centroids

The system SHALL aggregate C-end rows into bounded consumer clusters by `(date, region)` so the 22k-row workbook becomes a stable, interactive geography layer without losing the address dimension.

#### Scenario: Clusters are requested

- GIVEN the C-end workbook is present
- WHEN `/api/cases/food-supply/c2c/clusters` is called
- THEN the response SHALL include a bounded list of clusters with `orders`, `weight_kg`, `boxes`, centroid coordinates, and `cluster_authenticity_level`
- AND SHALL include `data_source`, `distance_source`, `path_source`, `authenticity_level`, and `fallback_reason`
- AND SHALL NOT describe local region-centroid fallbacks as real provider geocoding.

### Requirement: Drone last-mile optimization is payload and range safe

The system SHALL evaluate drone delivery for the facility/B-store to consumer-centroid leg under drone payload and range constraints and SHALL report infeasible clusters explicitly.

#### Scenario: Last-mile optimization is requested

- GIVEN case drone and vehicle resources and bounded C-end clusters
- WHEN `/api/cases/food-supply/optimize/last-mile` is called with `persist:false`
- THEN the response SHALL include drone, vehicle, and hybrid mode results per cluster
- AND `constraint_validation` SHALL report `payload_violations`, `range_violations`, and `unassigned_clusters`
- AND drone-infeasible clusters SHALL be marked with an explicit `fallback_reason` and SHALL NOT be recommended as drone-deliverable.

### Requirement: Last-mile mode comparison is explainable

The system SHALL compare drone, vehicle, and hybrid last-mile modes on cost, duration, carbon, freshness risk, and service level, and SHALL recommend only among feasible modes.

#### Scenario: Mode comparison is requested

- GIVEN bounded C-end clusters with resolved centroids
- WHEN the last-mile response is returned
- THEN each mode row SHALL include `cost`, `duration_min`, `carbon_kg`, `freshness_risk`, `service_level`, `feasible`, and `fallback_reason`
- AND the recommended mode SHALL be feasible
- AND the response SHALL include a `recommendation_reason` that explains the selected mode.

### Requirement: Geocoding cache is isolated and bounded

The system SHALL persist geocoding results only in `case_food_geocoding_cache` and SHALL NOT mutate production `shipment_facts`, `orders`, or `vehicles`.

#### Scenario: Geocoding is persisted

- GIVEN a bounded geocode call with `persist:true`
- WHEN the response is returned
- THEN the truth contract SHALL report `raw_fact_mutation:false` and `source_tables_mutated:["case_food_*"]`
- AND the cache table SHALL be queryable by `address_hash` for subsequent hits.

### Requirement: C-end geography and drone last-mile are visible in the console

The frontend SHALL surface C-end cluster geography and drone last-mile comparison in the food supply-chain case page.

#### Scenario: Operator opens the case page

- GIVEN the Vue app is running and the user is logged in
- WHEN the user opens `/cases/food-supply`
- THEN the GIS network tab SHALL show a C-end clusters panel with resolved vs needs-geocoding KPIs
- AND the dispatch tab SHALL show a drone last-mile comparison panel with feasibility and recommendation metadata.
