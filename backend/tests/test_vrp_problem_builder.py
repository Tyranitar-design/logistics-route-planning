import sys
from pathlib import Path

BACKEND_ROOT = Path(r"D:\物流路径规划系统项目\backend")
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.vrp_problem_builder import VRPProblemBuilder
from app.services.optimization_engine.base import ProblemType


def test_vrp_problem_builder_builds_cvrp_problem():
    builder = VRPProblemBuilder()
    payload = {
        "depot": [116.397, 39.908],
        "customers": [[121.473, 31.230], [113.2644, 23.1291]],
        "demands": [3, 4],
        "capacity": 10,
        "use_precise_distance": False,
    }

    result = builder.build_from_payload(payload)

    assert result.problem_type == ProblemType.CVRP
    assert result.vrp_data.n_customers == 2
    assert result.build_metadata["problem_type"] == "cvrp"
    assert result.build_metadata["has_service_times"] is False


def test_vrp_problem_builder_builds_multiobjective_problem():
    builder = VRPProblemBuilder()
    payload = {
        "problem_type": "multi_objective",
        "depot": [116.397, 39.908],
        "customers": [[121.473, 31.230], [113.2644, 23.1291]],
        "demands": [3, 4],
        "service_times": [5, 6],
        "capacity": 10,
        "use_precise_distance": False,
    }

    result = builder.build_from_payload(payload)

    assert result.problem_type == ProblemType.MULTI_OBJECTIVE
    assert result.build_metadata["problem_type"] == "multi_objective"
    assert result.build_metadata["has_service_times"] is True
    assert list(result.problem.service_times) == [5.0, 6.0]
