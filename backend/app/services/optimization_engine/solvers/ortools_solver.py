"""
OR-Tools 求解器
==============

使用 Google OR-Tools 求解 VRP 问题

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


@SolverRegistry.register(SolverType.ORTOOLS)
class ORToolsSolver(OptimizationSolver):
    """
    OR-Tools VRP 求解器
    """
    
    def __init__(self, 
                 first_solution_strategy: str = "PATH_CHEAPEST_ARC",
                 local_search_metaheuristic: str = "GUIDED_LOCAL_SEARCH",
                 **kwargs):
        """
        初始化
        
        Args:
            first_solution_strategy: 初始解策略
            local_search_metaheuristic: 局部搜索元启发式
            **kwargs: 其他参数
        """
        super().__init__("OR-Tools", SolverType.ORTOOLS)
        self.first_solution_strategy = first_solution_strategy
        self.local_search_metaheuristic = local_search_metaheuristic
        self.parameters.update(kwargs)
    
    def is_available(self) -> bool:
        """检查 OR-Tools 是否可用"""
        try:
            from ortools.constraint_solver import routing_enums_pb2
            from ortools.constraint_solver import pywrapcp
            return True
        except ImportError:
            return False
    
    @timeit
    def solve(self, 
              problem: OptimizationProblem,
              time_limit: float = 60.0,
              **kwargs) -> OptimizationResult:
        """
        求解 VRP 问题
        
        Args:
            problem: VRP 问题
            time_limit: 时间限制（秒）
            **kwargs: 其他参数
        
        Returns:
            优化结果
        """
        from ortools.constraint_solver import routing_enums_pb2
        from ortools.constraint_solver import pywrapcp
        
        # 获取问题数据
        data = problem.data
        
        # 创建路由模型
        manager = pywrapcp.RoutingIndexManager(
            data.n_customers + 1,  # 节点数
            data.n_vehicles,       # 车辆数
            0                      # 仓库索引
        )
        routing = pywrapcp.RoutingModel(manager)
        
        # 距离回调
        def distance_callback(from_index, to_index):
            from_node = manager.IndexToNode(from_index)
            to_node = manager.IndexToNode(to_index)
            return int(data.distance_matrix[from_node][to_node] * 100)
        
        transit_callback_index = routing.RegisterTransitCallback(distance_callback)
        routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)
        
        # 容量约束
        def demand_callback(from_index):
            from_node = manager.IndexToNode(from_index)
            if from_node == 0:
                return 0
            return int(data.demands[from_node - 1])
        
        demand_callback_index = routing.RegisterUnaryTransitCallback(demand_callback)
        routing.AddDimensionWithVehicleCapacity(
            demand_callback_index,
            0,  # null capacity slack
            [int(data.vehicle_capacity)] * data.n_vehicles,
            True,
            'Capacity'
        )
        
        # 求解参数
        search_parameters = pywrapcp.DefaultRoutingSearchParameters()
        
        # 设置初始解策略
        strategy_map = {
            "PATH_CHEAPEST_ARC": routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC,
            "SAVINGS": routing_enums_pb2.FirstSolutionStrategy.SAVINGS,
            "SWEEP": routing_enums_pb2.FirstSolutionStrategy.SWEEP,
        }
        search_parameters.first_solution_strategy = strategy_map.get(
            self.first_solution_strategy,
            routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
        )
        
        # 设置局部搜索
        metaheuristic_map = {
            "GUIDED_LOCAL_SEARCH": routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH,
            "SIMULATED_ANNEALING": routing_enums_pb2.LocalSearchMetaheuristic.SIMULATED_ANNEALING,
            "TABU_SEARCH": routing_enums_pb2.LocalSearchMetaheuristic.TABU_SEARCH,
        }
        search_parameters.local_search_metaheuristic = metaheuristic_map.get(
            self.local_search_metaheuristic,
            routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
        )
        
        search_parameters.time_limit.seconds = int(time_limit)
        
        # 求解
        solution = routing.SolveWithParameters(search_parameters)
        
        if not solution:
            raise RuntimeError("OR-Tools 未能找到解")
        
        # 提取路线
        routes = []
        total_distance = 0
        
        for vehicle_id in range(data.n_vehicles):
            index = routing.Start(vehicle_id)
            route = []
            route_distance = 0
            
            while not routing.IsEnd(index):
                node = manager.IndexToNode(index)
                route.append(node)
                previous_index = index
                index = solution.Value(routing.NextVar(index))
                route_distance += routing.GetArcCostForVehicle(
                    previous_index, index, vehicle_id
                )
            
            route.append(manager.IndexToNode(index))  # 返回仓库
            
            if len(route) > 2:  # 非空路线
                routes.append(route)
                total_distance += route_distance / 100  # 还原
        
        # 创建结果
        result = OptimizationResult(
            solver_name=self.name,
            problem_type=problem.problem_type,
            solution=routes,
            objective_values=np.array([total_distance]),
            solve_time=0.0,  # 由装饰器填充
            routes=routes
        )
        
        return result
