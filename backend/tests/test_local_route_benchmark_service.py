import importlib
import os
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


def _build_client(monkeypatch):
    monkeypatch.setenv("DISABLE_ML_ROUTES", "1")
    _clear_logistics_prometheus_collectors()

    if "app" in sys.modules:
        importlib.reload(sys.modules["app"])
    else:
        importlib.import_module("app")

    from app import create_app
    from app.models import Node, Route, User, db

    app = create_app("testing")
    app.config["JWT_SECRET_KEY"] = "local-route-benchmark-secret"

    with app.app_context():
        db.create_all()

        user = User(username="admin", real_name="管理员", role="admin", status="active")
        user.password = "admin123"
        db.session.add(user)
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
                Node(
                    id=4,
                    name="缺坐标点",
                    type="station",
                    city="未知",
                    longitude=None,
                    latitude=None,
                    status="active",
                ),
            ]
        )
        db.session.add_all(
            [
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
                ),
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
        db.session.commit()

    client = app.test_client()
    login_response = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "admin123"},
    )
    token = login_response.get_json()["access_token"]
    return app, client, {"Authorization": f"Bearer {token}"}


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


def test_local_route_benchmark_returns_multiple_local_strategies(monkeypatch):
    app, _, _ = _build_client(monkeypatch)

    from app.services.local_route_benchmark_service import LocalRouteBenchmarkService

    with app.app_context():
        result = LocalRouteBenchmarkService().benchmark(1, 3, include_provider=False)

    assert result["success"] is True
    assert result["data_source"] == "nodes/routes"
    assert result["distance_source"] == "local_graph_only"
    assert result["authenticity_level"] == "C-local-graph-benchmark"
    assert result["summary"]["local_strategy_count"] >= 6
    assert result["summary"]["successful_local_strategies"] >= 6
    assert result["summary"]["best_local_strategy"] in {
        candidate["strategy_id"] for candidate in result["local_strategies"]
    }
    assert {candidate["algorithm"] for candidate in result["local_strategies"]} >= {"Dijkstra", "A*"}


def test_local_route_benchmark_attaches_provider_deltas(monkeypatch):
    app, _, _ = _build_client(monkeypatch)

    import app.services.local_route_benchmark_service as benchmark_module
    from app.services.local_route_benchmark_service import LocalRouteBenchmarkService

    class FakeAmapService:
        def multi_route(self, origin, destination):
            return {
                "success": True,
                "routes": [
                    {
                        "distance": 158000,
                        "duration": 9000,
                        "distance_km": 158.0,
                        "duration_minutes": 150.0,
                        "provider": "amap",
                        "provider_status": "ok",
                        "degraded": False,
                        "polyline": [[origin[0], origin[1]], [destination[0], destination[1]]],
                    }
                ],
                "provider": "amap",
                "provider_status": "ok",
                "degraded": False,
            }

    monkeypatch.setattr(benchmark_module, "get_amap_service", lambda: FakeAmapService())

    with app.app_context():
        result = LocalRouteBenchmarkService().benchmark(1, 3, include_provider=True)

    assert result["success"] is True
    assert result["provider_status"] == "ok"
    assert result["distance_source"] == "local_graph_vs_amap"
    assert result["provider_route"]["distance_source"] == "amap"
    assert result["summary"]["provider_available"] is True
    assert any(
        candidate["comparison_to_provider"]["comparable"]
        for candidate in result["local_strategies"]
        if candidate["success"]
    )


def test_local_route_benchmark_compares_amap_and_tianditu(monkeypatch):
    app, _, _ = _build_client(monkeypatch)

    import app.services.local_route_benchmark_service as benchmark_module
    from app.services.local_route_benchmark_service import LocalRouteBenchmarkService

    class FakeAmapService:
        def multi_route(self, origin, destination):
            return {
                "success": True,
                "routes": [
                    {
                        "distance": 158000,
                        "duration": 9000,
                        "distance_km": 158.0,
                        "duration_minutes": 150.0,
                        "provider": "amap",
                        "provider_status": "ok",
                        "degraded": False,
                        "polyline": [[origin[0], origin[1]], [destination[0], destination[1]]],
                    }
                ],
                "provider": "amap",
                "provider_status": "ok",
                "degraded": False,
            }

    class FakeTiandituService:
        def get_route_for_frontend(self, origin, destination, strategy):
            return {
                "success": True,
                "source": "tianditu",
                "distance_km": 164.5,
                "duration_minutes": 162.0,
                "polyline": [[origin[0], origin[1]], [destination[0], destination[1]]],
                "provider": "tianditu",
                "provider_status": "ok",
                "degraded": False,
                "fallback_reason": None,
            }

    monkeypatch.setattr(benchmark_module, "get_amap_service", lambda: FakeAmapService())
    monkeypatch.setattr(benchmark_module, "get_tianditu_service", lambda: FakeTiandituService())

    with app.app_context():
        result = LocalRouteBenchmarkService().benchmark(
            1,
            3,
            include_provider=True,
            provider_sources=["amap", "tianditu"],
        )

    assert result["success"] is True
    assert result["provider_status"] == "ok"
    assert result["distance_source"] == "local_graph_vs_amap_tianditu"
    assert result["summary"]["provider_count"] == 2
    assert result["summary"]["provider_available_count"] == 2
    assert {route["provider"] for route in result["provider_routes"]} == {"amap", "tianditu"}
    first_success = next(candidate for candidate in result["local_strategies"] if candidate["success"])
    assert set(first_success["comparison_to_providers"].keys()) == {"amap", "tianditu"}
    assert first_success["comparison_to_provider"]["provider"] == "amap"


