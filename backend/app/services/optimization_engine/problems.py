"""
问题定义模块
===========

定义各种优化问题的具体实现

作者: 小彩
日期: 2026-04-19
"""

import numpy as np
from typing import List, Tuple, Dict, Any, Optional
from dataclasses import dataclass, field
from .base import OptimizationProblem, ProblemType


@dataclass
class VRPData:
    """VRP 问题数据"""
    n_customers: int
    n_vehicles: int
    vehicle_capacity: float
    depot: np.ndarray
    customers: np.ndarray
    demands: np.ndarray
    distance_matrix: Optional[np.ndarray] = None
    
    def __post_init__(self):
        """自动计算距离矩阵"""
        if self.distance_matrix is None:
            self._compute_distance_matrix()
    
    def _compute_distance_matrix(self):
        """计算距离矩阵"""
        n = self.n_customers + 1
        
        # 确保 depot 和 customers 是正确的形状
        depot = np.array(self.depot).reshape(-1)[:2].reshape(1, 2)
        customers = np.array(self.customers).reshape(-1, 2) if len(self.customers) > 0 else np.zeros((0, 2))
        
        points = np.vstack([depot, customers])
        self.distance_matrix = np.zeros((n, n))
        for i in range(n):
            for j in range(n):
                self.distance_matrix[i, j] = np.linalg.norm(points[i] - points[j])
    
    @classmethod
    def generate_random(cls, n_customers: int, seed: int = 42, 
                        capacity: float = 50) -> 'VRPData':
        """生成随机数据"""
        np.random.seed(seed)
        
        depot = np.array([50.0, 50.0])
        customers = np.random.uniform(0, 100, (n_customers, 2))
        demands = np.random.randint(5, 20, n_customers)
        n_vehicles = max(1, int(np.ceil(demands.sum() / capacity * 1.5)))
        
        return cls(
            n_customers=n_customers,
            n_vehicles=n_vehicles,
            vehicle_capacity=capacity,
            depot=depot,
            customers=customers,
            demands=demands
        )


class VRPProblem(OptimizationProblem):
    """
    VRP 问题基类
    """
    
    def __init__(self, data: VRPData, name: str = "VRP"):
        super().__init__(name)
        self.data = data
        self.problem_type = ProblemType.VRP
        self.n_objectives = 1
        self.n_variables = data.n_customers
    
    def evaluate(self, solution: List[List[int]]) -> np.ndarray:
        """
        评估解
        
        Args:
            solution: 路线列表，每条路线是一个客户序列
        
        Returns:
            目标值数组 [总距离]
        """
        total_distance = 0.0
        
        for route in solution:
            if len(route) < 2:
                continue
            
            # 加上仓库到第一个客户的距离
            total_distance += self.data.distance_matrix[0, route[0]]
            
            # 客户之间的距离
            for i in range(len(route) - 1):
                total_distance += self.data.distance_matrix[route[i], route[i+1]]
            
            # 最后一个客户返回仓库
            total_distance += self.data.distance_matrix[route[-1], 0]
        
        return np.array([total_distance])
    
    def is_feasible(self, solution: List[List[int]]) -> bool:
        """检查解是否可行"""
        # 检查所有客户是否被访问
        visited = set()
        for route in solution:
            for customer in route:
                if customer in visited:
                    return False  # 重复访问
                visited.add(customer)
        
        expected = set(range(1, self.data.n_customers + 1))
        if visited != expected:
            return False  # 有客户未被访问
        
        return True
    
    def get_initial_solution(self) -> List[List[int]]:
        """获取初始解（贪心构造）"""
        unvisited = set(range(1, self.data.n_customers + 1))
        routes = []
        
        while unvisited:
            route = []
            load = 0
            
            while unvisited:
                # 找最近的可行客户
                current = route[-1] if route else 0
                best = None
                best_dist = float('inf')
                
                for customer in unvisited:
                    if load + self.data.demands[customer-1] <= self.data.vehicle_capacity:
                        dist = self.data.distance_matrix[current, customer]
                        if dist < best_dist:
                            best_dist = dist
                            best = customer
                
                if best is None:
                    break
                
                route.append(best)
                load += self.data.demands[best-1]
                unvisited.remove(best)
            
            if route:
                routes.append(route)
        
        return routes


class CVRPProblem(VRPProblem):
    """
    容量约束 VRP (CVRP)
    """
    
    def __init__(self, data: VRPData, name: str = "CVRP"):
        super().__init__(data, name)
        self.problem_type = ProblemType.CVRP
    
    def is_feasible(self, solution: List[List[int]]) -> bool:
        """检查解是否可行（包含容量约束）"""
        if not super().is_feasible(solution):
            return False
        
        # 检查每条路线的容量约束
        for route in solution:
            load = sum(self.data.demands[c-1] for c in route)
            if load > self.data.vehicle_capacity:
                return False
        
        return True


