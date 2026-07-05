"""Real shipment-fact prediction baselines for Phase 3 AI upgrade.

This module intentionally starts with explainable baselines over real
`shipment_facts` before introducing heavier ML/DL dependencies. The output
contract already carries the metrics and truth metadata needed by future
LightGBM/LSTM/RL layers.
"""

from __future__ import annotations

import hashlib
import math
import statistics
import threading
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple
from uuid import uuid4

import numpy as np
from sqlalchemy import func, or_

from app.models import ShipmentFact, Vehicle, db


DEFAULT_TASKS = ("demand", "eta", "delay", "cost")
MIN_EVALUATION_ROWS = 4
DEFAULT_LIMIT = 50000
MAX_FEATURE_ROWS = 1000
MIN_MODEL_ROWS = 8
DEFAULT_MODEL_HASH_BUCKETS = 24
MAX_MODEL_HASH_BUCKETS = 96
DEFAULT_MODEL_TEST_RATIO = 0.25


@dataclass
class PredictionRecord:
    id: Any
    target: float
    feature_key: str
    fallback_key: str
    payload: Dict[str, Any]


@dataclass
class PredictionSeries:
    task: str
    grain: str
    source_field: str
    rows: List[Tuple[Any, float]]
    status: str
    fallback_reason: Optional[str]
    summary: Dict[str, Any]


