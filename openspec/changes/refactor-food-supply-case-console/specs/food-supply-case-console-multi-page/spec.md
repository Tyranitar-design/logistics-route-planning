## ADDED Requirements

### Requirement: Multi-page food supply case console
The system SHALL present the food supply-chain case as a shared Vue layout with focused child routes for overview, GIS, forecast, dispatch, multimodal, C2C, clustering, trace, scenarios, business, and agent views.

#### Scenario: Child route renders without collapsing the case shell
- **WHEN** an operator opens any `/cases/food-supply/*` child route
- **THEN** the shared case shell, truth metadata, and the selected child view render without dynamic-import failure or blank-page fallback

### Requirement: AMap JS API case maps with explainable fallback
The system SHALL use the AMap JS API for case maps when `VITE_AMAP_KEY` is configured, including road, satellite, traffic, marker, polyline, and trajectory animation capabilities, while preserving an explicit degraded fallback when the browser provider is unavailable.

#### Scenario: AMap provider is configured
- **WHEN** the browser can load AMap with the configured frontend key
- **THEN** case GIS and dispatch maps render AMap markers and route polylines, expose layer controls, and keep `distance_source`, `path_source`, `authenticity_level`, and `fallback_reason` visible

#### Scenario: AMap provider is unavailable
- **WHEN** AMap loading fails or the frontend key is missing
- **THEN** the page shows an explainable fallback panel and still renders the non-map optimization tables and charts

### Requirement: Solver trajectory animation and freshness replay
The system SHALL convert dispatch solver plans into replay frames that show vehicle position, route progress, cumulative distance/time, load, and freshness decay without changing business data.

#### Scenario: Dispatch plan contains coordinate stops
- **WHEN** a dispatch optimization result returns plans with sequenced stops and coordinates
- **THEN** the dispatch page can play, pause, reset, and speed-control moving vehicle trajectories while a synchronized freshness curve highlights the current replay point

#### Scenario: Dispatch plan lacks real road geometry
- **WHEN** a dispatch result uses Haversine, aggregate, or missing polyline geometry
- **THEN** the replay remains available as an estimated visualization and the truth strip marks the authenticity and fallback reason instead of presenting it as real navigation

### Requirement: Dispatch replay can upgrade to real AMap route geometry
The system SHALL allow dispatch replay requests to opt into AMap route geometry so distance, duration, polyline, and replay frames can upgrade from estimated C-level geometry to A/B-level provider-backed geometry when the provider succeeds.

#### Scenario: AMap route provider succeeds for all assigned routes
- **WHEN** `/api/cases/food-supply/optimize/dispatch-fresh` is called with `route_provider=amap` and AMap returns valid driving routes for all assigned customer routes
- **THEN** the response uses `distance_source=amap_driving`, `path_source=amap_route_polyline`, `authenticity_level=A`, and replay frames follow the provider polyline

#### Scenario: AMap route provider partially fails
- **WHEN** at least one assigned customer route has an AMap route but at least one route falls back
- **THEN** the response uses a mixed B-level truth status and each route-level `route_geometry` reports its own provider status and fallback reason

#### Scenario: AMap route polyline fails but distance matrix succeeds
- **WHEN** AMap driving route geometry is unavailable for assigned routes but `distance_matrix` returns valid road distance and duration
- **THEN** the response uses `distance_source=amap_distance_matrix`, `path_source=estimated_polyline_with_amap_distance_matrix`, `authenticity_level=B`, keeps the replay geometry estimated, and preserves a route-level fallback reason

### Requirement: Startup and verification remain deterministic
The system SHALL keep the launch script, frontend build, backend pytest, OpenSpec validation, and harness checks deterministic without requiring live provider keys in automated tests.

#### Scenario: Automated tests run without external provider keys
- **WHEN** backend tests or CI-style harness checks execute with mocked or missing map providers
- **THEN** tests pass by validating contract fields and degraded reasons rather than depending on live AMap, Tianditu, OSM, or MiniMax calls
