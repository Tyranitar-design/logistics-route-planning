"""
优化引擎 API 路由
================

提供 REST API 接口调用优化引擎

作者: 小彩
日期: 2026-04-19
"""

from flask import Blueprint, request, jsonify
from typing import Dict, Any
import numpy as np

from . import (
    SolverFactory,
    VRPProblem,
    CVRPProblem,
    VRPTWProblem,
    FacilityLocationProblem,
    MultiObjectiveVRP,
    VRPData,
    ResultComparator,
    SolverType
)

optimization_bp = Blueprint('optimization', __name__)


@optimization_bp.route('/api/optimization/solvers', methods=['GET'])
def list_solvers():
    """
    列出所有可用求解器
    
    Returns:
        {
            "solvers": [
                {
                    "type": "gurobi",
                    "name": "Gurobi",
                    "available": true,
                    "description": "...",
                    "best_for": "..."
                },
                ...
            ]
        }
    """
    solvers = []
    
    for solver_type in SolverType:
        info = SolverFactory.get_solver_info(solver_type)
        solvers.append({
            "type": solver_type.value,
            "name": info.get("name", solver_type.value),
            "available": SolverFactory.is_available(solver_type),
            "description": info.get("description", ""),
            "best_for": info.get("best_for", "")
        })
    
    return jsonify({"solvers": solvers})


