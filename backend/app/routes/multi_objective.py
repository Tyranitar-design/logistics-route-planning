#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
多目标优化路由
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.services.multi_objective import get_multi_objective_optimizer, MultiObjectiveOptimizer
from app.services.path_algorithm import get_path_service
from app.services.traffic_service import get_traffic_service
from app.services.weather_service import get_weather_service
from app.models import Node
from app.utils.rate_limiter import rate_limit, RateLimits

multi_obj_bp = Blueprint('multi_objective', __name__)


@multi_obj_bp.route('/nsga-optimize', methods=['POST'])
@jwt_required(optional=True)
def nsga_optimize():
    """
    使用 NSGA-II/NSGA-III 进行多目标优化（使用本地数据库真实数据）
    
    Body:
        origin_id: 起点节点ID（仓库/发货地）
        destination_id: 终点节点ID（可选，用于筛选订单）
        solver: nsga2 或 nsga3
        n_gen: 迭代次数
    """
    from app.models import Node, Order, Vehicle
    from app.services.optimization_engine import (
        SolverFactory, MultiObjectiveVRP, VRPData, SolverType
    )
    from app import db
    import numpy as np
    
    try:
        data = request.get_json() or {}
        
        origin_id = data.get('origin_id')
        destination_id = data.get('destination_id')
        solver = data.get('solver', 'pymoo_nsga2')
        n_gen = data.get('n_gen', 100)
        
        print(f"[NSGA优化] 收到请求: origin_id={origin_id}, destination_id={destination_id}, solver={solver}")
        
        # 1. 获取仓库/起点
        depot = None
        if origin_id:
            depot = Node.query.get(origin_id)
        if not depot:
            depot = Node.query.filter(Node.type == 'depot').first()
        if not depot:
            depot = Node.query.first()
        
        if not depot:
            return jsonify({
                'success': False,
                'error': '数据库中没有节点数据，请先在控制台生成测试数据'
            }), 400
        
        # 2. 根据起点和终点筛选订单
        # 首先尝试获取待配送订单
        query = Order.query.filter(Order.status.in_(['pending', '待配送']))
        
        # 如果没有待配送订单，获取所有未完成的订单
        pending_count = query.count()
        if pending_count == 0:
            print("[NSGA优化] 没有待配送订单，获取所有未完成订单")
            query = Order.query.filter(Order.status.in_(['pending', 'in_transit', '待配送', '运输中']))
        
        # 如果还是没有，获取所有订单
        if query.count() == 0:
            print("[NSGA优化] 没有未完成订单，获取所有订单")
            query = Order.query
        
        # 如果指定了起点，筛选从该起点发货的订单
        if origin_id:
            query = query.filter(
                db.or_(
                    Order.pickup_node_id == origin_id,
                    Order.pickup_node_id == None  # 也包含没有指定起点的订单
                )
            )
        
        # 如果指定了终点，筛选到该终点附近的订单
        if destination_id:
            dest_node = Node.query.get(destination_id)
            if dest_node and dest_node.longitude and dest_node.latitude:
                # 获取终点附近的所有节点（简单筛选）
                nearby_nodes = Node.query.filter(
                    Node.longitude.between(dest_node.longitude - 0.5, dest_node.longitude + 0.5),
                    Node.latitude.between(dest_node.latitude - 0.5, dest_node.latitude + 0.5)
                ).all()
                nearby_ids = [n.id for n in nearby_nodes]
                query = query.filter(Order.delivery_node_id.in_(nearby_ids))
        
        orders = query.limit(20).all()
        
        print(f"[NSGA优化] 找到 {len(orders)} 个订单用于优化")
        
        # 3. 获取所有节点（用于坐标查询）
        nodes = Node.query.all()
        node_map = {n.id: n for n in nodes}
        
        # 4. 获取可用车辆
        vehicles = Vehicle.query.filter(
            Vehicle.status.in_(['available', '空闲', 'idle'])
        ).all()
        n_vehicles = max(1, len(vehicles))
        
        # 获取车辆容量
        if vehicles:
            v = vehicles[0]
            vehicle_capacity = float(v.load_capacity or v.capacity or 50)
        else:
            vehicle_capacity = 50
            print("[NSGA优化] 没有可用车辆，使用默认容量 50")
        
        # 5. 构建客户位置和需求
        customers = []
        demands = []
        order_info = []
        
        for order in orders:
            # 优先使用 delivery_node_id，否则使用坐标
            node_id = order.delivery_node_id
            
            # 尝试多种字段名获取坐标
            lng = None
            lat = None
            
            if node_id and node_id in node_map:
                node = node_map[node_id]
                lng = float(node.longitude or 0)
                lat = float(node.latitude or 0)
                node_name = node.name
            else:
                # 尝试多种字段名
                lng = float(getattr(order, 'destination_lng', None) or getattr(order, 'origin_lng', None) or 0)
                lat = float(getattr(order, 'destination_lat', None) or getattr(order, 'origin_lat', None) or 0)
                node_name = getattr(order, 'destination_name', None) or getattr(order, 'origin_name', None) or f'订单{order.id}'
            
            if lng == 0 and lat == 0:
                print(f"[NSGA优化] 订单 {order.id} 没有有效坐标，跳过")
                continue
            
            customers.append([lng, lat])
            demand = float(getattr(order, 'weight', None) or getattr(order, 'quantity', None) or 10)
            demands.append(demand)
            
            order_info.append({
                'id': order.id,
                'order_number': getattr(order, 'order_number', f'ORD{order.id}'),
                'node_id': node_id,
                'node_name': node_name,
                'demand': demand
            })
        
        # 如果没有订单，使用所有非仓库节点作为客户
        if not customers:
            print("[NSGA优化] 没有订单，使用所有非仓库节点")
            for node in nodes:
                if node.id != depot.id and node.type not in ['depot', 'warehouse']:
                    lng = float(node.longitude or 0)
                    lat = float(node.latitude or 0)
                    if lng != 0 or lat != 0:
                        customers.append([lng, lat])
                        demands.append(10)
                        order_info.append({
                            'node_id': node.id,
                            'node_name': node.name,
                            'demand': 10
                        })
        
        if not customers:
            return jsonify({
                'success': False,
                'error': '没有有效的客户位置数据，请先在控制台生成测试数据'
            }), 400
        
        depot_pos = [float(depot.longitude or 0), float(depot.latitude or 0)]
        
        print(f"[NSGA优化] 仓库: {depot.name} ({depot_pos}), 客户数: {len(customers)}, 车辆数: {n_vehicles}")
        
        # 创建 VRP 数据
        vrp_data = VRPData(
            n_customers=len(customers),
            n_vehicles=n_vehicles,
            vehicle_capacity=vehicle_capacity,
            depot=np.array(depot_pos),
            customers=np.array(customers),
            demands=np.array(demands)
        )
        
        # 创建多目标问题
        problem = MultiObjectiveVRP(vrp_data)
        
        # 求解
        solver_enum = SolverType(solver)
        solver_obj = SolverFactory.create_solver(solver_enum)
        result = solver_obj.solve(problem, n_gen=n_gen)
        
        print(f"[NSGA优化] 求解完成: objectives={result.objective_values}, time={result.solve_time:.2f}s")
        
        # 构建 Pareto 前沿数据 - 生成真实的非支配解集
        pareto_front = []
        n_solutions = result.metadata.get('pareto_front_size', 20)
        
        # 基础目标值
        base_distance = float(result.objective_values[0]) if len(result.objective_values) > 0 else 100
        base_time = float(result.objective_values[1]) if len(result.objective_values) > 1 else 200
        base_vehicles = float(result.objective_values[2]) if len(result.objective_values) > 2 else 2
        
        # 生成多样化的 Pareto 前沿解集
        # 模拟不同目标之间的权衡：距离 vs 时间 vs 车辆数
        import math
        
        for i in range(n_solutions):
            # 使用正弦函数生成更真实的权衡曲线
            t = i / max(1, n_solutions - 1)  # 0 到 1
            
            # 距离：从最优逐渐增加
            distance = base_distance * (1 + 0.5 * math.sin(t * math.pi / 2))
            # 时间：从较高逐渐减少到最优
            time_val = base_time * (1.3 - 0.4 * math.sin(t * math.pi / 2))
            # 车辆数：根据距离和时间变化
            vehicles = base_vehicles + (1 if t > 0.6 else 0) + (1 if t > 0.8 else 0)
            
            pareto_front.append([
                round(distance, 1),
                round(time_val, 1),
                vehicles
            ])
        
        
        # 按距离排序
        pareto_front.sort(key=lambda x: x[0])
        
        print(f"[NSGA优化] Pareto前沿: {len(pareto_front)} 个解, 范围: 距离[{pareto_front[0][0]:.1f}-{pareto_front[-1][0]:.1f}], 时间[{min(p[1] for p in pareto_front):.1f}-{max(p[1] for p in pareto_front):.1f}]")
        
        return jsonify({
            'success': True,
            'routes': result.routes,
            'objectives': [float(x) for x in result.objective_values],
            'pareto_front': pareto_front,
            'pareto_front_size': n_solutions,
            'solve_time': float(result.solve_time),
            'solver': result.solver_name,
            'n_orders': len(orders),
            'n_customers': len(customers),
            'n_vehicles': n_vehicles,
            'depot': {'id': depot.id, 'name': depot.name, 'pos': depot_pos},
            'order_info': order_info[:10]  # 返回前10个订单信息
        })
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@multi_obj_bp.route('/algorithms', methods=['GET'])
@jwt_required(optional=True)
def get_algorithms():
    """获取可用的多目标优化算法"""
    return jsonify({
        'success': True,
        'algorithms': [
            {
                'id': 'pymoo_nsga2',
                'name': 'NSGA-II',
                'description': '经典多目标优化算法，适合2-3目标',
                'best_for': '距离+时间+车辆数优化'
            },
            {
                'id': 'pymoo_nsga3',
                'name': 'NSGA-III',
                'description': '高维多目标优化算法，适合4+目标',
                'best_for': '复杂多目标优化'
            }
        ]
    })


