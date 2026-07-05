## Overview

The C-end enhancement is implemented as three bounded sub-systems on top of the existing case service: (1) address geocoding with explicit provenance, (2) region clustering that reduces 22k rows to a stable consumer-geography layer, and (3) drone last-mile optimization that reuses case resources. Every layer preserves the existing truth contract (`data_source`, `distance_source`, `path_source`, `authenticity_level`, `fallback_reason`, `solver`) and never fakes coordinates.

## Data Boundary

- C-end rows come from `一：5、C端消费者需求与地址信息.xlsx` (22,259 rows: date, region, weight_kg, boxes, address).
- A new `case_food_geocoding_cache` table stores `address_hash → (longitude, latitude, provider, authenticity_level, fallback_reason, formatted_address, created_at)`. It is case-scoped and never mirrors production facts.
- Persisted C-end demand still targets `case_food_demands`; geocoded coordinates enrich those rows only when `persist=true` is explicitly confirmed.
- Region centroids are derived from geocoded addresses or from known city coordinates already present in the case (facilities, B-stores). When neither is available, the row is reported as `needs_geocoding` with `authenticity_level=C` — it is never assigned an invented coordinate.

## Geocoding Strategy

- Address cleaning: trim, collapse whitespace, strip trailing duplicated region tokens (the workbook contains entries like `安徽省合肥市包河区安徽省合肥市`), and normalize to a deterministic `address_hash` (sha256) so duplicate addresses share one provider call.
- Provider precedence: `amap.geocode` → `tianditu.geocode` → local region-centroid fallback. The first non-degraded result wins; later providers are not called once a row is resolved.
- Bounded batch: a single `/c2c/geocode` request resolves at most `geocode_limit` unique addresses (default 60, hard cap 200) and reports `requested` vs `resolved` vs `cached` vs `needs_geocoding` counts.
- Cache policy: every successful provider result is persisted to `case_food_geocoding_cache` when `persist=true`; subsequent requests with `use_cache=true` return cached coordinates without calling the provider, and report `cache_status=hit|miss|disabled|stored`.
- Truth contract: provider-resolved coordinates are `authenticity_level=A` with `distance_source=amap_geocode|tianditu_geocode`; region-centroid fallback is `authenticity_level=C` with `fallback_reason=REGION_CENTROID_LOCAL_FALLBACK`; unmatched addresses are `needs_geocoding=true` with `fallback_reason=GEOCODE_PROVIDER_NO_MATCH`.

## Region Clustering Strategy

- 22,259 C-end rows are aggregated by `(date_label, region)` into a bounded set of consumer clusters (the workbook's `对方地区` column already yields ~30–50 regions such as 合肥 / 阜阳/亳州 / 安庆 / 重庆).
- Each cluster carries `orders`, `weight_kg`, `boxes`, the resolved centroid coordinate (geocoded or local fallback), and `cluster_authenticity_level`.
- Distance/duration from the nearest facility or B-store to each cluster centroid reuses the existing Haversine baseline and provider matrix adapters, so cluster-level last-mile distance keeps the same provenance metadata as the rest of the case.

## Drone Last-Mile Strategy

- Drones (`载重 10kg / 续航 20km / 速度 14m·s ≈ 50.4 km·h / 400 元·次`) are evaluated for the facility/B-store → consumer-centroid leg, not the long-haul orchard→warehouse leg.
- Feasibility filter: a cluster is drone-eligible when `weight_kg ≤ payload_kg` and the one-way distance is within `range_km` (configurable `range_reserve` ratio defaults to 0.9 so the drone keeps return-trip margin).
- Mode comparison: for each cluster the endpoint reports `drone`, `vehicle`, and `hybrid` options with `cost`, `duration_min`, `carbon_kg`, `freshness_risk`, `feasible`, and `fallback_reason`. Vehicle cost uses the case vehicle `cost_per_km`; drone cost uses `cost_per_trip`; hybrid uses drone for feasible clusters and vehicle for the rest.
- Recommendation: prefer the mode with the best weighted objective (cost + carbon + freshness risk + service level) among feasible modes; infeasible modes are reported with explicit `fallback_reason` and are never silently recommended.
- Hard constraints: drone payload and range are validated per cluster and surfaced in `constraint_validation` (`payload_violations`, `range_violations`, `unassigned_clusters`); RL/policy modes remain `shadow_rerank_only`.

## Performance Strategy

- Process-level Excel cache: `load_dataset()` memoizes the parsed workbook dataset on the service instance keyed by a file-size + mtime signature, so repeated requests in one Flask process do not re-read 22k rows.
- Geocoding cache: provider results are cached by `address_hash`, so the second `/c2c/geocode` call is a DB read, not a network call.
- Region clustering: the 22k → ~40 reduction happens once per dataset load and is reused by both geocoding and last-mile endpoints.
- Bounded limits: every new endpoint caps `limit`, `geocode_limit`, `cluster_limit`, and `store_limit`; harness smoke payloads use small bounded values so the demo stays interactive.

## API Boundary

- Public prefix stays `/api/cases/food-supply`.
- New endpoints:
  - `GET /c2c/clusters` — bounded C-end consumer clusters with centroid provenance.
  - `POST /c2c/geocode` — bounded address geocoding with cache policy.
  - `GET /c2c/geocode/status` — cache size, provider readiness, last resolved counts.
  - `POST /optimize/last-mile` — drone vs vehicle vs hybrid last-mile comparison.
- Write endpoints default to `persist=false`; persisted writes touch only `case_food_*` tables.
- Every response includes `data_source`, `distance_source`, `path_source`, `authenticity_level`, `fallback_reason`, and `solver`.

## UX Strategy

- The Vue case page gains a "C 端地理分布" panel inside the GIS network tab: cluster table, KPI strip (resolved / needs_geocoding / cache hit rate), and an ECharts scatter of cluster centroids colored by authenticity level.
- The case page gains a "无人机最后一公里" panel inside the dispatch tab: feasibility summary, mode comparison table, recommendation card, and explicit degradation labels when drones are infeasible or providers are unavailable.
- Empty/degraded states explain missing geocoding, provider fallback, drone infeasibility, and cache miss so the operator never confuses a fallback with a real provider result.
