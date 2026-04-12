"""
Kafka 生产者服务 - 发送订单事件到 Kafka
"""
import json
from datetime import datetime

# Kafka 配置
KAFKA_BOOTSTRAP_SERVERS = 'localhost:9092'
ORDER_TOPIC = 'logistics.orders'

# 生产者实例
_producer = None


def get_producer():
    """获取 Kafka 生产者实例（懒加载）"""
    global _producer
    if _producer is None:
        try:
            from kafka import KafkaProducer
            _producer = KafkaProducer(
                bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
                value_serializer=lambda v: json.dumps(v, ensure_ascii=False).encode('utf-8'),
                acks='all',  # 确保消息已写入
                retries=3
            )
            print("[Kafka Producer] 已连接")
        except Exception as e:
            print(f"[Kafka Producer] 连接失败: {e}")
            _producer = None
    return _producer


def send_order_event(order_data: dict, event_type: str = 'created'):
    """
    发送订单事件到 Kafka
    
    Args:
        order_data: 订单数据字典
        event_type: 事件类型 (created, updated, completed, cancelled)
    """
    producer = get_producer()
    if producer is None:
        print("[Kafka Producer] 未连接，跳过发送")
        return False
    
    try:
        # 构建事件消息
        event = {
            'event_type': event_type,
            'timestamp': datetime.now().isoformat(),
            'order_id': order_data.get('id') or order_data.get('order_id'),
            'order_number': order_data.get('order_number'),
            'status': order_data.get('status'),
            'cost': float(order_data.get('cost', 0)),
            'pickup_node_id': order_data.get('pickup_node_id'),
            'delivery_node_id': order_data.get('delivery_node_id'),
            'customer_name': order_data.get('customer_name'),
            'vehicle_id': order_data.get('vehicle_id'),
            'created_at': order_data.get('created_at'),
            'updated_at': datetime.now().isoformat()
        }
        
        # 发送到 Kafka
        future = producer.send(ORDER_TOPIC, value=event)
        result = future.get(timeout=10)
        
        print(f"[Kafka] 订单事件已发送: {event['order_id']} -> partition {result.partition}")
        return True
        
    except Exception as e:
        print(f"[Kafka Producer] 发送失败: {e}")
        return False


def send_vehicle_event(vehicle_data: dict, event_type: str = 'status_update'):
    """
    发送车辆状态事件到 Kafka
    """
    producer = get_producer()
    if producer is None:
        return False
    
    try:
        event = {
            'event_type': event_type,
            'timestamp': datetime.now().isoformat(),
            'vehicle_id': vehicle_data.get('id') or vehicle_data.get('vehicle_id'),
            'status': vehicle_data.get('status'),
            'location_lat': vehicle_data.get('current_lat'),
            'location_lng': vehicle_data.get('current_lng'),
            'driver_name': vehicle_data.get('driver_name')
        }
        
        future = producer.send('logistics.vehicles', value=event)
        result = future.get(timeout=10)
        return True
        
    except Exception as e:
        print(f"[Kafka Producer] 车辆事件发送失败: {e}")
        return False


def send_tracking_event(tracking_data: dict):
    """
    发送轨迹事件到 Kafka
    """
    producer = get_producer()
    if producer is None:
        return False
    
    try:
        event = {
            'timestamp': datetime.now().isoformat(),
            **tracking_data
        }
        
        future = producer.send('logistics.tracking', value=event)
        result = future.get(timeout=10)
        return True
        
    except Exception as e:
        print(f"[Kafka Producer] 轨迹事件发送失败: {e}")
        return False


def close_producer():
    """关闭 Kafka 生产者"""
    global _producer
    if _producer:
        _producer.flush()
        _producer.close()
        _producer = None
        print("[Kafka Producer] 已关闭")
