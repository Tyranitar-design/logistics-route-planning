import importlib
import os
import sys


PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


def _build_client(monkeypatch):
    monkeypatch.setenv("DISABLE_ML_ROUTES", "1")

    if "app" in sys.modules:
        importlib.reload(sys.modules["app"])
    else:
        importlib.import_module("app")

    from app import create_app, db
    from app.models import Node, User

    app = create_app("testing")
    app.config["JWT_SECRET_KEY"] = "multi-objective-optimize-od-secret"

    with app.app_context():
        db.create_all()

        user = User(username="admin", real_name="管理员", role="admin", status="active")
        user.password = "admin123"
        db.session.add(user)

        db.session.add(
            Node(
                name="北京仓库",
                type="warehouse",
                city="北京",
                province="北京",
                longitude=116.4074,
                latitude=39.9042,
                status="active",
            )
        )
        db.session.add(
            Node(
                name="澳门特别行政区物流节点",
                type="station",
                city="澳门",
                province="澳门",
                longitude=113.5439,
                latitude=22.1987,
                status="active",
            )
        )
        db.session.commit()

    client = app.test_client()
    login_response = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "admin123"},
    )
    token = login_response.get_json()["access_token"]
    return client, {"Authorization": f"Bearer {token}"}


def _payload(algorithm):
    return {
        "origin_id": 1,
        "destination_id": 2,
        "algorithm": algorithm,
        "weights": {
            "distance": 0.25,
            "time": 0.30,
            "cost": 0.20,
            "traffic": 0.15,
            "weather_risk": 0.10,
        },
    }


def _assert_recommendation_explanation_contract(item, payload):
    assert item["recommendation_reason"]
    assert item["recommendation_reason_source"] == "backend_multi_objective_governance"
    assert item["selection_metrics"]["candidate_count"] == payload["candidate_generation"]["candidate_count"]
    assert item["selection_metrics"]["front_quality"] == payload["front_quality"]
    assert item["selection_metrics"]["distance_source"] == payload["distance_source"]
    assert item["selection_metrics"]["path_source"] == payload["path_source"]
    assert item["selection_metrics"]["authenticity_level"] == payload["authenticity_level"]
    assert isinstance(item["selection_metrics"]["objective_ranks"], dict)
    assert item["selection_metrics"]["best_objectives"]
    assert isinstance(item["tradeoff_summary"]["strengths"], list)
    assert isinstance(item["tradeoff_summary"]["compromises"], list)


def test_optimize_modes_use_specified_od_truth_when_graph_has_no_route(monkeypatch):
    client, headers = _build_client(monkeypatch)

    for algorithm in ["all", "weighted_sum", "pareto"]:
        response = client.post(
            "/api/multi-objective/optimize",
            headers=headers,
            json=_payload(algorithm),
        )

        assert response.status_code == 200, response.get_json()
        payload = response.get_json()
        first = payload["recommendations"][0]

        assert payload["success"] is True
        assert first["objectives"]["distance"] > 1000
        assert first["objectives"]["distance"] < 5000
        assert len(first["path"]) == 2
        assert payload["distance_source"] == "precise_distance_provider"
        assert payload["path_source"] == "specified_origin_destination"
        assert payload["authenticity_level"] in {"B", "C"}
        assert payload["distance_cache_stats"]["total_pairs"] > 0
        assert "amap_attempted_pairs" in payload["distance_cache_stats"]
        assert first["distance_source"] == "precise_distance_provider"
        assert first["path_source"] == "specified_origin_destination"
        assert first["distance_cache_stats"]["total_pairs"] > 0
        _assert_recommendation_explanation_contract(first, payload)

        if payload["authenticity_level"] == "C":
            assert payload["fallback_reason"]

        if algorithm in {"all", "pareto"}:
            assert payload["front_quality"] == "single_solution_projection"


