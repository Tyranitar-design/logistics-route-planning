"""
数据分析 API 路由
- 预测性维护
- 客户画像
- 供应链可视化
- 碳足迹计算
"""

from flask import Blueprint, request, jsonify
from datetime import datetime, timedelta
from typing import Dict, List, Any
import random

from app.services.data_analytics_service import data_analytics_service
from app.models import db
from app.models import Order, Vehicle, Node

analytics_bp = Blueprint('data_analytics', __name__, url_prefix='/api/data-analytics')


# ==================== 预测性维护 ====================

@analytics_bp.route('/predictive-maintenance', methods=['GET'])
def get_predictive_maintenance():
    """
    获取预测性维护数据
    - 路线拥堵预测
    - 高风险路线识别
    """
    try:
        # 获取路线数据
        routes = []
        for r in Node.query.filter(Node.type.in_(['warehouse', 'distribution'])).limit(10).all():
            routes.append({
                'id': r.id,
                'name': r.name,
                'type': r.type
            })
        
        # 如果没有路线，使用模拟数据
        if not routes:
            routes = [
                {'id': i, 'name': f'路线{i}', 'type': 'distribution'}
                for i in range(1, 6)
            ]
        
        result = data_analytics_service.get_predictive_maintenance(routes)
        
        return jsonify({
            'success': True,
            'data': result
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@analytics_bp.route('/traffic-prediction', methods=['POST'])
def predict_traffic():
    """
    预测特定路线的交通状况
    """
    try:
        data = request.get_json() or {}
        routes = data.get('routes', [])
        
        if not routes:
            # 获取所有路线
            for r in Node.query.filter(Node.type.in_(['warehouse', 'distribution'])).limit(10).all():
                routes.append({
                    'id': r.id,
                    'name': r.name
                })
        
        predictions = data_analytics_service.traffic_predictor.predict_all_routes(routes)
        
        return jsonify({
            'success': True,
            'predictions': predictions
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


# ==================== 客户画像分析 ====================

@analytics_bp.route('/customer-profiles', methods=['GET'])
def get_customer_profiles():
    """
    获取客户画像分析
    """
    try:
        # 获取订单数据
        orders = []
        for o in Order.query.limit(100).all():
            orders.append({
                'id': o.id,
                'order_number': o.order_number,
                'customer_name': o.customer_name,
                'status': o.status,
                'priority': o.priority,
                'created_at': o.created_at.isoformat() if o.created_at else None,
                'actual_cost': float(o.actual_cost) if o.actual_cost else None,
                'estimated_cost': float(o.estimated_cost) if o.estimated_cost else None,
                'weight': float(o.weight) if o.weight else None,
                'cargo_type': o.cargo_type,
                'pickup_node_id': o.pickup_node_id,
                'delivery_node_id': o.delivery_node_id
            })
        
        # 提取客户列表
        customer_names = list(set(o['customer_name'] for o in orders if o.get('customer_name')))
        customers = [{'id': i+1, 'name': name} for i, name in enumerate(customer_names)]
        
        # 如果没有客户，使用模拟数据
        if not customers:
            customers = [
                {'id': 1, 'name': '客户A'},
                {'id': 2, 'name': '客户B'},
                {'id': 3, 'name': '客户C'}
            ]
            orders = [
                {
                    'id': 1,
                    'customer_name': '客户A',
                    'status': 'delivered',
                    'created_at': (datetime.now() - timedelta(days=i)).isoformat(),
                    'actual_cost': 500 + i * 100,
                    'weight': 5 + i
                }
                for i in range(10)
            ]
        
        result = data_analytics_service.get_customer_analysis(customers, orders)
        
        return jsonify({
            'success': True,
            'data': result
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@analytics_bp.route('/customer/<int:customer_id>', methods=['GET'])
def get_customer_detail(customer_id: int):
    """
    获取单个客户详情
    """
    try:
        # 获取客户订单
        orders = []
        for o in Order.query.filter(Order.customer_name == f'客户{customer_id}').limit(50).all():
            orders.append({
                'id': o.id,
                'order_number': o.order_number,
                'status': o.status,
                'created_at': o.created_at.isoformat() if o.created_at else None,
                'actual_cost': float(o.actual_cost) if o.actual_cost else None,
                'weight': float(o.weight) if o.weight else None
            })
        
        customer = {'id': customer_id, 'name': f'客户{customer_id}'}
        
        profile = data_analytics_service.customer_analyzer.analyze_customer(customer, orders)
        
        return jsonify({
            'success': True,
            'profile': {
                'customer_id': profile.customer_id,
                'customer_name': profile.customer_name,
                'value_level': profile.value_level,
                'value_score': profile.value_score,
                'total_orders': profile.total_orders,
                'total_revenue': profile.total_revenue,
                'satisfaction_score': profile.satisfaction_score,
                'recommendations': profile.recommendations
            }
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


# ==================== 供应链可视化 ====================

@analytics_bp.route('/supply-chain', methods=['GET'])
def get_supply_chain():
    """
    获取供应链可视化数据
    """
    try:
        # 获取节点
        nodes = []
        try:
            for n in Node.query.limit(20).all():
                nodes.append({
                    'id': n.id,
                    'name': n.name or '未命名',
                    'type': n.type or 'unknown',
                    'status': getattr(n, 'status', 'active') or 'active',
                    'latitude': n.latitude or 0,
                    'longitude': n.longitude or 0
                })
        except Exception as db_err:
            print(f"[供应链] 数据库查询失败: {db_err}")
        
        # 获取订单
        orders = []
        try:
            for o in Order.query.limit(50).all():
                orders.append({
                    'id': o.id,
                    'status': o.status or 'pending',
                    'pickup_node_id': o.pickup_node_id,
                    'delivery_node_id': o.delivery_node_id,
                    'weight': float(o.weight) if o.weight else 1
                })
        except Exception as db_err:
            print(f"[供应链] 订单查询失败: {db_err}")
        
        # 如果没有数据，使用模拟
        if not nodes:
            nodes = [
                {'id': 1, 'name': '北京仓库', 'type': 'warehouse', 'status': 'active', 'latitude': 39.9, 'longitude': 116.4},
                {'id': 2, 'name': '上海仓库', 'type': 'warehouse', 'status': 'active', 'latitude': 31.2, 'longitude': 121.5},
                {'id': 3, 'name': '广州配送站', 'type': 'distribution', 'status': 'active', 'latitude': 23.1, 'longitude': 113.3},
                {'id': 4, 'name': '深圳配送站', 'type': 'distribution', 'status': 'active', 'latitude': 22.5, 'longitude': 114.1}
            ]
            orders = [
                {'id': 1, 'status': 'delivered', 'pickup_node_id': 1, 'delivery_node_id': 3, 'weight': 10},
                {'id': 2, 'status': 'in_progress', 'pickup_node_id': 2, 'delivery_node_id': 4, 'weight': 15}
            ]
        
        result = data_analytics_service.get_supply_chain_dashboard(nodes, orders)
        
        return jsonify({
            'success': True,
            'data': result
        })
    
    except Exception as e:
        import traceback
        print(f"[供应链] 错误: {e}")
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@analytics_bp.route('/supply-chain/track/<int:order_id>', methods=['GET'])
def track_order(order_id: int):
    """
    追踪订单在供应链中的位置
    """
    try:
        # 获取供应链数据
        nodes = []
        for n in Node.query.limit(20).all():
            nodes.append({
                'id': n.id,
                'name': n.name,
                'type': n.type,
                'status': 'active',
                'latitude': n.latitude,
                'longitude': n.longitude,
                'location': {'lat': n.latitude, 'lng': n.longitude}
            })
        
        # 获取订单连接
        order = Order.query.get(order_id)
        if not order:
            return jsonify({
                'success': False,
                'message': '订单不存在'
            }), 404
        
        connections = [{
            'from': order.pickup_node_id,
            'to': order.delivery_node_id,
            'order_id': order.id,
            'status': order.status,
            'weight': order.weight
        }]
        
        tracking = data_analytics_service.supply_chain_visualizer.track_order(order_id, nodes, connections)
        
        return jsonify({
            'success': True,
            'tracking': tracking
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


# ==================== 碳足迹计算 ====================

@analytics_bp.route('/carbon-footprint', methods=['GET'])
def get_carbon_footprint():
    """
    获取碳足迹报告
    """
    try:
        # 获取路线数据
        routes = []
        orders = []
        
        # 从数据库获取
        try:
            for o in Order.query.limit(20).all():
                orders.append({
                    'id': o.id,
                    'order_number': o.order_number or f'ORD{o.id}',
                    'distance': float(o.distance) if o.distance else random.randint(50, 500),
                    'weight': float(o.weight) if o.weight else random.uniform(1, 10)
                })
        except Exception as db_err:
            print(f"[碳足迹] 订单查询失败: {db_err}")
        
        # 如果没有订单，使用模拟数据
        if not orders:
            orders = [
                {'id': i, 'order_number': f'ORD{i:04d}', 'distance': random.randint(50, 200), 'weight': random.uniform(1, 10)}
                for i in range(1, 11)
            ]
        
        # 模拟路线数据
        routes = [
            {'id': i, 'name': f'路线{i}', 'distance': random.randint(100, 500), 'vehicle_type': 'medium', 'fuel_type': 'diesel'}
            for i in range(1, 6)
        ]
        
        result = data_analytics_service.get_carbon_footprint_report(routes, orders)
        
        return jsonify({
            'success': True,
            'data': result
        })
    
    except Exception as e:
        import traceback
        print(f"[碳足迹] 错误: {e}")
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@analytics_bp.route('/carbon-footprint/calculate', methods=['POST'])
def calculate_carbon():
    """
    计算特定路线/订单的碳足迹
    """
    try:
        data = request.get_json() or {}
        
        distance = data.get('distance', 100)
        vehicle_type = data.get('vehicle_type', 'medium')
        fuel_type = data.get('fuel_type', 'diesel')
        
        footprint = data_analytics_service.carbon_calculator.calculate_emission(
            distance, vehicle_type, fuel_type
        )
        
        return jsonify({
            'success': True,
            'footprint': {
                'distance_km': footprint.distance_km,
                'vehicle_type': footprint.vehicle_type,
                'fuel_type': footprint.fuel_type,
                'co2_emission_kg': footprint.co2_emission_kg,
                'emission_per_km': footprint.emission_per_km,
                'green_alternative': footprint.green_alternative,
                'reduction_potential': footprint.reduction_potential
            }
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@analytics_bp.route('/green-routes', methods=['POST'])
def find_green_routes():
    """
    推荐绿色低碳路线
    """
    try:
        data = request.get_json() or {}
        routes = data.get('routes', [])
        
        if not routes:
            routes = [
                {'id': i, 'name': f'路线{i}', 'distance': random.randint(100, 500)}
                for i in range(1, 6)
            ]
        
        green_routes = data_analytics_service.carbon_calculator.find_green_routes(routes)
        
        return jsonify({
            'success': True,
            'data': green_routes
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


# ==================== 综合仪表盘 ====================

@analytics_bp.route('/dashboard', methods=['GET'])
def get_dashboard():
    """
    获取数据分析综合仪表盘
    """
    try:
        import random
        
        # 预测性维护
        routes = [{'id': i, 'name': f'路线{i}'} for i in range(1, 6)]
        predictive = data_analytics_service.get_predictive_maintenance(routes)
        
        # 客户画像
        customers = [{'id': i, 'name': f'客户{i}'} for i in range(1, 11)]
        orders = [
            {
                'id': i,
                'customer_name': f'客户{random.randint(1, 10)}',
                'status': random.choice(['delivered', 'in_transit', 'pending']),
                'created_at': (datetime.now() - timedelta(days=random.randint(1, 30))).isoformat(),
                'actual_cost': random.randint(100, 1000),
                'weight': random.uniform(1, 10)
            }
            for i in range(50)
        ]
        customer_analysis = data_analytics_service.get_customer_analysis(customers, orders)
        
        # 供应链
        nodes = [
            {'id': 1, 'name': '北京仓库', 'type': 'warehouse', 'status': 'active', 'latitude': 39.9, 'longitude': 116.4},
            {'id': 2, 'name': '上海仓库', 'type': 'warehouse', 'status': 'active', 'latitude': 31.2, 'longitude': 121.5},
            {'id': 3, 'name': '广州配送站', 'type': 'distribution', 'status': 'active', 'latitude': 23.1, 'longitude': 113.3}
        ]
        supply_orders = [
            {'id': 1, 'status': 'delivered', 'pickup_node_id': 1, 'delivery_node_id': 3, 'weight': 10}
        ]
        supply_chain = data_analytics_service.get_supply_chain_dashboard(nodes, supply_orders)
        
        # 碳足迹
        carbon_routes = [{'id': i, 'name': f'路线{i}', 'distance': random.randint(100, 300)} for i in range(1, 4)]
        carbon_orders = [{'id': i, 'distance': random.randint(50, 200), 'weight': random.uniform(1, 10)} for i in range(10)]
        carbon = data_analytics_service.get_carbon_footprint_report(carbon_routes, carbon_orders)
        
        return jsonify({
            'success': True,
            'dashboard': {
                'predictive_maintenance': {
                    'high_risk_count': predictive['summary']['high_risk_count'],
                    'predictions': predictive['traffic_predictions'][:3]
                },
                'customer_analysis': {
                    'total_customers': customer_analysis['summary']['total_customers'],
                    'high_value_count': customer_analysis['summary']['high_value_count'],
                    'avg_satisfaction': customer_analysis['summary']['avg_satisfaction']
                },
                'supply_chain': {
                    'fulfillment_rate': supply_chain['metrics']['fulfillment_rate'],
                    'on_time_delivery': supply_chain['metrics']['on_time_delivery'],
                    'bottleneck_nodes': supply_chain['metrics']['bottleneck_nodes']
                },
                'carbon_footprint': {
                    'total_emission_kg': carbon['summary']['total_emission_kg'],
                    'potential_saving_kg': carbon['summary']['potential_saving_kg'],
                    'greenest_route': carbon['route_emissions'].get('greenest_route')
                }
            }
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


def register_data_analytics_routes(app):
    """注册数据分析路由"""
    app.register_blueprint(analytics_bp)