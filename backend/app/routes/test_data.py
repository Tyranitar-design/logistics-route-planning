#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试数据 API 路由
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from app.services.test_data_generator import test_data_generator
from app.services.audit_service import audit_service, AuditModule, AuditAction
from app.utils.rate_limiter import rate_limit, RateLimits

test_data_bp = Blueprint('test_data', __name__)


@test_data_bp.route('/generate', methods=['POST'])
@jwt_required()
@rate_limit(**RateLimits.SENSITIVE)
def generate_data():
    """生成测试数据"""
    data = request.get_json() or {}
    
    nodes_count = data.get('nodes_count', 20)
    vehicles_count = data.get('vehicles_count', 15)
    orders_count = data.get('orders_count', 50)
    clear_existing = data.get('clear_existing', False)
    
    # 限制数量
    nodes_count = min(max(nodes_count, 0), 100)
    vehicles_count = min(max(vehicles_count, 0), 50)
    orders_count = min(max(orders_count, 0), 200)
    
    result = test_data_generator.generate_all(
        nodes_count=nodes_count,
        vehicles_count=vehicles_count,
        orders_count=orders_count,
        clear_existing=clear_existing
    )
    
    if result.get('success'):
        # 记录审计日志
        audit_service.log(
            action=AuditAction.CREATE,
            module=AuditModule.SYSTEM,
            description=f'生成测试数据: {result.get("message")}',
            extra_data={
                'nodes_count': nodes_count,
                'vehicles_count': vehicles_count,
                'orders_count': orders_count,
                'clear_existing': clear_existing
            }
        )
    
    return jsonify(result)


@test_data_bp.route('/generate/nodes', methods=['POST'])
@jwt_required()
@rate_limit(**RateLimits.API)
def generate_nodes():
    """只生成节点数据"""
    data = request.get_json() or {}
    
    count = min(max(data.get('count', 20), 1), 100)
    clear_existing = data.get('clear_existing', False)
    
    nodes = test_data_generator.generate_nodes(count=count, clear_existing=clear_existing)
    
    audit_service.log(
        action=AuditAction.CREATE,
        module=AuditModule.NODE,
        description=f'生成 {len(nodes)} 个测试节点',
        extra_data={'count': count}
    )
    
    return jsonify({
        'success': True,
        'count': len(nodes),
        'nodes': [{'id': n.id, 'name': n.name, 'type': n.type} for n in nodes]
    })


@test_data_bp.route('/generate/vehicles', methods=['POST'])
@jwt_required()
@rate_limit(**RateLimits.API)
def generate_vehicles():
    """只生成车辆数据"""
    data = request.get_json() or {}
    
    count = min(max(data.get('count', 15), 1), 50)
    clear_existing = data.get('clear_existing', False)
    
    vehicles = test_data_generator.generate_vehicles(count=count, clear_existing=clear_existing)
    
    audit_service.log(
        action=AuditAction.CREATE,
        module=AuditModule.VEHICLE,
        description=f'生成 {len(vehicles)} 辆测试车辆',
        extra_data={'count': count}
    )
    
    return jsonify({
        'success': True,
        'count': len(vehicles),
        'vehicles': [{'id': v.id, 'plate_number': v.plate_number, 'status': v.status} for v in vehicles]
    })


@test_data_bp.route('/generate/orders', methods=['POST'])
@jwt_required()
@rate_limit(**RateLimits.API)
def generate_orders():
    """只生成订单数据"""
    data = request.get_json() or {}
    
    count = min(max(data.get('count', 50), 1), 200)
    clear_existing = data.get('clear_existing', False)
    
    try:
        orders = test_data_generator.generate_orders(count=count, clear_existing=clear_existing)
        
        audit_service.log(
            action=AuditAction.CREATE,
            module=AuditModule.ORDER,
            description=f'生成 {len(orders)} 个测试订单',
            extra_data={'count': count}
        )
        
        return jsonify({
            'success': True,
            'count': len(orders),
            'orders': [{'id': o.id, 'order_number': o.order_number, 'status': o.status} for o in orders]
        })
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400


@test_data_bp.route('/generate/routes', methods=['POST'])
@jwt_required()
@rate_limit(**RateLimits.API)
def generate_routes():
    """只生成路线数据"""
    data = request.get_json() or {}
    
    count = min(max(data.get('count', 30), 1), 100)
    clear_existing = data.get('clear_existing', False)
    
    try:
        routes = test_data_generator.generate_routes(count=count, clear_existing=clear_existing)
        
        audit_service.log(
            action=AuditAction.CREATE,
            module=AuditModule.SYSTEM,
            description=f'生成 {len(routes)} 条测试路线',
            extra_data={'count': count}
        )
        
        return jsonify({
            'success': True,
            'count': len(routes),
            'routes': [{'id': r.id, 'name': r.name, 'distance': r.distance} for r in routes]
        })
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400


@test_data_bp.route('/status', methods=['GET'])
@jwt_required()
def get_status():
    """获取当前数据统计"""
    from app.models import Node, Vehicle, Order, Route
    
    return jsonify({
        'nodes': Node.query.count(),
        'vehicles': Vehicle.query.count(),
        'orders': Order.query.count(),
        'routes': Route.query.count(),
        'orders_by_status': {
            'pending': Order.query.filter_by(status='pending').count(),
            'in_transit': Order.query.filter_by(status='in_transit').count(),
            'delivered': Order.query.filter_by(status='delivered').count(),
            'cancelled': Order.query.filter_by(status='cancelled').count(),
        },
        'vehicles_by_status': {
            'available': Vehicle.query.filter_by(status='available').count(),
            'in_use': Vehicle.query.filter_by(status='in_use').count(),
            'maintenance': Vehicle.query.filter_by(status='maintenance').count(),
            'offline': Vehicle.query.filter_by(status='offline').count(),
        }
    })