@optimization_bp.route('/api/optimization/solve', methods=['POST'])
def solve_vrp():
    """
    求解 VRP 问题
    
    Request Body:
        {
            "customers": [[x, y], ...],     # 客户坐标
            "demands": [d1, d2, ...],       # 需求量
            "depot": [x, y],                # 仓库坐标
            "capacity": 50,                 # 车辆容量
            "solver": "ortools",            # 求解器类型
            "time_limit": 60                # 时间限制
        }
    
    Returns:
        {
            "routes": [[1, 2, 3], [4, 5]],  # 路线
            "total_distance": 123.45,       # 总距离
            "solve_time": 1.23,             # 求解时间
            "gap": 0.01                     # 最优间隙
        }
    """
    data = request.get_json()
    
    # 解析数据
    customers = np.array(data.get('customers', []))
    demands = np.array(data.get('demands', []))
    depot = np.array(data.get('depot', [50, 50]))
    capacity = data.get('capacity', 50)
    solver_type_str = data.get('solver', 'ortools')
    time_limit = data.get('time_limit', 60)
    
    n_customers = len(customers)
    
    # 创建 VRP 数据
    vrp_data = VRPData(
        n_customers=n_customers,
        n_vehicles=max(1, int(np.ceil(demands.sum() / capacity * 1.5))),
        vehicle_capacity=capacity,
        depot=depot,
        customers=customers,
        demands=demands
    )
    
    # 创建问题
    problem = CVRPProblem(vrp_data)
    
    # 解析求解器类型
    solver_type = SolverType(solver_type_str)
    
    try:
        # 创建求解器并求解
        solver = SolverFactory.create_solver(solver_type)
        result = solver.solve(problem, time_limit=time_limit)
        
        return jsonify({
            "success": True,
            "routes": result.routes,
            "total_distance": float(result.primary_objective),
            "solve_time": result.solve_time,
            "gap": result.gap if result.gap is not None else 0.0,
            "solver": result.solver_name
        })
    
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@optimization_bp.route('/api/optimization/compare', methods=['POST'])
def compare_solvers():
    """
    对比多个求解器
    
    Request Body:
        {
            "customers": [[x, y], ...],
            "demands": [d1, d2, ...],
            "depot": [x, y],
            "capacity": 50,
            "solvers": ["ortools", "genetic", "gurobi"],
            "time_limit": 60
        }
    
    Returns:
        {
            "results": {
                "ortools": {...},
                "genetic": {...},
                ...
            },
            "comparison": {...},
            "best_solver": "ortools"
        }
    """
    data = request.get_json()
    
    # 解析数据
    customers = np.array(data.get('customers', []))
    demands = np.array(data.get('demands', []))
    depot = np.array(data.get('depot', [50, 50]))
    capacity = data.get('capacity', 50)
    solver_strs = data.get('solvers', ['ortools', 'genetic'])
    time_limit = data.get('time_limit', 60)
    
    n_customers = len(customers)
    
    vrp_data = VRPData(
        n_customers=n_customers,
        n_vehicles=max(1, int(np.ceil(demands.sum() / capacity * 1.5))),
        vehicle_capacity=capacity,
        depot=depot,
        customers=customers,
        demands=demands
    )
    
    problem = CVRPProblem(vrp_data)
    
    # 解析求解器类型
    solver_types = [SolverType(s) for s in solver_strs if SolverFactory.is_available(SolverType(s))]
    
    try:
        # 用多个求解器求解
        results = SolverFactory.solve_with_all(problem, solver_types, time_limit)
        
        # 格式化结果
        formatted = {}
        for solver_type, result in results.items():
            formatted[solver_type.value] = {
                "routes": result.routes,
                "total_distance": float(result.primary_objective),
                "solve_time": result.solve_time,
                "gap": result.gap if result.gap is not None else 0.0
            }
        
        # 对比
        comparison = ResultComparator.compare(results)
        
        return jsonify({
            "success": True,
            "results": formatted,
            "best_solver": comparison.best_solver.value if comparison.best_solver else None,
            "rankings": [(s.value, float(score)) for s, score in comparison.rankings]
        })
    
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@optimization_bp.route('/api/optimization/multi-objective', methods=['POST'])
def solve_multi_objective():
    """
    求解多目标 VRP
    
    Request Body:
        {
            "customers": [[x, y], ...],
            "demands": [d1, d2, ...],
            "service_times": [t1, t2, ...],
            "depot": [x, y],
            "capacity": 50,
            "solver": "pymoo_nsga2",
            "n_gen": 100
        }
    
    Returns:
        {
            "pareto_front": [[f1, f2, f3], ...],
            "best_solution": {
                "routes": [...],
                "objectives": [f1, f2, f3]
            }
        }
    """
    data = request.get_json()
    
    customers = np.array(data.get('customers', []))
    demands = np.array(data.get('demands', []))
    service_times = np.array(data.get('service_times', np.zeros(len(customers))))
    depot = np.array(data.get('depot', [50, 50]))
    capacity = data.get('capacity', 50)
    solver_type_str = data.get('solver', 'pymoo_nsga2')
    n_gen = data.get('n_gen', 100)
    
    n_customers = len(customers)
    
    vrp_data = VRPData(
        n_customers=n_customers,
        n_vehicles=max(1, int(np.ceil(demands.sum() / capacity * 1.5))),
        vehicle_capacity=capacity,
        depot=depot,
        customers=customers,
        demands=demands
    )
    
    problem = MultiObjectiveVRP(vrp_data, service_times)
    
    solver_type = SolverType(solver_type_str)
    
    try:
        solver = SolverFactory.create_solver(solver_type)
        result = solver.solve(problem, n_gen=n_gen)
        
        return jsonify({
            "success": True,
            "routes": result.routes,
            "objectives": result.objective_values.tolist(),
            "pareto_front_size": result.metadata.get('pareto_front_size', 1),
            "solve_time": result.solve_time
        })
    
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@optimization_bp.route('/api/optimization/recommend', methods=['POST'])
def recommend_solver():
    """
    根据问题特征推荐求解器
    
    Request Body:
        {
            "n_customers": 50,
            "n_objectives": 2,
            "has_time_windows": false,
            "need_exact": false
        }
    
    Returns:
        {
            "recommended": "ortools",
            "reason": "...",
            "alternatives": [...]
        }
    """
    data = request.get_json()
    
    n_customers = data.get('n_customers', 10)
    n_objectives = data.get('n_objectives', 1)
    has_time_windows = data.get('has_time_windows', False)
    need_exact = data.get('need_exact', False)
    
    # 推荐逻辑
    recommended = None
    reason = ""
    alternatives = []
    
    if n_objectives > 1:
        # 多目标
        if n_objectives <= 3:
            recommended = SolverType.PYMOO_NSGA2
            reason = "NSGA-II 适合 2-3 个目标的优化"
            alternatives = [SolverType.PYMOO_NSGA3]
        else:
            recommended = SolverType.PYMOO_NSGA3
            reason = "NSGA-III 适合 4+ 个目标的优化"
            alternatives = [SolverType.PYMOO_NSGA2]
    
    elif need_exact:
        # 需要精确解
        if SolverFactory.is_available(SolverType.GUROBI):
            recommended = SolverType.GUROBI
            reason = "Gurobi 提供精确最优解"
            alternatives = [SolverType.ORTOOLS]
        else:
            recommended = SolverType.ORTOOLS
            reason = "OR-Tools 是可用的最佳选择"
    
    elif n_customers > 100:
        # 大规模问题
        recommended = SolverType.ALNS
        reason = "ALNS 适合大规模问题"
        alternatives = [SolverType.ORTOOLS, SolverType.GENETIC]
    
    else:
        # 一般情况
        recommended = SolverType.ORTOOLS
        reason = "OR-Tools 快速可靠"
        alternatives = [SolverType.GENETIC]
    
    # 检查可用性
    if not SolverFactory.is_available(recommended):
        available = SolverFactory.list_available_solvers()
        if available:
            recommended = available[0]
            reason = f"推荐求解器不可用，使用 {recommended.value}"
    
    return jsonify({
        "recommended": recommended.value,
        "reason": reason,
        "alternatives": [s.value for s in alternatives if SolverFactory.is_available(s)]
    })
