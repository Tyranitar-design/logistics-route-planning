import os
import sys


PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT in sys.path:
    sys.path.remove(PROJECT_ROOT)
sys.path.insert(0, PROJECT_ROOT)


def _sample_payload():
    return {
        "solver": "auto",
        "n_vehicles": 2,
        "vehicle_capacity": 7,
        "node_labels": ["仓", "A", "B", "C", "D"],
        "demands": [2, 3, 4, 2],
        "distance_matrix": [
            [0, 18, 45, 110, 95],
            [18, 0, 55, 120, 80],
            [45, 55, 0, 70, 115],
            [110, 120, 70, 0, 140],
            [95, 80, 115, 140, 0],
        ],
        "distance_source": "payload_distance_matrix",
        "data_source": "test_payload",
    }


class _UnavailableGurobi:
    def check(self, run_smoke=False):
        return {
            "available": False,
            "provider_status": "degraded",
            "fallback_reason": "GUROBI_PYTHON_API_UNAVAILABLE",
            "checks": {
                "install_dir_present": True,
                "cli_available": True,
                "license_file_present": True,
                "python_api_available": False,
                "smoke_status": "not_run",
            },
        }


class _AvailableGurobi:
    def check(self, run_smoke=False):
        return {
            "available": True,
            "provider_status": "ok",
            "fallback_reason": None,
            "checks": {
                "install_dir_present": True,
                "cli_available": True,
                "license_file_present": True,
                "python_api_available": True,
                "smoke_status": "not_run",
            },
        }


def test_vrp_degrades_to_capacity_nearest_neighbor_when_gurobi_unavailable():
    from app.services.gurobi_vrp_service import GurobiVRPService

    result = GurobiVRPService(capability_service=_UnavailableGurobi()).solve(_sample_payload())

    assert result["success"] is True
    assert result["solver"] == "nearest_neighbor_capacity_fallback"
    assert result["provider_status"] == "degraded"
    assert result["fallback_reason"] == "GUROBI_PYTHON_API_UNAVAILABLE"
    assert result["summary"]["assigned_customers"] == 4
    assert result["summary"]["unassigned_customers"] == 0
    assert result["distance_source"] == "payload_distance_matrix"
    assert result["path_source"] == "solver_node_sequence"
    assert result["constraints"] == [
        "each_customer_served_at_most_once",
        "vehicle_capacity",
        "depot_depart_return_balance",
        "subtour_elimination_mtz_when_gurobi",
    ]


def test_vrp_explicit_greedy_is_not_reported_as_gurobi_fallback():
    from app.services.gurobi_vrp_service import GurobiVRPService

    payload = _sample_payload()
    payload["solver"] = "greedy"

    result = GurobiVRPService(capability_service=_UnavailableGurobi()).solve(payload)

    assert result["success"] is True
    assert result["solver"] == "nearest_neighbor_capacity"
    assert result["provider_status"] == "ok"
    assert result["fallback_reason"] is None
    assert result["solver_quality"] == "heuristic_baseline"


def test_vrp_uses_gurobi_branch_when_available(monkeypatch):
    from app.services.gurobi_vrp_service import GurobiVRPService

    service = GurobiVRPService(capability_service=_AvailableGurobi())
    called = {"value": False}

    def fake_solve_with_gurobi(dataset, time_limit):
        called["value"] = True
        return service._format_result(
            dataset=dataset,
            routes=[
                service._route_payload(dataset, 0, [0, 1, 2, 0], 118.0, 5.0),
                service._route_payload(dataset, 1, [0, 3, 4, 0], 345.0, 6.0),
            ],
            unassigned_customers=[],
            objective_value=463.0,
            optimality_gap=0.0,
            model_status=2,
        )

    monkeypatch.setattr(service, "_solve_with_gurobi", fake_solve_with_gurobi)

    result = service.solve(_sample_payload())

    assert called["value"] is True
    assert result["success"] is True
    assert result["solver"] == "gurobi_cvrp_milp"
    assert result["provider_status"] == "ok"
    assert result["solver_quality"] == "exact_milp"
    assert result["summary"]["optimality_gap"] == 0.0
    assert result["summary"]["used_vehicles"] == 2


def test_vrp_gurobi_without_fallback_returns_actionable_failure():
    from app.services.gurobi_vrp_service import GurobiVRPService

    payload = _sample_payload()
    payload["solver"] = "gurobi"
    payload["allow_fallback"] = False

    result = GurobiVRPService(capability_service=_UnavailableGurobi()).solve(payload)

    assert result["success"] is False
    assert result["solver"] == "gurobi_cvrp_milp"
    assert result["fallback_reason"] == "GUROBI_PYTHON_API_UNAVAILABLE"
    assert result["gurobi_status"]["checks"]["python_api_available"] is False


def test_vrp_endpoint_returns_demo_payload(monkeypatch):
    monkeypatch.setenv("DISABLE_ML_ROUTES", "1")

    for module_name in list(sys.modules):
        if module_name == "app" or module_name.startswith("app."):
            sys.modules.pop(module_name)

    from flask import Flask
    import app.routes.optimization as optimization_routes

    class FakeVRPService:
        def demo_payload(self):
            return {"distance_matrix": [[0, 1], [1, 0]], "demands": [1]}

        def solve(self, payload):
            return {
                "success": True,
                "solver": "nearest_neighbor_capacity_fallback",
                "provider_status": "degraded",
                "fallback_reason": "GUROBI_PYTHON_API_UNAVAILABLE",
                "summary": {"assigned_customers": 1, "unassigned_customers": 0},
                "routes": [],
                "distance_source": "payload_distance_matrix",
                "path_source": "solver_node_sequence",
            }

    monkeypatch.setattr(
        optimization_routes,
        "get_gurobi_vrp_service",
        lambda: FakeVRPService(),
    )

    app = Flask(__name__)
    app.register_blueprint(optimization_routes.optimization_bp, url_prefix="/api/optimization")
    client = app.test_client()

    response = client.get("/api/optimization/gurobi/vrp-demo")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert payload["solver"] == "nearest_neighbor_capacity_fallback"
    assert payload["path_source"] == "solver_node_sequence"
