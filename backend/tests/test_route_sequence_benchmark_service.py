import importlib
import os
import sys


PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT in sys.path:
    sys.path.remove(PROJECT_ROOT)
sys.path.insert(0, PROJECT_ROOT)


class _UnavailableGurobi:
    def check(self, run_smoke=False):
        return {
            "available": False,
            "provider_status": "degraded",
            "fallback_reason": "GUROBI_PYTHON_API_UNAVAILABLE",
            "authenticity_level": "C",
            "checks": {
                "install_dir_present": True,
                "cli_available": True,
                "license_file_present": True,
                "python_api_available": False,
                "smoke_status": "not_run",
            },
            "security": {
                "license_contents_returned": False,
                "secret_values_returned": False,
            },
        }


def _build_app(monkeypatch, *, full_graph=True):
    monkeypatch.setenv("DISABLE_ML_ROUTES", "1")
    _clear_logistics_prometheus_collectors()

    for module_name in list(sys.modules):
        if module_name == "app" or module_name.startswith("app."):
            sys.modules.pop(module_name)

    importlib.import_module("app")
    from app import create_app
    from app.models import Node, Route, db

    app = create_app("testing")
    with app.app_context():
        db.drop_all()
        db.create_all()
        db.session.add_all(
            [
                Node(
                    id=1,
                    name="广州仓",
                    type="warehouse",
                    city="广州",
                    longitude=113.2644,
                    latitude=23.1291,
                    status="active",
                ),
                Node(
                    id=2,
                    name="佛山中转",
                    type="distribution_center",
                    city="佛山",
                    longitude=113.1214,
                    latitude=23.0215,
                    status="active",
                ),
                Node(
                    id=3,
                    name="深圳站",
                    type="station",
                    city="深圳",
                    longitude=114.0579,
                    latitude=22.5431,
                    status="active",
                ),
            ]
        )
        routes = [
            Route(
                id=1,
                name="广州-佛山",
                start_node_id=1,
                end_node_id=2,
                distance=28.0,
                duration=0.7,
                toll_cost=10,
                fuel_cost=25,
                status="active",
                route_data=(
                    '{"distance_source":"haversine_corrected",'
                    '"duration_source":"estimated_speed",'
                    '"provider":"local","provider_status":"degraded",'
                    '"fallback_reason":"ROUTE_DISTANCE_BACKFILL_HAVERSINE"}'
                ),
            )
        ]
        if full_graph:
            routes.extend(
                [
                    Route(
                        id=2,
                        name="佛山-深圳",
                        start_node_id=2,
                        end_node_id=3,
                        distance=138.0,
                        duration=2.2,
                        toll_cost=42,
                        fuel_cost=110,
                        status="active",
                        route_data=(
                            '{"distance_source":"amap_driving_route",'
                            '"duration_source":"amap_driving_route",'
                            '"provider":"amap","provider_status":"ok"}'
                        ),
                    ),
                    Route(
                        id=3,
                        name="广州-深圳直达",
                        start_node_id=1,
                        end_node_id=3,
                        distance=162.0,
                        duration=4.0,
                        toll_cost=60,
                        fuel_cost=130,
                        status="active",
                        route_data='{"legacy": true}',
                    ),
                ]
            )
        db.session.add_all(routes)
        db.session.commit()

    return app


def _clear_logistics_prometheus_collectors():
    try:
        from prometheus_client import REGISTRY
    except Exception:
        return

    collector_to_names = getattr(REGISTRY, "_collector_to_names", {})
    for collector, names in list(collector_to_names.items()):
        if any(str(name).startswith("logistics_") for name in names):
            try:
                REGISTRY.unregister(collector)
            except KeyError:
                pass