class ShipmentPredictionService:
    """Build real-data prediction datasets and baseline evaluation reports."""

    def __init__(self) -> None:
        self._trained_models: Dict[str, Dict[str, Any]] = {}
        self._jobs: Dict[str, Dict[str, Any]] = {}
        self._job_lock = threading.Lock()

    def dataset_health(self) -> Dict[str, Any]:
        total = ShipmentFact.query.count()
        demand_records = ShipmentFact.query.filter(ShipmentFact.shipped_at.isnot(None)).count()
        eta_records = self._actual_delivery_query().count()
        delay_records = self._actual_delivery_query().filter(ShipmentFact.eta_at.isnot(None)).count()
        cost_records = ShipmentFact.query.filter(ShipmentFact.freight.isnot(None), ShipmentFact.freight > 0).count()

        status_counts = self._status_counts()

        readiness = {
            "demand": self._readiness(demand_records, minimum=7),
            "eta": self._readiness(eta_records, minimum=MIN_EVALUATION_ROWS),
            "delay": self._readiness(delay_records, minimum=MIN_EVALUATION_ROWS),
            "cost": self._readiness(cost_records, minimum=MIN_EVALUATION_ROWS),
        }
        provider_status = "ok" if total > 0 else "degraded"
        fallback_reason = None if total > 0 else "SHIPMENT_FACTS_EMPTY"
        authenticity_level = "B" if total > 0 else "C"

        return {
            "success": True,
            "data_source": "shipment_fact",
            "provider_status": provider_status,
            "fallback_reason": fallback_reason,
            "authenticity_level": authenticity_level,
            "model_status": "baseline_ready" if any(item["ready"] for item in readiness.values()) else "insufficient_data",
            "summary": {
                "total_records": total,
                "demand_records": demand_records,
                "eta_records": eta_records,
                "delay_records": delay_records,
                "cost_records": cost_records,
                "status_counts": status_counts,
            },
            "readiness": readiness,
            "truth_contract": self._truth_contract(),
        }

    def timeline_audit(self, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Audit shipment time fields before selecting a forecasting grain."""
        payload = payload or {}
        city = self._clean_text(payload.get("city") or payload.get("destination_city"))
        sequence_length = max(1, min(168, self._coerce_int(payload.get("sequence_length"), 14)))
        fields = {
            "shipped_at": ShipmentFact.shipped_at,
            "eta_at": ShipmentFact.eta_at,
            "delivered_at": ShipmentFact.delivered_at,
            "signed_at": ShipmentFact.signed_at,
            "created_at": ShipmentFact.created_at,
        }

        field_summaries: Dict[str, Any] = {}
        for name, column in fields.items():
            field_summaries[name] = self._timeline_field_summary(column, name=name, city=city)

        shipped = field_summaries.get("shipped_at", {})
        recommended_grain = "daily"
        if shipped.get("distinct_dates", 0) < MIN_EVALUATION_ROWS and shipped.get("distinct_hours", 0) >= MIN_EVALUATION_ROWS:
            recommended_grain = "hourly"

        best_field = "shipped_at"
        if shipped.get("distinct_dates", 0) < MIN_EVALUATION_ROWS and shipped.get("distinct_hours", 0) < MIN_EVALUATION_ROWS:
            ranked = sorted(
                field_summaries.items(),
                key=lambda item: (item[1].get("distinct_dates", 0), item[1].get("distinct_hours", 0)),
                reverse=True,
            )
            best_field = ranked[0][0] if ranked else "shipped_at"
            recommended_grain = (
                "daily"
                if field_summaries.get(best_field, {}).get("distinct_dates", 0) >= MIN_EVALUATION_ROWS
                else "hourly"
            )

        recommended_summary = field_summaries.get(best_field, {})
        training_windows = max(
            0,
            int(
                recommended_summary.get(
                    "distinct_dates" if recommended_grain == "daily" else "distinct_hours",
                    0,
                )
            )
            - sequence_length,
        )
        provider_status = "ok" if recommended_summary.get("non_null_records", 0) else "degraded"
        fallback_reason = None
        if provider_status != "ok":
            fallback_reason = "NO_TIMELINE_FIELDS_AVAILABLE"
        elif shipped.get("distinct_dates", 0) < MIN_EVALUATION_ROWS:
            fallback_reason = "SHIPMENT_DAILY_POINTS_INSUFFICIENT"

        return {
            "success": True,
            "data_source": "shipment_fact",
            "provider_status": provider_status,
            "fallback_reason": fallback_reason,
            "authenticity_level": "B" if provider_status == "ok" else "C",
            "audit_version": "shipment_timeline_audit_v1",
            "city": city,
            "fields": field_summaries,
            "time_fields": field_summaries,
            "recommended": {
                "series_source": best_field,
                "time_granularity": recommended_grain,
                "training_windows": training_windows,
                "minimum_training_windows": 32,
                "deep_learning_ready": training_windows >= 32,
                "status": "ready_for_deep_shadow_training" if training_windows >= 32 else "needs_more_time_points",
            },
            "recommended_granularity": recommended_grain,
            "recommended_series_source": best_field,
            "training_window_count": training_windows,
            "truth_contract": {
                **self._truth_contract(),
                "timeline_audit": "real shipment_facts time columns only; no simulated dates are treated as real history",
            },
        }

    def evaluate_baselines(self, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        payload = payload or {}
        tasks = self._normalise_tasks(payload.get("tasks") or DEFAULT_TASKS)
        horizon_days = max(1, min(60, self._coerce_int(payload.get("horizon_days"), 7)))
        limit = max(1, min(DEFAULT_LIMIT, self._coerce_int(payload.get("limit"), DEFAULT_LIMIT)))
        city = self._clean_text(payload.get("city") or payload.get("destination_city"))
        time_granularity = self._normalise_granularity(payload.get("time_granularity"), default="auto")
        series_source = self._normalise_series_source(payload.get("series_source"), default="shipped_at")

        results: Dict[str, Any] = {}
        for task in tasks:
            if task == "demand":
                results[task] = self.evaluate_demand(
                    horizon_days=horizon_days,
                    city=city,
                    limit=limit,
                    time_granularity=time_granularity,
                    series_source=series_source,
                )
            elif task == "eta":
                results[task] = self.evaluate_eta(limit=limit)
            elif task == "delay":
                results[task] = self.evaluate_delay(limit=limit)
            elif task == "cost":
                results[task] = self.evaluate_cost(limit=limit)
            else:
                results[task] = self._unsupported_task(task)

        provider_status = "ok" if results and all(item.get("provider_status") == "ok" for item in results.values()) else "degraded"
        fallback_reasons = [
            item.get("fallback_reason")
            for item in results.values()
            if item.get("fallback_reason")
        ]
        return {
            "success": True,
            "data_source": "shipment_fact",
            "provider_status": provider_status,
            "fallback_reason": ";".join(fallback_reasons) if fallback_reasons else None,
            "authenticity_level": "B" if provider_status == "ok" else "C",
            "model_family": "explainable_baseline",
            "summary": {
                "tasks": tasks,
                "horizon_days": horizon_days,
                "limit": limit,
                "city": city,
                "ready_tasks": [task for task, item in results.items() if item.get("provider_status") == "ok"],
            },
            "results": results,
            "truth_contract": self._truth_contract(),
        }

    def forecast_demand(
        self,
        days: int = 7,
        city: Optional[str] = None,
        limit: int = DEFAULT_LIMIT,
        time_granularity: str = "auto",
        series_source: str = "shipped_at",
    ) -> Dict[str, Any]:
        return self.evaluate_demand(
            horizon_days=max(1, min(60, days)),
            city=self._clean_text(city),
            limit=max(1, min(DEFAULT_LIMIT, limit)),
            time_granularity=self._normalise_granularity(time_granularity, default="auto"),
            series_source=self._normalise_series_source(series_source, default="shipped_at"),
            forecast_only=True,
        )

    def evaluate_time_series_benchmark(self, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Compare real-data time-series baselines and report DL readiness.

        This is intentionally dependency-light. It establishes the time-indexed
        contract and backtest metrics needed before introducing LSTM/TFT
        training jobs.
        """
        payload = payload or {}
        task = str(payload.get("task") or "demand").strip().lower()
        horizon_days = max(1, min(60, self._coerce_int(payload.get("horizon_days"), 14)))
        test_days = max(1, min(60, self._coerce_int(payload.get("test_days"), horizon_days)))
        sequence_length = max(3, min(90, self._coerce_int(payload.get("sequence_length"), 14)))
        limit = max(1, min(DEFAULT_LIMIT, self._coerce_int(payload.get("limit"), DEFAULT_LIMIT)))
        city = self._clean_text(payload.get("city") or payload.get("destination_city"))

        series = self._daily_target_series(task=task, city=city, limit=limit)
        if series is None:
            return {
                "success": False,
                "task": task,
                "data_source": "shipment_fact",
                "provider_status": "degraded",
                "fallback_reason": "UNSUPPORTED_TIME_SERIES_TASK",
                "authenticity_level": "C",
                "metrics": self._empty_metrics(),
                "truth_contract": self._truth_contract(),
            }
        if len(series) < MIN_EVALUATION_ROWS:
            result = self._insufficient_result(task, len(series), f"{task.upper()}_TIME_SERIES_POINTS_INSUFFICIENT")
            result.update(
                {
                    "model_family": "time_series_baseline_benchmark",
                    "benchmark_version": "shipment_fact_time_series_benchmark_v1",
                    "series_summary": self._time_series_summary(series, task=task, city=city),
                    "deep_learning_readiness": self._deep_learning_readiness(
                        series,
                        sequence_length=sequence_length,
                    ),
                }
            )
            return result

        test_size = min(test_days, max(1, len(series) // 3))
        split_at = max(1, len(series) - test_size)
        model_ids = [
            "historical_mean",
            "weekday_mean",
            "moving_average_7",
            "seasonal_naive_7",
            "exponential_smoothing_alpha_0_35",
        ]
        model_results = [
            self._time_series_model_result(series, split_at, model_id)
            for model_id in model_ids
        ]
        model_results.sort(
            key=lambda item: (
                item.get("metrics", {}).get("mae") is None,
                item.get("metrics", {}).get("mae") if item.get("metrics", {}).get("mae") is not None else float("inf"),
            )
        )
        best_model = model_results[0] if model_results else None
        forecast = self._forecast_time_series(
            series,
            model_id=best_model.get("model_id") if best_model else "weekday_mean",
            horizon_days=horizon_days,
        )
        readiness = self._deep_learning_readiness(series, sequence_length=sequence_length)

        return {
            "success": True,
            "task": task,
            "prediction_target": self._target_definition(task).get("target_name", task),
            "data_source": "shipment_fact",
            "provider_status": "ok" if best_model else "degraded",
            "fallback_reason": None if best_model else "TIME_SERIES_MODEL_RESULTS_EMPTY",
            "authenticity_level": "B",
            "model_family": "time_series_baseline_benchmark",
            "benchmark_version": "shipment_fact_time_series_benchmark_v1",
            "series_summary": self._time_series_summary(series, task=task, city=city),
            "backtest": {
                "test_days": test_size,
                "train_points": split_at,
                "test_points": len(series) - split_at,
                "models": model_results,
                "best_model": best_model,
            },
            "forecast": forecast,
            "deep_learning_readiness": readiness,
            "truth_contract": {
                **self._truth_contract(),
                "model_boundary": "classical_time_series_benchmark_now_lstm_tft_readiness_only",
                "business_mutation": "none",
            },
        }

    def forecast_capacity_gap(self, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Forecast daily shipment demand against available vehicle capacity."""
        payload = payload or {}
        horizon_days = max(1, min(60, self._coerce_int(payload.get("horizon_days"), 14)))
        test_days = max(1, min(60, self._coerce_int(payload.get("test_days"), horizon_days)))
        sequence_length = max(3, min(90, self._coerce_int(payload.get("sequence_length"), 14)))
        limit = max(1, min(DEFAULT_LIMIT, self._coerce_int(payload.get("limit"), DEFAULT_LIMIT)))
        city = self._clean_text(payload.get("city") or payload.get("destination_city"))
        include_all_vehicles = bool(payload.get("include_all_vehicles", False))

        demand_series = self._daily_capacity_demand_series(city=city, limit=limit)
        fleet = self._fleet_capacity_summary(include_all_vehicles=include_all_vehicles)
        if not demand_series:
            return {
                "success": True,
                "data_source": "shipment_fact",
                "provider_status": "degraded",
                "fallback_reason": "CAPACITY_DEMAND_SERIES_EMPTY",
                "authenticity_level": "C",
                "model_family": "capacity_gap_forecast",
                "forecast_version": "shipment_capacity_gap_v1",
                "summary": {
                    "daily_points": 0,
                    "horizon_days": horizon_days,
                    "city": city,
                },
                "fleet_capacity": fleet,
                "forecast": [],
                "deep_learning_readiness": self._deep_learning_readiness([], sequence_length=sequence_length),
                "truth_contract": self._capacity_gap_truth_contract(),
            }

        weight_series = [(row["date"], row["weight_kg"]) for row in demand_series]
        volume_series = [(row["date"], row["volume_m3"]) for row in demand_series]
        shipment_series = [(row["date"], float(row["shipment_count"])) for row in demand_series]
        weight_model = self._best_time_series_model(weight_series, test_days=test_days)
        volume_model = self._best_time_series_model(volume_series, test_days=test_days)
        shipment_model = self._best_time_series_model(shipment_series, test_days=test_days)
        weight_forecast = self._forecast_time_series(weight_series, weight_model["model_id"], horizon_days)
        volume_forecast = self._forecast_time_series(volume_series, volume_model["model_id"], horizon_days)
        shipment_forecast = self._forecast_time_series(shipment_series, shipment_model["model_id"], horizon_days)

        rows = []
        for weight_row, volume_row, shipment_row in zip(weight_forecast, volume_forecast, shipment_forecast):
            predicted_weight = max(0.0, float(weight_row["predicted_value"]))
            predicted_volume = max(0.0, float(volume_row["predicted_value"]))
            predicted_shipments = max(0.0, float(shipment_row["predicted_value"]))
            weight_gap = max(0.0, predicted_weight - fleet["total_capacity_weight_kg"])
            volume_gap = max(0.0, predicted_volume - fleet["total_capacity_volume_m3"])
            rows.append(
                {
                    "date": weight_row["date"],
                    "predicted_shipments": round(predicted_shipments, 4),
                    "predicted_weight_kg": round(predicted_weight, 4),
                    "predicted_volume_m3": round(predicted_volume, 4),
                    "capacity_weight_kg": fleet["total_capacity_weight_kg"],
                    "capacity_volume_m3": fleet["total_capacity_volume_m3"],
                    "weight_gap_kg": round(weight_gap, 4),
                    "volume_gap_m3": round(volume_gap, 4),
                    "weight_utilization": self._ratio(predicted_weight, fleet["total_capacity_weight_kg"]),
                    "volume_utilization": self._ratio(predicted_volume, fleet["total_capacity_volume_m3"]),
                    "status": "shortage" if weight_gap > 0 or volume_gap > 0 else "covered",
                }
            )

        shortage_days = [row for row in rows if row["status"] == "shortage"]
        readiness = self._deep_learning_readiness(weight_series, sequence_length=sequence_length)
        provider_status = "ok" if fleet["available_vehicles"] > 0 and fleet["total_capacity_weight_kg"] > 0 else "degraded"
        fallback_reasons = []
        if provider_status != "ok":
            fallback_reasons.append("NO_AVAILABLE_VEHICLE_CAPACITY")
        if len(weight_series) < MIN_EVALUATION_ROWS:
            fallback_reasons.append("CAPACITY_HISTORY_POINTS_INSUFFICIENT")

        return {
            "success": True,
            "data_source": "shipment_fact",
            "provider_status": provider_status if not fallback_reasons else "degraded",
            "fallback_reason": ";".join(fallback_reasons) if fallback_reasons else None,
            "authenticity_level": "B" if not fallback_reasons else "C",
            "model_family": "capacity_gap_forecast",
            "forecast_version": "shipment_capacity_gap_v1",
            "summary": {
                "daily_points": len(demand_series),
                "horizon_days": horizon_days,
                "test_days": test_days,
                "city": city,
                "shortage_days": len(shortage_days),
                "max_weight_gap_kg": round(max((row["weight_gap_kg"] for row in rows), default=0.0), 4),
                "max_volume_gap_m3": round(max((row["volume_gap_m3"] for row in rows), default=0.0), 4),
                "avg_weight_utilization": self._round_or_none(
                    statistics.mean([row["weight_utilization"] for row in rows if row["weight_utilization"] is not None])
                    if rows and any(row["weight_utilization"] is not None for row in rows)
                    else None,
                    4,
                ),
            },
            "fleet_capacity": fleet,
            "models": {
                "weight": weight_model,
                "volume": volume_model,
                "shipments": shipment_model,
            },
            "forecast": rows,
            "deep_learning_readiness": readiness,
            "recommendations": self._capacity_gap_recommendations(rows, fleet),
            "truth_contract": self._capacity_gap_truth_contract(),
        }

    def forecast_cost_volatility(self, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Forecast shipment cost pressure and volatility from real freight history."""
        payload = payload or {}
        horizon_days = max(1, min(60, self._coerce_int(payload.get("horizon_days"), 14)))
        test_days = max(1, min(60, self._coerce_int(payload.get("test_days"), horizon_days)))
        sequence_length = max(3, min(90, self._coerce_int(payload.get("sequence_length"), 14)))
        volatility_window = max(3, min(30, self._coerce_int(payload.get("volatility_window"), 7)))
        limit = max(1, min(DEFAULT_LIMIT, self._coerce_int(payload.get("limit"), DEFAULT_LIMIT)))
        city = self._clean_text(payload.get("city") or payload.get("destination_city"))

        series_rows = self._daily_cost_volatility_series(city=city, limit=limit)
        if not series_rows:
            return {
                "success": True,
                "data_source": "shipment_fact",
                "provider_status": "degraded",
                "fallback_reason": "COST_VOLATILITY_SERIES_EMPTY",
                "authenticity_level": "C",
                "model_family": "cost_volatility_forecast",
                "forecast_version": "shipment_cost_volatility_v1",
                "summary": {
                    "daily_points": 0,
                    "horizon_days": horizon_days,
                    "city": city,
                },
                "forecast": [],
                "deep_learning_readiness": self._deep_learning_readiness([], sequence_length=sequence_length),
                "truth_contract": self._cost_volatility_truth_contract(),
            }

        avg_freight_series = [(row["date"], row["avg_freight"]) for row in series_rows]
        unit_kg_series = [(row["date"], row["unit_cost_per_kg"]) for row in series_rows]
        total_freight_series = [(row["date"], row["total_freight"]) for row in series_rows]

        avg_freight_model = self._best_time_series_model(avg_freight_series, test_days=test_days)
        unit_kg_model = self._best_time_series_model(unit_kg_series, test_days=test_days)
        total_freight_model = self._best_time_series_model(total_freight_series, test_days=test_days)

        avg_freight_forecast = self._forecast_time_series(avg_freight_series, avg_freight_model["model_id"], horizon_days)
        unit_kg_forecast = self._forecast_time_series(unit_kg_series, unit_kg_model["model_id"], horizon_days)
        total_freight_forecast = self._forecast_time_series(total_freight_series, total_freight_model["model_id"], horizon_days)

        historical_unit_costs = [row["unit_cost_per_kg"] for row in series_rows if row["unit_cost_per_kg"] > 0]
        recent_volatility = self._rolling_coefficient_of_variation(historical_unit_costs, volatility_window)
        historical_volatilities = [
            self._rolling_coefficient_of_variation(historical_unit_costs[:index], volatility_window)
            for index in range(volatility_window, len(historical_unit_costs) + 1)
        ]
        historical_volatilities = [value for value in historical_volatilities if value is not None]
        volatility_threshold = max(
            0.15,
            (statistics.mean(historical_volatilities) if historical_volatilities else 0.0)
            + (statistics.pstdev(historical_volatilities) if len(historical_volatilities) > 1 else 0.0),
        )
        unit_cost_threshold = self._percentile(historical_unit_costs, 0.75) or (
            statistics.mean(historical_unit_costs) if historical_unit_costs else 0.0
        )

        rows = []
        for avg_row, unit_row, total_row in zip(avg_freight_forecast, unit_kg_forecast, total_freight_forecast):
            predicted_avg_freight = max(0.0, float(avg_row["predicted_value"]))
            predicted_unit_cost = max(0.0, float(unit_row["predicted_value"]))
            predicted_total_freight = max(0.0, float(total_row["predicted_value"]))
            unit_pressure = self._ratio(predicted_unit_cost, unit_cost_threshold) if unit_cost_threshold else None
            volatility_pressure = self._ratio(recent_volatility or 0.0, volatility_threshold)
            risk_score = min(
                1.0,
                max(
                    0.0,
                    0.55 * (volatility_pressure or 0.0)
                    + 0.45 * max(0.0, (unit_pressure or 1.0) - 1.0),
                ),
            )
            risk_level = "high" if risk_score >= 0.75 else "medium" if risk_score >= 0.45 else "low"
            rows.append(
                {
                    "date": avg_row["date"],
                    "predicted_avg_freight": round(predicted_avg_freight, 4),
                    "predicted_unit_cost_per_kg": round(predicted_unit_cost, 6),
                    "predicted_total_freight": round(predicted_total_freight, 4),
                    "unit_cost_threshold": round(unit_cost_threshold, 6) if unit_cost_threshold else None,
                    "expected_volatility_cv": self._round_or_none(recent_volatility, 6),
                    "volatility_threshold": round(volatility_threshold, 6),
                    "unit_cost_pressure": unit_pressure,
                    "risk_score": round(risk_score, 6),
                    "risk_level": risk_level,
                    "method": {
                        "avg_freight": avg_row["method"],
                        "unit_cost": unit_row["method"],
                        "total_freight": total_row["method"],
                    },
                }
            )

        risk_days = [row for row in rows if row["risk_level"] in ("medium", "high")]
        high_risk_days = [row for row in rows if row["risk_level"] == "high"]
        readiness = self._deep_learning_readiness(unit_kg_series, sequence_length=sequence_length)
        fallback_reasons = []
        if len(unit_kg_series) < MIN_EVALUATION_ROWS:
            fallback_reasons.append("COST_VOLATILITY_HISTORY_POINTS_INSUFFICIENT")

        return {
            "success": True,
            "data_source": "shipment_fact",
            "provider_status": "ok" if not fallback_reasons else "degraded",
            "fallback_reason": ";".join(fallback_reasons) if fallback_reasons else None,
            "authenticity_level": "B" if not fallback_reasons else "C",
            "model_family": "cost_volatility_forecast",
            "forecast_version": "shipment_cost_volatility_v1",
            "summary": {
                "daily_points": len(series_rows),
                "horizon_days": horizon_days,
                "test_days": test_days,
                "city": city,
                "risk_days": len(risk_days),
                "high_risk_days": len(high_risk_days),
                "recent_volatility_cv": self._round_or_none(recent_volatility, 6),
                "volatility_threshold": round(volatility_threshold, 6),
                "unit_cost_threshold": round(unit_cost_threshold, 6) if unit_cost_threshold else None,
                "avg_unit_cost_per_kg": self._round_or_none(
                    statistics.mean(historical_unit_costs) if historical_unit_costs else None,
                    6,
                ),
            },
            "models": {
                "avg_freight": avg_freight_model,
                "unit_cost_per_kg": unit_kg_model,
                "total_freight": total_freight_model,
            },
            "forecast": rows,
            "deep_learning_readiness": readiness,
            "recommendations": self._cost_volatility_recommendations(rows),
            "truth_contract": self._cost_volatility_truth_contract(),
        }

    def prediction_scorecard(self, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Aggregate Phase 3 prediction readiness into one decision scorecard."""
        payload = payload or {}
        horizon_days = max(1, min(60, self._coerce_int(payload.get("horizon_days"), 14)))
        test_days = max(1, min(60, self._coerce_int(payload.get("test_days"), horizon_days)))
        sequence_length = max(3, min(90, self._coerce_int(payload.get("sequence_length"), 14)))
        limit = max(1, min(DEFAULT_LIMIT, self._coerce_int(payload.get("limit"), DEFAULT_LIMIT)))
        city = self._clean_text(payload.get("city") or payload.get("destination_city"))

        health = self.dataset_health()
        baseline = self.evaluate_baselines(
            {
                "tasks": list(DEFAULT_TASKS),
                "horizon_days": horizon_days,
                "limit": limit,
                "city": city,
            }
        )
        time_series = self.evaluate_time_series_benchmark(
            {
                "task": "demand",
                "horizon_days": horizon_days,
                "test_days": test_days,
                "sequence_length": sequence_length,
                "limit": limit,
                "city": city,
            }
        )
        capacity_gap = self.forecast_capacity_gap(
            {
                "horizon_days": horizon_days,
                "test_days": test_days,
                "sequence_length": sequence_length,
                "limit": limit,
                "city": city,
            }
        )
        cost_volatility = self.forecast_cost_volatility(
            {
                "horizon_days": horizon_days,
                "test_days": test_days,
                "sequence_length": sequence_length,
                "limit": limit,
                "city": city,
            }
        )

        readiness = health.get("readiness", {})
        ready_tasks = baseline.get("summary", {}).get("ready_tasks", [])
        baseline_results = baseline.get("results", {})
        baseline_metric_rows = [
            item.get("metrics", {})
            for item in baseline_results.values()
            if item.get("metrics", {}).get("sample_count", 0) > 0
        ]
        baseline_avg_mape = (
            statistics.mean([float(item.get("mape")) for item in baseline_metric_rows if item.get("mape") is not None])
            if any(item.get("mape") is not None for item in baseline_metric_rows)
            else None
        )
        time_series_backtest = time_series.get("backtest") if isinstance(time_series.get("backtest"), dict) else {}
        time_series_best_model = (
            time_series_backtest.get("best_model")
            if isinstance(time_series_backtest.get("best_model"), dict)
            else {}
        )
        time_series_ready = bool(time_series.get("deep_learning_readiness", {}).get("ready"))
        capacity_shortage_days = int(capacity_gap.get("summary", {}).get("shortage_days") or 0)
        cost_risk_days = int(cost_volatility.get("summary", {}).get("risk_days") or 0)
        cost_high_risk_days = int(cost_volatility.get("summary", {}).get("high_risk_days") or 0)

        components = [
            self._scorecard_component(
                "data_readiness",
                "Real Data Readiness",
                100.0 * sum(1 for item in readiness.values() if item.get("ready")) / max(len(DEFAULT_TASKS), 1),
                "ok" if health.get("provider_status") == "ok" else "degraded",
                {
                    "total_records": health.get("summary", {}).get("total_records", 0),
                    "ready_tasks": [task for task, item in readiness.items() if item.get("ready")],
                },
            ),
            self._scorecard_component(
                "baseline_coverage",
                "Baseline Metric Coverage",
                100.0 * len(ready_tasks) / max(len(DEFAULT_TASKS), 1),
                "ok" if len(ready_tasks) == len(DEFAULT_TASKS) else "degraded",
                {
                    "ready_tasks": ready_tasks,
                    "avg_mape": self._round_or_none(baseline_avg_mape, 4),
                },
            ),
            self._scorecard_component(
                "time_series_readiness",
                "Time-Series / DL Readiness",
                100.0 if time_series_ready else 65.0 if time_series.get("provider_status") == "ok" else 20.0,
                "ok" if time_series_ready else "shadow",
                {
                    "best_model": time_series_best_model.get("model_id"),
                    "training_windows": time_series.get("deep_learning_readiness", {}).get("training_windows"),
                    "minimum_training_windows": time_series.get("deep_learning_readiness", {}).get("minimum_training_windows"),
                },
            ),
            self._scorecard_component(
                "capacity_planning",
                "Capacity Gap Planning",
                100.0 - min(60.0, 100.0 * capacity_shortage_days / max(horizon_days, 1)),
                "ok" if capacity_gap.get("provider_status") == "ok" and capacity_shortage_days == 0 else "degraded",
                {
                    "shortage_days": capacity_shortage_days,
                    "available_vehicles": capacity_gap.get("fleet_capacity", {}).get("available_vehicles"),
                    "max_weight_gap_kg": capacity_gap.get("summary", {}).get("max_weight_gap_kg"),
                },
            ),
            self._scorecard_component(
                "cost_volatility",
                "Cost Volatility Planning",
                100.0
                - min(45.0, 100.0 * cost_risk_days / max(horizon_days, 1))
                - min(25.0, 100.0 * cost_high_risk_days / max(horizon_days, 1)),
                "ok" if cost_volatility.get("provider_status") == "ok" and cost_high_risk_days == 0 else "degraded",
                {
                    "risk_days": cost_risk_days,
                    "high_risk_days": cost_high_risk_days,
                    "recent_volatility_cv": cost_volatility.get("summary", {}).get("recent_volatility_cv"),
                },
            ),
        ]
        weights = {
            "data_readiness": 0.2,
            "baseline_coverage": 0.2,
            "time_series_readiness": 0.2,
            "capacity_planning": 0.2,
            "cost_volatility": 0.2,
        }
        readiness_score = round(
            sum(component["score"] * weights.get(component["id"], 0.0) for component in components),
            4,
        )
        gates = [
            {
                "id": "real_data_available",
                "passed": health.get("provider_status") == "ok",
                "detail": "shipment_facts must provide prediction records.",
            },
            {
                "id": "baseline_metrics_available",
                "passed": len(ready_tasks) == len(DEFAULT_TASKS),
                "detail": "demand/eta/delay/cost baselines should all have metrics.",
            },
            {
                "id": "shadow_boundary_preserved",
                "passed": all(
                    contract.get("business_mutation") == "none"
                    for contract in [
                        time_series.get("truth_contract", {}),
                        capacity_gap.get("truth_contract", {}),
                        cost_volatility.get("truth_contract", {}),
                    ]
                ),
                "detail": "prediction scorecard must not mutate business state.",
            },
            {
                "id": "deep_learning_shadow_ready",
                "passed": time_series_ready,
                "detail": "LSTM/TFT requires enough daily training windows before offline shadow training.",
            },
        ]

        return {
            "success": True,
            "data_source": "shipment_fact",
            "provider_status": "ok" if health.get("provider_status") == "ok" else "degraded",
            "fallback_reason": None if health.get("provider_status") == "ok" else health.get("fallback_reason"),
            "authenticity_level": "B" if health.get("provider_status") == "ok" else "C",
            "model_family": "prediction_readiness_scorecard",
            "scorecard_version": "shipment_prediction_scorecard_v1",
            "summary": {
                "readiness_score": readiness_score,
                "status": "ready" if readiness_score >= 85 else "watch" if readiness_score >= 65 else "needs_work",
                "horizon_days": horizon_days,
                "test_days": test_days,
                "city": city,
                "ready_tasks": ready_tasks,
                "risk_summary": {
                    "capacity_shortage_days": capacity_shortage_days,
                    "cost_risk_days": cost_risk_days,
                    "cost_high_risk_days": cost_high_risk_days,
                    "dl_shadow_ready": time_series_ready,
                },
            },
            "components": components,
            "gates": gates,
            "recommendations": self._scorecard_recommendations(components, gates),
            "evidence": {
                "dataset": {
                    "total_records": health.get("summary", {}).get("total_records", 0),
                    "readiness": readiness,
                },
                "baseline": {
                    "ready_tasks": ready_tasks,
                    "avg_mape": self._round_or_none(baseline_avg_mape, 4),
                },
                "time_series": {
                    "best_model": time_series_best_model.get("model_id"),
                    "training_windows": time_series.get("deep_learning_readiness", {}).get("training_windows"),
                    "deployment_boundary": time_series.get("deep_learning_readiness", {}).get("deployment_boundary"),
                },
                "capacity_gap": {
                    "shortage_days": capacity_shortage_days,
                    "fleet_capacity": capacity_gap.get("fleet_capacity", {}),
                },
                "cost_volatility": {
                    "risk_days": cost_risk_days,
                    "high_risk_days": cost_high_risk_days,
                    "recent_volatility_cv": cost_volatility.get("summary", {}).get("recent_volatility_cv"),
                },
            },
            "truth_contract": {
                **self._truth_contract(),
                "business_mutation": "none",
                "deployment_boundary": "scorecard_readiness_only_models_remain_shadow_until_validated",
                "scorecard_inputs": [
                    "dataset_health",
                    "baseline_evaluate",
                    "time_series_benchmark",
                    "capacity_gap_forecast",
                    "cost_volatility_forecast",
                ],
            },
        }

    def dataset_preview(self, task: str = "eta", limit: int = 10) -> Dict[str, Any]:
        task = str(task or "eta").strip().lower()
        limit = max(1, min(100, int(limit or 10)))
        if task == "demand":
            rows = self._daily_demand_series(limit=DEFAULT_LIMIT)
            preview = [
                {"date": item[0].isoformat(), "orders": item[1]}
                for item in rows[-limit:]
            ]
        elif task == "delay":
            preview = [record.payload for record in self._delay_records(DEFAULT_LIMIT)[:limit]]
        elif task == "cost":
            preview = [record.payload for record in self._cost_records(DEFAULT_LIMIT)[:limit]]
        else:
            preview = [record.payload for record in self._eta_records(DEFAULT_LIMIT)[:limit]]

        return {
            "success": True,
            "task": task,
            "data_source": "shipment_fact",
            "provider_status": "ok" if preview else "degraded",
            "fallback_reason": None if preview else f"{task.upper()}_DATASET_EMPTY",
            "authenticity_level": "B" if preview else "C",
            "records": preview,
            "total_previewed": len(preview),
            "truth_contract": self._truth_contract(),
        }

    def build_feature_dataset(self, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Return model-ready feature rows and schema for one prediction target."""
        payload = payload or {}
        task = str(payload.get("task") or "eta").strip().lower()
        limit = max(1, min(DEFAULT_LIMIT, self._coerce_int(payload.get("limit"), DEFAULT_LIMIT)))
        row_limit = max(1, min(MAX_FEATURE_ROWS, self._coerce_int(payload.get("row_limit"), 100)))
        city = self._clean_text(payload.get("city") or payload.get("destination_city"))

        all_rows = self._feature_rows_for_task(task=task, limit=limit, city=city)
        if all_rows is None:
            return {
                "success": False,
                "task": task,
                "data_source": "shipment_fact",
                "provider_status": "degraded",
                "fallback_reason": "UNSUPPORTED_PREDICTION_TASK",
                "authenticity_level": "C",
                "rows": [],
                "row_count": 0,
                "truth_contract": self._truth_contract(),
            }

        rows = all_rows[:row_limit]
        provider_status = "ok" if all_rows else "degraded"
        fallback_reason = None if all_rows else f"{task.upper()}_FEATURE_DATASET_EMPTY"
        return {
            "success": True,
            "task": task,
            "dataset_name": f"shipment_fact_{task}_features_v1",
            "data_source": "shipment_fact",
            "provider_status": provider_status,
            "fallback_reason": fallback_reason,
            "authenticity_level": "B" if provider_status == "ok" else "C",
            "target_definition": self._target_definition(task),
            "feature_schema": self._feature_schema(task),
            "row_count": len(all_rows),
            "returned_rows": len(rows),
            "truncated": len(all_rows) > len(rows),
            "rows": rows,
            "summary": self._feature_dataset_summary(all_rows),
            "truth_contract": self._truth_contract(),
        }

    def model_status(self) -> Dict[str, Any]:
        """Return readiness plus in-memory model registry status."""
        health = self.dataset_health()
        models = [
            self._model_public_summary(model)
            for model in sorted(
                self._trained_models.values(),
                key=lambda item: item.get("trained_at", ""),
                reverse=True,
            )
        ]
        latest_by_task: Dict[str, Any] = {}
        for model in models:
            latest_by_task.setdefault(model["task"], model)

        provider_status = "ok" if models else "degraded"
        return {
            "success": True,
            "data_source": "shipment_fact",
            "provider_status": provider_status,
            "fallback_reason": None if models else "NO_TRAINED_MODELS_IN_MEMORY",
            "authenticity_level": "B" if health.get("summary", {}).get("total_records", 0) > 0 else "C",
            "model_family": "lightweight_machine_learning",
            "model_stage": "phase3_training_api",
            "model_count": len(models),
            "models": models,
            "latest_by_task": latest_by_task,
            "job_count": len(self._jobs),
            "latest_jobs": self._latest_job_summaries(),
            "dataset_readiness": health.get("readiness", {}),
            "training_contract": self._training_contract(),
            "truth_contract": self._truth_contract(),
        }

    def create_prediction_job(self, payload: Optional[Dict[str, Any]] = None, app=None) -> Dict[str, Any]:
        """Create a background prediction training/shadow-evaluation job."""
        payload = dict(payload or {})
        task = str(payload.get("task") or "demand").strip().lower()
        model_family = str(payload.get("model_family") or "lstm").strip().lower()
        job_id = f"ai-pred-{uuid4().hex[:12]}"
        created_at = self._utc_now()
        job = {
            "job_id": job_id,
            "status": "queued",
            "task": task,
            "model_family": model_family,
            "runtime_profile": payload.get("runtime_profile", "full"),
            "provider_status": "queued",
            "fallback_reason": None,
            "created_at": created_at,
            "updated_at": created_at,
            "progress": 0.0,
            "request": self._safe_job_request(payload),
            "truth_contract": {
                **self._training_contract(),
                "job_boundary": "background shadow job; no shipment_facts mutation",
            },
        }
        with self._job_lock:
            self._jobs[job_id] = job

        thread = threading.Thread(
            target=self._run_prediction_job,
            args=(job_id, payload, app),
            name=f"prediction-job-{job_id}",
            daemon=True,
        )
        thread.start()
        return {
            "success": True,
            "data_source": "shipment_fact",
            "provider_status": "accepted",
            "fallback_reason": None,
            "authenticity_level": "B",
            "job_id": job_id,
            "status": job["status"],
            "task": task,
            "model_family": model_family,
            "runtime_profile": job["runtime_profile"],
            "job": self._job_public_summary(job),
            "poll_url": f"/api/ai-prediction/jobs/{job_id}",
            "training_contract": self._training_contract(),
            "truth_contract": self._truth_contract(),
        }

    def prediction_job_status(self, job_id: str) -> Dict[str, Any]:
        with self._job_lock:
            job = dict(self._jobs.get(job_id) or {})
        if not job:
            return {
                "success": False,
                "provider_status": "degraded",
                "fallback_reason": "PREDICTION_JOB_NOT_FOUND",
                "job_id": job_id,
            }
        return {
            "success": True,
            "data_source": "shipment_fact",
            "provider_status": job.get("provider_status", "unknown"),
            "fallback_reason": job.get("fallback_reason"),
            "authenticity_level": "B" if job.get("provider_status") == "ok" else "C",
            "job_id": job.get("job_id"),
            "status": job.get("status"),
            "task": job.get("task"),
            "model_family": job.get("model_family"),
            "progress": job.get("progress", 0.0),
            "job": job,
            "truth_contract": self._truth_contract(),
        }

    def train_model(self, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Train a dependency-light model over real shipment_facts feature rows."""
        payload = payload or {}
        task = str(payload.get("task") or "eta").strip().lower()
        limit = max(1, min(DEFAULT_LIMIT, self._coerce_int(payload.get("limit"), DEFAULT_LIMIT)))
        city = self._clean_text(payload.get("city") or payload.get("destination_city"))
        test_ratio = self._bounded_float(payload.get("test_ratio"), DEFAULT_MODEL_TEST_RATIO, 0.1, 0.4)
        alpha = self._bounded_float(payload.get("alpha"), 1.0, 0.0001, 1000.0)
        hash_buckets = max(
            4,
            min(
                MAX_MODEL_HASH_BUCKETS,
                self._coerce_int(payload.get("hash_buckets"), DEFAULT_MODEL_HASH_BUCKETS),
            ),
        )

        rows = self._feature_rows_for_task(task=task, limit=limit, city=city)
        if rows is None:
            return self._unsupported_model_task(task)
        if len(rows) < MIN_MODEL_ROWS:
            return self._insufficient_model_result(task, len(rows), "MODEL_TRAINING_ROWS_INSUFFICIENT")

        split_at = max(1, min(len(rows) - 1, int(round(len(rows) * (1.0 - test_ratio)))))
        train_rows = rows[:split_at]
        test_rows = rows[split_at:]
        x_train, y_train, model_state = self._linear_dataset(
            train_rows,
            task=task,
            hash_buckets=hash_buckets,
        )
        x_test, y_test, _ = self._linear_dataset(test_rows, task=task, state=model_state)

        coefficients = self._fit_ridge_regression(x_train, y_train, alpha=alpha)
        predicted = self._predict_with_coefficients(x_test, coefficients)
        metrics = self._metrics(actual=y_test.tolist(), predicted=predicted.tolist())
        trained_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        model_id = f"{task}-{trained_at.replace(':', '').replace('-', '').replace('Z', '')}"
        model = {
            "model_id": model_id,
            "task": task,
            "model_type": "ridge_feature_hashing_regressor_v1",
            "model_family": "lightweight_machine_learning",
            "model_stage": "phase3_training_api",
            "trained_at": trained_at,
            "data_source": "shipment_fact",
            "provider_status": "ok",
            "fallback_reason": None,
            "authenticity_level": "B",
            "target_definition": self._target_definition(task),
            "feature_schema": self._feature_schema(task),
            "training_summary": {
                "row_count": len(rows),
                "training_rows": len(train_rows),
                "test_rows": len(test_rows),
                "test_ratio": round(test_ratio, 4),
                "limit": limit,
                "city": city,
                "alpha": alpha,
                "hash_buckets": hash_buckets,
                "feature_count": int(x_train.shape[1]),
            },
            "metrics": metrics,
            "state": model_state,
            "coefficients": coefficients.tolist(),
        }
        model["feature_importance"] = self._linear_feature_importance(model)
        self._trained_models[model_id] = model

        return {
            "success": True,
            "data_source": "shipment_fact",
            "provider_status": "ok",
            "fallback_reason": None,
            "authenticity_level": "B",
            "model": self._model_public_summary(model),
            "training_contract": self._training_contract(),
            "truth_contract": self._truth_contract(),
        }

    def evaluate_model(self, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Evaluate a cached trained model on current real feature rows."""
        payload = payload or {}
        task = str(payload.get("task") or "").strip().lower() or None
        model_id = self._clean_text(payload.get("model_id"))
        model = self._select_model(task=task, model_id=model_id)
        if model is None:
            return self._no_model_result(task=task, model_id=model_id)

        limit = max(1, min(DEFAULT_LIMIT, self._coerce_int(payload.get("limit"), DEFAULT_LIMIT)))
        city = self._clean_text(payload.get("city") or payload.get("destination_city"))
        rows = self._feature_rows_for_task(task=model["task"], limit=limit, city=city)
        if rows is None:
            return self._unsupported_model_task(model["task"])
        if len(rows) < MIN_EVALUATION_ROWS:
            return self._insufficient_model_result(model["task"], len(rows), "MODEL_EVALUATION_ROWS_INSUFFICIENT")

        row_limit = max(1, min(100, self._coerce_int(payload.get("row_limit"), 20)))
        x_eval, y_eval, _ = self._linear_dataset(rows, task=model["task"], state=model["state"])
        predicted = self._predict_with_coefficients(x_eval, np.asarray(model["coefficients"], dtype=float))
        metrics = self._metrics(actual=y_eval.tolist(), predicted=predicted.tolist())

        return {
            "success": True,
            "data_source": "shipment_fact",
            "provider_status": "ok",
            "fallback_reason": None,
            "authenticity_level": "B",
            "model": self._model_public_summary(model),
            "evaluation": {
                "row_count": len(rows),
                "returned_rows": min(row_limit, len(rows)),
                "metrics": metrics,
                "prediction_rows": self._prediction_rows(rows, y_eval, predicted, row_limit),
            },
            "truth_contract": self._truth_contract(),
        }

    def predict_with_model(self, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Return latest model predictions for feature rows without mutating business data."""
        payload = payload or {}
        task = str(payload.get("task") or "").strip().lower() or None
        model_id = self._clean_text(payload.get("model_id"))
        model = self._select_model(task=task, model_id=model_id)
        if model is None:
            return self._no_model_result(task=task, model_id=model_id)

        limit = max(1, min(DEFAULT_LIMIT, self._coerce_int(payload.get("limit"), DEFAULT_LIMIT)))
        row_limit = max(1, min(100, self._coerce_int(payload.get("row_limit"), 20)))
        city = self._clean_text(payload.get("city") or payload.get("destination_city"))
        rows = self._feature_rows_for_task(task=model["task"], limit=limit, city=city)
        if rows is None:
            return self._unsupported_model_task(model["task"])
        if not rows:
            return self._insufficient_model_result(model["task"], 0, "MODEL_PREDICTION_ROWS_EMPTY")

        x_pred, y_true, _ = self._linear_dataset(rows, task=model["task"], state=model["state"])
        predicted = self._predict_with_coefficients(x_pred, np.asarray(model["coefficients"], dtype=float))
        return {
            "success": True,
            "data_source": "shipment_fact",
            "provider_status": "ok",
            "fallback_reason": None,
            "authenticity_level": "B",
            "model": self._model_public_summary(model),
            "prediction": {
                "row_count": len(rows),
                "returned_rows": min(row_limit, len(rows)),
                "rows": self._prediction_rows(rows, y_true, predicted, row_limit),
                "mutation": "none",
            },
            "truth_contract": self._truth_contract(),
        }

    def evaluate_demand(
        self,
        horizon_days: int = 7,
        city: Optional[str] = None,
        limit: int = DEFAULT_LIMIT,
        time_granularity: str = "daily",
        series_source: str = "shipped_at",
        forecast_only: bool = False,
    ) -> Dict[str, Any]:
        series_info = self._demand_prediction_series(
            city=city,
            limit=limit,
            time_granularity=time_granularity,
            series_source=series_source,
        )
        series = series_info.rows
        if len(series) < MIN_EVALUATION_ROWS:
            result = self._insufficient_result(
                "demand",
                len(series),
                series_info.fallback_reason or "DEMAND_TIME_BUCKETS_INSUFFICIENT",
            )
            result.update(
                {
                    "prediction_target": "order_count_by_time_bucket",
                    "model": "time_bucket_mean_baseline",
                    "model_family": "time_series_baseline",
                    "forecast_status": "insufficient_history",
                    "time_granularity": series_info.grain,
                    "series_source": series_info.source_field,
                    "series_summary": series_info.summary,
                    "truth_contract": {
                        **self._truth_contract(),
                        "demand_series": "time-bucketed real shipment_facts without treating missing history as zero forecast",
                    },
                }
            )
            return result

        horizon_buckets = self._forecast_horizon_buckets(horizon_days, series_info.grain)
        test_size = min(horizon_buckets, max(1, len(series) // 3))
        train = series[:-test_size] if not forecast_only else series
        test = series[-test_size:] if not forecast_only else []
        if len(train) < 1:
            result = self._insufficient_result("demand", len(series), "DEMAND_TRAINING_POINTS_INSUFFICIENT")
            result.update(
                {
                    "forecast_status": "insufficient_training_history",
                    "time_granularity": series_info.grain,
                    "series_source": series_info.source_field,
                    "series_summary": series_info.summary,
                }
            )
            return result

        predictions = [
            self._time_bucket_mean_predict(train, item[0], series_info.grain)
            for item in test
        ]
        metrics = self._metrics(
            actual=[float(item[1]) for item in test],
            predicted=predictions,
        ) if test else self._empty_metrics()

        forecast = self._forecast_bucket_demand(train, horizon_buckets, series_info.grain)
        return {
            "success": True,
            "task": "demand",
            "prediction_target": "daily_order_count" if series_info.grain == "daily" else "hourly_order_count",
            "model": "weekday_mean_baseline" if series_info.grain == "daily" else "hour_weekday_mean_baseline",
            "model_family": "time_series_baseline",
            "model_stage": "phase3_baseline",
            "data_source": "shipment_fact",
            "provider_status": "ok" if series_info.status == "ok" else "degraded",
            "fallback_reason": series_info.fallback_reason,
            "authenticity_level": "B" if series_info.status == "ok" else "C",
            "forecast_status": "ok" if series_info.status == "ok" else "degraded",
            "time_granularity": series_info.grain,
            "series_source": series_info.source_field,
            "series_summary": series_info.summary,
            "metrics": metrics,
            "feature_summary": {
                "daily_points": series_info.summary.get("distinct_dates"),
                "time_bucket_points": len(series),
                "training_points": len(train),
                "test_points": len(test),
                "city": city,
                "limit": limit,
                "date_range": {
                    "start": series[0][0].isoformat(),
                    "end": series[-1][0].isoformat(),
                },
            },
            "forecast": forecast,
            "backtest": [
                {
                    "date": item[0].isoformat(),
                    "actual_orders": int(item[1]),
                    "predicted_orders": round(float(pred), 4),
                }
                for item, pred in zip(test, predictions)
            ],
            "truth_contract": {
                **self._truth_contract(),
                "demand_series": "time-bucketed real shipment_facts; empty history is degraded rather than rendered as zero demand",
            },
        }

    def evaluate_eta(self, limit: int = DEFAULT_LIMIT) -> Dict[str, Any]:
        return self._evaluate_record_baseline(
            task="eta",
            prediction_target="actual_transit_hours",
            model="od_mode_median_eta_baseline",
            records=self._eta_records(limit),
        )

    def evaluate_delay(self, limit: int = DEFAULT_LIMIT) -> Dict[str, Any]:
        records = self._delay_records(limit)
        result = self._evaluate_record_baseline(
            task="delay",
            prediction_target="arrival_delay_minutes",
            model="od_mode_median_delay_baseline",
            records=records,
        )
        if result.get("provider_status") == "ok":
            actual_delayed = sum(1 for item in result["backtest"] if item["actual"] > 15)
            predicted_delayed = sum(1 for item in result["backtest"] if item["predicted"] > 15)
            total = max(1, len(result["backtest"]))
            result["classification_summary"] = {
                "delay_threshold_minutes": 15,
                "actual_delay_rate": round(actual_delayed / total, 4),
                "predicted_delay_rate": round(predicted_delayed / total, 4),
            }
        return result

    def evaluate_cost(self, limit: int = DEFAULT_LIMIT) -> Dict[str, Any]:
        return self._evaluate_record_baseline(
            task="cost",
            prediction_target="freight_amount",
            model="od_mode_weight_unit_cost_baseline",
            records=self._cost_records(limit),
            prediction_fn=self._predict_cost,
        )

    def _evaluate_record_baseline(
        self,
        task: str,
        prediction_target: str,
        model: str,
        records: Sequence[PredictionRecord],
        prediction_fn=None,
    ) -> Dict[str, Any]:
        if len(records) < MIN_EVALUATION_ROWS:
            return self._insufficient_result(task, len(records), f"{task.upper()}_ROWS_INSUFFICIENT")

        test_size = min(max(1, len(records) // 4), max(1, len(records) - 1))
        train = list(records[:-test_size])
        test = list(records[-test_size:])
        if not train:
            return self._insufficient_result(task, len(records), f"{task.upper()}_TRAINING_ROWS_INSUFFICIENT")

        predicted = [
            prediction_fn(train, item) if prediction_fn else self._predict_group_median(train, item)
            for item in test
        ]
        actual = [float(item.target) for item in test]
        metrics = self._metrics(actual=actual, predicted=predicted)
        return {
            "success": True,
            "task": task,
            "prediction_target": prediction_target,
            "model": model,
            "model_stage": "phase3_baseline",
            "data_source": "shipment_fact",
            "provider_status": "ok",
            "fallback_reason": None,
            "authenticity_level": "B",
            "metrics": metrics,
            "feature_summary": {
                "records": len(records),
                "training_rows": len(train),
                "test_rows": len(test),
                "feature_keys": len({item.feature_key for item in records}),
                "fallback_keys": len({item.fallback_key for item in records}),
            },
            "backtest": [
                {
                    "id": item.id,
                    "actual": round(float(item.target), 4),
                    "predicted": round(float(pred), 4),
                    "absolute_error": round(abs(float(item.target) - float(pred)), 4),
                    **item.payload,
                }
                for item, pred in zip(test[:20], predicted[:20])
            ],
        }

    def _eta_records(self, limit: int) -> List[PredictionRecord]:
        query = (
            self._actual_delivery_query()
            .with_entities(*self._fact_projection_columns())
            .order_by(ShipmentFact.shipped_at.asc(), ShipmentFact.id.asc())
            .limit(limit)
        )
        records = []
        for fact in self._iter_query(query):
            actual_at = self._actual_at(fact)
            if not fact.shipped_at or not actual_at:
                continue
            hours = (actual_at - fact.shipped_at).total_seconds() / 3600.0
            if hours <= 0:
                continue
            records.append(self._record_from_fact(fact, hours, "actual_transit_hours"))
        return records

    def _delay_records(self, limit: int) -> List[PredictionRecord]:
        query = (
            self._actual_delivery_query()
            .filter(ShipmentFact.eta_at.isnot(None))
            .with_entities(*self._fact_projection_columns())
            .order_by(ShipmentFact.shipped_at.asc(), ShipmentFact.id.asc())
            .limit(limit)
        )
        records = []
        for fact in self._iter_query(query):
            actual_at = self._actual_at(fact)
            if not fact.eta_at or not actual_at:
                continue
            delay_minutes = (actual_at - fact.eta_at).total_seconds() / 60.0
            records.append(self._record_from_fact(fact, delay_minutes, "arrival_delay_minutes"))
        return records

    def _cost_records(self, limit: int) -> List[PredictionRecord]:
        query = (
            ShipmentFact.query.filter(ShipmentFact.freight.isnot(None), ShipmentFact.freight > 0)
            .with_entities(*self._fact_projection_columns())
            .order_by(ShipmentFact.id.asc())
            .limit(limit)
        )
        return [
            self._record_from_fact(fact, float(fact.freight or 0.0), "freight_amount")
            for fact in self._iter_query(query)
            if self._coerce_float(fact.freight, 0.0) > 0
        ]

    def _demand_prediction_series(
        self,
        city: Optional[str],
        limit: int,
        time_granularity: str,
        series_source: str,
    ) -> PredictionSeries:
        source_candidates = self._series_source_candidates(series_source)
        grain_candidates = self._granularity_candidates(time_granularity)
        attempts: List[PredictionSeries] = []

        for source in source_candidates:
            for grain in grain_candidates:
                sparse = self._bucketed_demand_series(city=city, source_field=source, grain=grain)
                complete = self._complete_bucket_series(sparse, grain)
                status = "ok" if len(complete) >= MIN_EVALUATION_ROWS else "degraded"
                reason = None if status == "ok" else f"DEMAND_{grain.upper()}_POINTS_INSUFFICIENT"
                if (
                    status == "ok"
                    and time_granularity == "auto"
                    and grain == "hourly"
                    and any(
                        attempt.source_field == source
                        and attempt.grain == "daily"
                        and len(attempt.rows) < MIN_EVALUATION_ROWS
                        for attempt in attempts
                    )
                ):
                    status = "degraded"
                    reason = "DEMAND_DAILY_POINTS_INSUFFICIENT_USING_HOURLY_FALLBACK"
                if source != "shipped_at":
                    reason = "BUSINESS_SHIPPED_AT_INSUFFICIENT_USING_AUXILIARY_TIME_FIELD" if status == "ok" else reason
                    status = "degraded"
                series = PredictionSeries(
                    task="demand",
                    grain=grain,
                    source_field=source,
                    rows=[(bucket, float(count)) for bucket, count in complete],
                    status=status,
                    fallback_reason=reason,
                    summary=self._time_bucket_series_summary(
                        sparse=sparse,
                        complete=complete,
                        city=city,
                        source_field=source,
                        grain=grain,
                        limit=limit,
                    ),
                )
                attempts.append(series)
                if len(complete) >= MIN_EVALUATION_ROWS and (source == "shipped_at" or series_source == "auto"):
                    return series

        if not attempts:
            return PredictionSeries(
                task="demand",
                grain="daily",
                source_field="shipped_at",
                rows=[],
                status="degraded",
                fallback_reason="DEMAND_TIME_BUCKETS_EMPTY",
                summary={},
            )
        return max(attempts, key=lambda item: len(item.rows))

    def _daily_demand_series(
        self,
        city: Optional[str] = None,
        limit: int = DEFAULT_LIMIT,
    ) -> List[Tuple[date, int]]:
        query = ShipmentFact.query.filter(ShipmentFact.shipped_at.isnot(None))
        if city:
            query = query.filter(
                or_(
                    ShipmentFact.destination_city_std == city,
                    ShipmentFact.origin_city_std == city,
                )
            )
        rows = (
            query.with_entities(ShipmentFact.shipped_at)
            .order_by(ShipmentFact.shipped_at.asc(), ShipmentFact.id.asc())
            .limit(limit)
        )
        counts: Counter[date] = Counter()
        for row in self._iter_query(rows):
            shipped_at = row[0]
            if shipped_at:
                counts[shipped_at.date()] += 1
        return sorted(counts.items(), key=lambda item: item[0])

    def _bucketed_demand_series(
        self,
        city: Optional[str],
        source_field: str,
        grain: str,
    ) -> List[Tuple[Any, int]]:
        column = self._series_field_column(source_field)
        if column is None:
            return []

        query = ShipmentFact.query.filter(column.isnot(None))
        if city:
            query = query.filter(
                or_(
                    ShipmentFact.destination_city_std == city,
                    ShipmentFact.origin_city_std == city,
                )
            )
        bucket_expr = self._time_bucket_expr(column, grain)
        rows_query = (
            query.with_entities(bucket_expr.label("bucket"), func.count(ShipmentFact.id))
            .group_by(bucket_expr)
            .order_by(bucket_expr.asc())
        )
        rows: List[Tuple[Any, int]] = []
        for bucket, count in self._iter_query(rows_query):
            parsed = self._parse_time_bucket(bucket, grain)
            if parsed is not None:
                rows.append((parsed, int(count or 0)))
        return sorted(rows, key=lambda item: item[0])

    def _demand_feature_rows(self, city: Optional[str], limit: int) -> List[Dict[str, Any]]:
        series = self._daily_demand_series(city=city, limit=limit)
        rows = []
        rolling_values: List[int] = []
        for target_day, orders in series:
            trailing_7 = statistics.mean(rolling_values[-7:]) if rolling_values else float(orders)
            trailing_28 = statistics.mean(rolling_values[-28:]) if rolling_values else float(orders)
            rows.append(
                {
                    "date": target_day.isoformat(),
                    "city_scope": city or "all",
                    "weekday": target_day.weekday(),
                    "is_weekend": target_day.weekday() >= 5,
                    "month": target_day.month,
                    "day_of_month": target_day.day,
                    "trailing_7d_avg_orders": round(float(trailing_7), 4),
                    "trailing_28d_avg_orders": round(float(trailing_28), 4),
                    "target": int(orders),
                    "target_name": "daily_order_count",
                }
            )
            rolling_values.append(int(orders))
        return rows

    def _feature_row_from_record(self, record: PredictionRecord) -> Dict[str, Any]:
        payload = dict(record.payload)
        return {
            "id": record.id,
            "origin_city": payload.get("origin_city"),
            "destination_city": payload.get("destination_city"),
            "transport_mode": payload.get("transport_mode"),
            "cargo_type": payload.get("cargo_type"),
            "weight_kg": payload.get("weight_kg"),
            "volume_m3": payload.get("volume_m3"),
            "freight": payload.get("freight"),
            "distance_km": payload.get("distance_km"),
            "shipped_weekday": payload.get("shipped_weekday"),
            "shipped_hour": payload.get("shipped_hour"),
            "feature_key": record.feature_key,
            "fallback_key": record.fallback_key,
            "target": round(float(record.target), 6),
            "target_name": payload.get("target_name"),
            "shipment_id": payload.get("shipment_id"),
            "order_id": payload.get("order_id"),
        }

    def _forecast_daily_demand(self, train: Sequence[Tuple[date, int]], days: int) -> List[Dict[str, Any]]:
        last_day = train[-1][0]
        residuals = []
        for idx, item in enumerate(train):
            history = train[:idx]
            if history:
                residuals.append(float(item[1]) - self._weekday_mean_predict(history, item[0]))
        spread = statistics.pstdev(residuals) if len(residuals) > 1 else max(1.0, statistics.mean([x[1] for x in train]) * 0.15)

        forecast = []
        for offset in range(1, days + 1):
            target_day = last_day + timedelta(days=offset)
            predicted = max(0.0, self._weekday_mean_predict(train, target_day))
            forecast.append(
                {
                    "date": target_day.isoformat(),
                    "predicted_orders": round(predicted, 4),
                    "lower_bound": round(max(0.0, predicted - 1.64 * spread), 4),
                    "upper_bound": round(predicted + 1.64 * spread, 4),
                    "method": "weekday_mean_baseline",
                }
            )
        return forecast

    def _forecast_bucket_demand(self, train: Sequence[Tuple[Any, float]], buckets: int, grain: str) -> List[Dict[str, Any]]:
        last_bucket = train[-1][0]
        residuals = []
        for idx, item in enumerate(train):
            history = train[:idx]
            if history:
                residuals.append(float(item[1]) - self._time_bucket_mean_predict(history, item[0], grain))
        mean_value = statistics.mean([float(x[1]) for x in train]) if train else 0.0
        spread = statistics.pstdev(residuals) if len(residuals) > 1 else max(1.0, mean_value * 0.15)

        forecast = []
        step = self._bucket_step(grain)
        for offset in range(1, buckets + 1):
            target_bucket = last_bucket + (step * offset)
            predicted = max(0.0, self._time_bucket_mean_predict(train, target_bucket, grain))
            forecast.append(
                {
                    "date": target_bucket.isoformat(),
                    "bucket_start": target_bucket.isoformat(),
                    "time_granularity": grain,
                    "predicted_orders": round(predicted, 4),
                    "lower_bound": round(max(0.0, predicted - 1.64 * spread), 4),
                    "upper_bound": round(predicted + 1.64 * spread, 4),
                    "method": "weekday_mean_baseline" if grain == "daily" else "hour_weekday_mean_baseline",
                }
            )
        return forecast

    def _daily_target_series(
        self,
        task: str,
        city: Optional[str],
        limit: int,
    ) -> Optional[List[Tuple[date, float]]]:
        if task == "demand":
            return [
                (day, float(count))
                for day, count in self._complete_demand_series(city=city, limit=limit)
            ]
        if task == "eta":
            records = self._daily_numeric_records(task="eta", city=city, limit=limit)
        elif task == "delay":
            records = self._daily_numeric_records(task="delay", city=city, limit=limit)
        elif task == "cost":
            records = self._daily_numeric_records(task="cost", city=city, limit=limit)
        else:
            return None

        grouped: Dict[date, List[float]] = defaultdict(list)
        for target_day, value in records:
            grouped[target_day].append(float(value))
        return [
            (target_day, float(statistics.mean(values)))
            for target_day, values in sorted(grouped.items(), key=lambda item: item[0])
            if values
        ]

    def _complete_demand_series(
        self,
        city: Optional[str],
        limit: int,
    ) -> List[Tuple[date, int]]:
        sparse = self._daily_demand_series(city=city, limit=limit)
        if not sparse:
            return []
        counts = dict(sparse)
        cursor = sparse[0][0]
        end = sparse[-1][0]
        result = []
        while cursor <= end:
            result.append((cursor, int(counts.get(cursor, 0))))
            cursor += timedelta(days=1)
        return result

    def _complete_bucket_series(self, sparse: Sequence[Tuple[Any, int]], grain: str) -> List[Tuple[Any, int]]:
        if not sparse:
            return []
        counts = {bucket: int(count or 0) for bucket, count in sparse}
        cursor = sparse[0][0]
        end = sparse[-1][0]
        step = self._bucket_step(grain)
        result: List[Tuple[Any, int]] = []
        while cursor <= end:
            result.append((cursor, int(counts.get(cursor, 0))))
            cursor = cursor + step
        return result

    def _time_bucket_series_summary(
        self,
        sparse: Sequence[Tuple[Any, int]],
        complete: Sequence[Tuple[Any, int]],
        city: Optional[str],
        source_field: str,
        grain: str,
        limit: int,
    ) -> Dict[str, Any]:
        values = [int(count or 0) for _, count in complete]
        dates = {
            bucket.date() if isinstance(bucket, datetime) else bucket
            for bucket, _ in complete
            if isinstance(bucket, (date, datetime))
        }
        return {
            "task": "demand",
            "city": city,
            "source_field": source_field,
            "time_granularity": grain,
            "limit": limit,
            "sparse_points": len(sparse),
            "time_bucket_points": len(complete),
            "distinct_dates": len(dates),
            "zero_value_buckets": sum(1 for value in values if value == 0),
            "target_min": min(values) if values else None,
            "target_max": max(values) if values else None,
            "target_avg": round(float(statistics.mean(values)), 6) if values else None,
            "date_range": {
                "start": complete[0][0].isoformat() if complete else None,
                "end": complete[-1][0].isoformat() if complete else None,
            },
            "note": (
                "daily shipped_at history is preferred; hourly grain is an explicit degraded fallback"
                if grain == "hourly"
                else "daily shipped_at business history"
            ),
        }

    def _daily_numeric_records(
        self,
        task: str,
        city: Optional[str],
        limit: int,
    ) -> List[Tuple[date, float]]:
        query = ShipmentFact.query.filter(ShipmentFact.shipped_at.isnot(None))
        if city:
            query = query.filter(
                or_(
                    ShipmentFact.destination_city_std == city,
                    ShipmentFact.origin_city_std == city,
                )
            )
        if task == "eta":
            query = query.filter(
                or_(ShipmentFact.delivered_at.isnot(None), ShipmentFact.signed_at.isnot(None))
            )
        elif task == "delay":
            query = query.filter(
                ShipmentFact.eta_at.isnot(None),
                or_(ShipmentFact.delivered_at.isnot(None), ShipmentFact.signed_at.isnot(None)),
            )
        elif task == "cost":
            query = query.filter(ShipmentFact.freight.isnot(None), ShipmentFact.freight > 0)

        rows_query = (
            query.with_entities(
                ShipmentFact.shipped_at,
                ShipmentFact.eta_at,
                ShipmentFact.delivered_at,
                ShipmentFact.signed_at,
                ShipmentFact.freight,
            )
            .order_by(ShipmentFact.shipped_at.asc(), ShipmentFact.id.asc())
            .limit(limit)
        )
        rows: List[Tuple[date, float]] = []
        for fact in self._iter_query(rows_query):
            shipped_at = fact.shipped_at
            if not shipped_at:
                continue
            if task == "eta":
                actual_at = self._actual_at(fact)
                if not actual_at:
                    continue
                value = (actual_at - shipped_at).total_seconds() / 3600.0
            elif task == "delay":
                actual_at = self._actual_at(fact)
                if not fact.eta_at or not actual_at:
                    continue
                value = (actual_at - fact.eta_at).total_seconds() / 60.0
            else:
                value = self._coerce_float(fact.freight, 0.0)
                if value <= 0:
                    continue
            rows.append((shipped_at.date(), float(value)))
        return rows

    def _time_series_model_result(
        self,
        series: Sequence[Tuple[date, float]],
        split_at: int,
        model_id: str,
    ) -> Dict[str, Any]:
        actual: List[float] = []
        predicted: List[float] = []
        rows: List[Dict[str, Any]] = []
        for index in range(split_at, len(series)):
            history = series[:index]
            target_day, target_value = series[index]
            prediction = self._predict_time_series_value(history, target_day, model_id)
            actual.append(float(target_value))
            predicted.append(float(prediction))
            rows.append(
                {
                    "date": target_day.isoformat(),
                    "actual": round(float(target_value), 6),
                    "predicted": round(float(prediction), 6),
                    "absolute_error": round(abs(float(target_value) - float(prediction)), 6),
                }
            )

        return {
            "model_id": model_id,
            "model_family": "classical_time_series",
            "metrics": self._metrics(actual=actual, predicted=predicted),
            "backtest_rows": rows[:14],
            "training_note": self._time_series_model_note(model_id),
        }

    def _forecast_time_series(
        self,
        series: Sequence[Tuple[date, float]],
        model_id: str,
        horizon_days: int,
    ) -> List[Dict[str, Any]]:
        history = list(series)
        forecast: List[Dict[str, Any]] = []
        for offset in range(1, horizon_days + 1):
            target_day = history[-1][0] + timedelta(days=1)
            predicted = max(0.0, self._predict_time_series_value(history, target_day, model_id))
            forecast.append(
                {
                    "date": target_day.isoformat(),
                    "predicted_value": round(predicted, 6),
                    "method": model_id,
                }
            )
            history.append((target_day, predicted))
        return forecast

    def _predict_time_series_value(
        self,
        history: Sequence[Tuple[date, float]],
        target_day: date,
        model_id: str,
    ) -> float:
        values = [float(value) for _, value in history]
        if not values:
            return 0.0
        if model_id == "weekday_mean":
            return self._weekday_mean_predict(history, target_day)
        if model_id == "moving_average_7":
            return float(statistics.mean(values[-min(7, len(values)):]))
        if model_id == "seasonal_naive_7":
            same_weekday = [
                value for day, value in reversed(history)
                if day.weekday() == target_day.weekday()
            ]
            return float(same_weekday[0] if same_weekday else values[-1])
        if model_id == "exponential_smoothing_alpha_0_35":
            return self._single_exponential_smoothing(values, alpha=0.35)
        return float(statistics.mean(values))

    def _single_exponential_smoothing(self, values: Sequence[float], alpha: float) -> float:
        level = float(values[0])
        for value in values[1:]:
            level = alpha * float(value) + (1.0 - alpha) * level
        return float(level)

    def _time_series_summary(
        self,
        series: Sequence[Tuple[date, float]],
        task: str,
        city: Optional[str],
    ) -> Dict[str, Any]:
        values = [float(value) for _, value in series]
        return {
            "task": task,
            "city": city,
            "daily_points": len(series),
            "date_range": {
                "start": series[0][0].isoformat() if series else None,
                "end": series[-1][0].isoformat() if series else None,
            },
            "target_min": round(min(values), 6) if values else None,
            "target_max": round(max(values), 6) if values else None,
            "target_avg": round(float(statistics.mean(values)), 6) if values else None,
            "zero_value_days": sum(1 for value in values if abs(value) < 1e-9),
        }

    def _deep_learning_readiness(
        self,
        series: Sequence[Tuple[date, float]],
        sequence_length: int,
    ) -> Dict[str, Any]:
        windows = max(0, len(series) - sequence_length)
        minimum_windows = 32
        ready = windows >= minimum_windows
        return {
            "ready": ready,
            "status": "ready_for_offline_training" if ready else "needs_more_time_points",
            "daily_points": len(series),
            "sequence_length": sequence_length,
            "training_windows": windows,
            "minimum_training_windows": minimum_windows,
            "candidate_models": ["LSTM", "GRU", "TemporalFusionTransformer"],
            "recommended_next_step": (
                "train_offline_lstm_tft_shadow_models"
                if ready
                else "continue_accumulating_daily_history_or_reduce_sequence_length_for_experiment"
            ),
            "deployment_boundary": "shadow_evaluation_only_until_backtests_beat_classical_baselines",
        }

    def _time_series_model_note(self, model_id: str) -> str:
        notes = {
            "historical_mean": "Predicts the average of all prior observations.",
            "weekday_mean": "Uses prior observations with the same weekday, falling back to global mean.",
            "moving_average_7": "Uses the trailing seven observed daily values.",
            "seasonal_naive_7": "Uses the most recent observation with the same weekday, falling back to last value.",
            "exponential_smoothing_alpha_0_35": "Single exponential smoothing with alpha=0.35.",
        }
        return notes.get(model_id, "Classical time-series baseline.")

    def _daily_capacity_demand_series(
        self,
        city: Optional[str],
        limit: int,
    ) -> List[Dict[str, Any]]:
        query = ShipmentFact.query.filter(ShipmentFact.shipped_at.isnot(None))
        if city:
            query = query.filter(
                or_(
                    ShipmentFact.origin_city_std == city,
                    ShipmentFact.destination_city_std == city,
                )
            )
        grouped: Dict[date, Dict[str, float]] = defaultdict(lambda: {
            "shipment_count": 0.0,
            "weight_kg": 0.0,
            "volume_m3": 0.0,
        })
        rows_query = (
            query.with_entities(
                ShipmentFact.shipped_at,
                ShipmentFact.weight_kg,
                ShipmentFact.volume_m3,
            )
            .order_by(ShipmentFact.shipped_at.asc(), ShipmentFact.id.asc())
            .limit(limit)
        )
        for fact in self._iter_query(rows_query):
            if not fact.shipped_at:
                continue
            row = grouped[fact.shipped_at.date()]
            row["shipment_count"] += 1
            row["weight_kg"] += max(0.0, self._coerce_float(fact.weight_kg, 0.0))
            row["volume_m3"] += max(0.0, self._coerce_float(fact.volume_m3, 0.0))

        if not grouped:
            return []

        start = min(grouped)
        end = max(grouped)
        result: List[Dict[str, Any]] = []
        cursor = start
        while cursor <= end:
            row = grouped[cursor]
            result.append(
                {
                    "date": cursor,
                    "shipment_count": float(row["shipment_count"]),
                    "weight_kg": float(row["weight_kg"]),
                    "volume_m3": float(row["volume_m3"]),
                }
            )
            cursor += timedelta(days=1)
        return result

    def _daily_cost_volatility_series(
        self,
        city: Optional[str],
        limit: int,
    ) -> List[Dict[str, Any]]:
        query = ShipmentFact.query.filter(
            ShipmentFact.shipped_at.isnot(None),
            ShipmentFact.freight.isnot(None),
            ShipmentFact.freight > 0,
        )
        if city:
            query = query.filter(
                or_(
                    ShipmentFact.origin_city_std == city,
                    ShipmentFact.destination_city_std == city,
                )
            )
        grouped: Dict[date, Dict[str, float]] = defaultdict(lambda: {
            "shipment_count": 0.0,
            "total_freight": 0.0,
            "weight_kg": 0.0,
            "volume_m3": 0.0,
        })
        rows_query = (
            query.with_entities(
                ShipmentFact.shipped_at,
                ShipmentFact.freight,
                ShipmentFact.weight_kg,
                ShipmentFact.volume_m3,
            )
            .order_by(ShipmentFact.shipped_at.asc(), ShipmentFact.id.asc())
            .limit(limit)
        )
        for fact in self._iter_query(rows_query):
            if not fact.shipped_at:
                continue
            row = grouped[fact.shipped_at.date()]
            row["shipment_count"] += 1
            row["total_freight"] += max(0.0, self._coerce_float(fact.freight, 0.0))
            row["weight_kg"] += max(0.0, self._coerce_float(fact.weight_kg, 0.0))
            row["volume_m3"] += max(0.0, self._coerce_float(fact.volume_m3, 0.0))

        result = []
        for target_day, row in sorted(grouped.items(), key=lambda item: item[0]):
            shipment_count = max(1.0, row["shipment_count"])
            total_freight = float(row["total_freight"])
            result.append(
                {
                    "date": target_day,
                    "shipment_count": float(row["shipment_count"]),
                    "total_freight": total_freight,
                    "avg_freight": total_freight / shipment_count,
                    "unit_cost_per_kg": total_freight / max(row["weight_kg"], 1.0),
                    "unit_cost_per_m3": total_freight / max(row["volume_m3"], 1.0),
                    "weight_kg": float(row["weight_kg"]),
                    "volume_m3": float(row["volume_m3"]),
                }
            )
        return result

    def _fleet_capacity_summary(self, include_all_vehicles: bool = False) -> Dict[str, Any]:
        query = Vehicle.query
        if not include_all_vehicles:
            query = query.filter(Vehicle.status.in_(["available", "idle", "空闲"]))
        vehicles = query.order_by(Vehicle.id.asc()).all()
        total_weight_tons = 0.0
        total_volume = 0.0
        vehicle_rows = []
        for vehicle in vehicles:
            weight_tons = self._coerce_float(
                vehicle.load_capacity if vehicle.load_capacity is not None else vehicle.capacity,
                0.0,
            )
            volume_m3 = self._coerce_float(
                vehicle.volume_capacity if vehicle.volume_capacity is not None else weight_tons * 3.0,
                0.0,
            )
            weight_tons = max(0.0, weight_tons)
            volume_m3 = max(0.0, volume_m3)
            total_weight_tons += weight_tons
            total_volume += volume_m3
            vehicle_rows.append(
                {
                    "id": vehicle.id,
                    "plate_number": vehicle.plate_number,
                    "status": vehicle.status,
                    "capacity_weight_tons": round(weight_tons, 4),
                    "capacity_volume_m3": round(volume_m3, 4),
                }
            )

        return {
            "vehicle_source": "vehicles",
            "capacity_source": "vehicles.available.load_capacity_volume_capacity"
            if not include_all_vehicles
            else "vehicles.all.load_capacity_volume_capacity",
            "include_all_vehicles": include_all_vehicles,
            "available_vehicles": len(vehicles),
            "total_capacity_weight_tons": round(total_weight_tons, 4),
            "total_capacity_weight_kg": round(total_weight_tons * 1000.0, 4),
            "total_capacity_volume_m3": round(total_volume, 4),
            "vehicles": vehicle_rows[:20],
        }

    def _best_time_series_model(
        self,
        series: Sequence[Tuple[date, float]],
        test_days: int,
    ) -> Dict[str, Any]:
        if len(series) < MIN_EVALUATION_ROWS:
            return {
                "model_id": "moving_average_7",
                "model_family": "classical_time_series",
                "metrics": self._empty_metrics(),
                "fallback_reason": "TIME_SERIES_POINTS_INSUFFICIENT",
            }
        test_size = min(test_days, max(1, len(series) // 3))
        split_at = max(1, len(series) - test_size)
        model_ids = [
            "historical_mean",
            "weekday_mean",
            "moving_average_7",
            "seasonal_naive_7",
            "exponential_smoothing_alpha_0_35",
        ]
        results = [
            self._time_series_model_result(series, split_at, model_id)
            for model_id in model_ids
        ]
        results.sort(
            key=lambda item: (
                item.get("metrics", {}).get("mae") is None,
                item.get("metrics", {}).get("mae") if item.get("metrics", {}).get("mae") is not None else float("inf"),
            )
        )
        best = dict(results[0])
        best["candidate_count"] = len(results)
        best["test_points"] = len(series) - split_at
        return best

    def _capacity_gap_recommendations(
        self,
        forecast_rows: Sequence[Dict[str, Any]],
        fleet: Dict[str, Any],
    ) -> List[str]:
        shortage_days = [row for row in forecast_rows if row.get("status") == "shortage"]
        recommendations = []
        if fleet.get("available_vehicles", 0) <= 0:
            recommendations.append("当前没有可用车辆容量，建议先补充运营运力配置或同步车辆状态。")
        if shortage_days:
            recommendations.append(f"未来 {len(shortage_days)} 天存在预测运力缺口，建议提前调车、外协或拆分波次。")
        high_utilization_days = [
            row for row in forecast_rows
            if (row.get("weight_utilization") or 0) >= 0.85 or (row.get("volume_utilization") or 0) >= 0.85
        ]
        if high_utilization_days:
            recommendations.append("部分日期预测利用率超过 85%，建议在智能调度中开启容量优先或风险保守策略。")
        recommendations.append("该预测仅用于 shadow planning，最终派车仍需由调度求解器校验容量、时间窗和订单唯一分配。")
        return recommendations

    def _cost_volatility_recommendations(self, forecast_rows: Sequence[Dict[str, Any]]) -> List[str]:
        high_risk_days = [row for row in forecast_rows if row.get("risk_level") == "high"]
        medium_risk_days = [row for row in forecast_rows if row.get("risk_level") == "medium"]
        recommendations = []
        if high_risk_days:
            recommendations.append(f"未来 {len(high_risk_days)} 天成本波动风险较高，建议提前锁价、复核承运商报价或切换备选线路。")
        if medium_risk_days:
            recommendations.append(f"未来 {len(medium_risk_days)} 天存在中等成本压力，建议在调度方案对比中提高成本权重。")
        recommendations.append("成本波动预测只用于经营预警和方案评分，不能直接替代财务结算或调度硬约束。")
        recommendations.append("后续 LightGBM/LSTM/TFT 成本模型应继续复用该 unit-cost 与 volatility 评估口径。")
        return recommendations

    def _scorecard_component(
        self,
        component_id: str,
        label: str,
        score: float,
        status: str,
        details: Dict[str, Any],
    ) -> Dict[str, Any]:
        bounded_score = round(max(0.0, min(100.0, float(score))), 4)
        return {
            "id": component_id,
            "label": label,
            "score": bounded_score,
            "status": status,
            "details": details,
        }

    def _scorecard_recommendations(
        self,
        components: Sequence[Dict[str, Any]],
        gates: Sequence[Dict[str, Any]],
    ) -> List[str]:
        recommendations = []
        failed_gates = [gate for gate in gates if not gate.get("passed")]
        weak_components = [component for component in components if float(component.get("score", 0.0)) < 70.0]
        if failed_gates:
            recommendations.append(
                "存在未通过 readiness gate，建议先补齐真实数据、baseline 指标或 shadow 训练窗口，再推进自动化建议。"
            )
        for component in weak_components:
            if component.get("id") == "capacity_planning":
                recommendations.append("运力规划分偏低，建议补充车辆状态、外协运力和波次拆分策略后再做调度收益评估。")
            elif component.get("id") == "cost_volatility":
                recommendations.append("成本波动分偏低，建议在调度方案对比中加入成本保护权重，并复核高风险线路报价。")
            elif component.get("id") == "time_series_readiness":
                recommendations.append("时序 readiness 仍处于 shadow 阶段，LSTM/TFT 应先离线回测超过经典 baseline。")
            elif component.get("id") == "baseline_coverage":
                recommendations.append("预测 baseline 覆盖不足，优先补齐 demand/ETA/delay/cost 的 MAE/RMSE/MAPE。")
        if not recommendations:
            recommendations.append("AI 预测链路已具备较好的 shadow readiness，可继续推进 LightGBM/LSTM/TFT 离线对比。")
        recommendations.append("该 scorecard 是验收与决策入口，不会写业务表，也不会替代 Gurobi/OR-Tools/ALNS 硬约束求解。")
        return recommendations

    def _capacity_gap_truth_contract(self) -> Dict[str, Any]:
        return {
            "data_source": "shipment_fact",
            "demand_source": "shipment_facts.shipped_at_weight_kg_volume_m3",
            "capacity_source": "vehicles.load_capacity_volume_capacity",
            "distance_source": "not_used_for_capacity_gap_forecast",
            "path_source": "not_route_geometry",
            "business_mutation": "none",
            "deployment_boundary": "shadow_capacity_planning_only_solver_must_enforce_hard_constraints",
            "authenticity_level": "B_for_real_shipments_and_vehicle_capacity_C_when_missing",
        }

    def _cost_volatility_truth_contract(self) -> Dict[str, Any]:
        return {
            "data_source": "shipment_fact",
            "cost_source": "shipment_facts.freight_weight_kg_volume_m3",
            "distance_source": "not_used_for_cost_volatility_forecast",
            "path_source": "not_route_geometry",
            "business_mutation": "none",
            "deployment_boundary": "shadow_cost_planning_only_not_financial_settlement_or_dispatch_controller",
            "authenticity_level": "B_for_real_freight_history_C_when_missing",
        }

    def _ratio(self, numerator: float, denominator: float) -> Optional[float]:
        if not denominator:
            return None
        return round(float(numerator) / float(denominator), 6)

    def _rolling_coefficient_of_variation(self, values: Sequence[float], window: int) -> Optional[float]:
        clean_values = [float(value) for value in values if value is not None and math.isfinite(float(value))]
        if not clean_values:
            return None
        sample = clean_values[-min(window, len(clean_values)):]
        if not sample:
            return None
        mean_value = statistics.mean(sample)
        if abs(mean_value) < 1e-9:
            return None
        return abs(statistics.pstdev(sample) / mean_value) if len(sample) > 1 else 0.0

    def _percentile(self, values: Sequence[float], percentile: float) -> Optional[float]:
        clean_values = sorted(float(value) for value in values if value is not None and math.isfinite(float(value)))
        if not clean_values:
            return None
        clipped = max(0.0, min(1.0, float(percentile)))
        if len(clean_values) == 1:
            return clean_values[0]
        position = (len(clean_values) - 1) * clipped
        lower = int(math.floor(position))
        upper = int(math.ceil(position))
        if lower == upper:
            return clean_values[lower]
        weight = position - lower
        return clean_values[lower] * (1.0 - weight) + clean_values[upper] * weight

    def _round_or_none(self, value: Optional[float], digits: int) -> Optional[float]:
        if value is None:
            return None
        try:
            if not math.isfinite(float(value)):
                return None
            return round(float(value), digits)
        except (TypeError, ValueError):
            return None

    def _weekday_mean_predict(self, train: Sequence[Tuple[date, int]], target_day: date) -> float:
        same_weekday = [count for day, count in train if day.weekday() == target_day.weekday()]
        values = same_weekday or [count for _, count in train]
        return float(statistics.mean(values))

    def _time_bucket_mean_predict(self, train: Sequence[Tuple[Any, float]], target_bucket: Any, grain: str) -> float:
        if grain == "daily":
            return self._weekday_mean_predict(train, target_bucket)
        same_hour_weekday = [
            value
            for bucket, value in train
            if isinstance(bucket, datetime)
            and isinstance(target_bucket, datetime)
            and bucket.weekday() == target_bucket.weekday()
            and bucket.hour == target_bucket.hour
        ]
        same_hour = [
            value
            for bucket, value in train
            if isinstance(bucket, datetime)
            and isinstance(target_bucket, datetime)
            and bucket.hour == target_bucket.hour
        ]
        values = same_hour_weekday or same_hour or [value for _, value in train]
        return float(statistics.mean(values)) if values else 0.0

    def _predict_group_median(self, train: Sequence[PredictionRecord], item: PredictionRecord) -> float:
        exact = [row.target for row in train if row.feature_key == item.feature_key]
        if exact:
            return float(statistics.median(exact))
        fallback = [row.target for row in train if row.fallback_key == item.fallback_key]
        if fallback:
            return float(statistics.median(fallback))
        return float(statistics.median([row.target for row in train]))

    def _predict_cost(self, train: Sequence[PredictionRecord], item: PredictionRecord) -> float:
        def unit_cost(row: PredictionRecord) -> Optional[float]:
            weight = self._coerce_float(row.payload.get("weight_kg"), 0.0)
            if weight <= 0:
                return None
            return float(row.target) / weight

        exact_units = [unit_cost(row) for row in train if row.feature_key == item.feature_key]
        exact_units = [value for value in exact_units if value is not None]
        fallback_units = [unit_cost(row) for row in train if row.fallback_key == item.fallback_key]
        fallback_units = [value for value in fallback_units if value is not None]
        all_units = [unit_cost(row) for row in train]
        all_units = [value for value in all_units if value is not None]

        weight = self._coerce_float(item.payload.get("weight_kg"), 0.0)
        if weight > 0 and (exact_units or fallback_units or all_units):
            unit = statistics.median(exact_units or fallback_units or all_units)
            return float(unit * weight)
        return self._predict_group_median(train, item)

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
            ShipmentFact.cargo_type,
            ShipmentFact.transport_mode,
            ShipmentFact.freight,
            ShipmentFact.shipped_at,
            ShipmentFact.eta_at,
            ShipmentFact.delivered_at,
            ShipmentFact.signed_at,
            ShipmentFact.weight_kg,
            ShipmentFact.volume_m3,
        )

    def _iter_query(self, query, chunk_size: int = 1000):
        return query.yield_per(chunk_size)

    def _record_from_fact(self, fact: Any, target: float, target_name: str) -> PredictionRecord:
        mode = self._clean_text(fact.transport_mode) or "unknown_mode"
        cargo = self._clean_text(fact.cargo_type) or "unknown_cargo"
        origin = self._clean_text(fact.origin_city_std) or "unknown_origin"
        destination = self._clean_text(fact.destination_city_std) or "unknown_destination"
        feature_key = "|".join([origin, destination, mode, cargo])
        fallback_key = "|".join([mode, cargo])
        distance_km = self._haversine_km(
            fact.origin_lng,
            fact.origin_lat,
            fact.destination_lng,
            fact.destination_lat,
        )
        payload = {
            "shipment_id": fact.external_shipment_id,
            "order_id": fact.external_order_id,
            "origin_city": origin,
            "destination_city": destination,
            "transport_mode": mode,
            "cargo_type": cargo,
            "weight_kg": self._coerce_float(fact.weight_kg, 0.0),
            "volume_m3": self._coerce_float(fact.volume_m3, 0.0),
            "freight": self._coerce_float(fact.freight, 0.0),
            "distance_km": distance_km,
            "shipped_weekday": fact.shipped_at.weekday() if fact.shipped_at else None,
            "shipped_hour": fact.shipped_at.hour if fact.shipped_at else None,
            "target_name": target_name,
        }
        return PredictionRecord(
            id=fact.external_order_id or fact.external_shipment_id or fact.id,
            target=float(target),
            feature_key=feature_key,
            fallback_key=fallback_key,
            payload=payload,
        )

    def _actual_delivery_query(self):
        return ShipmentFact.query.filter(
            ShipmentFact.shipped_at.isnot(None),
            or_(ShipmentFact.delivered_at.isnot(None), ShipmentFact.signed_at.isnot(None)),
        )

    def _actual_at(self, fact: ShipmentFact) -> Optional[datetime]:
        return fact.delivered_at or fact.signed_at

    def _metrics(self, actual: Sequence[float], predicted: Sequence[float]) -> Dict[str, Any]:
        if not actual or not predicted:
            return self._empty_metrics()
        pairs = [(float(a), float(p)) for a, p in zip(actual, predicted)]
        errors = [p - a for a, p in pairs]
        abs_errors = [abs(value) for value in errors]
        squared = [value * value for value in errors]
        ape = [abs(p - a) / max(abs(a), 1.0) for a, p in pairs]
        return {
            "mae": round(float(statistics.mean(abs_errors)), 6),
            "rmse": round(math.sqrt(float(statistics.mean(squared))), 6),
            "mape": round(float(statistics.mean(ape)) * 100.0, 6),
            "sample_count": len(pairs),
            "metric_note": "MAPE denominator is clipped at 1.0 to avoid division by zero.",
        }

    def _empty_metrics(self) -> Dict[str, Any]:
        return {
            "mae": None,
            "rmse": None,
            "mape": None,
            "sample_count": 0,
            "metric_note": "No backtest sample available.",
        }

    def _insufficient_result(self, task: str, rows: int, reason: str) -> Dict[str, Any]:
        return {
            "success": True,
            "task": task,
            "data_source": "shipment_fact",
            "provider_status": "degraded",
            "fallback_reason": reason,
            "authenticity_level": "C",
            "model_stage": "phase3_baseline",
            "metrics": self._empty_metrics(),
            "feature_summary": {
                "records": rows,
                "minimum_required": MIN_EVALUATION_ROWS,
            },
            "backtest": [],
            "forecast": [],
        }

    def _unsupported_task(self, task: str) -> Dict[str, Any]:
        return {
            "success": False,
            "task": task,
            "data_source": "shipment_fact",
            "provider_status": "degraded",
            "fallback_reason": "UNSUPPORTED_PREDICTION_TASK",
            "authenticity_level": "C",
            "metrics": self._empty_metrics(),
        }

    def _readiness(self, rows: int, minimum: int) -> Dict[str, Any]:
        return {
            "ready": rows >= minimum,
            "records": rows,
            "minimum_required": minimum,
            "status": "ready" if rows >= minimum else "insufficient_data",
        }

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
            "path_source": "not_route_geometry_prediction_features",
            "provider_status": "ok_or_degraded_per_dataset_readiness",
            "fallback_reason": "set_when_records_are_insufficient_or_task_unsupported",
            "authenticity_level": "B_for_real_fact_baselines_C_when_insufficient",
        }

    def _target_definition(self, task: str) -> Dict[str, Any]:
        definitions = {
            "demand": {
                "target_name": "daily_order_count",
                "unit": "orders",
                "source_fields": ["shipment_facts.shipped_at"],
                "grain": "day",
                "description": "Count of shipment facts shipped on each day.",
            },
            "eta": {
                "target_name": "actual_transit_hours",
                "unit": "hours",
                "source_fields": [
                    "shipment_facts.shipped_at",
                    "shipment_facts.delivered_at",
                    "shipment_facts.signed_at",
                ],
                "grain": "shipment",
                "description": "Hours from shipped_at to delivered_at, falling back to signed_at.",
            },
            "delay": {
                "target_name": "arrival_delay_minutes",
                "unit": "minutes",
                "source_fields": [
                    "shipment_facts.eta_at",
                    "shipment_facts.delivered_at",
                    "shipment_facts.signed_at",
                ],
                "grain": "shipment",
                "description": "Minutes between actual delivery/signing time and eta_at.",
            },
            "cost": {
                "target_name": "freight_amount",
                "unit": "currency",
                "source_fields": ["shipment_facts.freight"],
                "grain": "shipment",
                "description": "Shipment freight amount.",
            },
        }
        return definitions.get(task, {"target_name": task, "unit": "unknown", "source_fields": []})

    def _feature_schema(self, task: str) -> List[Dict[str, Any]]:
        if task == "demand":
            return [
                {"name": "date", "type": "date", "role": "time_index", "source": "shipment_facts.shipped_at"},
                {"name": "city_scope", "type": "category", "role": "filter_context", "source": "request.city"},
                {"name": "weekday", "type": "integer", "role": "feature", "source": "derived_date"},
                {"name": "is_weekend", "type": "boolean", "role": "feature", "source": "derived_date"},
                {"name": "month", "type": "integer", "role": "feature", "source": "derived_date"},
                {"name": "day_of_month", "type": "integer", "role": "feature", "source": "derived_date"},
                {"name": "trailing_7d_avg_orders", "type": "float", "role": "feature", "source": "derived_history"},
                {"name": "trailing_28d_avg_orders", "type": "float", "role": "feature", "source": "derived_history"},
                {"name": "target", "type": "integer", "role": "target", "source": "daily_count"},
            ]
        return [
            {"name": "origin_city", "type": "category", "role": "feature", "source": "shipment_facts.origin_city_std"},
            {"name": "destination_city", "type": "category", "role": "feature", "source": "shipment_facts.destination_city_std"},
            {"name": "transport_mode", "type": "category", "role": "feature", "source": "shipment_facts.transport_mode"},
            {"name": "cargo_type", "type": "category", "role": "feature", "source": "shipment_facts.cargo_type"},
            {"name": "weight_kg", "type": "float", "role": "feature", "source": "shipment_facts.weight_kg"},
            {"name": "volume_m3", "type": "float", "role": "feature", "source": "shipment_facts.volume_m3"},
            {"name": "freight", "type": "float", "role": "feature", "source": "shipment_facts.freight"},
            {"name": "distance_km", "type": "float", "role": "feature", "source": "shipment_fact_coordinates_haversine_when_needed"},
            {"name": "shipped_weekday", "type": "integer", "role": "feature", "source": "shipment_facts.shipped_at"},
            {"name": "shipped_hour", "type": "integer", "role": "feature", "source": "shipment_facts.shipped_at"},
            {"name": "feature_key", "type": "category", "role": "group_key", "source": "derived"},
            {"name": "fallback_key", "type": "category", "role": "fallback_group_key", "source": "derived"},
            {"name": "target", "type": "float", "role": "target", "source": self._target_definition(task).get("source_fields", [])},
        ]

    def _feature_dataset_summary(self, rows: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
        if not rows:
            return {
                "row_count": 0,
                "target_min": None,
                "target_max": None,
                "target_avg": None,
            }
        targets = [self._coerce_float(row.get("target"), 0.0) for row in rows]
        category_fields = ["origin_city", "destination_city", "transport_mode", "cargo_type", "city_scope"]
        category_cardinality = {
            field: len({row.get(field) for row in rows if row.get(field) is not None})
            for field in category_fields
            if any(field in row for row in rows)
        }
        return {
            "row_count": len(rows),
            "target_min": round(min(targets), 6),
            "target_max": round(max(targets), 6),
            "target_avg": round(float(statistics.mean(targets)), 6),
            "category_cardinality": category_cardinality,
        }

    def _feature_rows_for_task(
        self,
        task: str,
        limit: int,
        city: Optional[str] = None,
    ) -> Optional[List[Dict[str, Any]]]:
        if task == "demand":
            return self._demand_feature_rows(city=city, limit=limit)
        if task == "eta":
            return [self._feature_row_from_record(record) for record in self._eta_records(limit)]
        if task == "delay":
            return [self._feature_row_from_record(record) for record in self._delay_records(limit)]
        if task == "cost":
            return [self._feature_row_from_record(record) for record in self._cost_records(limit)]
        return None

    def _linear_dataset(
        self,
        rows: Sequence[Dict[str, Any]],
        task: str,
        hash_buckets: int = DEFAULT_MODEL_HASH_BUCKETS,
        state: Optional[Dict[str, Any]] = None,
    ) -> Tuple[np.ndarray, np.ndarray, Dict[str, Any]]:
        if state is None:
            numeric_fields = self._numeric_model_fields(task)
            categorical_fields = self._categorical_model_fields(task)
            means: Dict[str, float] = {}
            scales: Dict[str, float] = {}
            for field in numeric_fields:
                values = [self._coerce_float(row.get(field), 0.0) for row in rows]
                means[field] = float(statistics.mean(values)) if values else 0.0
                spread = float(statistics.pstdev(values)) if len(values) > 1 else 0.0
                scales[field] = spread if spread > 1e-9 else 1.0
            state = {
                "task": task,
                "numeric_fields": numeric_fields,
                "categorical_fields": categorical_fields,
                "numeric_means": means,
                "numeric_scales": scales,
                "hash_buckets": hash_buckets,
                "feature_names": self._linear_feature_names(numeric_fields, categorical_fields, hash_buckets),
            }
        else:
            numeric_fields = list(state["numeric_fields"])
            categorical_fields = list(state["categorical_fields"])
            hash_buckets = int(state["hash_buckets"])

        matrix: List[List[float]] = []
        targets: List[float] = []
        means = state["numeric_means"]
        scales = state["numeric_scales"]
        for row in rows:
            values = [1.0]
            for field in numeric_fields:
                raw_value = self._coerce_float(row.get(field), 0.0)
                values.append((raw_value - means.get(field, 0.0)) / scales.get(field, 1.0))
            hashed = [0.0] * (len(categorical_fields) * hash_buckets)
            for field_index, field in enumerate(categorical_fields):
                raw_value = row.get(field)
                category = "__missing__" if raw_value in (None, "") else str(raw_value)
                bucket = self._stable_bucket(f"{field}={category}", hash_buckets)
                hashed[field_index * hash_buckets + bucket] = 1.0
            values.extend(hashed)
            matrix.append(values)
            targets.append(self._coerce_float(row.get("target"), 0.0))

        return (
            np.asarray(matrix, dtype=float),
            np.asarray(targets, dtype=float),
            state,
        )

    def _numeric_model_fields(self, task: str) -> List[str]:
        if task == "demand":
            return [
                "weekday",
                "is_weekend",
                "month",
                "day_of_month",
                "trailing_7d_avg_orders",
                "trailing_28d_avg_orders",
            ]
        fields = [
            "weight_kg",
            "volume_m3",
            "distance_km",
            "shipped_weekday",
            "shipped_hour",
        ]
        if task != "cost":
            fields.append("freight")
        return fields

    def _categorical_model_fields(self, task: str) -> List[str]:
        if task == "demand":
            return ["city_scope"]
        return [
            "origin_city",
            "destination_city",
            "transport_mode",
            "cargo_type",
            "feature_key",
            "fallback_key",
        ]

    def _linear_feature_names(
        self,
        numeric_fields: Sequence[str],
        categorical_fields: Sequence[str],
        hash_buckets: int,
    ) -> List[str]:
        names = ["intercept"]
        names.extend([f"num:{field}" for field in numeric_fields])
        for field in categorical_fields:
            names.extend([f"hash:{field}:{idx}" for idx in range(hash_buckets)])
        return names

    def _fit_ridge_regression(self, x_train: np.ndarray, y_train: np.ndarray, alpha: float) -> np.ndarray:
        regularizer = np.eye(x_train.shape[1], dtype=float) * alpha
        regularizer[0, 0] = 0.0
        left = x_train.T @ x_train + regularizer
        right = x_train.T @ y_train
        try:
            return np.linalg.solve(left, right)
        except np.linalg.LinAlgError:
            return np.linalg.pinv(left) @ right

    def _predict_with_coefficients(self, matrix: np.ndarray, coefficients: np.ndarray) -> np.ndarray:
        return matrix @ coefficients

    def _linear_feature_importance(self, model: Dict[str, Any], top_n: int = 12) -> List[Dict[str, Any]]:
        names = model["state"].get("feature_names", [])
        coefficients = model.get("coefficients", [])
        pairs = []
        for name, coefficient in zip(names, coefficients):
            if name == "intercept":
                continue
            pairs.append((name, float(coefficient), abs(float(coefficient))))
        pairs.sort(key=lambda item: item[2], reverse=True)
        return [
            {
                "feature": name,
                "weight": round(weight, 6),
                "importance": round(importance, 6),
                "importance_type": "absolute_linear_weight_on_normalized_or_hashed_features",
            }
            for name, weight, importance in pairs[:top_n]
        ]

    def _model_public_summary(self, model: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "model_id": model["model_id"],
            "task": model["task"],
            "model_type": model["model_type"],
            "model_family": model["model_family"],
            "model_stage": model["model_stage"],
            "trained_at": model["trained_at"],
            "data_source": model["data_source"],
            "provider_status": model["provider_status"],
            "fallback_reason": model["fallback_reason"],
            "authenticity_level": model["authenticity_level"],
            "target_definition": model["target_definition"],
            "training_summary": model["training_summary"],
            "metrics": model["metrics"],
            "feature_importance": model.get("feature_importance", []),
        }

    def _select_model(
        self,
        task: Optional[str] = None,
        model_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        if model_id:
            model = self._trained_models.get(model_id)
            if model and (not task or model.get("task") == task):
                return model
            return None
        candidates = [
            model for model in self._trained_models.values()
            if not task or model.get("task") == task
        ]
        if not candidates:
            return None
        return sorted(candidates, key=lambda item: item.get("trained_at", ""), reverse=True)[0]

    def _prediction_rows(
        self,
        rows: Sequence[Dict[str, Any]],
        actual: np.ndarray,
        predicted: np.ndarray,
        row_limit: int,
    ) -> List[Dict[str, Any]]:
        result = []
        for row, actual_value, predicted_value in zip(rows[:row_limit], actual[:row_limit], predicted[:row_limit]):
            result.append(
                {
                    "id": row.get("id") or row.get("date"),
                    "target_name": row.get("target_name"),
                    "actual": round(float(actual_value), 6),
                    "predicted": round(float(predicted_value), 6),
                    "absolute_error": round(abs(float(actual_value) - float(predicted_value)), 6),
                    "origin_city": row.get("origin_city"),
                    "destination_city": row.get("destination_city"),
                    "city_scope": row.get("city_scope"),
                    "transport_mode": row.get("transport_mode"),
                    "cargo_type": row.get("cargo_type"),
                }
            )
        return result

    def _training_contract(self) -> Dict[str, Any]:
        return {
            "artifact_scope": "in_memory_process_cache",
            "business_mutation": "none",
            "model_type": "ridge_feature_hashing_regressor_v1",
            "dependency_profile": "numpy_only_no_sklearn_lightgbm_pytorch_required",
            "upgrade_path": "replace_or_compare_with_lightgbm_xgboost_lstm_tft_using_same_feature_contract",
        }

    def _unsupported_model_task(self, task: str) -> Dict[str, Any]:
        return {
            "success": False,
            "task": task,
            "data_source": "shipment_fact",
            "provider_status": "degraded",
            "fallback_reason": "UNSUPPORTED_PREDICTION_TASK",
            "authenticity_level": "C",
            "training_contract": self._training_contract(),
            "truth_contract": self._truth_contract(),
        }

    def _insufficient_model_result(self, task: str, rows: int, reason: str) -> Dict[str, Any]:
        return {
            "success": True,
            "task": task,
            "data_source": "shipment_fact",
            "provider_status": "degraded",
            "fallback_reason": reason,
            "authenticity_level": "C",
            "model_stage": "phase3_training_api",
            "metrics": self._empty_metrics(),
            "summary": {
                "records": rows,
                "minimum_required": MIN_MODEL_ROWS,
            },
            "training_contract": self._training_contract(),
            "truth_contract": self._truth_contract(),
        }

    def _no_model_result(
        self,
        task: Optional[str] = None,
        model_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        return {
            "success": True,
            "task": task,
            "model_id": model_id,
            "data_source": "shipment_fact",
            "provider_status": "degraded",
            "fallback_reason": "NO_TRAINED_MODEL_FOR_REQUEST",
            "authenticity_level": "C",
            "model_stage": "phase3_training_api",
            "metrics": self._empty_metrics(),
            "training_contract": self._training_contract(),
            "truth_contract": self._truth_contract(),
        }

    def _run_prediction_job(self, job_id: str, payload: Dict[str, Any], app=None) -> None:
        def run_inside_context():
            self._update_job(job_id, status="running", provider_status="running", progress=0.1)
            try:
                result = self._execute_prediction_job(payload)
                provider_status = result.get("provider_status", "ok" if result.get("success") else "degraded")
                self._update_job(
                    job_id,
                    status="completed",
                    provider_status=provider_status,
                    fallback_reason=result.get("fallback_reason"),
                    progress=1.0,
                    result=result,
                    completed_at=self._utc_now(),
                )
            except Exception as exc:  # pragma: no cover - defensive job isolation
                self._update_job(
                    job_id,
                    status="failed",
                    provider_status="degraded",
                    fallback_reason=f"PREDICTION_JOB_FAILED:{type(exc).__name__}",
                    progress=1.0,
                    error=str(exc),
                    completed_at=self._utc_now(),
                )

        if app is not None:
            with app.app_context():
                run_inside_context()
        else:
            run_inside_context()

    def _execute_prediction_job(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        task = str(payload.get("task") or "demand").strip().lower()
        model_family = str(payload.get("model_family") or "lstm").strip().lower()
        if model_family in {"tabular_baseline", "lightgbm", "xgboost", "ridge"}:
            result = self.train_model({**payload, "task": task})
            if result.get("model"):
                result["model"]["requested_model_family"] = model_family
            result["job_type"] = "tabular_training_snapshot"
            return result

        if model_family in {"lstm", "gru", "transformer", "transformerencoder", "temporal_fusion_transformer", "tft"}:
            benchmark = self.evaluate_time_series_benchmark(
                {
                    **payload,
                    "task": task,
                    "runtime_profile": "full",
                    "limit": self._coerce_int(payload.get("limit"), DEFAULT_LIMIT),
                    "horizon_days": self._coerce_int(payload.get("horizon_days"), 14),
                    "test_days": self._coerce_int(payload.get("test_days"), 14),
                    "sequence_length": self._coerce_int(payload.get("sequence_length"), 14),
                }
            )
            readiness = benchmark.get("deep_learning_readiness") or {}
            ready = bool(readiness.get("ready"))
            return {
                "success": True,
                "task": task,
                "model_family": model_family,
                "model_stage": "deep_shadow_job",
                "data_source": "shipment_fact",
                "provider_status": "ok" if ready else "degraded",
                "fallback_reason": None if ready else readiness.get("status") or benchmark.get("fallback_reason"),
                "authenticity_level": "B" if ready else "C",
                "deep_learning_readiness": readiness,
                "benchmark": benchmark,
                "model_snapshot": None,
                "training_contract": {
                    **self._training_contract(),
                    "deep_learning_boundary": (
                        "LSTM/GRU/Transformer jobs are shadow training gates; "
                        "no neural model is deployable until time-series windows pass readiness and backtests beat baselines"
                    ),
                },
                "truth_contract": self._truth_contract(),
            }

        return {
            "success": False,
            "task": task,
            "model_family": model_family,
            "provider_status": "degraded",
            "fallback_reason": "UNSUPPORTED_AI_JOB_MODEL_FAMILY",
            "authenticity_level": "C",
            "truth_contract": self._truth_contract(),
        }

    def _update_job(self, job_id: str, **updates: Any) -> None:
        with self._job_lock:
            job = self._jobs.get(job_id)
            if not job:
                return
            job.update(updates)
            job["updated_at"] = self._utc_now()

    def _latest_job_summaries(self, limit: int = 5) -> List[Dict[str, Any]]:
        with self._job_lock:
            jobs = list(self._jobs.values())
        return [
            self._job_public_summary(job)
            for job in sorted(jobs, key=lambda item: item.get("created_at", ""), reverse=True)[:limit]
        ]

    def _job_public_summary(self, job: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "job_id": job.get("job_id"),
            "status": job.get("status"),
            "task": job.get("task"),
            "model_family": job.get("model_family"),
            "provider_status": job.get("provider_status"),
            "fallback_reason": job.get("fallback_reason"),
            "progress": job.get("progress", 0.0),
            "created_at": job.get("created_at"),
            "updated_at": job.get("updated_at"),
            "completed_at": job.get("completed_at"),
        }

    def _safe_job_request(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        allowed = {
            "task",
            "model_family",
            "runtime_profile",
            "limit",
            "horizon_days",
            "test_days",
            "sequence_length",
            "city",
            "destination_city",
            "time_granularity",
            "series_source",
        }
        return {key: payload.get(key) for key in allowed if key in payload}

    def _utc_now(self) -> str:
        return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    def _stable_bucket(self, value: str, bucket_count: int) -> int:
        digest = hashlib.sha256(value.encode("utf-8")).hexdigest()
        return int(digest[:12], 16) % bucket_count

    def _normalise_tasks(self, tasks: Any) -> List[str]:
        if isinstance(tasks, str):
            raw = [item.strip() for item in tasks.split(",")]
        else:
            raw = [str(item).strip() for item in tasks]
        result = []
        for item in raw:
            task = item.lower()
            if task and task not in result:
                result.append(task)
        return result or list(DEFAULT_TASKS)

    def _normalise_granularity(self, value: Any, default: str = "daily") -> str:
        text = str(value or default).strip().lower()
        return text if text in {"daily", "hourly", "auto"} else default

    def _normalise_series_source(self, value: Any, default: str = "shipped_at") -> str:
        text = str(value or default).strip().lower()
        return text if text in {"shipped_at", "created_at", "eta_at", "delivered_at", "signed_at", "auto"} else default

    def _series_source_candidates(self, source: str) -> List[str]:
        if source == "auto":
            return ["shipped_at", "delivered_at", "signed_at", "created_at"]
        return [source]

    def _granularity_candidates(self, granularity: str) -> List[str]:
        if granularity == "auto":
            return ["daily", "hourly"]
        return [granularity]

    def _series_field_column(self, source_field: str):
        return {
            "shipped_at": ShipmentFact.shipped_at,
            "eta_at": ShipmentFact.eta_at,
            "delivered_at": ShipmentFact.delivered_at,
            "signed_at": ShipmentFact.signed_at,
            "created_at": ShipmentFact.created_at,
        }.get(source_field)

    def _time_bucket_expr(self, column, grain: str):
        try:
            dialect = db.session.get_bind().dialect
        except Exception:
            dialect = getattr(getattr(db.session, "bind", None), "dialect", None)
        dialect_name = getattr(dialect, "name", "")
        if grain == "hourly":
            if dialect_name == "sqlite":
                return func.strftime("%Y-%m-%d %H:00:00", column)
            return func.date_trunc("hour", column)
        if dialect_name == "sqlite":
            return func.strftime("%Y-%m-%d", column)
        return func.date(column)

    def _parse_time_bucket(self, value: Any, grain: str):
        if value is None:
            return None
        if isinstance(value, datetime):
            return value.replace(minute=0, second=0, microsecond=0) if grain == "hourly" else value.date()
        if isinstance(value, date):
            return datetime.combine(value, datetime.min.time()) if grain == "hourly" else value
        text = str(value)
        try:
            if grain == "hourly":
                return datetime.fromisoformat(text.replace(" ", "T")).replace(minute=0, second=0, microsecond=0)
            return datetime.fromisoformat(text[:10]).date()
        except ValueError:
            return None

    def _bucket_step(self, grain: str) -> timedelta:
        return timedelta(hours=1) if grain == "hourly" else timedelta(days=1)

    def _forecast_horizon_buckets(self, horizon_days: int, grain: str) -> int:
        days = max(1, min(60, self._coerce_int(horizon_days, 7)))
        return days * 24 if grain == "hourly" else days

    def _timeline_field_summary(self, column, name: str, city: Optional[str]) -> Dict[str, Any]:
        query = ShipmentFact.query.filter(column.isnot(None))
        if city:
            query = query.filter(
                or_(
                    ShipmentFact.destination_city_std == city,
                    ShipmentFact.origin_city_std == city,
                )
            )
        rows_query = query.with_entities(column).order_by(column.asc(), ShipmentFact.id.asc())
        dates = set()
        hours = set()
        non_null = 0
        first_value = None
        last_value = None
        for row in self._iter_query(rows_query):
            value = row[0]
            if not value:
                continue
            non_null += 1
            first_value = first_value or value
            last_value = value
            dates.add(value.date())
            hours.add(value.replace(minute=0, second=0, microsecond=0))
        total = ShipmentFact.query.count()
        return {
            "field": name,
            "non_null_records": non_null,
            "null_records": max(0, total - non_null),
            "null_rate": round((max(0, total - non_null) / max(total, 1)), 6),
            "distinct_dates": len(dates),
            "distinct_hours": len(hours),
            "range": {
                "start": first_value.isoformat() if first_value else None,
                "end": last_value.isoformat() if last_value else None,
            },
            "daily_training_windows_14": max(0, len(dates) - 14),
            "hourly_training_windows_24": max(0, len(hours) - 24),
        }

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

    def _clean_text(self, value: Any) -> Optional[str]:
        text = str(value).strip() if value is not None else ""
        return text or None


_service: Optional[ShipmentPredictionService] = None


def get_shipment_prediction_service() -> ShipmentPredictionService:
    global _service
    if _service is None:
        _service = ShipmentPredictionService()
    return _service
