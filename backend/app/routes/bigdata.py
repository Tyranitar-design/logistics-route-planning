"""
大数据分析 API 路由
提供实时数据流、统计聚合、Kafka 状态等接口
"""

from flask import Blueprint, jsonify, request
from app.services.kafka_service import (
    send_order_event,
    send_vehicle_event,
    send_tracking_event,
    send_alert_event,
    send_analytics_event,
    get_realtime_statistics,
    get_kafka_status
)

bigdata_bp = Blueprint('bigdata', __name__)


@bigdata_bp.route('/status', methods=['GET'])
def kafka_status():
    """获取 Kafka 连接状态"""
    try:
        status = get_kafka_status()
        return jsonify({
            'success': True,
            'data': status
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bigdata_bp.route('/statistics', methods=['GET'])
def realtime_statistics():
    """获取实时统计数据（大屏展示用）"""
    try:
        stats = get_realtime_statistics()
        if stats:
            return jsonify({
                'success': True,
                'data': stats
            })
        else:
            return jsonify({
                'success': False,
                'error': '无法获取统计数据'
            }), 500
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bigdata_bp.route('/send/order', methods=['POST'])
def send_order():
    """发送订单事件到 Kafka"""
    try:
        data = request.get_json()
        event_type = data.get('event_type', 'created')
        order_data = data.get('order_data', {})
        
        success = send_order_event(order_data, event_type)
        
        return jsonify({
            'success': success,
            'message': '订单事件已发送' if success else '发送失败'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bigdata_bp.route('/send/vehicle', methods=['POST'])
def send_vehicle():
    """发送车辆事件到 Kafka"""
    try:
        data = request.get_json()
        event_type = data.get('event_type', 'status_update')
        vehicle_data = data.get('vehicle_data', {})
        
        success = send_vehicle_event(vehicle_data, event_type)
        
        return jsonify({
            'success': success,
            'message': '车辆事件已发送' if success else '发送失败'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bigdata_bp.route('/send/tracking', methods=['POST'])
def send_tracking():
    """发送轨迹事件到 Kafka"""
    try:
        data = request.get_json()
        tracking_data = data.get('tracking_data', {})
        
        success = send_tracking_event(tracking_data)
        
        return jsonify({
            'success': success,
            'message': '轨迹事件已发送' if success else '发送失败'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bigdata_bp.route('/send/alert', methods=['POST'])
def send_alert():
    """发送预警事件到 Kafka"""
    try:
        data = request.get_json()
        alert_data = data.get('alert_data', {})
        
        success = send_alert_event(alert_data)
        
        return jsonify({
            'success': success,
            'message': '预警事件已发送' if success else '发送失败'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bigdata_bp.route('/send/analytics', methods=['POST'])
def send_analytics():
    """发送分析事件到 Kafka"""
    try:
        data = request.get_json()
        event_name = data.get('event_name', 'unknown')
        event_data = data.get('event_data', {})
        
        success = send_analytics_event(event_name, event_data)
        
        return jsonify({
            'success': success,
            'message': '分析事件已发送' if success else '发送失败'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bigdata_bp.route('/dashboard', methods=['GET'])
def dashboard_data():
    """
    获取大数据大屏所需的所有数据
    一次性返回所有展示数据，减少请求次数
    """
    try:
        from app import db
        from app.models import Order, Vehicle, Node, Route
        from datetime import datetime, timedelta
        from sqlalchemy import func
        
        # 时间范围
        now = datetime.now()
        today = now.date()
        week_ago = today - timedelta(days=7)
        
        # 基础统计
        total_orders = Order.query.count()
        total_vehicles = Vehicle.query.count()
        total_nodes = Node.query.count()
        total_routes = Route.query.count()
        
        # 订单状态分布
        order_status = db.session.query(
            Order.status,
            func.count(Order.id)
        ).group_by(Order.status).all()
        
        status_distribution = {s: c for s, c in order_status}
        
        # 车辆状态分布
        vehicle_status = db.session.query(
            Vehicle.status,
            func.count(Vehicle.id)
        ).group_by(Vehicle.status).all()
        
        vehicle_distribution = {s: c for s, c in vehicle_status}
        
        # 今日订单
        today_orders = Order.query.filter(
            func.date(Order.created_at) == today
        ).count()
        
        # 本周订单趋势
        weekly_trend = []
        for i in range(7):
            day = today - timedelta(days=6-i)
            count = Order.query.filter(
                func.date(Order.created_at) == day
            ).count()
            weekly_trend.append({
                'date': day.isoformat(),
                'count': count
            })
        
        # 总成本和距离
        total_cost = db.session.query(
            func.sum(Order.estimated_cost)
        ).scalar() or 0
        
        total_distance = db.session.query(
            func.sum(Order.distance)
        ).scalar() or 0
        
        # 平均成本
        avg_cost = float(total_cost / total_orders) if total_orders > 0 else 0
        
        # Kafka 状态
        kafka = get_kafka_status()
        
        return jsonify({
            'success': True,
            'data': {
                'summary': {
                    'total_orders': total_orders,
                    'total_vehicles': total_vehicles,
                    'total_nodes': total_nodes,
                    'total_routes': total_routes,
                    'today_orders': today_orders,
                    'total_cost': float(total_cost),
                    'total_distance': float(total_distance),
                    'avg_cost': avg_cost
                },
                'orders': {
                    'status_distribution': status_distribution,
                    'weekly_trend': weekly_trend
                },
                'vehicles': {
                    'status_distribution': vehicle_distribution
                },
                'kafka': kafka,
                'timestamp': now.isoformat()
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
