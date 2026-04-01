#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
敏捷路径优化 API 路由
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.services.agile_optimization_service import get_agile_optimization_service
import logging

logger = logging.getLogger(__name__)

agile_bp = Blueprint('agile', __name__)


@agile_bp.route('/optimize', methods=['POST'])
@jwt_required()
def optimize_routes():
    """
    敏捷路径优化
    
    Body:
        order_ids: 订单ID列表（可选，默认处理所有待分配订单）
        vehicle_ids: 车辆ID列表（可选，默认使用所有可用车辆）
        algorithm: 算法选择（默认 'simulated_annealing'）
            - 'simulated_annealing': 模拟退火
            - 'tabu_search': 禁忌搜索
            - 'hybrid': 混合算法
        constraints: 约束条件（可选）
            {
                "max_distance": 500,        # 最大行驶距离（公里）
                "max_duration": 480,        # 最大行驶时间（分钟）
                "min_load_rate": 50,        # 最小满载率（%）
                "time_window_strict": true  # 是否严格时间窗
            }
        weights: 优化权重（可选）
            {
                "cost": 0.5,        # 成本权重
                "time": 0.3,        # 时间权重
                "load_rate": 0.2    # 满载率权重
            }
    
    Returns:
        {
            "success": true,
            "routes": [...],
            "unassigned_orders": [...],
            "summary": {...},
            "algorithm": "simulated_annealing",
            "iterations": 1000,
            "improvement_rate": 15.5,
            "execution_time": 2.3
        }
    """
    try:
        data = request.get_json() or {}
        
        order_ids = data.get('order_ids')
        vehicle_ids = data.get('vehicle_ids')
        algorithm = data.get('algorithm', 'simulated_annealing')
        constraints = data.get('constraints')
        weights = data.get('weights')
        
        service = get_agile_optimization_service()
        result = service.optimize_routes(
            order_ids=order_ids,
            vehicle_ids=vehicle_ids,
            algorithm=algorithm,
            constraints=constraints,
            weights=weights
        )
        
        if result.success:
            return jsonify({
                'success': True,
                'routes': [
                    {
                        'vehicle_id': r.vehicle_id,
                        'vehicle_info': r.vehicle_info,
                        'nodes': [
                            {
                                'node_id': n.node_id,
                                'type': n.node_type,
                                'order_id': n.order_id,
                                'address': n.address,
                                'latitude': n.latitude,
                                'longitude': n.longitude,
                                'arrival_time': n.arrival_time
                            }
                            for n in r.nodes
                        ],
                        'total_distance': r.total_distance,
                        'total_duration': r.total_duration,
                        'total_cost': {
                            'fuel': r.total_cost.fuel,
                            'toll': r.total_cost.toll,
                            'labor': r.total_cost.labor,
                            'depreciation': r.total_cost.depreciation,
                            'time_cost': r.total_cost.time_cost,
                            'total': r.total_cost.total
                        },
                        'load_rate': r.load_rate,
                        'left_turns': r.left_turns,
                        'time_window_violations': r.time_window_violations,
                        'score': r.score,
                        'optimization_tips': r.optimization_tips
                    }
                    for r in result.routes
                ],
                'unassigned_orders': result.unassigned_orders,
                'summary': result.summary,
                'algorithm': result.algorithm,
                'iterations': result.iterations,
                'improvement_rate': result.improvement_rate,
                'execution_time': result.execution_time
            })
        else:
            return jsonify({'success': False, 'error': result.error}), 400
    
    except Exception as e:
        logger.error(f"敏捷路径优化失败: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@agile_bp.route('/merge-suggestions', methods=['GET'])
@jwt_required()
def get_merge_suggestions():
    """
    获取智能拼单建议
    
    Query params:
        order_ids: 订单ID列表（逗号分隔，可选）
        max_distance: 最大合并距离（公里，默认 30）
    
    Returns:
        {
            "success": true,
            "clusters": [
                {
                    "orders": [...],
                    "order_ids": [1, 2, 3],
                    "total_weight": 5.5,
                    "total_volume": 12.0,
                    "merge_benefit": 150.0,
                    "pickup_area": "北京朝阳区",
                    "delivery_area": "上海浦东"
                }
            ]
        }
    """
    try:
        from app.models import Order, Vehicle
        
        order_ids_str = request.args.get('order_ids')
        max_distance = request.args.get('max_distance', 30, type=float)
        
        # 查询订单
        query = Order.query.filter(Order.status.in_(['pending', 'assigned']))
        if order_ids_str:
            order_ids = [int(x.strip()) for x in order_ids_str.split(',') if x.strip().isdigit()]
            query = query.filter(Order.id.in_(order_ids))
        orders = query.all()
        
        # 查询车辆
        vehicles = Vehicle.query.filter(Vehicle.status == 'available').all()
        
        service = get_agile_optimization_service()
        clusters = service.merging_service.find_mergeable_orders(orders, vehicles)
        
        # 格式化输出
        formatted_clusters = []
        for cluster in clusters:
            formatted_clusters.append({
                'order_ids': cluster['order_ids'],
                'total_weight': cluster['total_weight'],
                'total_volume': cluster['total_volume'],
                'pickup_area': cluster['pickup_area'],
                'delivery_area': cluster['delivery_area'],
                'merge_benefit': cluster['merge_benefit'],
                'order_details': [
                    {
                        'id': o.id,
                        'order_number': o.order_number,
                        'customer': o.customer_name,
                        'weight': o.weight,
                        'volume': o.volume
                    }
                    for o in cluster['orders']
                ]
            })
        
        return jsonify({
            'success': True,
            'clusters': formatted_clusters,
            'total_clusters': len(formatted_clusters),
            'potential_savings': round(sum(c['merge_benefit'] for c in formatted_clusters), 2)
        })
    
    except Exception as e:
        logger.error(f"获取拼单建议失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@agile_bp.route('/realtime/<int:vehicle_id>', methods=['GET'])
@jwt_required()
def get_realtime_suggestions(vehicle_id: int):
    """
    获取实时优化建议
    
    Args:
        vehicle_id: 车辆ID
    
    Query params:
        lat: 当前纬度
        lng: 当前经度
    
    Returns:
        {
            "success": true,
            "vehicle_id": 1,
            "current_load_rate": 75.5,
            "suggestions": [
                {
                    "type": "traffic",
                    "message": "建议避开前方拥堵路段",
                    "priority": "high"
                }
            ]
        }
    """
    try:
        lat = request.args.get('lat', type=float)
        lng = request.args.get('lng', type=float)
        
        service = get_agile_optimization_service()
        
        if lat and lng:
            result = service.get_realtime_suggestions(vehicle_id, (lat, lng))
        else:
            result = service.get_realtime_suggestions(vehicle_id, (0, 0))
        
        return jsonify(result)
    
    except Exception as e:
        logger.error(f"获取实时建议失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@agile_bp.route('/algorithms', methods=['GET'])
@jwt_required()
def get_algorithms():
    """获取可用的优化算法列表"""
    return jsonify({
        'success': True,
        'algorithms': [
            {
                'id': 'simulated_annealing',
                'name': '模拟退火',
                'description': '模拟金属退火过程的随机搜索算法，适合复杂约束优化',
                'best_for': '时间窗约束、多目标优化',
                'performance': '中等速度，结果质量高',
                'parameters': {
                    'initial_temp': {'default': 1000, 'description': '初始温度'},
                    'final_temp': {'default': 1, 'description': '终止温度'},
                    'cooling_rate': {'default': 0.995, 'description': '冷却速率'}
                }
            },
            {
                'id': 'tabu_search',
                'name': '禁忌搜索',
                'description': '通过禁忌表避免重复搜索的启发式算法',
                'best_for': '大规模问题、快速求解',
                'performance': '速度较快，避免局部最优',
                'parameters': {
                    'max_iterations': {'default': 200, 'description': '最大迭代次数'},
                    'tabu_tenure': {'default': 10, 'description': '禁忌期限'}
                }
            },
            {
                'id': 'hybrid',
                'name': '混合算法',
                'description': '结合模拟退火和禁忌搜索的优点',
                'best_for': '追求最优解的场景',
                'performance': '较慢但结果最优',
                'parameters': {}
            }
        ],
        'constraint_options': {
            'max_distance': '最大行驶距离（公里）',
            'max_duration': '最大行驶时间（分钟）',
            'min_load_rate': '最小满载率（%）',
            'time_window_strict': '是否严格时间窗约束'
        },
        'weight_options': {
            'cost': '成本优化权重（0-1）',
            'time': '时间优化权重（0-1）',
            'load_rate': '满载率优化权重（0-1）'
        }
    })


@agile_bp.route('/cost-estimate', methods=['POST'])
@jwt_required()
def estimate_cost():
    """
    成本估算
    
    Body:
        distance: 距离（公里）
        duration: 时长（分钟）
        vehicle_type: 车辆类型
        load_weight: 载重（吨，可选）
    
    Returns:
        {
            "success": true,
            "cost_breakdown": {
                "fuel": 150.0,
                "toll": 100.0,
                "labor": 83.3,
                "depreciation": 50.0,
                "time_cost": 50.0,
                "total": 433.3
            }
        }
    """
    try:
        from app.services.agile_optimization_service import TMSModel
        
        data = request.get_json() or {}
        
        distance = data.get('distance', 100)
        duration = data.get('duration', 120)
        vehicle_type = data.get('vehicle_type', 'truck_medium')
        load_weight = data.get('load_weight', 0)
        
        tms = TMSModel()
        cost = tms.calculate_cost(distance, duration, vehicle_type, load_weight)
        
        return jsonify({
            'success': True,
            'cost_breakdown': {
                'fuel': cost.fuel,
                'toll': cost.toll,
                'labor': cost.labor,
                'depreciation': cost.depreciation,
                'time_cost': cost.time_cost,
                'total': cost.total
            },
            'parameters': {
                'distance_km': distance,
                'duration_minutes': duration,
                'vehicle_type': vehicle_type,
                'load_weight_tons': load_weight,
                'fuel_price': tms.fuel_price,
                'toll_rate': tms.toll_rate,
                'labor_rate': tms.labor_rate
            }
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@agile_bp.route('/apply', methods=['POST'])
@jwt_required()
def apply_optimization():
    """
    应用优化结果
    
    Body:
        routes: 优化后的路线列表
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
        from app.models import db, Order, Vehicle
        from datetime import datetime
        
        data = request.get_json()
        routes = data.get('routes', [])
        
        if not routes:
            return jsonify({'success': False, 'error': '请提供路线方案'}), 400
        
        results = []
        
        for route in routes:
            vehicle_id = route.get('vehicle_id')
            order_ids = route.get('order_ids', [])
            
            # 更新车辆状态
            vehicle = Vehicle.query.get(vehicle_id)
            if vehicle:
                vehicle.status = 'in_use'
            
            # 更新订单状态
            for order_id in order_ids:
                order = Order.query.get(order_id)
                if order:
                    order.status = 'assigned'
                    order.vehicle_id = vehicle_id
                    order.updated_at = datetime.utcnow()
            
            results.append({
                'vehicle_id': vehicle_id,
                'orders_updated': len(order_ids)
            })
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'成功应用 {len(results)} 条路线优化方案',
            'results': results
        })
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@agile_bp.route('/compare', methods=['POST'])
@jwt_required()
def compare_algorithms():
    """
    对比不同算法效果
    
    Body:
        order_ids: 订单ID列表（可选）
        vehicle_ids: 车辆ID列表（可选）
        algorithms: 要对比的算法列表（默认全部）
    
    Returns:
        各算法的对比结果
    """
    try:
        data = request.get_json() or {}
        
        order_ids = data.get('order_ids')
        vehicle_ids = data.get('vehicle_ids')
        algorithms = data.get('algorithms', ['simulated_annealing', 'tabu_search', 'hybrid'])
        
        service = get_agile_optimization_service()
        results = []
        
        for algorithm in algorithms:
            result = service.optimize_routes(
                order_ids=order_ids,
                vehicle_ids=vehicle_ids,
                algorithm=algorithm
            )
            
            if result.success:
                results.append({
                    'algorithm': algorithm,
                    'total_cost': result.summary.get('total_cost_yuan', 0),
                    'total_distance': result.summary.get('total_distance_km', 0),
                    'avg_load_rate': result.summary.get('avg_load_rate', 0),
                    'improvement_rate': result.improvement_rate,
                    'execution_time': result.execution_time,
                    'routes_count': len(result.routes)
                })
        
        # 排序
        results.sort(key=lambda x: x['total_cost'])
        
        return jsonify({
            'success': True,
            'comparison': results,
            'best_algorithm': results[0]['algorithm'] if results else None,
            'recommendation': '建议选择成本最低且执行时间合理的算法'
        })
    
    except Exception as e:
        logger.error(f"算法对比失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500