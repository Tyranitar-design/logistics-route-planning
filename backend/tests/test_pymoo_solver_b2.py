import sys
from pathlib import Path

import numpy as np

BACKEND_ROOT = Path(r"D:\物流路径规划系统项目\backend")
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.optimization_engine.problems import VRPData, CVRPProblem
from app.services.optimization_engine.solvers.pymoo_solver import (
    PymooNSGA2Solver,
    decode_permutation_to_routes,
)


def test_decode_permutation_to_routes_uses_capacity_repair():
    data = type(
        "DummyData",
        (),
        {
            "demands": [3, 4, 2],
            "vehicle_capacity": 7,
        },
    )()

    routes = decode_permutation_to_routes([0, 1, 2], data)
    assert routes == [[1, 2], [3]]


def test_pymoo_solver_is_available_or_cleanly_skipped():
    solver = PymooNSGA2Solver(pop_size=10)
    assert isinstance(solver.is_available(), bool)


def test_pymoo_solver_b2_metadata_structure_without_running_solver():
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
        distance_precision={"exact_count": 10, "approx_count": 2, "total_count": 16},
        source_summary={"amap": 10, "haversine_corrected": 2, "diagonal": 4},
        metadata={"distance_source": "precise_distance_provider"},
    )
    problem = CVRPProblem(data)
    solver = PymooNSGA2Solver(pop_size=10)

    # 不强行运行外部依赖，只校验 B2 接口层与 B1 元数据不冲突
    assert problem.data.metadata["distance_source"] == "precise_distance_provider"
    assert problem.data.distance_precision["exact_count"] == 10
    assert solver.pop_size == 10
    assert solver.crossover_prob == 0.9
