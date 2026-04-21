"""
智能调度服务 - 升级版
====================

使用新的优化引擎进行智能调度
支持：多种求解器、多目标优化、精确求解

作者: 小彩
日期: 2026-04-19
"""

import logging
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, field

from app.models import db
from app.models import Order, Vehicle, Node

# 导入优化引擎
from app.services.optimization_engine import (
    SolverFactory,
    CVRPProblem,
    MultiObjectiveVRP,
    VRPData,
    ResultComparator,
    SolverType
)

logger = logging.getLogger(__name__)


@dataclass
class DispatchPlanV2:
    """调度计划 V2"""
    vehicle_id: int
    vehicle_info: dict
    orders: List[dict]
    route_sequence: List[int]  # 客户ID序列
    total_distance: float
    total_duration: float
    total_cost: float
    score: float
    load_utilization: float  # 负载利用率
    
    # 多目标得分
    cost_score: float = 0.0
    time_score: float = 0.0
    load_score: float = 0.0


@dataclass
class OptimizationResultV2:
    """优化结果 V2"""
    success: bool
    plans: List[DispatchPlanV2]
    unassigned_orders: List[dict]
    summary: dict
    solver: str
    solve_time: float
    objectives: List[float] = None
    pareto_front: List[List[float]] = None  # Pareto 前沿
    error: str = None


