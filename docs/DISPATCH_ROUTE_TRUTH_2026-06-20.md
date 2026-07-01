# Dispatch Route Truth Contract

Date: 2026-06-20

## Purpose

Smart dispatch preview now returns route truth at the plan level. This makes each vehicle assignment explainable without pretending that the dispatch sequence is a real road-navigation polyline.

## Backend Contract

Each dispatch plan may include:

- `route_legs`: one row per assigned order origin-to-destination leg.
- `route_truth`: an aggregate truth summary for the plan.

The top-level dispatch response and `summary` also include aggregate `route_truth` across all plans.

### `route_legs`

Each leg describes the distance used for assigning one order:

- `order_ref`
- `order_number`
- `from_name`
- `to_name`
- `distance_km`
- `duration_minutes`
- `cost`
- `data_source`
- `distance_source`
- `duration_source`
- `path_source = dispatch_order_origin_destination_leg`
- `provider_status`
- `fallback_reason`
- `authenticity_level`

### `route_truth`

The aggregate summary includes:

- `path_source = dispatch_assignment_sequence`
- `leg_type = order_origin_destination`
- `leg_count`
- `assignment_leg_count`
- `estimated_leg_count`
- `distance_source_counts`
- `duration_source_counts`
- `provider_status_counts`
- `fallback_reason_counts`
- `authenticity_level`

## Important Boundary

`route_sequence` and `route_legs` are dispatch-planning traces. They are not provider road polylines and should not be displayed as completed navigation paths.

For road-level route geometry, use the route recommendation, AMap/Tianditu provider comparison, local route benchmark, or route-sequence benchmark contracts.

## Persistence

When a preview scenario is persisted or applied, each `dispatch_assignments.diagnostics_json` now includes the plan's `route_truth`. This gives later AI shadow mode and dynamic re-dispatch training a compact truth summary without storing large per-leg payloads repeatedly.

## Verification

Focused verification:

```powershell
python -m pytest backend\tests\test_dispatch_orchestration_layered.py backend\tests\test_dispatch_smart_contract.py -q
cd frontend-next
npm run typecheck
npm run build
```

Current result on 2026-06-20:

- backend dispatch suite: `7 passed`
- Next typecheck: passed
- Next production build: passed
