#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
数据生成器服务
自动生成模拟订单、车辆轨迹等实时数据
"""

import random
import threading
import time
from datetime import datetime
from typing import List, Dict, Optional
from dataclasses import dataclass
from app.models import db
from app.models import Order, Node, Vehicle, Route


@dataclass
class VehicleLocation:
    """车辆位置数据"""
    vehicle_id: int
    plate_number: str
    latitude: float
    longitude: float
    speed: float
    heading: float
    status: str
    timestamp: str


@dataclass
class NewOrderEvent:
    """新订单事件"""
    order_id: int
    order_number: str
    customer_name: str
    cargo_name: str
    priority: str
    status: str
    timestamp: str


class DataGenerator:
    """数据生成器"""
    
    # 客户数据
    CUSTOMERS = ['张三', '李四', '王五', '赵六', '钱七', '孙八', '周九', '吴十', 
                 '郑十一', '王十二', '冯十三', '陈十四', '褚十五', '卫十六']
    
    # 货物数据
    CARGOS = ['电子产品', '服装鞋帽', '食品饮料', '家具家电', '机械配件', 
              '日用品', '建材装饰', '化工原料', '医药品', '汽车零件',
              '办公用品', '体育器材', '玩具礼品', '农产品', '纺织品']
    
    # 优先级权重
    PRIORITIES = ['normal'] * 7 + ['express'] * 2 + ['urgent']
    
    # 状态流转
    STATUS_FLOW = ['pending', 'assigned', 'in_transit', 'delivered']
    
    def __init__(self):
        self._running = False
        self._thread = None
        self._order_interval = 30  # 秒
        self._location_interval = 5  # 秒
        self._callbacks = {
            'new_order': [],
            'vehicle_location': []
        }
        
        # 缓存数据
        self._nodes_cache = []
        self._vehicles_cache = []
        self._vehicle_routes = {}  # 车辆当前路线
        
    def start(self):
        """启动数据生成"""
        if self._running:
            return
        
        self._running = True
        self._load_cache()
        
        # 启动订单生成线程
        self._thread = threading.Thread(target=self._generate_loop, daemon=True)
        self._thread.start()
        
    def stop(self):
        """停止数据生成"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
            self._thread = None
            
    def _load_cache(self):
        """加载节点和车辆缓存"""
        self._nodes_cache = Node.query.filter_by(status='active').all()
        self._vehicles_cache = Vehicle.query.filter_by(status='available').all()
        
    def _generate_loop(self):
        """生成循环"""
        order_counter = 0
        location_counter = 0
        
        while self._running:
            time.sleep(1)
            order_counter += 1
            location_counter += 1
            
            # 定期生成订单
            if order_counter >= self._order_interval:
                order_counter = 0
                try:
                    self._generate_random_order()
                except Exception as e:
                    print(f"生成订单失败: {e}")
            
            # 定期更新车辆位置
            if location_counter >= self._location_interval:
                location_counter = 0
                try:
                    self._update_vehicle_locations()
                except Exception as e:
                    print(f"更新车辆位置失败: {e}")
                    
    def _generate_random_order(self):
        """生成随机订单"""
        if len(self._nodes_cache) < 2:
            return None
            
        # 随机选择起点和终点
        nodes = random.sample(self._nodes_cache, 2)
        pickup_node, delivery_node = nodes
        
        # 生成订单号
        order_number = f'ORD{datetime.now().strftime("%Y%m%d%H%M%S")}{random.randint(100, 999)}'
        
        # 随机数据
        customer = random.choice(self.CUSTOMERS)
        cargo = random.choice(self.CARGOS)
        priority = random.choice(self.PRIORITIES)
        weight = round(random.uniform(0.5, 50), 2)
        volume = round(random.uniform(0.1, 30), 2)
        
        # 创建订单
        order = Order(
            order_number=order_number,
            customer_name=customer,
            customer_phone=f'1{random.randint(3, 9)}{random.randint(100000000, 999999999)}',
            pickup_node_id=pickup_node.id,
            delivery_node_id=delivery_node.id,
            cargo_name=cargo,
            cargo_type='general',
            weight=weight,
            volume=volume,
            priority=priority,
            status='pending',
            notes='自动生成订单'
        )
        
        db.session.add(order)
        db.session.commit()
        
        # 触发回调
        event = NewOrderEvent(
            order_id=order.id,
            order_number=order_number,
            customer_name=customer,
            cargo_name=cargo,
            priority=priority,
            status='pending',
            timestamp=datetime.now().isoformat()
        )
        self._trigger_callback('new_order', event)
        
        return order
        
    def _update_vehicle_locations(self):
        """更新车辆位置"""
        for vehicle in self._vehicles_cache:
            # 获取或创建车辆路线
            if vehicle.id not in self._vehicle_routes:
                if len(self._nodes_cache) >= 2:
                    nodes = random.sample(self._nodes_cache, 2)
                    self._vehicle_routes[vehicle.id] = {
                        'start': nodes[0],
                        'end': nodes[1],
                        'progress': 0.0,
                        'status': 'moving'
                    }
            
            route = self._vehicle_routes.get(vehicle.id)
            if route:
                # 更新进度
                route['progress'] += random.uniform(0.02, 0.05)
                
                if route['progress'] >= 1.0:
                    # 到达终点，重新分配路线
                    route['progress'] = 0.0
                    if len(self._nodes_cache) >= 2:
                        nodes = random.sample(self._nodes_cache, 2)
                        route['start'] = nodes[0]
                        route['end'] = nodes[1]
                
                # 计算当前位置
                start = route['start']
                end = route['end']
                progress = route['progress']
                
                lat = start.latitude + (end.latitude - start.latitude) * progress
                lng = start.longitude + (end.longitude - start.longitude) * progress
                
                location = VehicleLocation(
                    vehicle_id=vehicle.id,
                    plate_number=vehicle.plate_number,
                    latitude=lat,
                    longitude=lng,
                    speed=random.uniform(30, 80),
                    heading=random.uniform(0, 360),
                    status=route['status'],
                    timestamp=datetime.now().isoformat()
                )
                
                self._trigger_callback('vehicle_location', location)
                
    def _trigger_callback(self, event_type, data):
        """触发回调"""
        for callback in self._callbacks.get(event_type, []):
            try:
                callback(data)
            except Exception as e:
                print(f"回调执行失败: {e}")
                
    def on(self, event_type, callback):
        """注册事件回调"""
        if event_type in self._callbacks:
            self._callbacks[event_type].append(callback)
            
    def generate_order_now(self) -> Optional[Order]:
        """立即生成一个订单"""
        return self._generate_random_order()
    
    def get_vehicle_locations(self) -> List[Dict]:
        """获取所有车辆当前位置"""
        locations = []
        for vehicle_id, route in self._vehicle_routes.items():
            start = route['start']
            end = route['end']
            progress = route['progress']
            
            locations.append({
                'vehicle_id': vehicle_id,
                'latitude': start.latitude + (end.latitude - start.latitude) * progress,
                'longitude': start.longitude + (end.longitude - start.longitude) * progress,
                'status': route['status'],
                'progress': progress
            })
        return locations


# 单例实例
_generator = None


def get_data_generator() -> DataGenerator:
    """获取数据生成器实例"""
    global _generator
    if _generator is None:
        _generator = DataGenerator()
    return _generator