def test_local_route_benchmark_reports_local_route_distance_sources(monkeypatch):
    app, _, _ = _build_client(monkeypatch)

    from app.services.local_route_benchmark_service import LocalRouteBenchmarkService

    with app.app_context():
        result = LocalRouteBenchmarkService().benchmark(1, 3, include_provider=False)

    assert result["success"] is True
    local_by_strategy = {candidate["strategy_id"]: candidate for candidate in result["local_strategies"]}

    distance_strategy = local_by_strategy["dijkstra_distance"]
    assert distance_strategy["route_truth"]["segment_count"] == 1
    assert distance_strategy["route_truth"]["distance_source_counts"] == {
        "route_table_legacy_unknown": 1
    }
    assert distance_strategy["route_segments"][0]["route_id"] == 3

    time_strategy = local_by_strategy["dijkstra_time"]
    assert time_strategy["route_truth"]["segment_count"] == 2
    assert time_strategy["route_truth"]["distance_source_counts"] == {
        "haversine_corrected": 1,
        "amap_driving_route": 1,
    }
    assert time_strategy["route_truth"]["provider_status_counts"] == {
        "degraded": 1,
        "ok": 1,
    }
    assert result["summary"]["local_distance_source_counts"]["amap_driving_route"] >= 1
    assert result["summary"]["local_distance_source_counts"]["haversine_corrected"] >= 1


def test_local_route_benchmark_marks_partial_provider_degradation(monkeypatch):
    app, _, _ = _build_client(monkeypatch)

    import app.services.local_route_benchmark_service as benchmark_module
    from app.services.local_route_benchmark_service import LocalRouteBenchmarkService

    class FakeAmapService:
        def multi_route(self, origin, destination):
            return {
                "success": True,
                "routes": [
                    {
                        "distance_km": 158.0,
                        "duration_minutes": 150.0,
                        "provider": "amap",
                        "provider_status": "ok",
                        "degraded": False,
                    }
                ],
                "provider": "amap",
                "provider_status": "ok",
                "degraded": False,
            }

    class BrokenTiandituService:
        def get_route_for_frontend(self, origin, destination, strategy):
            return {
                "success": False,
                "provider": "tianditu",
                "provider_status": "unavailable",
                "fallback_reason": "TIANDITU_KEY_MISSING",
                "error": "TIANDITU_KEY_MISSING",
            }

    monkeypatch.setattr(benchmark_module, "get_amap_service", lambda: FakeAmapService())
    monkeypatch.setattr(benchmark_module, "get_tianditu_service", lambda: BrokenTiandituService())

    with app.app_context():
        result = LocalRouteBenchmarkService().benchmark(
            1,
            3,
            include_provider=True,
            provider_sources=["amap", "tianditu"],
        )

    assert result["success"] is True
    assert result["provider_status"] == "degraded"
    assert result["summary"]["provider_available_count"] == 1
    assert result["provider_route"]["provider"] == "amap"
    assert result["provider_errors"]["tianditu"] == "TIANDITU_KEY_MISSING"
    assert "PARTIAL_PROVIDER_DEGRADATION" in result["fallback_reason"]


def test_local_route_benchmark_degrades_when_provider_fails(monkeypatch):
    app, _, _ = _build_client(monkeypatch)

    import app.services.local_route_benchmark_service as benchmark_module
    from app.services.local_route_benchmark_service import LocalRouteBenchmarkService

    class BrokenAmapService:
        def multi_route(self, origin, destination):
            raise RuntimeError("provider dns timeout")

    monkeypatch.setattr(benchmark_module, "get_amap_service", lambda: BrokenAmapService())

    with app.app_context():
        result = LocalRouteBenchmarkService().benchmark(1, 3, include_provider=True)

    assert result["success"] is True
    assert result["provider_status"] == "degraded"
    assert result["provider_route"] is None
    assert "provider dns timeout" in result["fallback_reason"]
    assert result["summary"]["successful_local_strategies"] >= 1


def test_local_route_benchmark_endpoint_requires_valid_od(monkeypatch):
    _, client, headers = _build_client(monkeypatch)

    missing_response = client.post(
        "/api/amap/route/local-benchmark",
        headers=headers,
        json={"origin_id": 1},
    )
    missing_payload = missing_response.get_json()

    invalid_response = client.post(
        "/api/amap/route/local-benchmark",
        headers=headers,
        json={"origin_id": 1, "destination_id": 4, "include_provider": False},
    )
    invalid_payload = invalid_response.get_json()

    assert missing_response.status_code == 400
    assert missing_payload["success"] is False
    assert invalid_response.status_code == 400
    assert invalid_payload["success"] is False
    assert invalid_payload["fallback_reason"] == "DESTINATION_COORDINATES_MISSING"


def test_local_route_benchmark_endpoint_returns_contract(monkeypatch):
    _, client, headers = _build_client(monkeypatch)

    response = client.post(
        "/api/amap/route/local-benchmark",
        headers=headers,
        json={"origin_id": 1, "destination_id": 3, "include_provider": False},
    )
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["success"] is True
    assert payload["origin"]["id"] == 1
    assert payload["destination"]["id"] == 3
    assert payload["provider_route"] is None
    assert payload["path_source"] == "local_route_graph"
    assert payload["summary"]["successful_local_strategies"] >= 1
    assert payload["local_strategies"][0]["distance_source"] == "local_graph"
