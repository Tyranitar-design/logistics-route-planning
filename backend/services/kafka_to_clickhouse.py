#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Kafka -> ClickHouse 数据消费者
从 Kafka 读取数据并写入 ClickHouse
"""

import json
import time
import requests
from datetime import datetime
from kafka import KafkaConsumer
import threading

# Kafka 配置
KAFKA_BOOTSTRAP_SERVERS = 'localhost:9092'
KAFKA_TOPICS = [
    'logistics.orders',
    'logistics.vehicles',
    'logistics.tracking',
    'logistics.alerts'
]

# ClickHouse 配置
CLICKHOUSE_HOST = 'http://localhost:8123'
CLICKHOUSE_DB = 'logistics'
CLICKHOUSE_USER = 'admin'
CLICKHOUSE_PASSWORD = 'admin123'

# 消费者组
GROUP_ID = 'logistics-clickhouse-consumer'


class KafkaToClickHouseConsumer:
    """Kafka 到 ClickHouse 的数据管道"""
    
    def __init__(self):
        self.consumer = None
        self.running = False
        self.stats = {
            'orders': 0,
            'vehicles': 0,
            'tracking': 0,
            'alerts': 0
        }
        
    def connect(self):
        """连接到 Kafka"""
        try:
            self.consumer = KafkaConsumer(
                *KAFKA_TOPICS,
                bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
                group_id=GROUP_ID,
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                auto_offset_reset='latest',
                enable_auto_commit=True
            )
            print(f"[OK] Kafka Consumer connected")
            return True
        except Exception as e:
            print(f"[ERROR] Kafka Consumer connection failed: {e}")
            return False
    
    def insert_to_clickhouse(self, table: str, data: dict):
        """插入数据到 ClickHouse"""
        try:
            # 构建 INSERT 语句
            if table == 'orders':
                query = f"""
                INSERT INTO {CLICKHOUSE_DB}.orders 
                (event_type, order_id, customer_name, origin, destination, status, cost, weight, distance, created_at, timestamp)
                VALUES
                """
                values = f"('{data.get('event_type', '')}', {data.get('order_id', 0)}, '{data.get('customer_name', '')}', '{data.get('origin', '')}', '{data.get('destination', '')}', '{data.get('status', '')}', {data.get('cost', 0)}, {data.get('weight', 0)}, {data.get('distance', 0)}, '{data.get('created_at', '')}', now())"
                
            elif table == 'vehicles':
                query = f"""
                INSERT INTO {CLICKHOUSE_DB}.vehicles 
                (event_type, vehicle_id, plate_number, status, latitude, longitude, speed, fuel_level, current_load, driver_name, timestamp)
                VALUES
                """
                values = f"('{data.get('event_type', '')}', {data.get('vehicle_id', 0)}, '{data.get('plate_number', '')}', '{data.get('status', '')}', {data.get('latitude', 0)}, {data.get('longitude', 0)}, {data.get('speed', 0)}, {data.get('fuel_level', 0)}, {data.get('current_load', 0)}, '{data.get('driver_name', '')}', now())"
                
            elif table == 'tracking':
                query = f"""
                INSERT INTO {CLICKHOUSE_DB}.tracking 
                (tracking_id, order_id, vehicle_id, latitude, longitude, speed, heading, event_time, timestamp)
                VALUES
                """
                values = f"('{data.get('tracking_id', '')}', {data.get('order_id', 0)}, {data.get('vehicle_id', 0)}, {data.get('latitude', 0)}, {data.get('longitude', 0)}, {data.get('speed', 0)}, {data.get('heading', 0)}, '{data.get('timestamp', '')}', now())"
                
            elif table == 'alerts':
                query = f"""
                INSERT INTO {CLICKHOUSE_DB}.alerts 
                (alert_id, alert_type, severity, title, message, source, related_order, related_vehicle, timestamp)
                VALUES
                """
                values = f"('{data.get('alert_id', '')}', '{data.get('alert_type', '')}', '{data.get('severity', '')}', '{data.get('title', '')}', '{data.get('message', '')}', '{data.get('source', '')}', {data.get('related_order', 0)}, {data.get('related_vehicle', 0)}, now())"
            else:
                return False
            
            # Execute insert with auth
            full_query = query + values
            response = requests.post(
                CLICKHOUSE_HOST,
                data=full_query,
                timeout=10,
                auth=(CLICKHOUSE_USER, CLICKHOUSE_PASSWORD)
            )
            
            if response.status_code == 200:
                self.stats[table] = self.stats.get(table, 0) + 1
                return True
            else:
                print(f"[ERROR] ClickHouse insert failed: {response.text}")
                return False
                
        except Exception as e:
            print(f"[ERROR] Insert ClickHouse failed: {e}")
            return False
    
    def process_message(self, topic: str, data: dict):
        """处理消息"""
        # 根据主题路由到对应表
        if topic == 'logistics.orders':
            self.insert_to_clickhouse('orders', data)
        elif topic == 'logistics.vehicles':
            self.insert_to_clickhouse('vehicles', data)
        elif topic == 'logistics.tracking':
            self.insert_to_clickhouse('tracking', data)
        elif topic == 'logistics.alerts':
            self.insert_to_clickhouse('alerts', data)
    
    def start(self):
        """启动消费者"""
        if not self.connect():
            return
        
        self.running = True
        print(f"[START] Consuming Kafka messages...")
        print(f"   Topics: {KAFKA_TOPICS}")
        
        try:
            for message in self.consumer:
                if not self.running:
                    break
                
                try:
                    topic = message.topic
                    data = message.value
                    
                    # 转义字符串中的单引号
                    def escape_quotes(obj):
                        if isinstance(obj, dict):
                            return {k: escape_quotes(v) for k, v in obj.items()}
                        elif isinstance(obj, str):
                            return obj.replace("'", "''")
                        else:
                            return obj
                    
                    data = escape_quotes(data)
                    
                    self.process_message(topic, data)
                    
                    # 每10条消息打印一次统计
                    total = sum(self.stats.values())
                    if total % 10 == 0:
                        print(f"[STATS] orders={self.stats['orders']}, vehicles={self.stats['vehicles']}, tracking={self.stats['tracking']}, alerts={self.stats['alerts']}")
                        
                except Exception as e:
                    print(f"[ERROR] Message processing failed: {e}")
                    
        except KeyboardInterrupt:
            print("\n[STOP] Stopping consumer...")
        finally:
            self.stop()
    
    def stop(self):
        """停止消费者"""
        self.running = False
        if self.consumer:
            self.consumer.close()
        print(f"[FINAL] Stats: {self.stats}")


# 单例实例
_consumer = None
_consumer_thread = None


def start_consumer():
    """启动消费者（后台线程）"""
    global _consumer, _consumer_thread
    
    if _consumer is not None:
        print("[WARN] Consumer already running")
        return
    
    _consumer = KafkaToClickHouseConsumer()
    _consumer_thread = threading.Thread(target=_consumer.start, daemon=True)
    _consumer_thread.start()
    print("[OK] Data consumer started (background thread)")


def stop_consumer():
    """停止消费者"""
    global _consumer
    if _consumer:
        _consumer.stop()
        _consumer = None


def get_consumer_stats():
    """获取消费者统计"""
    global _consumer
    if _consumer:
        return _consumer.stats
    return None


if __name__ == '__main__':
    # 直接运行
    consumer = KafkaToClickHouseConsumer()
    consumer.start()
