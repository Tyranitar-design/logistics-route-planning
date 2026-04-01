#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
高德地图 API 路由
支持：地理编码、路线规划、实时路况、多路线对比
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.services.amap_service import get_amap_service
from app.models import db, Node
import logging

logger = logging.getLogger(__name__)

amap_bp = Blueprint('amap', __name__)


@amap_bp.route('/geocode', methods=['GET'])
@jwt_required()
def geocode():
    """
    地理编码 - 地址转坐标
    
    Query params:
        address: 地址字符串
        city: 城市名称（可选）
    """
    try:
        address = request.args.get('address')
        city = request.args.get('city')
        
        if not address:
            return jsonify({'success': False, 'error': '请提供地址参数'}), 400
        
        service = get_amap_service()
        result = service.geocode(address, city)
        
        if result.success:
            return jsonify({
                'success': True,
                'data': {
                    'longitude': result.longitude,
                    'latitude': result.latitude,
                    'formatted_address': result.formatted_address,
                    'province': result.province,
                    'city': result.city,
                    'district': result.district
                }
            })
        else:
            return jsonify({'success': False, 'error': result.error}), 400
    
    except Exception as e:
        logger.error(f"地理编码失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@amap_bp.route('/regeocode', methods=['GET'])
@jwt_required()
def regeocode():
    """
    逆地理编码 - 坐标转地址
    
    Query params:
        longitude: 经度
        latitude: 纬度
    """
    try:
        longitude = request.args.get('longitude', type=float)
        latitude = request.args.get('latitude', type=float)
        
        if longitude is None or latitude is None:
            return jsonify({'success': False, 'error': '请提供经纬度参数'}), 400
        
        service = get_amap_service()
        result = service.regeocode(longitude, latitude)
        
        if result.success:
            return jsonify({
                'success': True,
                'data': {
                    'longitude': result.longitude,
                    'latitude': result.latitude,
                    'formatted_address': result.formatted_address,
                    'province': result.province,
                    'city': result.city,
                    'district': result.district
                }
            })
        else:
            return jsonify({'success': False, 'error': result.error}), 400
    
    except Exception as e:
        logger.error(f"逆地理编码失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@amap_bp.route('/route/driving', methods=['POST'])
@jwt_required()
def driving_route():
    """
    驾车路线规划
    
    Body:
        origin: 起点 (经度, 纬度) 或节点ID
        destination: 终点 (经度, 纬度) 或节点ID
        waypoints: 途经点列表（可选）
        strategy: 路线策略（0-10，默认0速度优先）
        show_traffic: 是否返回路况（默认true）
    """
    try:
        data = request.get_json()
        
        origin = data.get('origin')
        destination = data.get('destination')
        waypoints = data.get('waypoints', [])
        strategy = data.get('strategy', 0)
        show_traffic = data.get('show_traffic', True)
        
        if not origin or not destination:
            return jsonify({'success': False, 'error': '请提供起点和终点'}), 400
        
        # 支持节点ID或坐标
        def get_coordinates(point):
            if isinstance(point, int):
                # 是节点ID
                node = Node.query.get(point)
                if node and node.longitude and node.latitude:
                    return (node.longitude, node.latitude)
                return None
            elif isinstance(point, dict):
                return (point.get('longitude'), point.get('latitude'))
            elif isinstance(point, (list, tuple)) and len(point) >= 2:
                return (float(point[0]), float(point[1]))
            return None
        
        origin_coords = get_coordinates(origin)
        dest_coords = get_coordinates(destination)
        
        if not origin_coords:
            return jsonify({'success': False, 'error': '无效的起点'}), 400
        if not dest_coords:
            return jsonify({'success': False, 'error': '无效的终点'}), 400
        
        # 处理途经点
        waypoint_coords = []
        for wp in waypoints:
            coords = get_coordinates(wp)
            if coords:
                waypoint_coords.append(coords)
        
        service = get_amap_service()
        result = service.driving_route(
            origin_coords,
            dest_coords,
            waypoint_coords if waypoint_coords else None,
            strategy,
            show_traffic
        )
        
        if result.success:
            return jsonify({
                'success': True,
                'data': {
                    'distance': result.distance,
                    'duration': result.duration,
                    'tolls': result.tolls,
                    'toll_distance': result.toll_distance,
                    'distance_km': round(result.distance / 1000, 2),
                    'duration_minutes': round(result.duration / 60, 1),
                    'steps': result.steps,
                    'polyline': result.polyline,
                    'traffic_info': result.traffic_info
                }
            })
        else:
            return jsonify({'success': False, 'error': result.error}), 400
    
    except Exception as e:
        logger.error(f"路线规划失败: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@amap_bp.route('/route/multi', methods=['POST'])
@jwt_required()
def multi_route():
    """
    多路线规划（返回多条路线供选择）
    
    Body:
        origin: 起点
        destination: 终点
    """
    try:
        data = request.get_json()
        
        origin = data.get('origin')
        destination = data.get('destination')
        
        if not origin or not destination:
            return jsonify({'success': False, 'error': '请提供起点和终点'}), 400
        
        # 支持节点ID或坐标
        def get_coordinates(point):
            if isinstance(point, int):
                node = Node.query.get(point)
                if node and node.longitude and node.latitude:
                    return (node.longitude, node.latitude)
                return None
            elif isinstance(point, dict):
                return (point.get('longitude'), point.get('latitude'))
            elif isinstance(point, (list, tuple)) and len(point) >= 2:
                return (float(point[0]), float(point[1]))
            return None
        
        origin_coords = get_coordinates(origin)
        dest_coords = get_coordinates(destination)
        
        if not origin_coords or not dest_coords:
            return jsonify({'success': False, 'error': '无效的起点或终点'}), 400
        
        service = get_amap_service()
        result = service.multi_route(origin_coords, dest_coords)
        
        return jsonify(result)
    
    except Exception as e:
        logger.error(f"多路线规划失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@amap_bp.route('/traffic/around', methods=['GET'])
@jwt_required()
def traffic_around():
    """
    获取周边路况
    
    Query params:
        longitude: 经度
        latitude: 纬度
        radius: 搜索半径（米，默认1000）
    """
    try:
        longitude = request.args.get('longitude', type=float)
        latitude = request.args.get('latitude', type=float)
        radius = request.args.get('radius', 1000, type=int)
        
        if longitude is None or latitude is None:
            return jsonify({
                'success': True,
                'data': {
                    'status': None,
                    'evaluation': '请提供经纬度参数',
                    'roads': [],
                    'available': False
                }
            })
        
        service = get_amap_service()
        result = service.traffic_around((longitude, latitude), radius)
        
        if result.success:
            return jsonify({
                'success': True,
                'data': {
                    'status': result.status,
                    'evaluation': result.evaluation,
                    'roads': result.roads,
                    'available': True
                }
            })
        else:
            # 路况服务不可用时返回友好提示
            return jsonify({
                'success': True,
                'data': {
                    'status': None,
                    'evaluation': '路况服务暂不可用',
                    'roads': [],
                    'available': False
                }
            })
    
    except Exception as e:
        logger.error(f"路况查询失败: {e}")
        return jsonify({
            'success': True,
            'data': {
                'status': None,
                'evaluation': '路况查询失败',
                'roads': [],
                'available': False
            }
        })


@amap_bp.route('/traffic/node/<int:node_id>', methods=['GET'])
@jwt_required()
def traffic_at_node(node_id):
    """
    获取节点周边的路况
    
    Args:
        node_id: 节点ID
    """
    try:
        node = Node.query.get_or_404(node_id)
        
        if not node.longitude or not node.latitude:
            return jsonify({
                'success': True,
                'data': {
                    'node_id': node_id,
                    'node_name': node.name,
                    'status': None,
                    'evaluation': '该节点没有坐标信息',
                    'roads': [],
                    'available': False
                }
            })
        
        service = get_amap_service()
        result = service.traffic_around((node.longitude, node.latitude), 2000)
        
        if result.success:
            return jsonify({
                'success': True,
                'data': {
                    'node_id': node_id,
                    'node_name': node.name,
                    'status': result.status,
                    'evaluation': result.evaluation,
                    'roads': result.roads,
                    'available': True
                }
            })
        else:
            # 路况服务不可用时返回友好提示，而不是错误
            return jsonify({
                'success': True,
                'data': {
                    'node_id': node_id,
                    'node_name': node.name,
                    'status': None,
                    'evaluation': '路况服务暂不可用（需要在高德控制台开通）',
                    'roads': [],
                    'available': False
                }
            })
    
    except Exception as e:
        logger.error(f"节点路况查询失败: {e}")
        return jsonify({
            'success': True,
            'data': {
                'node_id': node_id,
                'node_name': None,
                'status': None,
                'evaluation': '路况查询失败',
                'roads': [],
                'available': False
            }
        })


@amap_bp.route('/distance-matrix', methods=['POST'])
@jwt_required()
def distance_matrix():
    """
    批量距离计算
    
    Body:
        origins: 起点列表（节点ID或坐标）
        destinations: 终点列表（节点ID或坐标）
        strategy: 路线策略（默认0）
    """
    try:
        data = request.get_json()
        
        origins = data.get('origins', [])
        destinations = data.get('destinations', [])
        strategy = data.get('strategy', 0)
        
        if not origins or not destinations:
            return jsonify({'success': False, 'error': '请提供起点和终点列表'}), 400
        
        # 支持节点ID或坐标
        def get_coordinates(point):
            if isinstance(point, int):
                node = Node.query.get(point)
                if node and node.longitude and node.latitude:
                    return (node.longitude, node.latitude)
                return None
            elif isinstance(point, dict):
                return (point.get('longitude'), point.get('latitude'))
            elif isinstance(point, (list, tuple)) and len(point) >= 2:
                return (float(point[0]), float(point[1]))
            return None
        
        origin_coords = []
        for o in origins:
            coords = get_coordinates(o)
            if coords:
                origin_coords.append(coords)
        
        dest_coords = []
        for d in destinations:
            coords = get_coordinates(d)
            if coords:
                dest_coords.append(coords)
        
        if not origin_coords or not dest_coords:
            return jsonify({'success': False, 'error': '无效的起点或终点'}), 400
        
        service = get_amap_service()
        result = service.distance_matrix(origin_coords, dest_coords, strategy)
        
        return jsonify(result)
    
    except Exception as e:
        logger.error(f"距离矩阵计算失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@amap_bp.route('/route/compare', methods=['POST'])
@jwt_required()
def compare_routes():
    """
    对比本地算法和高德地图的路线规划
    
    Body:
        origin_id: 起点节点ID
        destination_id: 终点节点ID
    """
    try:
        data = request.get_json()
        
        origin_id = data.get('origin_id')
        destination_id = data.get('destination_id')
        
        if not origin_id or not destination_id:
            return jsonify({'success': False, 'error': '请提供起点和终点节点ID'}), 400
        
        # 获取节点信息
        origin_node = Node.query.get_or_404(origin_id)
        dest_node = Node.query.get_or_404(destination_id)
        
        if not origin_node.longitude or not origin_node.latitude:
            return jsonify({'success': False, 'error': '起点节点缺少坐标信息'}), 400
        if not dest_node.longitude or not dest_node.latitude:
            return jsonify({'success': False, 'error': '终点节点缺少坐标信息'}), 400
        
        # 高德地图路线规划
        service = get_amap_service()
        amap_result = service.multi_route(
            (origin_node.longitude, origin_node.latitude),
            (dest_node.longitude, dest_node.latitude)
        )
        
        # 本地算法路线规划
        from app.services.path_algorithm import get_path_service
        path_service = get_path_service()
        local_result = path_service.dijkstra(origin_id, destination_id, 'distance')
        
        # 整合结果
        comparison = {
            'success': True,
            'origin': origin_node.to_dict(),
            'destination': dest_node.to_dict(),
            'amap': amap_result if amap_result.get('success') else None,
            'local': {
                'success': local_result.success,
                'path': local_result.path,
                'distance_km': local_result.total_distance,
                'duration_minutes': local_result.total_time * 60,  # 小时转分钟
                'cost': local_result.total_cost,
                'algorithm': local_result.algorithm,
                'computation_time': local_result.computation_time
            } if local_result.success else None
        }
        
        return jsonify(comparison)
    
    except Exception as e:
        logger.error(f"路线对比失败: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500
