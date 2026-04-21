"""
pymoo 求解器
============

使用 pymoo 求解多目标优化问题

作者: 小彩
日期: 2026-04-19
"""

import numpy as np
from typing import List, Optional, Dict, Any
from ..base import (
    OptimizationSolver,
    OptimizationProblem,
    OptimizationResult,
    SolverType,
    SolverRegistry,
    timeit
)


@SolverRegistry.register(SolverType.PYMOO_NSGA2)
class PymooNSGA2Solver(OptimizationSolver):
    """
    pymoo NSGA-II 求解器
    """
    
    def __init__(self, 
                 pop_size: int = 100,
                 crossover_prob: float = 0.9,
                 mutation_prob: float = None,
                 **kwargs):
        """
        初始化
        
        Args:
            pop_size: 种群大小
            crossover_prob: 交叉概率
            mutation_prob: 变异概率
            **kwargs: 其他参数
        """
        super().__init__("NSGA-II (pymoo)", SolverType.PYMOO_NSGA2)
        self.pop_size = pop_size
        self.crossover_prob = crossover_prob
        self.mutation_prob = mutation_prob
        self.parameters.update(kwargs)
    
    def is_available(self) -> bool:
        """检查 pymoo 是否可用"""
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
        """
        求解多目标优化问题
        
        Args:
            problem: 优化问题
            time_limit: 时间限制（秒）
            n_gen: 迭代次数
            **kwargs: 其他参数
        
        Returns:
            优化结果
        """
        from pymoo.core.problem import Problem as PymooProblem
        from pymoo.algorithms.moo.nsga2 import NSGA2
        from pymoo.optimize import minimize
        from pymoo.termination import get_termination
        from pymoo.operators.sampling.rnd import IntegerRandomSampling
        
        # 包装问题
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
                    # 解码为路线
                    routes = self._decode_routes(X[i])
                    F[i] = self.orig.evaluate(routes)
                
                out["F"] = F
            
            def _decode_routes(self, perm):
                """解码路线"""
                data = self.orig.data
                routes = []
                route = []
                load = 0
                
                # 需求转为列表避免索引问题
                demands_list = list(data.demands)
                
                for idx in perm:
                    customer = int(idx) + 1
                    demand = demands_list[customer - 1]
                    if load + demand <= data.vehicle_capacity:
                        route.append(customer)
                        load += demand
                    else:
                        if route:
                            routes.append(route)
                        route = [customer]
                        load = demand
                
                if route:
                    routes.append(route)
                
                return routes
        
        # 创建问题
        pymoo_problem = WrappedProblem(problem)
        
        # 创建算法
        algorithm = NSGA2(
            pop_size=self.pop_size,
            sampling=IntegerRandomSampling(),
            eliminate_duplicates=True
        )
        
        # 终止条件
        termination = get_termination("n_gen", n_gen)
        
        # 求解
        res = minimize(
            pymoo_problem,
            algorithm,
            termination,
            seed=42,
            verbose=False
        )
        
        # 提取最优解
        best_idx = np.argmin(res.F[:, 0])
        best_routes = pymoo_problem._decode_routes(res.X[best_idx])
        
        # 创建结果
        result = OptimizationResult(
            solver_name=self.name,
            problem_type=problem.problem_type,
            solution=best_routes,
            objective_values=res.F[best_idx],
            solve_time=0.0,
            iterations=n_gen,
            routes=best_routes,
            metadata={'pareto_front_size': len(res.F)}
        )
        
        return result


@SolverRegistry.register(SolverType.PYMOO_NSGA3)
class PymooNSGA3Solver(OptimizationSolver):
    """
    pymoo NSGA-III 求解器（高维多目标）
    """
    
    def __init__(self, 
                 pop_size: int = 100,
                 n_partitions: int = 12,
                 **kwargs):
        """
        初始化
        
        Args:
            pop_size: 种群大小
            n_partitions: 参考点分割数
            **kwargs: 其他参数
        """
        super().__init__("NSGA-III (pymoo)", SolverType.PYMOO_NSGA3)
        self.pop_size = pop_size
        self.n_partitions = n_partitions
        self.parameters.update(kwargs)
    
    def is_available(self) -> bool:
        """检查 pymoo 是否可用"""
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
        """
        求解高维多目标优化问题
        """
        from pymoo.core.problem import Problem as PymooProblem
        from pymoo.algorithms.moo.nsga3 import NSGA3
        from pymoo.optimize import minimize
        from pymoo.termination import get_termination
        from pymoo.operators.sampling.rnd import IntegerRandomSampling
        from pymoo.util.ref_dirs import get_reference_directions
        
        # 包装问题（同 NSGA-II）
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
                data = self.orig.data
                routes = []
                route = []
                load = 0
                
                # 需求转为列表避免索引问题
                demands_list = list(data.demands)
                
                for idx in perm:
                    customer = int(idx) + 1
                    demand = demands_list[customer - 1]
                    if load + demand <= data.vehicle_capacity:
                        route.append(customer)
                        load += demand
                    else:
                        if route:
                            routes.append(route)
                        route = [customer]
                        load = demand
                
                if route:
                    routes.append(route)
                
                return routes
        
        pymoo_problem = WrappedProblem(problem)
        
        # 生成参考方向
        ref_dirs = get_reference_directions(
            "das-dennis",
            problem.n_objectives,
            n_partitions=self.n_partitions
        )
        
        # 创建算法
        algorithm = NSGA3(
            pop_size=len(ref_dirs),
            ref_dirs=ref_dirs,
            sampling=IntegerRandomSampling(),
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
        
        # 提取最优解
        best_idx = np.argmin(res.F[:, 0])
        best_routes = pymoo_problem._decode_routes(res.X[best_idx])
        
        result = OptimizationResult(
            solver_name=self.name,
            problem_type=problem.problem_type,
            solution=best_routes,
            objective_values=res.F[best_idx],
            solve_time=0.0,
            iterations=n_gen,
            routes=best_routes,
            metadata={'pareto_front_size': len(res.F)}
        )
        
        return result
