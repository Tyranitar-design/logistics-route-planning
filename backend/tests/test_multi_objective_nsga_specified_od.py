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
    app.config["JWT_SECRET_KEY"] = "multi-objective-specified-od-secret"

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
                type="customer",
                city="澳门",
                province="澳门",
                longitude=113.5439,
                latitude=22.1987,
                status="active",
            )
        )

        for index in range(19):
            db.session.add(
                Node(
                    name=f"干扰节点{index + 1}",
                    type="customer",
                    city="干扰",
                    province="干扰",
                    longitude=80 + index,
                    latitude=20 + index * 0.5,
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


def _assert_front_explanation_contract(item, payload):
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


def test_nsga_origin_destination_without_orders_does_not_expand_to_all_nodes(monkeypatch):
    client, headers = _build_client(monkeypatch)

    response = client.post(
        "/api/multi-objective/nsga-optimize",
        headers=headers,
        json={
            "origin_id": 1,
            "destination_id": 2,
            "solver": "pymoo_nsga2",
            "n_gen": 10,
            "use_local_data": True,
        },
    )

    assert response.status_code == 200
    payload = response.get_json()

    assert payload["success"] is True
    assert payload["problem_mode"] == "specified_origin_destination"
    assert payload["n_orders"] == 0
    assert payload["n_customers"] == 1
    assert payload["objectives"][0] < 5000
    assert payload["objectives"][0] > 1000
    assert payload["path_source"] == "specified_origin_destination"
    assert payload["distance_source"] == "precise_distance_provider"
    assert payload["front_quality"] == "single_solution_projection"
    assert payload["pareto_front_size"] == 1
    assert payload["distance_cache_stats"]["total_pairs"] > 0
    assert "amap_attempted_pairs" in payload["distance_cache_stats"]
    assert payload["fallback_reason"] or payload["distance_precision"]["exact_count"] > 0
    assert payload["pareto_front"][0]["path"][0]["name"] == "北京仓库"
    assert payload["pareto_front"][0]["path"][1]["name"] == "澳门特别行政区物流节点"
    _assert_front_explanation_contract(payload["pareto_front"][0], payload)


def test_nsga_specified_od_returns_real_amap_route_candidate_front(monkeypatch):
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
                        "main_roads": ["京港澳高速"],
                        "polyline": [[116.4, 39.9], [113.5, 22.2]],
                    },
                    {
                        "route_index": 1,
                        "distance": 2320000,
                        "duration": 126000,
                        "tolls": 430,
                        "strategy": "时间优先",
                        "main_roads": ["大广高速"],
                        "polyline": [[116.4, 39.9], [113.5, 22.2]],
                    },
                    {
                        "route_index": 2,
                        "distance": 2500000,
                        "duration": 120000,
                        "tolls": 80,
                        "strategy": "少收费",
                        "main_roads": ["国道"],
                        "polyline": [[116.4, 39.9], [113.5, 22.2]],
                    },
                ],
            }

    monkeypatch.setattr(
        "app.services.amap_service.get_amap_service",
        lambda: FakeAmapService(),
    )

    response = client.post(
        "/api/multi-objective/nsga-optimize",
        headers=headers,
        json={
            "origin_id": 1,
            "destination_id": 2,
            "solver": "pymoo_nsga2",
            "n_gen": 10,
            "use_local_data": True,
        },
    )

    assert response.status_code == 200, response.get_json()
    payload = response.get_json()

    assert payload["success"] is True
    assert payload["problem_mode"] == "specified_origin_destination"
    assert payload["solver_status"] == "specified_od_route_candidates"
    assert payload["front_quality"] == "reported_front"
    assert payload["pareto_front_size"] >= 2
    assert payload["distance_source"] == "amap_driving_route"
    assert payload["path_source"] == "amap_driving_route"
    assert payload["authenticity_level"] == "B"
    assert payload["fallback_reason"] is None
    assert payload["candidate_generation"]["candidate_count"] == 3
    assert payload["distance_cache_stats"]["amap_calls"] == 1
    assert payload["distance_cache_stats"]["amap_route_successes"] == 3
    assert payload["objectives"][0] == 2200.0
    assert all(item["route_candidate_id"].startswith("amap-route-") for item in payload["pareto_front"])
    for item in payload["pareto_front"]:
        _assert_front_explanation_contract(item, payload)


def test_nsga_specified_od_expands_single_multi_route_with_strategy_candidates(monkeypatch):
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
        "/api/multi-objective/nsga-optimize",
        headers=headers,
        json={
            "origin_id": 1,
            "destination_id": 2,
            "solver": "pymoo_nsga2",
            "n_gen": 10,
            "use_local_data": True,
        },
    )

    assert response.status_code == 200, response.get_json()
    payload = response.get_json()

    assert payload["success"] is True
    assert payload["front_quality"] == "reported_front"
    assert payload["pareto_front_size"] >= 2
    assert payload["candidate_generation"]["source_counts"]["amap_multi_route"] == 1
    assert payload["candidate_generation"]["source_counts"]["amap_strategy_route"] >= 2
    assert payload["distance_cache_stats"]["amap_calls"] >= 3
    assert payload["distance_cache_stats"]["amap_route_successes"] >= 3
    assert any(
        item["route_candidate_id"].startswith("amap-strategy-")
        for item in payload["pareto_front"]
    )
    for item in payload["pareto_front"]:
        _assert_front_explanation_contract(item, payload)
