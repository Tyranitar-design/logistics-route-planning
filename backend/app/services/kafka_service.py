"""
Kafka 服务 - 实时数据流生产者
用于将订单、车辆、轨迹等数据发送到 Kafka 进行实时处理
"""

import json
import threading
from datetime import datetime
from flask import current_app

# Kafka 配置
KAFKA_BOOTSTRAP_SERVERS = 'localhost:9092'
KAFKA_TOPICS = {
    'orders': 'logistics.orders',
    'vehicles': 'logistics.vehicles',
    'tracking': 'logistics.tracking',
    'alerts': 'logistics.alerts',
    'analytics': 'logistics.analytics'
}

# 延迟导入 kafka，避免启动时连接失败
_kafka_producer = None

def get_kafka_producer():
    """获取 Kafka 生产者实例（延迟初始化）"""
    global _kafka_producer
    if _kafka_producer is None:
        try:
            from kafka import KafkaProducer
            _kafka_producer = KafkaProducer(
                bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
                value_serializer=lambda v: json.dumps(v, ensure_ascii=False).encode('utf-8'),
                key_serializer=lambda k: k.encode('utf-8') if k else None,
                retries=3,
                acks='all'
            )
            print(f"[OK] Kafka Producer connected: {KAFKA_BOOTSTRAP_SERVERS}")
        except Exception as e:
            print(f"[WARN] Kafka Producer connection failed: {e}")
            _kafka_producer = None
    return _kafka_producer


def send_to_kafka(topic: str, key: str, value: dict) -> bool:
    """
    发送消息到 Kafka
    
    Args:
        topic: 主题名称（orders/vehicles/tracking/alerts/analytics）
        key: 消息键（通常为记录ID）
        value: 消息内容（字典）
    
    Returns:
        bool: 是否发送成功
    """
    producer = get_kafka_producer()
    if producer is None:
        return False
    
    try:
        # 添加时间戳
        if 'timestamp' not in value:
            value['timestamp'] = datetime.now().isoformat()
        
        # 获取实际主题名
        actual_topic = KAFKA_TOPICS.get(topic, topic)
        
        # 异步发送
        future = producer.send(actual_topic, key=key, value=value)
        producer.flush(timeout=5)
        
        print(f"[Kafka] Sent: topic={actual_topic}, key={key}")
        return True
        
    except Exception as e:
        print(f"[ERROR] Kafka send failed: {e}")
        return False


def send_order_event(order_data: dict, event_type: str = 'created'):
    """
    发送订单事件到 Kafka
    
    Args:
        order_data: 订单数据
        event_type: 事件类型 (created/updated/completed/cancelled)
    """
    message = {
        'event_type': event_type,
        'order_id': order_data.get('id'),
        'customer_name': order_data.get('customer_name'),
        'origin': order_data.get('origin'),
        'destination': order_data.get('destination'),
        'status': order_data.get('status'),
        'cost': order_data.get('cost'),
        'weight': order_data.get('weight'),
        'distance': order_data.get('distance'),
        'created_at': order_data.get('created_at'),
        'updated_at': order_data.get('updated_at')
    }
    
    return send_to_kafka('orders', str(order_data.get('id', 'unknown')), message)


def send_vehicle_event(vehicle_data: dict, event_type: str = 'status_update'):
    """
    发送车辆事件到 Kafka
    
    Args:
        vehicle_data: 车辆数据
        event_type: 事件类型 (status_update/location_update/alert)
    """
    message = {
        'event_type': event_type,
        'vehicle_id': vehicle_data.get('id'),
        'plate_number': vehicle_data.get('plate_number'),
        'status': vehicle_data.get('status'),
        'latitude': vehicle_data.get('latitude'),
        'longitude': vehicle_data.get('longitude'),
        'speed': vehicle_data.get('speed'),
        'fuel_level': vehicle_data.get('fuel_level'),
        'current_load': vehicle_data.get('current_load'),
        'driver_name': vehicle_data.get('driver_name')
    }
    
    return send_to_kafka('vehicles', str(vehicle_data.get('id', 'unknown')), message)


