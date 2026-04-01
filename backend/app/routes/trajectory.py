#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
历史轨迹回放 API 路由
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from app.services.trajectory_service import get_trajectory_history
from app.models import db, Vehicle, Node, Order

trajectory_bp = Blueprint('trajectory', __name__)


@trajectory_bp.route('/generate/<int:vehicle_id>', methods=['POST'])
@jwt_required()
def generate_trajectory(vehicle_id):
    """
    生成演示轨迹
    
    Body:
        start_node_id: 起点节点ID
        end_node_id: 终点节点ID
        duration_minutes: 时长（分钟，默认60）
    """
    try:
        data = request.get_json() or {}
        
        start_node_id = data.get('start_node_id')
        end_node_id = data.get('end_node_id')
        duration = data.get('duration_minutes', 60)
        
        if not start_node_id or not end_node_id:
            return jsonify({'success': False, 'error': '请提供起点和终点节点'}), 400
        
        start_node = Node.query.get(start_node_id)
        end_node = Node.query.get(end_node_id)
        
        if not start_node or not end_node:
            return jsonify({'success': False, 'error': '节点不存在'}), 404
        
        if not start_node.latitude or not end_node.latitude:
            return jsonify({'success': False, 'error': '节点缺少坐标信息'}), 400
        
        vehicle = Vehicle.query.get(vehicle_id)
        if not vehicle:
            return jsonify({'success': False, 'error': '车辆不存在'}), 404
        
        # 生成轨迹
        service = get_trajectory_history()
        trajectory = service.generate_demo_trajectory(
            vehicle_id,
            start_node.latitude, start_node.longitude,
            end_node.latitude, end_node.longitude,
            duration
        )
        
        return jsonify({
            'success': True,
            'data': {
                'vehicle_id': vehicle_id,
                'plate_number': vehicle.plate_number,
                'start_node': start_node.name,
                'end_node': end_node.name,
                'points_count': len(trajectory),
                'trajectory': trajectory
            }
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@trajectory_bp.route('/<int:vehicle_id>', methods=['GET'])
@jwt_required()
def get_trajectory(vehicle_id):
    """
    获取车辆轨迹历史
    
    Query params:
        start_time: 开始时间（ISO格式）
        end_time: 结束时间（ISO格式）
    """
    try:
        start_time = request.args.get('start_time')
        end_time = request.args.get('end_time')
        
        service = get_trajectory_history()
        trajectory = service.get_trajectory(vehicle_id, start_time, end_time)
        
        vehicle = Vehicle.query.get(vehicle_id)
        
        return jsonify({
            'success': True,
            'data': {
                'vehicle_id': vehicle_id,
                'plate_number': vehicle.plate_number if vehicle else None,
                'points_count': len(trajectory),
                'trajectory': trajectory
            }
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@trajectory_bp.route('/all', methods=['GET'])
@jwt_required()
def get_all_trajectories():
    """获取所有车辆轨迹"""
    try:
        service = get_trajectory_history()
        trajectories = service.get_all_trajectories()
        
        return jsonify({
            'success': True,
            'data': trajectories
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@trajectory_bp.route('/<int:vehicle_id>', methods=['DELETE'])
@jwt_required()
def clear_trajectory(vehicle_id):
    """清除车辆轨迹历史"""
    try:
        service = get_trajectory_history()
        service.clear_trajectory(vehicle_id)
        
        return jsonify({
            'success': True,
            'message': '轨迹已清除'
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@trajectory_bp.route('/completed-orders', methods=['GET'])
@jwt_required()
def get_completed_orders_trajectory():
    """
    获取已完成订单的轨迹
    
    Query params:
        order_id: 订单ID（可选）
        days: 最近几天（默认7）
    """
    try:
        order_id = request.args.get('order_id', type=int)
        days = request.args.get('days', 7, type=int)
        
        query = Order.query.filter(Order.status == 'delivered')
        
        if order_id:
            query = query.filter(Order.id == order_id)
        else:
            from datetime import datetime, timedelta
            start_date = datetime.utcnow() - timedelta(days=days)
            query = query.filter(Order.created_at >= start_date)
        
        orders = query.limit(50).all()
        
        result = []
        for order in orders:
            # 为每个订单生成模拟轨迹
            if order.pickup_node and order.delivery_node:
                pickup = order.pickup_node
                delivery = order.delivery_node
                
                if pickup.latitude and delivery.latitude:
                    service = get_trajectory_history()
                    
                    # 使用订单ID作为轨迹ID的一部分
                    trajectory = service.generate_demo_trajectory(
                        order.id + 1000,  # 偏移避免冲突
                        pickup.latitude, pickup.longitude,
                        delivery.latitude, delivery.longitude,
                        random.randint(30, 90)
                    )
                    
                    result.append({
                        'order_id': order.id,
                        'order_number': order.order_number,
                        'customer_name': order.customer_name,
                        'pickup_node': pickup.name,
                        'delivery_node': delivery.name,
                        'vehicle_id': order.vehicle_id,
                        'trajectory': trajectory
                    })
        
        return jsonify({
            'success': True,
            'data': result,
            'count': len(result)
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
