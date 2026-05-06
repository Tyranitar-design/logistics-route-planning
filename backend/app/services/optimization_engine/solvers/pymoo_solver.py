"""
pymoo 求解器
============

使用 pymoo 求解多目标优化问题

B2 升级：
- 接入 VRP 专用交叉算子（OX / PMX）
- 接入 VRP 专用变异算子（Swap / 2-opt / Relocation）
- 接入容量可行性修复器
- 保留 B1 距离精度元数据透传

作者: 小彩
日期: 2026-04-19
"""

import numpy as np
from typing import Optional

from ..base import (
    OptimizationSolver,
    OptimizationProblem,
    OptimizationResult,
    SolverType,
    SolverRegistry,
    timeit
)
from ..operators import (
    order_crossover,
    pmx_crossover,
    swap_mutation,
    two_opt_mutation,
    relocation_mutation,
    repair_capacity_feasibility,
)


class VRPPermutationCrossover:
    """供 pymoo Crossover 调用的 VRP permutation crossover 包装器。"""

    def __init__(self, prob: float = 0.9, method: str = "ox"):
        from pymoo.core.crossover import Crossover

        class _Impl(Crossover):
            def __init__(self, outer_prob: float, outer_method: str):
                super().__init__(2, 2, prob=outer_prob)
                self.method = outer_method

            def _do(self, problem, X, **kwargs):
                _, n_matings, n_var = X.shape
                Y = np.empty((self.n_offsprings, n_matings, n_var), dtype=X.dtype)

                for k in range(n_matings):
                    p1 = X[0, k].astype(int).tolist()
                    p2 = X[1, k].astype(int).tolist()

                    if self.method == "pmx":
                        c1 = pmx_crossover(p1, p2)
                        c2 = pmx_crossover(p2, p1)
                    else:
                        c1 = order_crossover(p1, p2)
                        c2 = order_crossover(p2, p1)

                    Y[0, k] = np.asarray(c1, dtype=X.dtype)
                    Y[1, k] = np.asarray(c2, dtype=X.dtype)

                return Y

        self.impl = _Impl(prob, method)


class VRPPermutationMutation:
    """供 pymoo Mutation 调用的 VRP mutation 包装器。"""

    def __init__(self, prob: float = 1.0):
        from pymoo.core.mutation import Mutation

        class _Impl(Mutation):
            def __init__(self, outer_prob: float):
                super().__init__(prob=outer_prob)

            def _do(self, problem, X, **kwargs):
                Y = X.copy()
                for i in range(len(Y)):
                    perm = Y[i].astype(int).tolist()
                    choice = np.random.choice(["swap", "two_opt", "relocate"])
                    if choice == "swap":
                        mutated = swap_mutation(perm)
                    elif choice == "two_opt":
                        mutated = two_opt_mutation(perm)
                    else:
                        mutated = relocation_mutation(perm)
                    Y[i] = np.asarray(mutated, dtype=X.dtype)
                return Y

        self.impl = _Impl(prob)


def decode_permutation_to_routes(perm, data):
    """统一解码：排列 -> 容量可行路线集合。"""
    customer_sequence = [int(idx) + 1 for idx in perm]
    return repair_capacity_feasibility(
        customer_sequence=customer_sequence,
        demands=list(data.demands),
        vehicle_capacity=float(data.vehicle_capacity),
    )


@SolverRegistry.register(SolverType.PYMOO_NSGA2)
class PymooNSGA2Solver(OptimizationSolver):
    """pymoo NSGA-II 求解器"""

    def __init__(self,
                 pop_size: int = 100,
                 crossover_prob: float = 0.9,
                 mutation_prob: float = None,
                 **kwargs):
        super().__init__("NSGA-II (pymoo)", SolverType.PYMOO_NSGA2)
        self.pop_size = pop_size
        self.crossover_prob = crossover_prob
        self.mutation_prob = mutation_prob
        self.parameters.update(kwargs)

    def is_available(self) -> bool:
        try:
            from pymoo.algorithms.moo.nsga2 import NSGA2
            return True
        except ImportError:
            return False

    @timeit
    def solve(self,
              problem: OptimizationProblem,
              time_limit: float = 60.0,
              n_gen: int = 100,
              **kwargs) -> OptimizationResult:
        from pymoo.core.problem import Problem as PymooProblem
        from pymoo.algorithms.moo.nsga2 import NSGA2
        from pymoo.optimize import minimize
        from pymoo.termination import get_termination
        from pymoo.operators.sampling.rnd import PermutationRandomSampling

        class WrappedProblem(PymooProblem):
            def __init__(self, orig_problem):
                self.orig = orig_problem
                super().__init__(
                    n_var=orig_problem.n_variables,
                    n_obj=orig_problem.n_objectives,
                    vtype=int,
                    xl=0,
                    xu=orig_problem.n_variables - 1
                )

            def _evaluate(self, X, out, *args, **kwargs):
                n_pop = X.shape[0]
                F = np.zeros((n_pop, self.n_obj))
                for i in range(n_pop):
                    routes = self._decode_routes(X[i])
                    F[i] = self.orig.evaluate(routes)
                out["F"] = F

            def _decode_routes(self, perm):
                return decode_permutation_to_routes(perm, self.orig.data)

        data = problem.data
        distance_matrix = np.asarray(data.distance_matrix, dtype=float)
        expected_shape = (data.n_customers + 1, data.n_customers + 1)
        if distance_matrix.shape != expected_shape:
            raise ValueError(
                f"distance_matrix 维度错误，期望 {expected_shape}，实际 {distance_matrix.shape}"
            )

        pymoo_problem = WrappedProblem(problem)
        crossover = VRPPermutationCrossover(
            prob=self.crossover_prob,
            method=kwargs.get('crossover_method', 'ox')
        ).impl
        mutation = VRPPermutationMutation(
            prob=self.mutation_prob if self.mutation_prob is not None else 1.0
        ).impl

        algorithm = NSGA2(
            pop_size=self.pop_size,
            sampling=PermutationRandomSampling(),
            crossover=crossover,
            mutation=mutation,
            eliminate_duplicates=True
        )

        termination = get_termination("n_gen", n_gen)
        res = minimize(
            pymoo_problem,
            algorithm,
            termination,
            seed=42,
            verbose=False
        )

        best_idx = np.argmin(res.F[:, 0])
        best_routes = pymoo_problem._decode_routes(res.X[best_idx])

        # 构建真实 Pareto 前沿数据
        pareto_front = res.F.tolist()

        return OptimizationResult(
            solver_name=self.name,
            problem_type=problem.problem_type,
            solution=best_routes,
            objective_values=res.F[best_idx],
            solve_time=0.0,
            iterations=n_gen,
            routes=best_routes,
            metadata={
                'pareto_front_size': len(res.F),
                'pareto_front': pareto_front,
                'distance_source': getattr(data, 'metadata', {}).get('distance_source', 'unknown'),
                'distance_precision': getattr(data, 'distance_precision', {}),
                'source_summary': getattr(data, 'source_summary', {}),
                'distance_unit': 'km',
                'crossover_method': kwargs.get('crossover_method', 'ox'),
                'mutation_methods': ['swap', 'two_opt', 'relocate'],
                'repair_method': 'capacity_feasibility',
            }
        )


