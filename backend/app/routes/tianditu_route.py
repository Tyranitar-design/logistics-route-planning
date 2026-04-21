#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
天地图 API 路由
提供路径规划、地名搜索等接口
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.services.tianditu_service import get_tianditu_service
from app.models import Node
from app.utils.rate_limiter import rate_limit, RateLimits
import logging

logger = logging.getLogger(__name__)

tianditu_bp = Blueprint('tianditu', __name__)


@tianditu_bp.route('/drive', methods=['POST'])
@jwt_required()
@rate_limit(max_requests=100, window_seconds=60, key_func=lambda: f"tianditu_drive:{get_jwt_identity()}")
def driving_route():
    """
    天地图驾车路径规划
    
    Body:
        origin_id: 起点节点ID（二选一）
        origin: 起点坐标 [lng, lat]（二选一）
        destination_id: 终点节点ID（二选一）
        destination: 终点坐标 [lng, lat]（二选一）
        strategy: 路线策略（可选）
            '0' - 推荐路线（默认）
            '1' - 最短距离
            '2' - 最短时间
            '3' - 避开高速
    
    Returns:
        {
            "success": true,
            "source": "tianditu",
            "distance_km": 13.45,
            "duration_minutes": 13.6,
            "polyline": [[lng, lat], ...],
            "steps": [...],
            "coordinates_count": 178
        }
    """
    try:
        data = request.get_json() or {}
        tianditu_service = get_tianditu_service()
        
        # 获取起点
        origin = None
        if data.get('origin_id'):
            node = Node.query.get(data['origin_id'])
            if node and node.longitude and node.latitude:
                origin = (node.longitude, node.latitude)
        elif data.get('origin'):
            origin = tuple(data['origin'])
        
        # 获取终点
        destination = None
        if data.get('destination_id'):
            node = Node.query.get(data['destination_id'])
            if node and node.longitude and node.latitude:
                destination = (node.longitude, node.latitude)
        elif data.get('destination'):
            destination = tuple(data['destination'])
        
        if not origin or not destination:
            return jsonify({
                'success': False,
                'error': '请提供有效的起点和终点'
            }), 400
        
        # 获取策略
        strategy = data.get('strategy', '0')
        
        # 调用天地图服务
        result = tianditu_service.get_route_for_frontend(origin, destination, strategy)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"天地图路径规划失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@tianditu_bp.route('/drive/coords', methods=['POST'])
