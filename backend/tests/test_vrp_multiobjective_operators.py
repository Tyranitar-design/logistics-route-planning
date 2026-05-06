import sys
from pathlib import Path

BACKEND_ROOT = Path(r"D:\物流路径规划系统项目\backend")
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.optimization_engine.operators.vrp_crossover import (
    order_crossover,
    pmx_crossover,
)
from app.services.optimization_engine.operators.vrp_mutation import (
    swap_mutation,
    two_opt_mutation,
    relocation_mutation,
)
from app.services.optimization_engine.operators.vrp_repair import (
    repair_capacity_feasibility,
)


def assert_valid_permutation(result, expected_values):
    assert sorted(result) == sorted(expected_values)
    assert len(result) == len(expected_values)
    assert len(set(result)) == len(expected_values)


def test_order_crossover_returns_valid_permutation():
    p1 = [1, 2, 3, 4, 5, 6]
    p2 = [4, 1, 2, 6, 5, 3]
    child = order_crossover(p1, p2, (1, 3))
    assert_valid_permutation(child, p1)


def test_pmx_crossover_returns_valid_permutation():
    p1 = [1, 2, 3, 4, 5, 6]
    p2 = [4, 1, 2, 6, 5, 3]
    child = pmx_crossover(p1, p2, (1, 3))
    assert_valid_permutation(child, p1)


def test_swap_mutation_returns_valid_permutation():
    base = [1, 2, 3, 4, 5, 6]
    child = swap_mutation(base, (1, 4))
    assert_valid_permutation(child, base)
    assert child != base


def test_two_opt_mutation_returns_valid_permutation():
    base = [1, 2, 3, 4, 5, 6]
    child = two_opt_mutation(base, (1, 4))
    assert_valid_permutation(child, base)
    assert child != base


def test_relocation_mutation_returns_valid_permutation():
    base = [1, 2, 3, 4, 5, 6]
    child = relocation_mutation(base, (4, 1))
    assert_valid_permutation(child, base)
    assert child != base


def test_repair_capacity_feasibility_returns_non_overloaded_routes():
    routes = repair_capacity_feasibility(
        customer_sequence=[1, 2, 3, 4, 5],
        demands=[3, 4, 2, 5, 1],
        vehicle_capacity=7,
    )

    assert routes == [[1, 2], [3, 4], [5]]

    flat = [c for route in routes for c in route]
    assert flat == [1, 2, 3, 4, 5]

    demands = [3, 4, 2, 5, 1]
    for route in routes:
        assert sum(demands[c - 1] for c in route) <= 7