def send_tracking_event(tracking_data: dict):
    """
    发送轨迹事件到 Kafka
    
    Args:
        tracking_data: 轨迹数据
    """
    message = {
        'tracking_id': tracking_data.get('id'),
        'order_id': tracking_data.get('order_id'),
        'vehicle_id': tracking_data.get('vehicle_id'),
        'latitude': tracking_data.get('latitude'),
        'longitude': tracking_data.get('longitude'),
        'speed': tracking_data.get('speed'),
        'heading': tracking_data.get('heading'),
        'timestamp': tracking_data.get('timestamp')
    }
    
    return send_to_kafka('tracking', str(tracking_data.get('id', 'unknown')), message)


def send_alert_event(alert_data: dict):
    """
    发送预警事件到 Kafka
    
    Args:
        alert_data: 预警数据
    """
    message = {
        'alert_id': alert_data.get('id'),
        'alert_type': alert_data.get('alert_type'),
        'severity': alert_data.get('severity'),
        'title': alert_data.get('title'),
        'message': alert_data.get('message'),
        'source': alert_data.get('source'),
        'related_order': alert_data.get('related_order'),
        'related_vehicle': alert_data.get('related_vehicle')
    }
    
    return send_to_kafka('alerts', str(alert_data.get('id', 'unknown')), message)


def send_analytics_event(event_name: str, event_data: dict):
    """
    发送分析事件到 Kafka
    
    Args:
        event_name: 事件名称
        event_data: 事件数据
    """
    message = {
        'event_name': event_name,
        **event_data
    }
    
    return send_to_kafka('analytics', event_name, message)


# 大数据统计聚合函数
def get_realtime_statistics():
    """
    获取实时统计数据（用于大屏展示）
    
    Returns:
        dict: 实时统计数据
    """
    from app import db
    from app.models import Order, Vehicle, Node
    
    try:
        # 订单统计
        total_orders = Order.query.count()
        pending_orders = Order.query.filter_by(status='pending').count()
        in_progress_orders = Order.query.filter_by(status='in_progress').count()
        completed_orders = Order.query.filter_by(status='completed').count()
        
        # 车辆统计
        total_vehicles = Vehicle.query.count()
        active_vehicles = Vehicle.query.filter_by(status='available').count()
        in_transit_vehicles = Vehicle.query.filter_by(status='in_transit').count()
        
        # 节点统计
        total_nodes = Node.query.count()
        
        # 今日订单（简化处理）
        from datetime import date
        today = date.today()
        today_orders = Order.query.filter(
            db.func.date(Order.created_at) == today
        ).count()
        
        # 总成本
        total_cost = db.session.query(
            db.func.sum(Order.estimated_cost)
        ).scalar() or 0
        
        # 总距离
        total_distance = db.session.query(
            db.func.sum(Order.distance)
        ).scalar() or 0
        
        return {
            'orders': {
                'total': total_orders,
                'pending': pending_orders,
                'in_progress': in_progress_orders,
                'completed': completed_orders,
                'today': today_orders
            },
            'vehicles': {
                'total': total_vehicles,
                'active': active_vehicles,
                'in_transit': in_transit_vehicles
            },
            'nodes': {
                'total': total_nodes
            },
            'summary': {
                'total_cost': float(total_cost),
                'total_distance': float(total_distance),
                'avg_cost_per_order': float(total_cost / total_orders) if total_orders > 0 else 0
            },
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        print(f"[ERROR] Statistics failed: {e}")
        return None


def get_kafka_status():
    """
    获取 Kafka 连接状态
    
    Returns:
        dict: Kafka 状态信息
    """
    producer = get_kafka_producer()
    
    status = {
        'connected': producer is not None,
        'bootstrap_servers': KAFKA_BOOTSTRAP_SERVERS,
        'topics': list(KAFKA_TOPICS.values()),
        'timestamp': datetime.now().isoformat()
    }
    
    if producer:
        try:
            # 尝试获取集群元数据
            from kafka import KafkaAdminClient
            admin = KafkaAdminClient(
                bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS
            )
            topics = admin.list_topics()
            status['available_topics'] = topics
            admin.close()
        except Exception as e:
            status['metadata_error'] = str(e)
    
    return status
