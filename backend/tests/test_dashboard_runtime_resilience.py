import importlib
import os
import sys
from datetime import datetime, timedelta

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
    from app.models import User, db
    from app.models.layered_data import DataImportBatch, ShipmentFact

    app = create_app("testing")
    app.config["JWT_SECRET_KEY"] = "dashboard-test-secret"

    with app.app_context():
        db.create_all()
        user = User(username="admin", real_name="管理员", role="admin", status="active")
        user.password = "admin123"
        db.session.add(user)

        batch = DataImportBatch(
            dataset_source="test",
            source_filename="runtime.csv",
            quality_status="ready",
            raw_record_count=3,
            fact_record_count=3,
            quarantine_record_count=0,
        )
        db.session.add(batch)
        db.session.flush()

        recent_day = datetime.utcnow() - timedelta(days=2)
        older_day = datetime.utcnow() - timedelta(days=4)

        db.session.add_all([
            ShipmentFact(
                batch_id=batch.id,
                external_shipment_id="SHIP-A",
                external_order_id="ORD-A",
                customer_name_masked="客户甲",
                origin_city_raw="北京",
                origin_city_std="北京",
                destination_city_raw="上海",
                destination_city_std="上海",
                cargo_type="食品",
                freight=88.0,
                standard_status="delivered",
                shipped_at=recent_day,
                delivered_at=recent_day + timedelta(hours=6),
                signed_at=recent_day + timedelta(hours=7),
            ),
            ShipmentFact(
                batch_id=batch.id,
                external_shipment_id="SHIP-B",
                external_order_id="ORD-B",
                customer_name_masked="客户乙",
                origin_city_raw="广州",
                origin_city_std="广州",
                destination_city_raw="深圳",
                destination_city_std="深圳",
                cargo_type="零担",
                freight=128.0,
                standard_status="in_transit",
                shipped_at=recent_day,
            ),
            ShipmentFact(
                batch_id=batch.id,
                external_shipment_id="SHIP-C",
                external_order_id="ORD-C",
                customer_name_masked="客户丙",
                origin_city_raw="杭州",
                origin_city_std="杭州",
                destination_city_raw="南京",
                destination_city_std="南京",
                cargo_type="服装",
                freight=64.0,
                standard_status="assigned",
                shipped_at=older_day,
            ),
        ])
        db.session.commit()

    client = app.test_client()
    login_response = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "admin123"},
    )
    token = login_response.get_json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    return client, headers


def test_layered_trend_anchors_to_latest_available_shipment_day(monkeypatch):
    client, headers = _build_client(monkeypatch)

    response = client.get("/api/stats/orders/trend", headers=headers)

    assert response.status_code == 200
    payload = response.get_json()
    counts = [item["count"] for item in payload["trend"]]
    labels = [item["date"] for item in payload["trend"]]

    assert payload["data_source"] == "shipment_fact"
    assert len(counts) == 7
    assert max(counts) >= 2
    assert labels[-1] == (datetime.utcnow() - timedelta(days=2)).strftime("%m-%d")


def test_weather_now_gracefully_degrades_when_provider_fails(monkeypatch):
    client, headers = _build_client(monkeypatch)

    import app.routes.weather as weather_routes

    class FakeWeatherService:
        def get_weather_now(self, city):
            return {
                "success": False,
                "error": "INVALID_USER_KEY"
            }

    monkeypatch.setattr(weather_routes, "get_weather_service", lambda: FakeWeatherService())

    response = client.get("/api/weather/now?city=北京", headers=headers)

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert payload["data"]["weather"] == "服务降级"
    assert payload["data"]["source"] == "fallback"
    assert "INVALID_USER_KEY" in payload["data"]["note"]