class SmartDispatchServiceV2:
    """
    智能调度服务 V2
    
    使用新的优化引擎，支持多种求解器
    """
    
    def __init__(self):
        self.solver_factory = SolverFactory()
    
    def optimize_dispatch(
        self,
        orders: List[Order],
        vehicles: List[Vehicle],
        nodes: List[Node],
        depot_node: Node,
        solver_type: str = 'genetic',
        multi_objective: bool = False,
        time_limit: float = 60.0,
        **kwargs
    ) -> OptimizationResultV2:
        """
        优化调度
        
        Args:
            orders: 订单列表
            vehicles: 车辆列表
            nodes: 节点列表
            depot_node: 仓库节点
            solver_type: 求解器类型
            multi_objective: 是否多目标优化
            time_limit: 时间限制
        
        Returns:
            优化结果
        """
        try:
            # 转换数据
            vrp_data = self._convert_to_vrp_data(orders, vehicles, nodes, depot_node)
            
            if vrp_data is None:
                return OptimizationResultV2(
                    success=False,
                    plans=[],
                    unassigned_orders=[o.to_dict() for o in orders],
                    summary={},
                    solver='none',
                    solve_time=0,
                    error='数据转换失败'
                )
            
            # 创建问题
            if multi_objective:
                problem = MultiObjectiveVRP(vrp_data)
            else:
                problem = CVRPProblem(vrp_data)
            
            # 求解
            solver_enum = SolverType(solver_type)
            solver = SolverFactory.create_solver(solver_enum)
            result = solver.solve(problem, time_limit=time_limit, **kwargs)
            
            # 转换结果
            plans = self._convert_to_plans(result.routes, orders, vehicles, nodes, vrp_data)
            
            # 计算统计
            summary = {
                'total_distance': float(result.primary_objective),
                'solve_time': result.solve_time,
                'n_routes': len(result.routes),
                'solver': result.solver_name,
                'gap': float(result.gap) if result.gap else 0.0
            }
            
            return OptimizationResultV2(
                success=True,
                plans=plans,
                unassigned_orders=[],
                summary=summary,
                solver=result.solver_name,
                solve_time=result.solve_time,
                objectives=[float(x) for x in result.objective_values] if multi_objective else None,
                pareto_front=result.metadata.get('pareto_front', None) if multi_objective else None
            )
        
        except Exception as e:
            logger.error(f"优化失败: {e}")
            return OptimizationResultV2(
                success=False,
                plans=[],
                unassigned_orders=[o.to_dict() for o in orders],
                summary={},
                solver='error',
                solve_time=0,
                error=str(e)
            )
    
    def multi_objective_optimize(
        self,
        orders: List[Order],
        vehicles: List[Vehicle],
        nodes: List[Node],
        depot_node: Node,
        solver_type: str = 'pymoo_nsga2',
        n_gen: int = 100,
        return_pareto: bool = True
    ) -> OptimizationResultV2:
        """
        多目标优化
        
        返回 Pareto 前沿上的最优解
        
        Args:
            orders: 订单列表
            vehicles: 车辆列表
            nodes: 节点列表
            depot_node: 仓库节点
            solver_type: 求解器（NSGA-II 或 NSGA-III）
            n_gen: 迭代次数
            return_pareto: 是否返回 Pareto 前沿
        
        Returns:
            优化结果
        """
        try:
            # 转换数据
            vrp_data = self._convert_to_vrp_data(orders, vehicles, nodes, depot_node)
            
            if vrp_data is None:
                return OptimizationResultV2(
                    success=False,
                    plans=[],
                    unassigned_orders=[o.to_dict() for o in orders],
                    summary={},
                    solver='none',
                    solve_time=0,
                    error='数据转换失败'
                )
            
            # 创建多目标问题
            problem = MultiObjectiveVRP(vrp_data)
            
            # 求解
            solver_enum = SolverType(solver_type)
            solver = SolverFactory.create_solver(solver_enum)
            result = solver.solve(problem, n_gen=n_gen)
            
            # 转换结果
            plans = self._convert_to_plans(result.routes, orders, vehicles, nodes, vrp_data)
            
            # 构建多目标总结
            objectives = [float(x) for x in result.objective_values]
            summary = {
                'total_distance': objectives[0],
                'total_time': objectives[1],
                'n_vehicles': int(objectives[2]),
                'solve_time': result.solve_time,
                'pareto_size': result.metadata.get('pareto_front_size', 1)
            }
            
            return OptimizationResultV2(
                success=True,
                plans=plans,
                unassigned_orders=[],
                summary=summary,
                solver=result.solver_name,
                solve_time=result.solve_time,
                objectives=objectives,
                pareto_front=result.metadata.get('pareto_front', None) if return_pareto else None
            )
        
        except Exception as e:
            logger.error(f"多目标优化失败: {e}")
            return OptimizationResultV2(
                success=False,
                plans=[],
                unassigned_orders=[o.to_dict() for o in orders],
                summary={},
                solver='error',
                solve_time=0,
                error=str(e)
            )
    
    def compare_solvers(
        self,
        orders: List[Order],
        vehicles: List[Vehicle],
        nodes: List[Node],
        depot_node: Node,
        solver_types: List[str] = None,
        time_limit: float = 30.0
    ) -> Dict:
        """
        对比多个求解器
        
        Args:
            orders: 订单列表
            vehicles: 车辆列表
            nodes: 节点列表
            depot_node: 仓库节点
            solver_types: 求解器列表
            time_limit: 时间限制
        
        Returns:
            对比结果
        """
        if solver_types is None:
            solver_types = ['genetic', 'ortools', 'alns']
        
        # 转换数据
        vrp_data = self._convert_to_vrp_data(orders, vehicles, nodes, depot_node)
        
        if vrp_data is None:
            return {'success': False, 'error': '数据转换失败'}
        
        problem = CVRPProblem(vrp_data)
        
        # 解析求解器类型
        solver_enums = []
        for s in solver_types:
            try:
                st = SolverType(s)
                if SolverFactory.is_available(st):
                    solver_enums.append(st)
            except:
                pass
        
        if not solver_enums:
            return {'success': False, 'error': '没有可用的求解器'}
        
        # 求解
        results = SolverFactory.solve_with_all(problem, solver_enums, time_limit)
        
        # 对比
        comparison = ResultComparator.compare(results)
        
        # 格式化
        formatted = {}
        for solver_type, res in results.items():
            formatted[solver_type.value] = {
                'distance': float(res.primary_objective),
                'time': res.solve_time,
                'gap': float(res.gap) if res.gap else 0.0,
                'routes': res.routes
            }
        
        return {
            'success': True,
            'results': formatted,
            'best_solver': comparison.best_solver.value if comparison.best_solver else None,
            'rankings': [(s.value, float(score)) for s, score in comparison.rankings]
        }
    
    def recommend_solver(
        self,
        n_orders: int,
        n_vehicles: int,
        need_exact: bool = False
    ) -> Dict:
        """
        推荐求解器
        
        Args:
            n_orders: 订单数
            n_vehicles: 车辆数
            need_exact: 是否需要精确解
        
        Returns:
            推荐结果
        """
        recommended = None
        reason = ""
        alternatives = []
        
        if need_exact:
            if SolverFactory.is_available(SolverType.GUROBI):
                recommended = SolverType.GUROBI
                reason = "Gurobi 提供精确最优解"
                alternatives = [SolverType.ORTOOLS]
            else:
                recommended = SolverType.ORTOOLS
                reason = "OR-Tools 是可用的最佳选择"
        
        elif n_orders > 50:
            recommended = SolverType.ALNS
            reason = "ALNS 适合大规模问题"
            alternatives = [SolverType.GENETIC]
        
        else:
            recommended = SolverType.GENETIC
            reason = "遗传算法稳定可靠"
            alternatives = [SolverType.ORTOOLS]
        
        return {
            'recommended': recommended.value,
            'reason': reason,
            'alternatives': [s.value for s in alternatives if SolverFactory.is_available(s)]
        }
    
    def _convert_to_vrp_data(
        self,
        orders: List[Order],
        vehicles: List[Vehicle],
        nodes: List[Node],
        depot_node: Node
    ) -> Optional[VRPData]:
        """转换为 VRP 数据格式"""
        try:
            # 构建节点映射
            node_map = {node.id: node for node in nodes}
            
            # 客户位置和需求
            customers = []
            demands = []
            order_list = list(orders)
            
            for order in order_list:
                if order.delivery_node_id and order.delivery_node_id in node_map:
                    node = node_map[order.delivery_node_id]
                    customers.append([float(node.x or 0), float(node.y or 0)])
                    demands.append(float(order.weight or 1))
            
            if not customers:
                return None
            
            # 仓库位置
            depot = [float(depot_node.x or 0), float(depot_node.y or 0)]
            
            # 车辆容量
            vehicle_list = list(vehicles)
            capacity = vehicle_list[0].capacity if vehicle_list else 50
            n_vehicles = len(vehicle_list) if vehicle_list else max(1, len(customers) // 5)
            
            return VRPData(
                n_customers=len(customers),
                n_vehicles=n_vehicles,
                vehicle_capacity=float(capacity),
                depot=np.array(depot),
                customers=np.array(customers),
                demands=np.array(demands)
            )
        
        except Exception as e:
            logger.error(f"数据转换错误: {e}")
            return None
    
    def _convert_to_plans(
        self,
        routes: List[List[int]],
        orders: List[Order],
        vehicles: List[Vehicle],
        nodes: List[Node],
        vrp_data: VRPData
    ) -> List[DispatchPlanV2]:
        """转换路线为调度计划"""
        plans = []
        vehicle_list = list(vehicles)
        order_list = list(orders)
        node_map = {node.id: node for node in nodes}
        
        for route_idx, route in enumerate(routes):
            # 获取车辆信息
            vehicle = vehicle_list[route_idx] if route_idx < len(vehicle_list) else None
            vehicle_info = {
                'id': vehicle.id if vehicle else route_idx + 1,
                'plate': vehicle.plate if vehicle else f'车辆{route_idx + 1}',
                'capacity': vehicle.capacity if vehicle else vrp_data.vehicle_capacity
            }
            
            # 获取订单
            route_orders = []
            total_demand = 0
            for customer_idx in route:
                if customer_idx <= len(order_list):
                    order = order_list[customer_idx - 1]
                    route_orders.append({
                        'id': order.id,
                        'customer': order.customer_name,
                        'address': order.delivery_address,
                        'demand': float(vrp_data.demands[customer_idx - 1])
                    })
                    total_demand += float(vrp_data.demands[customer_idx - 1])
            
            # 计算距离
            total_distance = 0
            prev = 0
            for customer_idx in route:
                total_distance += float(vrp_data.distance_matrix[prev][customer_idx])
                prev = customer_idx
            total_distance += float(vrp_data.distance_matrix[prev][0])
            
            # 负载利用率
            load_utilization = total_demand / vrp_data.vehicle_capacity if vrp_data.vehicle_capacity > 0 else 0
            
            plan = DispatchPlanV2(
                vehicle_id=vehicle_info['id'],
                vehicle_info=vehicle_info,
                orders=route_orders,
                route_sequence=route,
                total_distance=total_distance,
                total_duration=total_distance * 2,  # 假设速度
                total_cost=total_distance * 0.5,  # 假设成本
                score=100 - total_distance * 0.1,
                load_utilization=load_utilization,
                cost_score=100 - total_distance * 0.3,
                time_score=100 - total_distance * 0.2,
                load_score=load_utilization * 100
            )
            
            plans.append(plan)
        
        return plans


# 创建全局实例
smart_dispatch_v2 = SmartDispatchServiceV2()
