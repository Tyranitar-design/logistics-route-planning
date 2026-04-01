#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
智能调度路由
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.services.dispatch_service import get_dispatch_service
from app.services.smart_dispatch_service import get_smart_dispatch_service

dispatch_bp = Blueprint('dispatch', __name__)


@dispatch_bp.route('/auto', methods=['POST'])
@jwt_required()
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
        
        service = get_dispatch_service()
        result = service.auto_dispatch(
            order_ids=order_ids,
            vehicle_ids=vehicle_ids,
            consider_weather=consider_weather,
            consider_traffic=consider_traffic,
            max_orders_per_vehicle=max_orders
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
                        'weather_impact': p.weather_impact,
                        'score': p.score,
                        'suggestions': p.suggestions
                    }
                    for p in result.plans
                ],
                'unassigned_orders': result.unassigned_orders,
                'summary': result.summary
            })
        else:
            return jsonify({'success': False, 'error': result.error}), 400
    
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
        from app.models import db, Order, Vehicle
        from datetime import datetime
        
        data = request.get_json()
        plans = data.get('plans', [])
        
        if not plans:
            return jsonify({'success': False, 'error': '请提供调度计划'}), 400
        
        results = []
        
        for plan in plans:
            vehicle_id = plan.get('vehicle_id')
            order_ids = plan.get('order_ids', [])
            
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
            'message': f'成功分配 {len(results)} 辆车的调度计划',
            'results': results
        })
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@dispatch_bp.route('/preview', methods=['POST'])
@jwt_required()
def preview_dispatch():
    """
    预览调度结果（不实际应用）
    
    与 /auto 接口相同，但不会修改数据库
    """
    return auto_dispatch()


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
        
        service = get_smart_dispatch_service()
        result = service.smart_dispatch(
            order_ids=order_ids,
            vehicle_ids=vehicle_ids,
            weights=weights,
            consider_weather=consider_weather,
            consider_traffic=consider_traffic,
            algorithm=algorithm
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
                        'fuel_cost': p.fuel_cost,
                        'toll_cost': p.toll_cost,
                        'weather_impact': p.weather_impact,
                        'score': p.score,
                        'cost_score': p.cost_score,
                        'time_score': p.time_score,
                        'satisfaction_score': p.satisfaction_score,
                        'suggestions': p.suggestions
                    }
                    for p in result.plans
                ],
                'unassigned_orders': result.unassigned_orders,
                'summary': result.summary,
                'algorithm': result.algorithm,
                'generations': result.generations,
                'convergence_score': result.convergence_score
            })
        else:
            return jsonify({'success': False, 'error': result.error}), 400
    
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
                'id': 'genetic',
                'name': '遗传算法',
                'description': '基于自然选择的多目标优化算法，适合复杂场景',
                'best_for': '多目标优化、大规模订单',
                'performance': '较慢但结果更优'
            },
            {
                'id': 'greedy',
                'name': '贪心算法',
                'description': '快速分配，每次选择局部最优解',
                'best_for': '快速响应、简单场景',
                'performance': '快速但可能不是全局最优'
            },
            {
                'id': 'balanced',
                'name': '均衡策略',
                'description': '综合考虑距离、容量、成本',
                'best_for': '一般场景',
                'performance': '速度和质量的平衡'
            }
        ],
        'weight_options': {
            'cost': '成本优化权重（0-1）',
            'time': '时间优化权重（0-1）',
            'satisfaction': '满意度优化权重（0-1）'
        }
    })
