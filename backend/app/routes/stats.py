#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
数据统计路由
"""

from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required
from datetime import datetime, timedelta
from sqlalchemy import func
from app.models import db, Order, Node, Route, Vehicle

stats_bp = Blueprint('stats', __name__)


@stats_bp.route('/overview', methods=['GET'])
@jwt_required()
def get_overview():
    """获取总览统计数据"""
    try:
        # 统计各表总数
        total_orders = Order.query.count()
        total_nodes = Node.query.count()
        total_routes = Route.query.count()
        total_vehicles = Vehicle.query.count()
        
        # 统计订单状态
        pending_orders = Order.query.filter_by(status='pending').count()
        in_transit_orders = Order.query.filter_by(status='in_transit').count()
        delivered_orders = Order.query.filter_by(status='delivered').count()
        
        # 统计车辆状态
        available_vehicles = Vehicle.query.filter_by(status='available').count()
        in_use_vehicles = Vehicle.query.filter_by(status='in_use').count()
        
        return jsonify({
            'total_orders': total_orders,
            'total_nodes': total_nodes,
            'total_routes': total_routes,
            'total_vehicles': total_vehicles,
            'pending_orders': pending_orders,
            'in_transit_orders': in_transit_orders,
            'delivered_orders': delivered_orders,
            'available_vehicles': available_vehicles,
            'in_use_vehicles': in_use_vehicles
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@stats_bp.route('/orders/trend', methods=['GET'])
@jwt_required()
def get_order_trend():
    """获取订单趋势数据（最近7天）"""
    try:
        today = datetime.utcnow().date()
        trend_data = []
        
        for i in range(6, -1, -1):
            date = today - timedelta(days=i)
            # 处理 created_at 可能为 NULL 的情况
            count = Order.query.filter(
                Order.created_at.isnot(None),
                func.date(Order.created_at) == date
            ).count()
            trend_data.append({
                'date': date.strftime('%m-%d'),
                'count': count
            })
        
        return jsonify({'trend': trend_data})
    except Exception as e:
        print(f"订单趋势查询错误: {str(e)}")
        return jsonify({'error': str(e)}), 500


@stats_bp.route('/orders/distribution', methods=['GET'])
@jwt_required()
def get_order_distribution():
    """获取订单状态分布"""
    try:
        distribution = db.session.query(
            Order.status,
            func.count(Order.id).label('count')
        ).group_by(Order.status).all()
        
        status_map = {
            'pending': '待分配',
            'assigned': '已分配',
            'in_transit': '运输中',
            'delivered': '已送达',
            'cancelled': '已取消'
        }
        
        result = []
        for status, count in distribution:
            result.append({
                'status': status,
                'name': status_map.get(status, status),
                'value': count
            })
        
        return jsonify({'distribution': result})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@stats_bp.route('/routes/analysis', methods=['GET'])
@jwt_required()
def get_route_analysis():
    """获取路线分析数据"""
    try:
        # 路线距离分布
        routes = Route.query.all()
        
        distance_ranges = {
            '0-50km': 0,
            '50-100km': 0,
            '100-200km': 0,
            '200km以上': 0
        }
        
        for route in routes:
            if route.distance:
                if route.distance <= 50:
                    distance_ranges['0-50km'] += 1
                elif route.distance <= 100:
                    distance_ranges['50-100km'] += 1
                elif route.distance <= 200:
                    distance_ranges['100-200km'] += 1
                else:
                    distance_ranges['200km以上'] += 1
        
        return jsonify({
            'distance_distribution': distance_ranges,
            'total_routes': len(routes)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@stats_bp.route('/vehicles/utilization', methods=['GET'])
@jwt_required()
def get_vehicle_utilization():
    """获取车辆利用率"""
    try:
        total = Vehicle.query.count()
        if total == 0:
            return jsonify({'utilization': []})
        
        status_count = db.session.query(
            Vehicle.status,
            func.count(Vehicle.id).label('count')
        ).group_by(Vehicle.status).all()
        
        status_map = {
            'available': '空闲',
            'in_use': '使用中',
            'maintenance': '维修中'
        }
        
        utilization = []
        for status, count in status_count:
            utilization.append({
                'name': status_map.get(status, status),
                'value': count
            })
        
        return jsonify({'utilization': utilization})
    except Exception as e:
        print(f"车辆利用率查询错误: {str(e)}")
        return jsonify({'error': str(e)}), 500
