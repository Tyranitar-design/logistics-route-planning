#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
智能调度路由
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.services.dispatch_service import get_dispatch_service
from app.services.smart_dispatch_service import get_smart_dispatch_service
from app.services.dispatch_orchestration_service import get_dispatch_orchestration_service
from app.utils.rate_limiter import rate_limit, RateLimits

dispatch_bp = Blueprint('dispatch', __name__)


SMART_DISPATCH_TRUTH_CONTRACT = {
    'data_source': 'postgres_orders_vehicles_nodes',
    'distance_source': 'haversine_legacy_dispatch',
    'path_source': 'dispatch_assignment_sequence',
    'authenticity_level': 'C',
    'fallback_reason': (
        'smart_dispatch_legacy_service_uses_haversine_distance_matrix; '
        'not_yet_precise_road_distance_or_turn_by_turn_path'
    ),
}


def _current_user_id():
    try:
        identity = get_jwt_identity()
        return int(identity) if identity is not None else None
    except Exception:
        return None


def _normalize_smart_dispatch_summary(summary, plans, unassigned_orders):
    """Keep legacy summary keys while adding frontend display and truth-contract keys."""
    summary = dict(summary or {})
    assigned_orders = sum(len(getattr(plan, 'orders', []) or []) for plan in plans)
    if assigned_orders == 0:
        assigned_orders = summary.get('assigned_orders', 0)

    unassigned_count = len(unassigned_orders or [])
    if unassigned_count == 0:
        unassigned_count = summary.get('unassigned_orders', 0)

    vehicles_used = len(plans or [])
    if vehicles_used == 0:
        vehicles_used = summary.get('vehicles_used', 0)

    total_distance = round(float(summary.get('total_distance', 0) or 0), 2)
    total_duration = round(float(summary.get('total_duration', 0) or 0), 2)
    total_cost = round(float(summary.get('total_cost', 0) or 0), 2)
    avg_cost = summary.get('avg_cost_per_order')
    if avg_cost is None:
        avg_cost = round(total_cost / assigned_orders, 2) if assigned_orders else 0

    summary.update({
        'assigned_orders': assigned_orders,
        'unassigned_orders': unassigned_count,
        'vehicles_used': vehicles_used,
        'total_distance': total_distance,
        'total_duration': total_duration,
        'total_cost': total_cost,
        'avg_cost_per_order': round(float(avg_cost or 0), 2),
        'total_orders_assigned': assigned_orders,
        'total_orders_unassigned': unassigned_count,
        'total_vehicles_used': vehicles_used,
        'total_distance_km': total_distance,
        'total_duration_min': total_duration,
        'average_cost_per_order': round(float(avg_cost or 0), 2),
        **SMART_DISPATCH_TRUTH_CONTRACT,
    })
    return summary


