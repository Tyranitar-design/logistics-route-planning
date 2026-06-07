import importlib
import os
import sys
from datetime import datetime, timedelta

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


def _reload_config_module():
    if "config" in sys.modules:
        return importlib.reload(sys.modules["config"])
    return importlib.import_module("config")


def _build_test_client(monkeypatch):
    monkeypatch.setenv("DISABLE_ML_ROUTES", "1")

    if "app" in sys.modules:
        importlib.reload(sys.modules["app"])
    else:
        importlib.import_module("app")

    from app import create_app
    from app.models import User, db
    from app.models.layered_data import DataImportBatch, ShipmentFact

    app = create_app("testing")
    app.config["JWT_SECRET_KEY"] = "test-secret"

    with app.app_context():
        db.create_all()
        user = User(username="admin", real_name="管理员", role="admin", status="active")
        user.password = "admin123"
        db.session.add(user)
        batch = DataImportBatch(
            dataset_source="test",
            source_filename="fixture.csv",
            quality_status="ready",
            raw_record_count=2,
            fact_record_count=2,
            quarantine_record_count=0,
        )
        db.session.add(batch)
        db.session.flush()
        db.session.add(
            ShipmentFact(
                batch_id=batch.id,
                external_shipment_id="SHIP-1",
                external_order_id="ORD-1",
                customer_name_masked="客户甲",
                origin_city_raw="北京",
                origin_city_std="北京",
                destination_city_raw="上海",
                destination_city_std="上海",
                cargo_type="快运",
                freight=188.5,
                standard_status="delivered",
                shipped_at=datetime.utcnow() - timedelta(days=1),
                delivered_at=datetime.utcnow(),
                signed_at=datetime.utcnow(),
            )
        )
        db.session.add(
            ShipmentFact(
                batch_id=batch.id,
                external_shipment_id="SHIP-2",
                external_order_id="ORD-2",
                customer_name_masked="客户乙",
                origin_city_raw="广州",
                origin_city_std="广州",
                destination_city_raw="深圳",
                destination_city_std="深圳",
                cargo_type="零担",
                freight=99.0,
                standard_status="assigned",
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


def test_config_prefers_postgres_database_url(monkeypatch):
    monkeypatch.setenv("POSTGRES_DATABASE_URL", "postgresql://tester@localhost:5432/logistics_route_system")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///fallback.db")

    config_module = _reload_config_module()

    assert config_module.Config.SQLALCHEMY_DATABASE_URI == "postgresql://tester@localhost:5432/logistics_route_system"


def test_create_app_can_skip_ml_routes(monkeypatch):
    monkeypatch.setenv("DISABLE_ML_ROUTES", "1")

    if "app" in sys.modules:
        importlib.reload(sys.modules["app"])
    else:
        importlib.import_module("app")

    from app import create_app

    app = create_app("testing")
    route_rules = {rule.rule for rule in app.url_map.iter_rules()}

    assert "/api/auth/login" in route_rules
    assert "/api/ml/train" not in route_rules


def test_stats_overview_prefers_layered_shipment_facts(monkeypatch):
    client, headers = _build_test_client(monkeypatch)

    response = client.get("/api/stats/overview", headers=headers)

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["data_source"] == "shipment_fact"
    assert payload["total_orders"] == 2
    assert payload["delivered_orders"] == 1
    assert payload["pending_orders"] == 1


def test_stats_order_trend_prefers_layered_shipment_facts(monkeypatch):
    client, headers = _build_test_client(monkeypatch)

    response = client.get("/api/stats/orders/trend", headers=headers)

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["data_source"] == "shipment_fact"
    assert sum(item["count"] for item in payload["trend"]) >= 2


def test_orders_route_falls_back_to_layered_shipment_facts(monkeypatch):
    client, headers = _build_test_client(monkeypatch)

    response = client.get("/api/orders?per_page=10&page=1", headers=headers)

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["data_source"] == "shipment_fact"
    assert payload["total"] == 2
    assert payload["orders"][0]["order_number"] in {"ORD-1", "ORD-2"}
