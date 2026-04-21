"""
列生成求解器
============

使用列生成求解 VRP

作者: 小彩
日期: 2026-04-19
"""

import numpy as np
from typing import List, Optional, Dict, Tuple
from ..base import (
    OptimizationSolver,
    OptimizationProblem,
    OptimizationResult,
    SolverType,
    SolverRegistry,
    timeit
)


@SolverRegistry.register(SolverType.COLUMN_GENERATION)
class ColumnGenerationSolver(OptimizationSolver):
    """
    列生成求解器
    
    用于求解大规模 VRP 问题
    """
    
    def __init__(self, max_iterations: int = 50, **kwargs):
        """
        初始化
        
        Args:
            max_iterations: 最大迭代次数
        """
        super().__init__("Column Generation", SolverType.COLUMN_GENERATION)
        self.max_iterations = max_iterations
        self.parameters.update(kwargs)
    
    def is_available(self) -> bool:
        """检查依赖"""
        try:
            from scipy.optimize import linprog
            return True
        except ImportError:
            return False
    
    @timeit
    def solve(self,
              problem: OptimizationProblem,
              time_limit: float = 60.0,
              **kwargs) -> OptimizationResult:
        """
        求解 VRP
        
        简化版列生成：
        1. 主问题：集合覆盖
        2. 子问题：最短路
        """
        data = problem.data
        n = data.n_customers
        
        # 初始化列（路线池）
        routes_pool = self._generate_initial_routes(data)
        
        # 迭代
        for iteration in range(self.max_iterations):
            # 求解主问题（简化版）
            duals = self._solve_master(routes_pool, n)
            
            # 求解子问题（生成新路线）
            new_routes = self._solve_pricing(duals, data)
            
            if not new_routes:
                break
            
            # 添加新路线
            routes_pool.extend(new_routes)
        
        # 选择最终路线
        selected_routes = self._select_routes(routes_pool, data)
        
        return OptimizationResult(
            solver_name=self.name,
            problem_type=problem.problem_type,
            solution=selected_routes,
            objective_values=np.array([self._calculate_cost(selected_routes, data)]),
            solve_time=0.0,
            routes=selected_routes
        )
    
    def _generate_initial_routes(self, data) -> List[List[int]]:
        """生成初始路线池"""
        routes = []
        n = data.n_customers
        Q = data.vehicle_capacity
        
        # 单客户路线
        for i in range(1, n + 1):
            if data.demands[i - 1] <= Q:
                routes.append([i])
        
        # 最近邻路线
        unvisited = set(range(1, n + 1))
        while unvisited:
            route = []
            load = 0
            current = 0
            
            while unvisited:
                best = None
                best_dist = float('inf')
                
                for customer in unvisited:
                    if load + data.demands[customer - 1] <= Q:
                        dist = data.distance_matrix[current][customer]
                        if dist < best_dist:
                            best_dist = dist
                            best = customer
                
                if best is None:
                    break
                
                route.append(best)
                load += data.demands[best - 1]
                current = best
                unvisited.remove(best)
            
            if route:
                routes.append(route)
        
        return routes
    
    def _solve_master(self, routes: List[List[int]], n: int) -> np.ndarray:
        """
        求解主问题（简化版）
        
        返回对偶变量
        """
        # 简化：使用贪心覆盖
        covered = set()
        duals = np.ones(n)
        
        for route in routes:
            for customer in route:
                if customer not in covered:
                    covered.add(customer)
                    duals[customer - 1] = 1.0 / len(route)
        
        return duals
    
    def _solve_pricing(self, duals: np.ndarray, data) -> List[List[int]]:
        """
        求解子问题（定价问题）
        
        生成有负约减成本的路线
        """
        n = data.n_customers
        Q = data.vehicle_capacity
        new_routes = []
        
        # 尝试生成新路线
        for _ in range(10):
            route = []
            load = 0
            current = 0
            total_dual = 0
            
            unvisited = set(range(1, n + 1))
            
            while unvisited:
                best = None
                best_ratio = -float('inf')
                
                for customer in unvisited:
                    if load + data.demands[customer - 1] <= Q:
                        dist = data.distance_matrix[current][customer]
                        ratio = duals[customer - 1] / (dist + 1e-6)
                        
                        if ratio > best_ratio:
                            best_ratio = ratio
                            best = customer
                
                if best is None:
                    break
                
                route.append(best)
                total_dual += duals[best - 1]
                load += data.demands[best - 1]
                current = best
                unvisited.remove(best)
            
            if route:
                # 计算约减成本
                cost = self._calculate_cost([route], data)
                reduced_cost = cost - total_dual
                
                if reduced_cost < -0.1:  # 有负约减成本
                    new_routes.append(route)
        
        return new_routes
    
    def _select_routes(self, routes: List[List[int]], data) -> List[List[int]]:
        """选择最终路线集合"""
        n = data.n_customers
        covered = set()
        selected = []
        total_cost = 0
        
        # 按成本排序
        route_costs = [(route, self._calculate_cost([route], data)) for route in routes]
        route_costs.sort(key=lambda x: x[1] / max(len(x[0]), 1))
        
        for route, cost in route_costs:
            # 检查是否有新覆盖的客户
            new_customers = set(route) - covered
            
            if new_customers:
                selected.append(route)
                covered.update(route)
                total_cost += cost
            
            if len(covered) == n:
                break
        
        return selected
    
    def _calculate_cost(self, routes: List[List[int]], data) -> float:
        """计算总成本"""
        total = 0
        for route in routes:
            prev = 0
            for customer in route:
                total += data.distance_matrix[prev][customer]
                prev = customer
            total += data.distance_matrix[prev][0]  # 返回仓库
        return total
