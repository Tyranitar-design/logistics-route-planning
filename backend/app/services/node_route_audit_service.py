#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Node/Route coordinate foundation audit service."""

from __future__ import annotations

import math
import json
from collections import defaultdict
from typing import Any, Dict, Iterable, List, Optional, Tuple

from sqlalchemy import func

from app.models import Node, Route
from app.models.layered_data import ShipmentFact


CHINA_LNG_RANGE = (73.0, 135.5)
CHINA_LAT_RANGE = (18.0, 54.5)
WORLD_LNG_RANGE = (-180.0, 180.0)
WORLD_LAT_RANGE = (-90.0, 90.0)


def _as_float(value: Any) -> Optional[float]:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _in_range(value: float, bounds: Tuple[float, float]) -> bool:
    return bounds[0] <= value <= bounds[1]


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


def _node_payload(node: Node, issue: str, **extra: Any) -> Dict[str, Any]:
    payload = {
        "id": node.id,
        "name": node.name,
        "type": node.type,
        "province": node.province,
        "city": node.city,
        "district": node.district,
        "longitude": node.longitude,
        "latitude": node.latitude,
        "status": node.status,
        "issue": issue,
    }
    payload.update(extra)
    return payload


def _route_payload(route: Route, issue: str, **extra: Any) -> Dict[str, Any]:
    payload = {
        "id": route.id,
        "name": route.name,
        "start_node_id": route.start_node_id,
        "end_node_id": route.end_node_id,
        "origin": route.origin,
        "destination": route.destination,
        "distance": route.distance,
        "duration": route.duration,
        "status": route.status,
        "issue": issue,
    }
    payload.update(extra)
    return payload


