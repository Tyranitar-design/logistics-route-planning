"""Real shipment-fact cost and operations analytics.

This service is a truthful dashboard layer over `shipment_facts`. It avoids
the legacy cost module's mock fallbacks and reports exactly which parts are
real freight facts versus feature-level estimates.
"""

from __future__ import annotations

import math
import statistics
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Sequence

from sqlalchemy import or_

from app.models import ShipmentFact


DEFAULT_LIMIT = 50000


class ShipmentCostAnalyticsService:
    """Build cost, service-level, and operations KPIs from shipment_facts."""

    def operations_summary(self, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        payload = payload or {}
        limit = max(1, min(DEFAULT_LIMIT, self._coerce_int(payload.get("limit"), DEFAULT_LIMIT)))
        trend_days = max(7, min(120, self._coerce_int(payload.get("trend_days"), 30)))
        lane_limit = max(3, min(30, self._coerce_int(payload.get("lane_limit"), 8)))
        city = self._clean_text(payload.get("city") or payload.get("destination_city"))

        facts = self._query_facts(limit=limit, city=city)
        if not facts:
            return {
                "success": True,
                "data_source": "shipment_fact",
                "provider_status": "degraded",
                "fallback_reason": "SHIPMENT_FACTS_EMPTY_FOR_COST_ANALYTICS",
                "authenticity_level": "C",
                "summary": self._empty_summary(limit=limit, city=city),
                "kpis": {},
                "cost_components": [],
                "trend": [],
                "top_lanes": [],
                "city_breakdown": [],
                "recommendations": ["导入真实 shipment_facts 后才能生成成本运营总览。"],
                "truth_contract": self._truth_contract(),
            }

        kpis = self._kpis(facts)
        top_lanes = self._top_lanes(facts, lane_limit=lane_limit)
        city_breakdown = self._city_breakdown(facts, limit=lane_limit)
        trend = self._trend(facts, trend_days=trend_days)
        status_counts = dict(Counter(self._status(fact) for fact in facts))
        provider_status = "ok" if kpis["freight_records"] > 0 else "degraded"
        fallback_reason = None if provider_status == "ok" else "FREIGHT_FIELDS_EMPTY_OR_ZERO"

        return {
            "success": True,
            "data_source": "shipment_fact",
            "provider_status": provider_status,
            "fallback_reason": fallback_reason,
            "authenticity_level": "B" if provider_status == "ok" else "C",
            "model_family": "shipment_fact_cost_operations_summary",
            "summary_version": "shipment_cost_operations_v1",
            "summary": {
                "records_scanned": len(facts),
                "limit": limit,
                "city": city,
                "trend_days": trend_days,
                "lane_limit": lane_limit,
                "status_counts": status_counts,
            },
            "kpis": kpis,
            "cost_components": self._cost_components(kpis),
            "trend": trend,
            "top_lanes": top_lanes,
            "city_breakdown": city_breakdown,
            "recommendations": self._recommendations(kpis, top_lanes),
            "truth_contract": self._truth_contract(),
        }

    def operations_scorecard(self, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Aggregate cost and service KPIs into one operations readiness scorecard."""
        payload = payload or {}
        summary = self.operations_summary(payload)
        kpis = summary.get("kpis") or {}
        top_lanes = summary.get("top_lanes") or []
        if not kpis:
            return {
                "success": True,
                "data_source": "shipment_fact",
                "provider_status": "degraded",
                "fallback_reason": summary.get("fallback_reason") or "OPERATIONS_KPIS_EMPTY",
                "authenticity_level": "C",
                "model_family": "shipment_fact_operations_scorecard",
                "scorecard_version": "shipment_operations_scorecard_v1",
                "summary": {
                    "readiness_score": 0.0,
                    "status": "needs_work",
                    "records_scanned": summary.get("summary", {}).get("records_scanned", 0),
                },
                "components": [],
                "gates": [],
                "recommendations": summary.get("recommendations", []),
                "evidence": {"operations_summary": summary.get("summary", {})},
                "truth_contract": {
                    **self._truth_contract(),
                    "deployment_boundary": "scorecard_readiness_only_not_accounting_or_dispatch_controller",
                },
            }

        freight_coverage = kpis.get("freight_coverage") or 0.0
        completion_rate = kpis.get("delivery_completion_rate") or 0.0
        on_time_rate = kpis.get("on_time_rate") if kpis.get("on_time_rate") is not None else 0.0
        exception_rate = kpis.get("exception_rate") or 0.0
        lane_concentration = max((lane.get("freight_share") or 0.0 for lane in top_lanes), default=0.0)
        cost_efficiency = self._cost_efficiency_score(kpis, top_lanes)

        components = [
            self._scorecard_component(
                "data_coverage",
                "Freight Data Coverage",
                100.0 * freight_coverage,
                "ok" if freight_coverage >= 0.9 else "degraded",
                {
                    "freight_coverage": freight_coverage,
                    "freight_records": kpis.get("freight_records"),
                    "total_shipments": kpis.get("total_shipments"),
                },
            ),
            self._scorecard_component(
                "service_quality",
                "Service Quality",
                55.0 * completion_rate + 45.0 * on_time_rate,
                "ok" if completion_rate >= 0.95 and on_time_rate >= 0.85 else "watch",
                {
                    "delivery_completion_rate": completion_rate,
                    "on_time_rate": on_time_rate,
                    "avg_delay_minutes": kpis.get("avg_delay_minutes"),
                },
            ),
            self._scorecard_component(
                "cost_efficiency",
                "Cost Efficiency",
                cost_efficiency,
                "ok" if cost_efficiency >= 75 else "watch",
                {
                    "freight_per_kg": kpis.get("freight_per_kg"),
                    "freight_per_m3": kpis.get("freight_per_m3"),
                    "avg_freight_per_paid_shipment": kpis.get("avg_freight_per_paid_shipment"),
                },
            ),
            self._scorecard_component(
                "exception_pressure",
                "Exception Pressure",
                100.0 - min(70.0, exception_rate * 500.0),
                "ok" if exception_rate <= 0.03 else "watch",
                {
                    "exception_rate": exception_rate,
                    "exception_shipments": kpis.get("exception_shipments"),
                },
            ),
            self._scorecard_component(
                "lane_concentration",
                "Lane Cost Concentration",
                100.0 - min(60.0, lane_concentration * 120.0),
                "ok" if lane_concentration <= 0.35 else "watch",
                {
                    "top_lane": top_lanes[0].get("lane") if top_lanes else None,
                    "top_lane_freight_share": lane_concentration,
                    "top_lane_count": len(top_lanes),
                },
            ),
        ]
        readiness_score = round(sum(component["score"] for component in components) / len(components), 4)
        gates = [
            {
                "id": "real_freight_available",
                "passed": freight_coverage > 0,
                "detail": "shipment_facts.freight must be available for cost analysis.",
            },
            {
                "id": "service_kpis_available",
                "passed": kpis.get("eta_records", 0) > 0 and kpis.get("delivered_shipments", 0) > 0,
                "detail": "ETA and actual delivery timestamps must support service-level KPIs.",
            },
            {
                "id": "unit_cost_available",
                "passed": kpis.get("freight_per_kg") is not None or kpis.get("freight_per_m3") is not None,
                "detail": "Weight or volume should be present for unit-cost metrics.",
            },
            {
                "id": "shadow_boundary_preserved",
                "passed": True,
                "detail": "scorecard is read-only and does not mutate financial, order, or dispatch state.",
            },
        ]

        return {
            "success": True,
            "data_source": "shipment_fact",
            "provider_status": summary.get("provider_status"),
            "fallback_reason": summary.get("fallback_reason"),
            "authenticity_level": summary.get("authenticity_level"),
            "model_family": "shipment_fact_operations_scorecard",
            "scorecard_version": "shipment_operations_scorecard_v1",
            "summary": {
                "readiness_score": readiness_score,
                "status": "ready" if readiness_score >= 85 else "watch" if readiness_score >= 65 else "needs_work",
                "records_scanned": summary.get("summary", {}).get("records_scanned", 0),
                "total_freight": kpis.get("total_freight"),
                "on_time_rate": on_time_rate,
                "exception_rate": exception_rate,
                "top_lane_freight_share": lane_concentration,
            },
            "components": components,
            "gates": gates,
            "recommendations": self._scorecard_recommendations(components, gates, summary.get("recommendations", [])),
            "evidence": {
                "kpis": kpis,
                "top_lanes": top_lanes[:5],
                "cost_components": summary.get("cost_components", []),
                "trend_tail": (summary.get("trend") or [])[-7:],
            },
            "truth_contract": {
                **self._truth_contract(),
                "deployment_boundary": "scorecard_readiness_only_not_accounting_or_dispatch_controller",
                "scorecard_inputs": ["operations_summary"],
            },
        }

    def _query_facts(self, limit: int, city: Optional[str]) -> List[Any]:
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
            ShipmentFact.origin_city_std,
            ShipmentFact.destination_city_std,
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

    def _kpis(self, facts: Sequence[ShipmentFact]) -> Dict[str, Any]:
        freight_values = [self._positive_float(fact.freight) for fact in facts]
        freight_values = [value for value in freight_values if value is not None]
        weights = [self._positive_float(fact.weight_kg) for fact in facts]
        weights = [value for value in weights if value is not None]
        volumes = [self._positive_float(fact.volume_m3) for fact in facts]
        volumes = [value for value in volumes if value is not None]
        transit_hours = [
            value for value in (self._transit_hours(fact) for fact in facts)
            if value is not None and value >= 0
        ]
        delay_minutes = [
            value for value in (self._delay_minutes(fact) for fact in facts)
            if value is not None
        ]
        eta_ready = [fact for fact in facts if fact.eta_at and self._actual_at(fact)]
        on_time = [
            fact for fact in eta_ready
            if self._actual_at(fact) and self._actual_at(fact) <= fact.eta_at
        ]

        total_freight = sum(freight_values)
        total_weight = sum(weights)
        total_volume = sum(volumes)
        total_shipments = len(facts)
        delivered_shipments = sum(1 for fact in facts if self._actual_at(fact))
        exception_shipments = sum(1 for fact in facts if self._clean_text(fact.exception_reason))

        return {
            "total_shipments": total_shipments,
            "freight_records": len(freight_values),
            "freight_coverage": self._ratio(len(freight_values), total_shipments),
            "total_freight": round(total_freight, 2),
            "avg_freight_per_shipment": self._round_or_none(total_freight / total_shipments if total_shipments else None, 2),
            "avg_freight_per_paid_shipment": self._round_or_none(statistics.mean(freight_values) if freight_values else None, 2),
            "total_weight_kg": round(total_weight, 2),
            "total_volume_m3": round(total_volume, 4),
            "freight_per_kg": self._round_or_none(total_freight / total_weight if total_weight > 0 else None, 4),
            "freight_per_m3": self._round_or_none(total_freight / total_volume if total_volume > 0 else None, 4),
            "delivered_shipments": delivered_shipments,
            "delivery_completion_rate": self._ratio(delivered_shipments, total_shipments),
            "eta_records": len(eta_ready),
            "on_time_shipments": len(on_time),
            "on_time_rate": self._ratio(len(on_time), len(eta_ready)),
            "avg_transit_hours": self._round_or_none(statistics.mean(transit_hours) if transit_hours else None, 3),
            "avg_delay_minutes": self._round_or_none(statistics.mean(delay_minutes) if delay_minutes else None, 3),
            "exception_shipments": exception_shipments,
            "exception_rate": self._ratio(exception_shipments, total_shipments),
        }

    def _cost_components(self, kpis: Dict[str, Any]) -> List[Dict[str, Any]]:
        total = float(kpis.get("total_freight") or 0.0)
        if total <= 0:
            return []
        # These are accounting heuristics over real freight totals, not invoice
        # components. They give the dashboard a stable cost decomposition while
        # keeping the truth contract explicit.
        components = [
            ("transport_base", total * 0.62),
            ("fuel_and_toll_estimate", total * 0.22),
            ("handling_service_estimate", total * 0.10),
            ("insurance_and_other", total * 0.06),
        ]
        return [
            {
                "component": name,
                "amount": round(amount, 2),
                "share": self._ratio(amount, total),
                "source": "freight_amount_allocation_heuristic",
            }
            for name, amount in components
        ]

    def _top_lanes(self, facts: Sequence[ShipmentFact], lane_limit: int) -> List[Dict[str, Any]]:
        lanes: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            "shipment_count": 0,
            "total_freight": 0.0,
            "total_weight_kg": 0.0,
            "transit_hours": [],
            "eta_records": 0,
            "on_time": 0,
        })
        for fact in facts:
            origin = self._clean_text(fact.origin_city_std) or "unknown_origin"
            destination = self._clean_text(fact.destination_city_std) or "unknown_destination"
            key = f"{origin}->{destination}"
            lane = lanes[key]
            lane["origin_city"] = origin
            lane["destination_city"] = destination
            lane["shipment_count"] += 1
            lane["total_freight"] += self._positive_float(fact.freight) or 0.0
            lane["total_weight_kg"] += self._positive_float(fact.weight_kg) or 0.0
            transit = self._transit_hours(fact)
            if transit is not None and transit >= 0:
                lane["transit_hours"].append(transit)
            actual_at = self._actual_at(fact)
            if fact.eta_at and actual_at:
                lane["eta_records"] += 1
                if actual_at <= fact.eta_at:
                    lane["on_time"] += 1

        rows = []
        total_freight = sum(float(lane["total_freight"]) for lane in lanes.values())
        for key, lane in lanes.items():
            freight = float(lane["total_freight"])
            weight = float(lane["total_weight_kg"])
            rows.append(
                {
                    "lane": key,
                    "origin_city": lane["origin_city"],
                    "destination_city": lane["destination_city"],
                    "shipment_count": lane["shipment_count"],
                    "total_freight": round(freight, 2),
                    "freight_share": self._ratio(freight, total_freight),
                    "avg_freight": self._round_or_none(freight / lane["shipment_count"] if lane["shipment_count"] else None, 2),
                    "freight_per_kg": self._round_or_none(freight / weight if weight > 0 else None, 4),
                    "avg_transit_hours": self._round_or_none(
                        statistics.mean(lane["transit_hours"]) if lane["transit_hours"] else None,
                        3,
                    ),
                    "on_time_rate": self._ratio(lane["on_time"], lane["eta_records"]),
                }
            )
        rows.sort(key=lambda item: (item["total_freight"], item["shipment_count"]), reverse=True)
        return rows[:lane_limit]

    def _city_breakdown(self, facts: Sequence[ShipmentFact], limit: int) -> List[Dict[str, Any]]:
        cities: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            "shipment_count": 0,
            "inbound_count": 0,
            "outbound_count": 0,
            "total_freight": 0.0,
            "total_weight_kg": 0.0,
        })
        for fact in facts:
            freight = self._positive_float(fact.freight) or 0.0
            weight = self._positive_float(fact.weight_kg) or 0.0
            origin = self._clean_text(fact.origin_city_std)
            destination = self._clean_text(fact.destination_city_std)
            for city, direction in ((origin, "outbound_count"), (destination, "inbound_count")):
                if not city:
                    continue
                row = cities[city]
                row["city"] = city
                row["shipment_count"] += 1
                row[direction] += 1
                row["total_freight"] += freight
                row["total_weight_kg"] += weight
        result = []
        for city, row in cities.items():
            freight = float(row["total_freight"])
            weight = float(row["total_weight_kg"])
            result.append(
                {
                    "city": city,
                    "shipment_count": row["shipment_count"],
                    "inbound_count": row["inbound_count"],
                    "outbound_count": row["outbound_count"],
                    "total_freight": round(freight, 2),
                    "freight_per_kg": self._round_or_none(freight / weight if weight > 0 else None, 4),
                }
            )
        result.sort(key=lambda item: (item["total_freight"], item["shipment_count"]), reverse=True)
        return result[:limit]

    def _trend(self, facts: Sequence[ShipmentFact], trend_days: int) -> List[Dict[str, Any]]:
        dated = [fact for fact in facts if fact.shipped_at]
        if not dated:
            return []
        end = max(fact.shipped_at.date() for fact in dated if fact.shipped_at)
        start = end - timedelta(days=trend_days - 1)
        grouped: Dict[date, Dict[str, float]] = defaultdict(lambda: {
            "shipment_count": 0.0,
            "total_freight": 0.0,
            "total_weight_kg": 0.0,
        })
        for fact in dated:
            day = fact.shipped_at.date()
            if day < start or day > end:
                continue
            row = grouped[day]
            row["shipment_count"] += 1
            row["total_freight"] += self._positive_float(fact.freight) or 0.0
            row["total_weight_kg"] += self._positive_float(fact.weight_kg) or 0.0

        result = []
        cursor = start
        while cursor <= end:
            row = grouped[cursor]
            freight = row["total_freight"]
            weight = row["total_weight_kg"]
            result.append(
                {
                    "date": cursor.isoformat(),
                    "shipment_count": int(row["shipment_count"]),
                    "total_freight": round(freight, 2),
                    "freight_per_kg": self._round_or_none(freight / weight if weight > 0 else None, 4),
                }
            )
            cursor += timedelta(days=1)
        return result

    def _recommendations(self, kpis: Dict[str, Any], top_lanes: Sequence[Dict[str, Any]]) -> List[str]:
        recommendations = []
        if (kpis.get("freight_coverage") or 0) < 0.8:
            recommendations.append("运费字段覆盖率偏低，成本分析应优先补齐 freight。")
        if kpis.get("on_time_rate") is not None and (kpis.get("on_time_rate") or 0) < 0.8:
            recommendations.append("准时率低于 80%，建议把高延误 OD 纳入调度风险评分。")
        if top_lanes and (top_lanes[0].get("freight_share") or 0) > 0.35:
            recommendations.append(f"{top_lanes[0].get('lane')} 成本占比过高，建议做线路合并、承运商议价或替代路径评估。")
        if kpis.get("freight_per_kg") is not None:
            recommendations.append("可将 freight_per_kg 与调度方案成本、路线 provider 距离联动，形成单位成本优化目标。")
        return recommendations or ["当前成本结构未发现明显异常，建议持续跟踪单位重量成本和准时率。"]

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

    def _cost_efficiency_score(
        self,
        kpis: Dict[str, Any],
        top_lanes: Sequence[Dict[str, Any]],
    ) -> float:
        freight_per_kg = kpis.get("freight_per_kg")
        if freight_per_kg is None:
            return 55.0
        lane_unit_costs = [
            float(lane.get("freight_per_kg"))
            for lane in top_lanes
            if lane.get("freight_per_kg") is not None
        ]
        if len(lane_unit_costs) < 2:
            return 85.0
        avg_lane_cost = statistics.mean(lane_unit_costs)
        if avg_lane_cost <= 0:
            return 75.0
        dispersion = statistics.pstdev(lane_unit_costs) / avg_lane_cost if len(lane_unit_costs) > 1 else 0.0
        return 100.0 - min(45.0, dispersion * 180.0)

    def _scorecard_recommendations(
        self,
        components: Sequence[Dict[str, Any]],
        gates: Sequence[Dict[str, Any]],
        base_recommendations: Sequence[str],
    ) -> List[str]:
        recommendations = list(base_recommendations[:3])
        if any(not gate.get("passed") for gate in gates):
            recommendations.append("存在未通过 operations gate，建议先补齐运费、ETA/签收时间和重量/体积字段。")
        for component in components:
            if float(component.get("score", 0.0)) >= 70.0:
                continue
            if component.get("id") == "service_quality":
                recommendations.append("服务质量分偏低，建议把低准时率 OD 线路纳入调度风险惩罚和客服预警。")
            elif component.get("id") == "exception_pressure":
                recommendations.append("异常压力分偏低，建议按异常原因聚合治理并回流到异常检测 scorecard。")
            elif component.get("id") == "lane_concentration":
                recommendations.append("线路成本集中度偏高，建议做承运商议价、替代线路和网络设计方案对比。")
            elif component.get("id") == "cost_efficiency":
                recommendations.append("成本效率分偏低，建议把单位重量/体积成本接入调度和路线 provider 对比。")
        recommendations.append("该 scorecard 只做经营分析验收，不替代财务结算、发票核算或调度控制器。")
        return list(dict.fromkeys(recommendations))

    def _empty_summary(self, limit: int, city: Optional[str]) -> Dict[str, Any]:
        return {
            "records_scanned": 0,
            "limit": limit,
            "city": city,
            "status_counts": {},
        }

    def _actual_at(self, fact: ShipmentFact) -> Optional[datetime]:
        return fact.delivered_at or fact.signed_at

    def _transit_hours(self, fact: ShipmentFact) -> Optional[float]:
        actual_at = self._actual_at(fact)
        if not fact.shipped_at or not actual_at:
            return None
        return (actual_at - fact.shipped_at).total_seconds() / 3600.0

    def _delay_minutes(self, fact: ShipmentFact) -> Optional[float]:
        actual_at = self._actual_at(fact)
        if not fact.eta_at or not actual_at:
            return None
        return (actual_at - fact.eta_at).total_seconds() / 60.0

    def _status(self, fact: ShipmentFact) -> str:
        return self._clean_text(fact.standard_status) or "unknown"

    def _truth_contract(self) -> Dict[str, Any]:
        return {
            "data_source": "shipment_fact",
            "revenue_cost_source": "shipment_facts.freight",
            "distance_source": "not_used_for_core_cost_kpis",
            "path_source": "not_route_geometry",
            "component_allocation": "freight_amount_allocation_heuristic",
            "business_mutation": "none",
            "fallback_reason": "set_when_shipment_facts_or_freight_are_missing",
            "authenticity_level": "B_for_real_freight_facts_C_when_missing",
        }

    def _ratio(self, numerator: float, denominator: float) -> Optional[float]:
        if not denominator:
            return None
        return round(float(numerator) / float(denominator), 6)

    def _round_or_none(self, value: Optional[float], digits: int) -> Optional[float]:
        if value is None or not math.isfinite(float(value)):
            return None
        return round(float(value), digits)

    def _positive_float(self, value: Any) -> Optional[float]:
        try:
            if value is None or value == "":
                return None
            number = float(value)
            return number if number > 0 else None
        except (TypeError, ValueError):
            return None

    def _coerce_int(self, value: Any, default: int) -> int:
        try:
            if value is None or value == "":
                return default
            return int(value)
        except (TypeError, ValueError):
            return default

    def _clean_text(self, value: Any) -> Optional[str]:
        text = str(value).strip() if value is not None else ""
        return text or None


_service: Optional[ShipmentCostAnalyticsService] = None


def get_shipment_cost_analytics_service() -> ShipmentCostAnalyticsService:
    global _service
    if _service is None:
        _service = ShipmentCostAnalyticsService()
    return _service
