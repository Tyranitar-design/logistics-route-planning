"""Route-sequence solver benchmark over the real node/route graph.

This service complements the small CVRP benchmark by using the project's
``nodes`` and ``routes`` tables as the distance foundation. It compares a
bounded TSP-like visit sequence across simple heuristics and optional exact
solvers while preserving route segment provenance.
"""

from __future__ import annotations

import math
import time
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from app.models import Node
from app.services.gurobi_capability_service import (
    GurobiCapabilityService,
    get_gurobi_capability_service,
)
from app.services.local_route_benchmark_service import LocalRouteBenchmarkService
from app.services.path_algorithm import DISTANCE_CORRECTION_FACTOR, DEFAULT_AVG_SPEED_KMH, PathAlgorithmService


DEFAULT_SEQUENCE_SOLVERS: Tuple[str, ...] = ("nearest_neighbor", "two_opt", "ortools", "gurobi")
MAX_SEQUENCE_NODES = 9
EXACT_DISTANCE_SOURCES = {"amap_driving_route", "tianditu", "cache", "precise_distance_provider"}


def _coerce_bool(value: Any, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def _coerce_float(value: Any, default: float) -> float:
    try:
        if value is None or value == "":
            return default
        numeric = float(value)
        return numeric if math.isfinite(numeric) else default
    except (TypeError, ValueError):
        return default


def _coerce_int(value: Any) -> Optional[int]:
    try:
        if value is None or value == "":
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def _dedupe_ints(values: Iterable[Any]) -> List[int]:
    result: List[int] = []
    for value in values:
        item = _coerce_int(value)
        if item is not None and item not in result:
            result.append(item)
    return result


def _node_payload(node: Node) -> Dict[str, Any]:
    payload = node.to_dict()
    payload.setdefault("node_name", payload.get("name"))
    return payload


def _increment_counts(target: Dict[str, int], source: Dict[str, Any]) -> None:
    for key, value in (source or {}).items():
        target[str(key)] = target.get(str(key), 0) + int(value or 0)


class RouteSequenceBenchmarkService:
    """Compare small route-sequence solvers on real ``nodes/routes`` data."""

    def __init__(
        self,
        path_service: Optional[PathAlgorithmService] = None,
        gurobi_capability_service: Optional[GurobiCapabilityService] = None,
    ):
        self.path_service = path_service
        self.gurobi_capability_service = gurobi_capability_service or get_gurobi_capability_service()

    def demo_payload(self) -> Dict[str, Any]:
        nodes = (
            Node.query.filter(
                Node.status == "active",
                Node.longitude.isnot(None),
                Node.latitude.isnot(None),
            )
            .order_by(Node.id.asc())
            .limit(5)
            .all()
        )
        if len(nodes) < 3:
            return {
                "depot_id": 1,
                "node_ids": [2, 3],
                "solvers": list(DEFAULT_SEQUENCE_SOLVERS),
                "return_to_depot": True,
                "allow_haversine_fallback": True,
                "time_limit": 5,
            }

        return {
            "depot_id": nodes[0].id,
            "node_ids": [node.id for node in nodes[1:]],
            "solvers": list(DEFAULT_SEQUENCE_SOLVERS),
            "return_to_depot": True,
            "allow_haversine_fallback": True,
            "time_limit": 5,
        }

    def benchmark(self, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        payload = self._with_demo_data_when_missing(payload or {})
        started = time.perf_counter()

        validation, depot, waypoints = self._load_nodes(payload)
        requested_solvers = self._normalise_solvers(payload.get("solvers") or DEFAULT_SEQUENCE_SOLVERS)
        return_to_depot = _coerce_bool(payload.get("return_to_depot"), True)
        allow_haversine_fallback = _coerce_bool(payload.get("allow_haversine_fallback"), True)
        time_limit = max(0.1, _coerce_float(payload.get("time_limit"), 5.0))

        if validation:
            return {
                "success": False,
                "error": validation,
                "benchmark_type": "small_route_sequence_solver_comparison",
                "data_source": "nodes/routes",
                "distance_source": "route_table_mixed_sources",
                "path_source": "node_sequence_solver",
                "provider_status": "failed",
                "fallback_reason": validation,
                "authenticity_level": "C-invalid-input",
                "summary": {
                    "requested_solvers": requested_solvers,
                    "node_count": 0,
                    "waypoint_count": 0,
                    "return_to_depot": return_to_depot,
                },
                "results": [],
                "rankings": [],
                "diagnostics": {
                    "requested_depot_id": payload.get("depot_id"),
                    "requested_node_ids": payload.get("node_ids"),
                },
            }

        assert depot is not None
        node_sequence = [depot] + waypoints
        matrix_result = self._build_distance_matrix(
            node_sequence,
            allow_haversine_fallback=allow_haversine_fallback,
        )

        rows = [
            self._run_solver(
                solver,
                matrix_result,
                return_to_depot=return_to_depot,
                time_limit=time_limit,
            )
            for solver in requested_solvers
        ]
        rankings = self._rank_rows(rows)
        elapsed = time.perf_counter() - started
        matrix_status = matrix_result["summary"]["provider_status"]
        provider_status = "ok" if matrix_status == "ok" and all(row.get("provider_status") == "ok" for row in rows) else "degraded"
        fallback_reasons = [
            reason
            for reason in [matrix_result["summary"].get("fallback_reason")]
            + [row.get("fallback_reason") for row in rows]
            if reason
        ]

        return {
            "success": any(row.get("success") and row.get("feasible") for row in rows),
            "benchmark_type": "small_route_sequence_solver_comparison",
            "data_source": "nodes/routes",
            "distance_source": matrix_result["summary"]["distance_source"],
            "path_source": "node_sequence_solver+local_route_graph",
            "provider_status": provider_status,
            "fallback_reason": ";".join(fallback_reasons) if fallback_reasons else None,
            "authenticity_level": self._overall_authenticity(matrix_result["summary"], provider_status),
            "solver": "route_sequence_benchmark",
            "origin": _node_payload(depot),
            "waypoints": [_node_payload(node) for node in waypoints],
            "distance_matrix": matrix_result["distance_matrix"],
            "duration_matrix_minutes": matrix_result["duration_matrix_minutes"],
            "matrix_truth": matrix_result["summary"],
            "results": rows,
            "rankings": rankings,
            "summary": {
                "requested_solvers": requested_solvers,
                "succeeded_solvers": [row["solver"] for row in rows if row.get("success")],
                "feasible_solvers": [row["solver"] for row in rows if row.get("success") and row.get("feasible")],
                "best_solver": rankings[0]["solver"] if rankings else None,
                "solve_time_seconds": round(elapsed, 6),
                "node_count": len(node_sequence),
                "waypoint_count": len(waypoints),
                "return_to_depot": return_to_depot,
                "allow_haversine_fallback": allow_haversine_fallback,
            },
            "diagnostics": {
                "ranking_rule": "feasible_successful_rows_sorted_by_total_distance_then_solve_time",
                "hard_constraints": [
                    "start_at_depot",
                    "visit_each_waypoint_once",
                    "return_to_depot_when_requested",
                    "finite_distance_for_each_leg",
                ],
                "bounded_node_limit": MAX_SEQUENCE_NODES,
                "requested_depot_id": depot.id,
                "requested_node_ids": [node.id for node in waypoints],
            },
        }

    def _with_demo_data_when_missing(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        if payload.get("depot_id") and payload.get("node_ids"):
            return dict(payload)
        demo = self.demo_payload()
        demo.update(payload)
        return demo

    def _load_nodes(self, payload: Dict[str, Any]) -> Tuple[Optional[str], Optional[Node], List[Node]]:
        depot_id = _coerce_int(payload.get("depot_id"))
        waypoint_ids = _dedupe_ints(payload.get("node_ids") or payload.get("waypoint_ids") or [])
        if depot_id is None:
            return "DEPOT_NODE_REQUIRED", None, []
        waypoint_ids = [node_id for node_id in waypoint_ids if node_id != depot_id]
        if not waypoint_ids:
            return "WAYPOINT_NODES_REQUIRED", None, []
        if len(waypoint_ids) + 1 > MAX_SEQUENCE_NODES:
            return "ROUTE_SEQUENCE_NODE_LIMIT_EXCEEDED", None, []

        requested_ids = [depot_id] + waypoint_ids
        nodes_by_id = {
            node.id: node
            for node in Node.query.filter(Node.id.in_(requested_ids)).all()
        }
        missing = [node_id for node_id in requested_ids if node_id not in nodes_by_id]
        if missing:
            return f"NODE_NOT_FOUND:{','.join(str(node_id) for node_id in missing)}", None, []

        coordinate_missing = [
            node_id
            for node_id in requested_ids
            if nodes_by_id[node_id].longitude is None or nodes_by_id[node_id].latitude is None
        ]
        if coordinate_missing:
            return f"NODE_COORDINATES_MISSING:{','.join(str(node_id) for node_id in coordinate_missing)}", None, []

        depot = nodes_by_id[depot_id]
        waypoints = [nodes_by_id[node_id] for node_id in waypoint_ids]
        return None, depot, waypoints

    def _build_distance_matrix(
        self,
        nodes: Sequence[Node],
        *,
        allow_haversine_fallback: bool,
    ) -> Dict[str, Any]:
        path_service = self.path_service or PathAlgorithmService(use_cache=False)
        truth_service = LocalRouteBenchmarkService(path_service=path_service)
        n = len(nodes)
        distance_matrix = [[0.0 for _ in range(n)] for _ in range(n)]
        duration_matrix = [[0.0 for _ in range(n)] for _ in range(n)]
        pairs: Dict[Tuple[int, int], Dict[str, Any]] = {}
        distance_source_counts: Dict[str, int] = {}
        duration_source_counts: Dict[str, int] = {}
        provider_status_counts: Dict[str, int] = {}
        fallback_reasons: List[str] = []
        failed_pair_count = 0
        fallback_pair_count = 0
        route_graph_pair_count = 0

        for i, origin in enumerate(nodes):
            for j, destination in enumerate(nodes):
                if i == j:
                    pairs[(i, j)] = self._same_node_pair(origin)
                    continue

                pair = self._route_graph_pair(path_service, truth_service, origin, destination)
                if not pair["success"] and allow_haversine_fallback:
                    pair = self._haversine_pair(origin, destination, pair.get("fallback_reason"))

                if pair["success"]:
                    distance_matrix[i][j] = round(float(pair["distance_km"]), 4)
                    duration_matrix[i][j] = round(float(pair["duration_minutes"]), 4)
                    if pair["distance_source"] == "haversine_corrected":
                        fallback_pair_count += 1
                    else:
                        route_graph_pair_count += 1
                else:
                    distance_matrix[i][j] = float("inf")
                    duration_matrix[i][j] = float("inf")
                    failed_pair_count += 1

                route_truth = pair.get("route_truth") or {}
                _increment_counts(distance_source_counts, route_truth.get("distance_source_counts") or {pair["distance_source"]: 1})
                _increment_counts(duration_source_counts, route_truth.get("duration_source_counts") or {pair["duration_source"]: 1})
                _increment_counts(provider_status_counts, route_truth.get("provider_status_counts") or {pair["provider_status"]: 1})
                if pair.get("fallback_reason"):
                    fallback_reasons.append(f"{origin.id}->{destination.id}:{pair['fallback_reason']}")
                pairs[(i, j)] = pair

        pair_count = n * max(0, n - 1)
        matrix_status = "ok" if failed_pair_count == 0 and fallback_pair_count == 0 and self._counts_all_ok(provider_status_counts) else "degraded"
        summary = {
            "distance_source": "route_table_mixed_sources" if route_graph_pair_count else "haversine_corrected",
            "pair_count": pair_count,
            "route_graph_pair_count": route_graph_pair_count,
            "haversine_fallback_pair_count": fallback_pair_count,
            "failed_pair_count": failed_pair_count,
            "distance_source_counts": distance_source_counts,
            "duration_source_counts": duration_source_counts,
            "provider_status_counts": provider_status_counts,
            "provider_status": matrix_status,
            "fallback_reason": ";".join(fallback_reasons[:8]) if fallback_reasons else None,
            "authenticity_level": self._matrix_authenticity(distance_source_counts, failed_pair_count, fallback_pair_count),
        }

        return {
            "node_ids": [node.id for node in nodes],
            "node_labels": [node.name for node in nodes],
            "distance_matrix": distance_matrix,
            "duration_matrix_minutes": duration_matrix,
            "pairs": pairs,
            "summary": summary,
        }

    def _route_graph_pair(
        self,
        path_service: PathAlgorithmService,
        truth_service: LocalRouteBenchmarkService,
        origin: Node,
        destination: Node,
    ) -> Dict[str, Any]:
        result = path_service.dijkstra(origin.id, destination.id, "distance")
        if not result.success:
            return {
                "success": False,
                "from_node_id": origin.id,
                "to_node_id": destination.id,
                "distance_km": None,
                "duration_minutes": None,
                "path_node_ids": [],
                "distance_source": "route_graph_unreachable",
                "duration_source": "route_graph_unreachable",
                "path_source": "local_route_graph",
                "provider_status": "failed",
                "fallback_reason": result.error or "LOCAL_ROUTE_PATH_NOT_FOUND",
                "route_segments": [],
                "route_truth": {
                    "segment_count": 0,
                    "missing_segment_count": 1,
                    "route_ids": [],
                    "distance_source_counts": {"route_graph_unreachable": 1},
                    "duration_source_counts": {"route_graph_unreachable": 1},
                    "provider_status_counts": {"failed": 1},
                    "authenticity_level": "C-local-route-unreachable",
                },
            }

        candidate = {
            "success": True,
            "path": result.path,
        }
        truth_service.attach_local_route_truth(candidate)
        route_truth = candidate.get("route_truth") or {}
        provider_status = "ok" if self._counts_all_ok(route_truth.get("provider_status_counts") or {}) else "degraded"
        fallback_reason = self._truth_fallback_reason(candidate.get("route_segments") or [])

        return {
            "success": True,
            "from_node_id": origin.id,
            "to_node_id": destination.id,
            "distance_km": result.total_distance,
            "duration_minutes": round(result.total_time * 60, 4),
            "cost": result.total_cost,
            "path_node_ids": [
                int(item["id"])
                for item in result.path
                if isinstance(item, dict) and item.get("id") is not None
            ],
            "distance_source": "local_route_graph",
            "duration_source": "local_route_graph",
            "path_source": "local_route_graph",
            "provider_status": provider_status,
            "fallback_reason": fallback_reason,
            "route_segments": candidate.get("route_segments") or [],
            "route_truth": route_truth,
        }

    def _haversine_pair(self, origin: Node, destination: Node, previous_reason: Optional[str]) -> Dict[str, Any]:
        distance = self._haversine_km(origin, destination) * DISTANCE_CORRECTION_FACTOR
        duration_minutes = (distance / DEFAULT_AVG_SPEED_KMH) * 60 if DEFAULT_AVG_SPEED_KMH else 0.0
        return {
            "success": True,
            "from_node_id": origin.id,
            "to_node_id": destination.id,
            "distance_km": round(distance, 4),
            "duration_minutes": round(duration_minutes, 4),
            "path_node_ids": [origin.id, destination.id],
            "distance_source": "haversine_corrected",
            "duration_source": "estimated_speed",
            "path_source": "coordinate_fallback_direct_leg",
            "provider_status": "degraded",
            "fallback_reason": f"HAVERSINE_FALLBACK_AFTER:{previous_reason or 'LOCAL_ROUTE_PATH_NOT_FOUND'}",
            "route_segments": [
                {
                    "sequence": 0,
                    "from_node_id": origin.id,
                    "to_node_id": destination.id,
                    "route_id": None,
                    "distance_source": "haversine_corrected",
                    "duration_source": "estimated_speed",
                    "provider_status": "degraded",
                    "fallback_reason": previous_reason or "LOCAL_ROUTE_PATH_NOT_FOUND",
                }
            ],
            "route_truth": {
                "segment_count": 1,
                "missing_segment_count": 1,
                "route_ids": [],
                "distance_source_counts": {"haversine_corrected": 1},
                "duration_source_counts": {"estimated_speed": 1},
                "provider_status_counts": {"degraded": 1},
                "authenticity_level": "C-haversine-fallback",
            },
        }

    def _same_node_pair(self, node: Node) -> Dict[str, Any]:
        return {
            "success": True,
            "from_node_id": node.id,
            "to_node_id": node.id,
            "distance_km": 0.0,
            "duration_minutes": 0.0,
            "path_node_ids": [node.id],
            "distance_source": "same_node",
            "duration_source": "same_node",
            "path_source": "same_node",
            "provider_status": "ok",
            "fallback_reason": None,
            "route_segments": [],
            "route_truth": {
                "segment_count": 0,
                "missing_segment_count": 0,
                "route_ids": [],
                "distance_source_counts": {},
                "duration_source_counts": {},
                "provider_status_counts": {},
                "authenticity_level": "A-same-node",
            },
        }

    def _run_solver(
        self,
        solver: str,
        matrix_result: Dict[str, Any],
        *,
        return_to_depot: bool,
        time_limit: float,
    ) -> Dict[str, Any]:
        if solver == "nearest_neighbor":
            return self._run_nearest_neighbor(matrix_result, return_to_depot)
        if solver == "two_opt":
            return self._run_two_opt(matrix_result, return_to_depot)
        if solver == "ortools":
            return self._run_ortools(matrix_result, return_to_depot, time_limit)
        if solver == "gurobi":
            return self._run_gurobi(matrix_result, return_to_depot, time_limit)
        return self._unsupported_solver_row(solver)

    def _run_nearest_neighbor(self, matrix_result: Dict[str, Any], return_to_depot: bool) -> Dict[str, Any]:
        started = time.perf_counter()
        model = None
        try:
            sequence = self._nearest_neighbor_sequence(matrix_result["distance_matrix"], return_to_depot)
        except ValueError as exc:
            return self._failed_solver_row("nearest_neighbor", "heuristic", str(exc), started)
        return self._success_solver_row(
            solver="nearest_neighbor",
            solver_family="local_sequence_heuristic",
            solver_quality="greedy_baseline",
            sequence_indices=sequence,
            matrix_result=matrix_result,
            started=started,
            return_to_depot=return_to_depot,
        )

    def _run_two_opt(self, matrix_result: Dict[str, Any], return_to_depot: bool) -> Dict[str, Any]:
        started = time.perf_counter()
        try:
            sequence = self._nearest_neighbor_sequence(matrix_result["distance_matrix"], return_to_depot)
            sequence = self._two_opt_sequence(sequence, matrix_result["distance_matrix"], return_to_depot)
        except ValueError as exc:
            return self._failed_solver_row("two_opt", "heuristic", str(exc), started)
        return self._success_solver_row(
            solver="two_opt",
            solver_family="local_sequence_heuristic",
            solver_quality="two_opt_improvement",
            sequence_indices=sequence,
            matrix_result=matrix_result,
            started=started,
            return_to_depot=return_to_depot,
        )

    def _run_ortools(self, matrix_result: Dict[str, Any], return_to_depot: bool, time_limit: float) -> Dict[str, Any]:
        started = time.perf_counter()
        if not return_to_depot:
            return self._failed_solver_row("ortools", "heuristic", "ORTOOLS_OPEN_PATH_NOT_SUPPORTED", started)
        if self._matrix_has_infinite_distance(matrix_result["distance_matrix"]):
            return self._failed_solver_row("ortools", "heuristic", "INFEASIBLE_DISTANCE_MATRIX", started)

        try:
            from ortools.constraint_solver import pywrapcp, routing_enums_pb2
        except Exception as exc:
            return self._failed_solver_row("ortools", "heuristic", f"ORTOOLS_UNAVAILABLE:{exc.__class__.__name__}", started)

        try:
            matrix = matrix_result["distance_matrix"]
            manager = pywrapcp.RoutingIndexManager(len(matrix), 1, 0)
            routing = pywrapcp.RoutingModel(manager)

            def distance_callback(from_index: int, to_index: int) -> int:
                from_node = manager.IndexToNode(from_index)
                to_node = manager.IndexToNode(to_index)
                return int(round(float(matrix[from_node][to_node]) * 1000))

            transit_callback_index = routing.RegisterTransitCallback(distance_callback)
            routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)
            search_parameters = pywrapcp.DefaultRoutingSearchParameters()
            search_parameters.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
            search_parameters.local_search_metaheuristic = routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
            search_parameters.time_limit.FromSeconds(max(1, int(math.ceil(time_limit))))
            solution = routing.SolveWithParameters(search_parameters)
            if solution is None:
                return self._failed_solver_row("ortools", "heuristic", "ORTOOLS_NO_SOLUTION", started)

            index = routing.Start(0)
            sequence = []
            while not routing.IsEnd(index):
                sequence.append(manager.IndexToNode(index))
                index = solution.Value(routing.NextVar(index))
            sequence.append(manager.IndexToNode(index))
        except Exception as exc:
            return self._failed_solver_row("ortools", "heuristic", f"ORTOOLS_SOLVE_FAILED:{exc.__class__.__name__}", started)

        return self._success_solver_row(
            solver="ortools",
            solver_family="ortools_routing",
            solver_quality="constraint_solver_heuristic",
            sequence_indices=sequence,
            matrix_result=matrix_result,
            started=started,
            return_to_depot=return_to_depot,
        )

    def _run_gurobi(self, matrix_result: Dict[str, Any], return_to_depot: bool, time_limit: float) -> Dict[str, Any]:
        started = time.perf_counter()
        if not return_to_depot:
            return self._failed_solver_row("gurobi_tsp_milp", "exact_milp", "GUROBI_OPEN_PATH_NOT_SUPPORTED", started)
        if self._matrix_has_infinite_distance(matrix_result["distance_matrix"]):
            return self._failed_solver_row("gurobi_tsp_milp", "exact_milp", "INFEASIBLE_DISTANCE_MATRIX", started)

        status = self.gurobi_capability_service.check(run_smoke=False)
        if not status.get("available"):
            row = self._failed_solver_row(
                "gurobi_tsp_milp",
                "exact_milp",
                status.get("fallback_reason") or "GUROBI_UNAVAILABLE",
                started,
            )
            row["gurobi_status"] = self._safe_gurobi_status(status)
            return row

        try:
            import gurobipy as gp
            from gurobipy import GRB
        except Exception as exc:
            return self._failed_solver_row("gurobi_tsp_milp", "exact_milp", f"GUROBI_IMPORT_FAILED:{exc.__class__.__name__}", started)

        try:
            matrix = matrix_result["distance_matrix"]
            n = len(matrix)
            model = gp.Model("route_sequence_tsp_benchmark")
            model.Params.OutputFlag = 0
            model.Params.TimeLimit = float(time_limit)
            x = model.addVars(
                [(i, j) for i in range(n) for j in range(n) if i != j],
                vtype=GRB.BINARY,
                name="x",
            )
            u = model.addVars(range(1, n), lb=1, ub=max(1, n - 1), vtype=GRB.CONTINUOUS, name="u")

            model.setObjective(gp.quicksum(matrix[i][j] * x[i, j] for i, j in x.keys()), GRB.MINIMIZE)
            for i in range(n):
                model.addConstr(gp.quicksum(x[i, j] for j in range(n) if i != j) == 1)
                model.addConstr(gp.quicksum(x[j, i] for j in range(n) if i != j) == 1)
            for i in range(1, n):
                for j in range(1, n):
                    if i != j:
                        model.addConstr(u[i] - u[j] + n * x[i, j] <= n - 1)

            model.optimize()
            if model.Status not in {GRB.OPTIMAL, GRB.TIME_LIMIT} or model.SolCount < 1:
                return self._failed_solver_row("gurobi_tsp_milp", "exact_milp", f"GUROBI_NO_SOLUTION_STATUS:{model.Status}", started)

            next_by_node = {
                i: j
                for i, j in x.keys()
                if x[i, j].X > 0.5
            }
            sequence = [0]
            current = 0
            for _ in range(n + 1):
                current = next_by_node.get(current)
                if current is None:
                    break
                sequence.append(current)
                if current == 0:
                    break
        except Exception as exc:
            return self._failed_solver_row("gurobi_tsp_milp", "exact_milp", f"GUROBI_SOLVE_FAILED:{exc.__class__.__name__}", started)
        finally:
            try:
                if model is not None:
                    model.dispose()
            except Exception:
                pass

        row = self._success_solver_row(
            solver="gurobi_tsp_milp",
            solver_family="gurobi",
            solver_quality="exact_milp",
            sequence_indices=sequence,
            matrix_result=matrix_result,
            started=started,
            return_to_depot=return_to_depot,
        )
        row["gurobi_status"] = self._safe_gurobi_status(status)
        return row

    def _nearest_neighbor_sequence(self, matrix: Sequence[Sequence[float]], return_to_depot: bool) -> List[int]:
        n = len(matrix)
        remaining = set(range(1, n))
        sequence = [0]
        current = 0
        while remaining:
            candidates = [
                (float(matrix[current][node]), node)
                for node in remaining
                if math.isfinite(float(matrix[current][node]))
            ]
            if not candidates:
                raise ValueError("NO_REACHABLE_NEXT_NODE")
            _, next_node = min(candidates, key=lambda item: (item[0], item[1]))
            sequence.append(next_node)
            remaining.remove(next_node)
            current = next_node

        if return_to_depot:
            if not math.isfinite(float(matrix[current][0])):
                raise ValueError("DEPOT_RETURN_LEG_UNREACHABLE")
            sequence.append(0)
        return sequence

    def _two_opt_sequence(self, sequence: List[int], matrix: Sequence[Sequence[float]], return_to_depot: bool) -> List[int]:
        best = list(sequence)
        best_distance = self._sequence_distance(best, matrix)
        end_exclusive = len(best) - 1 if return_to_depot else len(best)
        improved = True
        while improved:
            improved = False
            for i in range(1, max(1, end_exclusive - 1)):
                for k in range(i + 1, end_exclusive):
                    candidate = best[:i] + list(reversed(best[i : k + 1])) + best[k + 1 :]
                    candidate_distance = self._sequence_distance(candidate, matrix)
                    if candidate_distance + 1e-9 < best_distance:
                        best = candidate
                        best_distance = candidate_distance
                        improved = True
            end_exclusive = len(best) - 1 if return_to_depot else len(best)
        return best

    def _success_solver_row(
        self,
        *,
        solver: str,
        solver_family: str,
        solver_quality: str,
        sequence_indices: Sequence[int],
        matrix_result: Dict[str, Any],
        started: float,
        return_to_depot: bool,
    ) -> Dict[str, Any]:
        violations = self._validate_sequence(sequence_indices, matrix_result["distance_matrix"], return_to_depot)
        route_legs, route_truth = self._route_legs_and_truth(sequence_indices, matrix_result)
        total_distance = self._sequence_distance(sequence_indices, matrix_result["distance_matrix"])
        total_duration = self._sequence_distance(sequence_indices, matrix_result["duration_matrix_minutes"])
        node_ids = matrix_result["node_ids"]
        node_labels = matrix_result["node_labels"]
        provider_status = "ok" if not violations and self._counts_all_ok(route_truth["provider_status_counts"]) else "degraded"
        fallback_reason = None if provider_status == "ok" else self._row_fallback_reason(violations, route_legs)

        return {
            "success": not violations,
            "solver": solver,
            "solver_family": solver_family,
            "solver_quality": solver_quality,
            "provider_status": provider_status,
            "fallback_reason": fallback_reason,
            "authenticity_level": self._route_authenticity(route_truth, provider_status),
            "objective_value": round(total_distance, 4) if math.isfinite(total_distance) else None,
            "total_distance_km": round(total_distance, 4) if math.isfinite(total_distance) else None,
            "total_duration_minutes": round(total_duration, 4) if math.isfinite(total_duration) else None,
            "solve_time_seconds": round(time.perf_counter() - started, 6),
            "feasible": not violations,
            "hard_constraint_violations": violations,
            "node_sequence": [node_ids[index] for index in sequence_indices if 0 <= index < len(node_ids)],
            "node_labels": [node_labels[index] for index in sequence_indices if 0 <= index < len(node_labels)],
            "sequence_indices": list(sequence_indices),
            "route_legs": route_legs,
            "route_truth": route_truth,
            "summary": {
                "leg_count": len(route_legs),
                "visited_waypoints": len({idx for idx in sequence_indices if idx != 0}),
                "return_to_depot": return_to_depot,
                "total_distance_km": round(total_distance, 4) if math.isfinite(total_distance) else None,
                "total_duration_minutes": round(total_duration, 4) if math.isfinite(total_duration) else None,
            },
        }

    def _failed_solver_row(self, solver: str, solver_quality: str, reason: str, started: float) -> Dict[str, Any]:
        return {
            "success": False,
            "solver": solver,
            "solver_family": "route_sequence",
            "solver_quality": solver_quality,
            "provider_status": "degraded",
            "fallback_reason": reason,
            "authenticity_level": "C",
            "objective_value": None,
            "total_distance_km": None,
            "solve_time_seconds": round(time.perf_counter() - started, 6),
            "feasible": False,
            "hard_constraint_violations": ["SOLVER_UNAVAILABLE_OR_FAILED"],
            "node_sequence": [],
            "route_legs": [],
            "route_truth": {
                "leg_count": 0,
                "segment_count": 0,
                "missing_segment_count": 0,
                "route_ids": [],
                "distance_source_counts": {},
                "duration_source_counts": {},
                "provider_status_counts": {},
                "authenticity_level": "C-solver-failed",
            },
            "summary": {},
        }

    def _unsupported_solver_row(self, solver: str) -> Dict[str, Any]:
        return {
            "success": False,
            "solver": solver,
            "solver_family": "unsupported",
            "solver_quality": "unsupported",
            "provider_status": "degraded",
            "fallback_reason": "UNSUPPORTED_ROUTE_SEQUENCE_SOLVER",
            "authenticity_level": "C",
            "objective_value": None,
            "total_distance_km": None,
            "solve_time_seconds": 0.0,
            "feasible": False,
            "hard_constraint_violations": ["UNSUPPORTED_SOLVER"],
            "node_sequence": [],
            "route_legs": [],
            "route_truth": {},
            "summary": {},
        }

    def _validate_sequence(
        self,
        sequence: Sequence[int],
        matrix: Sequence[Sequence[float]],
        return_to_depot: bool,
    ) -> List[str]:
        violations: List[str] = []
        n = len(matrix)
        expected = set(range(1, n))
        sequence_list = list(sequence)
        if not sequence_list or sequence_list[0] != 0:
            violations.append("SEQUENCE_DOES_NOT_START_AT_DEPOT")
        if return_to_depot and (not sequence_list or sequence_list[-1] != 0):
            violations.append("SEQUENCE_DOES_NOT_RETURN_TO_DEPOT")

        visited = [idx for idx in sequence_list if idx != 0]
        visited_set = set(visited)
        if visited_set != expected:
            violations.append("WAYPOINT_VISIT_SET_MISMATCH")
        if len(visited) != len(visited_set):
            violations.append("DUPLICATE_WAYPOINT_VISIT")
        if any(idx < 0 or idx >= n for idx in sequence_list):
            violations.append("UNKNOWN_NODE_INDEX_IN_SEQUENCE")
        if any(
            0 <= sequence_list[pos] < n
            and 0 <= sequence_list[pos + 1] < n
            and not math.isfinite(float(matrix[sequence_list[pos]][sequence_list[pos + 1]]))
            for pos in range(len(sequence_list) - 1)
        ):
            violations.append("INFEASIBLE_LEG_IN_SEQUENCE")
        return violations

    def _route_legs_and_truth(
        self,
        sequence: Sequence[int],
        matrix_result: Dict[str, Any],
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        legs: List[Dict[str, Any]] = []
        distance_counts: Dict[str, int] = {}
        duration_counts: Dict[str, int] = {}
        status_counts: Dict[str, int] = {}
        route_ids: List[int] = []
        segment_count = 0
        missing_segment_count = 0

        for order, (from_index, to_index) in enumerate(zip(sequence, sequence[1:])):
            pair = matrix_result["pairs"].get((from_index, to_index))
            if not pair:
                continue
            route_truth = pair.get("route_truth") or {}
            _increment_counts(distance_counts, route_truth.get("distance_source_counts") or {pair["distance_source"]: 1})
            _increment_counts(duration_counts, route_truth.get("duration_source_counts") or {pair["duration_source"]: 1})
            _increment_counts(status_counts, route_truth.get("provider_status_counts") or {pair["provider_status"]: 1})
            segment_count += int(route_truth.get("segment_count") or 0)
            missing_segment_count += int(route_truth.get("missing_segment_count") or 0)
            for route_id in route_truth.get("route_ids") or []:
                if route_id not in route_ids:
                    route_ids.append(route_id)

            legs.append(
                {
                    "sequence": order,
                    "from_node_id": pair["from_node_id"],
                    "to_node_id": pair["to_node_id"],
                    "distance_km": pair.get("distance_km"),
                    "duration_minutes": pair.get("duration_minutes"),
                    "path_node_ids": pair.get("path_node_ids") or [],
                    "distance_source": pair.get("distance_source"),
                    "duration_source": pair.get("duration_source"),
                    "path_source": pair.get("path_source"),
                    "provider_status": pair.get("provider_status"),
                    "fallback_reason": pair.get("fallback_reason"),
                    "route_truth": route_truth,
                }
            )

        route_truth = {
            "leg_count": len(legs),
            "segment_count": segment_count,
            "missing_segment_count": missing_segment_count,
            "route_ids": route_ids,
            "distance_source_counts": distance_counts,
            "duration_source_counts": duration_counts,
            "provider_status_counts": status_counts,
            "authenticity_level": self._route_authenticity_from_counts(distance_counts, status_counts, missing_segment_count),
        }
        return legs, route_truth

    def _rank_rows(self, rows: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
        candidates = [
            row
            for row in rows
            if row.get("success")
            and row.get("feasible")
            and row.get("total_distance_km") is not None
        ]
        candidates.sort(
            key=lambda row: (
                float(row.get("total_distance_km") or 0.0),
                float(row.get("solve_time_seconds") or 0.0),
            )
        )
        return [
            {
                "rank": index,
                "solver": row["solver"],
                "total_distance_km": row.get("total_distance_km"),
                "total_duration_minutes": row.get("total_duration_minutes"),
                "solve_time_seconds": row.get("solve_time_seconds"),
                "solver_quality": row.get("solver_quality"),
            }
            for index, row in enumerate(candidates, start=1)
        ]

    def _normalise_solvers(self, solvers: Sequence[Any]) -> List[str]:
        result: List[str] = []
        aliases = {
            "nearest": "nearest_neighbor",
            "greedy": "nearest_neighbor",
            "baseline": "nearest_neighbor",
            "2opt": "two_opt",
            "2-opt": "two_opt",
            "gurobi_tsp": "gurobi",
        }
        for solver in solvers:
            name = str(solver).strip().lower()
            name = aliases.get(name, name)
            if name and name not in result:
                result.append(name)
        return result or list(DEFAULT_SEQUENCE_SOLVERS)

    def _sequence_distance(self, sequence: Sequence[int], matrix: Sequence[Sequence[float]]) -> float:
        total = 0.0
        for from_index, to_index in zip(sequence, sequence[1:]):
            value = float(matrix[from_index][to_index])
            if not math.isfinite(value):
                return float("inf")
            total += value
        return total

    def _matrix_has_infinite_distance(self, matrix: Sequence[Sequence[float]]) -> bool:
        return any(
            i != j and not math.isfinite(float(matrix[i][j]))
            for i in range(len(matrix))
            for j in range(len(matrix))
        )

    def _counts_all_ok(self, counts: Dict[str, int]) -> bool:
        if not counts:
            return True
        return set(counts.keys()) <= {"ok"}

    def _truth_fallback_reason(self, route_segments: Sequence[Dict[str, Any]]) -> Optional[str]:
        reasons = [
            segment.get("fallback_reason")
            for segment in route_segments
            if segment.get("fallback_reason")
        ]
        return ";".join(str(reason) for reason in reasons) if reasons else None

    def _row_fallback_reason(self, violations: Sequence[str], route_legs: Sequence[Dict[str, Any]]) -> Optional[str]:
        reasons = list(violations)
        for leg in route_legs:
            if leg.get("fallback_reason"):
                reasons.append(f"{leg['from_node_id']}->{leg['to_node_id']}:{leg['fallback_reason']}")
        return ";".join(reasons[:8]) if reasons else None

    def _matrix_authenticity(self, distance_counts: Dict[str, int], failed_pairs: int, fallback_pairs: int) -> str:
        if failed_pairs:
            return "C-route-matrix-incomplete"
        if fallback_pairs:
            return "C-route-matrix-with-haversine-fallback"
        if distance_counts and set(distance_counts.keys()) <= EXACT_DISTANCE_SOURCES:
            return "B-route-matrix-real-distance"
        if any(source in EXACT_DISTANCE_SOURCES for source in distance_counts):
            return "B/C-route-matrix-mixed-distance"
        return "C-route-matrix-estimated-distance"

    def _route_authenticity_from_counts(
        self,
        distance_counts: Dict[str, int],
        status_counts: Dict[str, int],
        missing_segments: int,
    ) -> str:
        if missing_segments:
            return "C-route-sequence-with-missing-segments"
        if not self._counts_all_ok(status_counts):
            return "C-route-sequence-degraded"
        if distance_counts and set(distance_counts.keys()) <= EXACT_DISTANCE_SOURCES:
            return "B-route-sequence-real-distance"
        if any(source in EXACT_DISTANCE_SOURCES for source in distance_counts):
            return "B/C-route-sequence-mixed-distance"
        return "C-route-sequence-estimated-distance"

    def _route_authenticity(self, route_truth: Dict[str, Any], provider_status: str) -> str:
        if provider_status != "ok":
            return "C"
        return route_truth.get("authenticity_level") or "C-route-sequence"

    def _overall_authenticity(self, matrix_summary: Dict[str, Any], provider_status: str) -> str:
        if provider_status != "ok":
            return "C"
        return matrix_summary.get("authenticity_level") or "C-route-sequence-benchmark"

    def _haversine_km(self, origin: Node, destination: Node) -> float:
        lat1 = float(origin.latitude or 0.0)
        lon1 = float(origin.longitude or 0.0)
        lat2 = float(destination.latitude or 0.0)
        lon2 = float(destination.longitude or 0.0)
        radius_km = 6371.0
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = (
            math.sin(dlat / 2) ** 2
            + math.cos(math.radians(lat1))
            * math.cos(math.radians(lat2))
            * math.sin(dlon / 2) ** 2
        )
        return radius_km * 2 * math.asin(math.sqrt(a))

    def _safe_gurobi_status(self, status: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "available": bool(status.get("available")),
            "provider_status": status.get("provider_status"),
            "fallback_reason": status.get("fallback_reason"),
            "authenticity_level": status.get("authenticity_level"),
            "checks": status.get("checks", {}),
            "security": status.get("security", {}),
        }


_service: Optional[RouteSequenceBenchmarkService] = None


def get_route_sequence_benchmark_service() -> RouteSequenceBenchmarkService:
    global _service
    if _service is None:
        _service = RouteSequenceBenchmarkService()
    return _service
