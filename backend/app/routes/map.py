#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
地图相关路由
"""

from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required
from app.models import db, Node, Route
import requests

map_bp = Blueprint('map', __name__)


# 节点类型映射
TYPE_TEXT_MAP = {
    'warehouse': '仓库',
    'station': '配送站',
    'transfer': '中转站',
    'customer': '客户点'
}


@map_bp.route('/nodes', methods=['GET'])
@jwt_required()
def get_map_nodes():
    """获取地图节点数据（GeoJSON格式）"""
    try:
        nodes = Node.query.filter_by(status='active').all()
        
        features = []
        for node in nodes:
            if node.longitude and node.latitude:
                features.append({
                    'type': 'Feature',
                    'geometry': {
                        'type': 'Point',
                        'coordinates': [node.longitude, node.latitude]
                    },
                    'properties': {
                        'id': node.id,
                        'name': node.name,
                        'type': node.type,
                        'typeText': TYPE_TEXT_MAP.get(node.type, node.type),
                        'address': node.address,
                        'contact': node.contact_person,
                        'phone': node.contact_phone
                    }
                })
        
        return jsonify({
            'type': 'FeatureCollection',
            'features': features
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@map_bp.route('/routes', methods=['GET'])
@jwt_required()
def get_map_routes():
    """获取地图路线数据（GeoJSON格式）"""
    try:
        routes = Route.query.filter_by(status='active').all()
        
        features = []
        for route in routes:
            if route.start_node and route.end_node:
                # 使用起点和终点的坐标
                start_coords = [route.start_node.longitude, route.start_node.latitude]
                end_coords = [route.end_node.longitude, route.end_node.latitude]
                
                if start_coords and end_coords:
                    features.append({
                        'type': 'Feature',
                        'geometry': {
                            'type': 'LineString',
                            'coordinates': [start_coords, end_coords]
                        },
                        'properties': {
                            'id': route.id,
                            'name': route.name,
                            'distance': route.distance,
                            'duration': route.duration,
                            'cost': getattr(route, 'total_cost', None) or route.distance * 2 if route.distance else 0
                        }
                    })
        
        return jsonify({
            'type': 'FeatureCollection',
            'features': features
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@map_bp.route('/geocode', methods=['GET'])
@jwt_required()
def geocode():
    """地址转坐标"""
    try:
        address = request.args.get('address')
        if not address:
            return jsonify({'error': '地址不能为空'}), 400
        
        key = current_app.config.get('AMAP_WEB_KEY')
        if not key:
            return jsonify({'error': '地图服务未配置'}), 500
        
        url = 'https://restapi.amap.com/v3/geocode/geo'
        params = {
            'key': key,
            'address': address
        }
        
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        if data.get('status') == '1' and data.get('geocodes'):
            geocode = data['geocodes'][0]
            location = geocode.get('location', '').split(',')
            return jsonify({
                'longitude': float(location[0]) if len(location) > 0 else None,
                'latitude': float(location[1]) if len(location) > 1 else None,
                'formatted_address': geocode.get('formatted_address'),
                'province': geocode.get('province'),
                'city': geocode.get('city'),
                'district': geocode.get('district')
            })
        else:
            return jsonify({'error': '地址解析失败'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@map_bp.route('/reverse-geocode', methods=['GET'])
@jwt_required()
def reverse_geocode():
    """坐标转地址"""
    try:
        longitude = request.args.get('longitude')
        latitude = request.args.get('latitude')
        
        if not longitude or not latitude:
            return jsonify({'error': '坐标不能为空'}), 400
        
        key = current_app.config.get('AMAP_WEB_KEY')
        if not key:
            return jsonify({'error': '地图服务未配置'}), 500
        
        url = 'https://restapi.amap.com/v3/geocode/regeo'
        params = {
            'key': key,
            'location': f'{longitude},{latitude}'
        }
        
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        if data.get('status') == '1':
            regeocode = data.get('regeocode', {})
            return jsonify({
                'formatted_address': regeocode.get('formatted_address'),
                'province': regeocode.get('addressComponent', {}).get('province'),
                'city': regeocode.get('addressComponent', {}).get('city'),
                'district': regeocode.get('addressComponent', {}).get('district')
            })
        else:
            return jsonify({'error': '逆地址解析失败'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@map_bp.route('/direction', methods=['GET'])
@jwt_required()
def get_direction():
    """路径规划"""
    try:
        origin = request.args.get('origin')  # 格式: longitude,latitude
        destination = request.args.get('destination')
        
        if not origin or not destination:
            return jsonify({'error': '起点和终点不能为空'}), 400
        
        key = current_app.config.get('AMAP_WEB_KEY')
        if not key:
            return jsonify({'error': '地图服务未配置'}), 500
        
        url = 'https://restapi.amap.com/v3/direction/driving'
        params = {
            'key': key,
            'origin': origin,
            'destination': destination
        }
        
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        if data.get('status') == '1':
            route = data.get('route', {})
            path = route.get('paths', [{}])[0] if route.get('paths') else {}
            
            return jsonify({
                'distance': float(path.get('distance', 0)) / 1000,  # 转换为公里
                'duration': float(path.get('duration', 0)) / 60,  # 转换为分钟
                'steps': path.get('steps', [])
            })
        else:
            return jsonify({'error': '路径规划失败'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@map_bp.route('/routes', methods=['GET'])
@jwt_required()
def get_all_routes():
    """获取所有路线（简化版，用于地图展示）"""
    try:
        # 获取所有订单的路线信息
        from app.models import Order
        orders = Order.query.filter(
            Order.pickup_node_id.isnot(None),
            Order.delivery_node_id.isnot(None)
        ).limit(20).all()
        
        routes_data = []
        for order in orders:
            if order.pickup_node and order.delivery_node:
                routes_data.append({
                    'id': order.id,
                    'order_number': order.order_number,
                    'origin': {
                        'id': order.pickup_node.id,
                        'name': order.pickup_node.name,
                        'coordinates': [order.pickup_node.longitude, order.pickup_node.latitude]
                    },
                    'destination': {
                        'id': order.delivery_node.id,
                        'name': order.delivery_node.name,
                        'coordinates': [order.delivery_node.longitude, order.delivery_node.latitude]
                    },
                    'status': order.status
                })
        
        return jsonify({
            'success': True,
            'routes': routes_data
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
