import importlib
import os
import sys
from datetime import datetime

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
    from app.models import Node, User, db
    from app.models.layered_data import DataImportBatch, ShipmentFact

    app = create_app("testing")
    app.config["JWT_SECRET_KEY"] = "order-route-shipment-test-secret"

    with app.app_context():
        db.create_all()

        user = User(username="admin", real_name="管理员", role="admin", status="active")
        user.password = "admin123"
        db.session.add(user)

        db.session.add_all(
            [
                Node(
                    id=1,
                    name="北京仓库",
                    type="warehouse",
                    city="北京",
                    longitude=116.4074,
                    latitude=39.9042,
                    status="active",
                ),
                Node(
                    id=2,
                    name="上海配送站",
                    type="station",
                    city="上海",
                    longitude=121.4737,
                    latitude=31.2304,
                    status="active",
                ),
            ]
        )

        batch = DataImportBatch(
            dataset_source="pytest",
            source_filename="orders.csv",
            quality_status="ready",
            raw_record_count=1,
            fact_record_count=1,
            quarantine_record_count=0,
        )
        db.session.add(batch)
        db.session.flush()
        db.session.add(
            ShipmentFact(
                id=35692,
                batch_id=batch.id,
                external_shipment_id="SHIP-35692",
                external_order_id="35692",
                customer_name_masked="测*",
                origin_city_raw="北京",
                origin_city_std="北京",
                destination_city_raw="上海",
                destination_city_std="上海",
                origin_lng=116.4074,
                origin_lat=39.9042,
                destination_lng=121.4737,
                destination_lat=31.2304,
                cargo_type="电子产品",
                weight_kg=12.0,
                volume_m3=0.8,
                freight=188.0,
                standard_status="assigned",
                geo_status="resolved",
                shipped_at=datetime.utcnow(),
            )
        )
        db.session.commit()

    import app.services.order_route_service as order_route_module

    class FakeAmapService:
        def multi_route(self, origin, destination):
            return {
                "success": True,
                "provider": "amap",
                "provider_status": "ok",
                "degraded": False,
                "fallback_reason": None,
                "authenticity": {"level": "A", "distance_source": "amap"},
                "routes": [
                    {
                        "distance": 1280000,
                        "duration": 48600,
                        "tolls": 360.0,
                        "toll_distance": 900000,
                        "strategy": "速度优先",
                        "main_roads": ["京沪高速"],
                        "provider": "amap",
                        "provider_status": "ok",
                        "degraded": False,
                        "fallback_reason": None,
                        "polyline": [[origin[0], origin[1]], [destination[0], destination[1]]],
                    }
                ],
            }

    monkeypatch.setattr(order_route_module, "get_amap_service", lambda: FakeAmapService())
    order_route_module._order_route_service = None

    client = app.test_client()
    login_response = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "admin123"},
    )
    token = login_response.get_json()["access_token"]
    return client, {"Authorization": f"Bearer {token}"}


def test_recommend_route_supports_shipment_fact_order_id(monkeypatch):
    client, headers = _build_client(monkeypatch)

    response = client.get("/api/orders/35692/recommend-route?prefer_source=auto", headers=headers)

    assert response.status_code == 200, response.get_json()
    payload = response.get_json()
    assert payload["success"] is True
    data = payload["data"]
    assert data["order_id"] == 35692
    assert data["order_number"] == "35692"
    assert data["data_source"] == "shipment_fact"
    assert data["origin"]["name"] == "北京仓库"
    assert data["destination"]["name"] == "上海配送站"
    assert data["amap_route"]["provider_status"] == "ok"
    assert data["recommended_route"]["distance_source"] == "amap_driving_route"
