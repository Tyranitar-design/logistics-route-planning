"""
Kafka 消费者服务 - 实时消费数据并推送
"""
import json
import threading
from datetime import datetime
from flask_socketio import SocketIO

# Kafka 配置
KAFKA_BOOTSTRAP_SERVERS = 'localhost:9092'
KAFKA_TOPICS = [
    'logistics.orders',
    'logistics.vehicles',
    'logistics.tracking',
    'logistics.alerts',
    'logistics.analytics'
]

# SocketIO 实例（由 app 初始化时注入）
socketio = None

def init_kafka_consumer(app_socketio):
    """初始化 Kafka 消费者"""
    global socketio
    socketio = app_socketio
    
    # 启动消费者线程
    consumer_thread = threading.Thread(target=_consume_loop, daemon=True)
    consumer_thread.start()
    print("[Kafka] Consumer thread started")


def _consume_loop():
    """消费循环"""
    try:
        from kafka import KafkaConsumer
        
        consumer = KafkaConsumer(
            *KAFKA_TOPICS,
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            group_id='logistics-dashboard',
            auto_offset_reset='latest'
        )
        
        print(f"[OK] Kafka Consumer connected, topics: {KAFKA_TOPICS}")
        
        for message in consumer:
            try:
                topic = message.topic
                data = message.value
                
                # 根据主题推送到不同频道
                if 'orders' in topic:
                    _handle_order_event(data)
                elif 'vehicles' in topic:
                    _handle_vehicle_event(data)
                elif 'tracking' in topic:
                    _handle_tracking_event(data)
                elif 'alerts' in topic:
                    _handle_alert_event(data)
                    
            except Exception as e:
                print(f"[ERROR] Message handling failed: {e}")
                
    except Exception as e:
        print(f"[ERROR] Kafka Consumer connection failed: {e}")


def _handle_order_event(data):
    """处理订单事件"""
    if socketio:
        event_type = data.get('event_type', 'unknown')
        
        # 推送到前端
        socketio.emit('order_update', {
            'type': 'order',
            'event': event_type,
            'data': data,
            'timestamp': datetime.now().isoformat()
        })
        
        # 同时推送统计更新
        _push_statistics()
        
        print(f"[WS] Order event pushed: {event_type}")


def _handle_vehicle_event(data):
    """处理车辆事件"""
    if socketio:
        event_type = data.get('event_type', 'unknown')
        
        socketio.emit('vehicle_update', {
            'type': 'vehicle',
            'event': event_type,
            'data': data,
            'timestamp': datetime.now().isoformat()
        })
        
        print(f"[WS] Vehicle event pushed: {event_type}")


def _handle_tracking_event(data):
    """处理轨迹事件"""
    if socketio:
        socketio.emit('tracking_update', {
            'type': 'tracking',
            'data': data,
            'timestamp': datetime.now().isoformat()
        })


def _handle_alert_event(data):
    """处理预警事件"""
    if socketio:
        socketio.emit('alert_update', {
            'type': 'alert',
            'data': data,
            'timestamp': datetime.now().isoformat()
        })
        
        print(f"[WS] Alert event pushed: {data.get('title', 'unknown')}")


def _push_statistics():
    """推送最新统计数据"""
    try:
        from app.services.kafka_service import get_realtime_statistics
        
        stats = get_realtime_statistics()
        if stats and socketio:
            socketio.emit('statistics_update', {
                'type': 'statistics',
                'data': stats,
                'timestamp': datetime.now().isoformat()
            })
    except Exception as e:
        print(f"[ERROR] Statistics push failed: {e}")
