#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
车辆追踪服务
实时追踪车辆位置、状态更新
"""

import logging
import random
import math
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass
from app.models import db
from app.models import Vehicle, Order, Node

logger = logging.getLogger(__name__)


@dataclass
class VehicleLocation:
    """车辆位置"""
    vehicle_id: int
    plate_number: str
    latitude: float
    longitude: float
    speed: float
    heading: float
    status: str
    timestamp: str


class TrackingService:
    """车辆追踪服务"""
    
    def __init__(self):
        # 车辆当前状态缓存
        self._vehicle_states = {}
        
    def update_vehicle_location(
        self, 
        vehicle_id: int, 
        latitude: float, 
        longitude: float,
        speed: float = 0,
        heading: float = 0,
        status: str = 'moving'
    ) -> bool:
        """
        更新车辆位置
        
        Args:
            vehicle_id: 车辆ID
            latitude: 纬度
            longitude: 经度
            speed: 速度 (km/h)
            heading: 方向角
            status: 状态
        
        Returns:
            是否更新成功
        """
        vehicle = Vehicle.query.get(vehicle_id)
        if not vehicle:
            return False
        
        # 更新缓存
        self._vehicle_states[vehicle_id] = {
            'latitude': latitude,
            'longitude': longitude,
            'speed': speed,
            'heading': heading,
            'status': status,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # 可以保存到数据库或发送到消息队列
        logger.info(f"车辆 {vehicle.plate_number} 位置更新: ({latitude}, {longitude})")
        
        return True
    
    def get_vehicle_location(self, vehicle_id: int) -> Optional[VehicleLocation]:
        """获取车辆当前位置"""
        vehicle = Vehicle.query.get(vehicle_id)
        if not vehicle:
            return None
        
        state = self._vehicle_states.get(vehicle_id)
        
        if state:
            return VehicleLocation(
                vehicle_id=vehicle_id,
                plate_number=vehicle.plate_number,
                latitude=state['latitude'],
                longitude=state['longitude'],
                speed=state['speed'],
                heading=state['heading'],
                status=state['status'],
                timestamp=state['timestamp']
            )
        
        # 没有缓存数据，返回默认值
        return VehicleLocation(
            vehicle_id=vehicle_id,
            plate_number=vehicle.plate_number,
            latitude=0,
            longitude=0,
            speed=0,
            heading=0,
            status=vehicle.status,
            timestamp=datetime.utcnow().isoformat()
        )
    
    def get_all_vehicle_locations(self) -> List[VehicleLocation]:
        """获取所有车辆位置"""
        vehicles = Vehicle.query.filter(Vehicle.status.in_(['available', 'busy'])).all()
        
        locations = []
        for vehicle in vehicles:
            loc = self.get_vehicle_location(vehicle.id)
            if loc:
                locations.append(loc)
        
        return locations
    
    def simulate_vehicle_movement(self, vehicle_id: int, route_points: List[Dict]):
        """
        模拟车辆沿路线移动
        
        Args:
            vehicle_id: 车辆ID
            route_points: 路线点列表 [{'lat': float, 'lng': float}, ...]
        """
        if not route_points:
            return
        
        for point in route_points:
            self.update_vehicle_location(
                vehicle_id,
                point['lat'],
                point['lng'],
                speed=random.uniform(30, 80),
                heading=random.uniform(0, 360),
                status='moving'
            )
    
    def get_nearby_vehicles(self, latitude: float, longitude: float, radius_km: float = 10) -> List[Dict]:
        """
        获取附近的车辆
        
        Args:
            latitude: 中心纬度
            longitude: 中心经度
            radius_km: 半径（公里）
        
        Returns:
            附近车辆列表
        """
        all_vehicles = self.get_all_vehicle_locations()
        
        nearby = []
        for v in all_vehicles:
            distance = self._haversine_distance(
                latitude, longitude,
                v.latitude, v.longitude
            )
            
            if distance <= radius_km:
                nearby.append({
                    'vehicle_id': v.vehicle_id,
                    'plate_number': v.plate_number,
                    'latitude': v.latitude,
                    'longitude': v.longitude,
                    'distance_km': round(distance, 2),
                    'status': v.status
                })
        
        # 按距离排序
        nearby.sort(key=lambda x: x['distance_km'])
        
        return nearby
    
    def _haversine_distance(self, lat1: float, lng1: float, lat2: float, lng2: float) -> float:
        """计算两点之间的距离（公里）"""
        R = 6371  # 地球半径
        
        dlat = math.radians(lat2 - lat1)
        dlng = math.radians(lng2 - lng1)
        
        a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng/2)**2
        c = 2 * math.asin(math.sqrt(a))
        
        return R * c
    
    def update_order_status(self, order_id: int, status: str) -> bool:
        """
        更新订单状态
        
        Args:
            order_id: 订单ID
            status: 新状态
        
        Returns:
            是否更新成功
        """
        order = Order.query.get(order_id)
        if not order:
            return False
        
        order.status = status
        
        if status == 'delivered':
            order.delivered_at = datetime.utcnow()
            # 释放车辆
            if order.vehicle_id:
                vehicle = Vehicle.query.get(order.vehicle_id)
                if vehicle:
                    vehicle.status = 'available'
        
        db.session.commit()
        
        return True
    
    def get_route_polyline(self, origin_id: int, destination_id: int) -> Dict:
        """
        获取路线轨迹坐标点
        
        Args:
            origin_id: 起点节点ID
            destination_id: 终点节点ID
        
        Returns:
            路线数据
        """
        try:
            origin = Node.query.get(origin_id)
            destination = Node.query.get(destination_id)
            
            if not origin or not destination:
                return {'success': False, 'error': '节点不存在'}
            
            if not origin.latitude or not destination.latitude:
                return {'success': False, 'error': '节点缺少坐标信息'}
            
            # 生成简单的直线轨迹（实际应用中可调用高德API获取真实路线）
            import math
            num_points = 20
            polyline = []
            
            for i in range(num_points + 1):
                progress = i / num_points
                lat = origin.latitude + (destination.latitude - origin.latitude) * progress
                lng = origin.longitude + (destination.longitude - origin.longitude) * progress
                polyline.append({
                    'latitude': round(lat, 6),
                    'longitude': round(lng, 6),
                    'progress': round(progress * 100, 1)
                })
            
            # 计算总距离
            distance = self._haversine_distance(
                origin.latitude, origin.longitude,
                destination.latitude, destination.longitude
            )
            
            return {
                'success': True,
                'origin': {'id': origin.id, 'name': origin.name},
                'destination': {'id': destination.id, 'name': destination.name},
                'polyline': polyline,
                'distance_km': round(distance, 2),
                'points_count': len(polyline)
            }
        
        except Exception as e:
            logger.error(f"获取路线轨迹失败: {e}")
            return {'success': False, 'error': str(e)}
    
    def simulate_tracking(self, order_id: int, speed: float = 1.0) -> Dict:
        """
        模拟订单运输轨迹
        
        Args:
            order_id: 订单ID
            speed: 模拟速度倍数
        
        Returns:
            模拟数据
        """
        try:
            order = Order.query.get(order_id)
            if not order:
                return {'success': False, 'error': '订单不存在'}
            
            if not order.pickup_node_id or not order.delivery_node_id:
                return {'success': False, 'error': '订单缺少起终点信息'}
            
            # 获取车辆信息
            vehicle = None
            if order.vehicle_id:
                vehicle = Vehicle.query.get(order.vehicle_id)
            
            # 获取路线
            route = self.get_route_polyline(order.pickup_node_id, order.delivery_node_id)
            
            if not route['success']:
                return route
            
            # 获取起点和终点节点
            pickup_node = Node.query.get(order.pickup_node_id)
            delivery_node = Node.query.get(order.delivery_node_id)
            
            # 转换 polyline 为前端期望的格式 [[lng, lat], ...]
            polyline_coords = [[p['longitude'], p['latitude']] for p in route['polyline']]
            
            return {
                'success': True,
                'data': {
                    'order_id': order_id,
                    'order_number': order.order_number,
                    'route': {
                        'polyline': polyline_coords,
                        'distance_km': route['distance_km'],
                        'duration_minutes': route['distance_km'] / 60 * 60,  # 假设平均时速60km
                        'origin': route['origin'],
                        'destination': route['destination']
                    },
                    'vehicle': {
                        'id': vehicle.id if vehicle else 1,
                        'plate_number': vehicle.plate_number if vehicle else '京A12345',
                        'vehicle_type': vehicle.vehicle_type if vehicle else '货车',
                        'driver_name': vehicle.driver_name if vehicle else '张司机',
                        'driver_phone': vehicle.driver_phone if vehicle else '13800138000'
                    } if vehicle else {
                        'id': 1,
                        'plate_number': '京A12345',
                        'vehicle_type': '货车',
                        'driver_name': '张司机',
                        'driver_phone': '13800138000'
                    }
                }
            }
        
        except Exception as e:
            logger.error(f"模拟轨迹失败: {e}")
            return {'success': False, 'error': str(e)}
    
    def calculate_position(self, polyline: List[Dict], progress: float):
        """计算指定进度下的位置"""
        from dataclasses import dataclass
        
        @dataclass
        class Position:
            longitude: float
            latitude: float
            distance_from_start: float
            progress: float
        
        if not polyline or len(polyline) < 2:
            return None
        
        # 找到对应的位置点
        index = int(len(polyline) * progress / 100)
        index = max(0, min(index, len(polyline) - 1))
        
        point = polyline[index]
        
        # 计算距离起点的距离
        total_distance = 0
        for i in range(1, index + 1):
            p1 = polyline[i - 1]
            p2 = polyline[i]
            total_distance += self._haversine_distance(
                p1['latitude'], p1['longitude'],
                p2['latitude'], p2['longitude']
            )
        
        return Position(
            longitude=point['longitude'],
            latitude=point['latitude'],
            distance_from_start=round(total_distance, 2),
            progress=progress
        )
    
    def estimate_arrival(self, order_id: int, progress: float = 0) -> Dict:
        """估算到达时间"""
        try:
            order = Order.query.get(order_id)
            if not order:
                return {'success': False, 'error': '订单不存在'}
            
            route = self.get_route_polyline(order.pickup_node_id, order.delivery_node_id)
            
            if not route['success']:
                return route
            
            remaining_distance = route['distance_km'] * (100 - progress) / 100
            avg_speed = 60  # km/h
            eta_minutes = (remaining_distance / avg_speed) * 60
            
            from datetime import timedelta
            eta_time = datetime.utcnow() + timedelta(minutes=eta_minutes)
            
            return {
                'success': True,
                'data': {
                    'order_id': order_id,
                    'current_progress': progress,
                    'remaining_distance_km': round(remaining_distance, 2),
                    'eta_minutes': round(eta_minutes, 0),
                    'estimated_arrival': eta_time.isoformat()
                }
            }
        
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_tracking_history(self, order_id: int) -> Dict:
        """获取订单运输历史轨迹"""
        try:
            order = Order.query.get(order_id)
            if not order:
                return {'success': False, 'error': '订单不存在'}
            
            route = self.get_route_polyline(order.pickup_node_id, order.delivery_node_id)
            
            if not route['success']:
                return route
            
            return {
                'success': True,
                'data': {
                    'order_id': order_id,
                    'order_number': order.order_number,
                    'status': order.status,
                    'polyline': route['polyline'],
                    'route_info': {
                        'origin': route['origin'],
                        'destination': route['destination'],
                        'total_distance_km': route['distance_km']
                    }
                }
            }
        
        except Exception as e:
            return {'success': False, 'error': str(e)}


# 单例实例
_tracking_service = None


def get_tracking_service() -> TrackingService:
    """获取追踪服务实例"""
    global _tracking_service
    if _tracking_service is None:
        _tracking_service = TrackingService()
    return _tracking_service
