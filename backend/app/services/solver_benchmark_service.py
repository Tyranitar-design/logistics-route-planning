"""Solver benchmark service for phase-2 optimization governance.

The benchmark keeps one bounded CVRP instance fixed and compares exact,
heuristic, and fallback solvers with explicit truth metadata. It is designed for
API smoke tests and the future dispatch control console, not for large batch
production optimization.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

import numpy as np

from app.services.gurobi_vrp_service import GurobiVRPService, VRPDataset, get_gurobi_vrp_service
from app.services.optimization_engine import CVRPProblem, SolverFactory, SolverType, VRPData


DEFAULT_SOLVERS = ["gurobi", "ortools", "alns", "greedy"]


class SolverBenchmarkService:
    """Compare small CVRP solvers using one shared dataset and metrics contract."""

    def __init__(self, vrp_service: Optional[GurobiVRPService] = None):
        self.vrp_service = vrp_service or get_gurobi_vrp_service()

    def demo_payload(self) -> Dict[str, Any]:
        payload = dict(self.vrp_service.demo_payload())
        payload.update(
            {
                "solvers": list(DEFAULT_SOLVERS),
                "time_limit": 5,
                "alns_iterations": 120,
            }
        )
        return payload

    def compare_small_vrp(self, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        payload = self._with_demo_data_when_missing(payload or {})
        started = time.perf_counter()
        dataset = self.vrp_service.build_dataset_for_benchmark(payload)
        validation = self.vrp_service.validate_dataset_for_benchmark(dataset)
        if validation:
            return {
                "success": False,
                "error": validation,
                "provider_status": "degraded",
                "fallback_reason": validation,
                "authenticity_level": dataset.authenticity_level,
            }

        requested_solvers = self._normalise_solvers(payload.get("solvers") or DEFAULT_SOLVERS)
        time_limit = max(0.1, self._coerce_float(payload.get("time_limit"), 5.0))
        rows = []
        for solver_name in requested_solvers:
            if solver_name == "greedy":
                rows.append(self._run_gurobi_vrp_branch(dataset, payload, "greedy", time_limit))
            elif solver_name == "gurobi":
                rows.append(self._run_gurobi_vrp_branch(dataset, payload, "gurobi", time_limit))
            elif solver_name in {"ortools", "alns"}:
                rows.append(self._run_engine_solver(dataset, payload, solver_name, time_limit))
            else:
                rows.append(self._unsupported_solver_row(solver_name))

        rankings = self._rank_rows(rows)
        best_solver = rankings[0]["solver"] if rankings else None
        elapsed = time.perf_counter() - started
        provider_status = "ok" if rows and all(row["provider_status"] == "ok" for row in rows) else "degraded"
        fallback_reasons = [
            row["fallback_reason"]
            for row in rows
            if row.get("fallback_reason")
        ]

        return {
            "success": True,
            "benchmark_type": "small_cvrp_solver_comparison",
            "data_source": dataset.data_source,
            "distance_source": dataset.distance_source,
            "path_source": "solver_node_sequence+optimization_engine_routes",
            "provider_status": provider_status,
            "fallback_reason": ";".join(fallback_reasons) if fallback_reasons else None,
            "authenticity_level": dataset.authenticity_level if provider_status == "ok" else "C",
            "solver": "benchmark_compare",
            "summary": {
                "requested_solvers": requested_solvers,
                "succeeded_solvers": [row["solver"] for row in rows if row["success"]],
                "feasible_solvers": [row["solver"] for row in rows if row["success"] and row["feasible"]],
                "best_solver": best_solver,
                "solve_time_seconds": round(elapsed, 6),
                "customer_count": dataset.n_customers,
                "vehicle_count": dataset.n_vehicles,
                "vehicle_capacity": dataset.vehicle_capacity,
            },
            "results": rows,
            "rankings": rankings,
            "input_summary": {
                "node_labels": dataset.node_labels,
                "demands": [round(value, 4) for value in dataset.demands],
                "total_demand": round(sum(dataset.demands), 4),
                **dataset.metadata,
            },
            "diagnostics": {
                "ranking_rule": "feasible_successful_rows_sorted_by_objective_then_solve_time",
                "hard_constraints": [
                    "each_customer_served_once",
                    "vehicle_capacity",
                    "vehicle_count_limit",
                ],
                "unsupported_solvers": [
                    row["solver"]
                    for row in rows
                    if row.get("fallback_reason") == "UNSUPPORTED_BENCHMARK_SOLVER"
                ],
            },
        }

    def _run_gurobi_vrp_branch(
        self,
        dataset: VRPDataset,
        payload: Dict[str, Any],
        solver_name: str,
        time_limit: float,
    ) -> Dict[str, Any]:
        branch_payload = {
            key: value
            for key, value in payload.items()
            if key not in {"solvers", "solver"}
        }
        branch_payload.update(
            {
                "solver": solver_name,
                "allow_fallback": solver_name != "gurobi",
                "time_limit": time_limit,
            }
        )
        result = self.vrp_service.solve(branch_payload)
        if not result.get("success"):
            return {
                "success": False,
                "solver": "gurobi_cvrp_milp" if solver_name == "gurobi" else solver_name,
                "solver_family": "gurobi_vrp_service",
                "solver_quality": "exact_milp" if solver_name == "gurobi" else "heuristic_baseline",
                "provider_status": result.get("provider_status", "degraded"),
                "fallback_reason": result.get("fallback_reason") or result.get("error"),
                "authenticity_level": result.get("authenticity_level", "C"),
                "feasible": False,
                "hard_constraint_violations": ["SOLVER_UNAVAILABLE_OR_FAILED"],
                "summary": {},
                "routes": [],
            }

        violations = self._validate_routes(
            dataset=dataset,
            route_sequences=[route.get("node_sequence", []) for route in result.get("routes", [])],
            unassigned_count=result.get("summary", {}).get("unassigned_customers", 0),
        )
        summary = result.get("summary", {})
        return {
            "success": True,
            "solver": result.get("solver"),
            "solver_family": "gurobi_vrp_service",
            "solver_quality": result.get("solver_quality"),
            "provider_status": result.get("provider_status", "ok"),
            "fallback_reason": result.get("fallback_reason"),
            "authenticity_level": result.get("authenticity_level", dataset.authenticity_level),
            "objective_value": summary.get("objective_value"),
            "total_distance": summary.get("total_distance"),
            "solve_time_seconds": result.get("solve_time_seconds"),
            "gap": summary.get("optimality_gap"),
            "used_vehicles": summary.get("used_vehicles"),
            "assigned_customers": summary.get("assigned_customers"),
            "unassigned_customers": summary.get("unassigned_customers"),
            "feasible": not violations,
            "hard_constraint_violations": violations,
            "summary": summary,
            "routes": result.get("routes", []),
            "diagnostics": result.get("diagnostics", {}),
        }

    def _run_engine_solver(
        self,
        dataset: VRPDataset,
        payload: Dict[str, Any],
        solver_name: str,
        time_limit: float,
    ) -> Dict[str, Any]:
        solver_type = SolverType(solver_name)
        if not SolverFactory.is_available(solver_type):
            return {
                "success": False,
                "solver": solver_name,
                "solver_family": "optimization_engine",
                "solver_quality": "unavailable",
                "provider_status": "degraded",
                "fallback_reason": f"{solver_name.upper()}_UNAVAILABLE",
                "authenticity_level": "C",
                "feasible": False,
                "hard_constraint_violations": ["SOLVER_UNAVAILABLE_OR_FAILED"],
                "summary": {},
                "routes": [],
            }

        started = time.perf_counter()
        try:
            solver_kwargs = {}
            if solver_type == SolverType.ALNS:
                solver_kwargs["n_iterations"] = max(1, int(payload.get("alns_iterations") or 120))
            solver = SolverFactory.create_solver(solver_type, **solver_kwargs)
            problem = self._to_cvrp_problem(dataset)
            result = solver.solve(problem, time_limit=time_limit)
        except Exception as exc:
            return {
                "success": False,
                "solver": solver_name,
                "solver_family": "optimization_engine",
                "solver_quality": "heuristic" if solver_name in {"ortools", "alns"} else "unknown",
                "provider_status": "degraded",
                "fallback_reason": f"{solver_name.upper()}_SOLVE_FAILED:{exc.__class__.__name__}",
                "authenticity_level": "C",
                "feasible": False,
                "hard_constraint_violations": ["SOLVER_UNAVAILABLE_OR_FAILED"],
                "summary": {},
                "routes": [],
            }

        elapsed = time.perf_counter() - started
        route_sequences = self._normalise_engine_routes(result.routes or [])
        violations = self._validate_routes(dataset, route_sequences, unassigned_count=0)
        assigned_customers = len(self._customers_in_routes(route_sequences)[0])
        total_distance = float(result.primary_objective)
        return {
            "success": True,
            "solver": solver_name,
            "solver_family": "optimization_engine",
            "solver_quality": "heuristic",
            "provider_status": "ok" if not violations else "degraded",
            "fallback_reason": None if not violations else "HARD_CONSTRAINT_VALIDATION_FAILED",
            "authenticity_level": dataset.authenticity_level if not violations else "C",
            "objective_value": round(total_distance, 4),
            "total_distance": round(total_distance, 4),
            "solve_time_seconds": round(float(getattr(result, "solve_time", elapsed)), 6),
            "gap": float(result.gap) if result.gap is not None else None,
            "used_vehicles": len(route_sequences),
            "assigned_customers": assigned_customers,
            "unassigned_customers": max(0, dataset.n_customers - assigned_customers),
            "feasible": not violations,
            "hard_constraint_violations": violations,
            "summary": {
                "total_customers": dataset.n_customers,
                "assigned_customers": assigned_customers,
                "unassigned_customers": max(0, dataset.n_customers - assigned_customers),
                "used_vehicles": len(route_sequences),
                "total_distance": round(total_distance, 4),
                "objective_value": round(total_distance, 4),
                "optimality_gap": float(result.gap) if result.gap is not None else None,
                "model_status": "optimization_engine_result",
            },
            "routes": [
                {
                    "vehicle_index": idx,
                    "node_sequence": route,
                    "node_labels": [
                        dataset.node_labels[node] if node < len(dataset.node_labels) else str(node)
                        for node in route
                    ],
                    "customers": [node for node in route if node != 0],
                    "distance": round(self._route_distance(dataset, route), 4),
                    "load": round(self._route_load(dataset, route), 4),
                    "capacity": round(dataset.vehicle_capacity, 4),
                    "capacity_utilization": round(self._route_load(dataset, route) / dataset.vehicle_capacity, 4)
                    if dataset.vehicle_capacity
                    else 0.0,
                }
                for idx, route in enumerate(route_sequences)
            ],
            "diagnostics": {
                "result_metadata": getattr(result, "metadata", {}),
                "iterations": getattr(result, "iterations", 0),
            },
        }

    def _to_cvrp_problem(self, dataset: VRPDataset) -> CVRPProblem:
        vrp_data = VRPData(
            n_customers=dataset.n_customers,
            n_vehicles=dataset.n_vehicles,
            vehicle_capacity=dataset.vehicle_capacity,
            depot=np.array([0.0, 0.0]),
            customers=np.array([[float(idx), 0.0] for idx in range(1, dataset.n_customers + 1)]),
            demands=np.array(dataset.demands),
            distance_matrix=np.array(dataset.distance_matrix, dtype=float),
            distance_precision={
                "source": dataset.distance_source,
                "total_count": (dataset.n_customers + 1) ** 2,
            },
            source_summary={
                dataset.distance_source: (dataset.n_customers + 1) ** 2,
            },
            metadata={
                "distance_source": dataset.distance_source,
                "path_source": "optimization_engine_routes",
                "benchmark_data_source": dataset.data_source,
            },
        )
        return CVRPProblem(vrp_data)

    def _normalise_engine_routes(self, routes: Sequence[Sequence[int]]) -> List[List[int]]:
        normalised = []
        for route in routes:
            clean = [int(node) for node in route]
            if not clean:
                continue
            if clean[0] != 0:
                clean = [0] + clean
            if clean[-1] != 0:
                clean = clean + [0]
            if len(clean) > 2:
                normalised.append(clean)
        return normalised

    def _validate_routes(
        self,
        dataset: VRPDataset,
        route_sequences: Sequence[Sequence[int]],
        unassigned_count: int,
    ) -> List[str]:
        violations: List[str] = []
        visited, duplicates = self._customers_in_routes(route_sequences)
        expected = set(range(1, dataset.n_customers + 1))
        missing = expected - visited
        extra = visited - expected

        if duplicates:
            violations.append("DUPLICATE_CUSTOMER_ASSIGNMENT")
        if missing and not unassigned_count:
            violations.append("MISSING_CUSTOMER_ASSIGNMENT")
        if extra:
            violations.append("UNKNOWN_CUSTOMER_IN_ROUTE")
        if len(route_sequences) > dataset.n_vehicles:
            violations.append("USED_VEHICLES_EXCEEDS_AVAILABLE_VEHICLES")
        if any(self._route_load(dataset, route) > dataset.vehicle_capacity + 1e-9 for route in route_sequences):
            violations.append("ROUTE_CAPACITY_EXCEEDED")
        return violations

    def _customers_in_routes(self, route_sequences: Sequence[Sequence[int]]) -> Tuple[Set[int], Set[int]]:
        visited: Set[int] = set()
        duplicates: Set[int] = set()
        for route in route_sequences:
            for node in route:
                node = int(node)
                if node == 0:
                    continue
                if node in visited:
                    duplicates.add(node)
                visited.add(node)
        return visited, duplicates

    def _route_load(self, dataset: VRPDataset, route: Sequence[int]) -> float:
        return sum(dataset.demands[node - 1] for node in route if node != 0 and 1 <= node <= dataset.n_customers)

    def _route_distance(self, dataset: VRPDataset, route: Sequence[int]) -> float:
        return sum(dataset.distance_matrix[route[idx]][route[idx + 1]] for idx in range(len(route) - 1))

    def _rank_rows(self, rows: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
        candidates = [
            row
            for row in rows
            if row.get("success")
            and row.get("feasible")
            and row.get("objective_value") is not None
        ]
        candidates.sort(
            key=lambda row: (
                float(row.get("objective_value") or 0.0),
                float(row.get("solve_time_seconds") or 0.0),
            )
        )
        return [
            {
                "rank": idx,
                "solver": row["solver"],
                "objective_value": row.get("objective_value"),
                "total_distance": row.get("total_distance"),
                "solve_time_seconds": row.get("solve_time_seconds"),
                "solver_quality": row.get("solver_quality"),
            }
            for idx, row in enumerate(candidates, start=1)
        ]

    def _normalise_solvers(self, solvers: Sequence[Any]) -> List[str]:
        result = []
        for solver in solvers:
            name = str(solver).strip().lower()
            if name in {"nearest_neighbor", "baseline"}:
                name = "greedy"
            if name and name not in result:
                result.append(name)
        return result or list(DEFAULT_SOLVERS)

    def _with_demo_data_when_missing(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        has_data = bool(
            payload.get("use_database")
            or payload.get("distance_matrix")
            or payload.get("customers")
            or payload.get("demands")
        )
        if has_data:
            return dict(payload)
        merged = self.vrp_service.demo_payload()
        merged.update(payload)
        return merged

    def _unsupported_solver_row(self, solver_name: str) -> Dict[str, Any]:
        return {
            "success": False,
            "solver": solver_name,
            "solver_family": "unsupported",
            "solver_quality": "unsupported",
            "provider_status": "degraded",
            "fallback_reason": "UNSUPPORTED_BENCHMARK_SOLVER",
            "authenticity_level": "C",
            "feasible": False,
            "hard_constraint_violations": ["UNSUPPORTED_SOLVER"],
            "summary": {},
            "routes": [],
        }

    def _coerce_float(self, value: Any, default: float) -> float:
        try:
            if value is None or value == "":
                return default
            return float(value)
        except (TypeError, ValueError):
            return default


_service: Optional[SolverBenchmarkService] = None


def get_solver_benchmark_service() -> SolverBenchmarkService:
    global _service
    if _service is None:
        _service = SolverBenchmarkService()
    return _service