@dispatch_bp.route('/auto', methods=['POST'])
@jwt_required()
@rate_limit(max_requests=15, window_seconds=60, key_func=lambda: f"auto_dispatch:{get_jwt_identity()}")
def auto_dispatch():
    """
    自动调度
    
    Body:
        order_ids: 订单ID列表（可选，默认处理所有待分配订单）
        vehicle_ids: 车辆ID列表（可选）
        consider_weather: 是否考虑天气（默认 true）
        consider_traffic: 是否考虑路况（默认 true）
        max_orders_per_vehicle: 每车最大订单数（默认 5）
    
    Returns:
        {
            "success": true,
            "plans": [...],  // 调度计划列表
            "unassigned_orders": [...],  // 未分配订单
            "summary": {...}  // 汇总信息
        }
    """
    try:
        data = request.get_json() or {}
        
        order_ids = data.get('order_ids')
        vehicle_ids = data.get('vehicle_ids')
        consider_weather = data.get('consider_weather', True)
        consider_traffic = data.get('consider_traffic', True)
        max_orders = data.get('max_orders_per_vehicle', 5)
        
        service = get_dispatch_orchestration_service()
        result = service.preview(
            {
                'order_ids': order_ids,
                'vehicle_ids': vehicle_ids,
                'consider_weather': consider_weather,
                'consider_traffic': consider_traffic,
                'max_orders_per_vehicle': max_orders,
                'algorithm': data.get('algorithm', 'balanced'),
                'weights': data.get('weights', {'cost': 0.4, 'time': 0.3, 'satisfaction': 0.3}),
                'limit': data.get('limit', data.get('per_page', 100)),
            },
            user_id=_current_user_id(),
        )

        status = 200 if result.get('success') else 400
        return jsonify(result), status
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@dispatch_bp.route('/merge-suggestions', methods=['GET'])
@jwt_required()
def suggest_merge():
    """
    获取可合并订单建议
    
    Query params:
        order_ids: 订单ID列表（逗号分隔，可选）
        max_distance: 最大合并距离（公里，默认 50）
    
    Returns:
        {
            "success": true,
            "clusters": [
                {
                    "orders": [...],
                    "order_ids": [...],
                    "center": {"latitude": ..., "longitude": ...},
                    "total_weight": ...,
                    "total_volume": ...
                }
            ]
        }
    """
    try:
        order_ids_str = request.args.get('order_ids')
        max_distance = request.args.get('max_distance', 50, type=float)
        
        order_ids = None
        if order_ids_str:
            order_ids = [int(x.strip()) for x in order_ids_str.split(',') if x.strip().isdigit()]
        
        service = get_dispatch_service()
        clusters = service.suggest_merge_orders(
            order_ids=order_ids,
            max_merge_distance=max_distance
        )
        
        return jsonify({
            'success': True,
            'clusters': clusters,
            'total_clusters': len(clusters)
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@dispatch_bp.route('/apply', methods=['POST'])
@jwt_required()
def apply_dispatch():
    """
    应用调度计划
    
    Body:
        plans: 调度计划列表
        [
            {
                "vehicle_id": 1,
                "order_ids": [1, 2, 3]
            }
        ]
    
    Returns:
        应用结果
    """
    try:
        data = request.get_json() or {}
        service = get_dispatch_orchestration_service()
        result = service.apply(data, user_id=_current_user_id())
        status = 200 if result.get('success') else 400
        return jsonify(result), status
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@dispatch_bp.route('/preview', methods=['POST'])
@jwt_required()
def preview_dispatch():
    """
    预览调度结果（不实际应用）
    
    统一调度预览，不修改原始订单/物流明细。
    """
    try:
        data = request.get_json() or {}
        service = get_dispatch_orchestration_service()
        result = service.preview(data, user_id=_current_user_id())
        status = 200 if result.get('success') else 400
        return jsonify(result), status
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@dispatch_bp.route('/health', methods=['GET'])
@jwt_required()
def dispatch_health():
    """调度数据健康与可执行性诊断。"""
    try:
        service = get_dispatch_orchestration_service()
        return jsonify(service.health())
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@dispatch_bp.route('/waves', methods=['POST'])
@jwt_required()
def create_dispatch_wave():
    """创建可计算的调度波次。"""
    try:
        data = request.get_json() or {}
        service = get_dispatch_orchestration_service()
        return jsonify(service.create_wave(data))
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@dispatch_bp.route('/scenarios', methods=['GET'])
@jwt_required()
def list_dispatch_scenarios():
    """列出最近调度场景。"""
    try:
        limit = request.args.get('limit', 20, type=int)
        service = get_dispatch_orchestration_service()
        return jsonify(service.list_scenarios(limit=limit))
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@dispatch_bp.route('/scenarios/<int:scenario_id>', methods=['GET'])
@jwt_required()
def get_dispatch_scenario(scenario_id):
    """查看调度场景详情。"""
    try:
        service = get_dispatch_orchestration_service()
        result = service.scenario_detail(scenario_id)
        status = 200 if result.get('success') else 404
        return jsonify(result), status
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@dispatch_bp.route('/smart', methods=['POST'])
@jwt_required()
def smart_dispatch():
    """
    智能调度 - 使用遗传算法优化
    
    Body:
        order_ids: 订单ID列表（可选，默认处理所有待分配订单）
        vehicle_ids: 车辆ID列表（可选）
        weights: 多目标权重（可选）
            {
                "cost": 0.4,        # 成本权重
                "time": 0.3,        # 时间权重
                "satisfaction": 0.3 # 满意度权重
            }
        consider_weather: 是否考虑天气（默认 true）
        consider_traffic: 是否考虑路况（默认 true）
        algorithm: 算法选择（默认 'genetic'）
            - 'genetic': 遗传算法（推荐）
            - 'greedy': 贪心算法
    
    Returns:
        {
            "success": true,
            "plans": [...],
            "unassigned_orders": [...],
            "summary": {...},
            "algorithm": "genetic",
            "generations": 100,
            "convergence_score": 0.85
        }
    """
    try:
        data = request.get_json() or {}
        
        order_ids = data.get('order_ids')
        vehicle_ids = data.get('vehicle_ids')
        weights = data.get('weights', {'cost': 0.4, 'time': 0.3, 'satisfaction': 0.3})
        consider_weather = data.get('consider_weather', True)
        consider_traffic = data.get('consider_traffic', True)
        algorithm = data.get('algorithm', 'genetic')
        
        service = get_dispatch_orchestration_service()
        result = service.preview(
            {
                'order_ids': order_ids,
                'vehicle_ids': vehicle_ids,
                'weights': weights,
                'consider_weather': consider_weather,
                'consider_traffic': consider_traffic,
                'algorithm': algorithm,
                'limit': data.get('limit', data.get('per_page', 100)),
                'max_orders_per_vehicle': data.get('max_orders_per_vehicle', 5),
                'use_precise_distance': data.get('use_precise_distance', True),
            },
            user_id=_current_user_id(),
        )
        status = 200 if result.get('success') else 400
        return jsonify(result), status
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@dispatch_bp.route('/algorithms', methods=['GET'])
@jwt_required()
def get_algorithms():
    """获取可用的调度算法列表"""
    return jsonify({
        'success': True,
        'algorithms': [
            {
                'id': 'balanced',
                'name': '均衡策略',
                'description': '综合考虑距离、容量、成本，当前生产默认策略',
                'best_for': '真实数据调度、稳定预览',
                'performance': '快速且可解释'
            },
            {
                'id': 'greedy',
                'name': '贪心算法',
                'description': '快速分配，每次选择局部最优解',
                'best_for': '快速响应、简单场景',
                'performance': '快速但可能不是全局最优'
            },
            {
                'id': 'capacity_first',
                'name': '载重优先',
                'description': '优先提升车辆装载率，适合运力紧张波次',
                'best_for': '车辆不足、拼单场景',
                'performance': '快速且偏装载率'
            },
            {
                'id': 'ortools',
                'name': 'OR-Tools',
                'description': '求解器目录已接入；当前按可用性进入影子对比',
                'best_for': '后续约束求解主链路',
                'performance': '可用时快速'
            },
            {
                'id': 'alns',
                'name': 'ALNS',
                'description': '自适应大邻域搜索；当前按可用性进入影子对比',
                'best_for': '大规模 VRP 迭代优化',
                'performance': '适合中大波次'
            },
            {
                'id': 'genetic',
                'name': '遗传算法',
                'description': '保留为对比算法，不再作为生产默认主链路',
                'best_for': '教学演示、对照实验',
                'performance': '较慢'
            }
        ],
        'weight_options': {
            'cost': '成本优化权重（0-1）',
            'time': '时间优化权重（0-1）',
            'satisfaction': '满意度优化权重（0-1）'
        }
    })


@dispatch_bp.route('/optimize-v2', methods=['POST'])
@jwt_required()
def optimize_dispatch_v2():
    """
    使用优化引擎进行调度（V2）
    
    Body:
        order_ids: 订单ID列表
        vehicle_ids: 车辆ID列表
        solver: 求解器类型
        multi_objective: 是否多目标优化
        time_limit: 时间限制
    """
    from app.models import Order, Vehicle, Node
    from app.services.smart_dispatch_service_v2 import smart_dispatch_v2
    
    try:
        data = request.get_json() or {}
        
        order_ids = data.get('order_ids', [])
        vehicle_ids = data.get('vehicle_ids', [])
        solver = data.get('solver', 'genetic')
        multi_objective = data.get('multi_objective', False)
        time_limit = data.get('time_limit', 60)
        
        # 获取数据
        orders = Order.query.filter(Order.id.in_(order_ids)).all() if order_ids else Order.query.filter(Order.status == 'pending').all()
        vehicles = Vehicle.query.filter(Vehicle.id.in_(vehicle_ids)).all() if vehicle_ids else Vehicle.query.filter(Vehicle.status == 'available').all()
        nodes = Node.query.all()
        
        # 找仓库
        depot = Node.query.filter(Node.type == 'depot').first()
        if not depot:
            depot = nodes[0] if nodes else None
        
        if not depot:
            return jsonify({'success': False, 'error': '找不到仓库节点'}), 400
        
        # 调用优化引擎
        result = smart_dispatch_v2.optimize_dispatch(
            orders=orders,
            vehicles=vehicles,
            nodes=nodes,
            depot_node=depot,
            solver_type=solver,
            multi_objective=multi_objective,
            time_limit=time_limit
        )
        
        if result.success:
            return jsonify({
                'success': True,
                'plans': [
                    {
                        'vehicle_id': p.vehicle_id,
                        'vehicle_info': p.vehicle_info,
                        'orders': p.orders,
                        'route_sequence': p.route_sequence,
                        'total_distance': p.total_distance,
                        'total_duration': p.total_duration,
                        'total_cost': p.total_cost,
                        'score': p.score,
                        'load_utilization': p.load_utilization
                    }
                    for p in result.plans
                ],
                'unassigned_orders': result.unassigned_orders,
                'summary': result.summary,
                'solver': result.solver,
                'solve_time': result.solve_time,
                'objectives': result.objectives
            })
        else:
            return jsonify({'success': False, 'error': result.error}), 400
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@dispatch_bp.route('/multi-objective-v2', methods=['POST'])
@jwt_required()
def multi_objective_optimize_v2():
    """
    多目标优化（V2）
    
    返回 Pareto 前沿上的最优解
    """
    from app.models import Order, Vehicle, Node
    from app.services.smart_dispatch_service_v2 import smart_dispatch_v2
    
    try:
        data = request.get_json() or {}
        
        order_ids = data.get('order_ids', [])
        vehicle_ids = data.get('vehicle_ids', [])
        solver = data.get('solver', 'pymoo_nsga2')
        n_gen = data.get('n_gen', 100)
        
        # 获取数据
        orders = Order.query.filter(Order.id.in_(order_ids)).all() if order_ids else Order.query.filter(Order.status == 'pending').all()
        vehicles = Vehicle.query.filter(Vehicle.id.in_(vehicle_ids)).all() if vehicle_ids else Vehicle.query.filter(Vehicle.status == 'available').all()
        nodes = Node.query.all()
        
        depot = Node.query.filter(Node.type == 'depot').first()
        if not depot:
            depot = nodes[0] if nodes else None
        
        if not depot:
            return jsonify({'success': False, 'error': '找不到仓库节点'}), 400
        
        # 调用多目标优化
        result = smart_dispatch_v2.multi_objective_optimize(
            orders=orders,
            vehicles=vehicles,
            nodes=nodes,
            depot_node=depot,
            solver_type=solver,
            n_gen=n_gen
        )
        
        if result.success:
            return jsonify({
                'success': True,
                'plans': [
                    {
                        'vehicle_id': p.vehicle_id,
                        'vehicle_info': p.vehicle_info,
                        'orders': p.orders,
                        'route_sequence': p.route_sequence,
                        'total_distance': p.total_distance,
                        'load_utilization': p.load_utilization
                    }
                    for p in result.plans
                ],
                'summary': result.summary,
                'solver': result.solver,
                'solve_time': result.solve_time,
                'objectives': result.objectives,
                'pareto_front_size': result.summary.get('pareto_size', 1)
            })
        else:
            return jsonify({'success': False, 'error': result.error}), 400
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@dispatch_bp.route('/compare-solvers', methods=['POST'])
@jwt_required()
def compare_solvers():
    """
    对比多个求解器
    """
    try:
        data = request.get_json() or {}
        service = get_dispatch_orchestration_service()
        result = service.compare_solvers(data)
        return jsonify(result)
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