@jwt_required()
@rate_limit(max_requests=100, window_seconds=60, key_func=lambda: f"tianditu_coords:{get_jwt_identity()}")
def driving_route_by_coords():
    """
    通过坐标进行路径规划（简化接口）
    
    Body:
        origin_lng: 起点经度
        origin_lat: 起点纬度
        dest_lng: 终点经度
        dest_lat: 终点纬度
        strategy: 路线策略（可选）
    
    Returns:
        路径规划结果
    """
    try:
        data = request.get_json() or {}
        
        origin_lng = data.get('origin_lng')
        origin_lat = data.get('origin_lat')
        dest_lng = data.get('dest_lng')
        dest_lat = data.get('dest_lat')
        
        if not all([origin_lng, origin_lat, dest_lng, dest_lat]):
            return jsonify({
                'success': False,
                'error': '请提供完整的坐标信息'
            }), 400
        
        tianditu_service = get_tianditu_service()
        strategy = data.get('strategy', '0')
        
        result = tianditu_service.get_route_for_frontend(
            (float(origin_lng), float(origin_lat)),
            (float(dest_lng), float(dest_lat)),
            strategy
        )
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"天地图坐标路径规划失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@tianditu_bp.route('/search', methods=['GET'])
@jwt_required()
@rate_limit(max_requests=50, window_seconds=60, key_func=lambda: f"tianditu_search:{get_jwt_identity()}")
def search_poi():
    """
    地名搜索
    
    Query Params:
        keywords: 搜索关键词
        level: 地图级别（可选，1-18，默认12）
    
    Returns:
        搜索结果列表
    """
    try:
        keywords = request.args.get('keywords')
        level = request.args.get('level', 12, type=int)
        
        if not keywords:
            return jsonify({
                'success': False,
                'error': '请提供搜索关键词'
            }), 400
        
        tianditu_service = get_tianditu_service()
        result = tianditu_service.search_poi(keywords, level)
        
        return jsonify({
            'success': result.success,
            'items': result.items,
            'total': result.total,
            'error': result.error
        })
        
    except Exception as e:
        logger.error(f"地名搜索失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@tianditu_bp.route('/geocode', methods=['GET'])
@jwt_required()
def geocode():
    """
    地理编码 - 地址转坐标
    
    Query Params:
        address: 地址字符串
        city: 城市名称（可选）
    
    Returns:
        {
            "success": true,
            "longitude": 116.39129,
            "latitude": 39.90709,
            "formatted_address": "..."
        }
    """
    try:
        address = request.args.get('address')
        city = request.args.get('city')
        
        if not address:
            return jsonify({
                'success': False,
                'error': '请提供地址'
            }), 400
        
        tianditu_service = get_tianditu_service()
        result = tianditu_service.geocode(address, city)
        
        return jsonify({
            'success': result.success,
            'longitude': result.longitude,
            'latitude': result.latitude,
            'formatted_address': result.formatted_address,
            'province': result.province,
            'city': result.city,
            'district': result.district,
            'error': result.error
        })
        
    except Exception as e:
        logger.error(f"地理编码失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@tianditu_bp.route('/distance-matrix', methods=['POST'])
@jwt_required()
@rate_limit(max_requests=30, window_seconds=60, key_func=lambda: f"tianditu_matrix:{get_jwt_identity()}")
def distance_matrix():
    """
    批量距离计算
    
    Body:
        origins: 起点列表 [[lng, lat], ...]
        destinations: 终点列表 [[lng, lat], ...]
        strategy: 路线策略（可选）
    
    Returns:
        {
            "success": true,
            "results": [
                {"origin_id": 0, "dest_id": 0, "distance": 13450, "duration": 819}
            ]
        }
    """
    try:
        data = request.get_json() or {}
        
        origins = data.get('origins', [])
        destinations = data.get('destinations', [])
        strategy = data.get('strategy', '0')
        
        if not origins or not destinations:
            return jsonify({
                'success': False,
                'error': '请提供起点和终点列表'
            }), 400
        
        # 转换为元组列表
        origins_tuples = [tuple(o) for o in origins]
        dests_tuples = [tuple(d) for d in destinations]
        
        tianditu_service = get_tianditu_service()
        result = tianditu_service.distance_matrix(origins_tuples, dests_tuples, strategy)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"距离矩阵计算失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@tianditu_bp.route('/compare/amap', methods=['POST'])
@jwt_required()
@rate_limit(max_requests=20, window_seconds=60, key_func=lambda: f"tianditu_compare:{get_jwt_identity()}")
def compare_with_amap():
    """
    天地图与高德地图路径对比
    
    Body:
        origin_id: 起点节点ID
        destination_id: 终点节点ID
        strategy: 路线策略（可选）
    
    Returns:
        {
            "success": true,
            "tianditu": {...},
            "amap": {...},
            "comparison": {
                "distance_diff": 0.5,
                "duration_diff": 2.3,
                "better_source": "tianditu"
            }
        }
    """
    try:
        from app.services.amap_service import get_amap_service
        
        data = request.get_json() or {}
        
        # 获取节点信息
        origin_id = data.get('origin_id')
        destination_id = data.get('destination_id')
        strategy = data.get('strategy', '0')
        
        if not origin_id or not destination_id:
            return jsonify({
                'success': False,
                'error': '请提供起点和终点节点ID'
            }), 400
        
        origin_node = Node.query.get(origin_id)
        dest_node = Node.query.get(destination_id)
        
        if not origin_node or not dest_node:
            return jsonify({
                'success': False,
                'error': '节点不存在'
            }), 404
        
        origin = (origin_node.longitude, origin_node.latitude)
        destination = (dest_node.longitude, dest_node.latitude)
        
        # 天地图路径规划
        tianditu_service = get_tianditu_service()
        tianditu_result = tianditu_service.get_route_for_frontend(origin, destination, strategy)
        
        # 高德路径规划
        amap_service = get_amap_service()
        amap_result = amap_service.driving_route(origin, destination)
        
        # 对比分析
        comparison = {
            'distance_diff': 0,
            'duration_diff': 0,
            'better_distance': None,
            'better_duration': None
        }
        
        if tianditu_result['success'] and amap_result.success:
            tianditu_dist = tianditu_result['distance_km']
            amap_dist = amap_result.distance / 1000  # 米转公里
            
            tianditu_dur = tianditu_result['duration_minutes']
            amap_dur = amap_result.duration / 60  # 秒转分钟
            
            comparison['distance_diff'] = round(tianditu_dist - amap_dist, 2)
            comparison['duration_diff'] = round(tianditu_dur - amap_dur, 1)
            comparison['better_distance'] = 'tianditu' if tianditu_dist < amap_dist else 'amap'
            comparison['better_duration'] = 'tianditu' if tianditu_dur < amap_dur else 'amap'
        
        return jsonify({
            'success': True,
            'tianditu': tianditu_result,
            'amap': {
                'success': amap_result.success,
                'distance_km': amap_result.distance / 1000 if amap_result.success else None,
                'duration_minutes': amap_result.duration / 60 if amap_result.success else None,
                'polyline': amap_result.polyline if amap_result.success else None,
                'error': amap_result.error
            },
            'comparison': comparison
        })
        
    except Exception as e:
        logger.error(f"路径对比失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@tianditu_bp.route('/keys', methods=['GET'])
@jwt_required()
def get_keys_info():
    """
    获取天地图 Key 配置信息（仅返回是否配置，不返回实际值）
    
    Returns:
        {
            "success": true,
            "browser_key_configured": true,
            "server_key_configured": true
        }
    """
    try:
        tianditu_service = get_tianditu_service()
        
        return jsonify({
            'success': True,
            'browser_key_configured': bool(tianditu_service.browser_key),
            'server_key_configured': bool(tianditu_service.server_key)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
