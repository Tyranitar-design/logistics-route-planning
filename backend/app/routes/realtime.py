#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
实时数据 API 路由
"""

from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required
from app.services.data_generator import get_data_generator

realtime_bp = Blueprint('realtime', __name__)


@realtime_bp.route('/vehicle-locations', methods=['GET'])
@jwt_required()
def get_vehicle_locations():
    """获取车辆实时位置"""
    generator = get_data_generator()
    locations = generator.get_vehicle_locations()
    
    return jsonify({
        'success': True,
        'data': {
            'locations': locations,
            'count': len(locations)
        }
    })


@realtime_bp.route('/start-generator', methods=['POST'])
@jwt_required()
def start_generator():
    """启动数据生成器"""
    generator = get_data_generator()
    generator.start()
    
    return jsonify({
        'success': True,
        'message': '数据生成器已启动'
    })


@realtime_bp.route('/stop-generator', methods=['POST'])
@jwt_required()
def stop_generator():
    """停止数据生成器"""
    generator = get_data_generator()
    generator.stop()
    
    return jsonify({
        'success': True,
        'message': '数据生成器已停止'
    })


@realtime_bp.route('/generator-status', methods=['GET'])
@jwt_required()
def generator_status():
    """获取数据生成器状态"""
    generator = get_data_generator()
    
    return jsonify({
        'success': True,
        'data': {
            'running': generator._running,
            'order_interval': generator.order_interval,
            'status_interval': generator.status_interval,
            'location_interval': generator.location_interval,
            'active_vehicles': len(generator._vehicle_locations)
        }
    })


@realtime_bp.route('/config', methods=['POST'])
@jwt_required()
def config_generator():
    """配置数据生成器"""
    from flask import request
    
    generator = get_data_generator()
    data = request.get_json()
    
    if 'order_interval' in data:
        generator.order_interval = max(10, int(data['order_interval']))
    if 'status_interval' in data:
        generator.status_interval = max(30, int(data['status_interval']))
    if 'location_interval' in data:
        generator.location_interval = max(1, int(data['location_interval']))
    
    return jsonify({
        'success': True,
        'message': '配置已更新',
        'config': {
            'order_interval': generator.order_interval,
            'status_interval': generator.status_interval,
            'location_interval': generator.location_interval
        }
    })
