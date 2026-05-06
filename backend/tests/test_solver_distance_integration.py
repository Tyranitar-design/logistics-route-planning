import sys
from pathlib import Path

import numpy as np

BACKEND_ROOT = Path(r"D:\物流路径规划系统项目\backend")
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.optimization_engine.problems import VRPData, CVRPProblem
from app.services.optimization_engine.solvers.genetic_solver import GeneticSolver


def test_vrpdata_accepts_external_distance_and_duration_matrix():
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
        duration_matrix=np.array([
            [0.0, 5.0, 8.0],
            [5.0, 0.0, 6.0],
            [8.0, 6.0, 0.0],
        ]),
        distance_precision={"exact_count": 4, "approx_count": 2, "total_count": 9},
        source_summary={"amap": 4, "haversine_corrected": 2, "diagonal": 3},
        metadata={"distance_source": "precise_distance_provider"},
    )

    assert data.n_nodes == 3
    assert data.distance_matrix.shape == (3, 3)
    assert data.duration_matrix.shape == (3, 3)
    assert data.metadata["distance_source"] == "precise_distance_provider"
    assert data.distance_precision["exact_count"] == 4


def test_problem_evaluate_uses_injected_distance_matrix():
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
        metadata={"distance_source": "external_injected"},
    )
    problem = CVRPProblem(data)

    # 路线 0 -> 1 -> 2 -> 0 = 10 + 15 + 20 = 45
    objective = problem.evaluate([[1, 2]])
    assert float(objective[0]) == 45.0


def test_genetic_solver_returns_distance_metadata_from_unified_matrix():
    data = VRPData(
        n_customers=3,
        n_vehicles=2,
        vehicle_capacity=10,
        depot=np.array([0.0, 0.0]),
        customers=np.array([[1.0, 0.0], [2.0, 0.0], [3.0, 0.0]]),
        demands=np.array([3, 4, 2]),
        distance_matrix=np.array([
            [0.0, 10.0, 20.0, 30.0],
            [10.0, 0.0, 15.0, 25.0],
            [20.0, 15.0, 0.0, 12.0],
            [30.0, 25.0, 12.0, 0.0],
        ]),
        distance_precision={"exact_count": 10, "approx_count": 2, "total_count": 16},
        source_summary={"amap": 10, "haversine_corrected": 2, "diagonal": 4},
        metadata={"distance_source": "precise_distance_provider"},
    )
    problem = CVRPProblem(data)
    solver = GeneticSolver(pop_size=10, elite_size=2)

    result = solver.solve(problem, time_limit=1, n_gen=5)

    assert result.metadata["distance_source"] == "precise_distance_provider"
    assert result.metadata["distance_precision"]["exact_count"] == 10
    assert result.metadata["distance_unit"] == "km"
    assert isinstance(result.routes, list)