@SolverRegistry.register(SolverType.PYMOO_NSGA3)
class PymooNSGA3Solver(OptimizationSolver):
    """pymoo NSGA-III 求解器（高维多目标）"""

    def __init__(self,
                 pop_size: int = 100,
                 n_partitions: int = 12,
                 **kwargs):
        super().__init__("NSGA-III (pymoo)", SolverType.PYMOO_NSGA3)
        self.pop_size = pop_size
        self.n_partitions = n_partitions
        self.parameters.update(kwargs)

    def is_available(self) -> bool:
        try:
            from pymoo.algorithms.moo.nsga3 import NSGA3
            return True
        except ImportError:
            return False

    @timeit
    def solve(self,
              problem: OptimizationProblem,
              time_limit: float = 60.0,
              n_gen: int = 100,
              **kwargs) -> OptimizationResult:
        from pymoo.core.problem import Problem as PymooProblem
        from pymoo.algorithms.moo.nsga3 import NSGA3
        from pymoo.optimize import minimize
        from pymoo.termination import get_termination
        from pymoo.operators.sampling.rnd import PermutationRandomSampling
        from pymoo.util.ref_dirs import get_reference_directions

        class WrappedProblem(PymooProblem):
            def __init__(self, orig_problem):
                self.orig = orig_problem
                super().__init__(
                    n_var=orig_problem.n_variables,
                    n_obj=orig_problem.n_objectives,
                    vtype=int,
                    xl=0,
                    xu=orig_problem.n_variables - 1
                )

            def _evaluate(self, X, out, *args, **kwargs):
                n_pop = X.shape[0]
                F = np.zeros((n_pop, self.n_obj))
                for i in range(n_pop):
                    routes = self._decode_routes(X[i])
                    F[i] = self.orig.evaluate(routes)
                out["F"] = F

            def _decode_routes(self, perm):
                return decode_permutation_to_routes(perm, self.orig.data)

        data = problem.data
        distance_matrix = np.asarray(data.distance_matrix, dtype=float)
        expected_shape = (data.n_customers + 1, data.n_customers + 1)
        if distance_matrix.shape != expected_shape:
            raise ValueError(
                f"distance_matrix 维度错误，期望 {expected_shape}，实际 {distance_matrix.shape}"
            )

        pymoo_problem = WrappedProblem(problem)
        ref_dirs = get_reference_directions(
            "das-dennis",
            problem.n_objectives,
            n_partitions=self.n_partitions
        )

        crossover = VRPPermutationCrossover(
            prob=kwargs.get('crossover_prob', 0.9),
            method=kwargs.get('crossover_method', 'ox')
        ).impl
        mutation = VRPPermutationMutation(
            prob=kwargs.get('mutation_prob', 1.0)
        ).impl

        algorithm = NSGA3(
            pop_size=len(ref_dirs),
            ref_dirs=ref_dirs,
            sampling=PermutationRandomSampling(),
            crossover=crossover,
            mutation=mutation,
            eliminate_duplicates=True
        )

        termination = get_termination("n_gen", n_gen)
        res = minimize(
            pymoo_problem,
            algorithm,
            termination,
            seed=42,
            verbose=False
        )

        best_idx = np.argmin(res.F[:, 0])
        best_routes = pymoo_problem._decode_routes(res.X[best_idx])

        # 构建真实 Pareto 前沿数据
        pareto_front = res.F.tolist()

        return OptimizationResult(
            solver_name=self.name,
            problem_type=problem.problem_type,
            solution=best_routes,
            objective_values=res.F[best_idx],
            solve_time=0.0,
            iterations=n_gen,
            routes=best_routes,
            metadata={
                'pareto_front_size': len(res.F),
                'pareto_front': pareto_front,
                'distance_source': getattr(data, 'metadata', {}).get('distance_source', 'unknown'),
                'distance_precision': getattr(data, 'distance_precision', {}),
                'source_summary': getattr(data, 'source_summary', {}),
                'distance_unit': 'km',
                'crossover_method': kwargs.get('crossover_method', 'ox'),
                'mutation_methods': ['swap', 'two_opt', 'relocate'],
                'repair_method': 'capacity_feasibility',
            }
        )
