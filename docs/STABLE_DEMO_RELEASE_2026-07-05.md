# 2026-07-05 稳定展示版发布记录

## Release Summary

本次发布目标是形成一个可启动、可演示、可复盘的稳定版本，主展示链路为 Vue 单前端 + Flask + PostgreSQL/PostGIS + 食品供应链仓配优化案例。

This release packages a stable, demo-ready version of the Logistics Command Center. The main demo flow is the Vue frontend, Flask backend, PostgreSQL/PostGIS data layer, and the peach fresh-food supply-chain optimization case.

## Demo Entry Points

- Online demo: `https://logistics-demo-yu.top`
- Local frontend: `http://[::1]:5173/cases/food-supply`
- Food case overview: `/cases/food-supply`
- Food case dispatch console: `/cases/food-supply/dispatch`
- Backend readiness: `/api/ready`
- Runtime capability check: `/api/runtime/capabilities?solver_probe=0`

## What Is Included

- PostgreSQL/PostGIS production data readiness with `shipment_facts=50000`.
- Food supply-chain case module with isolated `case_food_*` data and Excel source audit.
- AMap JS map rendering, dispatch replay animation, and route truth metadata.
- OR-Tools VRPTW, PSO, and greedy route candidates for dispatch comparison.
- Weight controls for cost, freshness, timeliness, carbon, and load balance.
- Agent/GIS/Decision runtime health endpoints with safe degraded states.
- Tencent Cloud deployment script support for SSH identity files.
- Production Docker support for frontend AMap build-time keys and food-case read-only data mounting.

## Truth Contract

The system must not present estimated geometry as real navigation. Route and optimization responses continue to expose:

- `distance_source`
- `path_source`
- `authenticity_level`
- `fallback_reason`
- `provider_status`

In the validated AMap dispatch flow, `route_provider=amap` returned:

```text
solver_family       ortools_cvrptw
execution_mode      vrptw_solver
distance_source     amap_driving
path_source         amap_route_polyline
authenticity_level  A
assigned_orders     8
route_count         8
animation_stage     dispatch_solver_replay_v1
first_route_frames  17
```

## Local Validation

Validated on 2026-07-05:

```powershell
backend\.venv\Scripts\python.exe -B -m pytest backend\tests\test_food_supply_case_service.py -q
# 48 passed

backend\.venv\Scripts\python.exe -B -m pytest backend\tests\test_runtime_agent_gis_decision_routes.py backend\tests\test_optional_capability_service.py backend\tests\test_postgres_layered_preview_fallback.py -q
# 20 passed

backend\.venv\Scripts\python.exe -B -m pytest backend\tests\test_dispatch_orchestration_layered.py backend\tests\test_shipment_prediction_service.py backend\tests\test_shipment_anomaly_service.py backend\tests\test_shipment_cost_analytics_service.py -q
# 41 passed

npx openspec validate refactor-food-supply-case-console --strict
# valid

cd frontend
npm run build
# built successfully; only known glyphicons, old CSS *zoom, and large chunk warnings remain

backend\.venv\Scripts\python.exe backend\scripts\enterprise_smoke_harness.py --base-url http://127.0.0.1:5000 --timeout 25
# passed=true, total=44, ok=40, auth_required=4, route_missing=0, failed=0
```

Browser validation covered:

- `/cases/food-supply` renders the canonical overview route.
- `/cases/food-supply/dispatch` renders without a Vite overlay.
- Dispatch replay starts and progresses from `0%` to `50%`.
- Cost weight slider changes from `32%` to `85%`.
- Candidate comparison generates `particle_swarm_pso`, `ortools_cvrptw`, and `greedy_vrptw_fresh`.
- No relevant frontend console errors were observed during the checked flow.

## Deployment Notes

Recommended Tencent Cloud deployment:

```powershell
python scripts\deploy_tencent_cloud_command_center.py --identity-file <local-ssh-private-key> --skip-dump
```

Use `--skip-dump` when the server already has the correct PostgreSQL/PostGIS production data. Omit it only when intentionally restoring a fresh database dump.

The deployment script does not print secrets. Keep `.env.production`, SSH private keys, API keys, database passwords, and license files outside Git.

Production deployment on 2026-07-05:

- Remote host: `122.152.220.116`
- Remote release directory: `/opt/logistics-route-system`
- Backend/frontend containers: recreated and healthy
- Data counts: `shipment_facts=50000`, `raw_logistics_shipment_records=50000`, `nodes=21`, `routes=306`, `vehicles=2`
- IP smoke: `http://122.152.220.116/api/ready` returned PostgreSQL + `registered_capabilities.missing=[]`
- Food case smoke: summary/network/page/dispatch page all returned 200
- Dispatch smoke: `dispatch-fresh` returned `assigned_orders=8`, `animation.frame_count=136`, `authenticity_level=B`
- Auth dispatch smoke: `/api/dispatch/health` and `/api/dispatch/preview` worked after login

## Remaining Non-Blocking Warnings

- Frontend build still reports legacy glyphicons runtime paths.
- Frontend CSS minification still reports old `*zoom` syntax.
- Some chunks are larger than 500 kB and can be split in a later performance pass.
- Several AI endpoints intentionally return degraded readiness when trained models or long historical time windows are not available.
- `https://logistics-demo-yu.top` currently has an expired certificate (`2026-07-01`). `certbot renew --cert-name logistics-demo-yu.top` failed because ACME validation reached a DNSPod `webblock.html` response. The app is deployed and passes IP/curl smoke, but formal HTTPS demo requires fixing domain/ACME validation first.
