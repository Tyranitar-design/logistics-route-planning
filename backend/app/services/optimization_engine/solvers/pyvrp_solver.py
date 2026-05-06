"""
PyVRP 求解器
============

基于 PyVRP 的现代 VRP 求解器
特点：快速、现代化、支持多种 VRP 变体

参考：https://github.com/PyVRP/PyVRP
版本：0.14.0

作者: 小彩
日期: 2026-04-25
"""

import numpy as np
from typing import List, Dict, Any, Optional
import time

from ..base import (
    OptimizationSolver,
    OptimizationProblem,
    OptimizationResult,
    SolverType,
    ProblemType,
    timeit
)


class PyVRPSolver(OptimizationSolver):
    """
    PyVRP 求解器
    
    支持的问题类型：
    - CVRP (容量约束)
    - VRPTW (时间窗)
    - PDP (取送货)
    - MDVRP (多车场)
    - HDVRP (异构车队)
    
    参考文档：https://pyvrp.org/
    """
    
    def __init__(self, **kwargs):
        super().__init__("PyVRP", SolverType.PYVRP)
        
        # PyVRP 参数
        self.max_runtime = kwargs.get('max_runtime', 10)  # 秒
        self.nr_iterations = kwargs.get('nr_iterations', 100000)
        
        # 尝试导入 PyVRP
        self.pyvrp_available = False
        self.pyvrp = None
        
        try:
            import pyvrp
            self.pyvrp = pyvrp
            self.pyvrp_available = True
        except ImportError:
            print("⚠️ PyVRP 未安装，请运行: pip install pyvrp")
    
    def is_available(self) -> bool:
        """检查求解器是否可用"""
        return self.pyvrp_available
    
    def solve(self, problem: OptimizationProblem, 
              time_limit: float = 60.0,
              **kwargs) -> OptimizationResult:
        """
        使用 PyVRP 求解 VRP 问题
        
        Args:
            problem: VRP 优化问题
            time_limit: 时间限制（秒）
            **kwargs: 其他参数
        
        Returns:
            优化结果
        """
        if not self.pyvrp_available:
            raise RuntimeError("PyVRP 未安装")
        
        start_time = time.time()
        
        # 将问题转换为 PyVRP 格式（返回 Model 实例）
        model = self._convert_to_pyvrp_model(problem)
        
        # 配置停止条件
        from pyvrp import stop
        
        # 使用时间限制
        stop_criteria = stop.MaxRuntime(time_limit)
        
        # 求解：直接在 model 上调用 solve
        result = model.solve(stop=stop_criteria, display=False)
        
        # 转换结果
        solution = result.best
        routes = self._extract_routes(solution, problem)
        
        # 计算目标值
        objective = self._calculate_objective(problem, routes)
        
        solve_time = time.time() - start_time
        raw_data = problem.data
        
        return OptimizationResult(
            solver_name=self.name,
            problem_type=problem.problem_type,
            solution=routes,
            objective_values=np.array([objective]),
            solve_time=solve_time,
            iterations=getattr(result, 'num_iterations', 0),
            routes=routes,
            metadata={
                'nroutes': len(routes),
                'nvehicles': len(routes),
                'cost': result.cost(),
                'distance_source': getattr(raw_data, 'metadata', {}).get('distance_source', 'unknown'),
                'distance_precision': getattr(raw_data, 'distance_precision', {}),
                'source_summary': getattr(raw_data, 'source_summary', {}),
                'distance_unit': 'km',
                'pyvrp_edge_cost_unit': 'm',
            }
        )
    
    def _convert_to_pyvrp_model(self, problem: OptimizationProblem):
        """将问题转换为 PyVRP Model 实例，主流程使用统一精确距离矩阵
        
        PyVRP 0.13+ API:
        - add_depot(x, y) 直接传坐标
        - add_client(x, y, delivery=...) 直接传坐标和需求
        - add_edge(frm_obj, to_obj, distance=...) 传节点对象和距离
        - add_vehicle_type(num_available, capacity=...) 传车辆数和容量
        """
        data = problem.data
        capacity = data.vehicle_capacity
        distance_matrix = np.asarray(data.distance_matrix, dtype=float)
        expected_shape = (data.n_customers + 1, data.n_customers + 1)
        if distance_matrix.shape != expected_shape:
            raise ValueError(
                f"distance_matrix 维度错误，期望 {expected_shape}，实际 {distance_matrix.shape}"
            )
        
        depot_coord = np.array(data.depot).reshape(-1)[:2]
        customers = np.array(data.customers).reshape(-1, 2) if len(data.customers) > 0 else np.zeros((0, 2))
        demands = np.asarray(data.demands).tolist()
        
        # 创建模型
        model = self.pyvrp.Model()
        
        # 添加车场（直接传坐标）
        depot_obj = model.add_depot(x=float(depot_coord[0]), y=float(depot_coord[1]))
        
        # 添加客户（直接传坐标和需求）
        client_objs = []
        for i in range(len(customers)):
            client = model.add_client(
                x=float(customers[i][0]),
                y=float(customers[i][1]),
                delivery=int(demands[i])
            )
            client_objs.append(client)
        
        # 添加车辆类型
        model.add_vehicle_type(num_available=int(data.n_vehicles), capacity=int(capacity))
        
        # 添加边（统一精确距离矩阵：km -> m，整数）
        all_nodes = [depot_obj] + client_objs
        for i, frm in enumerate(all_nodes):
            for j, to in enumerate(all_nodes):
                if i != j:
                    dist_m = int(round(float(distance_matrix[i][j]) * 1000))
                    model.add_edge(frm, to, distance=max(1, dist_m))
        
        return model

    
    def _euclidean_distance(self, p1, p2):
        """计算欧氏距离"""
        return np.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)
    
    def _extract_routes(self, solution, problem: OptimizationProblem) -> List[List[int]]:
        """提取路线
        
        PyVRP 0.13+ API:
        - route.visits() 返回 1-indexed 客户编号列表
        - 直接与 VRPData 的 1-indexed 约定对齐
        """
        routes = []
        
        for route in solution.routes():
            # visits() 返回 [1, 2, ...]，1-indexed 客户编号
            visits = list(route.visits()) if hasattr(route, 'visits') else list(route)
            if visits:
                routes.append(visits)
        
        return routes
        
        return routes
    
    def _calculate_objective(self, problem: OptimizationProblem, routes: List[List[int]]) -> float:
        """计算目标值（总距离），统一使用 problem.data.distance_matrix"""
        total_distance = 0.0
        distance_matrix = np.asarray(problem.data.distance_matrix, dtype=float)
        
        for route in routes:
            for i in range(len(route) - 1):
                from_node = route[i]
                to_node = route[i + 1]
                total_distance += float(distance_matrix[from_node][to_node])
        
        return total_distance
    
    def solve_vrptw(self, coords, demands, capacities, time_windows, service_times, num_vehicles):
        """求解带时间窗的 VRP"""
        
        model = self.pyvrp.Model()
        
        # 添加车场
        model.add_depot(location=model.add_location(x=coords[0][0], y=coords[0][1]))
        
        # 添加客户（带时间窗）
        for i in range(1, len(coords)):
            model.add_client(
                location=model.add_location(x=coords[i][0], y=coords[i][1]),
                delivery=demands[i],
                tw_start=time_windows[i][0] if time_windows[i][0] else 0,
                tw_end=time_windows[i][1] if time_windows[i][1] else 24*3600,
                service_duration=service_times[i]
            )
        
        # 添加车辆
        model.add_vehicle_type(num_vehicles, capacity=capacities[0])
        
        # 添加距离
        for frm in model.locations:
            for to in model.locations:
                if frm != to:
                    dist = self._euclidean_distance((frm.x, frm.y), (to.x, to.y))
                    model.add_edge(frm, to, distance=dist)
        
        result = model.solve(stop=self.pyvrp.stop.MaxRuntime(self.max_runtime))
        
        return result
    
    def solve_pdp(self, coords, demands, pickups, capacities, num_vehicles):
        """求解取送货问题 (PDP)"""
        
        model = self.pyvrp.Model()
        
        # 添加车场
        model.add_depot(location=model.add_location(x=coords[0][0], y=coords[0][1]))
        
        # 添加客户（带取货和送货）
        for i in range(1, len(coords)):
            model.add_client(
                location=model.add_location(x=coords[i][0], y=coords[i][1]),
                delivery=demands[i] if demands[i] > 0 else 0,
                pickup=pickups[i] if pickups[i] > 0 else 0
            )
        
        # 添加车辆
        model.add_vehicle_type(num_vehicles, capacity=capacities[0])
        
        # 添加距离
        for frm in model.locations:
            for to in model.locations:
                if frm != to:
                    dist = self._euclidean_distance((frm.x, frm.y), (to.x, to.y))
                    model.add_edge(frm, to, distance=dist)
        
        result = model.solve(stop=self.pyvrp.stop.MaxRuntime(self.max_runtime))
        
        return result
    
    def solve_mdvrp(self, coords, demands, depots, capacities, num_vehicles_per_depot):
        """求解多车场 VRP (MDVRP)"""
        
        model = self.pyvrp.Model()
        
        # 添加多个车场
        for depot_idx in depots:
            model.add_depot(
                location=model.add_location(x=coords[depot_idx][0], y=coords[depot_idx][1])
            )
        
        # 添加客户（分配到最近车场）
        for i in range(len(coords)):
            if i in depots:
                continue
            
            # 找到最近的车场
            min_dist = float('inf')
            nearest_depot = depots[0]
            for depot_idx in depots:
                dist = self._euclidean_distance(coords[i], coords[depot_idx])
                if dist < min_dist:
                    min_dist = dist
                    nearest_depot = depot_idx
            
            model.add_client(
                location=model.add_location(x=coords[i][0], y=coords[i][1]),
                delivery=demands[i],
                depot=nearest_depot
            )
        
        # 为每个车场添加车辆
        for depot_idx in depots:
            model.add_vehicle_type(
                num_vehicles_per_depot, 
                capacity=capacities[depot_idx],
                depot=depot_idx
            )
        
        # 添加距离
        for frm in model.locations:
            for to in model.locations:
                if frm != to:
                    dist = self._euclidean_distance((frm.x, frm.y), (to.x, to.y))
                    model.add_edge(frm, to, distance=dist)
        
        result = model.solve(stop=self.pyvrp.stop.MaxRuntime(self.max_runtime))
        
        return result


# 注册求解器
from ..base import SolverRegistry

try:
    @SolverRegistry.register(SolverType.PYVRP)
    class _PyVRPSolver(PyVRPSolver):
        pass
except:
    pass