class NodeRouteAuditService:
    """Read-only audit for the logistics graph data foundation."""

    def __init__(self, sample_limit: int = 20):
        self.sample_limit = max(1, int(sample_limit or 20))

    def audit(self) -> Dict[str, Any]:
        nodes = Node.query.all()
        routes = Route.query.all()
        node_map = {node.id: node for node in nodes}

        node_audit = self._audit_nodes(nodes)
        route_audit = self._audit_routes(routes, node_map)
        shipment_audit = self._audit_shipment_facts(nodes)

        summary = {
            "nodes_total": len(nodes),
            "nodes_active": sum(1 for node in nodes if node.status == "active"),
            "node_issue_count": node_audit["issue_count"],
            "routes_total": len(routes),
            "routes_active": sum(1 for route in routes if route.status == "active"),
            "route_issue_count": route_audit["issue_count"],
            "shipment_fact_total": shipment_audit["summary"]["total"],
            "shipment_fact_coordinate_issue_count": shipment_audit["summary"]["coordinate_issue_count"],
        }

        return {
            "success": True,
            "data_source": "postgresql_nodes_routes_shipment_facts",
            "distance_source": "haversine_geodesic_audit",
            "path_source": "route_table_edges",
            "authenticity_level": "B",
            "fallback_reason": None,
            "summary": summary,
            "nodes": node_audit,
            "routes": route_audit,
            "shipment_facts": shipment_audit,
            "recommendations": self._recommendations(node_audit, route_audit, shipment_audit),
        }

    def _audit_nodes(self, nodes: Iterable[Node]) -> Dict[str, Any]:
        issues = {
            "missing_coordinates": [],
            "invalid_coordinates": [],
            "zero_coordinates": [],
            "outside_china_bounds": [],
            "suspected_lng_lat_swapped": [],
            "duplicate_coordinates": [],
        }
        counts = {key: 0 for key in issues}
        duplicate_groups: Dict[Tuple[float, float], List[Node]] = defaultdict(list)

        for node in nodes:
            lng = _as_float(node.longitude)
            lat = _as_float(node.latitude)

            if lng is None or lat is None:
                self._record_issue(issues, counts, "missing_coordinates", _node_payload(node, "missing_coordinates"))
                continue

            if abs(lng) < 0.000001 and abs(lat) < 0.000001:
                self._record_issue(issues, counts, "zero_coordinates", _node_payload(node, "zero_coordinates"))
                continue

            lng_world_ok = _in_range(lng, WORLD_LNG_RANGE)
            lat_world_ok = _in_range(lat, WORLD_LAT_RANGE)
            if not lng_world_ok or not lat_world_ok:
                swapped = (
                    _in_range(lat, CHINA_LNG_RANGE)
                    and _in_range(lng, CHINA_LAT_RANGE)
                    and _in_range(lng, WORLD_LAT_RANGE)
                )
                bucket = "suspected_lng_lat_swapped" if swapped else "invalid_coordinates"
                self._record_issue(issues, counts, bucket, _node_payload(node, bucket))
                continue

            if _in_range(lat, CHINA_LNG_RANGE) and _in_range(lng, CHINA_LAT_RANGE):
                self._record_issue(
                    issues,
                    counts,
                    "suspected_lng_lat_swapped",
                    _node_payload(node, "suspected_lng_lat_swapped"),
                )
                continue

            if not (_in_range(lng, CHINA_LNG_RANGE) and _in_range(lat, CHINA_LAT_RANGE)):
                self._record_issue(issues, counts, "outside_china_bounds", _node_payload(node, "outside_china_bounds"))

            duplicate_groups[(round(lng, 5), round(lat, 5))].append(node)

        for (lng, lat), group in duplicate_groups.items():
            if len(group) <= 1:
                continue
            self._record_issue(
                issues,
                counts,
                "duplicate_coordinates",
                {
                    "longitude": lng,
                    "latitude": lat,
                    "count": len(group),
                    "nodes": [
                        {"id": node.id, "name": node.name, "city": node.city, "status": node.status}
                        for node in group[: self.sample_limit]
                    ],
                    "issue": "duplicate_coordinates",
                },
            )

        return {
            "summary": counts,
            "issue_count": sum(counts.values()),
            "samples": issues,
        }

    def _audit_routes(self, routes: Iterable[Route], node_map: Dict[int, Node]) -> Dict[str, Any]:
        issues = {
            "missing_endpoint_ids": [],
            "dangling_node_reference": [],
            "same_endpoint": [],
            "endpoint_missing_coordinates": [],
            "missing_distance": [],
            "nonpositive_distance": [],
            "distance_shorter_than_geodesic": [],
            "distance_too_large_vs_geodesic": [],
            "duration_speed_anomaly": [],
        }
        counts = {key: 0 for key in issues}
        distance_source_summary: Dict[str, int] = {}

        for route in routes:
            source = self._route_distance_source(route)
            distance_source_summary[source] = distance_source_summary.get(source, 0) + 1

            start_id = route.start_node_id
            end_id = route.end_node_id
            if not start_id or not end_id:
                self._record_issue(issues, counts, "missing_endpoint_ids", _route_payload(route, "missing_endpoint_ids"))
                continue

            if start_id == end_id:
                self._record_issue(issues, counts, "same_endpoint", _route_payload(route, "same_endpoint"))

            start = node_map.get(start_id)
            end = node_map.get(end_id)
            if not start or not end:
                self._record_issue(
                    issues,
                    counts,
                    "dangling_node_reference",
                    _route_payload(
                        route,
                        "dangling_node_reference",
                        missing_start=not bool(start),
                        missing_end=not bool(end),
                    ),
                )
                continue

            start_lng, start_lat = _as_float(start.longitude), _as_float(start.latitude)
            end_lng, end_lat = _as_float(end.longitude), _as_float(end.latitude)
            if None in (start_lng, start_lat, end_lng, end_lat):
                self._record_issue(
                    issues,
                    counts,
                    "endpoint_missing_coordinates",
                    _route_payload(
                        route,
                        "endpoint_missing_coordinates",
                        start_node=start.name,
                        end_node=end.name,
                    ),
                )
                continue

            distance = _as_float(route.distance)
            if distance is None:
                self._record_issue(issues, counts, "missing_distance", _route_payload(route, "missing_distance"))
                continue
            if distance <= 0:
                self._record_issue(issues, counts, "nonpositive_distance", _route_payload(route, "nonpositive_distance"))
                continue

            geodesic_km = _haversine_km(start_lng, start_lat, end_lng, end_lat)
            if geodesic_km > 0.2:
                ratio = distance / geodesic_km
                payload_extra = {
                    "geodesic_km": round(geodesic_km, 2),
                    "distance_to_geodesic_ratio": round(ratio, 3),
                    "start_node": start.name,
                    "end_node": end.name,
                }
                if ratio < 0.85:
                    self._record_issue(
                        issues,
                        counts,
                        "distance_shorter_than_geodesic",
                        _route_payload(route, "distance_shorter_than_geodesic", **payload_extra),
                    )
                elif ratio > 5.0 and distance - geodesic_km > 30:
                    self._record_issue(
                        issues,
                        counts,
                        "distance_too_large_vs_geodesic",
                        _route_payload(route, "distance_too_large_vs_geodesic", **payload_extra),
                    )
            elif distance > 10:
                self._record_issue(
                    issues,
                    counts,
                    "distance_too_large_vs_geodesic",
                    _route_payload(
                        route,
                        "distance_too_large_vs_geodesic",
                        geodesic_km=round(geodesic_km, 2),
                        distance_to_geodesic_ratio=None,
                        start_node=start.name,
                        end_node=end.name,
                    ),
                )

            duration = _as_float(route.duration)
            if duration and duration > 0 and distance > 0:
                speed_kmh = distance / duration
                if speed_kmh < 5 or speed_kmh > 140:
                    self._record_issue(
                        issues,
                        counts,
                        "duration_speed_anomaly",
                        _route_payload(
                            route,
                            "duration_speed_anomaly",
                            speed_kmh=round(speed_kmh, 2),
                            start_node=start.name,
                            end_node=end.name,
                        ),
                    )

        return {
            "summary": counts,
            "issue_count": sum(counts.values()),
            "distance_source_summary": distance_source_summary,
            "samples": issues,
        }

    def _audit_shipment_facts(self, nodes: Iterable[Node]) -> Dict[str, Any]:
        total = ShipmentFact.query.count()
        if total == 0:
            return {
                "summary": {
                    "total": 0,
                    "coordinate_issue_count": 0,
                    "missing_any_coordinates": 0,
                    "outside_china_bounds": 0,
                    "origin_cities": 0,
                    "destination_cities": 0,
                    "origin_cities_without_nodes": 0,
                    "destination_cities_without_nodes": 0,
                },
                "samples": {
                    "origin_cities_without_nodes": [],
                    "destination_cities_without_nodes": [],
                },
            }

        missing_any = ShipmentFact.query.filter(
            (ShipmentFact.origin_lat.is_(None))
            | (ShipmentFact.origin_lng.is_(None))
            | (ShipmentFact.destination_lat.is_(None))
            | (ShipmentFact.destination_lng.is_(None))
        ).count()

        out_of_bounds = ShipmentFact.query.filter(
            (ShipmentFact.origin_lng < CHINA_LNG_RANGE[0])
            | (ShipmentFact.origin_lng > CHINA_LNG_RANGE[1])
            | (ShipmentFact.origin_lat < CHINA_LAT_RANGE[0])
            | (ShipmentFact.origin_lat > CHINA_LAT_RANGE[1])
            | (ShipmentFact.destination_lng < CHINA_LNG_RANGE[0])
            | (ShipmentFact.destination_lng > CHINA_LNG_RANGE[1])
            | (ShipmentFact.destination_lat < CHINA_LAT_RANGE[0])
            | (ShipmentFact.destination_lat > CHINA_LAT_RANGE[1])
        ).count()

        origin_cities = self._distinct_values(ShipmentFact.origin_city_std)
        destination_cities = self._distinct_values(ShipmentFact.destination_city_std)
        node_cities = {self._norm_city(node.city) for node in nodes if self._norm_city(node.city)}
        node_names = {self._norm_city(node.name) for node in nodes if self._norm_city(node.name)}
        known_places = node_cities | node_names

        origin_without_nodes = sorted(city for city in origin_cities if self._norm_city(city) not in known_places)
        dest_without_nodes = sorted(city for city in destination_cities if self._norm_city(city) not in known_places)

        return {
            "summary": {
                "total": total,
                "coordinate_issue_count": missing_any + out_of_bounds,
                "missing_any_coordinates": missing_any,
                "outside_china_bounds": out_of_bounds,
                "origin_cities": len(origin_cities),
                "destination_cities": len(destination_cities),
                "origin_cities_without_nodes": len(origin_without_nodes),
                "destination_cities_without_nodes": len(dest_without_nodes),
            },
            "samples": {
                "origin_cities_without_nodes": origin_without_nodes[: self.sample_limit],
                "destination_cities_without_nodes": dest_without_nodes[: self.sample_limit],
                "top_origin_cities": self._top_city_counts(ShipmentFact.origin_city_std),
                "top_destination_cities": self._top_city_counts(ShipmentFact.destination_city_std),
            },
        }

    def _distinct_values(self, column) -> List[str]:
        rows = (
            ShipmentFact.query.with_entities(column)
            .filter(column.isnot(None))
            .distinct()
            .all()
        )
        return [row[0] for row in rows if row[0]]

    def _top_city_counts(self, column) -> List[Dict[str, Any]]:
        rows = (
            ShipmentFact.query.with_entities(column, func.count())
            .filter(column.isnot(None))
            .group_by(column)
            .order_by(func.count().desc())
            .limit(self.sample_limit)
            .all()
        )
        return [{"city": row[0], "count": int(row[1])} for row in rows]

    def _append_sample(self, target: List[Dict[str, Any]], payload: Dict[str, Any]) -> None:
        if len(target) < self.sample_limit:
            target.append(payload)

    @staticmethod
    def _route_distance_source(route: Route) -> str:
        if route.distance is None:
            return "missing_distance"
        if route.route_data:
            try:
                payload = json.loads(route.route_data)
                if isinstance(payload, dict):
                    return payload.get("distance_source") or payload.get("distance_backfill", {}).get("distance_source") or "route_table_legacy_unknown"
            except (TypeError, ValueError):
                return "route_table_legacy_non_json"
        return "route_table_legacy_unknown"

    def _record_issue(
        self,
        samples: Dict[str, List[Dict[str, Any]]],
        counts: Dict[str, int],
        key: str,
        payload: Dict[str, Any],
    ) -> None:
        counts[key] += 1
        self._append_sample(samples[key], payload)

    @staticmethod
    def _norm_city(value: Optional[str]) -> Optional[str]:
        if not value:
            return None
        text = str(value).strip()
        for token in ["市", "特别行政区", "物流节点", "（由真实运单网络自动生成）", "(由真实运单网络自动生成)"]:
            text = text.replace(token, "")
        return text.strip() or None

    @staticmethod
    def _recommendations(node_audit: Dict[str, Any], route_audit: Dict[str, Any], shipment_audit: Dict[str, Any]) -> List[str]:
        recommendations = []
        node_summary = node_audit["summary"]
        route_summary = route_audit["summary"]
        shipment_summary = shipment_audit["summary"]

        if node_summary["missing_coordinates"] or node_summary["invalid_coordinates"]:
            recommendations.append("先修复缺失或非法 Node 坐标，再评估高德/天地图 provider 是否真实降级。")
        if node_summary["suspected_lng_lat_swapped"]:
            recommendations.append("存在疑似经纬度反写节点，应先人工确认后批量纠正。")
        if route_summary["dangling_node_reference"] or route_summary["endpoint_missing_coordinates"]:
            recommendations.append("Route 存在悬空端点或端点缺坐标，本地路径算法需要先剔除这些边。")
        if route_summary["distance_shorter_than_geodesic"] or route_summary["distance_too_large_vs_geodesic"]:
            recommendations.append("Route 距离与节点直线距离偏差异常，建议用高德/天地图批量重算并保留 distance_source。")
        if shipment_summary["origin_cities_without_nodes"] or shipment_summary["destination_cities_without_nodes"]:
            recommendations.append("真实 shipment_facts 城市覆盖超过当前 Node 网络，应补充运营节点映射表。")
        if not recommendations:
            recommendations.append("Node/Route 坐标底座未发现阻断级问题，可进入 provider 对比和本地路径算法增强。")

        return recommendations


def audit_node_route_coordinates(sample_limit: int = 20) -> Dict[str, Any]:
    return NodeRouteAuditService(sample_limit=sample_limit).audit()
