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
    from app.models import Node, Order, User, Vehicle

    app = create_app("testing")
    app.config["JWT_SECRET_KEY"] = "dispatch-smart-contract-secret"

    with app.app_context():
        db.create_all()

        user = User(username="admin", real_name="管理员", role="admin", status="active")
        user.password = "admin123"
        db.session.add(user)

        pickup = Node(
            name="北京仓库",
            code="BJ-WH",
            type="warehouse",
            city="北京",
            province="北京",
            address="北京市仓库",
            longitude=116.4074,
            latitude=39.9042,
            status="active",
        )
        delivery = Node(
            name="天津客户",
            code="TJ-CUST",
            type="customer",
            city="天津",
            province="天津",
            address="天津市客户",
            longitude=117.2000,
            latitude=39.1333,
            status="active",
        )
        db.session.add_all([pickup, delivery])
        db.session.flush()

        db.session.add(
            Vehicle(
                plate_number="京A-TEST",
                vehicle_type="truck",
                load_capacity=10,
                volume_capacity=40,
                capacity=10,
                status="空闲",
            )
        )
        db.session.add(
            Order(
                order_number="SO-DISPATCH-001",
                customer_name="测试客户",
                pickup_node_id=pickup.id,
                delivery_node_id=delivery.id,
                weight=2,
                volume=5,
                priority="normal",
                status="pending",
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


def test_smart_dispatch_accepts_local_statuses_and_returns_display_truth_contract(monkeypatch):
    client, headers = _build_client(monkeypatch)

    response = client.post(
        "/api/dispatch/smart",
        headers=headers,
        json={
            "algorithm": "greedy",
            "weights": {"cost": 0.4, "time": 0.3, "satisfaction": 0.3},
            "consider_weather": False,
            "consider_traffic": False,
        },
    )

    assert response.status_code == 200, response.get_json()
    payload = response.get_json()

    assert payload["success"] is True
    assert payload["plans"]
    assert payload["summary"]["assigned_orders"] == 1
    assert payload["summary"]["total_orders_assigned"] == 1
    assert payload["summary"]["total_orders_unassigned"] == 0
    assert payload["summary"]["total_vehicles_used"] == 1
    assert payload["summary"]["total_distance_km"] > 0
    assert payload["summary"]["average_cost_per_order"] > 0
    assert payload["distance_source"] == "haversine_legacy_dispatch"
    assert payload["path_source"] == "dispatch_assignment_sequence"
    assert payload["authenticity_level"] == "C"
    assert payload["fallback_reason"]