def test_weighted_sum_raises_authenticity_when_driving_route_exact_is_available(monkeypatch, tmp_path):
    client, headers = _build_client(monkeypatch)

    from app.services.distance_cache_service import DistanceCacheService
    from app.services.precise_distance_provider import PreciseDistanceProvider
    import app.services.precise_distance_provider as precise_distance_provider_module

    provider = PreciseDistanceProvider()
    provider._distance_cache = DistanceCacheService(db_path=str(tmp_path / "distance_cache.db"))
    precise_distance_provider_module._precise_distance_provider = provider

    class FakeAmapService:
        def distance_matrix(self, origins, destinations, strategy):
            return {
                "success": False,
                "provider": "amap",
                "provider_status": "degraded",
                "fallback_reason": "AMAP_DISTANCE_MATRIX_NO_ROUTE",
            }

        def driving_route(self, origin_coord, destination_coord, strategy=0, show_traffic=True):
            from app.services.amap_service import AmapRouteResult

            if origin_coord == destination_coord:
                return AmapRouteResult(success=False, fallback_reason="SAME_POINT")

            return AmapRouteResult(
                success=True,
                distance=2234000,
                duration=112200,
                provider="amap",
                provider_status="ok",
                degraded=False,
                fallback_reason=None,
            )

    monkeypatch.setattr(
        "app.services.amap_service.get_amap_service",
        lambda: FakeAmapService(),
    )

    response = client.post(
        "/api/multi-objective/optimize",
        headers=headers,
        json=_payload("weighted_sum"),
    )

    assert response.status_code == 200, response.get_json()
    payload = response.get_json()
    first = payload["recommendations"][0]

    assert payload["success"] is True
    assert payload["authenticity_level"] == "B"
    assert payload["fallback_reason"] is None
    assert payload["distance_cache_stats"]["amap_route_successes"] >= 1
    assert payload["distance_metadata"]["distance_matrix_fallback_reason"] == "AMAP_DISTANCE_MATRIX_NO_ROUTE"
    assert first["objectives"]["distance"] == 2234.0
    _assert_recommendation_explanation_contract(first, payload)


def test_optimize_modes_use_real_amap_route_alternatives_for_specified_od(monkeypatch):
    client, headers = _build_client(monkeypatch)

    class FakeAmapService:
        def multi_route(self, origin_coord, destination_coord):
            return {
                "success": True,
                "provider": "amap",
                "provider_status": "ok",
                "fallback_reason": None,
                "routes": [
                    {
                        "route_index": 0,
                        "distance": 2200000,
                        "duration": 138000,
                        "tolls": 820,
                        "strategy": "速度优先",
                        "main_roads": ["京港澳高速", "许广高速"],
                        "polyline": [[116.4, 39.9], [114.3, 30.6], [113.5, 22.2]],
                    },
                    {
                        "route_index": 1,
                        "distance": 2320000,
                        "duration": 126000,
                        "tolls": 430,
                        "strategy": "时间优先",
                        "main_roads": ["大广高速", "广佛高速"],
                        "polyline": [[116.4, 39.9], [115.8, 28.7], [113.5, 22.2]],
                    },
                    {
                        "route_index": 2,
                        "distance": 2500000,
                        "duration": 120000,
                        "tolls": 80,
                        "strategy": "少收费",
                        "main_roads": ["国道", "城市快速路"],
                        "polyline": [[116.4, 39.9], [112.9, 27.8], [113.5, 22.2]],
                    },
                ],
            }

    monkeypatch.setattr(
        "app.services.amap_service.get_amap_service",
        lambda: FakeAmapService(),
    )

    for algorithm in ["all", "weighted_sum", "pareto"]:
        response = client.post(
            "/api/multi-objective/optimize",
            headers=headers,
            json=_payload(algorithm),
        )

        assert response.status_code == 200, response.get_json()
        payload = response.get_json()

        assert payload["success"] is True
        assert payload["total_routes"] == 3 or payload["pareto_summary"]["total_routes"] == 3
        assert payload["distance_source"] == "amap_driving_route"
        assert payload["path_source"] == "amap_driving_route"
        assert payload["authenticity_level"] == "B"
        assert payload["fallback_reason"] is None
        assert payload["candidate_generation"]["candidate_count"] == 3
        assert payload["candidate_generation"]["front_quality"] != "single_solution_projection"
        assert payload["distance_cache_stats"]["amap_calls"] == 1
        assert payload["distance_cache_stats"]["amap_route_successes"] == 3

        recommendations = payload["recommendations"]
        assert recommendations
        assert all(item["route_candidate_id"].startswith("amap-route-") for item in recommendations)
        assert any(item.get("polyline") for item in recommendations)
        for item in recommendations:
            _assert_recommendation_explanation_contract(item, payload)

        if algorithm in {"all", "pareto"}:
            assert payload["front_quality"] == "reported_front"
            assert payload["pareto_summary"]["pareto_count"] >= 2


