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
    from app.models import User, Node, db
    from app.models.layered_data import DataImportBatch, ShipmentFact

    app = create_app("testing")
    app.config["JWT_SECRET_KEY"] = "tracking-shipment-test-secret"

    with app.app_context():
        db.create_all()

        user = User(username="admin", real_name="管理员", role="admin", status="active")
        user.password = "admin123"
        db.session.add(user)

        db.session.add_all([
            Node(
                id=1,
                name="北京仓库",
                type="warehouse",
                province="北京市",
                city="北京市",
                longitude=116.45747,
                latitude=39.908823,
                status="active",
            ),
            Node(
                id=2,
                name="永安配送站",
                type="station",
                province="福建省",
                city="永安",
                longitude=117.36525,
                latitude=25.974086,
                status="active",
            ),
        ])

        batch = DataImportBatch(
            dataset_source="test",
            source_filename="tracking.csv",
            quality_status="ready",
            raw_record_count=1,
            fact_record_count=1,
            quarantine_record_count=0,
        )
        db.session.add(batch)
        db.session.flush()

        db.session.add(
            ShipmentFact(
                batch_id=batch.id,
                external_shipment_id="SHIP-TRACK-1",
                external_order_id="ORD-TRACK-1",
                customer_name_masked="李*",
                origin_city_raw="北京",
                origin_city_std="北京",
                destination_city_raw="永安",
                destination_city_std="永安",
                origin_lng=116.45747,
                origin_lat=39.908823,
                destination_lng=117.36525,
                destination_lat=25.974086,
                cargo_type="食品",
                freight=66.0,
                standard_status="in_transit",
                shipped_at=datetime.utcnow(),
            )
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


def test_tracking_simulate_supports_shipment_fact_order(monkeypatch):
    client, headers = _build_client(monkeypatch)

    response = client.get("/api/tracking/simulate/1?speed=1", headers=headers)

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert payload["data"]["route"]["distance_km"] > 0
    assert len(payload["data"]["route"]["polyline"]) >= 2
    assert payload["data"]["route"]["origin"]["name"] == "北京仓库"
    assert payload["data"]["route"]["destination"]["name"] == "永安配送站"
