"""Real-data AI anomaly detection APIs."""

from flask import Blueprint, jsonify, request

from app.services.shipment_anomaly_service import get_shipment_anomaly_service


ai_anomaly_bp = Blueprint("ai_anomaly", __name__)

INTERACTIVE_LIMIT = 5000
INTERACTIVE_ANOMALY_LIMIT = 80
FULL_LIMIT = 50000


def _runtime_profile(payload: dict | None = None, default: str = "interactive") -> str:
    value = (payload or {}).get("runtime_profile") or request.args.get("runtime_profile") or default
    return "full" if str(value).lower() == "full" else "interactive"


def _coerce_int(value, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _coerce_bool(value, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _apply_runtime_profile(payload: dict | None = None, default: str = "interactive") -> dict:
    payload = dict(payload or {})
    profile = _runtime_profile(payload, default=default)
    max_limit = FULL_LIMIT if profile == "full" else INTERACTIVE_LIMIT
    fallback_limit = FULL_LIMIT if profile == "full" else INTERACTIVE_LIMIT
    payload["runtime_profile"] = profile
    payload["limit"] = max(1, min(max_limit, _coerce_int(payload.get("limit"), fallback_limit)))
    payload["anomaly_limit"] = max(
        1,
        min(INTERACTIVE_ANOMALY_LIMIT if profile == "interactive" else 500, _coerce_int(payload.get("anomaly_limit"), 100)),
    )
    if profile == "interactive":
        payload["use_ml"] = False
        tasks = payload.get("tasks")
        if not tasks:
            payload["tasks"] = ["status", "geo", "cost", "eta", "delay", "od_volume", "node_congestion"]
        elif isinstance(tasks, str):
            payload["tasks"] = ",".join([item for item in tasks.split(",") if item.strip().lower() != "ml"])
        elif isinstance(tasks, (list, tuple)):
            payload["tasks"] = [item for item in tasks if str(item).lower() != "ml"]
    else:
        payload["use_ml"] = _coerce_bool(payload.get("use_ml"), default=True)
    return payload


def _attach_runtime_profile(result: dict, payload: dict) -> dict:
    if isinstance(result, dict):
        result.setdefault("runtime_profile", payload.get("runtime_profile", "interactive"))
        result.setdefault(
            "runtime_limits",
            {
                "limit": payload.get("limit"),
                "anomaly_limit": payload.get("anomaly_limit"),
                "use_ml": payload.get("use_ml"),
            },
        )
    return result


@ai_anomaly_bp.route("/health", methods=["GET"])
@ai_anomaly_bp.route("/dataset-health", methods=["GET"])
def anomaly_dataset_health():
    """Return real shipment-fact anomaly-detection readiness."""
    result = get_shipment_anomaly_service().health()
    return jsonify(result)


@ai_anomaly_bp.route("/detect", methods=["GET", "POST"])
def detect_shipment_anomalies():
    """
    Detect explainable anomalies from real shipment_facts.

    Query/Body:
        tasks: status,geo,cost,eta,delay,od_volume,node_congestion,ml
        limit: maximum source facts to scan
        anomaly_limit: maximum anomalies returned
        city: optional origin/destination city filter
        use_ml: whether to use optional IsolationForest if available
    """
    if request.method == "POST":
        payload = request.get_json(silent=True) or {}
    else:
        payload = {
            "tasks": request.args.get("tasks"),
            "limit": request.args.get("limit", 50000, type=int),
            "anomaly_limit": request.args.get("anomaly_limit", 100, type=int),
            "city": request.args.get("city") or request.args.get("destination_city"),
            "use_ml": request.args.get("use_ml"),
        }
    payload = _apply_runtime_profile(payload)
    result = get_shipment_anomaly_service().detect(payload)
    result = _attach_runtime_profile(result, payload)
    status_code = 200 if result.get("success") else 400
    return jsonify(result), status_code


@ai_anomaly_bp.route("/scorecard", methods=["GET", "POST"])
@ai_anomaly_bp.route("/readiness-scorecard", methods=["GET", "POST"])
def anomaly_readiness_scorecard():
    """
    Aggregate anomaly detection readiness and risk pressure.

    Query/Body:
        tasks: status,geo,cost,eta,delay,od_volume,node_congestion,ml
        limit: maximum source facts to scan
        anomaly_limit: maximum anomalies returned into the scorecard evidence
        use_ml: whether to include optional IsolationForest signal
    """
    if request.method == "POST":
        payload = request.get_json(silent=True) or {}
    else:
        payload = {
            "tasks": request.args.get("tasks"),
            "limit": request.args.get("limit", 50000, type=int),
            "anomaly_limit": request.args.get("anomaly_limit", 100, type=int),
            "use_ml": request.args.get("use_ml"),
        }
    payload = _apply_runtime_profile(payload)
    result = get_shipment_anomaly_service().scorecard(payload)
    result = _attach_runtime_profile(result, payload)
    status_code = 200 if result.get("success") else 400
    return jsonify(result), status_code


@ai_anomaly_bp.route("/explain", methods=["GET", "POST"])
def explain_shipment_anomaly():
    """Explain anomaly signals for one shipment/order identifier."""
    if request.method == "POST":
        payload = request.get_json(silent=True) or {}
    else:
        payload = {
            "id": request.args.get("id"),
            "order_id": request.args.get("order_id"),
            "shipment_id": request.args.get("shipment_id"),
        }
    result = get_shipment_anomaly_service().explain(payload)
    status_code = 200 if result.get("success") else 400
    return jsonify(result), status_code


def register_ai_anomaly_routes(app):
    """Register real-data AI anomaly detection routes."""
    app.register_blueprint(ai_anomaly_bp, url_prefix="/api/ai-anomaly")
