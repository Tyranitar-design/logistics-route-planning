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
    
    已统一：走 VRPProblemBuilder + PreciseDistanceProvider 构建问题，
    与 /api/optimization/multi-objective 共用基础设施。
    
    Body:
        origin_id: 起点节点ID（仓库/发货地）
        destination_id: 终点节点ID（可选，用于筛选订单）
        solver: nsga2 或 nsga3
        n_gen: 迭代次数
    """
    from app.models import Node, Order, Vehicle
    from app.services.optimization_engine import (
        SolverFactory, SolverType
    )
    from app.services.vrp_problem_builder import VRPProblemBuilder
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
        query = Order.query.filter(Order.status.in_(['pending', '待配送']))
        
        if query.count() == 0:
            print("[NSGA优化] 没有待配送订单，获取所有未完成订单")
            query = Order.query.filter(Order.status.in_(['pending', 'in_transit', '待配送', '运输中']))
        
        if query.count() == 0:
            print("[NSGA优化] 没有未完成订单，获取所有订单")
            query = Order.query
        
        if origin_id:
            query = query.filter(
                db.or_(
                    Order.pickup_node_id == origin_id,
                    Order.pickup_node_id == None
                )
            )
        
        if destination_id:
            dest_node = Node.query.get(destination_id)
            if dest_node and dest_node.longitude and dest_node.latitude:
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
            node_id = order.delivery_node_id
            
            lng = None
            lat = None
            
            if node_id and node_id in node_map:
                node = node_map[node_id]
                lng = float(node.longitude or 0)
                lat = float(node.latitude or 0)
                node_name = node.name
            else:
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
        
        if not customers and destination_id:
            dest_node = Node.query.get(destination_id)
            if dest_node and dest_node.id != depot.id and dest_node.longitude and dest_node.latitude:
                print("[NSGA优化] 无匹配订单，按指定起终点构建真实 OD 候选路线")
                return jsonify(_build_specified_od_nsga_projection(
                    depot=depot,
                    destination=dest_node,
                    solver=solver,
                    n_gen=n_gen,
                    n_vehicles=n_vehicles,
                    vehicle_capacity=vehicle_capacity,
                ))

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
        
        # ========== 统一链路：使用 VRPProblemBuilder 构建问题 ==========
        # 构造标准 payload，与 /api/optimization/multi-objective 共用基础设施
        payload = {
            'customers': customers,
            'demands': demands,
            'depot': depot_pos,
            'capacity': vehicle_capacity,
            'problem_type': 'multi_objective',
            'use_precise_distance': True,
            'strategy': 0,
        }
        
        problem_builder = VRPProblemBuilder()
        build_result = problem_builder.build_from_payload(payload)
        problem = build_result.problem
        vrp_data = build_result.vrp_data
        
        # 求解
        solver_enum = SolverType(solver)
        solver_obj = SolverFactory.create_solver(solver_enum)
        result = solver_obj.solve(problem, n_gen=n_gen)
        
        print(f"[NSGA优化] 求解完成: objectives={result.objective_values}, time={result.solve_time:.2f}s")
        
        # ========== 透传真实 Pareto 前沿（不再伪造） ==========
        # 从 result.metadata 中获取真实 Pareto 前沿大小
        pareto_front_size = int(result.metadata.get('pareto_front_size', 1))
        
        # 如果求解器返回了完整 Pareto 前沿数据，直接使用
        # 否则用当前最优解的目标值作为唯一解
        pareto_front = result.metadata.get('pareto_front', None)
        if pareto_front is None:
            # 只有一个解时，构建单点 Pareto 前沿
            pareto_front = [[float(x) for x in result.objective_values]]
        
        return jsonify({
            'success': True,
            'routes': result.routes,
            'objectives': [float(x) for x in result.objective_values],
            'pareto_front': pareto_front,
            'pareto_front_size': pareto_front_size,
            'solve_time': float(result.solve_time),
            'solver': result.solver_name,
            'n_orders': len(orders),
            'n_customers': len(customers),
            'n_vehicles': n_vehicles,
            'depot': {'id': depot.id, 'name': depot.name, 'pos': depot_pos},
            'order_info': order_info[:10],
            # 新增：距离精度信息
            'distance_precision': vrp_data.distance_precision,
            'source_summary': vrp_data.source_summary,
            'distance_metadata': vrp_data.metadata,
            'build_metadata': build_result.build_metadata,
        })
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


def _node_route_payload(node):
    return {
        'id': node.id,
        'name': node.name,
        'longitude': float(node.longitude or 0),
        'latitude': float(node.latitude or 0),
        'type': node.type,
    }


def _build_specified_od_nsga_projection(depot, destination, solver, n_gen, n_vehicles, vehicle_capacity):
    """Build an explicit OD response instead of silently expanding to all nodes.

    NSGA VRP solvers evaluate depot-customer-depot tours. For a UI request with
    an explicit origin and destination, that is the wrong problem shape: the
    user asked for one OD path, not a fleet tour over every known node.
    """
    optimizer = get_multi_objective_optimizer()
    candidates = _build_specified_od_route_candidates(depot, destination)
    truth_meta = _truth_meta_from_routes(candidates)
    pareto_solutions = optimizer.find_pareto_front(candidates)
    front_quality = _front_quality_for_route_count(len(candidates), len(pareto_solutions))
    pareto_front = []
    for i, solution in enumerate(pareto_solutions):
        front_point = {
            'type': 'pareto',
            'title': f'候选路线 {i + 1}',
            'description': optimizer._generate_description(solution),
            'path': solution.path,
            'objectives': solution.objectives,
            'rank': solution.rank,
            'crowding_distance': 9999 if solution.crowding_distance == float('inf') else solution.crowding_distance,
        }
        pareto_front.append(_attach_route_candidate_metadata(front_point, candidates))
    pareto_front = _attach_explanations_to_recommendations(
        pareto_front,
        candidates,
        truth_meta,
        front_quality,
    )

    representative = min(
        candidates,
        key=lambda item: item.get('objectives', {}).get('distance', float('inf')),
    )
    representative_objectives = representative.get('objectives', {})
    objectives = [
        float(representative_objectives.get('distance', 0)),
        float(representative_objectives.get('time', 0)),
        1.0,
    ]
    precision = truth_meta.get('distance_precision') or {}
    cache_stats = truth_meta.get('distance_cache_stats') or {}
    source_summary = truth_meta.get('source_summary') or {}
    metadata = truth_meta.get('distance_metadata') or {}
    fallback_reason = truth_meta.get('fallback_reason')
    authenticity_level = truth_meta.get('authenticity_level') or 'C'
    fresh_amap_count = int(precision.get('fresh_amap_count', 0) or 0)
    exact_cache_count = int(precision.get('exact_cache_count', 0) or 0)

    return {
        'success': True,
        'problem_mode': 'specified_origin_destination',
        'routes': [
            {
                'route_candidate_id': route.get('route_candidate_id'),
                'path': [node.get('name') for node in route.get('path', [])],
                'objectives': route.get('objectives', {}),
                'route_strategy': route.get('route_strategy'),
            }
            for route in candidates
        ],
        'objectives': objectives,
        'pareto_front': pareto_front,
        'pareto_front_size': len(pareto_front),
        'pareto_summary': {
            'front_quality': front_quality,
            'reason': 'explicit_origin_destination_without_orders',
            'pareto_count': len(pareto_front),
            'total_routes': len(candidates),
        },
        'front_quality': front_quality,
        'solve_time': 0.0,
        'solver': solver,
        'solver_status': 'specified_od_route_candidates'
        if front_quality != 'single_solution_projection'
        else 'specified_od_projection',
        'n_orders': 0,
        'n_customers': 1,
        'n_vehicles': 1,
        'depot': {'id': depot.id, 'name': depot.name, 'pos': [float(depot.longitude), float(depot.latitude)]},
        'destination': {
            'id': destination.id,
            'name': destination.name,
            'pos': [float(destination.longitude), float(destination.latitude)],
        },
        'order_info': [],
        **truth_meta,
        'distance_precision': precision,
        'distance_cache_stats': cache_stats,
        'source_summary': source_summary,
        'distance_metadata': {
            **metadata,
            'distance_source': truth_meta.get('distance_source'),
            'path_source': truth_meta.get('path_source'),
            'authenticity_level': authenticity_level,
            'fallback_reason': fallback_reason,
            'vehicle_capacity': vehicle_capacity,
            'requested_n_vehicles': n_vehicles,
            'n_gen': n_gen,
        },
        'distance_source': truth_meta.get('distance_source'),
        'path_source': truth_meta.get('path_source'),
        'authenticity_level': authenticity_level,
        'fallback_reason': fallback_reason,
        'authenticity': {
            'level': authenticity_level,
            'distance_source': truth_meta.get('distance_source'),
            'path_source': truth_meta.get('path_source'),
            'fallback_reason': fallback_reason,
            'message': '指定起终点请求未匹配待配送订单，返回真实 OD 候选路线；若候选不足会明确标注前沿质量。',
        },
        'build_metadata': {
            'problem_type': 'specified_origin_destination',
            'n_customers': 1,
            'n_vehicles': 1,
            'distance_precision': precision,
            'distance_cache_stats': cache_stats,
            'source_summary': source_summary,
            'distance_metadata': metadata,
            'use_precise_distance': True,
            'strategy': representative.get('route_strategy', 0),
            'fallback_reason': fallback_reason,
            'exact_distance_available': authenticity_level in {'A', 'B'},
            'fresh_amap_count': fresh_amap_count,
            'exact_cache_count': exact_cache_count,
        },
    }


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
        
        # 如果没有找到图路径，按指定起终点构造可解释的 OD 候选路线。
        # 不再使用裸直线距离伪装成正常优化结果。
        if not unique_routes:
            origin_node = Node.query.get(int(origin_id))
            dest_node = Node.query.get(int(destination_id))
            
            if origin_node and dest_node:
                unique_routes.extend(_build_specified_od_route_candidates(origin_node, dest_node))
                print(f"[多目标优化] 无图路径，生成 {len(unique_routes)} 条指定 OD 候选路线")
        
        # 添加路况和天气因素
        unique_routes = _enhance_routes_with_context(unique_routes, origin_id, destination_id)
        truth_meta = _truth_meta_from_routes(unique_routes)
        
        # 执行多目标优化
        optimizer = get_multi_objective_optimizer()
        
        if algorithm == 'weighted_sum':
            result = optimizer.optimize_weighted_sum(unique_routes, weights)
            front_quality = _front_quality_for_route_count(len(unique_routes), 1 if result.success else 0)
            recommendations = _attach_truth_to_recommendations([{
                'type': 'weighted_best',
                'title': '加权最优方案',
                'description': optimizer._generate_description(result),
                'path': result.path,
                'objectives': result.objectives,
                'score': result.weighted_score
            }] if result.success else [], truth_meta)
            recommendations = [
                _attach_route_candidate_metadata(item, unique_routes)
                for item in recommendations
            ]
            recommendations = _attach_explanations_to_recommendations(
                recommendations,
                unique_routes,
                truth_meta,
                front_quality,
                weights,
            )
            # 统一返回格式
            return jsonify({
                'success': result.success,
                'recommendations': recommendations,
                'algorithm': result.algorithm,
                'total_routes': len(unique_routes),
                'front_quality': front_quality,
                'pareto_summary': {
                    'front_quality': front_quality,
                    'pareto_count': 1 if result.success else 0,
                    'total_routes': len(unique_routes),
                },
                **truth_meta,
            })
        
        elif algorithm == 'pareto':
            pareto_front = optimizer.find_pareto_front(unique_routes)
            front_quality = _front_quality_for_route_count(len(unique_routes), len(pareto_front))
            # 统一返回格式
            recommendations = []
            for i, r in enumerate(pareto_front[:5]):
                recommendation = {
                    'type': 'pareto',
                    'title': f'均衡方案 {i + 1}',
                    'description': optimizer._generate_description(r),
                    'path': r.path,
                    'objectives': r.objectives,
                    'rank': r.rank,
                    # Infinity 无法被 JSON 序列化，改为很大的数字
                    'crowding_distance': 9999 if r.crowding_distance == float('inf') else r.crowding_distance
                }
                recommendations.append(_attach_route_candidate_metadata(recommendation, unique_routes))
            recommendations = _attach_truth_to_recommendations(recommendations, truth_meta)
            recommendations = _attach_explanations_to_recommendations(
                recommendations,
                unique_routes,
                truth_meta,
                front_quality,
                weights,
            )
            return jsonify({
                'success': True,
                'recommendations': recommendations,
                'pareto_count': len(pareto_front),
                'total_routes': len(unique_routes),
                'algorithm': 'pareto',
                'front_quality': front_quality,
                'pareto_summary': {
                    'front_quality': front_quality,
                    'pareto_count': len(pareto_front),
                    'total_routes': len(unique_routes),
                },
                **truth_meta,
            })
        
        else:  # 'all'
            recommendations = optimizer.generate_recommendations(unique_routes, weights)
            recommendations['recommendations'] = _attach_truth_to_recommendations(
                recommendations.get('recommendations', []),
                truth_meta,
            )
            recommendations['recommendations'] = [
                _attach_route_candidate_metadata(item, unique_routes)
                for item in recommendations['recommendations']
            ]
            front_quality = _front_quality_for_route_count(
                recommendations.get('total_routes', len(unique_routes)),
                recommendations.get('pareto_count', 0),
            )
            recommendations['recommendations'] = _attach_explanations_to_recommendations(
                recommendations['recommendations'],
                unique_routes,
                truth_meta,
                front_quality,
                weights,
            )
            recommendations.update({
                **truth_meta,
                'front_quality': front_quality,
            })
            recommendations.setdefault('pareto_summary', {})
            recommendations['pareto_summary']['front_quality'] = recommendations['front_quality']
            recommendations['pareto_summary']['total_routes'] = recommendations.get('total_routes', len(unique_routes))
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


def _build_specified_od_route_candidate(origin_node, dest_node):
    """Build a single OD candidate with explicit distance/path provenance."""
    from app.services.precise_distance_provider import get_precise_distance_provider

    provider = get_precise_distance_provider()
    matrix_result = provider.build_distance_matrix(
        coordinates=[
            (float(origin_node.longitude), float(origin_node.latitude)),
            (float(dest_node.longitude), float(dest_node.latitude)),
        ],
        node_ids=[origin_node.id, dest_node.id],
        strategy=0,
        use_amap=True,
    )

    distance_km = float(matrix_result.distance_matrix_km[0][1])
    duration_min = float(matrix_result.duration_matrix_min[0][1])
    precision = matrix_result.precision or {}
    cache_stats = matrix_result.cache_stats or {}
    metadata = matrix_result.metadata or {}
    source_summary = matrix_result.source_summary or {}
    exact_count = int(precision.get('exact_count', 0) or 0)
    approx_count = int(precision.get('approx_count', 0) or 0)
    fallback_reason = metadata.get('fallback_reason')
    if not fallback_reason and exact_count == 0 and approx_count > 0:
        fallback_reason = 'precise_distance_provider_returned_approximate_cache_without_exact_amap_distance'

    authenticity_level = 'B' if exact_count > 0 else 'C'
    if fallback_reason:
        authenticity_level = 'C'

    return {
        'route_candidate_id': 'specified-od-projection-0',
        'path': [_node_route_payload(origin_node), _node_route_payload(dest_node)],
        'objectives': {
            'distance': round(distance_km, 2),
            'time': round(duration_min, 1),
            'cost': round(distance_km * 0.8, 2),
        },
        'algorithm': 'specified_origin_destination',
        'is_projection': True,
        'data_source': 'postgres_nodes',
        'distance_source': 'precise_distance_provider',
        'path_source': 'specified_origin_destination',
        'authenticity_level': authenticity_level,
        'fallback_reason': fallback_reason,
        'distance_precision': precision,
        'distance_cache_stats': cache_stats,
        'source_summary': source_summary,
        'distance_metadata': {
            **metadata,
            'distance_source': 'precise_distance_provider',
            'path_source': 'specified_origin_destination',
            'authenticity_level': authenticity_level,
            'fallback_reason': fallback_reason,
            'distance_cache_stats': cache_stats,
        },
    }


def _build_specified_od_route_candidates(origin_node, dest_node):
    """Build real OD route alternatives, falling back to one explicit projection.

    Candidate generation is deliberately source-first: AMap driving routes are
    treated as path candidates, while the precise distance provider is only the
    fallback single-candidate projection when route alternatives are unavailable.
    """
    candidates = _build_amap_route_candidates(origin_node, dest_node)
    if candidates:
        return candidates
    return [_build_specified_od_route_candidate(origin_node, dest_node)]


def _build_amap_route_candidates(origin_node, dest_node):
    from app.services.amap_service import get_amap_service

    origin = (float(origin_node.longitude), float(origin_node.latitude))
    destination = (float(dest_node.longitude), float(dest_node.latitude))
    amap_service = get_amap_service()

    try:
        result = amap_service.multi_route(origin, destination)
    except Exception as exc:
        result = {
            'success': False,
            'provider': 'amap',
            'provider_status': 'degraded',
            'fallback_reason': f'amap_multi_route_error:{exc}',
            'routes': [],
        }

    candidates = []
    seen = set()
    raw_routes = result.get('routes', []) or []
    if result.get('success') and raw_routes:
        for index, route in enumerate(raw_routes):
            candidate = _amap_route_to_candidate(
                origin_node,
                dest_node,
                route,
                route_index=route.get('route_index', index),
                candidate_id_prefix='amap-route',
                generation_source='amap_multi_route',
                provider=result.get('provider') or 'amap',
                provider_status=result.get('provider_status') or 'ok',
                fallback_reason=result.get('fallback_reason'),
                raw_candidate_count=len(raw_routes),
                register_api_call=index == 0,
            )
            _append_unique_route_candidate(candidates, candidate, seen)

    if result.get('success') and raw_routes and len(candidates) < 3:
        _extend_with_amap_strategy_candidates(
            candidates,
            seen,
            amap_service,
            origin_node,
            dest_node,
            origin,
            destination,
            min_candidates=3,
        )

    return candidates


def _extend_with_amap_strategy_candidates(
    candidates,
    seen,
    amap_service,
    origin_node,
    dest_node,
    origin,
    destination,
    min_candidates=3,
):
    strategies = [
        (0, '速度最快'),
        (1, '费用优先'),
        (2, '距离优先'),
        (4, '躲避拥堵'),
        (7, '躲避收费和不走高速'),
        (9, '躲避收费和不走高速且躲避拥堵'),
    ]

    for strategy, strategy_label in strategies:
        if len(candidates) >= min_candidates:
            break
        try:
            route_result = amap_service.driving_route(
                origin,
                destination,
                strategy=strategy,
                show_traffic=True,
            )
        except Exception:
            continue

        if not getattr(route_result, 'success', False):
            continue

        route = {
            'distance': route_result.distance,
            'duration': route_result.duration,
            'tolls': route_result.tolls,
            'toll_distance': route_result.toll_distance,
            'strategy': strategy_label,
            'main_roads': _main_roads_from_steps(route_result.steps or []),
            'polyline': route_result.polyline or [],
            'traffic_info': route_result.traffic_info or {},
        }
        candidate = _amap_route_to_candidate(
            origin_node,
            dest_node,
            route,
            route_index=strategy,
            candidate_id_prefix='amap-strategy',
            generation_source='amap_strategy_route',
            provider=getattr(route_result, 'provider', 'amap') or 'amap',
            provider_status=getattr(route_result, 'provider_status', 'ok') or 'ok',
            fallback_reason=getattr(route_result, 'fallback_reason', None),
            raw_candidate_count=1,
            register_api_call=True,
        )
        _append_unique_route_candidate(candidates, candidate, seen)


def _amap_route_to_candidate(
    origin_node,
    dest_node,
    route,
    route_index,
    candidate_id_prefix,
    generation_source,
    provider,
    provider_status,
    fallback_reason,
    raw_candidate_count,
    register_api_call,
):
    distance_m = float(route.get('distance') or 0)
    duration_s = float(route.get('duration') or 0)
    if distance_m <= 0 or duration_s <= 0:
        return None

    distance_km = round(distance_m / 1000.0, 2)
    duration_min = round(duration_s / 60.0, 1)
    tolls = float(route.get('tolls') or 0)
    strategy = route.get('strategy')
    polyline = route.get('polyline') or []
    traffic_score = _traffic_score_from_route(route)

    return {
        'route_candidate_id': f'{candidate_id_prefix}-{route_index}',
        'path': [_node_route_payload(origin_node), _node_route_payload(dest_node)],
        'objectives': {
            'distance': distance_km,
            'time': duration_min,
            'cost': round(distance_km * 0.8 + tolls, 2),
            'traffic': traffic_score,
            'weather_risk': 10,
        },
        'algorithm': generation_source,
        'optimize_by': 'route_alternative',
        'data_source': 'postgres_nodes',
        'distance_source': 'amap_driving_route',
        'path_source': 'amap_driving_route',
        'authenticity_level': 'B',
        'fallback_reason': fallback_reason,
        'route_strategy': strategy,
        'route_index': route_index,
        'tolls': tolls,
        'toll_distance_km': round(float(route.get('toll_distance') or 0) / 1000.0, 2),
        'main_roads': route.get('main_roads') or [],
        'polyline': polyline,
        'distance_precision': {
            'exact_count': 1,
            'approx_count': 0,
            'total_count': 1,
            'fresh_amap_count': 1,
            'exact_cache_count': 0,
            'approx_cache_count': 0,
            'fallback_count': 0,
        },
        'distance_cache_stats': {
            'cache_hits': 0,
            'amap_calls': 1 if register_api_call else 0,
            'haversine_fallbacks': 0,
            'total_pairs': 1,
            'amap_attempted_pairs': 1 if register_api_call else 0,
            'amap_successes': 1,
            'amap_route_attempted_pairs': 1 if register_api_call else 0,
            'amap_route_successes': 1,
            'amap_rejected_pairs': 0,
            'cache_rejected_pairs': 0,
        },
        'source_summary': {
            'amap_route': 1,
        },
        'candidate_generation': {
            'source': generation_source,
            'provider': provider,
            'provider_status': provider_status,
            'route_index': route_index,
            'strategy': strategy,
            'raw_candidate_count': raw_candidate_count,
        },
        'distance_metadata': {
            'provider': provider,
            'provider_status': provider_status,
            'fallback_reason': fallback_reason,
            'distance_source': 'amap_driving_route',
            'path_source': 'amap_driving_route',
            'authenticity_level': 'B',
            'route_strategy': strategy,
            'route_index': route_index,
            'main_roads': route.get('main_roads') or [],
            'has_polyline': bool(polyline),
        },
    }


def _append_unique_route_candidate(candidates, candidate, seen):
    if not candidate:
        return False
    objectives = candidate.get('objectives') or {}
    signature = (
        round(float(objectives.get('distance') or 0), 1),
        round(float(objectives.get('time') or 0), 1),
        round(float(candidate.get('tolls') or 0), 1),
        str(candidate.get('route_strategy')),
    )
    if signature in seen:
        return False
    seen.add(signature)
    candidates.append(candidate)
    return True


def _main_roads_from_steps(steps):
    roads = []
    for step in steps:
        road = step.get('road') if isinstance(step, dict) else None
        if road and road not in roads:
            roads.append(road)
    return roads[:5]


def _traffic_score_from_route(route):
    traffic_info = route.get('traffic_info') or {}
    congestion_ratio = traffic_info.get('congestion_ratio')
    if congestion_ratio is None:
        return 70
    try:
        return max(0, min(100, round(100 - float(congestion_ratio) * 100, 1)))
    except (TypeError, ValueError):
        return 70


def _truth_meta_from_routes(routes):
    route = next((item for item in routes if item.get('distance_source') or item.get('path_source')), None)
    if not route:
        return {
            'data_source': 'route_graph',
            'distance_source': 'route_graph',
            'path_source': 'path_algorithm_graph',
            'authenticity_level': 'C',
            'fallback_reason': 'legacy_path_algorithm_result_without_unified_truth_contract',
        }

    candidate_generation = _candidate_generation_summary(routes)
    return {
        'data_source': route.get('data_source') or 'postgres_nodes',
        'distance_source': route.get('distance_source'),
        'path_source': route.get('path_source'),
        'authenticity_level': route.get('authenticity_level'),
        'fallback_reason': route.get('fallback_reason'),
        'distance_precision': route.get('distance_precision'),
        'distance_cache_stats': _sum_numeric_dicts([item.get('distance_cache_stats') for item in routes]),
        'source_summary': _sum_numeric_dicts([item.get('source_summary') for item in routes]),
        'distance_metadata': route.get('distance_metadata'),
        'candidate_generation': candidate_generation,
    }


def _attach_truth_to_recommendations(recommendations, truth_meta):
    enriched = []
    for recommendation in recommendations:
        item = dict(recommendation)
        for key in [
            'data_source',
            'distance_source',
            'path_source',
            'authenticity_level',
            'fallback_reason',
            'distance_precision',
            'distance_cache_stats',
            'source_summary',
            'distance_metadata',
            'candidate_generation',
        ]:
            if truth_meta.get(key) is not None:
                item.setdefault(key, truth_meta.get(key))
        enriched.append(item)
    return enriched


def _attach_explanations_to_recommendations(
    recommendations,
    routes,
    truth_meta,
    front_quality,
    weights=None,
):
    context = _build_recommendation_explanation_context(routes, truth_meta, front_quality, weights)
    enriched = []
    for index, recommendation in enumerate(recommendations):
        item = dict(recommendation)
        match = _find_matching_route_candidate(item, routes) or item
        objectives = item.get('objectives') or match.get('objectives') or {}
        objective_ranks = _objective_ranks_for(objectives, context)
        tradeoff_summary = _build_tradeoff_summary(item, objective_ranks, context)
        item.setdefault(
            'recommendation_reason',
            _build_recommendation_reason(item, objective_ranks, tradeoff_summary, context, index),
        )
        item.setdefault('recommendation_reason_source', 'backend_multi_objective_governance')
        item.setdefault('tradeoff_summary', tradeoff_summary)
        item.setdefault('selection_metrics', {
            'candidate_count': context['candidate_count'],
            'front_quality': front_quality,
            'distance_source': truth_meta.get('distance_source'),
            'path_source': truth_meta.get('path_source'),
            'authenticity_level': truth_meta.get('authenticity_level'),
            'fallback_reason': truth_meta.get('fallback_reason'),
            'objective_ranks': objective_ranks,
            'best_objectives': context['best_objectives'],
            'weights_used': context['weights_used'],
            'route_candidate_id': item.get('route_candidate_id') or match.get('route_candidate_id'),
            'route_strategy': item.get('route_strategy') or match.get('route_strategy'),
            'source_counts': (truth_meta.get('candidate_generation') or {}).get('source_counts', {}),
        })
        enriched.append(item)
    return enriched


def _build_recommendation_explanation_context(routes, truth_meta, front_quality, weights=None):
    objective_configs = MultiObjectiveOptimizer.OBJECTIVES
    route_objectives = [
        route.get('objectives') or {}
        for route in routes
        if isinstance(route.get('objectives'), dict)
    ]
    best_objectives = {}
    objective_values = {}
    for obj_name, config in objective_configs.items():
        values = [
            float(objectives[obj_name])
            for objectives in route_objectives
            if obj_name in objectives and _is_number(objectives[obj_name])
        ]
        if not values:
            continue
        best_value = min(values) if config.minimize else max(values)
        worst_value = max(values) if config.minimize else min(values)
        best_objectives[obj_name] = {
            'label': config.display_name,
            'unit': config.unit,
            'best_value': round(best_value, 2),
            'worst_value': round(worst_value, 2),
            'minimize': config.minimize,
        }
        objective_values[obj_name] = values

    candidate_generation = truth_meta.get('candidate_generation') or {}
    return {
        'candidate_count': int(candidate_generation.get('candidate_count') or len(routes) or 0),
        'front_quality': front_quality,
        'best_objectives': best_objectives,
        'objective_values': objective_values,
        'weights_used': _normalize_explanation_weights(weights),
    }


def _objective_ranks_for(objectives, context):
    ranks = {}
    objective_configs = MultiObjectiveOptimizer.OBJECTIVES
    for obj_name, value in (objectives or {}).items():
        if obj_name not in objective_configs or not _is_number(value):
            continue
        values = context['objective_values'].get(obj_name) or []
        if not values:
            continue
        config = objective_configs[obj_name]
        unique_values = sorted(set(values), reverse=not config.minimize)
        numeric_value = float(value)
        rank = 1
        for index, candidate_value in enumerate(unique_values):
            if abs(candidate_value - numeric_value) <= 1e-9:
                rank = index + 1
                break
        ranks[obj_name] = {
            'rank': rank,
            'total': len(unique_values),
            'value': round(numeric_value, 2),
            'label': config.display_name,
            'unit': config.unit,
            'minimize': config.minimize,
        }
    return ranks


def _build_tradeoff_summary(recommendation, objective_ranks, context):
    strengths = []
    compromises = []
    candidate_count = max(int(context.get('candidate_count') or 0), 1)

    if candidate_count == 1:
        strengths.append('唯一真实候选，作为指定起终点代表方案')
    for obj_name, rank_info in objective_ranks.items():
        label = rank_info.get('label') or obj_name
        rank = int(rank_info.get('rank') or 0)
        total = int(rank_info.get('total') or candidate_count)
        if rank == 1:
            strengths.append(f'{label}当前最优')
        elif total > 1:
            compromises.append(f'{label}排名第{rank}/{total}')

    if recommendation.get('type') == 'weighted_best':
        strengths.insert(0, '按当前权重综合得分最低')
    elif recommendation.get('type') == 'pareto':
        strengths.insert(0, '非支配候选，代表一种真实路线权衡')
    elif recommendation.get('type') == 'single_objective':
        objective = recommendation.get('objective')
        label = objective_ranks.get(objective, {}).get('label') if objective else None
        strengths.insert(0, f'{label or recommendation.get("title") or "单目标"}表现最优')

    return {
        'strengths': _dedupe_text(strengths),
        'compromises': _dedupe_text(compromises),
        'front_quality': context.get('front_quality'),
    }


def _build_recommendation_reason(recommendation, objective_ranks, tradeoff_summary, context, index):
    title = recommendation.get('title') or f'方案 {index + 1}'
    strengths = tradeoff_summary.get('strengths') or []
    compromises = tradeoff_summary.get('compromises') or []
    front_quality = context.get('front_quality')
    candidate_count = context.get('candidate_count')
    reason_parts = [f'{title}基于{candidate_count}条真实候选路线评估']
    if strengths:
        reason_parts.append('优势：' + '、'.join(strengths[:3]))
    if compromises:
        reason_parts.append('取舍：' + '、'.join(compromises[:3]))
    if objective_ranks:
        rank_bits = [
            f"{info.get('label')}第{info.get('rank')}/{info.get('total')}"
            for info in objective_ranks.values()
            if info.get('rank') is not None
        ]
        if rank_bits:
            reason_parts.append('排名：' + '，'.join(rank_bits[:4]))
    reason_parts.append(f'前沿质量：{front_quality}')
    return '；'.join(reason_parts)


def _normalize_explanation_weights(weights):
    if not weights:
        return {name: config.default_weight for name, config in MultiObjectiveOptimizer.OBJECTIVES.items()}
    total = sum(float(value) for value in weights.values() if _is_number(value))
    if total <= 0:
        return {name: config.default_weight for name, config in MultiObjectiveOptimizer.OBJECTIVES.items()}
    return {
        key: round(float(value) / total, 4)
        for key, value in weights.items()
        if _is_number(value)
    }


def _is_number(value):
    try:
        float(value)
        return True
    except (TypeError, ValueError):
        return False


def _dedupe_text(items):
    seen = set()
    result = []
    for item in items:
        if not item or item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result


def _attach_route_candidate_metadata(recommendation, routes):
    item = dict(recommendation)
    match = _find_matching_route_candidate(item, routes)
    if not match:
        return item

    for key in [
        'route_candidate_id',
        'route_strategy',
        'route_index',
        'tolls',
        'toll_distance_km',
        'main_roads',
        'polyline',
    ]:
        if match.get(key) is not None:
            item.setdefault(key, match.get(key))
    return item


def _find_matching_route_candidate(recommendation, routes):
    rec_path = recommendation.get('path')
    rec_objectives = recommendation.get('objectives') or {}
    for route in routes:
        if rec_path == route.get('path') and _objectives_match(rec_objectives, route.get('objectives') or {}):
            return route

    for route in routes:
        if _objectives_match(rec_objectives, route.get('objectives') or {}):
            return route

    return None


def _objectives_match(left, right):
    if not left or not right:
        return False
    for key in ['distance', 'time', 'cost']:
        if key in left and key in right:
            try:
                if abs(float(left[key]) - float(right[key])) > 0.01:
                    return False
            except (TypeError, ValueError):
                return False
    return True


def _sum_numeric_dicts(items):
    summary = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        for key, value in item.items():
            if isinstance(value, (int, float)):
                summary[key] = summary.get(key, 0) + value
    return summary


def _candidate_generation_summary(routes):
    if not routes:
        return {
            'source': 'none',
            'candidate_count': 0,
            'front_quality': 'empty_front',
        }

    source_counts = {}
    strategies = []
    for route in routes:
        generation = route.get('candidate_generation') or {}
        source = generation.get('source') or route.get('algorithm') or 'unknown'
        source_counts[source] = source_counts.get(source, 0) + 1
        strategy = route.get('route_strategy')
        if strategy is not None and strategy not in strategies:
            strategies.append(strategy)

    return {
        'source': next(iter(source_counts.keys())),
        'source_counts': source_counts,
        'candidate_count': len(routes),
        'front_quality': _front_quality_for_route_count(len(routes), len(routes)),
        'strategies': strategies,
    }


def _front_quality_for_route_count(route_count, pareto_count):
    if route_count <= 1:
        return 'single_solution_projection'
    if pareto_count <= 1:
        return 'degenerate_front'
    return 'reported_front'


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
