#!/usr/bin/env python
"""Focused enterprise smoke harness for local/server verification.

Usage:
    python backend/scripts/enterprise_smoke_harness.py --base-url http://127.0.0.1:5000
    python backend/scripts/enterprise_smoke_harness.py --base-url https://example.com --token %TOKEN%

The script intentionally prints compact status metadata only. It never prints
the provided token or any secret values.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from typing import Any, Dict, Optional


def _request(
    base_url: str,
    method: str,
    path: str,
    *,
    token: Optional[str] = None,
    payload: Optional[Dict[str, Any]] = None,
    timeout: float = 15.0,
) -> Dict[str, Any]:
    url = base_url.rstrip("/") + path
    body = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"

    started = time.time()
    request = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8", errors="replace")
            data = json.loads(raw) if raw else {}
            return _compact_response(path, response.status, data, time.time() - started)
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            data = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            data = {"error": raw[:300]}
        return _compact_response(path, exc.code, data, time.time() - started)
    except Exception as exc:
        return {
            "path": path,
            "status_code": None,
            "ok": False,
            "success": False,
            "elapsed_ms": int((time.time() - started) * 1000),
            "error": f"{exc.__class__.__name__}: {exc}",
        }


def _compact_response(path: str, status_code: int, data: Dict[str, Any], elapsed: float) -> Dict[str, Any]:
    summary = data.get("summary") or {}
    demo_readiness = data.get("demo_readiness") or {}
    database_runtime = data.get("database_runtime") or {}
    capability_summary = data.get("summary") if path.startswith("/api/optimization/capabilities") else None
    if 200 <= status_code < 300:
        classification = "ok"
    elif status_code in {401, 403}:
        classification = "auth_required"
    elif status_code == 404:
        classification = "route_missing"
    elif status_code >= 500:
        classification = "server_error"
    else:
        classification = "http_error"

    return {
        "path": path,
        "status_code": status_code,
        "ok": 200 <= status_code < 300,
        "success": data.get("success"),
        "classification": classification,
        "route_present": status_code != 404,
        "elapsed_ms": int(elapsed * 1000),
        "provider_status": data.get("provider_status"),
        "fallback_reason": data.get("fallback_reason") or data.get("error"),
        "demo_readiness_status": demo_readiness.get("status"),
        "demo_readiness_score": demo_readiness.get("score"),
        "database_backend": database_runtime.get("backend"),
        "shipment_facts": database_runtime.get("shipment_facts"),
        "assigned_orders": summary.get("assigned_orders") or summary.get("total_orders_assigned"),
        "unassigned_orders": summary.get("unassigned_orders") or summary.get("total_orders_unassigned"),
        "solver_family": data.get("solver_family"),
        "execution_mode": data.get("execution_mode"),
        "distance_source": data.get("distance_source"),
        "path_source": data.get("path_source"),
        "authenticity_level": data.get("authenticity_level"),
        "matrix_mode": data.get("matrix_mode"),
        "pair_count": summary.get("pair_count"),
        "polyline_points": summary.get("polyline_points"),
        "route_count": summary.get("provider_count"),
        "route_geometry_count": summary.get("geometry_count"),
        "route_history_count": summary.get("history_count"),
        "recommended_provider": summary.get("recommended_provider"),
        "recommended_score": summary.get("recommended_score"),
        "best_quality_score": summary.get("best_quality_score"),
        "recommendation_reason": summary.get("recommendation_reason"),
        "cache_status": data.get("cache_status") or summary.get("cache_status"),
        "cache_kind": data.get("cache_kind"),
        "pareto_size": summary.get("pareto_size"),
        "capabilities_available": (capability_summary or {}).get("available"),
        "capabilities_total": (capability_summary or {}).get("total"),
    }


def _check(
    name: str,
    method: str,
    path: str,
    payload: Optional[Dict[str, Any]] = None,
    *,
    allow_auth_required: bool = False,
) -> Dict[str, Any]:
    return {
        "name": name,
        "method": method,
        "path": path,
        "payload": payload,
        "allow_auth_required": allow_auth_required,
    }


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Run focused logistics enterprise smoke checks.")
    parser.add_argument("--base-url", default=os.environ.get("LOGISTICS_BACKEND_URL", "http://127.0.0.1:5000"))
    parser.add_argument("--token", default=os.environ.get("LOGISTICS_AUTH_TOKEN"))
    parser.add_argument("--timeout", type=float, default=15.0)
    args = parser.parse_args(argv)

    dispatch_payload = {
        "data_source": "auto",
        "limit": 20,
        "algorithm": "balanced",
        "policy_mode": "solver_only",
        "persist": False,
        "use_precise_distance": False,
        "max_orders_per_vehicle": 5,
        "weights": {"cost": 0.4, "time": 0.3, "satisfaction": 0.3},
    }
    enterprise_payload = {
        "runtime_profile": "interactive",
        "limit": 5000,
        "trend_days": 14,
        "lane_limit": 5,
        "horizon_days": 7,
        "anomaly_limit": 8,
    }
    carbon_payload = {
        "distance": 120,
        "vehicle_type": "medium",
        "fuel_type": "diesel",
    }
    agent_preview_payload = {
        "tool_name": "dispatch_preview",
        "parameters": {"persist": True, "limit": 20, "policy_mode": "dqn_shadow"},
    }
    decision_dry_run_payload = {
        "scenario_type": "dispatch",
        "name": "demo smoke dry-run",
        "persist": False,
        "summary": {"source": "enterprise_smoke_harness"},
        "payload": {"policy_mode": "solver_only"},
    }
    food_dispatch_payload = {
        "wave_date": "06-01",
        "store_limit": 8,
        "persist": False,
    }
    food_network_payload = {
        "max_facilities": 2,
        "store_limit": 12,
        "persist": False,
    }
    food_solver_compare_payload = {
        "wave_date": "06-01",
        "store_limit": 8,
        "max_facilities": 2,
        "persist": False,
    }
    food_matrix_osm_payload = {
        "matrix_mode": "osm",
        "limit": 8,
        "persist": False,
    }
    food_matrix_amap_payload = {
        "matrix_mode": "amap",
        "limit": 2,
        "persist": False,
    }
    food_matrix_tianditu_payload = {
        "matrix_mode": "tianditu",
        "limit": 2,
        "persist": False,
    }
    food_osm_cache_build_payload = {
        "mode": "case-baseline",
        "limit": 8,
        "overwrite": False,
    }
    food_route_preview_payload = {
        "source_code": "FAC-1",
        "target_code": "BSTORE-001",
        "provider": "osm",
    }
    food_route_compare_payload = {
        "source_code": "FAC-1",
        "target_code": "BSTORE-001",
        "providers": ["amap", "tianditu", "osm", "haversine"],
        "use_cache": True,
        "persist": True,
        "cache_ttl_hours": 24,
    }
    food_network_milp_payload = {
        "solver_mode": "milp",
        "max_facilities": 2,
        "store_limit": 8,
        "persist": False,
    }
    food_dispatch_ortools_payload = {
        "solver_mode": "ortools",
        "wave_date": "06-01",
        "store_limit": 8,
        "persist": False,
    }
    food_dispatch_pyvrp_payload = {
        "solver_mode": "pyvrp",
        "wave_date": "06-01",
        "store_limit": 8,
        "persist": False,
    }
    food_pareto_nsga_payload = {
        "algorithm_family": "nsga",
        "max_facilities": 2,
        "store_limit": 8,
        "persist": False,
    }
    food_solver_compare_advanced_payload = {
        "advanced_mode": True,
        "wave_date": "06-01",
        "store_limit": 8,
        "max_facilities": 2,
        "persist": False,
    }
    food_scenario_payload = {
        "name": "food supply smoke dry-run",
        "persist": False,
        "summary": {"source": "enterprise_smoke_harness"},
        "payload": {"case_id": "peach-supply-chain-2023"},
    }
    food_c2c_geocode_payload = {
        "geocode_limit": 5,
        "provider": "auto",
        "persist": False,
    }
    food_last_mile_payload = {
        "cluster_limit": 8,
        "persist": False,
    }
    food_multimodal_payload = {
        "cluster_limit": 6,
        "persist": False,
    }
    food_dispatch_fresh_payload = {
        "wave_date": "06-01",
        "store_limit": 8,
        "time_window_hours": 48,
        "freshness_window_days": 4,
        "persist": False,
    }
    food_trace_issue_payload = {
        "orchard_code": "ORCHARD-A",
        "wave_date": "09-01",
        "cluster_code": "CC-HEFEI",
    }
    food_scenarios_compare_payload = {}

    checks = [
        _check("ready", "GET", "/api/ready"),
        _check("runtime_capabilities", "GET", "/api/runtime/capabilities?solver_probe=0"),
        _check("gis_provider_health", "GET", "/api/gis/provider-health"),
        _check("advanced_ml_status", "GET", "/api/advanced-ml/status"),
        _check("advanced_ml_with_anomaly", "GET", "/api/advanced-ml/predict/with-anomaly?days=7"),
        _check("enterprise_summary", "POST", "/api/analytics/enterprise-summary", enterprise_payload, allow_auth_required=True),
        _check("data_analytics_carbon", "POST", "/api/data-analytics/carbon-footprint/calculate", carbon_payload),
        _check("agent_tool_preview", "POST", "/api/agent/tools/preview", agent_preview_payload),
        _check("decision_scenario_dry_run", "POST", "/api/decision/scenarios", decision_dry_run_payload),
        _check("optimization_capabilities", "GET", "/api/optimization/capabilities"),
        _check("dispatch_health", "GET", "/api/dispatch/health", allow_auth_required=True),
        _check("dispatch_preview", "POST", "/api/dispatch/preview", dispatch_payload, allow_auth_required=True),
        _check("dispatch_smart", "POST", "/api/dispatch/smart", dispatch_payload, allow_auth_required=True),
        _check("food_supply_summary", "GET", "/api/cases/food-supply/summary"),
        _check("food_supply_network", "GET", "/api/cases/food-supply/network"),
        _check("food_supply_network_design", "POST", "/api/cases/food-supply/optimize/network-design", food_network_payload),
        _check("food_supply_dispatch", "POST", "/api/cases/food-supply/optimize/dispatch", food_dispatch_payload),
        _check("food_supply_solver_compare", "POST", "/api/cases/food-supply/optimize/solver-compare", food_solver_compare_payload),
        _check("food_supply_osm_cache_status", "GET", "/api/cases/food-supply/osm-cache/status"),
        _check("food_supply_osm_cache_build", "POST", "/api/cases/food-supply/osm-cache/build", food_osm_cache_build_payload),
        _check("food_supply_route_preview", "POST", "/api/cases/food-supply/routes/preview", food_route_preview_payload),
        _check("food_supply_route_compare", "POST", "/api/cases/food-supply/routes/compare", food_route_compare_payload),
        _check("food_supply_route_compare_cached", "POST", "/api/cases/food-supply/routes/compare", food_route_compare_payload),
        _check("food_supply_route_compare_history", "GET", "/api/cases/food-supply/routes/compare/history?source_code=FAC-1&target_code=BSTORE-001&limit=5"),
        _check("food_supply_matrix_osm", "POST", "/api/cases/food-supply/distance-matrix/build", food_matrix_osm_payload),
        _check("food_supply_matrix_amap", "POST", "/api/cases/food-supply/distance-matrix/build", food_matrix_amap_payload),
        _check("food_supply_matrix_tianditu", "POST", "/api/cases/food-supply/distance-matrix/build", food_matrix_tianditu_payload),
        _check("food_supply_network_milp", "POST", "/api/cases/food-supply/optimize/network-design", food_network_milp_payload),
        _check("food_supply_dispatch_ortools", "POST", "/api/cases/food-supply/optimize/dispatch", food_dispatch_ortools_payload),
        _check("food_supply_dispatch_pyvrp", "POST", "/api/cases/food-supply/optimize/dispatch", food_dispatch_pyvrp_payload),
        _check("food_supply_pareto_nsga", "POST", "/api/cases/food-supply/optimize/pareto", food_pareto_nsga_payload),
        _check("food_supply_solver_compare_advanced", "POST", "/api/cases/food-supply/optimize/solver-compare", food_solver_compare_advanced_payload),
        _check("food_supply_scenario_dry_run", "POST", "/api/cases/food-supply/scenarios", food_scenario_payload),
        _check("food_supply_c2c_clusters", "GET", "/api/cases/food-supply/c2c/clusters"),
        _check("food_supply_c2c_geocode", "POST", "/api/cases/food-supply/c2c/geocode", food_c2c_geocode_payload),
        _check("food_supply_c2c_geocode_status", "GET", "/api/cases/food-supply/c2c/geocode/status"),
        _check("food_supply_last_mile", "POST", "/api/cases/food-supply/optimize/last-mile", food_last_mile_payload),
        _check("food_supply_orchard_timeseries", "GET", "/api/cases/food-supply/orchards/timeseries"),
        _check("food_supply_orchard_forecast", "GET", "/api/cases/food-supply/orchards/forecast?horizon=14&freshness_days=4"),
        _check("food_supply_multimodal", "POST", "/api/cases/food-supply/optimize/multimodal", food_multimodal_payload),
        _check("food_supply_dispatch_fresh", "POST", "/api/cases/food-supply/optimize/dispatch-fresh", food_dispatch_fresh_payload),
        _check("food_supply_trace_issue", "POST", "/api/cases/food-supply/trace/issue", food_trace_issue_payload),
        _check("food_supply_scenarios_compare", "POST", "/api/cases/food-supply/scenarios/compare", food_scenarios_compare_payload),
        _check("food_supply_business_kpi", "GET", "/api/cases/food-supply/business-kpi"),
    ]

    results = []
    for check in checks:
        result = _request(
            args.base_url,
            check["method"],
            check["path"],
            token=args.token,
            payload=check.get("payload"),
            timeout=args.timeout,
        )
        auth_allowed = bool(check.get("allow_auth_required"))
        route_present = bool(result.get("route_present")) and result.get("status_code") is not None
        result.update(
            {
                "name": check["name"],
                "method": check["method"],
                "auth_required_allowed": auth_allowed,
                "passed": bool(result.get("ok"))
                or (result.get("classification") == "auth_required" and auth_allowed),
                "route_present": route_present,
            }
        )
        results.append(result)

    route_missing = [item["name"] for item in results if item.get("classification") == "route_missing"]
    auth_required = [item["name"] for item in results if item.get("classification") == "auth_required"]
    failed = [item["name"] for item in results if not item.get("passed")]
    output = {
        "base_url": args.base_url,
        "token_provided": bool(args.token),
        "passed": not route_missing and not failed,
        "summary": {
            "total": len(results),
            "ok": sum(1 for item in results if item.get("ok")),
            "auth_required": len(auth_required),
            "route_missing": len(route_missing),
            "failed": len(failed),
        },
        "route_missing": route_missing,
        "auth_required": auth_required,
        "failed": failed,
        "results": results,
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0 if output["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
