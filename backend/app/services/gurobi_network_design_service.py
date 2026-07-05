"""Small network-design MILP demo for Gurobi phase 2.

The service models a capacitated facility-location problem (CFLP) for a small
logistics network. It can consume payload data or a bounded sample derived from
`shipment_facts`.
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple

from sqlalchemy import func

from app.models import ShipmentFact
from app.services.gurobi_capability_service import get_gurobi_capability_service


SHIPMENT_FACT_STATUSES = ("assigned", "pending", "in_transit", "delivered")
MAX_NETWORK_CUSTOMERS = 12
MAX_NETWORK_CANDIDATES = 8


@dataclass
class NetworkCustomer:
    id: Any
    name: str
    demand: float
    lat: Optional[float] = None
    lon: Optional[float] = None
    data_source: str = "payload"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "demand": round(self.demand, 4),
            "lat": self.lat,
            "lon": self.lon,
            "data_source": self.data_source,
        }


@dataclass
class NetworkCandidate:
    id: Any
    name: str
    capacity: float
    fixed_cost: float
    lat: Optional[float] = None
    lon: Optional[float] = None
    data_source: str = "payload"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "capacity": round(self.capacity, 4),
            "fixed_cost": round(self.fixed_cost, 4),
            "lat": self.lat,
            "lon": self.lon,
            "data_source": self.data_source,
        }


@dataclass
class NetworkDesignDataset:
    customers: List[NetworkCustomer]
    candidates: List[NetworkCandidate]
    distance_matrix: List[List[float]]
    transport_cost_per_km: float
    max_facilities: Optional[int]
    data_source: str
    distance_source: str
    authenticity_level: str
    metadata: Dict[str, Any]


class GurobiNetworkDesignService:
    """Capacitated facility-location demo with explicit fallback semantics."""

    def __init__(self, capability_service=None):
        self.capability_service = capability_service or get_gurobi_capability_service()

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

        if preferred_solver in {"greedy", "baseline", "nearest"}:
            result = self._solve_with_greedy(dataset)
            result["solver"] = "greedy_facility_capacity"
            result["provider_status"] = "ok"
            result["fallback_reason"] = None
            result["solver_quality"] = "heuristic_baseline"
        elif preferred_solver in {"auto", "gurobi"} and gurobi_status["available"]:
            try:
                result = self._solve_with_gurobi(dataset, time_limit=float(payload.get("time_limit") or 30.0))
                result["solver"] = "gurobi_cflp_milp"
                result["provider_status"] = "ok"
                result["fallback_reason"] = None
                result["solver_quality"] = "exact_milp"
            except Exception as exc:
                if not allow_fallback:
                    raise
                result = self._solve_with_greedy(dataset)
                result["solver"] = "greedy_facility_capacity_fallback"
                result["provider_status"] = "degraded"
                result["fallback_reason"] = f"GUROBI_NETWORK_SOLVE_FAILED:{exc.__class__.__name__}"
                result["solver_quality"] = "heuristic_fallback"
        else:
            if preferred_solver == "gurobi" and not allow_fallback:
                return {
                    "success": False,
                    "error": gurobi_status["fallback_reason"] or "GUROBI_UNAVAILABLE",
                    "solver": "gurobi_cflp_milp",
                    "provider_status": "degraded",
                    "fallback_reason": gurobi_status["fallback_reason"] or "GUROBI_UNAVAILABLE",
                    "authenticity_level": dataset.authenticity_level,
                    "gurobi_status": self._safe_gurobi_status(gurobi_status),
                }
            result = self._solve_with_greedy(dataset)
            result["solver"] = "greedy_facility_capacity_fallback"
            result["provider_status"] = "degraded"
            result["fallback_reason"] = gurobi_status["fallback_reason"] or "GUROBI_UNAVAILABLE"
            result["solver_quality"] = "heuristic_fallback"

        elapsed = time.perf_counter() - started
        result.update(
            {
                "success": True,
                "data_source": dataset.data_source,
                "distance_source": dataset.distance_source,
                "path_source": "facility_customer_assignment",
                "authenticity_level": dataset.authenticity_level
                if result["provider_status"] == "ok"
                else "C",
                "solve_time_seconds": round(elapsed, 6),
                "gurobi_status": self._safe_gurobi_status(gurobi_status),
                "input_summary": {
                    "customers": len(dataset.customers),
                    "candidates": len(dataset.candidates),
                    "total_demand": round(sum(customer.demand for customer in dataset.customers), 4),
                    "total_capacity": round(sum(candidate.capacity for candidate in dataset.candidates), 4),
                    "transport_cost_per_km": dataset.transport_cost_per_km,
                    "max_facilities": dataset.max_facilities,
                    **dataset.metadata,
                },
                "constraints": [
                    "customer_assigned_or_unmet",
                    "open_facility_capacity",
                    "assignment_only_to_open_facility",
                    "optional_max_facilities",
                ],
            }
        )
        return result

    def demo_payload(self) -> Dict[str, Any]:
        return {
            "solver": "auto",
            "transport_cost_per_km": 2.4,
            "max_facilities": 2,
            "customers": [
                {"id": "C-GZ", "name": "广州需求", "demand": 120, "lat": 23.1291, "lon": 113.2644},
                {"id": "C-SZ", "name": "深圳需求", "demand": 160, "lat": 22.5431, "lon": 114.0579},
                {"id": "C-DG", "name": "东莞需求", "demand": 90, "lat": 23.0207, "lon": 113.7518},
                {"id": "C-ZH", "name": "珠海需求", "demand": 70, "lat": 22.2711, "lon": 113.5767},
            ],
            "candidates": [
                {"id": "F-GZ", "name": "广州中心仓", "capacity": 260, "fixed_cost": 46000, "lat": 23.1291, "lon": 113.2644},
                {"id": "F-SZ", "name": "深圳前置仓", "capacity": 220, "fixed_cost": 42000, "lat": 22.5431, "lon": 114.0579},
                {"id": "F-FS", "name": "佛山备选仓", "capacity": 180, "fixed_cost": 35000, "lat": 23.0215, "lon": 113.1214},
            ],
            "distance_source": "haversine_payload",
            "data_source": "payload_demo",
        }

    def database_dataset_payload(self, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Return a bounded real shipment_facts network dataset for UI previews."""
        payload = {**(payload or {}), "use_database": True}
        dataset = self._build_dataset_from_database(payload)
        source_mode = dataset.metadata.get("source_mode")
        is_real = dataset.data_source == "shipment_fact_od_aggregate" and source_mode == "database_od_aggregate"
        total_demand = sum(customer.demand for customer in dataset.customers)
        total_capacity = sum(candidate.capacity for candidate in dataset.candidates)

        return {
            "success": True,
            "status": "success",
            "customers": [customer.to_dict() for customer in dataset.customers],
            "candidates": [candidate.to_dict() for candidate in dataset.candidates],
            "distance_matrix": dataset.distance_matrix,
            "transport_cost_per_km": dataset.transport_cost_per_km,
            "max_facilities": dataset.max_facilities,
            "data_source": dataset.data_source,
            "distance_source": dataset.distance_source if is_real else "haversine_payload",
            "path_source": "shipment_fact_city_od_aggregate" if is_real else "synthetic_preview",
            "authenticity_level": dataset.authenticity_level if is_real else "D",
            "fallback_reason": (
                "coordinate_city_aggregate_not_navigation_path"
                if is_real
                else "SHIPMENT_FACT_NETWORK_DATA_UNAVAILABLE_USING_DEMO"
            ),
            "summary": {
                "customers": len(dataset.customers),
                "candidates": len(dataset.candidates),
                "total_demand": round(total_demand, 4),
                "total_capacity": round(total_capacity, 4),
                "capacity_coverage_rate": round(total_capacity / total_demand, 4) if total_demand else 0.0,
                **dataset.metadata,
            },
        }

    def _build_dataset(self, payload: Dict[str, Any]) -> NetworkDesignDataset:
        if payload.get("use_database"):
            return self._build_dataset_from_database(payload)

        if not payload:
            payload = self.demo_payload()

        customers = [
            self._customer_from_payload(item, idx)
            for idx, item in enumerate(payload.get("customers") or self.demo_payload()["customers"], start=1)
        ]
        candidates = [
            self._candidate_from_payload(item, idx)
            for idx, item in enumerate(payload.get("candidates") or self.demo_payload()["candidates"], start=1)
        ]
        distance_matrix = payload.get("distance_matrix")
        if distance_matrix:
            matrix = self._coerce_matrix(distance_matrix)
            distance_source = str(payload.get("distance_source") or "payload_distance_matrix")
            authenticity_level = "B"
        else:
            matrix = self._distance_matrix(customers, candidates)
            distance_source = str(payload.get("distance_source") or "haversine_payload")
            authenticity_level = "C"

        return NetworkDesignDataset(
            customers=customers[:MAX_NETWORK_CUSTOMERS],
            candidates=candidates[:MAX_NETWORK_CANDIDATES],
            distance_matrix=matrix,
            transport_cost_per_km=max(0.0, self._coerce_float(payload.get("transport_cost_per_km"), 2.0)),
            max_facilities=self._optional_int(payload.get("max_facilities")),
            data_source=str(payload.get("data_source") or "payload"),
            distance_source=distance_source,
            authenticity_level=authenticity_level,
            metadata={"source_mode": "payload"},
        )

    def _build_dataset_from_database(self, payload: Dict[str, Any]) -> NetworkDesignDataset:
        customer_limit = min(max(int(payload.get("customer_limit") or 6), 1), MAX_NETWORK_CUSTOMERS)
        candidate_limit = min(max(int(payload.get("candidate_limit") or 4), 1), MAX_NETWORK_CANDIDATES)
        shipment_facts_total = ShipmentFact.query.count()

        customer_rows = (
            ShipmentFact.query.with_entities(
                ShipmentFact.destination_city_std,
                func.avg(ShipmentFact.destination_lat),
                func.avg(ShipmentFact.destination_lng),
                func.count(ShipmentFact.id),
                func.sum(func.coalesce(ShipmentFact.weight_kg, 1.0)),
            )
            .filter(
                ShipmentFact.standard_status.in_(SHIPMENT_FACT_STATUSES),
                ShipmentFact.destination_city_std.isnot(None),
                ShipmentFact.destination_lat.isnot(None),
                ShipmentFact.destination_lng.isnot(None),
            )
            .group_by(ShipmentFact.destination_city_std)
            .order_by(func.count(ShipmentFact.id).desc())
            .limit(customer_limit)
            .all()
        )
        candidate_rows = (
            ShipmentFact.query.with_entities(
                ShipmentFact.origin_city_std,
                func.avg(ShipmentFact.origin_lat),
                func.avg(ShipmentFact.origin_lng),
                func.count(ShipmentFact.id),
                func.sum(func.coalesce(ShipmentFact.weight_kg, 1.0)),
            )
            .filter(
                ShipmentFact.standard_status.in_(SHIPMENT_FACT_STATUSES),
                ShipmentFact.origin_city_std.isnot(None),
                ShipmentFact.origin_lat.isnot(None),
                ShipmentFact.origin_lng.isnot(None),
            )
            .group_by(ShipmentFact.origin_city_std)
            .order_by(func.count(ShipmentFact.id).desc())
            .limit(candidate_limit)
            .all()
        )

        if not customer_rows or not candidate_rows:
            return self._build_dataset(self.demo_payload())

        customers = [
            NetworkCustomer(
                id=f"C-{idx}",
                name=row[0] or f"customer-{idx}",
                lat=float(row[1]),
                lon=float(row[2]),
                demand=max(1.0, self._coerce_float(row[4], self._coerce_float(row[3], 1.0)) / 1000.0),
                data_source="shipment_fact_destination_aggregate",
            )
            for idx, row in enumerate(customer_rows, start=1)
        ]
        total_customer_demand = sum(customer.demand for customer in customers)
        candidates = []
        for idx, row in enumerate(candidate_rows, start=1):
            historical_weight_tons = max(
                1.0,
                self._coerce_float(row[4], self._coerce_float(row[3], 1.0)) / 1000.0,
            )
            capacity = max(historical_weight_tons * 1.2, total_customer_demand / max(1, candidate_limit))
            candidates.append(
                NetworkCandidate(
                    id=f"F-{idx}",
                    name=row[0] or f"facility-{idx}",
                    lat=float(row[1]),
                    lon=float(row[2]),
                    capacity=capacity,
                    fixed_cost=round(30000 + capacity * 80, 2),
                    data_source="shipment_fact_origin_aggregate",
                )
            )

        return NetworkDesignDataset(
            customers=customers,
            candidates=candidates,
            distance_matrix=self._distance_matrix(customers, candidates),
            transport_cost_per_km=max(0.0, self._coerce_float(payload.get("transport_cost_per_km"), 2.0)),
            max_facilities=self._optional_int(payload.get("max_facilities")),
            data_source="shipment_fact_od_aggregate",
            distance_source="haversine_corrected",
            authenticity_level="C",
            metadata={
                "source_mode": "database_od_aggregate",
                "customer_limit": customer_limit,
                "candidate_limit": candidate_limit,
                "shipment_facts_total": int(shipment_facts_total),
                "customer_bucket_count": len(customer_rows),
                "candidate_bucket_count": len(candidate_rows),
            },
        )

    def _solve_with_gurobi(self, dataset: NetworkDesignDataset, time_limit: float) -> Dict[str, Any]:
        import gurobipy as gp
        from gurobipy import GRB

        customer_range = range(len(dataset.customers))
        candidate_range = range(len(dataset.candidates))
        total_demand = sum(customer.demand for customer in dataset.customers)
        max_distance = max(max(row) for row in dataset.distance_matrix) if dataset.distance_matrix else 1.0
        unmet_penalty = max_distance * dataset.transport_cost_per_km * max(total_demand, 1.0) * 10.0

        model = gp.Model("logistics_network_design_cflp")
        model.setParam("OutputFlag", 0)
        model.setParam("TimeLimit", time_limit)

        open_facility = model.addVars(candidate_range, vtype=GRB.BINARY, name="open")
        assign = model.addVars(customer_range, candidate_range, vtype=GRB.BINARY, name="assign")
        unmet = model.addVars(customer_range, vtype=GRB.BINARY, name="unmet")

        for i in customer_range:
            model.addConstr(
                gp.quicksum(assign[i, j] for j in candidate_range) + unmet[i] == 1,
                name=f"assign_or_unmet_{i}",
            )

        for j in candidate_range:
            model.addConstr(
                gp.quicksum(dataset.customers[i].demand * assign[i, j] for i in customer_range)
                <= dataset.candidates[j].capacity * open_facility[j],
                name=f"capacity_{j}",
            )
            for i in customer_range:
                model.addConstr(assign[i, j] <= open_facility[j], name=f"open_link_{i}_{j}")

        if dataset.max_facilities:
            model.addConstr(
                gp.quicksum(open_facility[j] for j in candidate_range) <= dataset.max_facilities,
                name="max_facilities",
            )

        model.setObjective(
            gp.quicksum(dataset.candidates[j].fixed_cost * open_facility[j] for j in candidate_range)
            + gp.quicksum(
                dataset.customers[i].demand
                * dataset.distance_matrix[i][j]
                * dataset.transport_cost_per_km
                * assign[i, j]
                for i in customer_range
                for j in candidate_range
            )
            + unmet_penalty * gp.quicksum(dataset.customers[i].demand * unmet[i] for i in customer_range),
            GRB.MINIMIZE,
        )
        model.optimize()

        if model.status not in {GRB.OPTIMAL, GRB.TIME_LIMIT, GRB.SOLUTION_LIMIT}:
            raise RuntimeError(f"Gurobi network design failed with status {model.status}")

        open_indices = [j for j in candidate_range if open_facility[j].X > 0.5]
        assignments = []
        unassigned = []
        for i in customer_range:
            assigned_j = None
            for j in candidate_range:
                if assign[i, j].X > 0.5:
                    assigned_j = j
                    break
            if assigned_j is None:
                unassigned.append(self._unassigned_customer(dataset.customers[i], "NETWORK_CAPACITY_OR_FACILITY_LIMIT"))
            else:
                assignments.append(self._assignment_payload(dataset, i, assigned_j))

        return self._format_result(
            dataset=dataset,
            open_indices=open_indices,
            assignments=assignments,
            unassigned_customers=unassigned,
            objective_value=float(model.ObjVal),
            optimality_gap=float(model.MIPGap) if hasattr(model, "MIPGap") else 0.0,
            model_status=getattr(model, "status", None),
        )

    def _solve_with_greedy(self, dataset: NetworkDesignDataset) -> Dict[str, Any]:
        candidate_scores = sorted(
            range(len(dataset.candidates)),
            key=lambda idx: (dataset.candidates[idx].fixed_cost, -dataset.candidates[idx].capacity),
        )
        max_facilities = dataset.max_facilities or len(dataset.candidates)
        open_indices: List[int] = []
        remaining_capacity: Dict[int, float] = {}
        for idx in candidate_scores:
            if len(open_indices) >= max_facilities:
                break
            open_indices.append(idx)
            remaining_capacity[idx] = dataset.candidates[idx].capacity
            if sum(remaining_capacity.values()) >= sum(customer.demand for customer in dataset.customers):
                break

        if not open_indices and dataset.candidates:
            open_indices = [candidate_scores[0]]
            remaining_capacity[open_indices[0]] = dataset.candidates[open_indices[0]].capacity

        assignments = []
        unassigned = []
        customer_order = sorted(range(len(dataset.customers)), key=lambda idx: dataset.customers[idx].demand, reverse=True)
        for i in customer_order:
            feasible = [
                j for j in open_indices if remaining_capacity.get(j, 0.0) >= dataset.customers[i].demand
            ]
            if not feasible:
                unassigned.append(self._unassigned_customer(dataset.customers[i], "NETWORK_CAPACITY_OR_FACILITY_LIMIT"))
                continue
            best_j = min(feasible, key=lambda j: dataset.distance_matrix[i][j])
            assignments.append(self._assignment_payload(dataset, i, best_j))
            remaining_capacity[best_j] -= dataset.customers[i].demand

        total_fixed = sum(dataset.candidates[j].fixed_cost for j in open_indices)
        transport = sum(item["transport_cost"] for item in assignments)
        penalty = sum(item["demand"] for item in unassigned) * 100000.0

        return self._format_result(
            dataset=dataset,
            open_indices=open_indices,
            assignments=assignments,
            unassigned_customers=unassigned,
            objective_value=total_fixed + transport + penalty,
            optimality_gap=None,
            model_status="greedy_baseline",
        )

    def _format_result(
        self,
        dataset: NetworkDesignDataset,
        open_indices: Sequence[int],
        assignments: Sequence[Dict[str, Any]],
        unassigned_customers: Sequence[Dict[str, Any]],
        objective_value: float,
        optimality_gap: Optional[float],
        model_status: Any,
    ) -> Dict[str, Any]:
        selected = [self._facility_payload(dataset, idx, assignments) for idx in open_indices]
        fixed_cost = sum(item["fixed_cost"] for item in selected)
        transport_cost = sum(item["transport_cost"] for item in assignments)
        assigned_demand = sum(item["demand"] for item in assignments)
        total_demand = assigned_demand + sum(item["demand"] for item in unassigned_customers)
        return {
            "summary": {
                "selected_facilities": len(selected),
                "assigned_customers": len(assignments),
                "unassigned_customers": len(unassigned_customers),
                "assigned_demand": round(assigned_demand, 4),
                "total_demand": round(total_demand, 4),
                "demand_coverage_rate": round(assigned_demand / total_demand, 4) if total_demand else 0.0,
                "fixed_cost": round(fixed_cost, 4),
                "transport_cost": round(transport_cost, 4),
                "total_cost": round(fixed_cost + transport_cost, 4),
                "objective_value": round(float(objective_value), 4),
                "optimality_gap": optimality_gap,
                "model_status": model_status,
            },
            "selected_facilities": selected,
            "assignments": list(assignments),
            "unassigned_customers": list(unassigned_customers),
            "diagnostics": {
                "unassigned_reason_distribution": self._reason_distribution(unassigned_customers),
                "max_network_customers": MAX_NETWORK_CUSTOMERS,
                "max_network_candidates": MAX_NETWORK_CANDIDATES,
            },
        }

    def _facility_payload(
        self,
        dataset: NetworkDesignDataset,
        idx: int,
        assignments: Sequence[Dict[str, Any]],
    ) -> Dict[str, Any]:
        candidate = dataset.candidates[idx]
        used_capacity = sum(item["demand"] for item in assignments if item["facility_id"] == candidate.id)
        return {
            **candidate.to_dict(),
            "used_capacity": round(used_capacity, 4),
            "utilization": round(used_capacity / candidate.capacity, 4) if candidate.capacity else 0.0,
        }

    def _assignment_payload(self, dataset: NetworkDesignDataset, customer_idx: int, candidate_idx: int) -> Dict[str, Any]:
        customer = dataset.customers[customer_idx]
        candidate = dataset.candidates[candidate_idx]
        distance = dataset.distance_matrix[customer_idx][candidate_idx]
        transport_cost = customer.demand * distance * dataset.transport_cost_per_km
        return {
            "customer_id": customer.id,
            "customer_name": customer.name,
            "facility_id": candidate.id,
            "facility_name": candidate.name,
            "demand": round(customer.demand, 4),
            "distance_km": round(distance, 4),
            "transport_cost": round(transport_cost, 4),
        }

    def _unassigned_customer(self, customer: NetworkCustomer, reason: str) -> Dict[str, Any]:
        return {
            **customer.to_dict(),
            "unassigned_reason": reason,
        }

    def _validate_dataset(self, dataset: NetworkDesignDataset) -> Optional[str]:
        if not dataset.customers:
            return "NO_NETWORK_CUSTOMERS"
        if not dataset.candidates:
            return "NO_NETWORK_CANDIDATES"
        if len(dataset.customers) > MAX_NETWORK_CUSTOMERS:
            return "NETWORK_CUSTOMER_COUNT_EXCEEDS_DEMO_LIMIT"
        if len(dataset.candidates) > MAX_NETWORK_CANDIDATES:
            return "NETWORK_CANDIDATE_COUNT_EXCEEDS_DEMO_LIMIT"
        if any(customer.demand <= 0 for customer in dataset.customers):
            return "CUSTOMER_DEMAND_MUST_BE_POSITIVE"
        if any(candidate.capacity <= 0 for candidate in dataset.candidates):
            return "FACILITY_CAPACITY_MUST_BE_POSITIVE"
        if len(dataset.distance_matrix) != len(dataset.customers):
            return "DISTANCE_MATRIX_SHAPE_INVALID"
        if any(len(row) != len(dataset.candidates) for row in dataset.distance_matrix):
            return "DISTANCE_MATRIX_SHAPE_INVALID"
        return None

    def _customer_from_payload(self, item: Dict[str, Any], idx: int) -> NetworkCustomer:
        return NetworkCustomer(
            id=item.get("id") or idx,
            name=str(item.get("name") or item.get("city") or f"customer-{idx}"),
            demand=max(0.0, self._coerce_float(item.get("demand"), 0.0)),
            lat=self._optional_float(item.get("lat") or item.get("latitude")),
            lon=self._optional_float(item.get("lon") or item.get("lng") or item.get("longitude")),
            data_source=str(item.get("data_source") or "payload"),
        )

    def _candidate_from_payload(self, item: Dict[str, Any], idx: int) -> NetworkCandidate:
        return NetworkCandidate(
            id=item.get("id") or idx,
            name=str(item.get("name") or item.get("city") or f"facility-{idx}"),
            capacity=max(0.0, self._coerce_float(item.get("capacity"), 0.0)),
            fixed_cost=max(0.0, self._coerce_float(item.get("fixed_cost"), 0.0)),
            lat=self._optional_float(item.get("lat") or item.get("latitude")),
            lon=self._optional_float(item.get("lon") or item.get("lng") or item.get("longitude")),
            data_source=str(item.get("data_source") or "payload"),
        )

    def _distance_matrix(
        self,
        customers: Sequence[NetworkCustomer],
        candidates: Sequence[NetworkCandidate],
    ) -> List[List[float]]:
        matrix = []
        for customer in customers:
            row = []
            for candidate in candidates:
                if customer.lat is None or customer.lon is None or candidate.lat is None or candidate.lon is None:
                    row.append(0.0)
                else:
                    row.append(round(self._haversine_km((customer.lon, customer.lat), (candidate.lon, candidate.lat)), 4))
            matrix.append(row)
        return matrix

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

    def _coerce_matrix(self, matrix: Sequence[Sequence[Any]]) -> List[List[float]]:
        return [[max(0.0, self._coerce_float(value, 0.0)) for value in row] for row in matrix]

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

    def _optional_int(self, value: Any) -> Optional[int]:
        if value is None or value == "":
            return None
        try:
            return max(1, int(value))
        except (TypeError, ValueError):
            return None

    def _optional_float(self, value: Any) -> Optional[float]:
        if value is None or value == "":
            return None
        return self._coerce_float(value, 0.0)

    def _coerce_float(self, value: Any, default: float = 0.0) -> float:
        try:
            if value is None or value == "":
                return default
            return float(value)
        except (TypeError, ValueError):
            return default


_service: Optional[GurobiNetworkDesignService] = None


def get_gurobi_network_design_service() -> GurobiNetworkDesignService:
    global _service
    if _service is None:
        _service = GurobiNetworkDesignService()
    return _service
