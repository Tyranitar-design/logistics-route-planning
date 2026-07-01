"""Small vehicle-assignment optimization demo for Gurobi phase 2.

The service solves a bounded assignment problem:

- each order is either assigned to one vehicle or marked unassigned
- vehicle weight/volume capacities are hard constraints
- objective prefers high-priority/high-value assigned orders

Gurobi is used when available. A transparent greedy fallback keeps the API
usable while exposing the degraded solver status.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence

from app.models import Order, ShipmentFact, Vehicle
from app.services.gurobi_capability_service import get_gurobi_capability_service


DISPATCHABLE_ORDER_STATUSES = ("pending", "assigned", "待调度", "待配送", "待分配")
SHIPMENT_FACT_DISPATCHABLE_STATUSES = ("assigned", "pending", "in_transit")
AVAILABLE_VEHICLE_STATUSES = ("available", "idle", "空闲")


@dataclass
class AssignmentOrder:
    id: Any
    order_number: str
    weight_tons: float
    volume_m3: float
    priority: str = "normal"
    freight: float = 0.0
    data_source: str = "payload"

    @property
    def value(self) -> float:
        priority_scores = {
            "urgent": 120.0,
            "high": 100.0,
            "normal": 70.0,
            "low": 40.0,
            "加急": 120.0,
            "高": 100.0,
            "普通": 70.0,
            "低": 40.0,
        }
        base = priority_scores.get(str(self.priority).lower(), priority_scores.get(self.priority, 70.0))
        return base + max(0.0, self.freight) / 100.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "order_number": self.order_number,
            "weight_tons": round(self.weight_tons, 4),
            "volume_m3": round(self.volume_m3, 4),
            "priority": self.priority,
            "freight": round(self.freight, 2),
            "data_source": self.data_source,
            "value": round(self.value, 4),
        }


@dataclass
class AssignmentVehicle:
    id: Any
    plate_number: str
    capacity_weight_tons: float
    capacity_volume_m3: float
    status: str = "available"
    data_source: str = "payload"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "plate_number": self.plate_number,
            "capacity_weight_tons": round(self.capacity_weight_tons, 4),
            "capacity_volume_m3": round(self.capacity_volume_m3, 4),
            "status": self.status,
            "data_source": self.data_source,
        }


class GurobiAssignmentService:
    """Small exact assignment demo with explicit solver truth metadata."""

    def __init__(self, capability_service=None):
        self.capability_service = capability_service or get_gurobi_capability_service()

    def solve(self, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        payload = payload or {}
        started = time.perf_counter()

        orders = self._load_orders(payload)
        vehicles = self._load_vehicles(payload)
        max_orders_per_vehicle = int(payload.get("max_orders_per_vehicle") or 999)
        preferred_solver = str(payload.get("solver") or "auto").lower()
        allow_fallback = bool(payload.get("allow_fallback", True))

        validation = self._validate_inputs(orders, vehicles)
        if validation:
            return {
                "success": False,
                "error": validation,
                "solver": None,
                "provider_status": "degraded",
                "fallback_reason": validation,
                "authenticity_level": "C",
            }

        gurobi_status = self.capability_service.check(run_smoke=False)

        if preferred_solver in {"greedy", "greedy_capacity", "greedy_capacity_fallback"}:
            result = self._solve_with_greedy(orders, vehicles, max_orders_per_vehicle)
            result["solver"] = "greedy_capacity"
            result["provider_status"] = "ok"
            result["fallback_reason"] = None
            result["authenticity_level"] = "C"
        elif preferred_solver in {"auto", "gurobi"} and gurobi_status["available"]:
            try:
                result = self._solve_with_gurobi(orders, vehicles, max_orders_per_vehicle)
                result["solver"] = "gurobi"
                result["provider_status"] = "ok"
                result["fallback_reason"] = None
                result["authenticity_level"] = "A"
            except Exception as exc:
                if not allow_fallback:
                    raise
                result = self._solve_with_greedy(orders, vehicles, max_orders_per_vehicle)
                result["solver"] = "greedy_capacity_fallback"
                result["provider_status"] = "degraded"
                result["fallback_reason"] = f"GUROBI_SOLVE_FAILED:{exc.__class__.__name__}"
                result["authenticity_level"] = "C"
        else:
            if preferred_solver == "gurobi" and not allow_fallback:
                return {
                    "success": False,
                    "error": gurobi_status["fallback_reason"] or "GUROBI_UNAVAILABLE",
                    "solver": "gurobi",
                    "provider_status": "degraded",
                    "fallback_reason": gurobi_status["fallback_reason"] or "GUROBI_UNAVAILABLE",
                    "authenticity_level": "C",
                    "gurobi_status": gurobi_status,
                }
            result = self._solve_with_greedy(orders, vehicles, max_orders_per_vehicle)
            result["solver"] = "greedy_capacity_fallback"
            result["provider_status"] = "degraded"
            result["fallback_reason"] = gurobi_status["fallback_reason"] or "GUROBI_UNAVAILABLE"
            result["authenticity_level"] = "C"

        elapsed = time.perf_counter() - started
        result.update(
            {
                "success": True,
                "data_source": self._infer_data_source(orders, vehicles),
                "solve_time_seconds": round(elapsed, 6),
                "gurobi_status": {
                    "available": gurobi_status["available"],
                    "provider_status": gurobi_status["provider_status"],
                    "fallback_reason": gurobi_status["fallback_reason"],
                    "checks": gurobi_status["checks"],
                },
                "input_summary": {
                    "orders": len(orders),
                    "vehicles": len(vehicles),
                    "total_order_weight_tons": round(sum(o.weight_tons for o in orders), 4),
                    "total_order_volume_m3": round(sum(o.volume_m3 for o in orders), 4),
                    "total_vehicle_weight_capacity_tons": round(
                        sum(v.capacity_weight_tons for v in vehicles), 4
                    ),
                    "total_vehicle_volume_capacity_m3": round(
                        sum(v.capacity_volume_m3 for v in vehicles), 4
                    ),
                },
            }
        )
        return result

    def demo_payload(self) -> Dict[str, Any]:
        return {
            "solver": "auto",
            "max_orders_per_vehicle": 3,
            "orders": [
                {"id": "O-1001", "weight_tons": 2.0, "volume_m3": 7.0, "priority": "urgent", "freight": 1800},
                {"id": "O-1002", "weight_tons": 3.5, "volume_m3": 8.0, "priority": "high", "freight": 1600},
                {"id": "O-1003", "weight_tons": 1.0, "volume_m3": 2.5, "priority": "normal", "freight": 700},
                {"id": "O-1004", "weight_tons": 4.2, "volume_m3": 12.0, "priority": "high", "freight": 2100},
                {"id": "O-1005", "weight_tons": 6.0, "volume_m3": 16.0, "priority": "low", "freight": 900},
            ],
            "vehicles": [
                {"id": "V-01", "plate_number": "粤A-Demo01", "capacity_weight_tons": 6.0, "capacity_volume_m3": 18.0},
                {"id": "V-02", "plate_number": "粤B-Demo02", "capacity_weight_tons": 8.0, "capacity_volume_m3": 24.0},
            ],
        }

    def _load_orders(self, payload: Dict[str, Any]) -> List[AssignmentOrder]:
        raw_orders = payload.get("orders")
        if raw_orders:
            return [self._order_from_payload(item, idx) for idx, item in enumerate(raw_orders, start=1)]

        if payload.get("use_database"):
            limit = min(max(int(payload.get("limit") or 20), 1), 100)
            source = str(payload.get("data_source") or "auto").lower()
            if source in {"auto", "shipment_facts", "shipment_fact"} and ShipmentFact.query.count() > 0:
                facts = (
                    ShipmentFact.query.filter(
                        ShipmentFact.standard_status.in_(SHIPMENT_FACT_DISPATCHABLE_STATUSES)
                    )
                    .order_by(ShipmentFact.shipped_at.desc().nullslast(), ShipmentFact.id.desc())
                    .limit(limit)
                    .all()
                )
                return [self._order_from_fact(fact) for fact in facts]

            legacy_orders = (
                Order.query.filter(Order.status.in_(DISPATCHABLE_ORDER_STATUSES))
                .order_by(Order.created_at.desc().nullslast(), Order.id.desc())
                .limit(limit)
                .all()
            )
            return [self._order_from_legacy(order) for order in legacy_orders]

        return [self._order_from_payload(item, idx) for idx, item in enumerate(self.demo_payload()["orders"], start=1)]

    def _load_vehicles(self, payload: Dict[str, Any]) -> List[AssignmentVehicle]:
        raw_vehicles = payload.get("vehicles")
        if raw_vehicles:
            return [self._vehicle_from_payload(item, idx) for idx, item in enumerate(raw_vehicles, start=1)]

        if payload.get("use_database"):
            vehicles = Vehicle.query.filter(Vehicle.status.in_(AVAILABLE_VEHICLE_STATUSES)).all()
            return [self._vehicle_from_model(vehicle) for vehicle in vehicles]

        return [
            self._vehicle_from_payload(item, idx)
            for idx, item in enumerate(self.demo_payload()["vehicles"], start=1)
        ]

    def _solve_with_gurobi(
        self,
        orders: Sequence[AssignmentOrder],
        vehicles: Sequence[AssignmentVehicle],
        max_orders_per_vehicle: int,
    ) -> Dict[str, Any]:
        import gurobipy as gp
        from gurobipy import GRB

        model = gp.Model("logistics_vehicle_assignment")
        model.setParam("OutputFlag", 0)

        order_range = range(len(orders))
        vehicle_range = range(len(vehicles))
        x = model.addVars(order_range, vehicle_range, vtype=GRB.BINARY, name="assign")
        unassigned = model.addVars(order_range, vtype=GRB.BINARY, name="unassigned")

        for i in order_range:
            model.addConstr(
                gp.quicksum(x[i, j] for j in vehicle_range) + unassigned[i] == 1,
                name=f"assign_once_{i}",
            )

        for j, vehicle in enumerate(vehicles):
            model.addConstr(
                gp.quicksum(orders[i].weight_tons * x[i, j] for i in order_range)
                <= vehicle.capacity_weight_tons,
                name=f"weight_capacity_{j}",
            )
            model.addConstr(
                gp.quicksum(orders[i].volume_m3 * x[i, j] for i in order_range)
                <= vehicle.capacity_volume_m3,
                name=f"volume_capacity_{j}",
            )
            model.addConstr(
                gp.quicksum(x[i, j] for i in order_range) <= max_orders_per_vehicle,
                name=f"max_orders_{j}",
            )

        model.setObjective(
            gp.quicksum(orders[i].value * x[i, j] for i in order_range for j in vehicle_range)
            - gp.quicksum(orders[i].value * 2.0 * unassigned[i] for i in order_range),
            GRB.MAXIMIZE,
        )
        model.optimize()

        if model.status not in {GRB.OPTIMAL, GRB.TIME_LIMIT, GRB.SOLUTION_LIMIT}:
            raise RuntimeError(f"Gurobi assignment failed with status {model.status}")

        assignments = []
        for j, vehicle in enumerate(vehicles):
            assigned_orders = [orders[i] for i in order_range if x[i, j].X > 0.5]
            assignments.append(self._build_vehicle_assignment(vehicle, assigned_orders))

        assigned_ids = {order.id for item in assignments for order in item["orders"]}
        unassigned_orders = [
            self._unassigned_payload(order, vehicles)
            for order in orders
            if order.id not in assigned_ids
        ]

        return self._format_result(
            assignments=assignments,
            unassigned_orders=unassigned_orders,
            objective_value=float(model.ObjVal),
            optimality_gap=float(model.MIPGap) if hasattr(model, "MIPGap") else 0.0,
            model_status=getattr(model, "status", None),
        )

    def _solve_with_greedy(
        self,
        orders: Sequence[AssignmentOrder],
        vehicles: Sequence[AssignmentVehicle],
        max_orders_per_vehicle: int,
    ) -> Dict[str, Any]:
        remaining = {
            vehicle.id: {
                "weight": vehicle.capacity_weight_tons,
                "volume": vehicle.capacity_volume_m3,
                "count": max_orders_per_vehicle,
                "orders": [],
            }
            for vehicle in vehicles
        }
        vehicle_by_id = {vehicle.id: vehicle for vehicle in vehicles}
        unassigned = []

        for order in sorted(orders, key=lambda item: item.value, reverse=True):
            best_vehicle_id = None
            best_leftover = None
            for vehicle in vehicles:
                state = remaining[vehicle.id]
                if (
                    state["weight"] >= order.weight_tons
                    and state["volume"] >= order.volume_m3
                    and state["count"] > 0
                ):
                    leftover = (state["weight"] - order.weight_tons) + 0.1 * (
                        state["volume"] - order.volume_m3
                    )
                    if best_leftover is None or leftover < best_leftover:
                        best_leftover = leftover
                        best_vehicle_id = vehicle.id
            if best_vehicle_id is None:
                unassigned.append(self._unassigned_payload(order, vehicles))
                continue

            state = remaining[best_vehicle_id]
            state["orders"].append(order)
            state["weight"] -= order.weight_tons
            state["volume"] -= order.volume_m3
            state["count"] -= 1

        assignments = [
            self._build_vehicle_assignment(vehicle_by_id[vehicle_id], state["orders"])
            for vehicle_id, state in remaining.items()
        ]

        return self._format_result(
            assignments=assignments,
            unassigned_orders=unassigned,
            objective_value=sum(
                order["value"]
                for assignment in assignments
                for order in assignment["orders"]
            ),
            optimality_gap=None,
            model_status="greedy_fallback",
        )

    def _format_result(
        self,
        assignments: List[Dict[str, Any]],
        unassigned_orders: List[Dict[str, Any]],
        objective_value: float,
        optimality_gap: Optional[float],
        model_status: Any,
    ) -> Dict[str, Any]:
        assigned_orders = sum(len(item["orders"]) for item in assignments)
        total_orders = assigned_orders + len(unassigned_orders)
        used_vehicles = sum(1 for item in assignments if item["orders"])
        return {
            "summary": {
                "total_orders": total_orders,
                "assigned_orders": assigned_orders,
                "unassigned_orders": len(unassigned_orders),
                "used_vehicles": used_vehicles,
                "assignment_rate": round(assigned_orders / total_orders, 4) if total_orders else 0.0,
                "objective_value": round(float(objective_value), 4),
                "optimality_gap": optimality_gap,
                "model_status": model_status,
            },
            "assignments": assignments,
            "unassigned_orders": unassigned_orders,
            "diagnostics": {
                "unassigned_reason_distribution": self._reason_distribution(unassigned_orders),
                "hard_constraints": [
                    "each_order_assigned_at_most_once",
                    "vehicle_weight_capacity",
                    "vehicle_volume_capacity",
                    "max_orders_per_vehicle",
                ],
            },
            "distance_source": "not_required_for_assignment",
            "path_source": "vehicle_order_assignment_milp",
        }

    def _build_vehicle_assignment(
        self,
        vehicle: AssignmentVehicle,
        orders: Sequence[AssignmentOrder],
    ) -> Dict[str, Any]:
        total_weight = sum(order.weight_tons for order in orders)
        total_volume = sum(order.volume_m3 for order in orders)
        return {
            "vehicle": vehicle.to_dict(),
            "orders": [order.to_dict() for order in orders],
            "order_count": len(orders),
            "total_weight_tons": round(total_weight, 4),
            "total_volume_m3": round(total_volume, 4),
            "weight_utilization": round(total_weight / vehicle.capacity_weight_tons, 4)
            if vehicle.capacity_weight_tons
            else 0.0,
            "volume_utilization": round(total_volume / vehicle.capacity_volume_m3, 4)
            if vehicle.capacity_volume_m3
            else 0.0,
        }

    def _unassigned_payload(
        self,
        order: AssignmentOrder,
        vehicles: Sequence[AssignmentVehicle],
    ) -> Dict[str, Any]:
        fits_any_weight = any(vehicle.capacity_weight_tons >= order.weight_tons for vehicle in vehicles)
        fits_any_volume = any(vehicle.capacity_volume_m3 >= order.volume_m3 for vehicle in vehicles)
        if not fits_any_weight:
            reason = "ORDER_EXCEEDS_ALL_VEHICLE_WEIGHT_CAPACITY"
        elif not fits_any_volume:
            reason = "ORDER_EXCEEDS_ALL_VEHICLE_VOLUME_CAPACITY"
        else:
            reason = "FLEET_CAPACITY_EXHAUSTED"
        return {
            **order.to_dict(),
            "unassigned_reason": reason,
        }

    def _order_from_payload(self, item: Dict[str, Any], idx: int) -> AssignmentOrder:
        weight_tons = self._coerce_float(
            item.get("weight_tons")
            or item.get("weight")
            or (self._coerce_float(item.get("weight_kg"), 0.0) / 1000.0),
            0.0,
        )
        return AssignmentOrder(
            id=item.get("id") or item.get("order_id") or idx,
            order_number=str(item.get("order_number") or item.get("id") or f"order-{idx}"),
            weight_tons=max(0.0, weight_tons),
            volume_m3=max(0.0, self._coerce_float(item.get("volume_m3") or item.get("volume"), 0.0)),
            priority=str(item.get("priority") or "normal"),
            freight=self._coerce_float(item.get("freight"), 0.0),
            data_source=str(item.get("data_source") or "payload"),
        )

    def _vehicle_from_payload(self, item: Dict[str, Any], idx: int) -> AssignmentVehicle:
        capacity_weight = self._coerce_float(
            item.get("capacity_weight_tons")
            or item.get("capacity_weight")
            or item.get("load_capacity")
            or item.get("capacity"),
            0.0,
        )
        return AssignmentVehicle(
            id=item.get("id") or item.get("vehicle_id") or idx,
            plate_number=str(item.get("plate_number") or item.get("plate") or f"vehicle-{idx}"),
            capacity_weight_tons=max(0.0, capacity_weight),
            capacity_volume_m3=max(
                0.0,
                self._coerce_float(
                    item.get("capacity_volume_m3")
                    or item.get("capacity_volume")
                    or item.get("volume_capacity"),
                    capacity_weight * 3.0,
                ),
            ),
            status=str(item.get("status") or "available"),
            data_source=str(item.get("data_source") or "payload"),
        )

    def _order_from_fact(self, fact: ShipmentFact) -> AssignmentOrder:
        return AssignmentOrder(
            id=fact.id,
            order_number=str(fact.external_order_id or fact.external_shipment_id or fact.id),
            weight_tons=max(0.001, self._coerce_float(fact.weight_kg, 1.0) / 1000.0),
            volume_m3=max(0.001, self._coerce_float(fact.volume_m3, 1.0)),
            priority="normal",
            freight=self._coerce_float(fact.freight, 0.0),
            data_source="shipment_fact",
        )

    def _order_from_legacy(self, order: Order) -> AssignmentOrder:
        return AssignmentOrder(
            id=order.id,
            order_number=str(order.order_number or order.id),
            weight_tons=max(0.001, self._coerce_float(order.weight, 1.0)),
            volume_m3=max(0.001, self._coerce_float(order.volume, 1.0)),
            priority=str(order.priority or "normal"),
            freight=self._coerce_float(order.freight, 0.0),
            data_source="orders",
        )

    def _vehicle_from_model(self, vehicle: Vehicle) -> AssignmentVehicle:
        capacity_weight = self._coerce_float(
            vehicle.load_capacity if vehicle.load_capacity is not None else vehicle.capacity,
            0.0,
        )
        return AssignmentVehicle(
            id=vehicle.id,
            plate_number=str(vehicle.plate_number),
            capacity_weight_tons=max(0.0, capacity_weight),
            capacity_volume_m3=max(0.0, self._coerce_float(vehicle.volume_capacity, capacity_weight * 3.0)),
            status=str(vehicle.status or "available"),
            data_source="vehicle_table",
        )

    def _validate_inputs(
        self,
        orders: Sequence[AssignmentOrder],
        vehicles: Sequence[AssignmentVehicle],
    ) -> Optional[str]:
        if not orders:
            return "NO_ASSIGNMENT_ORDERS"
        if not vehicles:
            return "NO_ASSIGNMENT_VEHICLES"
        if all(vehicle.capacity_weight_tons <= 0 for vehicle in vehicles):
            return "NO_POSITIVE_WEIGHT_CAPACITY"
        if all(vehicle.capacity_volume_m3 <= 0 for vehicle in vehicles):
            return "NO_POSITIVE_VOLUME_CAPACITY"
        return None

    def _infer_data_source(
        self,
        orders: Sequence[AssignmentOrder],
        vehicles: Sequence[AssignmentVehicle],
    ) -> str:
        order_sources = sorted({order.data_source for order in orders})
        vehicle_sources = sorted({vehicle.data_source for vehicle in vehicles})
        return "+".join(order_sources + vehicle_sources)

    def _reason_distribution(self, unassigned_orders: Sequence[Dict[str, Any]]) -> Dict[str, int]:
        result: Dict[str, int] = {}
        for order in unassigned_orders:
            reason = str(order.get("unassigned_reason") or "UNKNOWN")
            result[reason] = result.get(reason, 0) + 1
        return result

    def _coerce_float(self, value: Any, default: float = 0.0) -> float:
        try:
            if value is None or value == "":
                return default
            return float(value)
        except (TypeError, ValueError):
            return default


_service: Optional[GurobiAssignmentService] = None


def get_gurobi_assignment_service() -> GurobiAssignmentService:
    global _service
    if _service is None:
        _service = GurobiAssignmentService()
    return _service
