# Logistics Decision Console Next

This is the parallel Next.js + TypeScript + Tailwind shell for the logistics route planning platform.

It does not replace the existing Vue command center yet. It is the migration entrypoint for the modern decision console.

## Stack

- Next.js App Router
- React
- TypeScript
- Tailwind CSS
- Leaflet route tile preview

## API Configuration

Create `.env.local` from `.env.example`:

```powershell
Copy-Item .env.example .env.local
```

Set the Flask API base URL:

```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:5000/api
NEXT_API_BASE_URL=http://localhost:5000/api
```

`NEXT_API_BASE_URL` is used by server-side fetching. `NEXT_PUBLIC_API_BASE_URL` is kept for future client-side modules.

Protected Flask APIs use `Authorization: Bearer ...`. Server-side Next fetches forward auth in this order:

- explicit `Authorization` passed by a caller
- server-only `NEXT_API_BEARER_TOKEN` or `NEXT_API_AUTH_TOKEN`
- incoming request `Authorization`
- `access_token`, `jwt`, or `token` cookie

Do not commit real tokens. The env variables are only for local smoke or trusted server-side deployment wiring.

When a server-side fetch receives `HTTP_401` and the auth source is not an explicit caller header or server env token, `safeApiFetch` uses the httpOnly `refresh_token` cookie to call Flask `/api/auth/refresh`, then retries the original request once with the refreshed access token. Browser JavaScript still never receives raw token values. Cookie persistence is guaranteed through Next route handlers such as `/api/auth/session` and `/api/auth/refresh`; during plain server rendering it is best-effort, but the current render can still retry with the refreshed token.

The route comparison page can optionally render Leaflet map tiles:

```env
NEXT_PUBLIC_ROUTE_TILE_URL=https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png
NEXT_PUBLIC_ROUTE_TILE_ATTRIBUTION=&copy; OpenStreetMap contributors
```

These values are browser-visible by design. Leave them empty to use the SVG provider-polyline preview only. For Tianditu or other commercial tiles, configure a browser-safe tile URL according to the provider's terms and key policy.

## Current Screens

The Next shell now has a shared console layout and seven real routes:

- `/` overview
- `/ai-prediction`
- `/anomaly-detection`
- `/dispatch`
- `/dispatch/scenarios/[id]`
- `/network-design`
- `/map-view`
- `/route-compare`
- `/login`

The pages read:

- `/api/ai-prediction/health`
- `/api/ai-prediction/baseline/evaluate`
- `/api/ai-prediction/demand/forecast`
- `/api/ai-prediction/features/dataset`
- `/api/ai-prediction/model/status`
- `/api/ai-anomaly/health`
- `/api/ai-anomaly/detect`
- `/api/dispatch/health`
- `/api/dispatch/algorithms`
- `/api/dispatch/waves`
- `/api/dispatch/preview`
- `/api/dispatch/scenarios`
- `/api/dispatch/compare-solvers`
- `/api/dispatch/learning-dataset`
- `/api/dispatch/policy-scorer`
- `/api/dispatch/reward-model`
- `/api/dispatch/redispatch-simulator`
- `/api/dispatch/redispatch-profiles`
- `/api/optimization/gurobi/health`
- `/api/optimization/gurobi/network-design-demo`
- `/api/optimization/gurobi/network-design`
- `/api/optimization/solver-benchmark-demo`
- `/api/optimization/route-sequence-benchmark`
- `/api/amap/provider-health`
- `/api/amap/distance/cache/stats`
- `/api/amap/distance/validate`
- `/api/amap/route/compare`
- `/api/amap/route/local-benchmark`
- `/api/tianditu/keys`
- `/api/tianditu/compare/amap`
- `/api/orders/recommend-route`
- `/api/orders/35692/recommend-route`
- `/api/nodes`
- `/api/orders`
- Next auth bridge:
  - `/api/auth/login`
  - `/api/auth/logout`
  - `/api/auth/refresh`
  - `/api/auth/session`
- Route compare BFF:
  - `/api/route-compare/suggestions`

If the Flask backend is offline, the shell renders degraded states instead of a blank page.

The dispatch page sends `persist: false` to `/api/dispatch/preview`, so server-rendered page refreshes do not create preview scenarios.

