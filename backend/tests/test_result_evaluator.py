import sys
from pathlib import Path

import numpy as np

BACKEND_ROOT = Path(r"D:\物流路径规划系统项目\backend")
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.result_evaluator import ResultEvaluator
from app.services.optimization_engine.problems import VRPData, CVRPProblem, MultiObjectiveVRP
from app.services.optimization_engine.base import OptimizationResult, ProblemType


def make_cvrp_problem():
    data = VRPData(
        n_customers=3,
        n_vehicles=2,
        vehicle_capacity=7,
        depot=np.array([0.0, 0.0]),
        customers=np.array([[1.0, 0.0], [2.0, 0.0], [3.0, 0.0]]),
        demands=np.array([3, 4, 2]),
        distance_matrix=np.array([
            [0.0, 10.0, 20.0, 30.0],
            [10.0, 0.0, 15.0, 25.0],
            [20.0, 15.0, 0.0, 12.0],
            [30.0, 25.0, 12.0, 0.0],
        ]),
    )
    return CVRPProblem(data)


def test_result_evaluator_reports_feasible_solution():
    problem = make_cvrp_problem()
    result = OptimizationResult(
        solver_name="TestSolver",
        problem_type=ProblemType.CVRP,
        solution=[[1, 2], [3]],
        objective_values=np.array([57.0]),
        solve_time=0.12,
        gap=0.0,
        iterations=5,
        routes=[[1, 2], [3]],
        metadata={
            "distance_source": "precise_distance_provider",
            "distance_precision": {"exact_count": 10, "approx_count": 2, "total_count": 16},
            "source_summary": {"cache_exact": 10, "cache_approx": 2, "diagonal": 4},
        },
    )

    report = ResultEvaluator().evaluate(problem, result).to_dict()

    assert report["feasible"] is True
    assert report["violations"] == []
    assert report["distance_precision_summary"]["exact_count"] == 10


def test_result_evaluator_reports_missing_and_duplicate_customers():
    problem = make_cvrp_problem()
    result = OptimizationResult(
        solver_name="BadSolver",
        problem_type=ProblemType.CVRP,
        solution=[[1, 1]],
        objective_values=np.array([10.0]),
        solve_time=0.1,
        routes=[[1, 1]],
        metadata={},
    )

    report = ResultEvaluator().evaluate(problem, result).to_dict()

    assert report["feasible"] is False
    assert any("重复客户" in v for v in report["violations"])
    assert any("遗漏客户" in v for v in report["violations"])


def test_result_evaluator_reports_pareto_summary_for_multiobjective():
    data = VRPData(
        n_customers=2,
        n_vehicles=1,
        vehicle_capacity=10,
        depot=np.array([0.0, 0.0]),
        customers=np.array([[1.0, 0.0], [2.0, 0.0]]),
        demands=np.array([3, 4]),
        distance_matrix=np.array([
            [0.0, 10.0, 20.0],
            [10.0, 0.0, 15.0],
            [20.0, 15.0, 0.0],
        ]),
    )
    problem = MultiObjectiveVRP(data, service_times=np.array([5.0, 6.0]))
    result = OptimizationResult(
        solver_name="PymooNSGA2",
        problem_type=ProblemType.MULTI_OBJECTIVE,
        solution=[[1, 2]],
        objective_values=np.array([45.0, 56.0, 1.0]),
        solve_time=0.5,
        iterations=10,
        routes=[[1, 2]],
        metadata={"pareto_front_size": 2},
    )

    report = ResultEvaluator().evaluate(problem, result).to_dict()

    assert report["pareto_summary"]["enabled"] is True
    assert report["pareto_summary"]["metrics"]["pareto_count"] == 1
