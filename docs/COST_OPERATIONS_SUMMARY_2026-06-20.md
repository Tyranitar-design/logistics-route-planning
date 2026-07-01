# Cost Operations Summary

Date: 2026-06-20

## Purpose

`/api/analytics/operations-summary` is a real-data operations and cost overview for the Next.js decision console. `/api/analytics/operations-scorecard` aggregates the same facts into a readiness scorecard for executive triage. Both read PostgreSQL `shipment_facts` and avoid the legacy `/api/cost/*` mock fallback behavior.

The endpoint is intended for enterprise KPI monitoring:

- order volume
- freight coverage
- total freight
- average freight
- unit cost by weight/volume
- delivery completion
- on-time rate
- average transit and delay
- top OD lanes by freight
- city cost breakdown
- recent freight trend

## Endpoint

```text
GET /api/analytics/operations-summary
POST /api/analytics/operations-summary
GET /api/analytics/operations-scorecard
POST /api/analytics/operations-scorecard
```

Authentication follows the existing analytics API contract and requires JWT.

Request body / query:

```json
{
  "limit": 50000,
  "trend_days": 30,
  "lane_limit": 8,
  "city": "上海"
}
```

## Output Contract

Top-level truth:

- `data_source = shipment_fact`
- `provider_status = ok` when real freight rows exist
- `fallback_reason = FREIGHT_FIELDS_EMPTY_OR_ZERO` when shipment facts exist but freight is missing
- `authenticity_level = B` for real freight facts
- `truth_contract.business_mutation = none`

Important fields:

- `summary`: scan limit, city scope, status counts, trend and lane limits.
- `kpis`: freight totals, unit costs, completion/on-time/exception rates, transit and delay.
- `cost_components`: heuristic allocation over real freight totals. It is not invoice-line accounting.
- `trend`: recent daily shipment/freight/unit-cost trend.
- `top_lanes`: OD lanes sorted by freight.
- `city_breakdown`: inbound/outbound city freight summary.
- `recommendations`: cost and service-level recommendations derived from the KPIs.

## Operations Scorecard

`/api/analytics/operations-scorecard` reuses `operations-summary` as its evidence source and returns:

- `summary.readiness_score`: 0-100 operations/cost readiness score.
- `summary.status`: `ready` / `watch` / `needs_work`.
- `components[]`: freight data coverage, service quality, cost efficiency, exception pressure, and lane cost concentration.
- `gates[]`: real freight availability, service KPI availability, unit-cost availability, and read-only boundary.
- `recommendations[]`: operating actions derived from weak components and KPI recommendations.
- `evidence`: KPI, lane, cost component, and trend tail snapshots used by the scorecard.

Boundary:

- `truth_contract.business_mutation = none`
- `truth_contract.deployment_boundary = scorecard_readiness_only_not_accounting_or_dispatch_controller`
- It is a KPI/readiness surface, not invoice accounting, settlement, or a dispatch controller.

## Frontend

`frontend-next` `/` now includes an `Operations Scorecard` panel, an `Operations & Cost` panel, and top-level `真实运费` / `运营评分` metrics. The panels show:

- total freight
- average freight
- on-time rate
- delivery completion rate
- freight coverage
- freight per kg
- average transit hours
- exception rate
- top OD cost lanes
- cost recommendations
- readiness gates and operations scorecard recommendations

If the user is not authenticated, the Next page shows the standard degraded state from `safeApiFetch` instead of exposing data.

## Boundary

These endpoints do not mutate:

- `shipment_facts`
- `orders`
- `routes`
- `vehicles`
- dispatch tables

The cost components are explicitly marked as `freight_amount_allocation_heuristic`. They help the dashboard explain freight structure, but they are not real invoice components.

## Verification

```powershell
python -m py_compile backend/app/services/shipment_cost_analytics_service.py backend/app/routes/analytics.py backend/tests/test_shipment_cost_analytics_service.py
python -m pytest backend\tests\test_shipment_cost_analytics_service.py -q
cd frontend-next
npm run typecheck
npm run build
```

Current result:

- backend cost analytics suite: `3 passed`
- Next typecheck: passed
- Next production build: passed
