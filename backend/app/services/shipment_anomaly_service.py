"""Real shipment-fact anomaly detection for AI upgrade Phase 3/4.

This service is intentionally separate from the legacy realtime anomaly demo
routes. It reads real `shipment_facts`, emits explainable rule/statistical
findings, and can optionally add IsolationForest findings when scikit-learn is
available in the runtime.
"""

from __future__ import annotations

import importlib.util
import math
import statistics
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np
from sqlalchemy import func, or_

from app.models import ShipmentFact, db


DEFAULT_ANOMALY_TASKS = ("status", "geo", "cost", "eta", "delay", "od_volume")
DEFAULT_LIMIT = 50000
MAX_ANOMALY_ROWS = 50000
MAX_ANOMALY_RETURN = 500
MIN_GROUP_SIZE = 5
MIN_ROBUST_ROWS = 6
DEFAULT_Z_THRESHOLD = 3.5
DEFAULT_DELAY_THRESHOLD_MINUTES = 120.0
DEFAULT_IFOREST_MIN_ROWS = 20


@dataclass
class ShipmentAnomalyRecord:
    id: Any
    fact_id: int
    shipment_id: Optional[str]
    order_id: Optional[str]
    origin_city: str
    destination_city: str
    transport_mode: str
    cargo_type: str
    status: str
    freight: float
    weight_kg: float
    volume_m3: float
    distance_km: Optional[float]
    transit_hours: Optional[float]
    delay_minutes: Optional[float]
    unit_cost_per_kg: Optional[float]
    group_key: str
    fallback_key: str
    payload: Dict[str, Any]


