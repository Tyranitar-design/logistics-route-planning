#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Local route algorithm benchmark service.

The service compares multiple local graph-search strategies against an optional
road-network provider route. It keeps truth metadata explicit so callers can
separate local graph estimates from provider road-network distances.
"""

from __future__ import annotations

import json
import math
from typing import Any, Dict, Iterable, List, Optional, Tuple

from app.models import Node, Route, db
from app.services.amap_service import get_amap_service
from app.services.path_algorithm import PathAlgorithmService, PathResult
from app.services.tianditu_service import get_tianditu_service


LOCAL_STRATEGIES: Tuple[Tuple[str, str, str], ...] = (
    ("dijkstra_distance", "dijkstra", "distance"),
    ("dijkstra_time", "dijkstra", "time"),
    ("dijkstra_cost", "dijkstra", "cost"),
    ("dijkstra_comprehensive", "dijkstra", "comprehensive"),
    ("astar_distance", "a_star", "distance"),
    ("astar_time", "a_star", "time"),
    ("astar_cost", "a_star", "cost"),
)

DEFAULT_PROVIDER_SOURCES: Tuple[str, ...] = ("amap",)
SUPPORTED_PROVIDER_SOURCES = {"amap", "tianditu"}


def _finite_number(value: Any) -> Optional[float]:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(numeric):
        return None
    return numeric


def _ratio(delta: Optional[float], baseline: Optional[float]) -> Optional[float]:
    if delta is None or baseline is None or baseline <= 0:
        return None
    return round(delta / baseline, 6)


def _node_payload(node: Node) -> Dict[str, Any]:
    payload = node.to_dict()
    payload.setdefault("node_name", payload.get("name"))
    return payload


def _provider_status_from_candidate(candidate: Optional[Dict[str, Any]], fallback_reason: Optional[str]) -> str:
    if candidate and candidate.get("provider_status"):
        return str(candidate["provider_status"])
    if candidate:
        return "ok"
    if fallback_reason:
        return "degraded"
    return "unknown"


def _normalize_provider_sources(provider_sources: Optional[Iterable[Any]]) -> List[str]:
    sources: List[str] = []
    for source in provider_sources or DEFAULT_PROVIDER_SOURCES:
        normalized = str(source).strip().lower()
        if normalized in SUPPORTED_PROVIDER_SOURCES and normalized not in sources:
            sources.append(normalized)
    return sources or list(DEFAULT_PROVIDER_SOURCES)


def _load_route_data(value: Optional[str]) -> Dict[str, Any]:
    if not value:
        return {}
    try:
        payload = json.loads(value)
        return payload if isinstance(payload, dict) else {"legacy_route_data": payload}
    except (TypeError, ValueError):
        return {"legacy_route_data": value}


def _increment_count(counts: Dict[str, int], key: Optional[str], fallback: str) -> None:
    normalized = str(key or fallback)
    counts[normalized] = counts.get(normalized, 0) + 1


class LocalRouteBenchmarkService:
    """Builds explainable local-vs-provider route benchmark payloads."""

    def __init__(self, path_service: Optional[PathAlgorithmService] = None):
        # Use a fresh graph by default so tests and runtime audits see current DB rows.
        self.path_service = path_service or PathAlgorithmService()

    def benchmark(
        self,
        origin_id: int,
        destination_id: int,
        *,
        include_provider: bool = True,
        strategy: int | str = 0,
        provider_sources: Optional[Iterable[Any]] = None,
    ) -> Dict[str, Any]:
        origin = db.session.get(Node, origin_id)
        destination = db.session.get(Node, destination_id)
        requested_providers = _normalize_provider_sources(provider_sources) if include_provider else []
        diagnostics: Dict[str, Any] = {
            "requested_origin_id": origin_id,
            "requested_destination_id": destination_id,
            "include_provider": include_provider,
            "provider_strategy": strategy,
            "requested_provider_sources": requested_providers,
            "node_count": Node.query.count(),
            "active_route_count": Route.query.filter_by(status="active").count(),
        }

        validation_error = self._validate_nodes(origin, destination)
        if validation_error:
            return {
                "success": False,
                "error": validation_error,
                "origin": _node_payload(origin) if origin else None,
                "destination": _node_payload(destination) if destination else None,
                "provider_route": None,
                "provider_routes": [],
                "provider_errors": {},
                "local_strategies": [],
                "summary": {
                    "local_strategy_count": 0,
                    "successful_local_strategies": 0,
                    "best_local_strategy": None,
                    "provider_count": len(requested_providers),
                    "provider_available_count": 0,
                },
                "diagnostics": diagnostics,
                "data_source": "nodes/routes",
                "distance_source": self._distance_source_label(requested_providers),
                "path_source": "local_route_graph_vs_provider_polyline",
                "provider_status": "failed",
                "fallback_reason": validation_error,
                "authenticity_level": "C-invalid-input",
            }

        assert origin is not None and destination is not None
        provider_errors: Dict[str, str] = {}
        provider_results: Dict[str, Dict[str, Any]] = {}
        if include_provider:
            provider_results, provider_errors = self._provider_routes(
                origin,
                destination,
                strategy,
                requested_providers,
            )
        provider_route = self._primary_provider_route(provider_results, requested_providers)
        provider_route_list = [
            provider_results[source]
            for source in requested_providers
            if source in provider_results
        ]

        local_strategies = [
            self._run_local_strategy(origin_id, destination_id, strategy_id, algorithm, optimize_by)
            for strategy_id, algorithm, optimize_by in LOCAL_STRATEGIES
        ]
        for candidate in local_strategies:
            self._attach_local_route_truth(candidate)
            self._attach_provider_deltas(candidate, provider_results, provider_route)

        successful_local = [candidate for candidate in local_strategies if candidate.get("success")]
        summary = self._summary(local_strategies, provider_route, provider_results, requested_providers)
        summary["local_distance_source_counts"] = self._aggregate_local_truth_counts(
            successful_local,
            "distance_source_counts",
        )
        summary["local_provider_status_counts"] = self._aggregate_local_truth_counts(
            successful_local,
            "provider_status_counts",
        )
        provider_status = self._overall_provider_status(provider_results, provider_errors, requested_providers)
        success = bool(successful_local or provider_route)
        fallback_reason = self._fallback_reason(
            successful_local,
            provider_route,
            provider_errors,
            requested_providers,
            include_provider,
        )

        diagnostics.update(
            {
                "provider_errors": provider_errors,
                "provider_route_available": bool(provider_route),
                "provider_available_sources": list(provider_results.keys()),
                "local_success_count": len(successful_local),
                "local_failure_count": len(local_strategies) - len(successful_local),
                "local_strategy_ids": [candidate["strategy_id"] for candidate in local_strategies],
            }
        )

        return {
            "success": success,
            "origin": _node_payload(origin),
            "destination": _node_payload(destination),
            "provider_route": provider_route,
            "provider_routes": provider_route_list,
            "provider_errors": provider_errors,
            "local_strategies": local_strategies,
            "summary": summary,
            "diagnostics": diagnostics,
            "data_source": "nodes/routes",
            "distance_source": self._distance_source_label(requested_providers) if provider_route else "local_graph_only",
            "path_source": "local_route_graph_vs_provider_polyline" if provider_route else "local_route_graph",
            "provider_status": provider_status if success else "failed",
            "fallback_reason": fallback_reason,
            "authenticity_level": "B/C-comparative-benchmark" if provider_route else "C-local-graph-benchmark",
        }

    def _validate_nodes(self, origin: Optional[Node], destination: Optional[Node]) -> Optional[str]:
        if not origin:
            return "ORIGIN_NODE_NOT_FOUND"
        if not destination:
            return "DESTINATION_NODE_NOT_FOUND"
        if origin.longitude is None or origin.latitude is None:
            return "ORIGIN_COORDINATES_MISSING"
        if destination.longitude is None or destination.latitude is None:
            return "DESTINATION_COORDINATES_MISSING"
        return None

    def _provider_routes(
        self,
        origin: Node,
        destination: Node,
        strategy: int | str,
        provider_sources: Iterable[str],
    ) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, str]]:
        routes: Dict[str, Dict[str, Any]] = {}
        errors: Dict[str, str] = {}

        for source in provider_sources:
            if source == "tianditu":
                route, error = self._tianditu_provider_route(origin, destination, strategy)
            else:
                route, error = self._amap_provider_route(origin, destination, strategy)

            if route:
                routes[source] = route
            if error:
                errors[source] = error

        return routes, errors

    def _amap_provider_route(
        self,
        origin: Node,
        destination: Node,
        strategy: int | str,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        try:
            result = get_amap_service().multi_route(
                (origin.longitude, origin.latitude),
                (destination.longitude, destination.latitude),
            )
        except Exception as exc:  # pragma: no cover - exact provider failures vary by environment.
            return None, f"AMAP_PROVIDER_EXCEPTION: {exc}"

        if not result or not result.get("success"):
            reason = (result or {}).get("fallback_reason") or (result or {}).get("error") or "AMAP_ROUTE_UNAVAILABLE"
            return None, reason

        routes = result.get("routes") or []
        if not routes:
            return None, result.get("fallback_reason") or "AMAP_ROUTE_EMPTY"

        route = dict(routes[0])
        distance_km = _finite_number(route.get("distance_km"))
        distance_m = _finite_number(route.get("distance"))
        if distance_km is None and distance_m is not None:
            distance_km = round(distance_m / 1000, 3)

        duration_minutes = _finite_number(route.get("duration_minutes"))
        duration_seconds = _finite_number(route.get("duration"))
        if duration_minutes is None and duration_seconds is not None:
            duration_minutes = round(duration_seconds / 60, 3)

        degraded = bool(route.get("degraded", result.get("degraded", False)))
        provider_status = route.get("provider_status") or result.get("provider_status") or ("degraded" if degraded else "ok")
        fallback_reason = route.get("fallback_reason") or result.get("fallback_reason")

        route.update(
            {
                "success": True,
                "source": "amap",
                "provider": route.get("provider") or result.get("provider") or "amap",
                "provider_status": provider_status,
                "degraded": degraded,
                "fallback_reason": fallback_reason,
                "distance_km": distance_km,
                "duration_minutes": duration_minutes,
                "distance_source": "amap" if provider_status == "ok" and not degraded else "amap_fallback_estimate",
                "path_source": "amap_polyline" if route.get("polyline") else "amap_route_summary",
                "data_source": "nodes",
                "authenticity_level": "B-road-provider" if provider_status == "ok" and not degraded else "C-provider-fallback",
                "strategy": route.get("strategy") or strategy,
            }
        )
        return route, fallback_reason

    def _tianditu_provider_route(
        self,
        origin: Node,
        destination: Node,
        strategy: int | str,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        try:
            result = get_tianditu_service().get_route_for_frontend(
                (origin.longitude, origin.latitude),
                (destination.longitude, destination.latitude),
                str(strategy),
            )
        except Exception as exc:  # pragma: no cover - exact provider failures vary by environment.
            return None, f"TIANDITU_PROVIDER_EXCEPTION: {exc}"

        if not result or not result.get("success"):
            reason = (
                (result or {}).get("fallback_reason")
                or (result or {}).get("error")
                or "TIANDITU_ROUTE_UNAVAILABLE"
            )
            return None, reason

        route = dict(result)
        distance_km = _finite_number(route.get("distance_km") or route.get("distance"))
        duration_minutes = _finite_number(route.get("duration_minutes"))
        duration_seconds = _finite_number(route.get("duration"))
        if duration_minutes is None and duration_seconds is not None:
            duration_minutes = round(duration_seconds / 60, 3)

        degraded = bool(route.get("degraded", False))
        provider_status = route.get("provider_status") or ("degraded" if degraded else "ok")
        fallback_reason = route.get("fallback_reason") or route.get("error")

        route.update(
            {
                "success": True,
                "source": "tianditu",
                "provider": route.get("provider") or "tianditu",
                "provider_status": provider_status,
                "degraded": degraded,
                "fallback_reason": fallback_reason,
                "distance_km": distance_km,
                "duration_minutes": duration_minutes,
                "distance_source": "tianditu" if provider_status == "ok" and not degraded else "tianditu_fallback_estimate",
                "path_source": "tianditu_polyline" if route.get("polyline") else "tianditu_route_summary",
                "data_source": "nodes",
                "authenticity_level": "B-road-provider" if provider_status == "ok" and not degraded else "C-provider-fallback",
                "strategy": route.get("strategy") or strategy,
            }
        )
        return route, fallback_reason

    def _run_local_strategy(
        self,
        origin_id: int,
        destination_id: int,
        strategy_id: str,
        algorithm: str,
        optimize_by: str,
    ) -> Dict[str, Any]:
        try:
            if algorithm == "a_star":
                result = self.path_service.a_star(origin_id, destination_id, optimize_by)
            else:
                result = self.path_service.dijkstra(origin_id, destination_id, optimize_by)
        except Exception as exc:
            result = PathResult(
                success=False,
                path=[],
                total_distance=0,
                total_time=0,
                total_cost=0,
                algorithm="A*" if algorithm == "a_star" else "Dijkstra",
                optimize_by=optimize_by,
                visited_nodes=0,
                computation_time=0,
                error=str(exc),
            )

        duration_minutes = round(result.total_time * 60, 3) if result.success else None
        candidate: Dict[str, Any] = {
            "success": bool(result.success),
            "strategy_id": strategy_id,
            "source": "local_graph",
            "provider": "local",
            "algorithm": result.algorithm,
            "optimize_by": result.optimize_by,
            "distance_km": result.total_distance if result.success else None,
            "duration_minutes": duration_minutes,
            "cost": result.total_cost if result.success else None,
            "path": result.path,
            "visited_nodes": result.visited_nodes,
            "computation_time": result.computation_time,
            "error": result.error,
            "data_source": "nodes/routes",
            "distance_source": "local_graph",
            "path_source": "local_route_graph",
            "provider_status": "ok" if result.success else "failed",
            "fallback_reason": None if result.success else result.error or "LOCAL_ROUTE_FAILED",
            "authenticity_level": "C-local-graph",
            "authenticity": {
                "mode": "approximate",
                "level": "C",
                "is_strict": False,
                "allow_fallback": True,
                "has_real_distance": False,
                "has_real_duration": False,
                "used_fallback": False,
                "used_simulation": False,
                "distance_source": "local_graph",
                "duration_source": "local_graph",
                "exact_ratio": 0.0,
                "approx_ratio": 1.0,
                "message": "Local graph route is an explainability and fallback baseline, not a road-provider truth source.",
            },
        }
        return candidate

    def _attach_local_route_truth(self, local_candidate: Dict[str, Any]) -> None:
        if not local_candidate.get("success"):
            local_candidate["route_segments"] = []
            local_candidate["route_truth"] = {
                "segment_count": 0,
                "missing_segment_count": 0,
                "distance_source_counts": {},
                "duration_source_counts": {},
                "provider_status_counts": {},
                "authenticity_level": "C-local-route-failed",
            }
            return

        path = local_candidate.get("path") or []
        node_ids = [item.get("id") for item in path if isinstance(item, dict) and item.get("id") is not None]
        segments: List[Dict[str, Any]] = []
        distance_source_counts: Dict[str, int] = {}
        duration_source_counts: Dict[str, int] = {}
        provider_status_counts: Dict[str, int] = {}
        route_ids: List[int] = []
        missing_segment_count = 0

        for index, (start_id, end_id) in enumerate(zip(node_ids, node_ids[1:])):
            route = self._find_route_segment(int(start_id), int(end_id))
            if not route:
                missing_segment_count += 1
                segment = {
                    "sequence": index,
                    "from_node_id": start_id,
                    "to_node_id": end_id,
                    "route_id": None,
                    "distance_source": "route_segment_missing",
                    "duration_source": "route_segment_missing",
                    "provider_status": "degraded",
                    "fallback_reason": "ROUTE_SEGMENT_NOT_FOUND",
                }
                _increment_count(distance_source_counts, segment["distance_source"], "route_segment_missing")
                _increment_count(duration_source_counts, segment["duration_source"], "route_segment_missing")
                _increment_count(provider_status_counts, segment["provider_status"], "degraded")
                segments.append(segment)
                continue

            route_ids.append(route.id)
            route_data = _load_route_data(route.route_data)
            backfill = route_data.get("distance_backfill") if isinstance(route_data.get("distance_backfill"), dict) else {}
            distance_source = route_data.get("distance_source") or backfill.get("distance_source") or "route_table_legacy_unknown"
            duration_source = route_data.get("duration_source") or backfill.get("duration_source") or "route_table_legacy_unknown"
            provider_status = route_data.get("provider_status") or backfill.get("provider_status") or "unknown"
            fallback_reason = route_data.get("fallback_reason") or backfill.get("fallback_reason")
            segment = {
                "sequence": index,
                "from_node_id": start_id,
                "to_node_id": end_id,
                "route_id": route.id,
                "route_name": route.name,
                "distance_km": route.distance,
                "duration_hours": route.duration,
                "distance_source": distance_source,
                "duration_source": duration_source,
                "provider": route_data.get("provider") or backfill.get("provider"),
                "provider_status": provider_status,
                "fallback_reason": fallback_reason,
            }
            _increment_count(distance_source_counts, distance_source, "route_table_legacy_unknown")
            _increment_count(duration_source_counts, duration_source, "route_table_legacy_unknown")
            _increment_count(provider_status_counts, provider_status, "unknown")
            segments.append(segment)

        local_candidate["route_segments"] = segments
        local_candidate["route_truth"] = {
            "segment_count": len(segments),
            "missing_segment_count": missing_segment_count,
            "route_ids": route_ids,
            "distance_source_counts": distance_source_counts,
            "duration_source_counts": duration_source_counts,
            "provider_status_counts": provider_status_counts,
            "authenticity_level": self._local_route_authenticity_level(distance_source_counts, missing_segment_count),
        }

    def attach_local_route_truth(self, local_candidate: Dict[str, Any]) -> Dict[str, Any]:
        """Attach route-table provenance to a local graph candidate and return it."""
        self._attach_local_route_truth(local_candidate)
        return local_candidate

    def _find_route_segment(self, start_id: int, end_id: int) -> Optional[Route]:
        routes = Route.query.filter(
            Route.status == "active",
            (
                ((Route.start_node_id == start_id) & (Route.end_node_id == end_id))
                | ((Route.start_node_id == end_id) & (Route.end_node_id == start_id))
            ),
        ).all()
        if not routes:
            return None
        return min(
            routes,
            key=lambda route: (
                route.distance is None,
                route.distance if route.distance is not None else float("inf"),
                route.id,
            ),
        )

    def _local_route_authenticity_level(self, distance_source_counts: Dict[str, int], missing_segments: int) -> str:
        if missing_segments:
            return "C-local-graph-incomplete"
        if not distance_source_counts:
            return "C-local-graph"
        exact_sources = {"amap_driving_route", "tianditu", "cache", "precise_distance_provider"}
        if all(source in exact_sources for source in distance_source_counts):
            return "B-local-graph-real-distance"
        if any(source in exact_sources for source in distance_source_counts):
            return "B/C-local-graph-mixed-distance"
        return "C-local-graph-estimated-distance"

    def _aggregate_local_truth_counts(
        self,
        local_candidates: Iterable[Dict[str, Any]],
        field: str,
    ) -> Dict[str, int]:
        aggregate: Dict[str, int] = {}
        for candidate in local_candidates:
            route_truth = candidate.get("route_truth") or {}
            counts = route_truth.get(field) or {}
            for key, value in counts.items():
                aggregate[str(key)] = aggregate.get(str(key), 0) + int(value or 0)
        return aggregate

    def _attach_provider_deltas(
        self,
        local_candidate: Dict[str, Any],
        provider_candidates: Dict[str, Dict[str, Any]],
        primary_provider: Optional[Dict[str, Any]],
    ) -> None:
        comparisons: Dict[str, Dict[str, Any]] = {}
        for provider, provider_candidate in provider_candidates.items():
            comparisons[provider] = self._provider_delta(local_candidate, provider_candidate)

        local_candidate["comparison_to_providers"] = comparisons

        if not local_candidate.get("success") or not primary_provider:
            local_candidate["comparison_to_provider"] = {
                "comparable": False,
                "fallback_reason": "LOCAL_OR_PROVIDER_ROUTE_MISSING",
            }
            return

        local_candidate["comparison_to_provider"] = self._provider_delta(local_candidate, primary_provider)

    def _provider_delta(
        self,
        local_candidate: Dict[str, Any],
        provider_candidate: Dict[str, Any],
    ) -> Dict[str, Any]:
        if not local_candidate.get("success"):
            return {
                "comparable": False,
                "provider": provider_candidate.get("provider") or "road_provider",
                "fallback_reason": "LOCAL_ROUTE_MISSING",
            }

        local_distance = _finite_number(local_candidate.get("distance_km"))
        provider_distance = _finite_number(provider_candidate.get("distance_km"))
        local_duration = _finite_number(local_candidate.get("duration_minutes"))
        provider_duration = _finite_number(provider_candidate.get("duration_minutes"))
        distance_delta = (
            round(local_distance - provider_distance, 3)
            if local_distance is not None and provider_distance is not None
            else None
        )
        duration_delta = (
            round(local_duration - provider_duration, 3)
            if local_duration is not None and provider_duration is not None
            else None
        )

        return {
            "comparable": distance_delta is not None or duration_delta is not None,
            "provider": provider_candidate.get("provider") or "road_provider",
            "provider_distance_km": provider_distance,
            "provider_duration_minutes": provider_duration,
            "distance_delta_km": distance_delta,
            "distance_delta_ratio": _ratio(distance_delta, provider_distance),
            "duration_delta_minutes": duration_delta,
            "duration_delta_ratio": _ratio(duration_delta, provider_duration),
        }

    def _summary(
        self,
        local_strategies: Iterable[Dict[str, Any]],
        provider_candidate: Optional[Dict[str, Any]],
        provider_candidates: Dict[str, Dict[str, Any]],
        requested_providers: Iterable[str],
    ) -> Dict[str, Any]:
        strategies = list(local_strategies)
        successful = [candidate for candidate in strategies if candidate.get("success")]
        best_distance = self._min_candidate(successful, "distance_km")
        best_duration = self._min_candidate(successful, "duration_minutes")
        best_cost = self._min_candidate(successful, "cost")
        best_for_delta = self._min_abs_delta(successful)

        return {
            "local_strategy_count": len(strategies),
            "successful_local_strategies": len(successful),
            "failed_local_strategies": len(strategies) - len(successful),
            "best_local_strategy": best_distance.get("strategy_id") if best_distance else None,
            "best_distance_strategy": best_distance.get("strategy_id") if best_distance else None,
            "best_duration_strategy": best_duration.get("strategy_id") if best_duration else None,
            "best_cost_strategy": best_cost.get("strategy_id") if best_cost else None,
            "closest_to_provider_strategy": best_for_delta.get("strategy_id") if best_for_delta else None,
            "provider_available": bool(provider_candidate),
            "primary_provider": provider_candidate.get("provider") if provider_candidate else None,
            "provider_count": len(list(requested_providers)),
            "provider_available_count": len(provider_candidates),
            "provider_available_sources": list(provider_candidates.keys()),
            "provider_distance_km": provider_candidate.get("distance_km") if provider_candidate else None,
            "provider_duration_minutes": provider_candidate.get("duration_minutes") if provider_candidate else None,
        }

    def _min_candidate(self, candidates: List[Dict[str, Any]], field: str) -> Optional[Dict[str, Any]]:
        ranked = [
            (value, candidate)
            for candidate in candidates
            for value in [_finite_number(candidate.get(field))]
            if value is not None
        ]
        if not ranked:
            return None
        return min(ranked, key=lambda item: item[0])[1]

    def _min_abs_delta(self, candidates: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        ranked = []
        for candidate in candidates:
            comparison = candidate.get("comparison_to_provider") or {}
            distance_delta = _finite_number(comparison.get("distance_delta_km"))
            if distance_delta is not None:
                ranked.append((abs(distance_delta), candidate))
        if not ranked:
            return None
        return min(ranked, key=lambda item: item[0])[1]

    def _fallback_reason(
        self,
        successful_local: List[Dict[str, Any]],
        provider_candidate: Optional[Dict[str, Any]],
        provider_errors: Dict[str, str],
        requested_providers: Iterable[str],
        include_provider: bool,
    ) -> Optional[str]:
        if not successful_local:
            return "LOCAL_ROUTE_UNAVAILABLE"
        if include_provider and not provider_candidate:
            return self._format_provider_errors(provider_errors) or "PROVIDER_ROUTE_UNAVAILABLE"

        requested = list(requested_providers)
        if include_provider and provider_errors and len(provider_errors) < len(requested):
            return f"PARTIAL_PROVIDER_DEGRADATION: {self._format_provider_errors(provider_errors)}"
        return provider_candidate.get("fallback_reason") if provider_candidate else None

    def _primary_provider_route(
        self,
        provider_candidates: Dict[str, Dict[str, Any]],
        requested_providers: Iterable[str],
    ) -> Optional[Dict[str, Any]]:
        for source in requested_providers:
            candidate = provider_candidates.get(source)
            if candidate:
                return candidate
        return None

    def _overall_provider_status(
        self,
        provider_candidates: Dict[str, Dict[str, Any]],
        provider_errors: Dict[str, str],
        requested_providers: Iterable[str],
    ) -> str:
        requested = list(requested_providers)
        if not requested:
            return "unknown"
        if not provider_candidates:
            return "degraded" if provider_errors else "unknown"
        if provider_errors or len(provider_candidates) < len(requested):
            return "degraded"
        if any(candidate.get("provider_status") != "ok" or candidate.get("degraded") for candidate in provider_candidates.values()):
            return "degraded"
        return "ok"

    def _distance_source_label(self, requested_providers: Iterable[str]) -> str:
        providers = [source for source in requested_providers if source in SUPPORTED_PROVIDER_SOURCES]
        if not providers:
            return "local_graph_only"
        return f"local_graph_vs_{'_'.join(providers)}"

    def _format_provider_errors(self, provider_errors: Dict[str, str]) -> Optional[str]:
        if not provider_errors:
            return None
        return "; ".join(f"{provider}={reason}" for provider, reason in provider_errors.items())
