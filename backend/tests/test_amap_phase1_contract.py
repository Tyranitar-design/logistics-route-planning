import importlib
import os
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


def _reload_module(module_name):
    if module_name in sys.modules:
        return importlib.reload(sys.modules[module_name])
    return importlib.import_module(module_name)


def _build_client(monkeypatch):
    monkeypatch.setenv("DISABLE_ML_ROUTES", "1")

    if "app" in sys.modules:
        importlib.reload(sys.modules["app"])
    else:
        importlib.import_module("app")

    from app import create_app
    from app.models import User, Node, db

    app = create_app("testing")
    app.config["JWT_SECRET_KEY"] = "amap-phase1-secret"

    with app.app_context():
        db.create_all()

        user = User(username="admin", real_name="管理员", role="admin", status="active")
        user.password = "admin123"
        db.session.add(user)

        db.session.add_all(
            [
                Node(
                    name="北京仓库",
                    type="warehouse",
                    city="北京",
                    province="北京",
                    longitude=116.4074,
                    latitude=39.9042,
                    status="active",
                ),
                Node(
                    name="澳门特别行政区物流节点",
                    type="distribution_center",
                    city="澳门",
                    province="澳门",
                    longitude=113.5439,
                    latitude=22.1987,
                    status="active",
                ),
                Node(
                    name="无坐标节点",
                    type="customer",
                    city="未知",
                    province="未知",
                    longitude=None,
                    latitude=None,
                    status="active",
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
    headers = {"Authorization": f"Bearer {token}"}
    return client, headers


def test_amap_service_prefers_service_key(monkeypatch):
    monkeypatch.setenv("AMAP_WEB_KEY", "web-key-should-not-win")
    monkeypatch.setenv("AMAP_SERVICE_KEY", "service-key-should-win")

    amap_service_module = _reload_module("app.services.amap_service")
    service = amap_service_module.AmapService(
        web_key="web-key-should-not-win",
        service_key="service-key-should-win",
    )

    assert service._get_key() == "service-key-should-win"


def test_amap_service_reports_key_unavailable_when_missing(monkeypatch):
    amap_service_module = _reload_module("app.services.amap_service")
    service = amap_service_module.AmapService(web_key="", service_key="")

    result = service._make_request("direction/driving", {"origin": "1,1", "destination": "2,2"})

    assert result["status"] == "0"
    assert result["provider_status"] == "unavailable"
    assert result["fallback_reason"] == "AMAP_KEY_MISSING"


def test_driving_route_returns_provider_and_authenticity(monkeypatch):
    client, headers = _build_client(monkeypatch)

    import app.routes.amap as amap_routes

    class FakeAmapService:
        def driving_route(self, origin, destination, waypoints, strategy, show_traffic):
            from app.services.amap_service import AmapRouteResult

            return AmapRouteResult(
                success=True,
                distance=12345,
                duration=1800,
                tolls=18.5,
                toll_distance=5000,
                steps=[{"instruction": "直行", "distance": 500, "duration": 60, "toll_road": False}],
                polyline=[[116.4074, 39.9042], [113.5439, 22.1987]],
                traffic_info={"evaluation": "缓行", "segments": []},
            )

    monkeypatch.setattr(amap_routes, "get_amap_service", lambda: FakeAmapService())

    response = client.post(
        "/api/amap/route/driving",
        headers=headers,
        json={
            "origin": 1,
            "destination": 2,
            "strategy": 4,
            "show_traffic": True,
        },
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert payload["data"]["provider"] == "amap"
    assert payload["data"]["provider_status"] == "ok"
    assert payload["data"]["degraded"] is False
    assert payload["data"]["fallback_reason"] is None
    assert payload["data"]["authenticity"]["distance_source"] == "amap"


def test_traffic_node_returns_available_false_with_provider_metadata(monkeypatch):
    client, headers = _build_client(monkeypatch)

    import app.routes.amap as amap_routes

    class FakeAmapService:
        def traffic_around(self, center, radius):
            from app.services.amap_service import AmapTrafficResult

            return AmapTrafficResult(
                success=False,
                error="INVALID_USER_KEY",
            )

    monkeypatch.setattr(amap_routes, "get_amap_service", lambda: FakeAmapService())

    response = client.get("/api/amap/traffic/node/1", headers=headers)

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert payload["data"]["available"] is False
    assert payload["data"]["provider"] == "amap"
    assert payload["data"]["provider_status"] == "degraded"
    assert payload["data"]["fallback_reason"] == "INVALID_USER_KEY"


def test_weather_now_returns_provider_metadata_on_fallback(monkeypatch):
    client, headers = _build_client(monkeypatch)

    import app.routes.weather as weather_routes

    class FakeWeatherService:
        def get_weather_now(self, city):
            return {
                "success": False,
                "error": "INVALID_USER_KEY",
            }

    monkeypatch.setattr(weather_routes, "get_weather_service", lambda: FakeWeatherService())

    response = client.get("/api/weather/now?city=北京", headers=headers)

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert payload["data"]["source"] == "fallback"
    assert payload["data"]["provider"] == "amap"
    assert payload["data"]["provider_status"] == "degraded"
    assert payload["data"]["degraded"] is True
    assert payload["data"]["note"] == "INVALID_USER_KEY"


def test_node_weather_reports_resolved_city_confidence(monkeypatch):
    client, headers = _build_client(monkeypatch)

    import app.routes.weather as weather_routes

    class FakeWeatherService:
        def get_weather_now(self, city):
            return {
                "success": True,
                "data": {
                    "province": city,
                    "city": city,
                    "adcode": "110000",
                    "weather": "晴",
                    "temperature": "20",
                    "wind_direction": "北",
                    "wind_power": "3",
                    "humidity": "20",
                    "report_time": "2026-05-21 12:00:00",
                    "provider": "amap",
                    "provider_status": "ok",
                    "degraded": False,
                    "fallback_reason": None,
                    "source": "amap",
                    "authenticity": {
                        "distance_source": "amap",
                        "duration_source": "amap",
                    },
                },
            }

        def analyze_transport_impact(self, weather, temperature):
            class _Impact:
                def to_dict(self):
                    return {
                        "impact_level": "无影响",
                        "speed_reduction": 0,
                        "delay_risk": 0.05,
                        "safety_warning": "",
                        "suggestions": ["天气良好，可正常运输"],
                    }

            return _Impact()

    monkeypatch.setattr(weather_routes, "get_weather_service", lambda: FakeWeatherService())

    response = client.get("/api/weather/node/1", headers=headers)

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert payload["data"]["resolved_city"] == "北京"
    assert payload["data"]["resolved_city_confidence"] == "direct"
