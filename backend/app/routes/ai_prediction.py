"""Real-data AI prediction baseline APIs."""

from flask import Blueprint, jsonify, request

from app.services.shipment_prediction_service import get_shipment_prediction_service


ai_prediction_bp = Blueprint("ai_prediction", __name__)


@ai_prediction_bp.route("/health", methods=["GET"])
@ai_prediction_bp.route("/dataset-health", methods=["GET"])
def prediction_dataset_health():
    """Return real shipment-fact prediction dataset readiness."""
    result = get_shipment_prediction_service().dataset_health()
    return jsonify(result)


@ai_prediction_bp.route("/baseline/evaluate", methods=["POST"])
def evaluate_prediction_baselines():
    """
    Evaluate Phase 3 explainable baselines.

    Request Body:
        {
            "tasks": ["demand", "eta", "delay", "cost"],
            "horizon_days": 7,
            "limit": 50000,
            "city": "上海"
        }
    """
    payload = request.get_json(silent=True) or {}
    result = get_shipment_prediction_service().evaluate_baselines(payload)
    status_code = 200 if result.get("success") else 400
    return jsonify(result), status_code


@ai_prediction_bp.route("/demand/forecast", methods=["GET"])
def forecast_demand():
    """Forecast daily demand from historical shipment_facts."""
    days = request.args.get("days", 7, type=int)
    city = request.args.get("city") or request.args.get("destination_city")
    limit = request.args.get("limit", 50000, type=int)
    result = get_shipment_prediction_service().forecast_demand(days=days, city=city, limit=limit)
    status_code = 200 if result.get("success") else 400
    return jsonify(result), status_code


@ai_prediction_bp.route("/time-series/benchmark", methods=["GET", "POST"])
@ai_prediction_bp.route("/time-series-benchmark", methods=["GET", "POST"])
def prediction_time_series_benchmark():
    """
    Compare real-data time-series baselines and report LSTM/TFT readiness.

    Query/Body:
        task: demand | eta | delay | cost
        horizon_days: forecast horizon
        test_days: backtest holdout days
        sequence_length: sequence window for LSTM/TFT readiness
        limit: maximum source facts to scan
        city: optional city filter
    """
    if request.method == "POST":
        payload = request.get_json(silent=True) or {}
    else:
        payload = {
            "task": request.args.get("task", "demand"),
            "horizon_days": request.args.get("horizon_days", 14, type=int),
            "test_days": request.args.get("test_days", 14, type=int),
            "sequence_length": request.args.get("sequence_length", 14, type=int),
            "limit": request.args.get("limit", 50000, type=int),
            "city": request.args.get("city") or request.args.get("destination_city"),
        }
    result = get_shipment_prediction_service().evaluate_time_series_benchmark(payload)
    status_code = 200 if result.get("success") else 400
    return jsonify(result), status_code


@ai_prediction_bp.route("/capacity-gap/forecast", methods=["GET", "POST"])
@ai_prediction_bp.route("/capacity-gap-forecast", methods=["GET", "POST"])
def prediction_capacity_gap_forecast():
    """
    Forecast shipment weight/volume demand against vehicle capacity.

    Query/Body:
        horizon_days: forecast horizon
        test_days: baseline backtest holdout days
        sequence_length: sequence window for LSTM/TFT readiness
        limit: maximum source facts to scan
        city: optional city filter
        include_all_vehicles: include non-available vehicles when true
    """
    if request.method == "POST":
        payload = request.get_json(silent=True) or {}
    else:
        payload = {
            "horizon_days": request.args.get("horizon_days", 14, type=int),
            "test_days": request.args.get("test_days", 14, type=int),
            "sequence_length": request.args.get("sequence_length", 14, type=int),
            "limit": request.args.get("limit", 50000, type=int),
            "city": request.args.get("city") or request.args.get("destination_city"),
            "include_all_vehicles": request.args.get("include_all_vehicles", "false").lower() in ("1", "true", "yes"),
        }
    result = get_shipment_prediction_service().forecast_capacity_gap(payload)
    status_code = 200 if result.get("success") else 400
    return jsonify(result), status_code


@ai_prediction_bp.route("/cost-volatility/forecast", methods=["GET", "POST"])
@ai_prediction_bp.route("/cost-volatility-forecast", methods=["GET", "POST"])
def prediction_cost_volatility_forecast():
    """
    Forecast cost pressure and volatility from real shipment_facts freight.

    Query/Body:
        horizon_days: forecast horizon
        test_days: baseline backtest holdout days
        sequence_length: sequence window for LSTM/TFT readiness
        volatility_window: rolling window for unit-cost volatility
        limit: maximum source facts to scan
        city: optional city filter
    """
    if request.method == "POST":
        payload = request.get_json(silent=True) or {}
    else:
        payload = {
            "horizon_days": request.args.get("horizon_days", 14, type=int),
            "test_days": request.args.get("test_days", 14, type=int),
            "sequence_length": request.args.get("sequence_length", 14, type=int),
            "volatility_window": request.args.get("volatility_window", 7, type=int),
            "limit": request.args.get("limit", 50000, type=int),
            "city": request.args.get("city") or request.args.get("destination_city"),
        }
    result = get_shipment_prediction_service().forecast_cost_volatility(payload)
    status_code = 200 if result.get("success") else 400
    return jsonify(result), status_code


