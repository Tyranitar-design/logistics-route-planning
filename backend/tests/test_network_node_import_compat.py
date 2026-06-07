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
    app.config["JWT_SECRET_KEY"] = "network-import-test-secret"

    with app.app_context():
        db.create_all()

        user = User(username="admin", real_name="管理员", role="admin", status="active")
        user.password = "admin123"
        db.session.add(user)

        db.session.add_all([
            Node(
                name="北京仓库",
                type="warehouse",
                province="北京市",
                city="北京市",
                longitude=116.45747,
                latitude=39.908823,
                capacity=500,
                status="active",
            ),
            Node(
                name="广州配送站",
                type="distribution",
                province="广东省",
                city="广州市",
                longitude=113.264385,
                latitude=23.129112,
                capacity=300,
                status="active",
            ),
            Node(
                name="永安站点A",
                type="station",
                province="福建省",
                city="永安",
                longitude=117.36525,
                latitude=25.974086,
                capacity=120,
                status="active",
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


def test_network_import_nodes_treats_station_as_customer_source(monkeypatch):
    client, headers = _build_client(monkeypatch)

    response = client.post(
        "/api/network/import/nodes",
        headers=headers,
        json={},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["status"] == "success"
    assert payload["total_customers"] == 1
    assert payload["total_candidates"] == 2
    assert payload["customers"][0]["name"] == "永安站点A"
    assert payload["distance_source"] == "derived_from_input"
    assert payload["path_source"] == "node_import_dataset"
    assert payload["authenticity_level"] == "C"
    assert payload["fallback_reason"] == "imported_nodes_are_coordinate_dataset_not_navigation_path"
