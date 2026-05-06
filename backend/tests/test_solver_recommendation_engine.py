import sys
from pathlib import Path

BACKEND_ROOT = Path(r"D:\物流路径规划系统项目\backend")
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.solver_recommendation_engine import SolverRecommendationEngine
from app.services.optimization_engine.base import ProblemType, SolverType


def test_solver_recommendation_engine_prefers_gurobi_for_small_high_accuracy():
    engine = SolverRecommendationEngine()
    rec = engine.recommend(
        ProblemType.CVRP,
        n_customers=10,
        require_high_accuracy=True,
        available_solvers=[SolverType.GUROBI, SolverType.ORTOOLS],
    )

    assert rec.recommended_solver == SolverType.GUROBI
    assert "高精度" in "".join(rec.reasoning)


def test_solver_recommendation_engine_prefers_ortools_for_fast_response():
    engine = SolverRecommendationEngine()
    rec = engine.recommend(
        ProblemType.CVRP,
        n_customers=120,
        prefer_fast_response=True,
        available_solvers=[SolverType.ORTOOLS, SolverType.ALNS, SolverType.GENETIC],
    )

    assert rec.recommended_solver == SolverType.ORTOOLS
    assert rec.problem_summary["scale"] == "large"


def test_solver_recommendation_engine_prefers_pymoo_for_multiobjective():
    engine = SolverRecommendationEngine()
    rec = engine.recommend(
        ProblemType.MULTI_OBJECTIVE,
        n_customers=30,
        available_solvers=[SolverType.PYMOO_NSGA2, SolverType.PYMOO_NSGA3, SolverType.ORTOOLS],
    )

    assert rec.recommended_solver == SolverType.PYMOO_NSGA2
    assert rec.alternatives[0] == SolverType.PYMOO_NSGA3
