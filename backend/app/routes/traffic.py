#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
实时路况路由
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.services.traffic_service import get_traffic_service

traffic_bp = Blueprint('traffic', __name__)


@traffic_bp.route('/road', methods=['GET'])
@jwt_required()
def get_road_traffic():
    """
    获取道路实时路况
    
    Query params:
        city: 城市名称
        road_name: 道路名称（可选）
    """
    try:
        city = request.args.get('city', '北京')
        road_name = request.args.get('road_name')
        
        service = get_traffic_service()
        result = service.get_road_traffic(city, road_name)
        
        return jsonify(result)
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@traffic_bp.route('/rectangle', methods=['GET'])
@jwt_required()
def get_rectangle_traffic():
    """
    获取区域路况
    
    Query params:
        location: 左下角经纬度,右上角经纬度 (如: "116.35,39.85,116.45,39.95")
    """
    try:
        location = request.args.get('location')
        
        if not location:
            return jsonify({
                'success': False,
                'error': '请提供区域范围参数'
            }), 400
        
        service = get_traffic_service()
        result = service.get_rectangle_traffic(location)
        
        return jsonify(result)
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@traffic_bp.route('/route', methods=['POST'])
@jwt_required()
def check_route_traffic():
    """
    检查路线路况
    
    Body:
        origin: 起点 (lng,lat)
        destination: 终点 (lng,lat)
        waypoints: 途经点（可选）
    """
    try:
        data = request.get_json()
        
        origin = data.get('origin')
        destination = data.get('destination')
        waypoints = data.get('waypoints')
        
        if not origin or not destination:
            return jsonify({
                'success': False,
                'error': '请提供起点和终点'
            }), 400
        
        service = get_traffic_service()
        result = service.check_route_traffic(origin, destination, waypoints)
        
        return jsonify(result)
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@traffic_bp.route('/analyze', methods=['POST'])
@jwt_required()
def analyze_and_avoid():
    """
    分析路况并自动规避拥堵
    
    Body:
        origin: 起点 (lng,lat)
        destination: 终点 (lng,lat)
        waypoints: 途经点（可选）
        threshold: 拥堵阈值（1-5，默认4）
    """
    try:
        data = request.get_json()
        
        origin = data.get('origin')
        destination = data.get('destination')
        waypoints = data.get('waypoints')
        threshold = data.get('threshold', 4)
        
        if not origin or not destination:
            return jsonify({
                'success': False,
                'error': '请提供起点和终点'
            }), 400
        
        service = get_traffic_service()
        result = service.analyze_traffic_and_avoid(origin, destination, waypoints, threshold)
        
        return jsonify(result)
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@traffic_bp.route('/monitor', methods=['POST'])
@jwt_required()
def monitor_routes():
    """
    批量监控多条路线的路况
    
    Body:
        routes: 路线列表 [{origin, destination}, ...]
    """
    try:
        data = request.get_json()
        routes = data.get('routes', [])
        
        if not routes:
            return jsonify({
                'success': False,
                'error': '请提供路线列表'
            }), 400
        
        service = get_traffic_service()
        results = []
        
        for route in routes[:10]:  # 最多监控10条路线
            origin = route.get('origin')
            destination = route.get('destination')
            
            if origin and destination:
                result = service.analyze_traffic_and_avoid(origin, destination)
                results.append({
                    'origin': origin,
                    'destination': destination,
                    **result
                })
        
        return jsonify({
            'success': True,
            'results': results,
            'total': len(results)
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