def test_route_sequence_benchmark_uses_real_route_truth(monkeypatch):
    app = _build_app(monkeypatch, full_graph=True)

    from app.services.route_sequence_benchmark_service import RouteSequenceBenchmarkService

    payload = {
        "depot_id": 1,
        "node_ids": [2, 3],
        "solvers": ["nearest_neighbor", "two_opt", "gurobi", "unknown"],
        "return_to_depot": True,
        "allow_haversine_fallback": False,
        "time_limit": 1,
    }
    with app.app_context():
        service = RouteSequenceBenchmarkService(gurobi_capability_service=_UnavailableGurobi())
        result = service.benchmark(payload)

    assert result["success"] is True
    assert result["benchmark_type"] == "small_route_sequence_solver_comparison"
    assert result["data_source"] == "nodes/routes"
    assert result["distance_source"] == "route_table_mixed_sources"
    assert result["provider_status"] == "degraded"
    assert result["matrix_truth"]["pair_count"] == 6
    assert result["matrix_truth"]["route_graph_pair_count"] == 6
    assert result["matrix_truth"]["haversine_fallback_pair_count"] == 0

    rows = {row["solver"]: row for row in result["results"]}
    assert rows["nearest_neighbor"]["success"] is True
    assert rows["nearest_neighbor"]["feasible"] is True
    assert rows["nearest_neighbor"]["node_sequence"][0] == 1
    assert rows["nearest_neighbor"]["node_sequence"][-1] == 1
    assert rows["two_opt"]["success"] is True
    assert rows["gurobi_tsp_milp"]["success"] is False
    assert rows["gurobi_tsp_milp"]["fallback_reason"] == "GUROBI_PYTHON_API_UNAVAILABLE"
    assert rows["unknown"]["fallback_reason"] == "UNSUPPORTED_ROUTE_SEQUENCE_SOLVER"

    truth = rows["nearest_neighbor"]["route_truth"]
    assert truth["leg_count"] == 3
    assert truth["distance_source_counts"]["amap_driving_route"] >= 1
    assert truth["distance_source_counts"]["haversine_corrected"] >= 1
    assert "route_table_legacy_unknown" in truth["distance_source_counts"]
    assert rows["nearest_neighbor"]["route_legs"][0]["path_node_ids"]
    assert result["rankings"][0]["solver"] in {"nearest_neighbor", "two_opt"}


def test_route_sequence_benchmark_degrades_with_haversine_fallback(monkeypatch):
    app = _build_app(monkeypatch, full_graph=False)

    from app.services.route_sequence_benchmark_service import RouteSequenceBenchmarkService

    payload = {
        "depot_id": 1,
        "node_ids": [2, 3],
        "solvers": ["nearest_neighbor", "two_opt"],
        "return_to_depot": True,
        "allow_haversine_fallback": True,
    }
    with app.app_context():
        result = RouteSequenceBenchmarkService(
            gurobi_capability_service=_UnavailableGurobi()
        ).benchmark(payload)

    assert result["success"] is True
    assert result["provider_status"] == "degraded"
    assert result["matrix_truth"]["haversine_fallback_pair_count"] > 0
    assert "haversine_corrected" in result["matrix_truth"]["distance_source_counts"]
    assert "HAVERSINE_FALLBACK_AFTER" in result["fallback_reason"]
    assert result["results"][0]["success"] is True
    assert result["results"][0]["route_truth"]["missing_segment_count"] > 0


def test_route_sequence_benchmark_real_endpoint_smoke(monkeypatch):
    app = _build_app(monkeypatch, full_graph=True)
    client = app.test_client()

    response = client.post(
        "/api/optimization/route-sequence-benchmark",
        json={
            "depot_id": 1,
            "node_ids": [2, 3],
            "solvers": ["nearest_neighbor", "two_opt"],
            "return_to_depot": True,
            "allow_haversine_fallback": False,
        },
    )
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["success"] is True
    assert payload["benchmark_type"] == "small_route_sequence_solver_comparison"
    assert payload["summary"]["best_solver"] in {"nearest_neighbor", "two_opt"}
    assert payload["results"][0]["route_truth"]["leg_count"] == 3


def test_route_sequence_benchmark_endpoint_contract(monkeypatch):
    monkeypatch.setenv("DISABLE_ML_ROUTES", "1")

    for module_name in list(sys.modules):
        if module_name == "app" or module_name.startswith("app."):
            sys.modules.pop(module_name)

    from flask import Flask
    import app.routes.optimization as optimization_routes

    class FakeRouteSequenceService:
        def demo_payload(self):
            return {"depot_id": 1, "node_ids": [2, 3]}

        def benchmark(self, payload):
            return {
                "success": True,
                "benchmark_type": "small_route_sequence_solver_comparison",
                "solver": "route_sequence_benchmark",
                "summary": {"best_solver": "nearest_neighbor"},
                "results": [],
                "rankings": [],
                "data_source": "nodes/routes",
                "distance_source": "route_table_mixed_sources",
                "path_source": "node_sequence_solver+local_route_graph",
                "provider_status": "ok",
                "fallback_reason": None,
                "authenticity_level": "B/C-route-sequence",
            }

    monkeypatch.setattr(
        optimization_routes,
        "get_route_sequence_benchmark_service",
        lambda: FakeRouteSequenceService(),
    )

    app = Flask(__name__)
    app.register_blueprint(optimization_routes.optimization_bp, url_prefix="/api/optimization")
    client = app.test_client()

    demo_response = client.get("/api/optimization/route-sequence-benchmark-demo")
    post_response = client.post(
        "/api/optimization/route-sequence-benchmark",
        json={"depot_id": 1, "node_ids": [2, 3]},
    )

    assert demo_response.status_code == 200
    assert post_response.status_code == 200
    assert demo_response.get_json()["benchmark_type"] == "small_route_sequence_solver_comparison"
    assert post_response.get_json()["summary"]["best_solver"] == "nearest_neighbor"
