#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Backfill missing Route distances with explicit source metadata."""

from __future__ import annotations

import json
import math
from datetime import datetime
from typing import Any, Dict, Optional

from app.models import Node, Route, db
from app.services.amap_service import get_amap_service


ROAD_DISTANCE_CORRECTION_FACTOR = 1.3
DEFAULT_AVG_SPEED_KMH = 60.0


def _haversine_km(lng1: float, lat1: float, lng2: float, lat2: float) -> float:
    radius_km = 6371.0088
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlng / 2) ** 2
    )
    return 2 * radius_km * math.asin(math.sqrt(a))


def _load_route_data(value: Optional[str]) -> Dict[str, Any]:
    if not value:
        return {}
    try:
        payload = json.loads(value)
        return payload if isinstance(payload, dict) else {"legacy_route_data": payload}
    except (TypeError, ValueError):
        return {"legacy_route_data": value}


class RouteDistanceBackfillService:
    """Fill missing route distances while preserving provenance in route_data."""

    def backfill(
        self,
        apply: bool = False,
        provider: str = "haversine",
        limit: Optional[int] = None,
    ) -> Dict[str, Any]:
        provider = (provider or "haversine").lower()
        if provider not in {"haversine", "amap"}:
            raise ValueError("provider must be 'haversine' or 'amap'")

        query = Route.query.filter(Route.distance.is_(None)).order_by(Route.id.asc())
        if limit:
            query = query.limit(limit)
        routes = query.all()

        summary = {
            "candidate_routes": len(routes),
            "updated": 0,
            "skipped": 0,
            "dry_run": not apply,
            "provider": provider,
            "source_summary": {},
        }
        samples = []

        for route in routes:
            result = self._build_distance_result(route, provider)
            if not result["success"]:
                summary["skipped"] += 1
                samples.append(self._sample(route, result))
                continue

            summary["updated"] += 1
            source = result["distance_source"]
            summary["source_summary"][source] = summary["source_summary"].get(source, 0) + 1
            samples.append(self._sample(route, result))

            if apply:
                route.distance = result["distance_km"]
                route.duration = result["duration_hours"]
                route.route_data = self._merge_route_data(route.route_data, result)

        if apply:
            db.session.commit()
        else:
            db.session.rollback()

        return {
            "success": True,
            "summary": summary,
            "samples": samples[:20],
        }

    def _build_distance_result(self, route: Route, provider: str) -> Dict[str, Any]:
        start = Node.query.get(route.start_node_id) if route.start_node_id else None
        end = Node.query.get(route.end_node_id) if route.end_node_id else None
        if not start or not end:
            return {
                "success": False,
                "error": "ROUTE_ENDPOINT_NOT_FOUND",
                "fallback_reason": "ROUTE_ENDPOINT_NOT_FOUND",
            }
        if None in (start.longitude, start.latitude, end.longitude, end.latitude):
            return {
                "success": False,
                "error": "ROUTE_ENDPOINT_COORDINATE_MISSING",
                "fallback_reason": "ROUTE_ENDPOINT_COORDINATE_MISSING",
            }

        origin = (float(start.longitude), float(start.latitude))
        destination = (float(end.longitude), float(end.latitude))

        if provider == "amap":
            try:
                amap = get_amap_service().driving_route(origin, destination)
                if amap.success and amap.distance:
                    distance_km = round(float(amap.distance) / 1000.0, 2)
                    duration_hours = round(float(amap.duration or 0) / 3600.0, 2)
                    if duration_hours <= 0 and distance_km > 0:
                        duration_hours = round(distance_km / DEFAULT_AVG_SPEED_KMH, 2)
                    degraded = bool(amap.degraded)
                    return {
                        "success": True,
                        "distance_km": distance_km,
                        "duration_hours": duration_hours,
                        "distance_source": "haversine_corrected" if degraded else "amap_driving_route",
                        "duration_source": "estimated_speed" if degraded else "amap_driving_route",
                        "provider": "amap",
                        "provider_status": amap.provider_status,
                        "degraded": degraded,
                        "fallback_reason": amap.fallback_reason,
                        "authenticity": amap.authenticity,
                        "polyline_points": len(amap.polyline or []),
                    }
            except Exception as exc:
                return self._haversine_result(origin, destination, fallback_reason=f"AMAP_BACKFILL_ERROR:{exc}")

        return self._haversine_result(origin, destination, fallback_reason="ROUTE_DISTANCE_BACKFILL_HAVERSINE")

    def _haversine_result(self, origin, destination, fallback_reason: str) -> Dict[str, Any]:
        straight_km = _haversine_km(origin[0], origin[1], destination[0], destination[1])
        distance_km = round(straight_km * ROAD_DISTANCE_CORRECTION_FACTOR, 2)
        duration_hours = round(distance_km / DEFAULT_AVG_SPEED_KMH, 2) if distance_km else 0
        return {
            "success": True,
            "distance_km": distance_km,
            "duration_hours": duration_hours,
            "distance_source": "haversine_corrected",
            "duration_source": "estimated_speed",
            "provider": "local",
            "provider_status": "degraded",
            "degraded": True,
            "fallback_reason": fallback_reason,
            "authenticity": {
                "level": "C",
                "has_real_distance": False,
                "has_real_duration": False,
                "used_fallback": True,
                "distance_source": "haversine_corrected",
                "duration_source": "estimated_speed",
                "message": "Route distance was backfilled from endpoint coordinates using Haversine correction.",
            },
        }

    def _merge_route_data(self, existing: Optional[str], result: Dict[str, Any]) -> str:
        payload = _load_route_data(existing)
        payload["distance_source"] = result["distance_source"]
        payload["duration_source"] = result["duration_source"]
        payload["provider"] = result["provider"]
        payload["provider_status"] = result["provider_status"]
        payload["fallback_reason"] = result["fallback_reason"]
        payload["authenticity"] = result.get("authenticity")
        payload["distance_backfill"] = {
            "distance_km": result["distance_km"],
            "duration_hours": result["duration_hours"],
            "distance_source": result["distance_source"],
            "duration_source": result["duration_source"],
            "provider": result["provider"],
            "provider_status": result["provider_status"],
            "degraded": result["degraded"],
            "fallback_reason": result["fallback_reason"],
            "backfilled_at": datetime.utcnow().isoformat() + "Z",
        }
        if result.get("polyline_points") is not None:
            payload["distance_backfill"]["polyline_points"] = result["polyline_points"]
        return json.dumps(payload, ensure_ascii=False)

    @staticmethod
    def _sample(route: Route, result: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "route_id": route.id,
            "name": route.name,
            "start_node_id": route.start_node_id,
            "end_node_id": route.end_node_id,
            "success": result.get("success"),
            "distance_km": result.get("distance_km"),
            "duration_hours": result.get("duration_hours"),
            "distance_source": result.get("distance_source"),
            "provider_status": result.get("provider_status"),
            "fallback_reason": result.get("fallback_reason"),
            "error": result.get("error"),
        }


def backfill_route_distances(apply: bool = False, provider: str = "haversine", limit: Optional[int] = None) -> Dict[str, Any]:
    return RouteDistanceBackfillService().backfill(apply=apply, provider=provider, limit=limit)
