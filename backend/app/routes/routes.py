#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
路线管理路由
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models import db, Route, Node
from app.services.path_algorithm import get_path_service
from app.utils.rate_limiter import rate_limit, RateLimits

routes_bp = Blueprint('routes', __name__)


@routes_bp.route('', methods=['GET'])
@jwt_required()
@rate_limit(**RateLimits.API)
def get_routes():
    """获取路线列表"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        status = request.args.get('status')
        
        query = Route.query
        
        if status:
            query = query.filter_by(status=status)
        
        pagination = query.order_by(Route.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return jsonify({
            'routes': [route.to_dict() for route in pagination.items],
            'total': pagination.total,
            'page': page,
            'per_page': per_page,
            'pages': pagination.pages
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@routes_bp.route('/<int:route_id>', methods=['GET'])
@jwt_required()
def get_route(route_id):
    """获取路线详情"""
    route = Route.query.get_or_404(route_id)
    return jsonify({'route': route.to_dict()})


@routes_bp.route('', methods=['POST'])
@jwt_required()
@rate_limit(max_requests=20, window_seconds=60, key_func=lambda: f"create_route:{get_jwt_identity()}")
def create_route():
    """创建路线"""
    try:
        data = request.get_json()
        
        route = Route(
            name=data['name'],
            origin_id=data.get('origin_id'),
            destination_id=data.get('destination_id'),
            distance=data.get('distance'),
            estimated_time=data.get('estimated_time'),
            fuel_cost=data.get('fuel_cost'),
            toll_cost=data.get('toll_cost'),
            total_cost=data.get('total_cost'),
            status=data.get('status', 'active'),
            notes=data.get('notes')
        )
        
        db.session.add(route)
        db.session.commit()
        
        return jsonify({
            'message': '路线创建成功',
            'route': route.to_dict()
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@routes_bp.route('/<int:route_id>', methods=['PUT'])
@jwt_required()
@rate_limit(max_requests=20, window_seconds=60, key_func=lambda: f"update_route:{get_jwt_identity()}")
def update_route(route_id):
    """更新路线"""
    try:
        route = Route.query.get_or_404(route_id)
        data = request.get_json()
        
        if 'name' in data:
            route.name = data['name']
        if 'origin_id' in data:
            route.origin_id = data['origin_id']
        if 'destination_id' in data:
            route.destination_id = data['destination_id']
        if 'distance' in data:
            route.distance = data['distance']
        if 'estimated_time' in data:
            route.estimated_time = data['estimated_time']
        if 'fuel_cost' in data:
            route.fuel_cost = data['fuel_cost']
        if 'toll_cost' in data:
            route.toll_cost = data['toll_cost']
        if 'total_cost' in data:
            route.total_cost = data['total_cost']
        if 'status' in data:
            route.status = data['status']
        if 'notes' in data:
            route.notes = data['notes']
        
        db.session.commit()
        
        return jsonify({
            'message': '路线更新成功',
            'route': route.to_dict()
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@routes_bp.route('/<int:route_id>', methods=['DELETE'])
@jwt_required()
@rate_limit(max_requests=10, window_seconds=60, key_func=lambda: f"delete_route:{get_jwt_identity()}")
def delete_route(route_id):
    """删除路线"""
    try:
        route = Route.query.get_or_404(route_id)
        
        db.session.delete(route)
        db.session.commit()
        
        return jsonify({'message': '路线删除成功'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@routes_bp.route('/recommend', methods=['POST'])
@jwt_required()
@rate_limit(max_requests=30, window_seconds=60, key_func=lambda: f"recommend_route:{get_jwt_identity()}")
def recommend_route():
    """路径规划推荐 - 使用高级算法（Dijkstra/A*）"""
    try:
        data = request.get_json()
        
        # 兼容不同的参数名
        origin_id = data.get('origin_id') or data.get('start_node_id')
        destination_id = data.get('destination_id') or data.get('end_node_id')
        optimize_by = data.get('optimize_by', 'distance')
        algorithm = data.get('algorithm', 'dijkstra')  # dijkstra 或 astar
        
        if not origin_id or not destination_id:
            return jsonify({'error': '请提供起点和终点', 'success': False}), 400
        
        # 获取路径服务
        service = get_path_service()
        
        # 选择算法
        if algorithm.lower() in ['astar', 'a*']:
            result = service.a_star(int(origin_id), int(destination_id), optimize_by)
        else:
            result = service.dijkstra(int(origin_id), int(destination_id), optimize_by)
        
        if not result.success:
            return jsonify({
                'success': False,
                'error': result.error
            }), 400
        
        return jsonify({
            'success': True,
            'path': result.path,
            'total_distance': result.total_distance,
            'total_time': result.total_time,
            'total_cost': result.total_cost,
            'algorithm': result.algorithm,
            'optimize_by': result.optimize_by,
            'visited_nodes': result.visited_nodes,
            'computation_time': result.computation_time
        })
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e), 'success': False}), 500


@routes_bp.route('/recommend/multi-objective', methods=['POST'])
@jwt_required()
def recommend_multi_objective():
    """多目标优化路径规划"""
    try:
        data = request.get_json()
        
        origin_id = data.get('origin_id') or data.get('start_node_id')
        destination_id = data.get('destination_id') or data.get('end_node_id')
        weights = data.get('weights', {'distance': 0.4, 'time': 0.3, 'cost': 0.3})
        
        if not origin_id or not destination_id:
            return jsonify({'error': '请提供起点和终点', 'success': False}), 400
        
        service = get_path_service()
        results = service.multi_objective_optimize(int(origin_id), int(destination_id), weights)
        
        return jsonify({
            'success': True,
            'results': results
        })
    
    except Exception as e:
        return jsonify({'error': str(e), 'success': False}), 500


@routes_bp.route('/recommend/compare', methods=['POST'])
@jwt_required()
def compare_algorithms():
    """对比不同算法的结果"""
    try:
        data = request.get_json()
        
        origin_id = data.get('origin_id') or data.get('start_node_id')
        destination_id = data.get('destination_id') or data.get('end_node_id')
        
        if not origin_id or not destination_id:
            return jsonify({'error': '请提供起点和终点', 'success': False}), 400
        
        service = get_path_service()
        
        # 对比两种算法
        dijkstra_result = service.dijkstra(int(origin_id), int(destination_id), 'distance')
        astar_result = service.a_star(int(origin_id), int(destination_id), 'distance')
        
        return jsonify({
            'success': True,
            'comparison': {
                'dijkstra': {
                    'path': dijkstra_result.path,
                    'distance': dijkstra_result.total_distance,
                    'time': dijkstra_result.total_time,
                    'cost': dijkstra_result.total_cost,
                    'visited_nodes': dijkstra_result.visited_nodes,
                    'computation_time': dijkstra_result.computation_time
                },
                'astar': {
                    'path': astar_result.path,
                    'distance': astar_result.total_distance,
                    'time': astar_result.total_time,
                    'cost': astar_result.total_cost,
                    'visited_nodes': astar_result.visited_nodes,
                    'computation_time': astar_result.computation_time
                }
            }
        })
    
    except Exception as e:
        return jsonify({'error': str(e), 'success': False}), 500


@routes_bp.route('/calculate', methods=['POST'])
@jwt_required()
def calculate_route():
    """计算路径"""
    try:
        data = request.get_json()
        # 简化实现，调用 recommend_route
        return recommend_route()
    except Exception as e:
        return jsonify({'error': str(e)}), 500
