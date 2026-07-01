import os
import sys


PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT in sys.path:
    sys.path.remove(PROJECT_ROOT)
sys.path.insert(0, PROJECT_ROOT)


def _sample_payload():
    return {
        "solver": "auto",
        "transport_cost_per_km": 2.0,
        "max_facilities": 2,
        "customers": [
            {"id": "C1", "name": "广州需求", "demand": 100, "lat": 23.1291, "lon": 113.2644},
            {"id": "C2", "name": "深圳需求", "demand": 150, "lat": 22.5431, "lon": 114.0579},
            {"id": "C3", "name": "东莞需求", "demand": 80, "lat": 23.0207, "lon": 113.7518},
        ],
        "candidates": [
            {"id": "F1", "name": "广州仓", "capacity": 220, "fixed_cost": 40000, "lat": 23.1291, "lon": 113.2644},
            {"id": "F2", "name": "深圳仓", "capacity": 200, "fixed_cost": 42000, "lat": 22.5431, "lon": 114.0579},
            {"id": "F3", "name": "佛山仓", "capacity": 160, "fixed_cost": 35000, "lat": 23.0215, "lon": 113.1214},
        ],
        "data_source": "test_payload",
        "distance_source": "haversine_payload",
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


def test_network_design_degrades_to_greedy_when_gurobi_unavailable():
    from app.services.gurobi_network_design_service import GurobiNetworkDesignService

    result = GurobiNetworkDesignService(capability_service=_UnavailableGurobi()).solve(_sample_payload())

    assert result["success"] is True
    assert result["solver"] == "greedy_facility_capacity_fallback"
    assert result["provider_status"] == "degraded"
    assert result["fallback_reason"] == "GUROBI_PYTHON_API_UNAVAILABLE"
    assert result["summary"]["assigned_customers"] >= 2
    assert result["summary"]["selected_facilities"] <= 2
    assert result["data_source"] == "test_payload"
    assert result["distance_source"] == "haversine_payload"
    assert result["path_source"] == "facility_customer_assignment"
    assert result["constraints"] == [
        "customer_assigned_or_unmet",
        "open_facility_capacity",
        "assignment_only_to_open_facility",
        "optional_max_facilities",
    ]


def test_network_design_explicit_greedy_is_not_gurobi_fallback():
    from app.services.gurobi_network_design_service import GurobiNetworkDesignService

    payload = _sample_payload()
    payload["solver"] = "greedy"

    result = GurobiNetworkDesignService(capability_service=_UnavailableGurobi()).solve(payload)

    assert result["success"] is True
    assert result["solver"] == "greedy_facility_capacity"
    assert result["provider_status"] == "ok"
    assert result["fallback_reason"] is None
    assert result["solver_quality"] == "heuristic_baseline"


def test_network_design_uses_gurobi_branch_when_available(monkeypatch):
    from app.services.gurobi_network_design_service import GurobiNetworkDesignService

    service = GurobiNetworkDesignService(capability_service=_AvailableGurobi())
    called = {"value": False}

    def fake_solve_with_gurobi(dataset, time_limit):
        called["value"] = True
        return service._format_result(
            dataset=dataset,
            open_indices=[0, 1],
            assignments=[
                service._assignment_payload(dataset, 0, 0),
                service._assignment_payload(dataset, 1, 1),
                service._assignment_payload(dataset, 2, 0),
            ],
            unassigned_customers=[],
            objective_value=83000.0,
            optimality_gap=0.0,
            model_status=2,
        )

    monkeypatch.setattr(service, "_solve_with_gurobi", fake_solve_with_gurobi)

    result = service.solve(_sample_payload())

    assert called["value"] is True
    assert result["success"] is True
    assert result["solver"] == "gurobi_cflp_milp"
    assert result["provider_status"] == "ok"
    assert result["solver_quality"] == "exact_milp"
    assert result["summary"]["optimality_gap"] == 0.0
    assert result["summary"]["demand_coverage_rate"] == 1.0


def test_network_design_gurobi_without_fallback_returns_actionable_failure():
    from app.services.gurobi_network_design_service import GurobiNetworkDesignService

    payload = _sample_payload()
    payload["solver"] = "gurobi"
    payload["allow_fallback"] = False

    result = GurobiNetworkDesignService(capability_service=_UnavailableGurobi()).solve(payload)

    assert result["success"] is False
    assert result["solver"] == "gurobi_cflp_milp"
    assert result["fallback_reason"] == "GUROBI_PYTHON_API_UNAVAILABLE"
    assert result["gurobi_status"]["checks"]["python_api_available"] is False


def test_network_design_endpoint_returns_demo_payload(monkeypatch):
    monkeypatch.setenv("DISABLE_ML_ROUTES", "1")

    for module_name in list(sys.modules):
        if module_name == "app" or module_name.startswith("app."):
            sys.modules.pop(module_name)

    from flask import Flask
    import app.routes.optimization as optimization_routes

    class FakeNetworkDesignService:
        def demo_payload(self):
            return {"customers": [], "candidates": []}

        def solve(self, payload):
            return {
                "success": True,
                "solver": "greedy_facility_capacity_fallback",
                "provider_status": "degraded",
                "fallback_reason": "GUROBI_PYTHON_API_UNAVAILABLE",
                "summary": {"assigned_customers": 1, "unassigned_customers": 0},
                "selected_facilities": [],
                "assignments": [],
                "distance_source": "haversine_payload",
                "path_source": "facility_customer_assignment",
            }

    monkeypatch.setattr(
        optimization_routes,
        "get_gurobi_network_design_service",
        lambda: FakeNetworkDesignService(),
    )

    app = Flask(__name__)
    app.register_blueprint(optimization_routes.optimization_bp, url_prefix="/api/optimization")
    client = app.test_client()

    response = client.get("/api/optimization/gurobi/network-design-demo")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert payload["solver"] == "greedy_facility_capacity_fallback"
    assert payload["path_source"] == "facility_customer_assignment"
