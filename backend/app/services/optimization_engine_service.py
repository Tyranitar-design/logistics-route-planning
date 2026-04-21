"""
优化引擎集成服务
================

将新的优化引擎集成到现有系统

作者: 小彩
日期: 2026-04-19
"""

import logging
import numpy as np
from typing import Dict, List, Optional, Any
from datetime import datetime

from app.models import db
from app.models import Order, Vehicle, Node

# 导入新的优化引擎
from app.services.optimization_engine import (
    SolverFactory,
    CVRPProblem,
    MultiObjectiveVRP,
    VRPData,
    ResultComparator,
    OptimizationVisualizer,
    SolverType
)

logger = logging.getLogger(__name__)


class OptimizationEngineService:
    """
    优化引擎服务
    
    统一调度各种优化算法
    """
    
    def __init__(self):
        self.solver_factory = SolverFactory()
    
    def optimize_routes(
        self,
        orders: List[Order],
        vehicles: List[Vehicle],
        nodes: List[Node],
        depot_node: Node,
        solver_type: str = 'ortools',
        time_limit: float = 60.0,
        multi_objective: bool = False
    ) -> Dict[str, Any]:
        """
        优化车辆路线
        
        Args:
            orders: 订单列表
            vehicles: 车辆列表
            nodes: 节点列表
            depot_node: 仓库节点
            solver_type: 求解器类型
            time_limit: 时间限制
            multi_objective: 是否多目标优化
        
        Returns:
            优化结果
        """
        # 转换为 VRP 数据
        vrp_data = self._convert_to_vrp_data(orders, vehicles, nodes, depot_node)
        
        if vrp_data is None:
            return {
                'success': False,
                'error': '数据转换失败'
            }
        
        # 创建问题
        if multi_objective:
            problem = MultiObjectiveVRP(vrp_data)
        else:
            problem = CVRPProblem(vrp_data)
        
        # 求解
        try:
            solver_enum = SolverType(solver_type)
            solver = SolverFactory.create_solver(solver_enum)
            result = solver.solve(problem, time_limit=time_limit)
            
            # 转换结果
            routes = self._convert_routes(result.routes, orders, nodes)
            
            return {
                'success': True,
                'routes': routes,
                'total_distance': float(result.primary_objective),
                'solve_time': result.solve_time,
                'gap': result.gap if result.gap else 0.0,
                'solver': result.solver_name,
                'objectives': result.objective_values.tolist() if multi_objective else None
            }
        
        except Exception as e:
            logger.error(f"优化失败: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def compare_solvers(
        self,
        orders: List[Order],
        vehicles: List[Vehicle],
        nodes: List[Node],
        depot_node: Node,
        solver_types: List[str] = None,
        time_limit: float = 30.0
    ) -> Dict[str, Any]:
        """
        对比多个求解器
        
        Args:
            orders: 订单列表
            vehicles: 车辆列表
            nodes: 节点列表
            depot_node: 仓库节点
            solver_types: 求解器类型列表
            time_limit: 时间限制
        
        Returns:
            对比结果
        """
        if solver_types is None:
            solver_types = ['ortools', 'genetic']
        
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
        try:
            results = SolverFactory.solve_with_all(problem, solver_enums, time_limit)
            
            # 对比
            comparison = ResultComparator.compare(results)
            
            # 格式化结果
            formatted = {}
            for solver_type, result in results.items():
                formatted[solver_type.value] = {
                    'routes': self._convert_routes(result.routes, orders, nodes),
                    'distance': float(result.primary_objective),
                    'time': result.solve_time
                }
            
            return {
                'success': True,
                'results': formatted,
                'best_solver': comparison.best_solver.value if comparison.best_solver else None,
                'rankings': [(s.value, float(score)) for s, score in comparison.rankings]
            }
        
        except Exception as e:
            logger.error(f"对比失败: {e}")
            return {'success': False, 'error': str(e)}
    
    def recommend_solver(
        self,
        n_orders: int,
        n_vehicles: int,
        has_time_windows: bool = False,
        need_exact: bool = False
    ) -> Dict[str, Any]:
        """
        推荐求解器
        
        Args:
            n_orders: 订单数
            n_vehicles: 车辆数
            has_time_windows: 是否有时间窗
            need_exact: 是否需要精确解
        
        Returns:
            推荐结果
        """
        # 推荐逻辑
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
            recommended = SolverType.ORTOOLS
            reason = "OR-Tools 快速可靠"
            alternatives = [SolverType.GENETIC]
        
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
            
            for order in orders:
                if order.delivery_node_id and order.delivery_node_id in node_map:
                    node = node_map[order.delivery_node_id]
                    customers.append([node.x or 0, node.y or 0])
                    demands.append(order.weight or 1)
            
            if not customers:
                return None
            
            # 仓库位置
            depot = [depot_node.x or 0, depot_node.y or 0]
            
            # 车辆容量
            capacity = vehicles[0].capacity if vehicles else 50
            n_vehicles = len(vehicles) if vehicles else max(1, len(orders) // 5)
            
            return VRPData(
                n_customers=len(customers),
                n_vehicles=n_vehicles,
                vehicle_capacity=capacity,
                depot=np.array(depot),
                customers=np.array(customers),
                demands=np.array(demands)
            )
        
        except Exception as e:
            logger.error(f"数据转换错误: {e}")
            return None
    
    def _convert_routes(
        self,
        routes: List[List[int]],
        orders: List[Order],
        nodes: List[Node]
    ) -> List[Dict]:
        """转换路线格式"""
        result = []
        node_map = {node.id: node for node in nodes}
        
        for route_idx, route in enumerate(routes):
            route_orders = []
            total_distance = 0
            
            for customer_idx in route:
                if customer_idx <= len(orders):
                    order = orders[customer_idx - 1]
                    route_orders.append({
                        'order_id': order.id,
                        'customer': order.customer_name,
                        'address': order.delivery_address
                    })
            
            result.append({
                'route_id': route_idx + 1,
                'orders': route_orders,
                'n_orders': len(route_orders)
            })
        
        return result


# 创建全局实例
optimization_engine_service = OptimizationEngineService()