@ai_prediction_bp.route("/scorecard", methods=["GET", "POST"])
@ai_prediction_bp.route("/readiness-scorecard", methods=["GET", "POST"])
def prediction_readiness_scorecard():
    """
    Aggregate prediction readiness into one scorecard for the decision console.

    Query/Body:
        horizon_days: forecast horizon
        test_days: baseline backtest holdout days
        sequence_length: sequence window for LSTM/TFT readiness
        limit: maximum source facts to scan
        city: optional city filter
    """
    if request.method == "POST":
        payload = request.get_json(silent=True) or {}
    else:
        payload = {
            "horizon_days": request.args.get("horizon_days", 14, type=int),
            "test_days": request.args.get("test_days", 14, type=int),
            "sequence_length": request.args.get("sequence_length", 14, type=int),
            "limit": request.args.get("limit", 50000, type=int),
            "city": request.args.get("city") or request.args.get("destination_city"),
        }
    result = get_shipment_prediction_service().prediction_scorecard(payload)
    status_code = 200 if result.get("success") else 400
    return jsonify(result), status_code


@ai_prediction_bp.route("/dataset/preview", methods=["GET"])
def prediction_dataset_preview():
    """Preview the fact-derived rows used for one prediction target."""
    task = request.args.get("task", "eta")
    limit = request.args.get("limit", 10, type=int)
    result = get_shipment_prediction_service().dataset_preview(task=task, limit=limit)
    status_code = 200 if result.get("success") else 400
    return jsonify(result), status_code


@ai_prediction_bp.route("/features/dataset", methods=["GET", "POST"])
@ai_prediction_bp.route("/training-dataset", methods=["GET", "POST"])
def prediction_feature_dataset():
    """
    Return model-ready shipment-fact feature rows and target definitions.

    Query/Body:
        task: demand | eta | delay | cost
        limit: maximum source facts to scan
        row_limit: maximum rows returned in this API response
        city: optional demand city filter
    """
    if request.method == "POST":
        payload = request.get_json(silent=True) or {}
    else:
        payload = {
            "task": request.args.get("task", "eta"),
            "limit": request.args.get("limit", 50000, type=int),
            "row_limit": request.args.get("row_limit", 100, type=int),
            "city": request.args.get("city") or request.args.get("destination_city"),
        }
    result = get_shipment_prediction_service().build_feature_dataset(payload)
    status_code = 200 if result.get("success") else 400
    return jsonify(result), status_code


@ai_prediction_bp.route("/model/status", methods=["GET"])
def prediction_model_status():
    """Return lightweight model registry status for Phase 3 training APIs."""
    result = get_shipment_prediction_service().model_status()
    return jsonify(result)


@ai_prediction_bp.route("/model/train", methods=["POST"])
def train_prediction_model():
    """
    Train a lightweight real-data model in process memory.

    Request Body:
        {
            "task": "eta",
            "limit": 50000,
            "test_ratio": 0.25,
            "hash_buckets": 24,
            "alpha": 1.0,
            "city": "上海"
        }
    """
    payload = request.get_json(silent=True) or {}
    result = get_shipment_prediction_service().train_model(payload)
    status_code = 200 if result.get("success") else 400
    return jsonify(result), status_code


@ai_prediction_bp.route("/model/evaluate", methods=["POST"])
def evaluate_prediction_model():
    """
    Evaluate a cached model on current shipment-fact feature rows.

    Request Body:
        {
            "task": "eta",
            "model_id": "optional",
            "limit": 50000,
            "row_limit": 20
        }
    """
    payload = request.get_json(silent=True) or {}
    result = get_shipment_prediction_service().evaluate_model(payload)
    status_code = 200 if result.get("success") else 400
    return jsonify(result), status_code


@ai_prediction_bp.route("/model/predict", methods=["POST"])
def predict_with_prediction_model():
    """
    Return cached-model predictions without mutating logistics facts.

    Request Body:
        {
            "task": "eta",
            "model_id": "optional",
            "limit": 50000,
            "row_limit": 20
        }
    """
    payload = request.get_json(silent=True) or {}
    result = get_shipment_prediction_service().predict_with_model(payload)
    status_code = 200 if result.get("success") else 400
    return jsonify(result), status_code


def register_ai_prediction_routes(app):
    """Register real-data AI prediction routes."""
    app.register_blueprint(ai_prediction_bp, url_prefix="/api/ai-prediction")
