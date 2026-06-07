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
    from app.models import User, db

    app = create_app("testing")
    app.config["JWT_SECRET_KEY"] = "network-truth-shell-test-secret"

    with app.app_context():
        db.create_all()

        user = User(username="admin", real_name="管理员", role="admin", status="active")
        user.password = "admin123"
        db.session.add(user)
        db.session.commit()

    client = app.test_client()
    login_response = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "admin123"},
    )
    token = login_response.get_json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    return client, headers


def _customers():
    return [
        {"id": 1, "name": "C1", "lat": 39.9, "lon": 116.4, "demand": 80},
        {"id": 2, "name": "C2", "lat": 39.8, "lon": 116.5, "demand": 60},
    ]


def _candidates():
    return [
        {"id": 101, "name": "F1", "lat": 39.85, "lon": 116.45, "capacity": 500, "fixed_cost": 100000},
        {"id": 102, "name": "F2", "lat": 39.75, "lon": 116.35, "capacity": 500, "fixed_cost": 80000},
    ]


def _assert_truth_shell(payload, distance_source, path_source, authenticity_level="C"):
    assert payload["distance_source"] == distance_source
    assert payload["path_source"] == path_source
    assert payload["authenticity_level"] == authenticity_level
    assert payload["fallback_reason"]


def test_network_core_location_solvers_return_truth_shell(monkeypatch):
    client, headers = _build_client(monkeypatch)

    cases = [
        (
            "/api/network/location/p-median",
            {"customers": _customers(), "candidates": _candidates(), "num_facilities": 1, "solver": "CBC"},
            "facility_assignment",
        ),
        (
            "/api/network/location/covering",
            {"customers": _customers(), "candidates": _candidates(), "service_radius": 1000},
            "coverage_assignment",
        ),
        (
            "/api/network/location/cflp",
            {"customers": _customers(), "candidates": _candidates(), "transport_cost_per_km": 2.0},
            "facility_flow_assignment",
        ),
        (
            "/api/network/location/multi-objective",
            {
                "customers": _customers(),
                "candidates": _candidates(),
                "num_facilities": 1,
                "weights": {"cost": 0.4, "distance": 0.4, "balance": 0.2},
                "solver": "CBC",
            },
            "facility_assignment_weighted",
        ),
        (
            "/api/network/location/dynamic",
            {
                "periods": [
                    {"name": "P1", "customers": _customers(), "demand_growth": 1.0},
                    {"name": "P2", "customers": _customers(), "demand_growth": 1.1},
                ],
                "candidates": _candidates(),
                "initial_facilities": 1,
            },
            "dynamic_facility_plan",
        ),
    ]

    for url, payload, path_source in cases:
        response = client.post(url, headers=headers, json=payload)
        assert response.status_code == 200, response.get_json()
        data = response.get_json()
        assert data["status"] == "success"
        _assert_truth_shell(data, "haversine", path_source)


def test_network_support_endpoints_return_synthetic_and_projection_truth(monkeypatch):
    client, headers = _build_client(monkeypatch)

    generated = client.post(
        "/api/network/test-data/generate",
        headers=headers,
        json={"num_customers": 5, "num_candidates": 3, "region": "china"},
    )
    assert generated.status_code == 200, generated.get_json()
    _assert_truth_shell(generated.get_json(), "synthetic_generator", "synthetic_sampling", "D")

    visualized = client.post(
        "/api/network/visualize",
        headers=headers,
        json={
            "customers": _customers(),
            "candidates": _candidates(),
            "selected_indices": [0],
            "assignments": {1: 101},
        },
    )
    assert visualized.status_code == 200, visualized.get_json()
    _assert_truth_shell(visualized.get_json(), "derived_from_input", "visualization_projection")


def test_network_scenario_chain_returns_truth_shell(monkeypatch):
    client, headers = _build_client(monkeypatch)

    scenario_payload = {
        "name": "Scenario A",
        "algorithm": "p-median",
        "customers": _customers(),
        "candidates": _candidates(),
        "parameters": {"numFacilities": 1},
        "selected_facilities": [_candidates()[0]],
        "assignments": {"1": 101, "2": 101},
        "total_cost": 1000,
        "total_distance": 100,
    }

    created = client.post("/api/network/scenarios", headers=headers, json=scenario_payload)
    assert created.status_code == 200, created.get_json()
    created_payload = created.get_json()
    _assert_truth_shell(created_payload, "derived_from_scenario", "scenario_create")

    scenario_id = created_payload["scenario_id"]

    listed = client.get("/api/network/scenarios", headers=headers)
    assert listed.status_code == 200, listed.get_json()
    _assert_truth_shell(listed.get_json(), "derived_from_scenario", "scenario_index")

    fetched = client.get(f"/api/network/scenarios/{scenario_id}", headers=headers)
    assert fetched.status_code == 200, fetched.get_json()
    _assert_truth_shell(fetched.get_json(), "derived_from_scenario", "scenario_snapshot")

    updated = client.put(
        f"/api/network/scenarios/{scenario_id}",
        headers=headers,
        json={"name": "Scenario A Updated"},
    )
    assert updated.status_code == 200, updated.get_json()
    _assert_truth_shell(updated.get_json(), "derived_from_scenario", "scenario_update")

    scenario_payload["name"] = "Scenario B"
    second = client.post("/api/network/scenarios", headers=headers, json=scenario_payload)
    assert second.status_code == 200, second.get_json()
    second_id = second.get_json()["scenario_id"]

    compared = client.get(f"/api/network/scenarios/{scenario_id}/compare/{second_id}", headers=headers)
    assert compared.status_code == 200, compared.get_json()
    _assert_truth_shell(compared.get_json(), "derived_from_scenario", "scenario_comparison")

    deleted = client.delete(f"/api/network/scenarios/{second_id}", headers=headers)
    assert deleted.status_code == 200, deleted.get_json()
    _assert_truth_shell(deleted.get_json(), "derived_from_scenario", "scenario_delete")
