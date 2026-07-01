"""Small CVRP exact-solve demo for Gurobi phase 2.

This service is deliberately bounded and explainable. It provides an API-sized
CVRP model suitable for smoke tests, frontend previews, and future comparison
against OR-Tools/ALNS.
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple

from app.models import ShipmentFact, Vehicle
from app.services.gurobi_capability_service import get_gurobi_capability_service


SHIPMENT_FACT_DISPATCHABLE_STATUSES = ("assigned", "pending", "in_transit")
AVAILABLE_VEHICLE_STATUSES = ("available", "idle", "空闲")
MAX_EXACT_CUSTOMERS = 8


@dataclass
class VRPDataset:
    n_customers: int
    n_vehicles: int
    vehicle_capacity: float
    demands: List[float]
    distance_matrix: List[List[float]]
    node_labels: List[str]
    data_source: str
    distance_source: str
    path_source: str
    authenticity_level: str
    metadata: Dict[str, Any]


class GurobiVRPService:
    """Small CVRP exact solve with transparent fallback."""

    def __init__(self, capability_service=None):
        self.capability_service = capability_service or get_gurobi_capability_service()

    def build_dataset_for_benchmark(self, payload: Optional[Dict[str, Any]] = None) -> VRPDataset:
        """Build the same bounded CVRP dataset used by solve() for comparisons."""
        payload = payload or {}
        return self._build_dataset(payload or self.demo_payload())

    def validate_dataset_for_benchmark(self, dataset: VRPDataset) -> Optional[str]:
        """Expose dataset validation to benchmark services without duplicating rules."""
        return self._validate_dataset(dataset)

    def solve(self, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        payload = payload or {}
        started = time.perf_counter()
        preferred_solver = str(payload.get("solver") or "auto").lower()
        allow_fallback = bool(payload.get("allow_fallback", True))

        dataset = self._build_dataset(payload)
        validation = self._validate_dataset(dataset)
        if validation:
            return {
                "success": False,
                "error": validation,
                "solver": None,
                "provider_status": "degraded",
                "fallback_reason": validation,
                "authenticity_level": dataset.authenticity_level,
            }

        gurobi_status = self.capability_service.check(run_smoke=False)

        if preferred_solver in {"greedy", "nearest_neighbor", "baseline"}:
            result = self._solve_with_greedy(dataset)
            result["solver"] = "nearest_neighbor_capacity"
            result["provider_status"] = "ok"
            result["fallback_reason"] = None
            result["solver_quality"] = "heuristic_baseline"
        elif preferred_solver in {"auto", "gurobi"} and gurobi_status["available"]:
            try:
                result = self._solve_with_gurobi(dataset, time_limit=float(payload.get("time_limit") or 30.0))
                result["solver"] = "gurobi_cvrp_milp"
                result["provider_status"] = "ok"
                result["fallback_reason"] = None
                result["solver_quality"] = "exact_milp"
            except Exception as exc:
                if not allow_fallback:
                    raise
                result = self._solve_with_greedy(dataset)
                result["solver"] = "nearest_neighbor_capacity_fallback"
                result["provider_status"] = "degraded"
                result["fallback_reason"] = f"GUROBI_VRP_SOLVE_FAILED:{exc.__class__.__name__}"
                result["solver_quality"] = "heuristic_fallback"
        else:
            if preferred_solver == "gurobi" and not allow_fallback:
                return {
                    "success": False,
                    "error": gurobi_status["fallback_reason"] or "GUROBI_UNAVAILABLE",
                    "solver": "gurobi_cvrp_milp",
                    "provider_status": "degraded",
                    "fallback_reason": gurobi_status["fallback_reason"] or "GUROBI_UNAVAILABLE",
                    "authenticity_level": dataset.authenticity_level,
                    "gurobi_status": self._safe_gurobi_status(gurobi_status),
                }
            result = self._solve_with_greedy(dataset)
            result["solver"] = "nearest_neighbor_capacity_fallback"
            result["provider_status"] = "degraded"
            result["fallback_reason"] = gurobi_status["fallback_reason"] or "GUROBI_UNAVAILABLE"
            result["solver_quality"] = "heuristic_fallback"

        elapsed = time.perf_counter() - started
        result.update(
            {
                "success": True,
                "data_source": dataset.data_source,
                "distance_source": dataset.distance_source,
                "path_source": dataset.path_source,
                "authenticity_level": dataset.authenticity_level
                if result["provider_status"] == "ok"
                else "C",
                "solve_time_seconds": round(elapsed, 6),
                "gurobi_status": self._safe_gurobi_status(gurobi_status),
                "input_summary": {
                    "n_customers": dataset.n_customers,
                    "n_vehicles": dataset.n_vehicles,
                    "vehicle_capacity": dataset.vehicle_capacity,
                    "total_demand": round(sum(dataset.demands), 4),
                    "node_labels": dataset.node_labels,
                    **dataset.metadata,
                },
                "constraints": [
                    "each_customer_served_at_most_once",
                    "vehicle_capacity",
                    "depot_depart_return_balance",
                    "subtour_elimination_mtz_when_gurobi",
                ],
            }
        )
        return result

    def demo_payload(self) -> Dict[str, Any]:
        return {
            "solver": "auto",
            "n_vehicles": 2,
            "vehicle_capacity": 7,
            "node_labels": ["广州仓", "佛山客户", "东莞客户", "深圳客户", "珠海客户"],
            "demands": [2, 3, 4, 2],
            "distance_matrix": [
                [0, 18, 45, 110, 95],
                [18, 0, 55, 120, 80],
                [45, 55, 0, 70, 115],
                [110, 120, 70, 0, 140],
                [95, 80, 115, 140, 0],
            ],
            "distance_source": "payload_distance_matrix",
            "data_source": "payload_demo",
        }

    def _build_dataset(self, payload: Dict[str, Any]) -> VRPDataset:
        if payload.get("use_database"):
            return self._build_dataset_from_database(payload)

        if not payload:
            payload = self.demo_payload()

        distance_matrix = payload.get("distance_matrix")
        node_labels = payload.get("node_labels") or payload.get("labels")
        demands = payload.get("demands") or []

        if distance_matrix:
            matrix = self._coerce_matrix(distance_matrix)
            n_customers = len(matrix) - 1
            labels = list(node_labels or [f"node-{idx}" for idx in range(n_customers + 1)])
            distance_source = str(payload.get("distance_source") or "payload_distance_matrix")
            authenticity_level = "B" if distance_source != "euclidean_payload" else "C"
        else:
            depot = payload.get("depot") or [0.0, 0.0]
            customers = payload.get("customers") or []
            matrix = self._euclidean_matrix(depot, customers)
            n_customers = len(customers)
            labels = list(node_labels or ["depot"] + [f"customer-{idx}" for idx in range(1, n_customers + 1)])
            distance_source = "euclidean_payload"
            authenticity_level = "C"

        clean_demands = [max(0.0, self._coerce_float(value, 0.0)) for value in demands]
        if len(clean_demands) < n_customers:
            clean_demands.extend([1.0] * (n_customers - len(clean_demands)))
        clean_demands = clean_demands[:n_customers]

        return VRPDataset(
            n_customers=n_customers,
            n_vehicles=max(1, int(payload.get("n_vehicles") or payload.get("vehicle_count") or 1)),
            vehicle_capacity=max(0.0, self._coerce_float(payload.get("vehicle_capacity") or payload.get("capacity"), 10.0)),
            demands=clean_demands,
            distance_matrix=matrix,
            node_labels=labels[: n_customers + 1],
            data_source=str(payload.get("data_source") or "payload"),
            distance_source=distance_source,
            path_source="solver_node_sequence",
            authenticity_level=authenticity_level,
            metadata={"source_mode": "payload"},
        )

    def _build_dataset_from_database(self, payload: Dict[str, Any]) -> VRPDataset:
        limit = min(max(int(payload.get("limit") or 5), 1), MAX_EXACT_CUSTOMERS)
        facts = (
            ShipmentFact.query.filter(
                ShipmentFact.standard_status.in_(SHIPMENT_FACT_DISPATCHABLE_STATUSES),
                ShipmentFact.origin_lng.isnot(None),
                ShipmentFact.origin_lat.isnot(None),
                ShipmentFact.destination_lng.isnot(None),
                ShipmentFact.destination_lat.isnot(None),
            )
            .order_by(ShipmentFact.shipped_at.desc().nullslast(), ShipmentFact.id.desc())
            .limit(limit)
            .all()
        )
        if not facts:
            return self._build_dataset(self.demo_payload())

        depot = (float(facts[0].origin_lng), float(facts[0].origin_lat))
        customers = [(float(fact.destination_lng), float(fact.destination_lat)) for fact in facts]
        matrix = self._haversine_matrix(depot, customers)
        demands = [max(0.001, self._coerce_float(fact.weight_kg, 1.0) / 1000.0) for fact in facts]

        vehicles = Vehicle.query.filter(Vehicle.status.in_(AVAILABLE_VEHICLE_STATUSES)).all()
        if vehicles:
            capacity = max(self._coerce_float(vehicle.load_capacity or vehicle.capacity, 0.0) for vehicle in vehicles)
            n_vehicles = min(len(vehicles), int(payload.get("n_vehicles") or len(vehicles)))
        else:
            capacity = max(sum(demands), 1.0)
            n_vehicles = int(payload.get("n_vehicles") or 1)

        return VRPDataset(
            n_customers=len(facts),
            n_vehicles=max(1, n_vehicles),
            vehicle_capacity=max(0.001, self._coerce_float(payload.get("vehicle_capacity"), capacity)),
            demands=demands,
            distance_matrix=matrix,
            node_labels=["depot"] + [str(fact.external_order_id or fact.external_shipment_id or fact.id) for fact in facts],
            data_source="shipment_fact+vehicle_table" if vehicles else "shipment_fact",
            distance_source="haversine_corrected",
            path_source="solver_node_sequence",
            authenticity_level="C",
            metadata={
                "source_mode": "database_sample",
                "sample_size": len(facts),
            },
        )

    def _solve_with_gurobi(self, dataset: VRPDataset, time_limit: float) -> Dict[str, Any]:
        import gurobipy as gp
        from gurobipy import GRB

        n = dataset.n_customers
        k_count = dataset.n_vehicles
        nodes = range(n + 1)
        customers = range(1, n + 1)
        vehicles = range(k_count)
        arcs = [(i, j, k) for i in nodes for j in nodes for k in vehicles if i != j]

        penalty = max(max(row) for row in dataset.distance_matrix) * (n + 1) * 10.0
        model = gp.Model("logistics_cvrp_small")
        model.setParam("OutputFlag", 0)
        model.setParam("TimeLimit", time_limit)

        x = model.addVars(arcs, vtype=GRB.BINARY, name="x")
        y = model.addVars(customers, vehicles, vtype=GRB.BINARY, name="y")
        u = model.addVars(customers, vehicles, lb=0.0, ub=float(n), vtype=GRB.CONTINUOUS, name="u")
        unassigned = model.addVars(customers, vtype=GRB.BINARY, name="unassigned")

        for customer in customers:
            model.addConstr(
                gp.quicksum(y[customer, vehicle] for vehicle in vehicles) + unassigned[customer] == 1,
                name=f"serve_once_{customer}",
            )

        for vehicle in vehicles:
            model.addConstr(
                gp.quicksum(x[0, j, vehicle] for j in customers) <= 1,
                name=f"depart_once_{vehicle}",
            )
            model.addConstr(
                gp.quicksum(x[i, 0, vehicle] for i in customers)
                == gp.quicksum(x[0, j, vehicle] for j in customers),
                name=f"return_balance_{vehicle}",
            )
            model.addConstr(
                gp.quicksum(dataset.demands[customer - 1] * y[customer, vehicle] for customer in customers)
                <= dataset.vehicle_capacity,
                name=f"capacity_{vehicle}",
            )

            for customer in customers:
                model.addConstr(
                    gp.quicksum(x[customer, j, vehicle] for j in nodes if j != customer)
                    == y[customer, vehicle],
                    name=f"out_{customer}_{vehicle}",
                )
                model.addConstr(
                    gp.quicksum(x[i, customer, vehicle] for i in nodes if i != customer)
                    == y[customer, vehicle],
                    name=f"in_{customer}_{vehicle}",
                )
                model.addConstr(u[customer, vehicle] >= y[customer, vehicle], name=f"u_lb_{customer}_{vehicle}")
                model.addConstr(u[customer, vehicle] <= n * y[customer, vehicle], name=f"u_ub_{customer}_{vehicle}")

            for i in customers:
                for j in customers:
                    if i != j:
                        model.addConstr(
                            u[i, vehicle] - u[j, vehicle] + n * x[i, j, vehicle] <= n - 1,
                            name=f"mtz_{i}_{j}_{vehicle}",
                        )

        model.setObjective(
            gp.quicksum(dataset.distance_matrix[i][j] * x[i, j, vehicle] for i, j, vehicle in arcs)
            + penalty * gp.quicksum(unassigned[customer] for customer in customers),
            GRB.MINIMIZE,
        )
        model.optimize()

        if model.status not in {GRB.OPTIMAL, GRB.TIME_LIMIT, GRB.SOLUTION_LIMIT}:
            raise RuntimeError(f"Gurobi CVRP failed with status {model.status}")

        routes = []
        assigned = set()
        for vehicle in vehicles:
            route = self._extract_gurobi_route(dataset, x, vehicle)
            if len(route["node_sequence"]) > 2:
                routes.append(route)
                assigned.update(node for node in route["node_sequence"] if node != 0)

        unassigned_payload = [
            self._unassigned_customer_payload(dataset, customer)
            for customer in customers
            if customer not in assigned
        ]

        return self._format_result(
            dataset=dataset,
            routes=routes,
            unassigned_customers=unassigned_payload,
            objective_value=float(model.ObjVal),
            optimality_gap=float(model.MIPGap) if hasattr(model, "MIPGap") else 0.0,
            model_status=getattr(model, "status", None),
        )

    def _solve_with_greedy(self, dataset: VRPDataset) -> Dict[str, Any]:
        unvisited = set(range(1, dataset.n_customers + 1))
        routes = []
        for vehicle_idx in range(dataset.n_vehicles):
            if not unvisited:
                break
            current = 0
            remaining_capacity = dataset.vehicle_capacity
            sequence = [0]
            load = 0.0
            distance = 0.0

            while True:
                feasible = [
                    customer
                    for customer in unvisited
                    if dataset.demands[customer - 1] <= remaining_capacity
                ]
                if not feasible:
                    break
                next_customer = min(feasible, key=lambda customer: dataset.distance_matrix[current][customer])
                distance += dataset.distance_matrix[current][next_customer]
                sequence.append(next_customer)
                load += dataset.demands[next_customer - 1]
                remaining_capacity -= dataset.demands[next_customer - 1]
                unvisited.remove(next_customer)
                current = next_customer

            if len(sequence) > 1:
                distance += dataset.distance_matrix[current][0]
                sequence.append(0)
                routes.append(
                    self._route_payload(
                        dataset=dataset,
                        vehicle_index=vehicle_idx,
                        sequence=sequence,
                        distance=distance,
                        load=load,
                    )
                )

        unassigned_payload = [
            self._unassigned_customer_payload(dataset, customer)
            for customer in sorted(unvisited)
        ]

        return self._format_result(
            dataset=dataset,
            routes=routes,
            unassigned_customers=unassigned_payload,
            objective_value=sum(route["distance"] for route in routes),
            optimality_gap=None,
            model_status="greedy_baseline",
        )

    def _extract_gurobi_route(self, dataset: VRPDataset, x: Any, vehicle_index: int) -> Dict[str, Any]:
        sequence = [0]
        current = 0
        visited_guard = set()
        total_distance = 0.0
        load = 0.0

        while True:
            next_node = None
            for candidate in range(dataset.n_customers + 1):
                if candidate == current:
                    continue
                try:
                    value = x[current, candidate, vehicle_index].X
                except Exception:
                    value = 0.0
                if value > 0.5:
                    next_node = candidate
                    break

            if next_node is None:
                if current != 0:
                    total_distance += dataset.distance_matrix[current][0]
                    sequence.append(0)
                break

            total_distance += dataset.distance_matrix[current][next_node]
            sequence.append(next_node)
            if next_node == 0:
                break
            if next_node in visited_guard:
                break
            visited_guard.add(next_node)
            load += dataset.demands[next_node - 1]
            current = next_node

        return self._route_payload(
            dataset=dataset,
            vehicle_index=vehicle_index,
            sequence=sequence,
            distance=total_distance,
            load=load,
        )

    def _format_result(
        self,
        dataset: VRPDataset,
        routes: List[Dict[str, Any]],
        unassigned_customers: List[Dict[str, Any]],
        objective_value: float,
        optimality_gap: Optional[float],
        model_status: Any,
    ) -> Dict[str, Any]:
        assigned_customers = sum(len(route["customers"]) for route in routes)
        total_customers = assigned_customers + len(unassigned_customers)
        total_distance = sum(route["distance"] for route in routes)
        return {
            "summary": {
                "total_customers": total_customers,
                "assigned_customers": assigned_customers,
                "unassigned_customers": len(unassigned_customers),
                "used_vehicles": len(routes),
                "total_distance": round(total_distance, 4),
                "assignment_rate": round(assigned_customers / total_customers, 4) if total_customers else 0.0,
                "objective_value": round(float(objective_value), 4),
                "optimality_gap": optimality_gap,
                "model_status": model_status,
            },
            "routes": routes,
            "unassigned_customers": unassigned_customers,
            "diagnostics": {
                "unassigned_reason_distribution": self._reason_distribution(unassigned_customers),
                "max_exact_customers": MAX_EXACT_CUSTOMERS,
            },
        }

    def _route_payload(
        self,
        dataset: VRPDataset,
        vehicle_index: int,
        sequence: Sequence[int],
        distance: float,
        load: float,
    ) -> Dict[str, Any]:
        customers = [node for node in sequence if node != 0]
        return {
            "vehicle_index": vehicle_index,
            "node_sequence": list(sequence),
            "node_labels": [dataset.node_labels[node] if node < len(dataset.node_labels) else str(node) for node in sequence],
            "customers": customers,
            "distance": round(distance, 4),
            "load": round(load, 4),
            "capacity": round(dataset.vehicle_capacity, 4),
            "capacity_utilization": round(load / dataset.vehicle_capacity, 4) if dataset.vehicle_capacity else 0.0,
        }

    def _unassigned_customer_payload(self, dataset: VRPDataset, customer: int) -> Dict[str, Any]:
        demand = dataset.demands[customer - 1]
        if demand > dataset.vehicle_capacity:
            reason = "CUSTOMER_DEMAND_EXCEEDS_VEHICLE_CAPACITY"
        else:
            reason = "FLEET_CAPACITY_EXHAUSTED"
        return {
            "customer_index": customer,
            "label": dataset.node_labels[customer] if customer < len(dataset.node_labels) else str(customer),
            "demand": round(demand, 4),
            "unassigned_reason": reason,
        }

    def _validate_dataset(self, dataset: VRPDataset) -> Optional[str]:
        if dataset.n_customers < 1:
            return "NO_CUSTOMERS"
        if dataset.n_customers > MAX_EXACT_CUSTOMERS:
            return "CUSTOMER_COUNT_EXCEEDS_SMALL_EXACT_LIMIT"
        if dataset.n_vehicles < 1:
            return "NO_VEHICLES"
        if dataset.vehicle_capacity <= 0:
            return "NO_POSITIVE_VEHICLE_CAPACITY"
        expected = dataset.n_customers + 1
        if len(dataset.distance_matrix) != expected:
            return "DISTANCE_MATRIX_SHAPE_INVALID"
        if any(len(row) != expected for row in dataset.distance_matrix):
            return "DISTANCE_MATRIX_SHAPE_INVALID"
        if len(dataset.demands) != dataset.n_customers:
            return "DEMAND_LENGTH_INVALID"
        return None

    def _coerce_matrix(self, matrix: Sequence[Sequence[Any]]) -> List[List[float]]:
        return [[max(0.0, self._coerce_float(value, 0.0)) for value in row] for row in matrix]

    def _euclidean_matrix(self, depot: Sequence[Any], customers: Sequence[Sequence[Any]]) -> List[List[float]]:
        points = [self._point_tuple(depot)] + [self._point_tuple(customer) for customer in customers]
        return self._point_distance_matrix(points, self._euclidean_distance)

    def _haversine_matrix(
        self,
        depot: Tuple[float, float],
        customers: Sequence[Tuple[float, float]],
    ) -> List[List[float]]:
        points = [depot] + list(customers)
        return self._point_distance_matrix(points, self._haversine_km)

    def _point_distance_matrix(self, points: Sequence[Tuple[float, float]], fn) -> List[List[float]]:
        matrix = []
        for source in points:
            row = []
            for target in points:
                row.append(round(float(fn(source, target)), 4))
            matrix.append(row)
        return matrix

    def _euclidean_distance(self, source: Tuple[float, float], target: Tuple[float, float]) -> float:
        return math.sqrt((source[0] - target[0]) ** 2 + (source[1] - target[1]) ** 2)

    def _haversine_km(self, source: Tuple[float, float], target: Tuple[float, float]) -> float:
        lng1, lat1 = source
        lng2, lat2 = target
        radius_km = 6371.0088
        d_lat = math.radians(lat2 - lat1)
        d_lng = math.radians(lng2 - lng1)
        a = (
            math.sin(d_lat / 2) ** 2
            + math.cos(math.radians(lat1))
            * math.cos(math.radians(lat2))
            * math.sin(d_lng / 2) ** 2
        )
        return radius_km * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)) * 1.18

    def _point_tuple(self, value: Sequence[Any]) -> Tuple[float, float]:
        return (self._coerce_float(value[0], 0.0), self._coerce_float(value[1], 0.0))

    def _safe_gurobi_status(self, status: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "available": bool(status.get("available")),
            "provider_status": status.get("provider_status"),
            "fallback_reason": status.get("fallback_reason"),
            "checks": status.get("checks", {}),
        }

    def _reason_distribution(self, items: Sequence[Dict[str, Any]]) -> Dict[str, int]:
        result: Dict[str, int] = {}
        for item in items:
            reason = str(item.get("unassigned_reason") or "UNKNOWN")
            result[reason] = result.get(reason, 0) + 1
        return result

    def _coerce_float(self, value: Any, default: float = 0.0) -> float:
        try:
            if value is None or value == "":
                return default
            return float(value)
        except (TypeError, ValueError):
            return default


_service: Optional[GurobiVRPService] = None


def get_gurobi_vrp_service() -> GurobiVRPService:
    global _service
    if _service is None:
        _service = GurobiVRPService()
    return _service
