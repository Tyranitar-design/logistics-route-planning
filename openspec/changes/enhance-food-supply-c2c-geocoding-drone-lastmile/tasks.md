## 1. SDD / Contract Tests

- [x] 1.1 Create OpenSpec proposal/design/tasks/spec delta for C2C geocoding and drone last-mile.
- [x] 1.2 Add backend tests for C2C geocoding cache model, provider success/fallback, address cleaning, and bounded limits.
- [x] 1.3 Add backend tests for C2C region clustering centroid provenance and demand aggregation.
- [x] 1.4 Add backend tests for drone last-mile feasibility, mode comparison, and recommendation under truth contract.

## 2. Backend C2C Geocoding

- [x] 2.1 Add isolated `case_food_geocoding_cache` model with `address_hash` unique constraint and provider provenance columns.
- [x] 2.2 Add address cleaning + sha256 hashing helpers and region-centroid local fallback.
- [x] 2.3 Implement bounded `_geocode_c2c_addresses` with amap → tianditu → local precedence and per-row provenance.
- [x] 2.4 Add `/api/cases/food-supply/c2c/geocode`, `/c2c/geocode/status` endpoints with cache policy and truth contract.
- [x] 2.5 Enrich `_load_c2c_demands` to keep the address dimension and expose region clusters.

## 3. Backend Region Clustering

- [x] 3.1 Add `_c2c_clusters` that aggregates 22k rows by `(date, region)` into bounded centroids.
- [x] 3.2 Resolve each centroid via geocoding cache or local fallback with `cluster_authenticity_level`.
- [x] 3.3 Add `GET /api/cases/food-supply/c2c/clusters` endpoint with cluster-level distance provenance.

## 4. Backend Drone Last-Mile

- [x] 4.1 Add `optimize_last_mile(payload)` with drone feasibility (payload + range reserve) and cluster-level distance.
- [x] 4.2 Add drone / vehicle / hybrid mode comparison with cost, duration, carbon, freshness risk, and service level.
- [x] 4.3 Add `/api/cases/food-supply/optimize/last-mile` route and constraint validation.
- [x] 4.4 Integrate last-mile results into solver comparison rows and Pareto multi-objective signals.

## 5. Performance Hardening

- [x] 5.1 Add process-level dataset cache keyed by workbook file-size + mtime signature.
- [x] 5.2 Cap `geocode_limit`, `cluster_limit`, and `store_limit` defaults and report effective limits in diagnostics.
- [x] 5.3 Reuse region clusters across geocoding and last-mile endpoints so 22k rows are parsed once per process.

## 6. Harness And Frontend

- [x] 6.1 Extend `enterprise_smoke_harness.py` with C2C clusters, geocode, geocode status, and last-mile checks.
- [x] 6.2 Add Vue API wrappers for the four new endpoints.
- [x] 6.3 Add C-end geography panel (clusters + KPI + scatter) to the GIS network tab.
- [x] 6.4 Add drone last-mile comparison panel to the dispatch tab.

## 7. Verification And Memory

- [x] 7.1 Run focused backend tests for the food supply case.
- [x] 7.2 Run frontend build after UI updates.
- [x] 7.3 Run OpenSpec strict validation.
- [x] 7.4 Update `.codex/memory/WORKLOG.md` and `.shared-memory` memory with verification evidence.