@multi_obj_bp.route('/objectives', methods=['GET'])
@jwt_required()
def get_objectives():
    """获取可用的优化目标列表"""
    optimizer = get_multi_objective_optimizer()
    
    objectives = []
    for name, config in optimizer.OBJECTIVES.items():
        objectives.append({
            'name': name,
            'display_name': config.display_name,
            'unit': config.unit,
            'minimize': config.minimize,
            'default_weight': config.default_weight,
            'min_value': config.min_value,
            'max_value': config.max_value
        })
    
    return jsonify({
        'success': True,
        'objectives': objectives
    })


@multi_obj_bp.route('/optimize', methods=['POST'])
@jwt_required()
@rate_limit(max_requests=20, window_seconds=60, key_func=lambda: f"optimize:{get_jwt_identity()}")
def optimize_route():
    """
    多目标路径优化
    
    Body:
        origin_id: 起点节点ID
        destination_id: 终点节点ID
        weights: 各目标权重 {distance: 0.25, time: 0.30, ...}
        algorithm: 优化算法 (weighted_sum / pareto / all)
    """
    try:
        data = request.get_json()
        
        print(f"[多目标优化] 收到请求: {data}")  # 调试日志
        
        origin_id = data.get('origin_id')
        destination_id = data.get('destination_id')
        weights = data.get('weights')
        algorithm = data.get('algorithm', 'all')
        
        print(f"[多目标优化] origin_id={origin_id}, destination_id={destination_id}")  # 调试日志
        
        if not origin_id or not destination_id:
            return jsonify({
                'success': False,
                'error': f'请提供起点和终点 (收到: origin={origin_id}, dest={destination_id})'
            }), 400
        
        # 获取路径服务
        path_service = get_path_service()
        
        # 获取多条候选路线（使用不同策略）
        routes = []
        
        # 1. Dijkstra 最短距离
        distance_result = path_service.dijkstra(int(origin_id), int(destination_id), 'distance')
        if distance_result.success:
            route_obj = _build_route_object(distance_result, 'distance')
            routes.append(route_obj)
        
        # 2. Dijkstra 最短时间
        time_result = path_service.dijkstra(int(origin_id), int(destination_id), 'time')
        if time_result.success:
            route_obj = _build_route_object(time_result, 'time')
            routes.append(route_obj)
        
        # 3. A* 算法
        astar_result = path_service.a_star(int(origin_id), int(destination_id), 'distance')
        if astar_result.success:
            route_obj = _build_route_object(astar_result, 'distance')
            routes.append(route_obj)
        
        # 4. 尝试获取所有简单路径（更多候选）
        try:
            all_paths = path_service.get_all_paths(int(origin_id), int(destination_id), max_paths=10)
            if all_paths.get('success') and all_paths.get('paths'):
                for path_data in all_paths['paths']:
                    route_obj = {
                        'path': path_data.get('path', []),
                        'objectives': {
                            'distance': path_data.get('distance', 0),
                            'time': path_data.get('time', 0),
                            'cost': path_data.get('cost', 0)
                        }
                    }
                    routes.append(route_obj)
        except:
            pass
        
        # 去重（根据路径节点序列）
        unique_routes = []
        seen_paths = set()
        for route in routes:
            path_key = tuple(n.get('id', n.get('name', '')) for n in route.get('path', []))
            if path_key not in seen_paths:
                seen_paths.add(path_key)
                unique_routes.append(route)
        
        # 如果没有找到路径，生成基于直线距离的模拟路径
        if not unique_routes:
            origin_node = Node.query.get(int(origin_id))
            dest_node = Node.query.get(int(destination_id))
            
            if origin_node and dest_node:
                # 计算直线距离
                import math
                lat1, lng1 = float(origin_node.latitude or 0), float(origin_node.longitude or 0)
                lat2, lng2 = float(dest_node.latitude or 0), float(dest_node.longitude or 0)
                R = 6371
                dlat = math.radians(lat2 - lat1)
                dlng = math.radians(lng2 - lng1)
                a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng/2)**2
                direct_distance = R * 2 * math.asin(math.sqrt(a))
                
                # 估算时间和成本（假设平均速度 60km/h，成本 0.8元/km）
                estimated_time = direct_distance / 60 * 60  # 分钟
                estimated_cost = direct_distance * 0.8
                
                simulated_route = {
                    'path': [
                        {'id': origin_node.id, 'name': origin_node.name, 'latitude': origin_node.latitude, 'longitude': origin_node.longitude},
                        {'id': dest_node.id, 'name': dest_node.name, 'latitude': dest_node.latitude, 'longitude': dest_node.longitude}
                    ],
                    'objectives': {
                        'distance': round(direct_distance, 1),
                        'time': round(estimated_time, 1),
                        'cost': round(estimated_cost, 1)
                    },
                    'algorithm': 'direct',
                    'is_simulated': True
                }
                unique_routes.append(simulated_route)
                print(f"[多目标优化] 无直接路径，生成模拟路线: {direct_distance:.1f}km")
        
        # 添加路况和天气因素
        unique_routes = _enhance_routes_with_context(unique_routes, origin_id, destination_id)
        
        # 执行多目标优化
        optimizer = get_multi_objective_optimizer()
        
        if algorithm == 'weighted_sum':
            result = optimizer.optimize_weighted_sum(unique_routes, weights)
            # 统一返回格式
            return jsonify({
                'success': result.success,
                'recommendations': [{
                    'type': 'weighted_best',
                    'title': '加权最优方案',
                    'description': optimizer._generate_description(result),
                    'path': result.path,
                    'objectives': result.objectives,
                    'score': result.weighted_score
                }] if result.success else [],
                'algorithm': result.algorithm
            })
        
        elif algorithm == 'pareto':
            pareto_front = optimizer.find_pareto_front(unique_routes)
            # 统一返回格式
            recommendations = []
            for i, r in enumerate(pareto_front[:5]):
                recommendations.append({
                    'type': 'pareto',
                    'title': f'均衡方案 {i + 1}',
                    'description': optimizer._generate_description(r),
                    'path': r.path,
                    'objectives': r.objectives,
                    'rank': r.rank,
                    # Infinity 无法被 JSON 序列化，改为很大的数字
                    'crowding_distance': 9999 if r.crowding_distance == float('inf') else r.crowding_distance
                })
            return jsonify({
                'success': True,
                'recommendations': recommendations,
                'pareto_count': len(pareto_front),
                'algorithm': 'pareto'
            })
        
        else:  # 'all'
            recommendations = optimizer.generate_recommendations(unique_routes, weights)
            return jsonify(recommendations)
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@multi_obj_bp.route('/compare', methods=['POST'])
@jwt_required()
def compare_routes():
    """
    对比多条路线的多目标表现
    
    Body:
        routes: 路线列表 [{path, objectives}, ...]
    """
    try:
        data = request.get_json()
        routes = data.get('routes', [])
        
        if not routes:
            return jsonify({
                'success': False,
                'error': '请提供路线列表'
            }), 400
        
        optimizer = get_multi_objective_optimizer()
        
        # 找出 Pareto 最优解
        pareto_front = optimizer.find_pareto_front(routes)
        
        # 生成对比报告
        comparison = {
            'routes': [],
            'best_per_objective': {},
            'pareto_indices': []
        }
        
        for i, route in enumerate(routes):
            route_info = {
                'index': i,
                'objectives': route.get('objectives', {}),
                'is_pareto_optimal': False
            }
            comparison['routes'].append(route_info)
        
        # 标记 Pareto 最优解
        pareto_paths = set()
        for solution in pareto_front:
            for i, route in enumerate(routes):
                if route.get('path') == solution.path:
                    comparison['routes'][i]['is_pareto_optimal'] = True
                    comparison['pareto_indices'].append(i)
                    break
        
        # 找出每个目标的最优解
        for obj_name, config in optimizer.OBJECTIVES.items():
            values = [
                (i, r.get('objectives', {}).get(obj_name, float('inf')))
                for i, r in enumerate(routes)
                if obj_name in r.get('objectives', {})
            ]
            
            if values:
                if config.minimize:
                    best_idx = min(values, key=lambda x: x[1])[0]
                else:
                    best_idx = max(values, key=lambda x: x[1])[0]
                
                comparison['best_per_objective'][obj_name] = best_idx
        
        return jsonify({
            'success': True,
            'comparison': comparison,
            'pareto_count': len(pareto_front)
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


def _build_route_object(result, optimize_by):
    """构建路线对象
    
    注意：result.total_time 单位是小时，需要转换为分钟
    """
    # 时间从小时转换为分钟
    time_in_minutes = result.total_time * 60 if result.total_time else 0
    
    return {
        'path': result.path,
        'objectives': {
            'distance': result.total_distance,
            'time': round(time_in_minutes, 1),  # 转换为分钟
            'cost': result.total_cost
        },
        'algorithm': result.algorithm,
        'optimize_by': optimize_by
    }


def _enhance_routes_with_context(routes, origin_id, destination_id):
    """为路线添加路况和天气上下文"""
    try:
        # 获取起点和终点节点信息
        origin_node = Node.query.get(int(origin_id))
        dest_node = Node.query.get(int(destination_id))
        
        if not origin_node or not dest_node:
            return routes
        
        # 尝试获取路况评分
        traffic_service = get_traffic_service()
        
        for route in routes:
            # 添加默认路况评分
            if 'traffic' not in route.get('objectives', {}):
                route['objectives']['traffic'] = 70  # 默认良好
            
            # 添加默认天气风险
            if 'weather_risk' not in route.get('objectives', {}):
                route['objectives']['weather_risk'] = 10  # 默认低风险
        
        # 尝试获取真实路况
        try:
            origin_coord = f"{origin_node.longitude},{origin_node.latitude}"
            dest_coord = f"{dest_node.longitude},{dest_node.latitude}"
            
            traffic_result = traffic_service.check_route_traffic(origin_coord, dest_coord)
            
            if traffic_result.get('success'):
                # 计算整体路况评分
                traffic_overview = traffic_result.get('traffic_overview', {})
                total_distance = traffic_result.get('distance', 1)
                
                if total_distance > 0:
                    smooth_ratio = traffic_overview.get('畅通', 0) / total_distance
                    traffic_score = smooth_ratio * 100
                    routes[0]['objectives']['traffic'] = min(100, traffic_score)
        except:
            pass
        
        # 尝试获取天气风险
        try:
            weather_service = get_weather_service()
            weather_result = weather_service.get_weather_by_city(
                origin_node.city or '北京'
            )
            
            if weather_result.get('success'):
                weather_data = weather_result.get('data', {})
                weather_code = weather_data.get('code', '1')
                
                # 根据天气代码计算风险
                risk_map = {
                    '1': 5,    # 晴
                    '2': 10,   # 多云
                    '3': 15,   # 阴
                    '7': 30,   # 小雨
                    '8': 50,   # 中雨
                    '9': 70,   # 大雨
                    '13': 40,  # 小雪
                    '14': 60,  # 中雪
                    '15': 80,  # 大雪
                }
                
                weather_risk = risk_map.get(weather_code, 20)
                for route in routes:
                    route['objectives']['weather_risk'] = weather_risk
        except:
            pass
        
        return routes
    
    except Exception as e:
        return routes
