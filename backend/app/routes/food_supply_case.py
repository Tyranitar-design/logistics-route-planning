"""Food supply-chain case study API routes."""

from __future__ import annotations

from flask import Blueprint, jsonify, request

from app.services.food_supply_case_service import get_food_supply_case_service


food_supply_case_bp = Blueprint("food_supply_case", __name__)


@food_supply_case_bp.route("/summary", methods=["GET"])
def food_supply_summary():
    return jsonify(get_food_supply_case_service().summary())


@food_supply_case_bp.route("/import/validate", methods=["POST"])
def food_supply_import_validate():
    return jsonify(get_food_supply_case_service().validate_import())


@food_supply_case_bp.route("/import/apply", methods=["POST"])
def food_supply_import_apply():
    payload = request.get_json(silent=True) or {}
    return jsonify(get_food_supply_case_service().apply_import(persist=bool(payload.get("persist"))))


@food_supply_case_bp.route("/network", methods=["GET"])
def food_supply_network():
    return jsonify(get_food_supply_case_service().network())


@food_supply_case_bp.route("/distance-matrix/build", methods=["POST"])
def food_supply_distance_matrix():
    payload = request.get_json(silent=True) or {}
    try:
        limit = int(payload.get("limit") or 80)
    except (TypeError, ValueError):
        limit = 80
    return jsonify(
        get_food_supply_case_service().build_distance_matrix(
            limit=limit,
            matrix_mode=str(payload.get("matrix_mode") or payload.get("provider") or "haversine"),
            persist=bool(payload.get("persist")),
        )
    )


@food_supply_case_bp.route("/osm-cache/status", methods=["GET"])
def food_supply_osm_cache_status():
    return jsonify(get_food_supply_case_service().osm_cache_status())


@food_supply_case_bp.route("/osm-cache/build", methods=["POST"])
def food_supply_osm_cache_build():
    payload = request.get_json(silent=True) or {}
    return jsonify(get_food_supply_case_service().build_osm_cache(payload))


@food_supply_case_bp.route("/routes/preview", methods=["POST"])
def food_supply_route_preview():
    payload = request.get_json(silent=True) or {}
    return jsonify(get_food_supply_case_service().preview_route(payload))


@food_supply_case_bp.route("/routes/compare", methods=["POST"])
def food_supply_route_compare():
    payload = request.get_json(silent=True) or {}
    return jsonify(get_food_supply_case_service().compare_routes(payload))


@food_supply_case_bp.route("/routes/compare/history", methods=["GET"])
def food_supply_route_compare_history():
    payload = {
        "limit": request.args.get("limit"),
        "source_code": request.args.get("source_code"),
        "target_code": request.args.get("target_code"),
    }
    return jsonify(get_food_supply_case_service().route_compare_history(payload))


@food_supply_case_bp.route("/optimize/network-design", methods=["POST"])
def food_supply_network_design():
    payload = request.get_json(silent=True) or {}
    return jsonify(get_food_supply_case_service().optimize_network_design(payload))


@food_supply_case_bp.route("/optimize/dispatch", methods=["POST"])
def food_supply_dispatch():
    payload = request.get_json(silent=True) or {}
    return jsonify(get_food_supply_case_service().optimize_dispatch(payload))


@food_supply_case_bp.route("/optimize/pareto", methods=["POST"])
def food_supply_pareto():
    payload = request.get_json(silent=True) or {}
    return jsonify(get_food_supply_case_service().optimize_pareto(payload))


@food_supply_case_bp.route("/optimize/solver-compare", methods=["POST"])
def food_supply_solver_compare():
    payload = request.get_json(silent=True) or {}
    return jsonify(get_food_supply_case_service().compare_solvers(payload))


@food_supply_case_bp.route("/scenarios", methods=["GET", "POST"])
def food_supply_scenarios():
    if request.method == "GET":
        return jsonify(get_food_supply_case_service().list_scenarios({"limit": request.args.get("limit")}))
    payload = request.get_json(silent=True) or {}
    return jsonify(get_food_supply_case_service().create_scenario(payload))


@food_supply_case_bp.route("/scenarios/compare", methods=["POST"])
def food_supply_scenarios_compare():
    payload = request.get_json(silent=True) or {}
    return jsonify(get_food_supply_case_service().compare_scenarios(payload))


@food_supply_case_bp.route("/trace/issue", methods=["POST"])
def food_supply_trace_issue():
    payload = request.get_json(silent=True) or {}
    return jsonify(get_food_supply_case_service().trace_issue(payload))


@food_supply_case_bp.route("/trace/<trace_code>", methods=["GET"])
def food_supply_trace_lookup(trace_code):
    return jsonify(get_food_supply_case_service().trace_lookup(trace_code))


@food_supply_case_bp.route("/agent/explain", methods=["POST"])
def food_supply_agent_explain():
    payload = request.get_json(silent=True) or {}
    return jsonify(get_food_supply_case_service().agent_explain(payload))


@food_supply_case_bp.route("/orchards/timeseries", methods=["GET"])
def food_supply_orchard_timeseries():
    return jsonify(get_food_supply_case_service().orchard_timeseries({}))


@food_supply_case_bp.route("/orchards/forecast", methods=["GET"])
def food_supply_orchard_forecast():
    payload = {
        "horizon": request.args.get("horizon"),
        "freshness_days": request.args.get("freshness_days"),
        "use_ml": request.args.get("use_ml") in ("1", "true", "True"),
        "use_optuna": request.args.get("use_optuna") in ("1", "true", "True"),
    }
    return jsonify(get_food_supply_case_service().orchard_forecast(payload))


@food_supply_case_bp.route("/c2c/clusters", methods=["GET"])
def food_supply_c2c_clusters():
    payload = {"cluster_limit": request.args.get("cluster_limit")}
    return jsonify(get_food_supply_case_service().c2c_clusters(payload))


@food_supply_case_bp.route("/c2c/geocode", methods=["POST"])
def food_supply_c2c_geocode():
    payload = request.get_json(silent=True) or {}
    return jsonify(get_food_supply_case_service().geocode_c2c_addresses(payload))


@food_supply_case_bp.route("/c2c/geocode/status", methods=["GET"])
def food_supply_c2c_geocode_status():
    return jsonify(get_food_supply_case_service().c2c_geocode_status())


@food_supply_case_bp.route("/c2c/geocode-regions", methods=["POST"])
def food_supply_c2c_geocode_regions():
    payload = request.get_json(silent=True) or {}
    return jsonify(get_food_supply_case_service().geocode_case_regions(payload))


@food_supply_case_bp.route("/business-kpi", methods=["GET"])
def food_supply_business_kpi():
    return jsonify(get_food_supply_case_service().business_kpi())


@food_supply_case_bp.route("/optimize/last-mile", methods=["POST"])
def food_supply_last_mile():
    payload = request.get_json(silent=True) or {}
    return jsonify(get_food_supply_case_service().optimize_last_mile(payload))


@food_supply_case_bp.route("/optimize/multimodal", methods=["POST"])
def food_supply_multimodal():
    payload = request.get_json(silent=True) or {}
    return jsonify(get_food_supply_case_service().optimize_multimodal(payload))


@food_supply_case_bp.route("/optimize/dispatch-fresh", methods=["POST"])
def food_supply_dispatch_fresh():
    payload = request.get_json(silent=True) or {}
    return jsonify(get_food_supply_case_service().optimize_dispatch_fresh(payload))
