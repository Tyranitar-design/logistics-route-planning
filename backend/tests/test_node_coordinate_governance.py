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

    from app import create_app
    from app.models import User, Node, db

    app = create_app("testing")
    app.config["JWT_SECRET_KEY"] = "node-coordinate-test-secret"

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
                    province="北京市",
                    city="北京市",
                    district="朝阳区",
                    address="北京市朝阳区物流园",
                    longitude=116.45747,
                    latitude=39.908823,
                    status="active",
                ),
                Node(
                    name="澳门特别行政区物流节点",
                    type="distribution_center",
                    province=None,
                    city="澳门特别行政区",
                    district=None,
                    address="澳门特别行政区（由真实运单网络自动生成）",
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


def test_coordinate_audit_lists_missing_nodes(monkeypatch):
    client, headers = _build_client(monkeypatch)

    response = client.get("/api/nodes/coordinate-audit", headers=headers)

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert payload["summary"]["missing_coordinates"] == 1
    assert payload["summary"]["total_nodes"] == 2
    assert payload["nodes"][0]["name"] == "澳门特别行政区物流节点"
    assert payload["nodes"][0]["resolution_query"].startswith("澳门特别行政区")


def test_resolve_coordinates_updates_node_from_amap(monkeypatch):
    client, headers = _build_client(monkeypatch)

    import app.routes.nodes as node_routes

    class FakeAmapService:
        def geocode(self, address, city=None):
            from app.services.amap_service import AmapGeocodeResult

            return AmapGeocodeResult(
                success=True,
                longitude=113.5439,
                latitude=22.1987,
                formatted_address="澳门特别行政区澳门半岛",
                province="澳门特别行政区",
                city="澳门特别行政区",
                district="澳门半岛",
                provider="amap",
                provider_status="ok",
                degraded=False,
                fallback_reason=None,
                authenticity={"message": "地理编码来自高德官方地理编码服务。"},
            )

    monkeypatch.setattr(node_routes, "get_amap_service", lambda: FakeAmapService())

    response = client.post("/api/nodes/2/resolve-coordinates", headers=headers)

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert payload["node"]["longitude"] == 113.5439
    assert payload["node"]["latitude"] == 22.1987
    assert payload["provider"] == "amap"
    assert payload["provider_status"] == "ok"
    assert payload["degraded"] is False


def test_resolve_coordinates_returns_explicit_degradation_on_geocode_failure(monkeypatch):
    client, headers = _build_client(monkeypatch)

    import app.routes.nodes as node_routes

    class FakeAmapService:
        def geocode(self, address, city=None):
            from app.services.amap_service import AmapGeocodeResult

            return AmapGeocodeResult(
                success=False,
                error="AMAP_GEOCODE_EMPTY",
                provider="amap",
                provider_status="degraded",
                degraded=True,
                fallback_reason="AMAP_GEOCODE_EMPTY",
                authenticity={"message": "地理编码来自高德官方地理编码服务。"},
            )

    monkeypatch.setattr(node_routes, "get_amap_service", lambda: FakeAmapService())

    response = client.post("/api/nodes/2/resolve-coordinates", headers=headers)

    assert response.status_code == 422
    payload = response.get_json()
    assert payload["success"] is False
    assert payload["provider"] == "amap"
    assert payload["provider_status"] == "degraded"
    assert payload["degraded"] is True
    assert payload["fallback_reason"] == "AMAP_GEOCODE_EMPTY"


def test_resolution_query_candidates_remove_generated_noise(monkeypatch):
    from app.models.node import Node
    from app.services.node_coordinate_service import build_resolution_candidates

    node = Node(
        name="澳门特别行政区物流节点",
        city="澳门特别行政区",
        province=None,
        district=None,
        address="澳门特别行政区（由真实运单网络自动生成）",
    )

    candidates = build_resolution_candidates(node)

    assert candidates[0] == "澳门特别行政区"
    assert "澳门特别行政区" in candidates
    assert not any("由真实运单网络自动生成" in item for item in candidates)


def test_resolution_query_candidates_use_city_normalization_for_district_style_nodes(monkeypatch):
    from app.models.node import Node
    from app.services.node_coordinate_service import build_resolution_candidates

    node = Node(
        name="秀英区物流节点",
        city="秀英区",
        province=None,
        district=None,
        address="秀英区（由真实运单网络自动生成）",
    )

    candidates = build_resolution_candidates(node)

    assert candidates[0] == "秀英区"
    assert "海口秀英区" in candidates
    assert "海南省海口市秀英区" in candidates
