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
    from app.models import Node, Route, User, db
    from app.models.layered_data import DataImportBatch, ShipmentFact

    app = create_app("testing")
    app.config["JWT_SECRET_KEY"] = "node-route-audit-test-secret"

    with app.app_context():
        db.create_all()

        user = User(username="admin", real_name="管理员", role="admin", status="active")
        user.password = "admin123"
        db.session.add(user)

        db.session.add_all(
            [
                Node(
                    id=1,
                    name="北京仓",
                    type="warehouse",
                    city="北京市",
                    longitude=116.40,
                    latitude=39.90,
                    status="active",
                ),
                Node(
                    id=2,
                    name="上海站",
                    type="distribution",
                    city="上海市",
                    longitude=121.47,
                    latitude=31.23,
                    status="active",
                ),
                Node(
                    id=3,
                    name="缺坐标站",
                    type="distribution",
                    city="深圳市",
                    status="active",
                ),
                Node(
                    id=4,
                    name="经纬度反写站",
                    type="distribution",
                    city="广州",
                    longitude=23.13,
                    latitude=113.26,
                    status="active",
                ),
            ]
        )

        db.session.add_all(
            [
                Route(id=1, name="京沪异常短线", start_node_id=1, end_node_id=2, distance=100, duration=2),
                Route(id=2, name="悬空线路", start_node_id=1, end_node_id=999, distance=20, duration=1),
                Route(id=3, name="缺坐标线路", start_node_id=1, end_node_id=3, distance=20, duration=1),
            ]
        )

        batch = DataImportBatch(
            dataset_source="pytest",
            raw_record_count=1,
            fact_record_count=1,
            quarantine_record_count=0,
            quality_status="ok",
        )
        db.session.add(batch)
        db.session.flush()
        db.session.add(
            ShipmentFact(
                batch_id=batch.id,
                external_shipment_id="S-1",
                external_order_id="O-1",
                origin_city_std="北京市",
                destination_city_std="成都市",
                origin_lng=116.4,
                origin_lat=39.9,
                destination_lng=104.0,
                destination_lat=30.6,
                standard_status="pending",
                geo_status="resolved",
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


def test_node_route_audit_service_flags_foundation_issues(monkeypatch):
    client, headers = _build_client(monkeypatch)

    response = client.get("/api/nodes/route-coordinate-audit?sample_limit=10", headers=headers)

    assert response.status_code == 200, response.get_json()
    payload = response.get_json()
    assert payload["success"] is True
    assert payload["distance_source"] == "haversine_geodesic_audit"
    assert payload["path_source"] == "route_table_edges"
    assert payload["summary"]["nodes_total"] == 4
    assert payload["summary"]["routes_total"] == 3
    assert payload["nodes"]["summary"]["missing_coordinates"] == 1
    assert payload["nodes"]["summary"]["suspected_lng_lat_swapped"] == 1
    assert payload["routes"]["summary"]["dangling_node_reference"] == 1
    assert payload["routes"]["summary"]["endpoint_missing_coordinates"] == 1
    assert payload["routes"]["summary"]["distance_shorter_than_geodesic"] == 1
    assert payload["shipment_facts"]["summary"]["destination_cities_without_nodes"] == 1
    assert payload["recommendations"]
