"""Compatibility APIs for the legacy Advanced ML frontend pages.

The old `/api/advanced-ml/*` routes used an in-memory demo service and were
often disabled together with legacy ML routes. These routes now stay available
as a lightweight real-data facade over `shipment_facts`. Deep models remain
background/shadow jobs until the time-series readiness gates pass.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

from flask import Blueprint, current_app, jsonify, request

from app.services.shipment_anomaly_service import get_shipment_anomaly_service
from app.services.shipment_prediction_service import get_shipment_prediction_service


advanced_ml_bp = Blueprint("advanced_ml", __name__, url_prefix="/api/advanced-ml")

INTERACTIVE_LIMIT = 5000
FULL_LIMIT = 50000


def _coerce_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _runtime_profile(payload: Optional[Dict[str, Any]] = None, default: str = "interactive") -> str:
    value = (payload or {}).get("runtime_profile") or request.args.get("runtime_profile") or default
    return "full" if str(value).lower() == "full" else "interactive"


def _bounded_limit(value: Any, profile: str) -> int:
    max_limit = FULL_LIMIT if profile == "full" else INTERACTIVE_LIMIT
    fallback = FULL_LIMIT if profile == "full" else INTERACTIVE_LIMIT
    return max(1, min(max_limit, _coerce_int(value, fallback)))


def _forecast_payload(default_profile: str = "interactive") -> Dict[str, Any]:
    profile = _runtime_profile(default=default_profile)
    return {
        "days": max(1, min(60, request.args.get("days", 7, type=int))),
        "city": request.args.get("city") or request.args.get("region") or request.args.get("destination_city"),
        "runtime_profile": profile,
        "limit": _bounded_limit(request.args.get("limit", type=int), profile),
        "time_granularity": request.args.get("time_granularity", "auto"),
        "series_source": request.args.get("series_source", "shipped_at"),
    }


def _forecast_points(forecast: Dict[str, Any]) -> List[Dict[str, Any]]:
    rows = forecast.get("forecast") or []
    points = []
    for idx, row in enumerate(rows):
        value = row.get("predicted_orders", row.get("value", 0))
        lower = row.get("lower_bound", row.get("lower", value))
        upper = row.get("upper_bound", row.get("upper", value))
        points.append(
            {
                "index": idx + 1,
                "date": row.get("date") or row.get("bucket_start"),
                "bucket_start": row.get("bucket_start") or row.get("date"),
                "value": value,
                "predicted_orders": value,
                "lower": lower,
                "upper": upper,
                "lower_bound": lower,
                "upper_bound": upper,
                "method": row.get("method") or forecast.get("model"),
                "time_granularity": row.get("time_granularity") or forecast.get("time_granularity"),
            }
        )
    return points


def _model_boundary_label(model_family: str) -> str:
    lowered = str(model_family or "").lower()
    if lowered in {"lstm", "gru", "transformer", "tft", "prophet", "ensemble"}:
        return (
            f"{model_family} compatibility request; current online response is real shipment_fact "
            "time-series baseline plus deep-model readiness/shadow metadata"
        )
    return "real shipment_fact time-series baseline"


def _prediction_response(
    forecast: Dict[str, Any],
    *,
    requested_model_family: str,
    profile: str,
    limit: int,
) -> Dict[str, Any]:
    points = _forecast_points(forecast)
    forecast_status = forecast.get("forecast_status") or ("ok" if points else "insufficient_history")
    provider_status = forecast.get("provider_status") or ("ok" if points else "degraded")
    fallback_reason = forecast.get("fallback_reason")
    if requested_model_family.lower() not in {"baseline", "time_series_baseline"}:
        fallback_reason = fallback_reason or "DEEP_MODEL_SHADOW_COMPAT_BASELINE_RESPONSE"

    return {
        "predictions": points,
        "forecast": forecast.get("forecast") or [],
        "forecast_status": forecast_status,
        "series_summary": forecast.get("series_summary") or {},
        "metrics": forecast.get("metrics") or {},
        "model": forecast.get("model"),
        "model_family": forecast.get("model_family") or "time_series_baseline",
        "requested_model_family": requested_model_family,
        "model_stage": forecast.get("model_stage") or "phase3_baseline",
        "provider_status": provider_status,
        "fallback_reason": fallback_reason,
        "data_source": forecast.get("data_source", "shipment_fact"),
        "runtime_profile": profile,
        "runtime_limits": {"limit": limit},
        "boundary": _model_boundary_label(requested_model_family),
        "truth_contract": forecast.get("truth_contract") or {},
    }


def _run_forecast(requested_model_family: str) -> Dict[str, Any]:
    payload = _forecast_payload()
    forecast = get_shipment_prediction_service().forecast_demand(
        days=payload["days"],
        city=payload["city"],
        limit=payload["limit"],
        time_granularity=payload["time_granularity"],
        series_source=payload["series_source"],
    )
    prediction = _prediction_response(
        forecast,
        requested_model_family=requested_model_family,
        profile=payload["runtime_profile"],
        limit=payload["limit"],
    )
    return {
        "success": True,
        "data_source": "shipment_fact",
        "provider_status": prediction["provider_status"],
        "fallback_reason": prediction["fallback_reason"],
        "authenticity_level": forecast.get("authenticity_level", "B"),
        "runtime_profile": payload["runtime_profile"],
        "model_family": prediction["model_family"],
        "model_stage": prediction["model_stage"],
        "data": prediction,
    }


def _alert_from_anomaly(item: Dict[str, Any]) -> Dict[str, Any]:
    level = str(item.get("level") or item.get("severity") or "info").lower()
    if level in {"critical", "high"}:
        ui_level = "critical"
    elif level in {"medium", "warning"}:
        ui_level = "warning"
    else:
        ui_level = "info"
    kind = item.get("type") or item.get("anomaly_type") or item.get("task") or "anomaly"
    source = item.get("shipment_id") or item.get("order_id") or item.get("fact_id")
    detail = item.get("message") or item.get("reason") or item.get("detail") or item.get("explanation")
    message = f"{kind}"
    if source:
        message += f" #{source}"
    if detail:
        message += f": {detail}"
    return {
        "level": ui_level,
        "message": message,
        "type": kind,
        "source_id": source,
        "raw": item,
    }


def _alerts_from_detection(detection: Dict[str, Any], limit: int = 8) -> List[Dict[str, Any]]:
    anomalies = detection.get("anomalies") or []
    alerts = [_alert_from_anomaly(item) for item in anomalies[:limit]]
    if not alerts:
        summary = detection.get("summary") or {}
        records = summary.get("records_scanned", 0)
        alerts.append(
            {
                "level": "info",
                "message": f"已完成 {records} 条真实运单轻量异常扫描，暂未发现高优先级异常。",
                "type": "anomaly_scan",
                "source_id": None,
            }
        )
    return alerts


def _degraded_response(message: str, exc: Exception, *, status_code: int = 200):
    return (
        jsonify(
            {
                "success": False,
                "provider_status": "degraded",
                "fallback_reason": message,
                "error": exc.__class__.__name__,
                "data_source": "shipment_fact",
                "runtime_profile": request.args.get("runtime_profile", "interactive"),
            }
        ),
        status_code,
    )


@advanced_ml_bp.route("/train", methods=["POST"])
def train_models():
    """Create a non-blocking deep-shadow training job over real shipment facts."""
    payload = request.get_json(silent=True) or {}
    profile = _runtime_profile(payload, default="full")
    days = max(1, min(60, _coerce_int(payload.get("days") or payload.get("horizon_days"), 14)))
    job_payload = {
        "task": payload.get("task") or "demand",
        "model_family": payload.get("model_family") or "lstm",
        "runtime_profile": profile,
        "limit": _bounded_limit(payload.get("limit"), profile),
        "horizon_days": days,
        "test_days": max(1, min(days, _coerce_int(payload.get("test_days"), min(days, 14)))),
        "sequence_length": max(3, min(90, _coerce_int(payload.get("sequence_length"), 14))),
    }
    try:
        result = get_shipment_prediction_service().create_prediction_job(
            job_payload,
            app=current_app._get_current_object(),
        )
        result.setdefault("message", "高级模型训练任务已创建，深度模型以 shadow job 方式后台执行。")
        result.setdefault("stats", {"limit": job_payload["limit"], "days": days})
        return jsonify(result), 202 if result.get("success") else 400
    except Exception as exc:
        current_app.logger.exception("advanced-ml train degraded")
        return _degraded_response("ADVANCED_ML_TRAIN_JOB_CREATE_FAILED", exc)


@advanced_ml_bp.route("/predict/lstm", methods=["GET"])
def predict_lstm():
    try:
        return jsonify(_run_forecast("lstm"))
    except Exception as exc:
        current_app.logger.exception("advanced-ml lstm forecast degraded")
        return _degraded_response("ADVANCED_ML_LSTM_COMPAT_FORECAST_FAILED", exc)


@advanced_ml_bp.route("/predict/prophet", methods=["GET"])
def predict_prophet():
    try:
        return jsonify(_run_forecast("prophet"))
    except Exception as exc:
        current_app.logger.exception("advanced-ml prophet forecast degraded")
        return _degraded_response("ADVANCED_ML_PROPHET_COMPAT_FORECAST_FAILED", exc)


@advanced_ml_bp.route("/predict/ensemble", methods=["GET"])
def predict_ensemble():
    try:
        return jsonify(_run_forecast("ensemble"))
    except Exception as exc:
        current_app.logger.exception("advanced-ml ensemble forecast degraded")
        return _degraded_response("ADVANCED_ML_ENSEMBLE_COMPAT_FORECAST_FAILED", exc)


@advanced_ml_bp.route("/predict/with-anomaly", methods=["GET"])
def predict_with_anomaly():
    """Return demand forecast plus a lightweight anomaly scan without 30s page stalls."""
    try:
        forecast_payload = _forecast_payload()
        forecast = get_shipment_prediction_service().forecast_demand(
            days=forecast_payload["days"],
            city=forecast_payload["city"],
            limit=forecast_payload["limit"],
            time_granularity=forecast_payload["time_granularity"],
            series_source=forecast_payload["series_source"],
        )
        prediction = _prediction_response(
            forecast,
            requested_model_family=request.args.get("model_family") or "ensemble",
            profile=forecast_payload["runtime_profile"],
            limit=forecast_payload["limit"],
        )
        anomaly_limit = max(1, min(30, request.args.get("anomaly_limit", 8, type=int)))
        detection = get_shipment_anomaly_service().detect(
            {
                "runtime_profile": forecast_payload["runtime_profile"],
                "limit": min(INTERACTIVE_LIMIT, forecast_payload["limit"]),
                "anomaly_limit": anomaly_limit,
                "use_ml": False,
                "tasks": ["status", "geo", "cost", "eta", "delay", "od_volume", "node_congestion"],
                "city": forecast_payload["city"],
            }
        )
        alerts = _alerts_from_detection(detection, limit=anomaly_limit)
        provider_status = (
            "ok"
            if prediction.get("provider_status") == "ok" and detection.get("provider_status") == "ok"
            else "degraded"
        )
        fallback_reasons = [
            reason
            for reason in [prediction.get("fallback_reason"), detection.get("fallback_reason")]
            if reason
        ]
        return jsonify(
            {
                "success": True,
                "data_source": "shipment_fact",
                "provider_status": provider_status,
                "fallback_reason": ";".join(fallback_reasons) if fallback_reasons else None,
                "authenticity_level": "B" if provider_status == "ok" else "C",
                "runtime_profile": forecast_payload["runtime_profile"],
                "model_family": prediction.get("model_family"),
                "data": {
                    "prediction": prediction,
                    "alerts": alerts,
                    "anomaly": {
                        "summary": detection.get("summary") or {},
                        "provider_status": detection.get("provider_status"),
                        "fallback_reason": detection.get("fallback_reason"),
                        "detector_family": detection.get("detector_family"),
                    },
                    "data_source": "shipment_fact",
                    "runtime_profile": forecast_payload["runtime_profile"],
                    "truth_contract": {
                        "business_mutation": "none",
                        "deep_model_boundary": "LSTM/Transformer/RL remain shadow/background unless readiness gates pass",
                    },
                },
            }
        )
    except Exception as exc:
        current_app.logger.exception("advanced-ml forecast with anomaly degraded")
        return _degraded_response("ADVANCED_ML_FORECAST_WITH_ANOMALY_FAILED", exc)


@advanced_ml_bp.route("/anomaly/detect", methods=["POST", "GET"])
def detect_anomalies():
    payload = request.get_json(silent=True) or {}
    profile = _runtime_profile(payload)
    try:
        detection = get_shipment_anomaly_service().detect(
            {
                **payload,
                "runtime_profile": profile,
                "limit": _bounded_limit(payload.get("limit") or request.args.get("limit", type=int), profile),
                "anomaly_limit": max(
                    1,
                    min(200, _coerce_int(payload.get("anomaly_limit") or request.args.get("anomaly_limit"), 50)),
                ),
                "use_ml": bool(payload.get("use_ml", False)),
            }
        )
        return jsonify(
            {
                "success": True,
                "data_source": "shipment_fact",
                "provider_status": detection.get("provider_status"),
                "fallback_reason": detection.get("fallback_reason"),
                "runtime_profile": profile,
                "data": {
                    **detection,
                    "alerts": _alerts_from_detection(detection, limit=20),
                },
            }
        )
    except Exception as exc:
        current_app.logger.exception("advanced-ml anomaly detect degraded")
        return _degraded_response("ADVANCED_ML_ANOMALY_DETECT_FAILED", exc)


@advanced_ml_bp.route("/predict/by-region", methods=["GET"])
def predict_by_region():
    try:
        return jsonify(_run_forecast(request.args.get("model_family") or "region_baseline"))
    except Exception as exc:
        current_app.logger.exception("advanced-ml region forecast degraded")
        return _degraded_response("ADVANCED_ML_REGION_FORECAST_FAILED", exc)


@advanced_ml_bp.route("/status", methods=["GET"])
def get_status():
    """Return truthful model/readiness state for legacy pages."""
    try:
        model_status = get_shipment_prediction_service().model_status()
        health = get_shipment_prediction_service().dataset_health()
        models = model_status.get("models") or []
        return jsonify(
            {
                "success": True,
                "is_trained": bool(models),
                "data_records": (health.get("summary") or {}).get("total_records", 0),
                "data_source": "shipment_fact",
                "provider_status": model_status.get("provider_status", "degraded"),
                "fallback_reason": model_status.get("fallback_reason"),
                "model_family": model_status.get("model_family"),
                "model_stage": model_status.get("model_stage"),
                "available_models": {
                    "baseline_forecast": True,
                    "lstm": "shadow_job",
                    "gru": "shadow_job",
                    "transformer": "shadow_job",
                    "prophet": "compat_baseline",
                    "anomaly_detector": True,
                },
                "deep_learning_readiness": model_status.get("dataset_readiness") or {},
                "models": models,
                "latest_jobs": model_status.get("latest_jobs") or [],
                "truth_contract": {
                    "business_mutation": "none",
                    "online_model": "time_series_baseline",
                    "deep_models": "background_shadow_until_readiness_passes",
                },
            }
        )
    except Exception as exc:
        current_app.logger.exception("advanced-ml status degraded")
        return _degraded_response("ADVANCED_ML_STATUS_FAILED", exc)


def register_advanced_ml_routes(app):
    """Register Advanced ML compatibility routes."""
    app.register_blueprint(advanced_ml_bp)