The dispatch page now shows plan-level route truth. Each preview plan can expose `route_legs` and `route_truth` from Flask, and the UI summarizes assignment leg count, estimated leg count, distance source distribution, and provider status distribution. This is an assignment-distance explanation layer, not a provider road polyline.

The dispatch page also reads `/api/dispatch/learning-dataset`. It summarizes persisted `dispatch_scenarios` / `dispatch_assignments` as a shadow-mode learning dataset: row count, readiness, average proxy reward, route truth coverage, source/status distributions, and feature schema. This is offline AI training data preparation only; DQL/DQN must stay in shadow scoring until separately validated.

The same page reads `/api/dispatch/policy-scorer` to compare offline shadow policies over that dataset. It shows the best deployable shadow policy, policy score, baseline delta, and a table of historical, balanced, utilization-first, reliability-first, risk-averse, cost-guarded, and non-deployable oracle policies. These scores are rank-sensitive proxy metrics and do not mutate dispatch scenarios, orders, or vehicle state.

The dispatch page also reads `/api/dispatch/reward-model`. It trains/evaluates the lightweight `linear_reward_ranker_v1` shadow baseline over persisted assignments and shows train/test size, MAE/RMSE/R2, pairwise rank accuracy, and feature importance. This is a learning baseline for later DQL/DQN work, not an online dispatch controller.

`/dispatch/scenarios/[id]` is the scenario history detail surface. It reads `/api/dispatch/scenarios/:id` plus the learning dataset, policy scorer, reward model, and redispatch simulator endpoints with `scenario_id=<id>`, then shows scenario summary, assignment rows, route truth, AI shadow context, scenario-scoped policy score, scenario-scoped reward-model metrics, and dynamic re-dispatch shadow simulation. This page is for traceability and replay-style inspection; it does not apply or mutate scenarios.

The dynamic re-dispatch panel calls `/api/dispatch/redispatch-simulator` with a synthetic delay/cost/provider-degradation profile. It shows impacted assignments, held-for-reassignment counts, reward delta, best deployable shadow policy, and row-level score impacts. The panel has an SSR form for `delay_minutes`, `delay_vehicle_ids`, `unavailable_vehicle_ids`, `cost_multiplier`, `provider_degradation`, `priority_order_refs`, `reliability_drop`, and `top_k`; submitted values stay in the URL and are forwarded server-side. It also reads `/api/dispatch/redispatch-profiles` to show anomaly-driven profiles generated from real shipment-fact anomaly signals, with `Apply` links that fill the simulator parameters. This is a read-only DQL/DQN preparation surface; final dispatch changes must still go through solver-backed apply flows.

The login page posts to the Next auth bridge, which forwards credentials to Flask and stores returned tokens in httpOnly cookies. Browser JavaScript does not receive the raw access or refresh token.

`/api/auth/session` also attempts one refresh-and-retry when the access token is missing or expired but the refresh cookie is still valid, keeping the console header and protected SSR pages aligned.

## Commands

```powershell
npm install
npm run dev
npm run typecheck
npm run build
```

Default dev port:

```text
http://localhost:5174
```

## Migration Boundary

- Existing Vue frontend remains the production UI.
- This Next.js shell starts with analysis overview, AI prediction, anomaly detection, smart dispatch, network design, advanced route comparison, solver benchmarks, and provider truth.
- Later modules should continue migrating page-by-page: interactive map controls, authenticated provider polyline smoke, browser-safe tile configuration, role-aware operations, and full authenticated workflows.

The network design page is a bounded CFLP decision surface. With `use_database=true`, it reads a small OD aggregate from `shipment_facts`; it is a real-data entrypoint, not a full 50k-shipment exact network solve.

The map view page is now a migrated provider-readiness surface. It aggregates AMap route/weather/traffic health, Tianditu key status, AMap distance cache totals, selected OD validation, node inventory, order route recommendation, and provider polyline preview. It does not expose backend API keys, raw tokens, or cache database paths. It supports the same selection query fields as route comparison:

- `origin_id`
- `destination_id`
- `order_id`
- `waypoint_ids`
- `prefer_source`
- `strategy`
- `node_query`
- `order_query`

