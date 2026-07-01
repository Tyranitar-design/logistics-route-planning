import os
import sys


PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT in sys.path:
    sys.path.remove(PROJECT_ROOT)
sys.path.insert(0, PROJECT_ROOT)


def _sample_payload():
    return {
        "solvers": ["gurobi", "greedy", "alns", "unknown"],
        "time_limit": 1,
        "alns_iterations": 30,
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


def test_solver_benchmark_compares_gurobi_greedy_alns_and_unsupported():
    from app.services.gurobi_vrp_service import GurobiVRPService
    from app.services.solver_benchmark_service import SolverBenchmarkService

    service = SolverBenchmarkService(
        vrp_service=GurobiVRPService(capability_service=_UnavailableGurobi())
    )

    result = service.compare_small_vrp(_sample_payload())

    assert result["success"] is True
    assert result["benchmark_type"] == "small_cvrp_solver_comparison"
    assert result["data_source"] == "test_payload"
    assert result["distance_source"] == "payload_distance_matrix"
    assert result["provider_status"] == "degraded"
    assert result["authenticity_level"] == "C"

    rows = {row["solver"]: row for row in result["results"]}
    assert rows["gurobi_cvrp_milp"]["success"] is False
    assert rows["gurobi_cvrp_milp"]["fallback_reason"] == "GUROBI_PYTHON_API_UNAVAILABLE"
    assert rows["nearest_neighbor_capacity"]["success"] is True
    assert rows["nearest_neighbor_capacity"]["provider_status"] == "ok"
    assert rows["nearest_neighbor_capacity"]["feasible"] is True
    assert rows["alns"]["success"] in {True, False}
    assert rows["unknown"]["fallback_reason"] == "UNSUPPORTED_BENCHMARK_SOLVER"

    ranked_solvers = [item["solver"] for item in result["rankings"]]
    assert "nearest_neighbor_capacity" in ranked_solvers
    assert result["summary"]["best_solver"] == result["rankings"][0]["solver"]
    assert result["diagnostics"]["ranking_rule"] == "feasible_successful_rows_sorted_by_objective_then_solve_time"


def test_solver_benchmark_uses_demo_data_when_only_solvers_are_supplied():
    from app.services.gurobi_vrp_service import GurobiVRPService
    from app.services.solver_benchmark_service import SolverBenchmarkService

    service = SolverBenchmarkService(
        vrp_service=GurobiVRPService(capability_service=_UnavailableGurobi())
    )

    result = service.compare_small_vrp({"solvers": ["greedy"]})

    assert result["success"] is True
    assert result["summary"]["customer_count"] == 4
    assert result["results"][0]["solver"] == "nearest_neighbor_capacity"
    assert result["results"][0]["summary"]["assigned_customers"] == 4


def test_solver_benchmark_endpoint_contract(monkeypatch):
    monkeypatch.setenv("DISABLE_ML_ROUTES", "1")

    for module_name in list(sys.modules):
        if module_name == "app" or module_name.startswith("app."):
            sys.modules.pop(module_name)

    from flask import Flask
    import app.routes.optimization as optimization_routes

    class FakeBenchmarkService:
        def demo_payload(self):
            return {"solvers": ["greedy"]}

        def compare_small_vrp(self, payload):
            return {
                "success": True,
                "benchmark_type": "small_cvrp_solver_comparison",
                "solver": "benchmark_compare",
                "summary": {"best_solver": "nearest_neighbor_capacity"},
                "results": [],
                "rankings": [],
                "data_source": "payload_demo",
                "distance_source": "payload_distance_matrix",
                "path_source": "solver_node_sequence+optimization_engine_routes",
                "provider_status": "ok",
                "fallback_reason": None,
                "authenticity_level": "B",
            }

    monkeypatch.setattr(
        optimization_routes,
        "get_solver_benchmark_service",
        lambda: FakeBenchmarkService(),
    )

    app = Flask(__name__)
    app.register_blueprint(optimization_routes.optimization_bp, url_prefix="/api/optimization")
    client = app.test_client()

    demo_response = client.get("/api/optimization/solver-benchmark-demo")
    post_response = client.post("/api/optimization/gurobi/compare-small-vrp", json={"solvers": ["greedy"]})

    assert demo_response.status_code == 200
    assert post_response.status_code == 200
    assert demo_response.get_json()["benchmark_type"] == "small_cvrp_solver_comparison"
    assert post_response.get_json()["summary"]["best_solver"] == "nearest_neighbor_capacity"
