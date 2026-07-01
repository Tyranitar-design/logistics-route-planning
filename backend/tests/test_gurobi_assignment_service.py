import importlib
import os
import sys


PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT in sys.path:
    sys.path.remove(PROJECT_ROOT)
sys.path.insert(0, PROJECT_ROOT)


def _sample_payload():
    return {
        "solver": "auto",
        "orders": [
            {"id": "O1", "weight_tons": 2.0, "volume_m3": 6.0, "priority": "urgent", "freight": 1000},
            {"id": "O2", "weight_tons": 4.0, "volume_m3": 10.0, "priority": "high", "freight": 1200},
            {"id": "O3", "weight_tons": 8.0, "volume_m3": 20.0, "priority": "low", "freight": 400},
        ],
        "vehicles": [
            {"id": "V1", "plate_number": "粤A10001", "capacity_weight_tons": 6.0, "capacity_volume_m3": 18.0},
            {"id": "V2", "plate_number": "粤A10002", "capacity_weight_tons": 5.0, "capacity_volume_m3": 16.0},
        ],
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


def test_vehicle_assignment_degrades_to_capacity_greedy_when_gurobi_unavailable():
    from app.services.gurobi_assignment_service import GurobiAssignmentService

    result = GurobiAssignmentService(capability_service=_UnavailableGurobi()).solve(_sample_payload())

    assert result["success"] is True
    assert result["solver"] == "greedy_capacity_fallback"
    assert result["provider_status"] == "degraded"
    assert result["fallback_reason"] == "GUROBI_PYTHON_API_UNAVAILABLE"
    assert result["summary"]["assigned_orders"] == 2
    assert result["summary"]["unassigned_orders"] == 1
    assert result["diagnostics"]["unassigned_reason_distribution"] == {
        "ORDER_EXCEEDS_ALL_VEHICLE_WEIGHT_CAPACITY": 1
    }
    assert result["distance_source"] == "not_required_for_assignment"
    assert result["path_source"] == "vehicle_order_assignment_milp"


def test_vehicle_assignment_uses_gurobi_branch_when_available(monkeypatch):
    from app.services.gurobi_assignment_service import GurobiAssignmentService

    service = GurobiAssignmentService(capability_service=_AvailableGurobi())
    called = {"value": False}

    def fake_solve_with_gurobi(orders, vehicles, max_orders_per_vehicle):
        called["value"] = True
        return service._format_result(
            assignments=[service._build_vehicle_assignment(vehicles[0], orders[:2])],
            unassigned_orders=[],
            objective_value=222.0,
            optimality_gap=0.0,
            model_status=2,
        )

    monkeypatch.setattr(service, "_solve_with_gurobi", fake_solve_with_gurobi)
    payload = _sample_payload()
    payload["orders"] = payload["orders"][:2]

    result = service.solve(payload)

    assert called["value"] is True
    assert result["success"] is True
    assert result["solver"] == "gurobi"
    assert result["provider_status"] == "ok"
    assert result["authenticity_level"] == "A"
    assert result["summary"]["optimality_gap"] == 0.0


def test_vehicle_assignment_explicit_greedy_is_not_reported_as_gurobi_fallback():
    from app.services.gurobi_assignment_service import GurobiAssignmentService

    payload = _sample_payload()
    payload["solver"] = "greedy"

    result = GurobiAssignmentService(capability_service=_UnavailableGurobi()).solve(payload)

    assert result["success"] is True
    assert result["solver"] == "greedy_capacity"
    assert result["provider_status"] == "ok"
    assert result["fallback_reason"] is None
    assert result["authenticity_level"] == "C"


def test_vehicle_assignment_endpoint_returns_demo_payload(monkeypatch):
    monkeypatch.setenv("DISABLE_ML_ROUTES", "1")

    for module_name in list(sys.modules):
        if module_name == "app" or module_name.startswith("app."):
            sys.modules.pop(module_name)

    from flask import Flask
    import app.routes.optimization as optimization_routes

    class FakeAssignmentService:
        def demo_payload(self):
            return {"orders": [], "vehicles": []}

        def solve(self, payload):
            return {
                "success": True,
                "solver": "greedy_capacity_fallback",
                "provider_status": "degraded",
                "fallback_reason": "GUROBI_PYTHON_API_UNAVAILABLE",
                "summary": {"assigned_orders": 1, "unassigned_orders": 0},
                "assignments": [],
                "unassigned_orders": [],
                "distance_source": "not_required_for_assignment",
                "path_source": "vehicle_order_assignment_milp",
            }

    monkeypatch.setattr(
        optimization_routes,
        "get_gurobi_assignment_service",
        lambda: FakeAssignmentService(),
    )

    app = Flask(__name__)
    app.register_blueprint(optimization_routes.optimization_bp, url_prefix="/api/optimization")
    client = app.test_client()

    response = client.get("/api/optimization/gurobi/vehicle-assignment-demo")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert payload["solver"] == "greedy_capacity_fallback"
    assert payload["path_source"] == "vehicle_order_assignment_milp"
