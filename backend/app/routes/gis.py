"""GIS/provider health aggregation routes."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict

from flask import Blueprint, current_app, jsonify

from app.models import Node, Route, db
from app.services.provider_key_resolver import (
    get_amap_keys,
    get_tianditu_keys,
    provider_key_status,
)


gis_bp = Blueprint("gis", __name__)


def _safe_count(model: Any) -> tuple[int, str | None]:
    try:
        return int(model.query.count()), None
    except Exception as exc:
        db.session.rollback()
        return 0, exc.__class__.__name__


def _postgis_status() -> Dict[str, Any]:
    uri = str(current_app.config.get("SQLALCHEMY_DATABASE_URI") or "")
    if not uri.startswith(("postgresql://", "postgresql+")):
        return {
            "provider": "postgis",
            "provider_status": "degraded",
            "available": False,
            "fallback_reason": "POSTGIS_REQUIRES_POSTGRESQL_RUNTIME",
            "version": None,
        }

    try:
        version = db.session.execute(db.text("SELECT PostGIS_Version()")).scalar()
        return {
            "provider": "postgis",
            "provider_status": "ok",
            "available": True,
            "fallback_reason": None,
            "version": str(version),
        }
    except Exception as exc:
        db.session.rollback()
        return {
            "provider": "postgis",
            "provider_status": "degraded",
            "available": False,
            "fallback_reason": f"POSTGIS_PROBE_FAILED:{exc.__class__.__name__}",
            "version": None,
        }


def _local_graph_status() -> Dict[str, Any]:
    node_count, node_error = _safe_count(Node)
    route_count, route_error = _safe_count(Route)
    available = node_count > 0 and route_count > 0 and not node_error and not route_error
    fallback_reason = None
    if not available:
        reasons = []
        if node_error:
            reasons.append(f"NODE_COUNT_FAILED:{node_error}")
        if route_error:
            reasons.append(f"ROUTE_COUNT_FAILED:{route_error}")
        if node_count == 0:
            reasons.append("NODE_GRAPH_EMPTY")
        if route_count == 0:
            reasons.append("ROUTE_GRAPH_EMPTY")
        fallback_reason = ";".join(reasons)
    return {
        "provider": "local_graph",
        "provider_status": "ok" if available else "degraded",
        "available": available,
        "fallback_reason": fallback_reason,
        "node_count": node_count,
        "route_count": route_count,
        "path_source": "local_dijkstra_astar_baseline",
        "distance_source": "route_table_or_haversine_fallback",
    }


def _geospatial_runtime_status() -> Dict[str, Any]:
    try:
        from app.services.optional_capability_service import get_optional_capability_service

        capabilities = get_optional_capability_service().check(run_smoke=False).get("capabilities", [])
        row = next((item for item in capabilities if item.get("id") == "geospatial_stack"), None)
        if row:
            return row
    except Exception as exc:
        return {
            "id": "geospatial_stack",
            "provider_status": "degraded",
            "available": False,
            "fallback_reason": f"GEOSPATIAL_PROBE_FAILED:{exc.__class__.__name__}",
        }
    return {
        "id": "geospatial_stack",
        "provider_status": "degraded",
        "available": False,
        "fallback_reason": "GEOSPATIAL_STACK_NOT_REPORTED",
    }


@gis_bp.route("/provider-health", methods=["GET"])
def gis_provider_health():
    """Aggregate safe GIS/provider health without exposing key values."""
    amap_keys = provider_key_status("amap", get_amap_keys())
    tianditu_keys = provider_key_status("tianditu", get_tianditu_keys())

    amap = {
        "provider": "amap",
        "provider_status": "ok" if amap_keys.get("effective_key_configured") else "degraded",
        "available": bool(amap_keys.get("effective_key_configured")),
        "fallback_reason": None if amap_keys.get("effective_key_configured") else "AMAP_KEY_MISSING",
        "keys": amap_keys,
        "role": "primary real-road routing, weather, traffic provider",
        "distance_source": "amap_driving_route",
        "path_source": "amap_polyline",
    }
    tianditu = {
        "provider": "tianditu",
        "provider_status": "ok" if tianditu_keys.get("effective_key_configured") else "degraded",
        "available": bool(tianditu_keys.get("effective_key_configured")),
        "fallback_reason": None if tianditu_keys.get("effective_key_configured") else "TIANDITU_KEY_MISSING",
        "keys": tianditu_keys,
        "role": "secondary real-road provider for comparison and fallback",
        "distance_source": "tianditu_driving_route",
        "path_source": "tianditu_polyline",
    }
    postgis = _postgis_status()
    local_graph = _local_graph_status()
    geospatial_runtime = _geospatial_runtime_status()

    components = {
        "amap": amap,
        "tianditu": tianditu,
        "postgis": postgis,
        "local_graph": local_graph,
        "geospatial_runtime": geospatial_runtime,
    }
    degraded = [
        name
        for name, item in components.items()
        if item.get("provider_status") not in {"ok", "configured"} and item.get("available") is not True
    ]
    reasons = [
        str(item.get("fallback_reason"))
        for item in components.values()
        if item.get("fallback_reason")
    ]

    real_provider_available = amap["available"] or tianditu["available"]
    postgis_available = postgis["available"]
    if real_provider_available and postgis_available:
        authenticity_level = "A"
        distance_source = "amap_or_tianditu_real_road"
        path_source = "provider_polyline_with_postgis_context"
    elif real_provider_available or postgis_available:
        authenticity_level = "B"
        distance_source = "partial_real_provider_or_postgis"
        path_source = "mixed_provider_or_spatial_baseline"
    else:
        authenticity_level = "C"
        distance_source = "local_graph_or_haversine_fallback"
        path_source = "local_algorithm_baseline"

    return jsonify(
        {
            "success": True,
            "provider": "gis_provider_health",
            "provider_status": "ok" if not degraded else "degraded",
            "degraded_components": degraded,
            "fallback_reason": ";".join(reasons) if reasons else None,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "components": components,
            "summary": {
                "real_provider_available": real_provider_available,
                "postgis_available": postgis_available,
                "local_graph_available": local_graph["available"],
                "geospatial_runtime_available": bool(geospatial_runtime.get("available")),
            },
            "distance_source": distance_source,
            "path_source": path_source,
            "authenticity_level": authenticity_level,
            "truth_contract": {
                "amap_role": "primary_real_provider",
                "tianditu_role": "comparison_or_fallback_provider",
                "local_graph_role": "offline_baseline_not_real_navigation",
                "secret_values_returned": False,
            },
            "security": {
                "api_keys_returned": False,
                "secret_values_returned": False,
            },
        }
    )
