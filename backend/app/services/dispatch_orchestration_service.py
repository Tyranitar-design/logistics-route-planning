"""Unified dispatch orchestration service.

This service bridges legacy orders and layered PostgreSQL shipment facts into a
single dispatchable model. It deliberately keeps hard constraints in Python
heuristics for the first production-safe pass, while exposing solver and
AI-shadow metadata for the later OR/RL stages.
"""

from __future__ import annotations

import json
import math
import time
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple
from uuid import uuid4

from sqlalchemy import func

from app.models import (
    DispatchAssignment,
    DispatchScenario,
    Node,
    Order,
    ShipmentFact,
    Vehicle,
    db,
)
from app.services.precise_distance_provider import get_precise_distance_provider


DISPATCHABLE_ORDER_STATUSES = ("pending", "assigned", "待调度", "待配送", "待分配")
SHIPMENT_FACT_DISPATCHABLE_STATUSES = ("assigned", "pending", "in_transit")
AVAILABLE_VEHICLE_STATUSES = ("available", "idle", "空闲")
DEFAULT_WAVE_LIMIT = 100
PRECISE_DISTANCE_LIMIT = 25
DEFAULT_COST_PER_KM = 5.0
DEFAULT_AVG_SPEED_KMH = 60.0


@dataclass
class DispatchOrder:
    """Normalized dispatch order from either legacy orders or shipment facts."""

    id: Any
    ref: str
    order_number: str
    data_source: str
    customer_name: Optional[str]
    origin_name: Optional[str]
    destination_name: Optional[str]
    origin_address: Optional[str]
    destination_address: Optional[str]
    origin_lng: Optional[float]
    origin_lat: Optional[float]
    destination_lng: Optional[float]
    destination_lat: Optional[float]
    weight_kg: float
    volume_m3: float
    priority: str
    status: str
    freight: float = 0.0
    cargo_type: Optional[str] = None
    exception_reason: Optional[str] = None
    created_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def demand_tons(self) -> float:
        return max(0.001, self.weight_kg / 1000.0)

    @property
    def has_coordinates(self) -> bool:
        return all(
            value is not None
            for value in (
                self.origin_lng,
                self.origin_lat,
                self.destination_lng,
                self.destination_lat,
            )
        )

    def coordinate_pair(self) -> Tuple[Tuple[float, float], Tuple[float, float]]:
        return (
            (float(self.origin_lng), float(self.origin_lat)),
            (float(self.destination_lng), float(self.destination_lat)),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "ref": self.ref,
            "order_number": self.order_number,
            "data_source": self.data_source,
            "customer_name": self.customer_name,
            "origin_name": self.origin_name,
            "destination_name": self.destination_name,
            "origin_address": self.origin_address,
            "destination_address": self.destination_address,
            "origin_lng": self.origin_lng,
            "origin_lat": self.origin_lat,
            "destination_lng": self.destination_lng,
            "destination_lat": self.destination_lat,
            "weight_kg": round(self.weight_kg, 3),
            "weight": round(self.weight_kg / 1000.0, 3),
            "volume_m3": round(self.volume_m3, 3),
            "volume": round(self.volume_m3, 3),
            "priority": self.priority,
            "status": self.status,
            "freight": self.freight,
            "cargo_type": self.cargo_type,
            "exception_reason": self.exception_reason,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            **self.metadata,
        }


@dataclass
class DispatchVehicle:
    """Normalized vehicle capacity view."""

    id: int
    plate_number: str
    vehicle_type: Optional[str]
    capacity_weight_tons: float
    capacity_volume_m3: float
    status: str
    driver_name: Optional[str]
    source: str = "vehicle_table"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "plate_number": self.plate_number,
            "vehicle_type": self.vehicle_type,
            "type": self.vehicle_type,
            "capacity_weight": round(self.capacity_weight_tons, 3),
            "load_capacity": round(self.capacity_weight_tons, 3),
            "capacity_volume": round(self.capacity_volume_m3, 3),
            "volume_capacity": round(self.capacity_volume_m3, 3),
            "status": self.status,
            "driver_name": self.driver_name,
            "source": self.source,
        }


