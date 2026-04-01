#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
运输轨迹 API 路由
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.services.tracking_service import get_tracking_service
import logging

logger = logging.getLogger(__name__)

tracking_bp = Blueprint('tracking', __name__)


@tracking_bp.route('/route/<int:origin_id>/<int:destination_id>', methods=['GET'])
@jwt_required()
def get_route_polyline(origin_id, destination_id):
    """
    获取路线轨迹坐标点
    
    Args:
        origin_id: 起点节点ID
        destination_id: 终点节点ID
    """
    try:
        service = get_tracking_service()
        result = service.get_route_polyline(origin_id, destination_id)
        
        if result['success']:
            return jsonify({
                'success': True,
                'data': result
            })
        else:
            return jsonify({'success': False, 'error': result['error']}), 400
    
    except Exception as e:
        logger.error(f"获取路线轨迹失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@tracking_bp.route('/simulate/<int:order_id>', methods=['GET'])
@jwt_required()
def simulate_tracking(order_id):
    """
    获取订单运输轨迹模拟数据
    
    Query params:
        speed: 模拟速度倍数（默认1.0）
    """
    try:
        speed = request.args.get('speed', 1.0, type=float)
        
        service = get_tracking_service()
        result = service.simulate_tracking(order_id, speed)
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 400
    
    except Exception as e:
        logger.error(f"获取模拟数据失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@tracking_bp.route('/position', methods=['POST'])
@jwt_required()
def calculate_position():
    """
    计算指定进度下的位置
    
    Body:
        polyline: 路线坐标点列表
        progress: 进度 (0-100)
    """
    try:
        data = request.get_json()
        polyline = data.get('polyline', [])
        progress = data.get('progress', 0)
        
        if not polyline or len(polyline) < 2:
            return jsonify({'success': False, 'error': '无效的路线数据'}), 400
        
        service = get_tracking_service()
        position = service.calculate_position(polyline, progress)
        
        if position:
            return jsonify({
                'success': True,
                'data': {
                    'longitude': position.longitude,
                    'latitude': position.latitude,
                    'distance_from_start': round(position.distance_from_start, 2),
                    'progress': round(position.progress, 1)
                }
            })
        else:
            return jsonify({'success': False, 'error': '无法计算位置'}), 400
    
    except Exception as e:
        logger.error(f"计算位置失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@tracking_bp.route('/eta/<int:order_id>', methods=['GET'])
@jwt_required()
def estimate_arrival(order_id):
    """
    估算订单到达时间
    
    Query params:
        progress: 当前进度（默认0）
    """
    try:
        progress = request.args.get('progress', 0, type=float)
        
        service = get_tracking_service()
        result = service.estimate_arrival(order_id, progress)
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 400
    
    except Exception as e:
        logger.error(f"估算到达时间失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@tracking_bp.route('/history/<int:order_id>', methods=['GET'])
@jwt_required()
def get_tracking_history(order_id):
    """获取订单运输历史轨迹"""
    try:
        service = get_tracking_service()
        result = service.get_tracking_history(order_id)
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 400
    
    except Exception as e:
        logger.error(f"获取历史轨迹失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
