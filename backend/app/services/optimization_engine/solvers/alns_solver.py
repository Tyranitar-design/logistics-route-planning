"""
ALNS 求解器
===========

自适应大邻域搜索算法

作者: 小彩
日期: 2026-04-19
"""

import numpy as np
from typing import List, Optional, Dict, Tuple
import random
import math
from ..base import (
    OptimizationSolver,
    OptimizationProblem,
    OptimizationResult,
    SolverType,
    SolverRegistry,
    timeit
)


@SolverRegistry.register(SolverType.ALNS)
class ALNSSolver(OptimizationSolver):
    """
    自适应大邻域搜索求解器
    
    特点：
    - 自适应算子选择
    - 模拟退火接受准则
    - 多种破坏和修复算子
    """
    
    def __init__(self,
                 n_iterations: int = 1000,
                 initial_temp: float = 100.0,
                 cooling_rate: float = 0.995,
                 destroy_fraction: float = 0.3,
                 **kwargs):
        """
        初始化
        
        Args:
            n_iterations: 迭代次数
            initial_temp: 初始温度
            cooling_rate: 冷却速率
            destroy_fraction: 破坏比例
        """
        super().__init__("ALNS", SolverType.ALNS)
        self.n_iterations = n_iterations
        self.initial_temp = initial_temp
        self.cooling_rate = cooling_rate
        self.destroy_fraction = destroy_fraction
        self.parameters.update(kwargs)
        
        # 算子权重
        self.destroy_weights = np.ones(4)  # 4种破坏算子
        self.repair_weights = np.ones(3)   # 3种修复算子
    
    def is_available(self) -> bool:
        """ALNS 总是可用"""
        return True
    
    @timeit
    def solve(self,
              problem: OptimizationProblem,
              time_limit: float = 60.0,
              **kwargs) -> OptimizationResult:
        """
        求解 VRP 问题
        """
        import time
        start_time = time.time()
        
        data = problem.data
        
        # 初始解
        current = self._get_initial_solution(data)
        current_cost = self._calculate_cost(current, data)
        
        best = current.copy()
        best_cost = current_cost
        
        temperature = self.initial_temp
        
        # 主循环
        for iteration in range(self.n_iterations):
            if time.time() - start_time > time_limit:
                break
            
            # 选择破坏算子
            destroy_idx = self._select_operator(self.destroy_weights)
            
            # 选择修复算子
            repair_idx = self._select_operator(self.repair_weights)
            
            # 破坏
            destroyed, removed = self._destroy(current, destroy_idx, data)
            
            # 修复
            candidate = self._repair(destroyed, removed, repair_idx, data)
            candidate_cost = self._calculate_cost(candidate, data)
            
            # 接受准则
            delta = candidate_cost - current_cost
            
            if delta < 0:
                # 改进
                current = candidate
                current_cost = candidate_cost
                
                if candidate_cost < best_cost:
                    best = candidate.copy()
                    best_cost = candidate_cost
                
                # 更新算子权重
                self.destroy_weights[destroy_idx] *= 1.1
                self.repair_weights[repair_idx] *= 1.1
            
            elif random.random() < math.exp(-delta / temperature):
                # 接受劣解
                current = candidate
                current_cost = candidate_cost
            
            # 冷却
            temperature *= self.cooling_rate
        
        # 解码路线
        routes = self._decode_solution(best, data)
        
        return OptimizationResult(
            solver_name=self.name,
            problem_type=problem.problem_type,
            solution=routes,
            objective_values=np.array([best_cost]),
            solve_time=0.0,
            iterations=self.n_iterations,
            routes=routes
        )
    
    def _get_initial_solution(self, data) -> List:
        """生成初始解（最近邻）"""
        n = data.n_customers
        depot = 0
        
        # 需求转为列表避免索引问题
        demands_list = list(data.demands)
        
        unvisited = set(range(1, n + 1))
        solution = []
        
        while unvisited:
            route = [depot]
            current = depot
            load = 0
            
            while unvisited:
                # 找最近的可行客户
                best_customer = None
                best_distance = float('inf')
                
                for customer in unvisited:
                    if load + demands_list[customer - 1] <= data.vehicle_capacity:
                        dist = data.distance_matrix[current][customer]
                        if dist < best_distance:
                            best_distance = dist
                            best_customer = customer
                
                if best_customer is None:
                    break
                
                route.append(best_customer)
                load += demands_list[best_customer - 1]
                current = best_customer
                unvisited.remove(best_customer)
            
            route.append(depot)
            solution.append(route)
        
        return solution
    
    def _calculate_cost(self, solution: List, data) -> float:
        """计算解的总成本"""
        total = 0
        for route in solution:
            for i in range(len(route) - 1):
                total += data.distance_matrix[route[i]][route[i + 1]]
        return total
    
    def _select_operator(self, weights: np.ndarray) -> int:
        """轮盘赌选择算子"""
        probs = weights / weights.sum()
        return np.random.choice(len(weights), p=probs)
    
    def _destroy(self, solution: List, operator: int, data) -> Tuple[List, List]:
        """破坏算子"""
        # 收集所有客户
        all_customers = []
        for route in solution:
            all_customers.extend(route[1:-1])  # 排除仓库
        
        n_remove = max(1, int(len(all_customers) * self.destroy_fraction))
        
        if operator == 0:
            # 随机移除
            removed = random.sample(all_customers, min(n_remove, len(all_customers)))
        
        elif operator == 1:
            # 最远移除
            distances = []
            for i, customer in enumerate(all_customers):
                dist = data.distance_matrix[0][customer]
                distances.append((dist, i))
            distances.sort(reverse=True)
            removed = [all_customers[i] for _, i in distances[:n_remove]]
        
        elif operator == 2:
            # 相关性移除（移除相近的客户）
            if all_customers:
                seed = random.choice(all_customers)
                distances = [(data.distance_matrix[seed][c], c) for c in all_customers if c != seed]
                distances.sort()
                removed = [seed] + [c for _, c in distances[:n_remove - 1]]
            else:
                removed = []
        
        else:
            # 路线移除
            if solution:
                route_idx = random.randint(0, len(solution) - 1)
                removed = solution[route_idx][1:-1]
            else:
                removed = []
        
        # 从解中移除
        destroyed = []
        for route in solution:
            new_route = [0]
            for node in route[1:-1]:
                if node not in removed:
                    new_route.append(node)
            if len(new_route) > 1:
                new_route.append(0)
                destroyed.append(new_route)
        
        return destroyed, removed
    
    def _repair(self, solution: List, removed: List, operator: int, data) -> List:
        """修复算子"""
        # 转换为集合方便操作
        remaining = set(removed)
        
        # 需求转为列表避免索引问题
        demands_list = list(data.demands)
        
        if operator == 0:
            # 贪婪插入
            while remaining:
                best_customer = None
                best_route_idx = None
                best_pos = None
                best_increase = float('inf')
                
                for customer in remaining:
                    for route_idx, route in enumerate(solution):
                        for pos in range(1, len(route)):
                            # 检查容量
                            route_load = sum(demands_list[c - 1] for c in route[1:-1])
                            if route_load + demands_list[customer - 1] <= data.vehicle_capacity:
                                # 计算插入成本
                                increase = (data.distance_matrix[route[pos - 1]][customer] +
                                          data.distance_matrix[customer][route[pos]] -
                                          data.distance_matrix[route[pos - 1]][route[pos]])
                                
                                if increase < best_increase:
                                    best_increase = increase
                                    best_customer = customer
                                    best_route_idx = route_idx
                                    best_pos = pos
                
                if best_customer is not None:
                    solution[best_route_idx].insert(best_pos, best_customer)
                    remaining.remove(best_customer)
                else:
                    # 创建新路线
                    solution.append([0, remaining.pop(), 0])
        
        elif operator == 1:
            # 最远插入
            while remaining:
                customer = remaining.pop()
                # 找到最佳插入位置
                best_route_idx = None
                best_pos = None
                best_increase = float('inf')
                
                for route_idx, route in enumerate(solution):
                    for pos in range(1, len(route)):
                        route_load = sum(demands_list[c - 1] for c in route[1:-1])
                        if route_load + demands_list[customer - 1] <= data.vehicle_capacity:
                            increase = (data.distance_matrix[route[pos - 1]][customer] +
                                      data.distance_matrix[customer][route[pos]] -
                                      data.distance_matrix[route[pos - 1]][route[pos]])
                            
                            if increase < best_increase:
                                best_increase = increase
                                best_route_idx = route_idx
                                best_pos = pos
                
                if best_route_idx is not None:
                    solution[best_route_idx].insert(best_pos, customer)
                else:
                    solution.append([0, customer, 0])
        
        else:
            # 最近插入
            while remaining:
                customer = remaining.pop()
                # 找到距离最近的路线
                best_route_idx = None
                best_pos = None
                min_dist = float('inf')
                
                for route_idx, route in enumerate(solution):
                    route_load = sum(demands_list[c - 1] for c in route[1:-1])
                    if route_load + demands_list[customer - 1] <= data.vehicle_capacity:
                        for pos in range(1, len(route)):
                            dist = min(data.distance_matrix[route[pos - 1]][customer],
                                      data.distance_matrix[customer][route[pos]])
                            if dist < min_dist:
                                min_dist = dist
                                best_route_idx = route_idx
                                best_pos = pos
                
                if best_route_idx is not None:
                    solution[best_route_idx].insert(best_pos, customer)
                else:
                    solution.append([0, customer, 0])
        
        return solution
    
    def _decode_solution(self, solution: List, data) -> List[List[int]]:
        """解码解"""
        routes = []
        for route in solution:
            if len(route) > 2:
                routes.append(route[1:-1])  # 排除仓库
        return routes