class DispatchOrchestrationService:
    """Application-level dispatch orchestration."""

    def health(self) -> Dict[str, Any]:
        legacy_total = Order.query.count()
        fact_total = ShipmentFact.query.count()
        legacy_dispatchable = Order.query.filter(Order.status.in_(DISPATCHABLE_ORDER_STATUSES)).count()
        fact_dispatchable = ShipmentFact.query.filter(
            ShipmentFact.standard_status.in_(SHIPMENT_FACT_DISPATCHABLE_STATUSES)
        ).count()
        vehicles_total = Vehicle.query.count()
        available_vehicles = self._load_vehicles()

        sample_orders = self._load_orders(limit=200, allow_layered_fallback=True, data_source="auto")
        diagnostics = self._build_diagnostics(sample_orders, available_vehicles)

        data_source = self._infer_order_source(sample_orders)
        if data_source == "none":
            data_source = self._select_data_source(legacy_total, fact_total)
        return {
            "success": True,
            "data_source": data_source,
            "order_sources": {
                "orders": {
                    "total": legacy_total,
                    "dispatchable": legacy_dispatchable,
                },
                "shipment_facts": {
                    "total": fact_total,
                    "dispatchable": fact_dispatchable,
                },
            },
            "vehicle_source": {
                "vehicles_total": vehicles_total,
                "available_vehicles": len(available_vehicles),
                "total_capacity_weight_tons": round(
                    sum(v.capacity_weight_tons for v in available_vehicles), 2
                ),
                "total_capacity_volume_m3": round(
                    sum(v.capacity_volume_m3 for v in available_vehicles), 2
                ),
            },
            "dispatchable_orders": len(sample_orders),
            "diagnostics": diagnostics,
            "provider_status": "ok" if sample_orders and available_vehicles else "degraded",
            "authenticity_level": "B" if data_source == "shipment_fact" else "C",
            "message": self._health_message(data_source, sample_orders, available_vehicles, diagnostics),
        }

    def create_wave(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        limit = self._coerce_limit(payload.get("limit") or payload.get("per_page") or DEFAULT_WAVE_LIMIT)
        orders = self._load_orders(
            order_ids=payload.get("order_ids"),
            limit=limit,
            city=payload.get("city"),
            origin_city=payload.get("origin_city"),
            destination_city=payload.get("destination_city"),
            status=payload.get("status"),
            search=payload.get("search"),
            allow_layered_fallback=True,
            data_source=payload.get("data_source", "auto"),
        )
        vehicles = self._load_vehicles(vehicle_ids=payload.get("vehicle_ids"))
        diagnostics = self._build_diagnostics(orders, vehicles)

        return {
            "success": True,
            "wave": {
                "id": f"wave-{uuid4().hex[:10]}",
                "limit": limit,
                "filters": self._clean_filters(payload),
                "candidate_orders": len(orders),
                "available_vehicles": len(vehicles),
                "total_weight_kg": round(sum(o.weight_kg for o in orders), 2),
                "total_volume_m3": round(sum(o.volume_m3 for o in orders), 2),
                "orders": [o.to_dict() for o in orders[: min(limit, 100)]],
                "vehicles": [v.to_dict() for v in vehicles],
                "diagnostics": diagnostics,
            },
            "data_source": self._infer_order_source(orders),
            "authenticity_level": "B" if self._infer_order_source(orders) == "shipment_fact" else "C",
        }

    def preview(self, payload: Dict[str, Any], user_id: Optional[int] = None, persist: bool = True) -> Dict[str, Any]:
        started = time.perf_counter()
        limit = self._coerce_limit(payload.get("limit") or payload.get("per_page") or DEFAULT_WAVE_LIMIT)
        orders = self._load_orders(
            order_ids=payload.get("order_ids"),
            limit=limit,
            city=payload.get("city"),
            origin_city=payload.get("origin_city"),
            destination_city=payload.get("destination_city"),
            status=payload.get("status"),
            search=payload.get("search"),
            allow_layered_fallback=True,
            data_source=payload.get("data_source", "auto"),
        )
        vehicles = self._load_vehicles(vehicle_ids=payload.get("vehicle_ids"))
        weights = self._normalize_weights(payload.get("weights") or {})
        algorithm = str(payload.get("algorithm") or payload.get("solver") or "auto").lower()
        max_orders_per_vehicle = int(payload.get("max_orders_per_vehicle") or 5)
        use_precise_distance = bool(payload.get("use_precise_distance", True))

        result = self._solve_wave(
            orders=orders,
            vehicles=vehicles,
            weights=weights,
            algorithm=algorithm,
            max_orders_per_vehicle=max_orders_per_vehicle,
            consider_weather=bool(payload.get("consider_weather", True)),
            consider_traffic=bool(payload.get("consider_traffic", True)),
            use_precise_distance=use_precise_distance,
        )
        result["solve_time_ms"] = round((time.perf_counter() - started) * 1000, 2)
        result["wave"] = {
            "filters": self._clean_filters(payload),
            "limit": limit,
            "candidate_orders": len(orders),
            "available_vehicles": len(vehicles),
        }
        self._attach_policy_shadow_contract(result, payload)

        if persist:
            scenario = self._persist_scenario(result, payload, user_id=user_id, status="preview")
            result["scenario_id"] = scenario.id
            result["scenario_code"] = scenario.scenario_code

        return result

    def apply(self, payload: Dict[str, Any], user_id: Optional[int] = None) -> Dict[str, Any]:
        scenario_id = payload.get("scenario_id")
        scenario_code = payload.get("scenario_code")

        scenario = None
        if scenario_id:
            scenario = DispatchScenario.query.get(int(scenario_id))
        elif scenario_code:
            scenario = DispatchScenario.query.filter_by(scenario_code=scenario_code).first()

        if scenario:
            assignments = DispatchAssignment.query.filter_by(scenario_id=scenario.id).all()
            for assignment in assignments:
                assignment.assignment_status = "applied"
            scenario.status = "applied"
            scenario.applied_at = datetime.utcnow()
            scenario.created_by = user_id or scenario.created_by
            db.session.commit()
            return {
                "success": True,
                "message": f"成功应用调度场景 {scenario.scenario_code}",
                "scenario_id": scenario.id,
                "scenario_code": scenario.scenario_code,
                "assignments_updated": len(assignments),
            }

        plans = payload.get("plans") or []
        if not plans:
            return {"success": False, "error": "请提供 scenario_id 或调度计划"}

        synthetic = {
            "plans": plans,
            "unassigned_orders": payload.get("unassigned_orders") or [],
            "summary": payload.get("summary") or {},
            "diagnostics": payload.get("diagnostics") or {},
            "solver": payload.get("solver", "manual_apply"),
            "data_source": payload.get("data_source", "unknown"),
            "distance_source": payload.get("distance_source", "unknown"),
            "provider_status": payload.get("provider_status", "unknown"),
            "authenticity_level": payload.get("authenticity_level", "C"),
            "fallback_reason": payload.get("fallback_reason"),
            "ai_shadow": payload.get("ai_shadow") or {},
        }
        scenario = self._persist_scenario(synthetic, payload, user_id=user_id, status="applied")
        scenario.applied_at = datetime.utcnow()
        for assignment in scenario.assignments:
            assignment.assignment_status = "applied"
        db.session.commit()
        return {
            "success": True,
            "message": f"成功应用 {len(scenario.assignments)} 条调度分配",
            "scenario_id": scenario.id,
            "scenario_code": scenario.scenario_code,
            "assignments_updated": len(scenario.assignments),
        }

    def scenario_detail(self, scenario_id: int) -> Dict[str, Any]:
        scenario = DispatchScenario.query.get(scenario_id)
        if not scenario:
            return {"success": False, "error": "调度场景不存在"}

        assignments = DispatchAssignment.query.filter_by(scenario_id=scenario.id).order_by(
            DispatchAssignment.vehicle_id,
            DispatchAssignment.sequence_index,
        ).all()
        return {
            "success": True,
            "scenario": self._scenario_to_dict(scenario, assignments),
        }

    def list_scenarios(self, limit: int = 20) -> Dict[str, Any]:
        scenarios = DispatchScenario.query.order_by(DispatchScenario.created_at.desc()).limit(limit).all()
        return {
            "success": True,
            "scenarios": [self._scenario_to_dict(s, None) for s in scenarios],
        }

    def compare_solvers(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        base_payload = dict(payload)
        solvers = base_payload.get("solvers") or ["greedy", "balanced", "capacity_first", "ortools", "alns", "genetic"]
        comparisons = []

        for solver in solvers:
            local_payload = dict(base_payload)
            local_payload["algorithm"] = solver
            local_payload["solver"] = solver
            local_payload["use_precise_distance"] = False
            result = self.preview(local_payload, persist=False)
            comparisons.append({
                "solver": solver,
                "available": result.get("solver_status", {}).get("available", True),
                "status": result.get("solver_status", {}).get("status", "ok"),
                "assigned_orders": result.get("summary", {}).get("assigned_orders", 0),
                "unassigned_orders": result.get("summary", {}).get("unassigned_orders", 0),
                "vehicles_used": result.get("summary", {}).get("vehicles_used", 0),
                "total_distance": result.get("summary", {}).get("total_distance", 0),
                "total_cost": result.get("summary", {}).get("total_cost", 0),
                "solve_time_ms": result.get("solve_time_ms", 0),
                "authenticity_level": result.get("authenticity_level"),
            })

        best = None
        viable = [item for item in comparisons if item["assigned_orders"] > 0]
        if viable:
            best = min(viable, key=lambda item: (item["unassigned_orders"], item["total_cost"], item["solve_time_ms"]))

        return {
            "success": True,
            "results": comparisons,
            "best_solver": best["solver"] if best else None,
            "note": "OR-Tools/ALNS use availability metadata in this phase; production assignment remains constraint-safe greedy wave unless the solver is integrated for this data shape.",
        }

    def _attach_policy_shadow_contract(self, result: Dict[str, Any], payload: Dict[str, Any]) -> None:
        policy_mode = self._normalise_policy_mode(payload.get("policy_mode"))
        plans = list(result.get("plans") or [])
        validation = self._validate_dispatch_plan_constraints(plans)
        solver_plan = {
            "solver": result.get("solver"),
            "requested_solver": result.get("requested_solver"),
            "summary": result.get("summary") or {},
            "plan_count": len(plans),
            "assigned_orders": (result.get("summary") or {}).get("assigned_orders", 0),
            "unassigned_orders": (result.get("summary") or {}).get("unassigned_orders", 0),
            "deployable": bool(validation.get("passed")),
            "hard_constraints_owner": "dispatch solver layer",
        }
        rerank = self._build_policy_rerank(plans, policy_mode, validation)

        result["policy_mode"] = policy_mode
        result["solver_plan"] = solver_plan
        result["rl_rerank"] = rerank
        result["constraint_validation"] = validation
        result["deployable"] = bool(validation.get("passed")) and policy_mode == "solver_only"
        result.setdefault("ai_shadow", {})
        result["ai_shadow"].update(
            {
                "policy_mode": policy_mode,
                "deployable": False,
                "hard_constraints_owner": "dispatch solver layer",
                "boundary": "DQN/PPO/Fitted-Q can score or rerank candidates only; solver validation remains mandatory",
            }
        )
        if result.get("summary") is not None:
            result["summary"]["policy_mode"] = policy_mode
            result["summary"]["constraint_validation_passed"] = bool(validation.get("passed"))
            result["summary"]["ai_policy_deployable"] = False

    def _normalise_policy_mode(self, value: Any) -> str:
        text = str(value or "solver_only").strip().lower()
        return text if text in {"solver_only", "shadow_rerank", "dqn_shadow"} else "solver_only"

    def _validate_dispatch_plan_constraints(self, plans: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
        order_refs: List[str] = []
        violations: List[Dict[str, Any]] = []
        for plan in plans:
            vehicle = plan.get("vehicle_info") or {}
            capacity_weight_kg = float(vehicle.get("capacity_weight", 0) or vehicle.get("load_capacity", 0) or 0) * 1000.0
            capacity_volume = float(vehicle.get("capacity_volume", 0) or vehicle.get("volume_capacity", 0) or 0)
            total_weight = sum(float(order.get("weight_kg", 0) or 0) for order in plan.get("orders") or [])
            total_volume = sum(float(order.get("volume_m3", 0) or order.get("volume", 0) or 0) for order in plan.get("orders") or [])
            if capacity_weight_kg > 0 and total_weight > capacity_weight_kg + 1e-6:
                violations.append({
                    "type": "capacity_weight_exceeded",
                    "vehicle_id": plan.get("vehicle_id"),
                    "total_weight_kg": round(total_weight, 3),
                    "capacity_weight_kg": round(capacity_weight_kg, 3),
                })
            if capacity_volume > 0 and total_volume > capacity_volume + 1e-6:
                violations.append({
                    "type": "capacity_volume_exceeded",
                    "vehicle_id": plan.get("vehicle_id"),
                    "total_volume_m3": round(total_volume, 3),
                    "capacity_volume_m3": round(capacity_volume, 3),
                })
            for order in plan.get("orders") or []:
                order_refs.append(str(order.get("ref") or order.get("id") or order.get("order_number")))

        duplicates = sorted([ref for ref, count in Counter(order_refs).items() if count > 1])
        for ref in duplicates:
            violations.append({"type": "duplicate_order_assignment", "order_ref": ref})

        return {
            "passed": not violations,
            "hard_constraints": [
                "order_unique_assignment",
                "vehicle_weight_capacity",
                "vehicle_volume_capacity",
            ],
            "assigned_order_count": len(order_refs),
            "duplicate_order_refs": duplicates,
            "violation_count": len(violations),
            "violations": violations,
            "validator_version": "dispatch_constraint_validation_v1",
        }

    def _build_policy_rerank(
        self,
        plans: Sequence[Dict[str, Any]],
        policy_mode: str,
        validation: Dict[str, Any],
    ) -> Dict[str, Any]:
        candidates = []
        for index, plan in enumerate(plans):
            load = float(plan.get("load_utilization") or 0.0)
            volume = float(plan.get("volume_utilization") or 0.0)
            cost = float(plan.get("total_cost") or 0.0)
            duration = float(plan.get("total_duration") or 0.0)
            if policy_mode == "dqn_shadow":
                policy_score = load * 45.0 + volume * 20.0 - cost * 0.01 - duration * 0.02
                policy_id = "dqn_shadow_q_score_v0"
            elif policy_mode == "shadow_rerank":
                policy_score = load * 35.0 + volume * 25.0 + float(plan.get("score") or 0.0) * 0.4
                policy_id = "balanced_shadow_rerank_v1"
            else:
                policy_score = float(plan.get("score") or 0.0)
                policy_id = "solver_order"
            candidates.append({
                "rank": index + 1,
                "vehicle_id": plan.get("vehicle_id"),
                "order_count": len(plan.get("orders") or []),
                "solver_score": plan.get("score"),
                "policy_score": round(policy_score, 4),
                "policy_id": policy_id,
                "load_utilization": plan.get("load_utilization"),
                "volume_utilization": plan.get("volume_utilization"),
            })

        reranked = sorted(candidates, key=lambda item: item["policy_score"], reverse=True)
        for index, item in enumerate(reranked, start=1):
            item["shadow_rank"] = index
        return {
            "success": True,
            "mode": policy_mode,
            "provider_status": "ok" if validation.get("passed") else "degraded",
            "deployable": False,
            "policy_family": "solver_only" if policy_mode == "solver_only" else "dispatch_rl_shadow_rerank",
            "candidate_count": len(candidates),
            "candidates": reranked,
            "recommendations": [
                "AI shadow rerank is advisory only; apply must keep solver-backed constraints.",
            ] if policy_mode != "solver_only" else [
                "当前为 solver_only，AI shadow 仅展示边界信息。",
            ],
            "truth_contract": {
                "mutation": "none",
                "deployable": False,
                "hard_constraints_owner": "dispatch solver layer",
            },
        }

    def _solve_wave(
        self,
        orders: List[DispatchOrder],
        vehicles: List[DispatchVehicle],
        weights: Dict[str, float],
        algorithm: str,
        max_orders_per_vehicle: int,
        consider_weather: bool,
        consider_traffic: bool,
        use_precise_distance: bool,
    ) -> Dict[str, Any]:
        diagnostics = self._build_diagnostics(orders, vehicles)
        if not orders:
            return self._empty_result("没有待调度订单", diagnostics, orders, vehicles, algorithm)
        if not vehicles:
            return self._empty_result("没有可用车辆", diagnostics, orders, vehicles, algorithm, success=False)

        distance_lookup, distance_meta = self._build_order_distance_lookup(orders, use_precise_distance)
        solver_status = self._solver_status(algorithm)
        effective_algorithm = algorithm if solver_status["available"] else "balanced"
        if effective_algorithm in ("auto", "ortools", "alns", "genetic"):
            effective_algorithm = "balanced"

        sorted_orders = self._rank_orders(orders, weights, effective_algorithm)
        vehicle_states = {
            vehicle.id: {
                "vehicle": vehicle,
                "orders": [],
                "total_weight_kg": 0.0,
                "total_volume_m3": 0.0,
                "total_distance": 0.0,
                "total_duration": 0.0,
                "total_cost": 0.0,
                "route_sequence": [],
                "route_legs": [],
            }
            for vehicle in vehicles
        }
        unassigned = []

        for order in sorted_orders:
            candidates = []
            distance_info = distance_lookup.get(order.ref) or self._estimate_order_distance(order)
            for vehicle in vehicles:
                state = vehicle_states[vehicle.id]
                capacity_ok = (
                    state["total_weight_kg"] + order.weight_kg <= vehicle.capacity_weight_tons * 1000.0
                    and state["total_volume_m3"] + order.volume_m3 <= vehicle.capacity_volume_m3
                )
                order_count_ok = len(state["orders"]) < max_orders_per_vehicle
                if not capacity_ok or not order_count_ok:
                    continue
                load_after = (state["total_weight_kg"] + order.weight_kg) / max(vehicle.capacity_weight_tons * 1000.0, 1.0)
                score = (
                    weights["cost"] * distance_info["cost"]
                    + weights["time"] * distance_info["duration_min"]
                    - weights["satisfaction"] * load_after * 100.0
                )
                if effective_algorithm == "capacity_first":
                    score -= load_after * 80.0
                elif effective_algorithm == "greedy":
                    score = distance_info["distance_km"]
                candidates.append((score, vehicle, distance_info))

            if not candidates:
                unassigned.append(self._unassigned_order(order, vehicles, max_orders_per_vehicle))
                continue

            _, selected_vehicle, distance_info = min(candidates, key=lambda item: item[0])
            state = vehicle_states[selected_vehicle.id]
            state["orders"].append(order)
            state["total_weight_kg"] += order.weight_kg
            state["total_volume_m3"] += order.volume_m3
            state["total_distance"] += distance_info["distance_km"]
            state["total_duration"] += distance_info["duration_min"]
            state["total_cost"] += distance_info["cost"]
            state["route_legs"].append(
                self._dispatch_route_leg(
                    order,
                    distance_info,
                    distance_meta,
                    sequence=len(state["route_legs"]),
                )
            )
            state["route_sequence"].extend([
                {
                    "type": "pickup",
                    "order_ref": order.ref,
                    "order_number": order.order_number,
                    "name": order.origin_name,
                    "address": order.origin_address,
                    "lng": order.origin_lng,
                    "lat": order.origin_lat,
                },
                {
                    "type": "delivery",
                    "order_ref": order.ref,
                    "order_number": order.order_number,
                    "name": order.destination_name,
                    "address": order.destination_address,
                    "lng": order.destination_lng,
                    "lat": order.destination_lat,
                },
            ])

        plans = []
        for state in vehicle_states.values():
            if not state["orders"]:
                continue
            vehicle = state["vehicle"]
            load_utilization = state["total_weight_kg"] / max(vehicle.capacity_weight_tons * 1000.0, 1.0)
            volume_utilization = state["total_volume_m3"] / max(vehicle.capacity_volume_m3, 1.0)
            route_truth = self._plan_route_truth(
                state["route_legs"],
                data_source=self._infer_order_source(state["orders"]),
            )
            plans.append({
                "vehicle_id": vehicle.id,
                "vehicle_info": vehicle.to_dict(),
                "orders": [order.to_dict() for order in state["orders"]],
                "route_sequence": state["route_sequence"],
                "route_legs": state["route_legs"],
                "route_truth": route_truth,
                "total_distance": round(state["total_distance"], 2),
                "total_duration": round(state["total_duration"], 2),
                "total_cost": round(state["total_cost"], 2),
                "fuel_cost": round(state["total_cost"] * 0.62, 2),
                "toll_cost": round(state["total_cost"] * 0.38, 2),
                "weather_impact": self._weather_impact_stub(consider_weather),
                "traffic_impact": self._traffic_impact_stub(consider_traffic),
                "score": round(max(1.0, 100.0 - state["total_cost"] / 100.0), 2),
                "cost_score": round(max(0.0, 100.0 - state["total_cost"] / 100.0), 2),
                "time_score": round(max(0.0, 100.0 - state["total_duration"] / 30.0), 2),
                "satisfaction_score": round(min(100.0, 70.0 + load_utilization * 30.0), 2),
                "load_utilization": round(load_utilization, 3),
                "volume_utilization": round(volume_utilization, 3),
                "suggestions": self._plan_suggestions(load_utilization, volume_utilization),
            })

        data_source = self._infer_order_source(orders)
        path_source = "dispatch_assignment_sequence"
        summary = self._summary(plans, unassigned, orders, vehicles)
        summary.update({
            "data_source": data_source,
            "distance_source": distance_meta["distance_source"],
            "path_source": path_source,
            "provider_status": distance_meta.get("provider_status", "ok"),
            "fallback_reason": distance_meta.get("fallback_reason"),
        })
        summary["route_truth"] = self._dispatch_route_truth(plans)
        ai_shadow = self._ai_shadow_summary(orders, plans, unassigned)
        authenticity_level = self._authenticity_level(data_source, distance_meta)
        summary["authenticity_level"] = authenticity_level
        return {
            "success": True,
            "plans": plans,
            "unassigned_orders": unassigned,
            "summary": summary,
            "diagnostics": diagnostics,
            "solver": effective_algorithm,
            "requested_solver": algorithm,
            "solver_status": solver_status,
            "algorithm": effective_algorithm,
            "data_source": data_source,
            "distance_source": distance_meta["distance_source"],
            "path_source": path_source,
            "distance_precision": distance_meta.get("precision", {}),
            "source_summary": distance_meta.get("source_summary", {}),
            "provider_status": distance_meta.get("provider_status", "ok"),
            "route_truth": summary["route_truth"],
            "authenticity_level": authenticity_level,
            "fallback_reason": distance_meta.get("fallback_reason"),
            "legacy_truth_contract": self._legacy_truth_contract(data_source, distance_meta),
            "ai_shadow": ai_shadow,
            "generations": 0,
            "convergence_score": summary.get("optimization_score", 0),
        }

    def _load_orders(
        self,
        order_ids: Optional[Sequence[Any]] = None,
        limit: int = DEFAULT_WAVE_LIMIT,
        city: Optional[str] = None,
        origin_city: Optional[str] = None,
        destination_city: Optional[str] = None,
        status: Optional[str] = None,
        search: Optional[str] = None,
        allow_layered_fallback: bool = True,
        data_source: str = "auto",
    ) -> List[DispatchOrder]:
        data_source = str(data_source or "auto").lower()
        if data_source in {"shipment_facts", "fact", "facts"}:
            data_source = "shipment_fact"
        if data_source not in {"auto", "shipment_fact", "orders"}:
            data_source = "auto"

        if data_source in {"auto", "shipment_fact"}:
            facts = self._query_shipment_facts(
                order_ids=order_ids,
                limit=limit,
                city=city,
                origin_city=origin_city,
                destination_city=destination_city,
                status=status,
                search=search,
            )
            if facts or data_source == "shipment_fact":
                return [self._from_shipment_fact(fact) for fact in facts]
            if not allow_layered_fallback:
                return []

        legacy_orders = self._query_legacy_orders(
            order_ids=order_ids,
            limit=limit,
            status=status,
            search=search,
        )
        if legacy_orders or data_source == "orders" or not allow_layered_fallback:
            return [self._from_order(order) for order in legacy_orders]

        facts = self._query_shipment_facts(
            order_ids=order_ids,
            limit=limit,
            city=city,
            origin_city=origin_city,
            destination_city=destination_city,
            status=status,
            search=search,
        )
        return [self._from_shipment_fact(fact) for fact in facts]

    def _query_legacy_orders(
        self,
        order_ids: Optional[Sequence[Any]],
        limit: int,
        status: Optional[str],
        search: Optional[str],
    ) -> List[Order]:
        legacy_query = Order.query
        if status:
            legacy_query = legacy_query.filter(Order.status == status)
        else:
            legacy_query = legacy_query.filter(Order.status.in_(DISPATCHABLE_ORDER_STATUSES))
        if order_ids:
            legacy_ids = [int(x) for x in order_ids if str(x).isdigit()]
            if legacy_ids:
                legacy_query = legacy_query.filter(Order.id.in_(legacy_ids))
        if search:
            pattern = f"%{search}%"
            legacy_query = legacy_query.filter(
                (Order.order_number.ilike(pattern)) |
                (Order.customer_name.ilike(pattern))
            )
        return legacy_query.order_by(Order.created_at.desc()).limit(limit).all()

    def _query_shipment_facts(
        self,
        order_ids: Optional[Sequence[Any]],
        limit: int,
        city: Optional[str],
        origin_city: Optional[str],
        destination_city: Optional[str],
        status: Optional[str],
        search: Optional[str],
    ) -> List[ShipmentFact]:
        fact_query = ShipmentFact.query
        if status:
            mapped_status = "assigned" if status == "pending" else status
            fact_query = fact_query.filter(ShipmentFact.standard_status == mapped_status)
        else:
            fact_query = fact_query.filter(ShipmentFact.standard_status.in_(SHIPMENT_FACT_DISPATCHABLE_STATUSES))
        if order_ids:
            fact_ids = [int(x) for x in order_ids if str(x).isdigit()]
            if fact_ids:
                fact_query = fact_query.filter(ShipmentFact.id.in_(fact_ids))
        if city:
            fact_query = fact_query.filter(
                (ShipmentFact.origin_city_std == city) |
                (ShipmentFact.destination_city_std == city)
            )
        if origin_city:
            fact_query = fact_query.filter(ShipmentFact.origin_city_std == origin_city)
        if destination_city:
            fact_query = fact_query.filter(ShipmentFact.destination_city_std == destination_city)
        if search:
            pattern = f"%{search}%"
            fact_query = fact_query.filter(
                (ShipmentFact.external_order_id.ilike(pattern)) |
                (ShipmentFact.external_shipment_id.ilike(pattern)) |
                (ShipmentFact.customer_name_masked.ilike(pattern))
            )

        facts = (
            fact_query.order_by(ShipmentFact.shipped_at.desc().nullslast(), ShipmentFact.created_at.desc())
            .limit(limit)
            .all()
        )
        return facts

    def _load_vehicles(self, vehicle_ids: Optional[Sequence[Any]] = None) -> List[DispatchVehicle]:
        query = Vehicle.query.filter(Vehicle.status.in_(AVAILABLE_VEHICLE_STATUSES))
        if vehicle_ids:
            ids = [int(x) for x in vehicle_ids if str(x).isdigit()]
            if ids:
                query = query.filter(Vehicle.id.in_(ids))
        vehicles = query.order_by(Vehicle.created_at.desc()).all()
        return [self._from_vehicle(vehicle) for vehicle in vehicles]

    def _from_order(self, order: Order) -> DispatchOrder:
        pickup = order.pickup_node
        delivery = order.delivery_node
        origin_lng = order.origin_lng or order.start_lng or (pickup.longitude if pickup else None)
        origin_lat = order.origin_lat or order.start_lat or (pickup.latitude if pickup else None)
        dest_lng = order.destination_lng or order.delivery_lng or (delivery.longitude if delivery else None)
        dest_lat = order.destination_lat or order.delivery_lat or (delivery.latitude if delivery else None)
        return DispatchOrder(
            id=order.id,
            ref=f"order:{order.id}",
            order_number=order.order_number,
            data_source="orders",
            customer_name=order.customer_name,
            origin_name=order.origin_name or (pickup.name if pickup else None),
            destination_name=order.destination_name or (delivery.name if delivery else None),
            origin_address=order.origin_address or (pickup.address if pickup else None),
            destination_address=order.destination_address or (delivery.address if delivery else None),
            origin_lng=origin_lng,
            origin_lat=origin_lat,
            destination_lng=dest_lng,
            destination_lat=dest_lat,
            weight_kg=self._normalize_weight_kg(order.weight),
            volume_m3=float(order.volume or 0.0),
            priority=order.priority or "normal",
            status=order.status or "pending",
            freight=float(order.freight or order.estimated_cost or 0.0),
            cargo_type=order.cargo_type,
            exception_reason=order.exceptions or order.notes,
            created_at=order.created_at,
            metadata={"legacy_order_id": order.id},
        )

    def _from_shipment_fact(self, fact: ShipmentFact) -> DispatchOrder:
        order_number = fact.external_order_id or fact.external_shipment_id or f"SHIP-{fact.id}"
        return DispatchOrder(
            id=fact.id,
            ref=f"shipment_fact:{fact.id}",
            order_number=order_number,
            data_source="shipment_fact",
            customer_name=fact.customer_name_masked,
            origin_name=fact.origin_city_std or fact.origin_city_raw,
            destination_name=fact.destination_city_std or fact.destination_city_raw,
            origin_address=fact.origin_city_raw,
            destination_address=fact.destination_city_raw,
            origin_lng=fact.origin_lng,
            origin_lat=fact.origin_lat,
            destination_lng=fact.destination_lng,
            destination_lat=fact.destination_lat,
            weight_kg=float(fact.weight_kg or 0.0),
            volume_m3=float(fact.volume_m3 or 0.0),
            priority="normal",
            status=fact.standard_status or "assigned",
            freight=float(fact.freight or 0.0),
            cargo_type=fact.cargo_type,
            exception_reason=fact.exception_reason,
            created_at=fact.shipped_at or fact.created_at,
            metadata={
                "external_shipment_id": fact.external_shipment_id,
                "external_order_id": fact.external_order_id,
                "geo_status": fact.geo_status,
                "transport_mode": fact.transport_mode,
                "logistics_company": fact.logistics_company,
            },
        )

    def _from_vehicle(self, vehicle: Vehicle) -> DispatchVehicle:
        capacity_weight = (
            getattr(vehicle, "capacity_weight", None)
            or getattr(vehicle, "load_capacity", None)
            or getattr(vehicle, "capacity", None)
            or 0.0
        )
        capacity_volume = (
            getattr(vehicle, "capacity_volume", None)
            or getattr(vehicle, "volume_capacity", None)
            or max(float(capacity_weight or 0.0) * 3.0, 1.0)
        )
        return DispatchVehicle(
            id=vehicle.id,
            plate_number=vehicle.plate_number,
            vehicle_type=vehicle.vehicle_type,
            capacity_weight_tons=max(float(capacity_weight or 0.0), 0.1),
            capacity_volume_m3=max(float(capacity_volume or 0.0), 0.1),
            status=vehicle.status or "available",
            driver_name=vehicle.driver_name,
        )

    def _build_order_distance_lookup(
        self,
        orders: List[DispatchOrder],
        use_precise_distance: bool,
    ) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, Any]]:
        lookup = {}
        valid_orders = [order for order in orders if order.has_coordinates]
        use_provider = use_precise_distance and 0 < len(valid_orders) <= PRECISE_DISTANCE_LIMIT

        if use_provider:
            try:
                cache = get_precise_distance_provider().distance_cache
            except Exception:
                cache = None
            if cache is not None:
                # 逐对查询：只算每个 order 的 origin→destination（n 对），
                # 避免构建 n×n 全矩阵（原 40 点→1600 对，现仅 20 对），
                # 大幅降低高德调用次数与 QPS 压力，杜绝跨 order 废对触发的逐对兜底。
                source_counter: Counter = Counter()
                exact_count = 0
                approx_count = 0
                for order in valid_orders:
                    origin, destination = order.coordinate_pair()
                    result = cache.get_distance(origin, destination, strategy=0, use_amap=True)
                    distance = round(float(result.get("distance_km", 0.0) or 0.0), 2)
                    duration = round(float(result.get("duration_minutes", 0.0) or 0.0), 2)
                    raw_source = result.get("source", "unknown")
                    is_exact = bool(result.get("is_exact", False))
                    # 规范化 source：get_distance 返回 'cache'，需用 is_exact 区分精确/近似
                    if raw_source == "cache":
                        norm_source = "cache_exact" if is_exact else "cache_approx"
                    elif raw_source in ("amap", "amap_route"):
                        norm_source = "amap_route"
                    else:
                        norm_source = raw_source
                    provider_status = self._leg_provider_status(norm_source)
                    lookup[order.ref] = {
                        "distance_km": distance,
                        "duration_min": duration,
                        "cost": round(max(distance * DEFAULT_COST_PER_KM, order.freight or 0.0), 2),
                        "source": result.get("source"),
                        "distance_source": norm_source,
                        "provider_status": provider_status,
                        "fallback_reason": None if provider_status == "ok" else f"{norm_source}_distance_estimate",
                    }
                    source_counter[norm_source] += 1
                    if is_exact:
                        exact_count += 1
                    else:
                        approx_count += 1
                metadata = self._metadata_from_paired_sources(
                    source_counter, exact_count, approx_count, len(valid_orders)
                )
                return lookup, metadata
            fallback_reason = "distance_cache_unavailable"
        else:
            fallback_reason = (
                "wave_too_large_for_live_distance_provider"
                if use_precise_distance and len(valid_orders) > PRECISE_DISTANCE_LIMIT
                else "precise_distance_disabled_or_missing_coordinates"
            )

        for order in orders:
            lookup[order.ref] = self._estimate_order_distance(order)
        missing_coords = len([o for o in orders if not o.has_coordinates])
        return lookup, {
            "distance_source": "haversine_corrected",
            "provider_status": "degraded",
            "fallback_reason": fallback_reason,
            "precision": {
                "exact_count": 0,
                "approx_count": max(0, len(orders) - missing_coords),
                "missing_coordinate_orders": missing_coords,
            },
            "source_summary": {"haversine_corrected": max(0, len(orders) - missing_coords)},
        }

    @staticmethod
    def _metadata_from_paired_sources(
        source_counter: Counter, exact_count: int, approx_count: int, total: int
    ) -> Dict[str, Any]:
        """逐对距离查询的 metadata 构造（与 _distance_metadata_from_matrix 输出格式一致）。"""
        sources = {k: v for k, v in source_counter.items() if v}
        if "amap" in sources or "amap_route" in sources:
            distance_source = "amap_route"
        elif sources.get("cache_exact"):
            distance_source = "distance_cache_exact"
        elif sources.get("cache_approx"):
            distance_source = "distance_cache_approx"
        else:
            distance_source = "haversine_corrected"

        if distance_source == "haversine_corrected":
            provider_status = "degraded"
        elif approx_count == 0 and exact_count > 0:
            provider_status = "ok"
        else:
            provider_status = "partial"

        return {
            "distance_source": distance_source,
            "provider_status": provider_status,
            "fallback_reason": None,
            "precision": {
                "exact_count": exact_count,
                "approx_count": approx_count,
                "fallback_count": 0,
            },
            "source_summary": dict(source_counter),
        }

    def _estimate_order_distance(self, order: DispatchOrder) -> Dict[str, Any]:
        if not order.has_coordinates:
            distance = 100.0
            source = "missing_coordinates_default"
            provider_status = "degraded"
            fallback_reason = "order_missing_coordinates"
        else:
            origin, destination = order.coordinate_pair()
            distance = self._haversine_km(origin, destination) * 1.3
            source = "haversine_corrected"
            provider_status = "degraded"
            fallback_reason = "precise_distance_disabled_or_provider_unavailable"
        duration = distance / DEFAULT_AVG_SPEED_KMH * 60.0
        return {
            "distance_km": round(distance, 2),
            "duration_min": round(duration, 2),
            "cost": round(max(distance * DEFAULT_COST_PER_KM, order.freight or 0.0), 2),
            "source": source,
            "distance_source": source,
            "provider_status": provider_status,
            "fallback_reason": fallback_reason,
        }

    def _build_diagnostics(self, orders: List[DispatchOrder], vehicles: List[DispatchVehicle]) -> Dict[str, Any]:
        reason_counts = Counter()
        missing_coordinates = [order for order in orders if not order.has_coordinates]
        zero_weight = [order for order in orders if order.weight_kg <= 0]
        total_weight = sum(order.weight_kg for order in orders)
        total_volume = sum(order.volume_m3 for order in orders)
        total_capacity_kg = sum(vehicle.capacity_weight_tons * 1000.0 for vehicle in vehicles)
        total_capacity_volume = sum(vehicle.capacity_volume_m3 for vehicle in vehicles)

        if not orders:
            reason_counts["no_dispatchable_orders"] += 1
        if not vehicles:
            reason_counts["no_available_vehicles"] += 1
        if missing_coordinates:
            reason_counts["missing_coordinates"] = len(missing_coordinates)
        if zero_weight:
            reason_counts["zero_or_missing_weight"] = len(zero_weight)
        if orders and vehicles and total_weight > total_capacity_kg:
            reason_counts["capacity_shortage_weight"] = 1
        if orders and vehicles and total_volume > total_capacity_volume:
            reason_counts["capacity_shortage_volume"] = 1

        return {
            "order_count": len(orders),
            "vehicle_count": len(vehicles),
            "missing_coordinate_orders": len(missing_coordinates),
            "zero_weight_orders": len(zero_weight),
            "total_weight_kg": round(total_weight, 2),
            "total_volume_m3": round(total_volume, 2),
            "total_capacity_weight_kg": round(total_capacity_kg, 2),
            "total_capacity_volume_m3": round(total_capacity_volume, 2),
            "capacity_gap_weight_kg": round(max(0.0, total_weight - total_capacity_kg), 2),
            "capacity_gap_volume_m3": round(max(0.0, total_volume - total_capacity_volume), 2),
            "reason_counts": dict(reason_counts),
            "recommendations": self._diagnostic_recommendations(reason_counts),
        }

    def _persist_scenario(
        self,
        result: Dict[str, Any],
        payload: Dict[str, Any],
        user_id: Optional[int],
        status: str,
    ) -> DispatchScenario:
        scenario = DispatchScenario(
            scenario_code=f"DS-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{uuid4().hex[:6]}",
            name=payload.get("name") or "智能调度场景",
            status=status,
            solver=result.get("solver"),
            data_source=result.get("data_source"),
            distance_source=result.get("distance_source"),
            provider_status=result.get("provider_status"),
            authenticity_level=result.get("authenticity_level"),
            fallback_reason=result.get("fallback_reason"),
            wave_filters_json=self._json_dumps(result.get("wave", {}).get("filters") or {}),
            summary_json=self._json_dumps(result.get("summary") or {}),
            diagnostics_json=self._json_dumps(result.get("diagnostics") or {}),
            ai_shadow_json=self._json_dumps(result.get("ai_shadow") or {}),
            created_by=user_id,
            applied_at=datetime.utcnow() if status == "applied" else None,
        )
        db.session.add(scenario)
        db.session.flush()

        for plan in result.get("plans") or []:
            for idx, order in enumerate(plan.get("orders") or []):
                assignment = DispatchAssignment(
                    scenario_id=scenario.id,
                    vehicle_id=plan.get("vehicle_id"),
                    vehicle_plate=(plan.get("vehicle_info") or {}).get("plate_number"),
                    order_source=order.get("data_source") or result.get("data_source") or "unknown",
                    order_ref=order.get("ref") or str(order.get("id")),
                    order_number=order.get("order_number"),
                    sequence_index=idx,
                    assignment_status=status,
                    weight_kg=order.get("weight_kg"),
                    volume_m3=order.get("volume_m3"),
                    distance_km=plan.get("total_distance"),
                    duration_min=plan.get("total_duration"),
                    cost=plan.get("total_cost"),
                    route_json=self._json_dumps(plan.get("route_sequence") or []),
                    diagnostics_json=self._json_dumps({
                        "load_utilization": plan.get("load_utilization"),
                        "volume_utilization": plan.get("volume_utilization"),
                        "route_truth": plan.get("route_truth"),
                    }),
                )
                db.session.add(assignment)
        db.session.commit()
        return scenario

    def _scenario_to_dict(
        self,
        scenario: DispatchScenario,
        assignments: Optional[List[DispatchAssignment]],
    ) -> Dict[str, Any]:
        data = {
            "id": scenario.id,
            "scenario_code": scenario.scenario_code,
            "name": scenario.name,
            "status": scenario.status,
            "solver": scenario.solver,
            "data_source": scenario.data_source,
            "distance_source": scenario.distance_source,
            "provider_status": scenario.provider_status,
            "authenticity_level": scenario.authenticity_level,
            "fallback_reason": scenario.fallback_reason,
            "wave_filters": self._json_loads(scenario.wave_filters_json, {}),
            "summary": self._json_loads(scenario.summary_json, {}),
            "diagnostics": self._json_loads(scenario.diagnostics_json, {}),
            "ai_shadow": self._json_loads(scenario.ai_shadow_json, {}),
            "created_at": scenario.created_at.isoformat() if scenario.created_at else None,
            "applied_at": scenario.applied_at.isoformat() if scenario.applied_at else None,
        }
        if assignments is not None:
            data["assignments"] = [
                {
                    "id": item.id,
                    "vehicle_id": item.vehicle_id,
                    "vehicle_plate": item.vehicle_plate,
                    "order_source": item.order_source,
                    "order_ref": item.order_ref,
                    "order_number": item.order_number,
                    "sequence_index": item.sequence_index,
                    "assignment_status": item.assignment_status,
                    "weight_kg": item.weight_kg,
                    "volume_m3": item.volume_m3,
                    "distance_km": item.distance_km,
                    "duration_min": item.duration_min,
                    "cost": item.cost,
                    "route": self._json_loads(item.route_json, []),
                    "diagnostics": self._json_loads(item.diagnostics_json, {}),
                }
                for item in assignments
            ]
        return data

    def _summary(
        self,
        plans: List[Dict[str, Any]],
        unassigned: List[Dict[str, Any]],
        orders: List[DispatchOrder],
        vehicles: List[DispatchVehicle],
    ) -> Dict[str, Any]:
        assigned = sum(len(plan.get("orders") or []) for plan in plans)
        total_distance = sum(float(plan.get("total_distance") or 0.0) for plan in plans)
        total_duration = sum(float(plan.get("total_duration") or 0.0) for plan in plans)
        total_cost = sum(float(plan.get("total_cost") or 0.0) for plan in plans)
        load_values = [float(plan.get("load_utilization") or 0.0) for plan in plans]
        return {
            "total_orders": len(orders),
            "assigned_orders": assigned,
            "unassigned_orders": len(unassigned),
            "vehicles_used": len(plans),
            "available_vehicles": len(vehicles),
            "total_distance": round(total_distance, 2),
            "total_duration": round(total_duration, 2),
            "total_cost": round(total_cost, 2),
            "avg_cost_per_order": round(total_cost / assigned, 2) if assigned else 0,
            "average_load_utilization": round(sum(load_values) / len(load_values), 3) if load_values else 0,
            "optimization_score": round(max(0.0, 100.0 - len(unassigned) * 5.0 - total_cost / 5000.0), 2),
            "total_orders_assigned": assigned,
            "total_orders_unassigned": len(unassigned),
            "total_vehicles_used": len(plans),
            "total_distance_km": round(total_distance, 2),
            "total_duration_min": round(total_duration, 2),
            "average_cost_per_order": round(total_cost / assigned, 2) if assigned else 0,
        }

    def _empty_result(
        self,
        message: str,
        diagnostics: Dict[str, Any],
        orders: List[DispatchOrder],
        vehicles: List[DispatchVehicle],
        algorithm: str,
        success: bool = True,
    ) -> Dict[str, Any]:
        return {
            "success": success,
            "plans": [],
            "unassigned_orders": [],
            "summary": {
                "message": message,
                "total_orders": len(orders),
                "assigned_orders": 0,
                "unassigned_orders": 0,
                "vehicles_used": 0,
                "total_orders_assigned": 0,
                "total_orders_unassigned": 0,
                "total_vehicles_used": 0,
                "total_distance_km": 0,
                "total_cost": 0,
                "average_cost_per_order": 0,
            },
            "diagnostics": diagnostics,
            "solver": algorithm,
            "solver_status": self._solver_status(algorithm),
            "data_source": self._infer_order_source(orders),
            "distance_source": "not_applicable",
            "provider_status": "degraded",
            "authenticity_level": "C",
            "fallback_reason": message,
            "ai_shadow": {"mode": "shadow", "enabled": False, "reason": message},
            "path_source": "not_applicable",
            "legacy_truth_contract": {},
        }

    @staticmethod
    def _normalize_weight_kg(weight: Optional[float]) -> float:
        value = float(weight or 0.0)
        if 0 < value <= 80:
            return value * 1000.0
        return value

    @staticmethod
    def _haversine_km(origin: Tuple[float, float], destination: Tuple[float, float]) -> float:
        lng1, lat1 = origin
        lng2, lat2 = destination
        radius = 6371.0
        dlat = math.radians(lat2 - lat1)
        dlng = math.radians(lng2 - lng1)
        a = (
            math.sin(dlat / 2) ** 2
            + math.cos(math.radians(lat1))
            * math.cos(math.radians(lat2))
            * math.sin(dlng / 2) ** 2
        )
        return radius * 2 * math.asin(math.sqrt(a))

    @staticmethod
    def _json_dumps(value: Any) -> str:
        return json.dumps(value, ensure_ascii=False, default=str)

    @staticmethod
    def _json_loads(value: Optional[str], default: Any) -> Any:
        if not value:
            return default
        try:
            return json.loads(value)
        except Exception:
            return default

    @staticmethod
    def _distance_metadata_from_matrix(matrix: Any) -> Dict[str, Any]:
        source_summary = dict(getattr(matrix, "source_summary", {}) or {})
        precision = dict(getattr(matrix, "precision", {}) or {})
        metadata = dict(getattr(matrix, "metadata", {}) or {})

        non_diagonal_sources = {
            source: count
            for source, count in source_summary.items()
            if source != "diagonal" and count
        }
        if any(source in non_diagonal_sources for source in ("amap_route", "amap")):
            distance_source = "amap_route"
        elif non_diagonal_sources.get("cache_exact"):
            distance_source = "distance_cache_exact"
        elif non_diagonal_sources.get("cache_approx"):
            distance_source = "distance_cache_approx"
        elif non_diagonal_sources and set(non_diagonal_sources) == {"haversine_corrected"}:
            distance_source = "haversine_corrected"
        elif non_diagonal_sources:
            distance_source = "mixed_distance_provider"
        else:
            distance_source = "precise_distance_provider"

        fallback_reason = (
            metadata.get("fallback_reason")
            or metadata.get("distance_matrix_fallback_reason")
        )
        exact_count = int(precision.get("exact_count") or 0)
        approx_count = int(precision.get("approx_count") or 0)
        fallback_count = int(precision.get("fallback_count") or 0)

        provider_status = metadata.get("provider_status")
        if not provider_status:
            if distance_source == "haversine_corrected" or (exact_count == 0 and approx_count > 0):
                provider_status = "degraded"
            elif fallback_count > 0 or distance_source in {"mixed_distance_provider", "distance_cache_approx"}:
                provider_status = "partial"
            else:
                provider_status = "ok"

        return {
            "distance_source": distance_source,
            "provider_status": provider_status,
            "fallback_reason": fallback_reason,
            "precision": precision,
            "source_summary": source_summary,
        }

    @staticmethod
    def _normalize_weights(weights: Dict[str, Any]) -> Dict[str, float]:
        cost = float(weights.get("cost", 0.4) or 0.4)
        time_weight = float(weights.get("time", 0.3) or 0.3)
        satisfaction = float(weights.get("satisfaction", 0.3) or 0.3)
        total = cost + time_weight + satisfaction
        if total <= 0:
            return {"cost": 0.4, "time": 0.3, "satisfaction": 0.3}
        return {
            "cost": cost / total,
            "time": time_weight / total,
            "satisfaction": satisfaction / total,
        }

    @staticmethod
    def _coerce_limit(value: Any) -> int:
        try:
            return max(1, min(int(value), 500))
        except Exception:
            return DEFAULT_WAVE_LIMIT

    @staticmethod
    def _clean_filters(payload: Dict[str, Any]) -> Dict[str, Any]:
        allowed = (
            "order_ids",
            "vehicle_ids",
            "city",
            "origin_city",
            "destination_city",
            "status",
            "search",
            "limit",
            "algorithm",
            "solver",
            "max_orders_per_vehicle",
            "consider_weather",
            "consider_traffic",
            "use_precise_distance",
            "data_source",
        )
        return {key: payload.get(key) for key in allowed if payload.get(key) not in (None, "", [])}

    @staticmethod
    def _infer_order_source(orders: List[DispatchOrder]) -> str:
        if not orders:
            return "none"
        sources = Counter(order.data_source for order in orders)
        return sources.most_common(1)[0][0]

    @staticmethod
    def _select_data_source(legacy_total: int, fact_total: int) -> str:
        if fact_total > 0:
            return "shipment_fact"
        if legacy_total > 0:
            return "orders"
        return "none"

    @staticmethod
    def _rank_orders(
        orders: List[DispatchOrder],
        weights: Dict[str, float],
        algorithm: str,
    ) -> List[DispatchOrder]:
        priority_score = {"urgent": 0, "express": 1, "normal": 2, "low": 3}
        if algorithm == "capacity_first":
            return sorted(orders, key=lambda o: (-o.weight_kg, priority_score.get(o.priority, 2), o.created_at or datetime.min))
        return sorted(orders, key=lambda o: (priority_score.get(o.priority, 2), -(o.freight or 0), o.created_at or datetime.min))

    @staticmethod
    def _plan_suggestions(load_utilization: float, volume_utilization: float) -> List[str]:
        suggestions = []
        if load_utilization < 0.35:
            suggestions.append("载重利用率偏低，可尝试合并同城或同线路订单")
        if load_utilization > 0.92 or volume_utilization > 0.92:
            suggestions.append("车辆接近满载，执行前请复核超载与装载安全")
        if not suggestions:
            suggestions.append("当前车辆负载处于可执行区间")
        return suggestions

    @staticmethod
    def _weather_impact_stub(enabled: bool) -> Dict[str, Any]:
        return {
            "enabled": enabled,
            "provider_status": "shadow",
            "message": "天气影响已进入调度元数据，当前版本暂按中性影响处理",
            "delay_minutes": 0,
        }

    @staticmethod
    def _traffic_impact_stub(enabled: bool) -> Dict[str, Any]:
        return {
            "enabled": enabled,
            "provider_status": "shadow",
            "message": "路况影响已进入调度元数据，当前版本由距离 provider 统一承载",
            "delay_minutes": 0,
        }

    @staticmethod
    def _unassigned_order(
        order: DispatchOrder,
        vehicles: List[DispatchVehicle],
        max_orders_per_vehicle: int,
    ) -> Dict[str, Any]:
        max_weight_kg = max((v.capacity_weight_tons * 1000.0 for v in vehicles), default=0.0)
        max_volume = max((v.capacity_volume_m3 for v in vehicles), default=0.0)
        if order.weight_kg > max_weight_kg:
            reason = "订单重量超过单车最大载重"
        elif order.volume_m3 > max_volume:
            reason = "订单体积超过单车最大容积"
        else:
            reason = "车辆容量或每车订单上限不足"
        data = order.to_dict()
        data["reason"] = reason
        data["max_orders_per_vehicle"] = max_orders_per_vehicle
        return data

    @staticmethod
    def _diagnostic_recommendations(reason_counts: Counter) -> List[str]:
        recommendations = []
        if reason_counts.get("no_dispatchable_orders"):
            recommendations.append("当前订单源没有可调度记录，请检查订单状态映射或分层数据筛选")
        if reason_counts.get("no_available_vehicles"):
            recommendations.append("当前无可用车辆，请补充运营运力或释放车辆状态")
        if reason_counts.get("missing_coordinates"):
            recommendations.append("部分订单缺少起终点坐标，建议补齐 geocoding 或节点映射")
        if reason_counts.get("capacity_shortage_weight") or reason_counts.get("capacity_shortage_volume"):
            recommendations.append("当前波次需求超过可用运力，请降低波次规模或增加车辆")
        if not recommendations:
            recommendations.append("数据满足基础调度条件")
        return recommendations

    @staticmethod
    def _health_message(
        data_source: str,
        orders: List[DispatchOrder],
        vehicles: List[DispatchVehicle],
        diagnostics: Dict[str, Any],
    ) -> str:
        if data_source == "shipment_fact":
            base = "调度已连接 PostgreSQL 分层真实物流数据"
        elif data_source == "orders":
            base = "调度使用 legacy orders 数据"
        else:
            base = "未发现可调度订单数据"
        if not vehicles:
            return f"{base}，但暂无可用车辆"
        if diagnostics.get("capacity_gap_weight_kg", 0) > 0:
            return f"{base}，当前波次存在运力缺口"
        return f"{base}，基础调度条件可用"

    @staticmethod
    def _ai_shadow_summary(
        orders: List[DispatchOrder],
        plans: List[Dict[str, Any]],
        unassigned: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        city_pairs = Counter(
            f"{order.origin_name or '未知'}->{order.destination_name or '未知'}"
            for order in orders
        )
        top_lanes = [{"lane": lane, "orders": count} for lane, count in city_pairs.most_common(5)]
        risk_score = min(100, len(unassigned) * 8 + sum(1 for order in orders if not order.has_coordinates) * 2)
        return {
            "mode": "shadow",
            "enabled": True,
            "models": {
                "eta_prediction": "heuristic_baseline",
                "delay_risk": "heuristic_baseline",
                "dql_policy": "planned_shadow_only",
            },
            "risk_score": risk_score,
            "top_lanes": top_lanes,
            "recommendations": [
                "DQL/DQN 暂处于 shadow mode，只参与评分解释，不直接覆盖约束求解结果",
                "后续可用已落库 dispatch_scenarios/assignments 训练动态重调度策略",
            ],
        }

    def _dispatch_route_leg(
        self,
        order: DispatchOrder,
        distance_info: Dict[str, Any],
        distance_meta: Dict[str, Any],
        sequence: int,
    ) -> Dict[str, Any]:
        distance_source = (
            distance_info.get("distance_source")
            or distance_info.get("source")
            or distance_meta.get("distance_source")
            or "unknown"
        )
        provider_status = distance_info.get("provider_status") or self._leg_provider_status(distance_source)
        if provider_status == "unknown":
            provider_status = distance_meta.get("provider_status", "unknown")

        fallback_reason = distance_info.get("fallback_reason")
        if not fallback_reason and provider_status != "ok":
            fallback_reason = distance_meta.get("fallback_reason") or f"{distance_source}_distance_estimate"

        return {
            "sequence": sequence,
            "order_ref": order.ref,
            "order_number": order.order_number,
            "from_name": order.origin_name,
            "to_name": order.destination_name,
            "from_lng": order.origin_lng,
            "from_lat": order.origin_lat,
            "to_lng": order.destination_lng,
            "to_lat": order.destination_lat,
            "distance_km": round(float(distance_info.get("distance_km") or 0.0), 2),
            "duration_minutes": round(float(distance_info.get("duration_min") or 0.0), 2),
            "cost": round(float(distance_info.get("cost") or 0.0), 2),
            "data_source": order.data_source,
            "distance_source": distance_source,
            "duration_source": distance_source,
            "path_source": "dispatch_order_origin_destination_leg",
            "provider_status": provider_status,
            "fallback_reason": fallback_reason,
            "authenticity_level": self._route_truth_authenticity(
                order.data_source,
                {distance_source: 1},
                {provider_status: 1},
            ),
        }

    def _plan_route_truth(self, route_legs: Sequence[Dict[str, Any]], data_source: str) -> Dict[str, Any]:
        distance_counts: Counter = Counter()
        duration_counts: Counter = Counter()
        status_counts: Counter = Counter()
        fallback_counts: Counter = Counter()
        estimated_leg_count = 0

        for leg in route_legs:
            distance_source = leg.get("distance_source") or "unknown"
            duration_source = leg.get("duration_source") or distance_source
            provider_status = leg.get("provider_status") or self._leg_provider_status(distance_source)
            distance_counts[str(distance_source)] += 1
            duration_counts[str(duration_source)] += 1
            status_counts[str(provider_status)] += 1
            if provider_status != "ok" or not self._is_exact_leg_source(distance_source):
                estimated_leg_count += 1
            if leg.get("fallback_reason"):
                fallback_counts[str(leg["fallback_reason"])] += 1

        return {
            "path_source": "dispatch_assignment_sequence",
            "leg_type": "order_origin_destination",
            "leg_count": len(route_legs),
            "assignment_leg_count": len(route_legs),
            "estimated_leg_count": estimated_leg_count,
            "distance_source_counts": dict(distance_counts),
            "duration_source_counts": dict(duration_counts),
            "provider_status_counts": dict(status_counts),
            "fallback_reason_counts": dict(fallback_counts),
            "authenticity_level": self._route_truth_authenticity(
                data_source,
                dict(distance_counts),
                dict(status_counts),
            ),
            "note": "Dispatch route legs explain each order origin-to-destination assignment distance; they are not road-navigation polylines.",
        }

    def _dispatch_route_truth(self, plans: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
        distance_counts: Counter = Counter()
        duration_counts: Counter = Counter()
        status_counts: Counter = Counter()
        fallback_counts: Counter = Counter()
        total_legs = 0
        estimated_legs = 0
        data_sources: Counter = Counter()

        for plan in plans:
            truth = plan.get("route_truth") or {}
            total_legs += int(truth.get("leg_count") or 0)
            estimated_legs += int(truth.get("estimated_leg_count") or 0)
            self._merge_counts(distance_counts, truth.get("distance_source_counts") or {})
            self._merge_counts(duration_counts, truth.get("duration_source_counts") or {})
            self._merge_counts(status_counts, truth.get("provider_status_counts") or {})
            self._merge_counts(fallback_counts, truth.get("fallback_reason_counts") or {})
            for order in plan.get("orders") or []:
                data_sources[str(order.get("data_source") or "unknown")] += 1

        primary_data_source = data_sources.most_common(1)[0][0] if data_sources else "unknown"
        return {
            "path_source": "dispatch_assignment_sequence",
            "leg_type": "order_origin_destination",
            "leg_count": total_legs,
            "assignment_leg_count": total_legs,
            "estimated_leg_count": estimated_legs,
            "distance_source_counts": dict(distance_counts),
            "duration_source_counts": dict(duration_counts),
            "provider_status_counts": dict(status_counts),
            "fallback_reason_counts": dict(fallback_counts),
            "authenticity_level": self._route_truth_authenticity(
                primary_data_source,
                dict(distance_counts),
                dict(status_counts),
            ),
            "note": "Dispatch assignment sequence is a planning trace, not a provider road polyline.",
        }

    @staticmethod
    def _merge_counts(target: Counter, source: Dict[str, Any]) -> None:
        for key, value in source.items():
            try:
                target[str(key)] += int(value)
            except (TypeError, ValueError):
                continue

    @staticmethod
    def _is_exact_leg_source(distance_source: Any) -> bool:
        return str(distance_source or "") in {
            "amap_route",
            "amap_driving_route",
            "tianditu_route",
            "cache_exact",
            "distance_cache_exact",
        }

    @classmethod
    def _leg_provider_status(cls, distance_source: Any) -> str:
        source = str(distance_source or "unknown")
        if cls._is_exact_leg_source(source):
            return "ok"
        if source in {
            "cache_approx",
            "distance_cache_approx",
            "mixed_distance_provider",
            "precise_distance_provider",
        }:
            return "partial"
        if source in {
            "haversine_corrected",
            "missing_coordinates_default",
            "route_graph_unreachable",
            "route_segment_missing",
        }:
            return "degraded"
        return "unknown"

    @classmethod
    def _route_truth_authenticity(
        cls,
        data_source: str,
        distance_counts: Dict[str, Any],
        status_counts: Dict[str, Any],
    ) -> str:
        if not distance_counts:
            return "C"
        statuses = {str(key) for key, value in status_counts.items() if value}
        all_exact = all(cls._is_exact_leg_source(source) for source in distance_counts)
        if data_source == "shipment_fact" and statuses <= {"ok"} and all_exact:
            return "B"
        if data_source == "shipment_fact":
            return "B-"
        return "C"

    @staticmethod
    def _authenticity_level(data_source: str, distance_meta: Dict[str, Any]) -> str:
        if data_source == "shipment_fact" and distance_meta.get("distance_source") in {
            "amap_route",
            "distance_cache_exact",
            "mixed_distance_provider",
            "precise_distance_provider",
        }:
            return "B"
        if data_source == "shipment_fact":
            return "B-"
        return "C"

    @staticmethod
    def _legacy_truth_contract(data_source: str, distance_meta: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "data_source": (
                "postgres_shipment_facts_vehicles"
                if data_source == "shipment_fact"
                else "postgres_orders_vehicles_nodes"
            ),
            "distance_source": "haversine_legacy_dispatch",
            "actual_distance_source": distance_meta.get("distance_source"),
            "path_source": "dispatch_assignment_sequence",
            "authenticity_level": "C",
            "fallback_reason": (
                "legacy compatibility contract only; actual distance_source/provider_status "
                "fields describe the current dispatch preview truth."
            ),
        }

    @staticmethod
    def _solver_status(algorithm: str) -> Dict[str, Any]:
        algorithm = str(algorithm or "auto").lower()
        native = {"auto", "balanced", "greedy", "capacity_first"}
        if algorithm in native:
            return {"available": True, "status": "ok", "mode": "native_dispatch_wave"}
        if algorithm in {"ortools", "alns", "genetic", "pymoo_nsga2"}:
            try:
                from app.services.optimization_engine import SolverFactory, SolverType

                solver_type = SolverType(algorithm)
                available = SolverFactory.is_available(solver_type)
                return {
                    "available": bool(available),
                    "status": "available" if available else "shadow_fallback",
                    "mode": "solver_catalog",
                    "fallback_solver": None if available else "balanced",
                }
            except Exception as exc:
                return {
                    "available": False,
                    "status": "shadow_fallback",
                    "mode": "solver_catalog",
                    "fallback_solver": "balanced",
                    "reason": str(exc),
                }
        return {"available": False, "status": "unknown_solver", "fallback_solver": "balanced"}


_dispatch_orchestration_service: Optional[DispatchOrchestrationService] = None


def get_dispatch_orchestration_service() -> DispatchOrchestrationService:
    global _dispatch_orchestration_service
    if _dispatch_orchestration_service is None:
        _dispatch_orchestration_service = DispatchOrchestrationService()
    return _dispatch_orchestration_service