class ShipmentAnomalyService:
    """Detect explainable anomalies from real shipment facts."""

    def health(self) -> Dict[str, Any]:
        total = ShipmentFact.query.count()
        cost_records = ShipmentFact.query.filter(ShipmentFact.freight.isnot(None), ShipmentFact.freight > 0).count()
        geo_ready = ShipmentFact.query.filter(
            ShipmentFact.origin_lng.isnot(None),
            ShipmentFact.origin_lat.isnot(None),
            ShipmentFact.destination_lng.isnot(None),
            ShipmentFact.destination_lat.isnot(None),
        ).count()
        delivered_records = self._actual_delivery_query().count()
        delay_records = self._actual_delivery_query().filter(ShipmentFact.eta_at.isnot(None)).count()
        status_counts = self._status_counts()
        sklearn_available = self._sklearn_available()
        provider_status = "ok" if total else "degraded"

        return {
            "success": True,
            "data_source": "shipment_fact",
            "distance_source": "shipment_fact_coordinates_haversine_when_needed",
            "path_source": "not_route_geometry_anomaly_features",
            "provider_status": provider_status,
            "fallback_reason": None if total else "SHIPMENT_FACTS_EMPTY",
            "authenticity_level": "B" if total else "C",
            "model_stage": "phase3_anomaly_detection",
            "summary": {
                "total_records": total,
                "cost_records": cost_records,
                "geo_ready_records": geo_ready,
                "eta_records": delivered_records,
                "delay_records": delay_records,
                "status_counts": status_counts,
            },
            "readiness": {
                "rules": {"ready": total > 0, "status": "ready" if total else "insufficient_data"},
                "robust_statistics": {
                    "ready": any(count >= MIN_ROBUST_ROWS for count in (cost_records, delivered_records, delay_records)),
                    "minimum_required": MIN_ROBUST_ROWS,
                },
                "isolation_forest": {
                    "ready": sklearn_available and total >= DEFAULT_IFOREST_MIN_ROWS,
                    "available": sklearn_available,
                    "minimum_required": DEFAULT_IFOREST_MIN_ROWS,
                    "fallback_reason": None if sklearn_available else "SKLEARN_NOT_INSTALLED",
                },
            },
            "truth_contract": self._truth_contract(),
        }

    def detect(self, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        payload = payload or {}
        tasks = self._normalise_tasks(payload.get("tasks") or DEFAULT_ANOMALY_TASKS)
        limit = max(1, min(MAX_ANOMALY_ROWS, self._coerce_int(payload.get("limit"), DEFAULT_LIMIT)))
        anomaly_limit = max(1, min(MAX_ANOMALY_RETURN, self._coerce_int(payload.get("anomaly_limit"), 100)))
        city = self._clean_text(payload.get("city") or payload.get("destination_city"))
        z_threshold = self._bounded_float(payload.get("z_threshold"), DEFAULT_Z_THRESHOLD, 2.0, 8.0)
        min_group_size = max(2, min(50, self._coerce_int(payload.get("min_group_size"), MIN_GROUP_SIZE)))
        delay_threshold = self._bounded_float(
            payload.get("delay_threshold_minutes"),
            DEFAULT_DELAY_THRESHOLD_MINUTES,
            15.0,
            1440.0,
        )
        use_ml = self._coerce_bool(payload.get("use_ml"), default=True)
        contamination = self._bounded_float(payload.get("contamination"), 0.03, 0.005, 0.2)

        facts = self._query_facts(limit=limit, city=city)
        records = [self._record_from_fact(fact) for fact in facts]
        anomalies: List[Dict[str, Any]] = []

        if "status" in tasks:
            anomalies.extend(self._detect_status_anomalies(records))
        if "geo" in tasks:
            anomalies.extend(self._detect_geo_anomalies(records))
        if "cost" in tasks:
            anomalies.extend(
                self._detect_robust_numeric_anomalies(
                    records=records,
                    value_field="freight",
                    task="cost",
                    anomaly_type="cost_outlier",
                    unit="currency",
                    z_threshold=z_threshold,
                    min_group_size=min_group_size,
                )
            )
            anomalies.extend(
                self._detect_robust_numeric_anomalies(
                    records=[record for record in records if record.unit_cost_per_kg is not None],
                    value_field="unit_cost_per_kg",
                    task="cost",
                    anomaly_type="unit_cost_outlier",
                    unit="currency_per_kg",
                    z_threshold=z_threshold,
                    min_group_size=min_group_size,
                )
            )
        if "eta" in tasks:
            anomalies.extend(self._detect_transit_anomalies(records, z_threshold, min_group_size))
        if "delay" in tasks:
            anomalies.extend(self._detect_delay_anomalies(records, z_threshold, min_group_size, delay_threshold))
        if "od_volume" in tasks:
            anomalies.extend(self._detect_od_volume_anomalies(records, z_threshold))
        if "node_congestion" in tasks:
            anomalies.extend(self._detect_destination_volume_anomalies(records, z_threshold))

        ml_anomalies, ml_status = self._detect_ml_anomalies(
            records=records,
            enabled=use_ml,
            contamination=contamination,
        )
        if use_ml and "ml" in tasks:
            anomalies.extend(ml_anomalies)

        anomalies = self._dedupe_and_sort(anomalies)[:anomaly_limit]
        summary = self._summary(records, anomalies, tasks)
        provider_status = "ok" if records else "degraded"

        return {
            "success": True,
            "data_source": "shipment_fact",
            "distance_source": "shipment_fact_coordinates_haversine_when_needed",
            "path_source": "not_route_geometry_anomaly_features",
            "provider_status": provider_status,
            "fallback_reason": None if records else "SHIPMENT_FACTS_EMPTY",
            "authenticity_level": "B" if records else "C",
            "model_stage": "phase3_anomaly_detection",
            "detector_family": "rules+robust_statistics+optional_isolation_forest",
            "summary": summary,
            "anomalies": anomalies,
            "diagnostics": {
                "tasks": tasks,
                "limit": limit,
                "city": city,
                "z_threshold": z_threshold,
                "min_group_size": min_group_size,
                "delay_threshold_minutes": delay_threshold,
                "anomaly_limit": anomaly_limit,
                "ml_detector": ml_status,
            },
            "truth_contract": self._truth_contract(),
        }

    def scorecard(self, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Aggregate anomaly-detection readiness and risk pressure."""
        payload = payload or {}
        tasks = self._normalise_tasks(
            payload.get("tasks") or list(DEFAULT_ANOMALY_TASKS) + ["node_congestion", "ml"]
        )
        limit = max(1, min(MAX_ANOMALY_ROWS, self._coerce_int(payload.get("limit"), DEFAULT_LIMIT)))
        anomaly_limit = max(1, min(MAX_ANOMALY_RETURN, self._coerce_int(payload.get("anomaly_limit"), 100)))
        use_ml = self._coerce_bool(payload.get("use_ml"), default=True)

        health = self.health()
        detection = self.detect(
            {
                "tasks": tasks,
                "limit": limit,
                "anomaly_limit": anomaly_limit,
                "use_ml": use_ml,
                "z_threshold": payload.get("z_threshold", DEFAULT_Z_THRESHOLD),
                "min_group_size": payload.get("min_group_size", MIN_GROUP_SIZE),
                "delay_threshold_minutes": payload.get("delay_threshold_minutes", DEFAULT_DELAY_THRESHOLD_MINUTES),
            }
        )

        summary = detection.get("summary", {})
        anomalies = detection.get("anomalies", [])
        by_level = summary.get("by_level", {}) or {}
        critical_count = int(by_level.get("critical", 0) or 0)
        high_count = int(by_level.get("high", 0) or 0)
        medium_count = int(by_level.get("medium", 0) or 0)
        high_risk_count = critical_count + high_count
        records_scanned = int(summary.get("records_scanned", 0) or 0)
        anomaly_count = int(summary.get("anomaly_count", 0) or 0)
        high_risk_rate = high_risk_count / max(records_scanned, 1)

        explainable_count = sum(
            1
            for item in anomalies
            if item.get("explanation") and item.get("actions") and item.get("data_source") == "shipment_fact"
        )
        explainability_ratio = explainable_count / max(len(anomalies), 1) if anomalies else 1.0
        ml_status = detection.get("diagnostics", {}).get("ml_detector", {}) or {}
        ml_score = 100.0 if ml_status.get("used") else 70.0 if ml_status.get("available") else 55.0

        components = [
            self._scorecard_component(
                "data_readiness",
                "Real Anomaly Data",
                100.0 if health.get("provider_status") == "ok" else 20.0,
                "ok" if health.get("provider_status") == "ok" else "degraded",
                {
                    "total_records": health.get("summary", {}).get("total_records"),
                    "geo_ready_records": health.get("summary", {}).get("geo_ready_records"),
                    "delay_records": health.get("summary", {}).get("delay_records"),
                },
            ),
            self._scorecard_component(
                "signal_coverage",
                "Signal Coverage",
                100.0 * len(tasks) / max(len(set(DEFAULT_ANOMALY_TASKS) | {"node_congestion", "ml"}), 1),
                "ok" if set(DEFAULT_ANOMALY_TASKS).issubset(set(tasks)) else "degraded",
                {
                    "tasks": tasks,
                    "detector_family": detection.get("detector_family"),
                    "robust_statistics_ready": health.get("readiness", {}).get("robust_statistics", {}).get("ready"),
                },
            ),
            self._scorecard_component(
                "risk_pressure",
                "Current Risk Pressure",
                100.0 - min(70.0, high_risk_rate * 1000.0) - min(20.0, medium_count * 5.0),
                "ok" if high_risk_count == 0 else "watch",
                {
                    "anomaly_count": anomaly_count,
                    "critical": critical_count,
                    "high": high_count,
                    "medium": medium_count,
                    "anomaly_rate": summary.get("anomaly_rate"),
                },
            ),
            self._scorecard_component(
                "explainability",
                "Explainability Contract",
                100.0 * explainability_ratio,
                "ok" if explainability_ratio >= 0.95 else "degraded",
                {
                    "explainable_count": explainable_count,
                    "returned_anomalies": len(anomalies),
                    "path_source": detection.get("path_source"),
                },
            ),
            self._scorecard_component(
                "ml_shadow_readiness",
                "ML Shadow Readiness",
                ml_score,
                "ok" if ml_status.get("used") else "shadow",
                {
                    "enabled": ml_status.get("enabled"),
                    "used": ml_status.get("used"),
                    "detector": ml_status.get("detector"),
                    "fallback_reason": ml_status.get("fallback_reason"),
                },
            ),
        ]
        readiness_score = round(sum(component["score"] for component in components) / max(len(components), 1), 4)
        gates = [
            {
                "id": "real_data_available",
                "passed": health.get("provider_status") == "ok",
                "detail": "shipment_facts must be available for anomaly detection.",
            },
            {
                "id": "rule_and_statistics_ready",
                "passed": bool(health.get("readiness", {}).get("rules", {}).get("ready"))
                and bool(health.get("readiness", {}).get("robust_statistics", {}).get("ready")),
                "detail": "rules and robust statistics are the production-safe anomaly baseline.",
            },
            {
                "id": "explainability_contract",
                "passed": explainability_ratio >= 0.95,
                "detail": "returned anomalies should include explanations, actions, and truth metadata.",
            },
            {
                "id": "shadow_boundary_preserved",
                "passed": True,
                "detail": "scorecard is read-only and does not persist anomaly events.",
            },
        ]

        return {
            "success": True,
            "data_source": "shipment_fact",
            "distance_source": "shipment_fact_coordinates_haversine_when_needed",
            "path_source": "not_route_geometry_anomaly_features",
            "provider_status": "ok" if health.get("provider_status") == "ok" else "degraded",
            "fallback_reason": None if health.get("provider_status") == "ok" else health.get("fallback_reason"),
            "authenticity_level": "B" if health.get("provider_status") == "ok" else "C",
            "model_family": "anomaly_readiness_scorecard",
            "scorecard_version": "shipment_anomaly_scorecard_v1",
            "summary": {
                "readiness_score": readiness_score,
                "status": "ready" if readiness_score >= 85 else "watch" if readiness_score >= 65 else "needs_work",
                "records_scanned": records_scanned,
                "anomaly_count": anomaly_count,
                "high_risk_count": high_risk_count,
                "anomaly_rate": summary.get("anomaly_rate"),
                "tasks": tasks,
            },
            "components": components,
            "gates": gates,
            "recommendations": self._scorecard_recommendations(components, gates, high_risk_count),
            "evidence": {
                "health": {
                    "summary": health.get("summary", {}),
                    "readiness": health.get("readiness", {}),
                },
                "detection": {
                    "by_type": summary.get("by_type", {}),
                    "by_level": summary.get("by_level", {}),
                    "top_od_lanes": summary.get("top_od_lanes", []),
                    "ml_detector": ml_status,
                },
            },
            "truth_contract": {
                **self._truth_contract(),
                "business_mutation": "none",
                "deployment_boundary": "scorecard_readiness_only_anomaly_events_not_persisted",
                "scorecard_inputs": ["health", "detect"],
            },
        }

    def explain(self, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Return focused anomalies for one shipment/order identifier."""
        payload = payload or {}
        identifier = self._clean_text(payload.get("id") or payload.get("order_id") or payload.get("shipment_id"))
        if not identifier:
            return {
                "success": False,
                "data_source": "shipment_fact",
                "provider_status": "degraded",
                "fallback_reason": "MISSING_SHIPMENT_OR_ORDER_IDENTIFIER",
                "authenticity_level": "C",
                "truth_contract": self._truth_contract(),
            }

        fact = ShipmentFact.query.filter(
            or_(
                ShipmentFact.external_order_id == identifier,
                ShipmentFact.external_shipment_id == identifier,
                ShipmentFact.id == self._coerce_int(identifier, -1),
            )
        ).first()
        if not fact:
            return {
                "success": True,
                "data_source": "shipment_fact",
                "provider_status": "degraded",
                "fallback_reason": "SHIPMENT_FACT_NOT_FOUND",
                "authenticity_level": "C",
                "query": identifier,
                "anomalies": [],
                "truth_contract": self._truth_contract(),
            }

        full_result = self.detect({
            "limit": DEFAULT_LIMIT,
            "anomaly_limit": MAX_ANOMALY_RETURN,
            "tasks": list(DEFAULT_ANOMALY_TASKS) + ["node_congestion"],
            "use_ml": False,
        })
        matching = [
            item for item in full_result.get("anomalies", [])
            if item.get("fact_id") == fact.id
            or item.get("order_id") == fact.external_order_id
            or item.get("shipment_id") == fact.external_shipment_id
        ]
        return {
            "success": True,
            "data_source": "shipment_fact",
            "distance_source": "shipment_fact_coordinates_haversine_when_needed",
            "path_source": "not_route_geometry_anomaly_features",
            "provider_status": "ok",
            "fallback_reason": None,
            "authenticity_level": "B",
            "query": identifier,
            "fact": self._record_from_fact(fact).payload,
            "anomaly_count": len(matching),
            "anomalies": matching,
            "truth_contract": self._truth_contract(),
        }

    def _query_facts(self, limit: int, city: Optional[str] = None) -> List[Any]:
        query = ShipmentFact.query
        if city:
            query = query.filter(
                or_(
                    ShipmentFact.origin_city_std == city,
                    ShipmentFact.destination_city_std == city,
                )
            )
        rows = (
            query.with_entities(*self._fact_projection_columns())
            .order_by(ShipmentFact.shipped_at.asc(), ShipmentFact.id.asc())
            .limit(limit)
        )
        return list(self._iter_query(rows))

    def _fact_projection_columns(self):
        return (
            ShipmentFact.id,
            ShipmentFact.external_shipment_id,
            ShipmentFact.external_order_id,
            ShipmentFact.origin_city_std,
            ShipmentFact.destination_city_std,
            ShipmentFact.origin_lng,
            ShipmentFact.origin_lat,
            ShipmentFact.destination_lng,
            ShipmentFact.destination_lat,
            ShipmentFact.geo_status,
            ShipmentFact.cargo_type,
            ShipmentFact.transport_mode,
            ShipmentFact.freight,
            ShipmentFact.standard_status,
            ShipmentFact.exception_reason,
            ShipmentFact.shipped_at,
            ShipmentFact.eta_at,
            ShipmentFact.delivered_at,
            ShipmentFact.signed_at,
            ShipmentFact.weight_kg,
            ShipmentFact.volume_m3,
        )

    def _iter_query(self, query, chunk_size: int = 1000):
        return query.yield_per(chunk_size)

    def _record_from_fact(self, fact: Any) -> ShipmentAnomalyRecord:
        origin = self._clean_text(fact.origin_city_std) or "unknown_origin"
        destination = self._clean_text(fact.destination_city_std) or "unknown_destination"
        mode = self._clean_text(fact.transport_mode) or "unknown_mode"
        cargo = self._clean_text(fact.cargo_type) or "unknown_cargo"
        freight = self._coerce_float(fact.freight, 0.0)
        weight = self._coerce_float(fact.weight_kg, 0.0)
        volume = self._coerce_float(fact.volume_m3, 0.0)
        actual_at = self._actual_at(fact)
        transit_hours = None
        if fact.shipped_at and actual_at:
            transit_hours = (actual_at - fact.shipped_at).total_seconds() / 3600.0
        delay_minutes = None
        if fact.eta_at and actual_at:
            delay_minutes = (actual_at - fact.eta_at).total_seconds() / 60.0
        unit_cost = freight / weight if freight > 0 and weight > 0 else None
        distance_km = self._haversine_km(
            fact.origin_lng,
            fact.origin_lat,
            fact.destination_lng,
            fact.destination_lat,
        )
        payload = {
            "fact_id": fact.id,
            "shipment_id": fact.external_shipment_id,
            "order_id": fact.external_order_id,
            "origin_city": origin,
            "destination_city": destination,
            "transport_mode": mode,
            "cargo_type": cargo,
            "status": fact.standard_status or "unknown",
            "exception_reason": fact.exception_reason,
            "freight": freight,
            "weight_kg": weight,
            "volume_m3": volume,
            "distance_km": distance_km,
            "unit_cost_per_kg": unit_cost,
            "transit_hours": transit_hours,
            "delay_minutes": delay_minutes,
            "geo_status": fact.geo_status,
            "origin_lng": fact.origin_lng,
            "origin_lat": fact.origin_lat,
            "destination_lng": fact.destination_lng,
            "destination_lat": fact.destination_lat,
            "shipped_at": fact.shipped_at.isoformat() if fact.shipped_at else None,
            "eta_at": fact.eta_at.isoformat() if fact.eta_at else None,
            "actual_at": actual_at.isoformat() if actual_at else None,
        }
        return ShipmentAnomalyRecord(
            id=fact.external_order_id or fact.external_shipment_id or fact.id,
            fact_id=fact.id,
            shipment_id=fact.external_shipment_id,
            order_id=fact.external_order_id,
            origin_city=origin,
            destination_city=destination,
            transport_mode=mode,
            cargo_type=cargo,
            status=fact.standard_status or "unknown",
            freight=freight,
            weight_kg=weight,
            volume_m3=volume,
            distance_km=distance_km,
            transit_hours=transit_hours,
            delay_minutes=delay_minutes,
            unit_cost_per_kg=unit_cost,
            group_key="|".join([origin, destination, mode, cargo]),
            fallback_key="|".join([mode, cargo]),
            payload=payload,
        )

    def _detect_status_anomalies(self, records: Sequence[ShipmentAnomalyRecord]) -> List[Dict[str, Any]]:
        anomalies = []
        for record in records:
            is_exception = record.status == "exception" or bool(record.payload.get("exception_reason"))
            if not is_exception:
                continue
            anomalies.append(
                self._anomaly(
                    record=record,
                    anomaly_type="status_exception",
                    task="status",
                    score=75.0,
                    value=1.0,
                    baseline=None,
                    method="business_rule",
                    explanation="运单状态或异常原因字段显示该运单处于异常状态。",
                    evidence={
                        "status": record.status,
                        "exception_reason": record.payload.get("exception_reason"),
                    },
                    actions=["核查异常原因", "联系承运商或司机", "必要时触发重调度"],
                )
            )
        return anomalies

    def _detect_geo_anomalies(self, records: Sequence[ShipmentAnomalyRecord]) -> List[Dict[str, Any]]:
        anomalies = []
        for record in records:
            missing_fields = [
                field for field in ("origin_lng", "origin_lat", "destination_lng", "destination_lat")
                if record.payload.get(field) in (None, "")
            ]
            if missing_fields:
                anomalies.append(
                    self._anomaly(
                        record=record,
                        anomaly_type="coordinate_missing",
                        task="geo",
                        score=70.0,
                        value=float(len(missing_fields)),
                        baseline=0.0,
                        method="business_rule",
                        explanation="运单缺少起终点坐标，无法可靠参与真实路径、距离和调度计算。",
                        evidence={"missing_fields": missing_fields, "geo_status": record.payload.get("geo_status")},
                        actions=["补齐地理编码", "进入路线推荐前置校验", "避免作为真实路网样本训练"],
                    )
                )
                continue

            out_of_bounds = []
            for prefix in ("origin", "destination"):
                lng = self._optional_float(record.payload.get(f"{prefix}_lng"))
                lat = self._optional_float(record.payload.get(f"{prefix}_lat"))
                if lng is None or lat is None:
                    continue
                if not self._is_china_like_coordinate(lng, lat):
                    out_of_bounds.append({"point": prefix, "lng": lng, "lat": lat})
            if out_of_bounds:
                anomalies.append(
                    self._anomaly(
                        record=record,
                        anomaly_type="coordinate_out_of_bounds",
                        task="geo",
                        score=82.0,
                        value=float(len(out_of_bounds)),
                        baseline=0.0,
                        method="business_rule",
                        explanation="运单坐标超出中国物流网络常见范围，可能存在经纬度错误或地理编码污染。",
                        evidence={"points": out_of_bounds, "geo_status": record.payload.get("geo_status")},
                        actions=["重新地理编码", "检查经纬度顺序", "从训练样本中降权或隔离"],
                    )
                )
        return anomalies

    def _detect_robust_numeric_anomalies(
        self,
        records: Sequence[ShipmentAnomalyRecord],
        value_field: str,
        task: str,
        anomaly_type: str,
        unit: str,
        z_threshold: float,
        min_group_size: int,
    ) -> List[Dict[str, Any]]:
        values_by_group = self._values_by_key(records, value_field, "group_key")
        values_by_fallback = self._values_by_key(records, value_field, "fallback_key")
        global_values = [self._record_value(record, value_field) for record in records]
        global_values = [value for value in global_values if value is not None and math.isfinite(value)]
        global_stats = self._robust_stats(global_values)

        anomalies = []
        for record in records:
            value = self._record_value(record, value_field)
            if value is None or not math.isfinite(value) or value <= 0:
                continue
            baseline_key = record.group_key
            baseline_values = values_by_group.get(record.group_key, [])
            baseline_scope = "od_mode_cargo"
            if len(baseline_values) < min_group_size:
                baseline_key = record.fallback_key
                baseline_values = values_by_fallback.get(record.fallback_key, [])
                baseline_scope = "mode_cargo"
            stats = self._robust_stats(baseline_values if len(baseline_values) >= min_group_size else global_values)
            if stats["count"] < MIN_ROBUST_ROWS:
                continue
            z_score = self._robust_z(value, stats)
            if abs(z_score) <= z_threshold:
                continue
            score = min(99.0, 45.0 + abs(z_score) * 10.0)
            anomalies.append(
                self._anomaly(
                    record=record,
                    anomaly_type=anomaly_type,
                    task=task,
                    score=score,
                    value=value,
                    baseline=stats["median"],
                    method="robust_mad",
                    explanation=(
                        f"{value_field}={value:.2f} {unit} 相对 {baseline_scope} 基线中位数 "
                        f"{stats['median']:.2f} 的稳健 z-score 为 {z_score:.2f}。"
                    ),
                    evidence={
                        "value_field": value_field,
                        "unit": unit,
                        "robust_z": round(z_score, 6),
                        "threshold": z_threshold,
                        "baseline_scope": baseline_scope,
                        "baseline_key": baseline_key,
                        "baseline_count": stats["count"],
                        "global_median": global_stats.get("median"),
                    },
                    actions=["复核费用口径", "检查计费重量/体积", "对同 OD/mode/cargo 历史样本做人工抽检"],
                )
            )
        return anomalies

    def _detect_transit_anomalies(
        self,
        records: Sequence[ShipmentAnomalyRecord],
        z_threshold: float,
        min_group_size: int,
    ) -> List[Dict[str, Any]]:
        anomalies = []
        for record in records:
            if record.transit_hours is not None and record.transit_hours <= 0:
                anomalies.append(
                    self._anomaly(
                        record=record,
                        anomaly_type="invalid_transit_time",
                        task="eta",
                        score=88.0,
                        value=record.transit_hours,
                        baseline=0.0,
                        method="business_rule",
                        explanation="实际签收/送达时间早于发运时间，时效字段存在时间顺序异常。",
                        evidence={"transit_hours": record.transit_hours},
                        actions=["修正时间字段", "隔离 ETA 训练样本", "检查原始导入记录"],
                    )
                )
        valid_records = [record for record in records if record.transit_hours is not None and record.transit_hours > 0]
        anomalies.extend(
            self._detect_robust_numeric_anomalies(
                records=valid_records,
                value_field="transit_hours",
                task="eta",
                anomaly_type="eta_transit_outlier",
                unit="hours",
                z_threshold=z_threshold,
                min_group_size=min_group_size,
            )
        )
        return anomalies

    def _detect_delay_anomalies(
        self,
        records: Sequence[ShipmentAnomalyRecord],
        z_threshold: float,
        min_group_size: int,
        delay_threshold: float,
    ) -> List[Dict[str, Any]]:
        anomalies = []
        valid_records = [record for record in records if record.delay_minutes is not None]
        for record in valid_records:
            if record.delay_minutes is not None and record.delay_minutes >= delay_threshold:
                score = min(99.0, 55.0 + (record.delay_minutes / max(delay_threshold, 1.0)) * 15.0)
                anomalies.append(
                    self._anomaly(
                        record=record,
                        anomaly_type="delay_threshold_breach",
                        task="delay",
                        score=score,
                        value=record.delay_minutes,
                        baseline=delay_threshold,
                        method="business_rule",
                        explanation=f"到达/签收时间比 ETA 晚 {record.delay_minutes:.1f} 分钟，超过阈值 {delay_threshold:.1f} 分钟。",
                        evidence={"delay_minutes": round(record.delay_minutes, 6), "threshold_minutes": delay_threshold},
                        actions=["复盘路况/装卸/司机执行原因", "更新 ETA 风险模型标签", "纳入动态重调度样本"],
                    )
                )
        anomalies.extend(
            self._detect_robust_numeric_anomalies(
                records=valid_records,
                value_field="delay_minutes",
                task="delay",
                anomaly_type="delay_distribution_outlier",
                unit="minutes",
                z_threshold=z_threshold,
                min_group_size=min_group_size,
            )
        )
        return anomalies

    def _detect_od_volume_anomalies(
        self,
        records: Sequence[ShipmentAnomalyRecord],
        z_threshold: float,
    ) -> List[Dict[str, Any]]:
        counts: Counter[str] = Counter(record.group_key for record in records)
        stats = self._robust_stats([float(value) for value in counts.values()])
        if stats["count"] < MIN_ROBUST_ROWS:
            return []

        anomalies = []
        by_key = defaultdict(list)
        for record in records:
            by_key[record.group_key].append(record)
        for key, count in counts.items():
            z_score = self._robust_z(float(count), stats)
            if z_score <= z_threshold:
                continue
            sample = by_key[key][0]
            anomalies.append(
                {
                    "anomaly_id": f"od_volume_spike:{key}",
                    "anomaly_type": "od_volume_spike",
                    "task": "od_volume",
                    "level": self._level_from_score(min(95.0, 45.0 + z_score * 10.0)),
                    "score": round(min(95.0, 45.0 + z_score * 10.0), 4),
                    "source": "od_lane",
                    "source_id": key,
                    "fact_id": None,
                    "shipment_id": None,
                    "order_id": None,
                    "origin_city": sample.origin_city,
                    "destination_city": sample.destination_city,
                    "transport_mode": sample.transport_mode,
                    "cargo_type": sample.cargo_type,
                    "detected_at": self._now_iso(),
                    "value": float(count),
                    "baseline": stats["median"],
                    "method": "robust_mad",
                    "explanation": f"OD/mode/cargo 组合 {key} 的样本量 {count} 显著高于网络常态。",
                    "evidence": {
                        "group_key": key,
                        "robust_z": round(z_score, 6),
                        "median_lane_volume": stats["median"],
                        "lane_count": stats["count"],
                    },
                    "actions": ["检查需求热区", "评估临时运力加班", "纳入网络设计 OD 聚合"],
                    "data_source": "shipment_fact",
                    "distance_source": "not_required_for_volume_anomaly",
                    "path_source": "od_aggregate_not_route_geometry",
                    "authenticity_level": "B",
                }
            )
        return anomalies

    def _detect_destination_volume_anomalies(
        self,
        records: Sequence[ShipmentAnomalyRecord],
        z_threshold: float,
    ) -> List[Dict[str, Any]]:
        counts: Counter[str] = Counter(record.destination_city for record in records)
        stats = self._robust_stats([float(value) for value in counts.values()])
        if stats["count"] < MIN_ROBUST_ROWS:
            return []
        anomalies = []
        for city, count in counts.items():
            z_score = self._robust_z(float(count), stats)
            if z_score <= z_threshold:
                continue
            anomalies.append(
                {
                    "anomaly_id": f"destination_volume_spike:{city}",
                    "anomaly_type": "destination_volume_spike",
                    "task": "node_congestion",
                    "level": self._level_from_score(min(95.0, 45.0 + z_score * 10.0)),
                    "score": round(min(95.0, 45.0 + z_score * 10.0), 4),
                    "source": "destination_city",
                    "source_id": city,
                    "fact_id": None,
                    "shipment_id": None,
                    "order_id": None,
                    "origin_city": None,
                    "destination_city": city,
                    "transport_mode": None,
                    "cargo_type": None,
                    "detected_at": self._now_iso(),
                    "value": float(count),
                    "baseline": stats["median"],
                    "method": "robust_mad",
                    "explanation": f"目的城市 {city} 的运单量 {count} 显著高于其他节点。",
                    "evidence": {
                        "destination_city": city,
                        "robust_z": round(z_score, 6),
                        "median_destination_volume": stats["median"],
                    },
                    "actions": ["检查节点拥堵", "增加目的城市临时运力", "纳入网络节点扩容候选"],
                    "data_source": "shipment_fact",
                    "distance_source": "not_required_for_node_volume_anomaly",
                    "path_source": "destination_aggregate_not_route_geometry",
                    "authenticity_level": "B",
                }
            )
        return anomalies

    def _detect_ml_anomalies(
        self,
        records: Sequence[ShipmentAnomalyRecord],
        enabled: bool,
        contamination: float,
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        if not enabled:
            return [], {"enabled": False, "used": False, "fallback_reason": "DISABLED_BY_REQUEST"}
        if not self._sklearn_available():
            return [], {
                "enabled": True,
                "used": False,
                "detector": "isolation_forest",
                "fallback_reason": "SKLEARN_NOT_INSTALLED",
            }

        rows = []
        row_records = []
        for record in records:
            vector = [
                record.freight,
                record.weight_kg,
                record.volume_m3,
                record.distance_km,
                record.transit_hours,
                record.delay_minutes,
                record.unit_cost_per_kg,
            ]
            if all(value is None for value in vector):
                continue
            rows.append([self._coerce_float(value, np.nan) for value in vector])
            row_records.append(record)
        if len(rows) < DEFAULT_IFOREST_MIN_ROWS:
            return [], {
                "enabled": True,
                "used": False,
                "detector": "isolation_forest",
                "fallback_reason": "IFOREST_ROWS_INSUFFICIENT",
                "rows": len(rows),
                "minimum_required": DEFAULT_IFOREST_MIN_ROWS,
            }

        try:
            from sklearn.ensemble import IsolationForest
        except Exception as exc:
            return [], {
                "enabled": True,
                "used": False,
                "detector": "isolation_forest",
                "fallback_reason": f"SKLEARN_IMPORT_FAILED:{exc.__class__.__name__}",
            }

        matrix = np.asarray(rows, dtype=float)
        medians = np.nanmedian(matrix, axis=0)
        medians = np.where(np.isfinite(medians), medians, 0.0)
        indices = np.where(~np.isfinite(matrix))
        matrix[indices] = np.take(medians, indices[1])
        try:
            model = IsolationForest(
                n_estimators=100,
                contamination=contamination,
                random_state=42,
            )
            labels = model.fit_predict(matrix)
            scores = model.decision_function(matrix)
        except Exception as exc:
            return [], {
                "enabled": True,
                "used": False,
                "detector": "isolation_forest",
                "fallback_reason": f"IFOREST_FAILED:{exc.__class__.__name__}",
            }

        anomalies = []
        min_score = float(np.min(scores)) if len(scores) else 0.0
        max_score = float(np.max(scores)) if len(scores) else 1.0
        spread = max(max_score - min_score, 1e-9)
        for record, label, raw_score in zip(row_records, labels, scores):
            if label != -1:
                continue
            normalized = (max_score - float(raw_score)) / spread
            score = min(98.0, 55.0 + normalized * 35.0)
            anomalies.append(
                self._anomaly(
                    record=record,
                    anomaly_type="ml_multivariate_outlier",
                    task="ml",
                    score=score,
                    value=round(float(raw_score), 6),
                    baseline=0.0,
                    method="isolation_forest",
                    explanation="IsolationForest 在费用、重量、体积、距离、时效、延误等联合特征上识别出多变量异常。",
                    evidence={
                        "isolation_score": round(float(raw_score), 6),
                        "contamination": contamination,
                        "feature_names": [
                            "freight",
                            "weight_kg",
                            "volume_m3",
                            "distance_km",
                            "transit_hours",
                            "delay_minutes",
                            "unit_cost_per_kg",
                        ],
                    },
                    actions=["进入人工复核队列", "检查是否为规则漏检异常", "用于后续 IsolationForest/LOF 模型校准"],
                )
            )
        return anomalies, {
            "enabled": True,
            "used": True,
            "detector": "isolation_forest",
            "rows": len(row_records),
            "contamination": contamination,
            "anomaly_count": len(anomalies),
            "fallback_reason": None,
        }

    def _anomaly(
        self,
        record: ShipmentAnomalyRecord,
        anomaly_type: str,
        task: str,
        score: float,
        value: Optional[float],
        baseline: Optional[float],
        method: str,
        explanation: str,
        evidence: Dict[str, Any],
        actions: List[str],
    ) -> Dict[str, Any]:
        return {
            "anomaly_id": f"{anomaly_type}:{record.fact_id}",
            "anomaly_type": anomaly_type,
            "task": task,
            "level": self._level_from_score(score),
            "score": round(float(score), 4),
            "source": "shipment_fact",
            "source_id": record.id,
            "fact_id": record.fact_id,
            "shipment_id": record.shipment_id,
            "order_id": record.order_id,
            "origin_city": record.origin_city,
            "destination_city": record.destination_city,
            "transport_mode": record.transport_mode,
            "cargo_type": record.cargo_type,
            "status": record.status,
            "detected_at": self._now_iso(),
            "value": None if value is None else round(float(value), 6),
            "baseline": None if baseline is None else round(float(baseline), 6),
            "method": method,
            "explanation": explanation,
            "evidence": evidence,
            "actions": actions,
            "data_source": "shipment_fact",
            "distance_source": "shipment_fact_coordinates_haversine_when_needed",
            "path_source": "not_route_geometry_anomaly_features",
            "authenticity_level": "B",
        }

    def _dedupe_and_sort(self, anomalies: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
        seen = set()
        result = []
        for item in anomalies:
            key = item.get("anomaly_id")
            if key in seen:
                continue
            seen.add(key)
            result.append(item)
        return sorted(
            result,
            key=lambda item: (
                -float(item.get("score") or 0.0),
                str(item.get("anomaly_type") or ""),
                str(item.get("source_id") or ""),
            ),
        )

    def _summary(
        self,
        records: Sequence[ShipmentAnomalyRecord],
        anomalies: Sequence[Dict[str, Any]],
        tasks: Sequence[str],
    ) -> Dict[str, Any]:
        by_type = Counter(item.get("anomaly_type") for item in anomalies)
        by_level = Counter(item.get("level") for item in anomalies)
        top_od = Counter(record.group_key for record in records).most_common(10)
        return {
            "records_scanned": len(records),
            "anomaly_count": len(anomalies),
            "anomaly_rate": round(len(anomalies) / max(len(records), 1), 6),
            "by_type": dict(sorted(by_type.items())),
            "by_level": dict(sorted(by_level.items())),
            "tasks": list(tasks),
            "top_od_lanes": [
                {"group_key": key, "shipment_count": count}
                for key, count in top_od
            ],
        }

    def _scorecard_component(
        self,
        component_id: str,
        label: str,
        score: float,
        status: str,
        details: Dict[str, Any],
    ) -> Dict[str, Any]:
        return {
            "id": component_id,
            "label": label,
            "score": round(max(0.0, min(100.0, float(score))), 4),
            "status": status,
            "details": details,
        }

    def _scorecard_recommendations(
        self,
        components: Sequence[Dict[str, Any]],
        gates: Sequence[Dict[str, Any]],
        high_risk_count: int,
    ) -> List[str]:
        recommendations = []
        if any(not gate.get("passed") for gate in gates):
            recommendations.append("存在未通过 readiness gate，建议先补齐真实数据、稳健统计样本或异常解释字段。")
        if high_risk_count:
            recommendations.append(f"当前存在 {high_risk_count} 个高风险/严重异常，建议优先进入人工复核和调度/客服处置队列。")
        weak_components = [component for component in components if float(component.get("score", 0.0)) < 70.0]
        for component in weak_components:
            if component.get("id") == "risk_pressure":
                recommendations.append("异常压力偏高，建议按异常等级和 OD 线路聚合生成治理任务。")
            elif component.get("id") == "ml_shadow_readiness":
                recommendations.append("ML shadow readiness 偏低时，规则检测仍为主链路；后续可补 IsolationForest/LOF/Autoencoder 离线对比。")
            elif component.get("id") == "signal_coverage":
                recommendations.append("异常信号覆盖不足，建议确保 status/geo/cost/eta/delay/od_volume/node_congestion 均进入检测。")
        if not recommendations:
            recommendations.append("异常检测链路具备较好的 explainable readiness，可继续推进异常落库和 DQL/DQN shadow 训练数据生成。")
        recommendations.append("该 scorecard 只做只读验收，不写异常事件表，也不直接改变订单、车辆或调度结果。")
        return recommendations

    def _values_by_key(
        self,
        records: Sequence[ShipmentAnomalyRecord],
        value_field: str,
        key_field: str,
    ) -> Dict[str, List[float]]:
        result: Dict[str, List[float]] = defaultdict(list)
        for record in records:
            value = self._record_value(record, value_field)
            if value is None or not math.isfinite(value):
                continue
            key = getattr(record, key_field)
            result[key].append(float(value))
        return result

    def _record_value(self, record: ShipmentAnomalyRecord, field: str) -> Optional[float]:
        if hasattr(record, field):
            return getattr(record, field)
        return self._optional_float(record.payload.get(field))

    def _robust_stats(self, values: Sequence[float]) -> Dict[str, Any]:
        clean = [float(value) for value in values if value is not None and math.isfinite(float(value))]
        if not clean:
            return {"count": 0, "median": 0.0, "mad": 0.0, "scale": 1.0}
        median = float(statistics.median(clean))
        deviations = [abs(value - median) for value in clean]
        mad = float(statistics.median(deviations)) if deviations else 0.0
        if mad > 1e-9:
            scale = mad * 1.4826
        elif len(clean) > 1:
            std = float(statistics.pstdev(clean))
            scale = std if std > 1e-9 else max(abs(median) * 0.1, 1.0)
        else:
            scale = max(abs(median) * 0.1, 1.0)
        return {
            "count": len(clean),
            "median": round(median, 6),
            "mad": round(mad, 6),
            "scale": scale,
        }

    def _robust_z(self, value: float, stats: Dict[str, Any]) -> float:
        return (float(value) - float(stats.get("median", 0.0))) / max(float(stats.get("scale") or 1.0), 1e-9)

    def _actual_delivery_query(self):
        return ShipmentFact.query.filter(
            ShipmentFact.shipped_at.isnot(None),
            or_(ShipmentFact.delivered_at.isnot(None), ShipmentFact.signed_at.isnot(None)),
        )

    def _actual_at(self, fact: ShipmentFact) -> Optional[datetime]:
        return fact.delivered_at or fact.signed_at

    def _status_counts(self) -> Dict[str, int]:
        rows = (
            db.session.query(ShipmentFact.standard_status, func.count(ShipmentFact.id))
            .group_by(ShipmentFact.standard_status)
            .all()
        )
        return {str(status or "unknown"): int(count or 0) for status, count in rows}

    def _truth_contract(self) -> Dict[str, Any]:
        return {
            "data_source": "shipment_fact",
            "distance_source": "shipment_fact_coordinates_haversine_when_needed",
            "path_source": "not_route_geometry_anomaly_features",
            "provider_status": "ok_or_degraded_per_dataset_readiness",
            "fallback_reason": "set_when_records_are_insufficient_or_optional_ml_dependency_missing",
            "authenticity_level": "B_for_real_fact_anomaly_detection_C_when_insufficient",
        }

    def _normalise_tasks(self, tasks: Any) -> List[str]:
        if isinstance(tasks, str):
            raw = [item.strip() for item in tasks.split(",")]
        else:
            raw = [str(item).strip() for item in tasks]
        supported = set(DEFAULT_ANOMALY_TASKS) | {"node_congestion", "ml"}
        result = []
        for item in raw:
            task = item.lower()
            if task in supported and task not in result:
                result.append(task)
        return result or list(DEFAULT_ANOMALY_TASKS)

    def _haversine_km(self, lng1: Any, lat1: Any, lng2: Any, lat2: Any) -> Optional[float]:
        lng1 = self._optional_float(lng1)
        lat1 = self._optional_float(lat1)
        lng2 = self._optional_float(lng2)
        lat2 = self._optional_float(lat2)
        if None in {lng1, lat1, lng2, lat2}:
            return None
        radius_km = 6371.0088
        d_lat = math.radians(lat2 - lat1)
        d_lng = math.radians(lng2 - lng1)
        a = (
            math.sin(d_lat / 2) ** 2
            + math.cos(math.radians(lat1))
            * math.cos(math.radians(lat2))
            * math.sin(d_lng / 2) ** 2
        )
        return round(radius_km * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)) * 1.18, 4)

    def _is_china_like_coordinate(self, lng: float, lat: float) -> bool:
        return 73.0 <= lng <= 136.0 and 3.0 <= lat <= 54.5

    def _sklearn_available(self) -> bool:
        return importlib.util.find_spec("sklearn") is not None

    def _level_from_score(self, score: float) -> str:
        if score >= 85:
            return "critical"
        if score >= 70:
            return "high"
        if score >= 50:
            return "medium"
        return "low"

    def _coerce_int(self, value: Any, default: int) -> int:
        try:
            if value is None or value == "":
                return default
            return int(value)
        except (TypeError, ValueError):
            return default

    def _coerce_float(self, value: Any, default: float) -> float:
        try:
            if value is None or value == "":
                return default
            return float(value)
        except (TypeError, ValueError):
            return default

    def _bounded_float(self, value: Any, default: float, minimum: float, maximum: float) -> float:
        number = self._coerce_float(value, default)
        return max(minimum, min(maximum, number))

    def _optional_float(self, value: Any) -> Optional[float]:
        try:
            if value is None or value == "":
                return None
            return float(value)
        except (TypeError, ValueError):
            return None

    def _coerce_bool(self, value: Any, default: bool) -> bool:
        if value is None:
            return default
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}

    def _clean_text(self, value: Any) -> Optional[str]:
        text = str(value).strip() if value is not None else ""
        return text or None

    def _now_iso(self) -> str:
        return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


_service: Optional[ShipmentAnomalyService] = None


def get_shipment_anomaly_service() -> ShipmentAnomalyService:
    global _service
    if _service is None:
        _service = ShipmentAnomalyService()
    return _service
