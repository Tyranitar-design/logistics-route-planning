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
    from app.models import DataImportBatch, ShipmentFact, User, Vehicle

    app = create_app("testing")
    app.config["JWT_SECRET_KEY"] = "dispatch-orchestration-secret"

    with app.app_context():
        db.create_all()

        user = User(username="admin", real_name="管理员", role="admin", status="active")
        user.password = "admin123"
        db.session.add(user)

        batch = DataImportBatch(
            dataset_source="unit-test",
            source_filename="dispatch.csv",
            quality_status="ready",
            raw_record_count=2,
            fact_record_count=2,
        )
        db.session.add(batch)
        db.session.flush()

        db.session.add_all([
            Vehicle(
                plate_number="京A10001",
                vehicle_type="truck",
                load_capacity=30,
                volume_capacity=90,
                capacity=30,
                status="available",
            ),
            Vehicle(
                plate_number="京A10002",
                vehicle_type="truck",
                load_capacity=30,
                volume_capacity=90,
                capacity=30,
                status="available",
            ),
        ])
        db.session.add_all([
            ShipmentFact(
                batch_id=batch.id,
                external_shipment_id="SHP-DISPATCH-001",
                external_order_id="ORD-DISPATCH-001",
                customer_name_masked="客户甲",
                origin_city_raw="北京",
                origin_city_std="北京",
                destination_city_raw="天津",
                destination_city_std="天津",
                origin_lng=116.4074,
                origin_lat=39.9042,
                destination_lng=117.2,
                destination_lat=39.1333,
                geo_status="resolved",
                cargo_type="普货",
                standard_status="assigned",
                weight_kg=12000,
                volume_m3=20,
                freight=500,
            ),
            ShipmentFact(
                batch_id=batch.id,
                external_shipment_id="SHP-DISPATCH-002",
                external_order_id="ORD-DISPATCH-002",
                customer_name_masked="客户乙",
                origin_city_raw="北京",
                origin_city_std="北京",
                destination_city_raw="石家庄",
                destination_city_std="石家庄",
                origin_lng=116.4074,
                origin_lat=39.9042,
                destination_lng=114.5149,
                destination_lat=38.0428,
                geo_status="resolved",
                cargo_type="普货",
                standard_status="assigned",
                weight_kg=15000,
                volume_m3=25,
                freight=650,
            ),
        ])
        db.session.commit()

    client = app.test_client()
    login_response = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    token = login_response.get_json()["access_token"]
    return client, {"Authorization": f"Bearer {token}"}, app


def test_dispatch_health_prefers_layered_facts_when_orders_empty(monkeypatch):
    client, headers, _ = _build_client(monkeypatch)

    response = client.get("/api/dispatch/health", headers=headers)

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert payload["data_source"] == "shipment_fact"
    assert payload["order_sources"]["shipment_facts"]["total"] == 2
    assert payload["vehicle_source"]["available_vehicles"] == 2
    assert payload["diagnostics"]["order_count"] == 2


def test_smart_dispatch_generates_plans_from_shipment_facts(monkeypatch):
    client, headers, _ = _build_client(monkeypatch)

    response = client.post(
        "/api/dispatch/smart",
        headers=headers,
        json={
            "algorithm": "balanced",
            "limit": 10,
            "max_orders_per_vehicle": 2,
            "use_precise_distance": False,
            "weights": {"cost": 0.4, "time": 0.3, "satisfaction": 0.3},
        },
    )

    assert response.status_code == 200, response.get_json()
    payload = response.get_json()
    assert payload["success"] is True
    assert payload["data_source"] == "shipment_fact"
    assert payload["summary"]["assigned_orders"] == 2
    assert payload["summary"]["total_orders_assigned"] == 2
    assert payload["plans"]
    assert payload["diagnostics"]["order_count"] == 2
    assert payload["ai_shadow"]["mode"] == "shadow"
    assert payload["distance_source"] == "haversine_corrected"
    assert payload["authenticity_level"].startswith("B")
    assert payload["scenario_id"]


def test_apply_persisted_dispatch_scenario(monkeypatch):
    client, headers, app = _build_client(monkeypatch)

    preview = client.post(
        "/api/dispatch/preview",
        headers=headers,
        json={"limit": 10, "use_precise_distance": False},
    ).get_json()

    response = client.post(
        "/api/dispatch/apply",
        headers=headers,
        json={"scenario_id": preview["scenario_id"]},
    )

    assert response.status_code == 200, response.get_json()
    payload = response.get_json()
    assert payload["success"] is True
    assert payload["assignments_updated"] == 2

    detail = client.get(f"/api/dispatch/scenarios/{preview['scenario_id']}", headers=headers)
    scenario = detail.get_json()["scenario"]
    assert scenario["status"] == "applied"
    assert len(scenario["assignments"]) == 2


def test_dispatch_capacity_shortage_is_explained(monkeypatch):
    client, headers, app = _build_client(monkeypatch)

    with app.app_context():
        from app.models import Vehicle, db

        Vehicle.query.update({"load_capacity": 1, "volume_capacity": 1})
        db.session.commit()

    response = client.post(
        "/api/dispatch/preview",
        headers=headers,
        json={"limit": 10, "use_precise_distance": False},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["summary"]["assigned_orders"] == 0
    assert payload["summary"]["unassigned_orders"] == 2
    assert payload["unassigned_orders"][0]["reason"]
    assert payload["diagnostics"]["reason_counts"]["capacity_shortage_weight"] == 1


def test_auto_data_source_prefers_shipment_facts_over_legacy_orders(monkeypatch):
    client, headers, app = _build_client(monkeypatch)

    with app.app_context():
        from app.models import Node, Order, db

        pickup = Node(
            name="旧仓库",
            code="LEG-WH",
            type="warehouse",
            city="北京",
            address="北京市旧仓库",
            longitude=116.4074,
            latitude=39.9042,
            status="active",
        )
        delivery = Node(
            name="旧客户",
            code="LEG-CUST",
            type="customer",
            city="天津",
            address="天津市旧客户",
            longitude=117.2,
            latitude=39.1333,
            status="active",
        )
        db.session.add_all([pickup, delivery])
        db.session.flush()
        db.session.add(
            Order(
                order_number="LEGACY-DISPATCH-001",
                customer_name="旧订单客户",
                pickup_node_id=pickup.id,
                delivery_node_id=delivery.id,
                weight=1,
                volume=2,
                priority="normal",
                status="pending",
            )
        )
        db.session.commit()

    auto_response = client.post(
        "/api/dispatch/preview",
        headers=headers,
        json={"limit": 10, "use_precise_distance": False},
    )
    assert auto_response.status_code == 200
    auto_payload = auto_response.get_json()
    assert auto_payload["data_source"] == "shipment_fact"
    assert auto_payload["summary"]["total_orders"] == 2

    legacy_response = client.post(
        "/api/dispatch/preview",
        headers=headers,
        json={"limit": 10, "data_source": "orders", "use_precise_distance": False},
    )
    assert legacy_response.status_code == 200
    legacy_payload = legacy_response.get_json()
    assert legacy_payload["data_source"] == "orders"
    assert legacy_payload["summary"]["total_orders"] == 1
