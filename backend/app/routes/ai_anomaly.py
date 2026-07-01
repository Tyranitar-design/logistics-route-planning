"""Real-data AI anomaly detection APIs."""

from flask import Blueprint, jsonify, request

from app.services.shipment_anomaly_service import get_shipment_anomaly_service


ai_anomaly_bp = Blueprint("ai_anomaly", __name__)


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
    result = get_shipment_anomaly_service().detect(payload)
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
    result = get_shipment_anomaly_service().scorecard(payload)
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