class VRPTWProblem(VRPProblem):
    """
    带时间窗的 VRP (VRPTW)
    """
    
    def __init__(self, data: VRPData, 
                 time_windows: np.ndarray,
                 service_times: np.ndarray,
                 name: str = "VRPTW"):
        super().__init__(data, name)
        self.problem_type = ProblemType.VRPTW
        self.time_windows = time_windows  # [n_customers+1, 2] - 最早/最晚到达时间
        self.service_times = service_times  # [n_customers+1] - 服务时间
        self.n_objectives = 2  # 距离 + 时间
    
    def evaluate(self, solution: List[List[int]]) -> np.ndarray:
        """
        评估解
        
        Returns:
            [总距离, 总时间窗违反]
        """
        total_distance = 0.0
        total_violation = 0.0
        
        for route in solution:
            if len(route) < 1:
                continue
            
            current_time = 0.0
            
            # 仓库到第一个客户
            first = route[0]
            total_distance += self.data.distance_matrix[0, first]
            current_time += self.data.distance_matrix[0, first]
            
            # 检查时间窗
            e, l = self.time_windows[first]
            if current_time < e:
                current_time = e  # 等待
            elif current_time > l:
                total_violation += current_time - l
            
            current_time += self.service_times[first]
            
            # 客户之间
            for i in range(len(route) - 1):
                current = route[i]
                next_customer = route[i+1]
                
                dist = self.data.distance_matrix[current, next_customer]
                total_distance += dist
                current_time += dist
                
                # 检查时间窗
                e, l = self.time_windows[next_customer]
                if current_time < e:
                    current_time = e
                elif current_time > l:
                    total_violation += current_time - l
                
                current_time += self.service_times[next_customer]
            
            # 返回仓库
            last = route[-1]
            total_distance += self.data.distance_matrix[last, 0]
        
        return np.array([total_distance, total_violation])


class FacilityLocationProblem(OptimizationProblem):
    """
    设施选址问题
    """
    
    def __init__(self, n_facilities: int, n_customers: int,
                 fixed_costs: np.ndarray, 
                 distances: np.ndarray,
                 demands: np.ndarray,
                 capacities: np.ndarray,
                 name: str = "FacilityLocation"):
        super().__init__(name)
        self.problem_type = ProblemType.FACILITY_LOCATION
        self.n_facilities = n_facilities
        self.n_customers = n_customers
        self.fixed_costs = fixed_costs
        self.distances = distances
        self.demands = demands
        self.capacities = capacities
        self.n_objectives = 2  # 总成本 + 最大服务距离
        self.n_variables = n_facilities + n_customers
    
    def evaluate(self, solution: Tuple[np.ndarray, np.ndarray]) -> np.ndarray:
        """
        评估解
        
        Args:
            solution: (open_facilities, assignments)
                - open_facilities: [n_facilities] 是否开放
                - assignments: [n_customers] 客户分配到哪个设施
        
        Returns:
            [总成本, 最大服务距离]
        """
        open_facilities, assignments = solution
        
        # 固定成本
        fixed_cost = np.sum(self.fixed_costs * open_facilities)
        
        # 运输成本
        transport_cost = 0.0
        max_distance = 0.0
        
        for j in range(self.n_customers):
            facility = assignments[j]
            dist = self.distances[j, facility]
            transport_cost += dist * self.demands[j]
            max_distance = max(max_distance, dist)
        
        total_cost = fixed_cost + transport_cost
        
        return np.array([total_cost, max_distance])
    
    def is_feasible(self, solution: Tuple[np.ndarray, np.ndarray]) -> bool:
        """检查解是否可行"""
        open_facilities, assignments = solution
        
        # 检查每个客户是否分配到开放的设施
        for j in range(self.n_customers):
            if not open_facilities[assignments[j]]:
                return False
        
        # 检查容量约束
        facility_loads = np.zeros(self.n_facilities)
        for j in range(self.n_customers):
            facility_loads[assignments[j]] += self.demands[j]
        
        for i in range(self.n_facilities):
            if open_facilities[i] and facility_loads[i] > self.capacities[i]:
                return False
        
        return True


class MultiObjectiveVRP(VRPProblem):
    """
    多目标 VRP
    
    目标：
    1. 总距离
    2. 总时间
    3. 车辆数
    """
    
    def __init__(self, data: VRPData, 
                 service_times: Optional[np.ndarray] = None,
                 name: str = "MultiObjectiveVRP"):
        super().__init__(data, name)
        self.problem_type = ProblemType.MULTI_OBJECTIVE
        self.n_objectives = 3
        self.service_times = service_times if service_times is not None else np.zeros(data.n_customers)
    
    def evaluate(self, solution: List[List[int]]) -> np.ndarray:
        """
        评估解
        
        Returns:
            [总距离, 总时间, 车辆数]
        """
        total_distance = 0.0
        total_time = 0.0
        n_vehicles = len(solution)
        
        for route in solution:
            if len(route) < 1:
                continue
            
            route_distance = 0.0
            route_time = 0.0
            
            # 仓库到第一个客户
            first = route[0]
            dist = self.data.distance_matrix[0, first]
            route_distance += dist
            route_time += dist
            
            # 客户之间
            for i in range(len(route)):
                customer = route[i]
                route_time += self.service_times[customer-1]
                
                if i < len(route) - 1:
                    next_customer = route[i+1]
                    dist = self.data.distance_matrix[customer, next_customer]
                    route_distance += dist
                    route_time += dist
            
            # 返回仓库
            last = route[-1]
            route_distance += self.data.distance_matrix[last, 0]
            route_time += self.data.distance_matrix[last, 0]
            
            total_distance += route_distance
            total_time += route_time
        
        return np.array([total_distance, total_time, n_vehicles])