def test_optimize_expands_single_amap_multi_route_with_strategy_routes(monkeypatch):
    client, headers = _build_client(monkeypatch)

    class FakeAmapService:
        def multi_route(self, origin_coord, destination_coord):
            return {
                "success": True,
                "provider": "amap",
                "provider_status": "ok",
                "fallback_reason": None,
                "routes": [
                    {
                        "route_index": 0,
                        "distance": 2200000,
                        "duration": 138000,
                        "tolls": 820,
                        "strategy": "速度最快",
                        "main_roads": ["京港澳高速"],
                        "polyline": [[116.4, 39.9], [113.5, 22.2]],
                    }
                ],
            }

        def driving_route(self, origin_coord, destination_coord, strategy=0, show_traffic=True):
            from app.services.amap_service import AmapRouteResult

            by_strategy = {
                1: AmapRouteResult(
                    success=True,
                    distance=2350000,
                    duration=132000,
                    tolls=320,
                    toll_distance=900000,
                    polyline=[[116.4, 39.9], [115.2, 28.2], [113.5, 22.2]],
                    steps=[{"road": "大广高速"}, {"road": "广佛高速"}],
                ),
                2: AmapRouteResult(
                    success=True,
                    distance=2180000,
                    duration=150000,
                    tolls=760,
                    toll_distance=1200000,
                    polyline=[[116.4, 39.9], [114.2, 29.1], [113.5, 22.2]],
                    steps=[{"road": "最短联络线"}, {"road": "珠三角环线"}],
                ),
                4: AmapRouteResult(
                    success=True,
                    distance=2420000,
                    duration=126000,
                    tolls=680,
                    toll_distance=1100000,
                    polyline=[[116.4, 39.9], [113.9, 27.7], [113.5, 22.2]],
                    steps=[{"road": "避拥堵快速路"}],
                ),
            }
            return by_strategy.get(strategy, AmapRouteResult(success=False, fallback_reason="NO_ALT"))

    monkeypatch.setattr(
        "app.services.amap_service.get_amap_service",
        lambda: FakeAmapService(),
    )

    response = client.post(
        "/api/multi-objective/optimize",
        headers=headers,
        json=_payload("pareto"),
    )

    assert response.status_code == 200, response.get_json()
    payload = response.get_json()

    assert payload["success"] is True
    assert payload["total_routes"] >= 3
    assert payload["front_quality"] == "reported_front"
    assert payload["distance_source"] == "amap_driving_route"
    assert payload["path_source"] == "amap_driving_route"
    assert payload["candidate_generation"]["source_counts"]["amap_multi_route"] == 1
    assert payload["candidate_generation"]["source_counts"]["amap_strategy_route"] >= 2
    assert payload["distance_cache_stats"]["amap_calls"] >= 3
    assert payload["distance_cache_stats"]["amap_route_successes"] >= 3
    assert any(
        item["route_candidate_id"].startswith("amap-strategy-")
        for item in payload["recommendations"]
    )
    for item in payload["recommendations"]:
        _assert_recommendation_explanation_contract(item, payload)