`/map-view` includes a `Map Selection Console` with direct Node/Order ID forms, SSR node/order search forms, and the shared client-side autocomplete. Autocomplete still calls the same-origin BFF `/api/route-compare/suggestions`; unauthenticated or upstream-degraded states return a friendly `success:false` JSON payload with HTTP 200 so the page can show an inline message without browser resource errors.

`/map-view` and `/route-compare` both include `Local Algorithm Benchmark`. The panel now prefers the backend `/api/amap/route/local-benchmark` contract and falls back to page-level candidate comparison if that endpoint is unavailable. Next requests `provider_sources: ["amap", "tianditu"]`, so the same panel can compare multiple local graph strategies against high-map and Tianditu road-provider candidates, showing:

- distance delta and percentage delta
- duration delta and percentage delta
- local path node count
- provider geometry point count
- candidate status
- backend strategy table for Dijkstra/A* targets
- road-provider table for AMap/Tianditu availability
- local route truth summary from `routes.route_data`
- partial provider degradation from `provider_errors`
- truth metadata explaining that local graph sequences and provider road polylines are comparative inputs, not one interchangeable truth source

`/map-view` and `/route-compare` also include `Route Sequence Solver Benchmark`. The panel calls `/api/optimization/route-sequence-benchmark` using the currently selected OD pair as a small closed sequence and shows:

- nearest-neighbor and 2-opt local sequence results
- optional OR-Tools/Gurobi solver rows when available
- route graph pair count and Haversine fallback pair count
- best node sequence
- route truth summary from `routes.route_data`
- solver degradation without failing the whole page

The sequence panel accepts `waypoint_ids` in the page URL, for example:

```text
/route-compare?origin_id=1&destination_id=3&waypoint_ids=2,5,8
/map-view?origin_id=1&destination_id=3&waypoint_ids=2,5,8
```

Node search, client autocomplete, and Node Inventory actions include a `途经` action that appends a node to the benchmark waypoint set while preserving the SSR-safe URL workflow.

The route comparison page is an authenticated-provider diagnostic surface. It compares AMap, Tianditu, local graph search, and the order route recommendation contract. It now accepts query-driven OD/order inputs through the page form:

- `origin_id`
- `destination_id`
- `order_id`
- `waypoint_ids`
- `prefer_source`
- `strategy`

If only `order_id` is provided and the Flask recommendation API returns origin/destination nodes, the provider comparison uses the order-derived OD pair. The page still shows degraded states when JWT-protected APIs are unavailable.

The page also renders a provider polyline preview. It parses AMap/Tianditu/recommended route `polyline` coordinates, plus any drawable local path coordinates, into a Leaflet tile preview when `NEXT_PUBLIC_ROUTE_TILE_URL` is configured and a bounded SVG geometry preview that always remains available as a fallback. The tile layer is presentation only; source truth still comes from provider route metadata and the per-source legend.

The page includes a `Cache & Tile Diagnostics` panel for route-truth checks:

- AMap distance cache totals from `/api/amap/distance/cache/stats`
- current OD validation from `/api/amap/distance/validate`
- cache hit-before-call and exists-after-call state
- safe distance source display without exposing the server cache database path
- tile-layer configured/degraded state for `NEXT_PUBLIC_ROUTE_TILE_URL`

The page includes a server-rendered `Selection Assist` panel for real data lookup:

- node suggestions call Flask `/api/nodes` with `node_query`
- order suggestions call Flask `/api/orders` with `order_query`
- order search reuses the backend's `shipment_facts` fallback when legacy `orders` is empty
- candidate actions update the URL with `origin_id`, `destination_id`, or `order_id`, keeping the workflow token-safe through SSR

The panel also has client-side autocomplete. Browser JavaScript calls the same-origin Next BFF route `/api/route-compare/suggestions`; that route reads httpOnly cookies on the server, forwards the request to Flask, retries once after refresh when possible, and returns sanitized node/order fields. Raw Flask tokens never enter browser JavaScript. Business/auth degradation is returned as HTTP 200 with `success:false`; invalid BFF parameters still return 400.

When the user is not authenticated or the Flask backend is unavailable, this panel shows degraded empty states instead of fake options.
