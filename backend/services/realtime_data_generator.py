#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
大数据实时数据生成器
生成模拟订单、车辆轨迹等数据并发送到 Kafka
"""

import json
import time
import random
import threading
from datetime import datetime
from kafka import KafkaProducer

# Kafka 配置
KAFKA_BOOTSTRAP_SERVERS = 'localhost:9092'

# 模拟数据
CUSTOMERS = ['张三', '李四', '王五', '赵六', '钱七', '孙八', '周九', '吴十', 
             '郑十一', '王十二', '冯十三', '陈十四', '褚十五', '卫十六']

CARGOS = ['电子产品', '服装鞋帽', '食品饮料', '家具家电', '机械配件', 
          '日用品', '建材装饰', '化工原料', '医药品', '汽车零件']

CITIES = [
    {'name': '北京', 'lat': 39.9042, 'lng': 116.4074},
    {'name': '上海', 'lat': 31.2304, 'lng': 121.4737},
    {'name': '广州', 'lat': 23.1291, 'lng': 113.2644},
    {'name': '深圳', 'lat': 22.5431, 'lng': 114.0579},
    {'name': '杭州', 'lat': 30.2741, 'lng': 120.1551},
    {'name': '成都', 'lat': 30.5728, 'lng': 104.0668},
    {'name': '武汉', 'lat': 30.5928, 'lng': 114.3055},
    {'name': '西安', 'lat': 34.3416, 'lng': 108.9398},
    {'name': '南京', 'lat': 32.0603, 'lng': 118.7969},
    {'name': '重庆', 'lat': 29.4316, 'lng': 106.9123},
]

VEHICLE_PLATES = [f'京A{random.randint(10000, 99999)}' for _ in range(20)]
DRIVERS = ['张师傅', '李师傅', '王师傅', '赵师傅', '刘师傅', '陈师傅', '杨师傅', '黄师傅']


class RealtimeDataGenerator:
    """实时数据生成器"""
    
    def __init__(self):
        self.producer = None
        self.running = False
        self.order_interval = 5  # 每5秒生成一个订单
        self.vehicle_interval = 2  # 每2秒更新车辆位置
        self.stats = {
            'orders': 0,
            'vehicles': 0,
            'tracking': 0
        }
        # 车辆状态缓存
        self.vehicle_states = {}
        for i, plate in enumerate(VEHICLE_PLATES):
            origin = random.choice(CITIES)
            dest = random.choice([c for c in CITIES if c != origin])
            self.vehicle_states[plate] = {
                'id': i + 1,
                'plate': plate,
                'status': random.choice(['available', 'in_transit', 'loading']),
                'origin': origin,
                'destination': dest,
                'progress': random.uniform(0, 1),
                'speed': random.uniform(40, 80),
                'fuel': random.uniform(30, 100),
                'load': random.uniform(0, 500),
                'driver': random.choice(DRIVERS)
            }
    
    def connect(self):
        """连接 Kafka"""
        try:
            self.producer = KafkaProducer(
                bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
                value_serializer=lambda v: json.dumps(v, ensure_ascii=False).encode('utf-8')
            )
            print(f"✅ Kafka Producer 连接成功")
            return True
        except Exception as e:
            print(f"❌ Kafka Producer 连接失败: {e}")
            return False
    
    def send_to_kafka(self, topic: str, data: dict):
        """发送数据到 Kafka"""
        try:
            self.producer.send(topic, value=data)
            self.producer.flush(timeout=5)
            return True
        except Exception as e:
            print(f"❌ 发送 Kafka 失败: {e}")
            return False
    
    def generate_order(self):
        """生成订单数据"""
        origin = random.choice(CITIES)
        dest = random.choice([c for c in CITIES if c != origin])
        
        order = {
            'event_type': 'created',
            'order_id': random.randint(10000, 99999),
            'customer_name': random.choice(CUSTOMERS),
            'origin': origin['name'],
            'destination': dest['name'],
            'status': 'pending',
            'cost': round(random.uniform(100, 5000), 2),
            'weight': round(random.uniform(0.5, 50), 2),
            'distance': round(random.uniform(100, 2000), 2),
            'created_at': datetime.now().isoformat(),
            'timestamp': datetime.now().isoformat()
        }
        
        self.send_to_kafka('logistics.orders', order)
        self.stats['orders'] += 1
        return order
    
    def generate_vehicle_update(self):
        """生成车辆位置更新"""
        updates = []
        
        for plate, state in self.vehicle_states.items():
            # 更新进度
            state['progress'] += random.uniform(0.01, 0.05)
            if state['progress'] >= 1.0:
                # 到达目的地，重新分配
                state['progress'] = 0
                state['origin'] = state['destination']
                state['destination'] = random.choice([c for c in CITIES if c != state['origin']])
            
            # 计算当前位置
            lat = state['origin']['lat'] + (state['destination']['lat'] - state['origin']['lat']) * state['progress']
            lng = state['origin']['lng'] + (state['destination']['lng'] - state['origin']['lng']) * state['progress']
            
            vehicle = {
                'event_type': 'location_update',
                'vehicle_id': state['id'],
                'plate_number': state['plate'],
                'status': state['status'],
                'latitude': round(lat, 6),
                'longitude': round(lng, 6),
                'speed': round(random.uniform(30, 80), 2),
                'fuel_level': round(state['fuel'] - random.uniform(0.1, 0.5), 2),
                'current_load': round(state['load'], 2),
                'driver_name': state['driver'],
                'timestamp': datetime.now().isoformat()
            }
            
            self.send_to_kafka('logistics.vehicles', vehicle)
            self.stats['vehicles'] += 1
            updates.append(vehicle)
        
        return updates
    
    def generate_tracking(self):
        """生成轨迹数据"""
        tracking_list = []
        
        for plate, state in self.vehicle_states.items():
            if state['status'] == 'in_transit':
                lat = state['origin']['lat'] + (state['destination']['lat'] - state['origin']['lat']) * state['progress']
                lng = state['origin']['lng'] + (state['destination']['lng'] - state['origin']['lng']) * state['progress']
                
                tracking = {
                    'tracking_id': f"TRK{datetime.now().strftime('%Y%m%d%H%M%S')}{random.randint(100, 999)}",
                    'order_id': random.randint(10000, 99999),
                    'vehicle_id': state['id'],
                    'latitude': round(lat, 6),
                    'longitude': round(lng, 6),
                    'speed': round(random.uniform(30, 80), 2),
                    'heading': round(random.uniform(0, 360), 2),
                    'timestamp': datetime.now().isoformat()
                }
                
                self.send_to_kafka('logistics.tracking', tracking)
                self.stats['tracking'] += 1
                tracking_list.append(tracking)
        
        return tracking_list
    
    def run(self):
        """运行生成器"""
        if not self.connect():
            return
        
        self.running = True
        print(f"🚀 开始生成实时数据...")
        print(f"   订单生成间隔: {self.order_interval}秒")
        print(f"   车辆更新间隔: {self.vehicle_interval}秒")
        
        order_counter = 0
        vehicle_counter = 0
        tracking_counter = 0
        
        try:
            while self.running:
                time.sleep(1)
                order_counter += 1
                vehicle_counter += 1
                tracking_counter += 1
                
                # 生成订单
                if order_counter >= self.order_interval:
                    order_counter = 0
                    self.generate_order()
                
                # 更新车辆位置
                if vehicle_counter >= self.vehicle_interval:
                    vehicle_counter = 0
                    self.generate_vehicle_update()
                
                # 生成轨迹
                if tracking_counter >= 3:
                    tracking_counter = 0
                    self.generate_tracking()
                
                # 每30秒打印统计
                total = sum(self.stats.values())
                if total % 50 == 0 and total > 0:
                    print(f"📊 已生成: orders={self.stats['orders']}, vehicles={self.stats['vehicles']}, tracking={self.stats['tracking']}")
                    
        except KeyboardInterrupt:
            print("\n⏹️ 停止生成...")
        finally:
            self.stop()
    
    def stop(self):
        """停止生成器"""
        self.running = False
        if self.producer:
            self.producer.close()
        print(f"📊 最终统计: {self.stats}")


# 全局实例
_generator = None
_generator_thread = None


def start_generator():
    """启动生成器（后台线程）"""
    global _generator, _generator_thread
    
    if _generator is not None:
        print("⚠️ 生成器已在运行")
        return
    
    _generator = RealtimeDataGenerator()
    _generator_thread = threading.Thread(target=_generator.run, daemon=True)
    _generator_thread.start()
    print("✅ 数据生成器已启动（后台线程）")


def stop_generator():
    """停止生成器"""
    global _generator
    if _generator:
        _generator.stop()
        _generator = None


def get_generator_stats():
    """获取生成器统计"""
    global _generator
    if _generator:
        return _generator.stats
    return None


if __name__ == '__main__':
    # 直接运行
    generator = RealtimeDataGenerator()
    generator.run()
