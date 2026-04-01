#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
历史轨迹服务
存储和回放车辆历史轨迹
"""

import logging
import random
import math
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass
from app.models import db
from app.models import Vehicle, Node, Order

logger = logging.getLogger(__name__)


@dataclass
class TrajectoryPoint:
    """轨迹点"""
    latitude: float
    longitude: float
    timestamp: str
    speed: float
    heading: float


class TrajectoryHistory:
    """历史轨迹管理"""
    
    def __init__(self):
        # 内存中存储轨迹数据
        # 实际应用中应该使用数据库或时序数据库
        self._trajectories = {}  # {vehicle_id: [TrajectoryPoint, ...]}
        
    def add_point(
        self, 
        vehicle_id: int, 
        latitude: float, 
        longitude: float,
        speed: float = 0,
        heading: float = 0
    ):
        """添加轨迹点"""
        if vehicle_id not in self._trajectories:
            self._trajectories[vehicle_id] = []
        
        point = TrajectoryPoint(
            latitude=latitude,
            longitude=longitude,
            timestamp=datetime.utcnow().isoformat(),
            speed=speed,
            heading=heading
        )
        
        self._trajectories[vehicle_id].append(point)
        
        # 限制轨迹点数量
        if len(self._trajectories[vehicle_id]) > 10000:
            self._trajectories[vehicle_id] = self._trajectories[vehicle_id][-5000:]
    
    def get_trajectory(
        self, 
        vehicle_id: int, 
        start_time: str = None, 
        end_time: str = None
    ) -> List[Dict]:
        """
        获取车辆轨迹
        
        Args:
            vehicle_id: 车辆ID
            start_time: 开始时间
            end_time: 结束时间
        
        Returns:
            轨迹点列表
        """
        if vehicle_id not in self._trajectories:
            return []
        
        points = self._trajectories[vehicle_id]
        
        # 时间过滤
        if start_time or end_time:
            filtered = []
            for p in points:
                if start_time and p.timestamp < start_time:
                    continue
                if end_time and p.timestamp > end_time:
                    continue
                filtered.append({
                    'latitude': p.latitude,
                    'longitude': p.longitude,
                    'timestamp': p.timestamp,
                    'speed': p.speed,
                    'heading': p.heading
                })
            return filtered
        
        return [{
            'latitude': p.latitude,
            'longitude': p.longitude,
            'timestamp': p.timestamp,
            'speed': p.speed,
            'heading': p.heading
        } for p in points]
    
    def get_all_trajectories(self) -> Dict[int, List[Dict]]:
        """获取所有车辆轨迹"""
        result = {}
        for vehicle_id in self._trajectories:
            result[vehicle_id] = self.get_trajectory(vehicle_id)
        return result
    
    def clear_trajectory(self, vehicle_id: int):
        """清除车辆轨迹"""
        if vehicle_id in self._trajectories:
            del self._trajectories[vehicle_id]
    
    def generate_demo_trajectory(
        self,
        vehicle_id: int,
        start_lat: float,
        start_lng: float,
        end_lat: float,
        end_lng: float,
        duration_minutes: int = 60
    ) -> List[Dict]:
        """
        生成演示轨迹
        
        Args:
            vehicle_id: 车辆ID
            start_lat: 起点纬度
            start_lng: 起点经度
            end_lat: 终点纬度
            end_lng: 终点经度
            duration_minutes: 行程时长（分钟）
        
        Returns:
            生成的轨迹点列表
        """
        # 清除旧轨迹
        self.clear_trajectory(vehicle_id)
        
        # 计算轨迹点数量（每分钟约2个点）
        num_points = duration_minutes * 2
        
        # 生成轨迹点
        trajectory = []
        base_time = datetime.utcnow() - timedelta(minutes=duration_minutes)
        
        for i in range(num_points):
            progress = i / (num_points - 1) if num_points > 1 else 0
            
            # 添加一些随机偏移，模拟实际行驶
            offset_lat = random.uniform(-0.002, 0.002)
            offset_lng = random.uniform(-0.002, 0.002)
            
            lat = start_lat + (end_lat - start_lat) * progress + offset_lat
            lng = start_lng + (end_lng - start_lng) * progress + offset_lng
            
            timestamp = (base_time + timedelta(minutes=i * 0.5)).isoformat()
            
            # 计算方向
            heading = math.degrees(math.atan2(
                end_lng - start_lng,
                end_lat - start_lat
            )) % 360
            
            point = {
                'latitude': round(lat, 6),
                'longitude': round(lng, 6),
                'timestamp': timestamp,
                'speed': round(random.uniform(30, 80), 1),
                'heading': round(heading, 1)
            }
            
            trajectory.append(point)
            self.add_point(vehicle_id, lat, lng, point['speed'], heading)
        
        return trajectory
    
    def get_trajectory_statistics(self, vehicle_id: int) -> Dict:
        """获取轨迹统计"""
        trajectory = self.get_trajectory(vehicle_id)
        
        if not trajectory:
            return {
                'vehicle_id': vehicle_id,
                'points_count': 0,
                'total_distance_km': 0,
                'total_duration_minutes': 0,
                'avg_speed': 0
            }
        
        # 计算总距离
        total_distance = 0
        for i in range(1, len(trajectory)):
            p1 = trajectory[i-1]
            p2 = trajectory[i]
            total_distance += self._haversine_distance(
                p1['latitude'], p1['longitude'],
                p2['latitude'], p2['longitude']
            )
        
        # 计算时长
        first_time = datetime.fromisoformat(trajectory[0]['timestamp'].replace('Z', '+00:00'))
        last_time = datetime.fromisoformat(trajectory[-1]['timestamp'].replace('Z', '+00:00'))
        duration = (last_time - first_time).total_seconds() / 60
        
        # 平均速度
        avg_speed = sum(p['speed'] for p in trajectory) / len(trajectory)
        
        return {
            'vehicle_id': vehicle_id,
            'points_count': len(trajectory),
            'total_distance_km': round(total_distance, 2),
            'total_duration_minutes': round(duration, 1),
            'avg_speed': round(avg_speed, 1)
        }
    
    def _haversine_distance(self, lat1: float, lng1: float, lat2: float, lng2: float) -> float:
        """计算两点之间的距离（公里）"""
        R = 6371
        
        dlat = math.radians(lat2 - lat1)
        dlng = math.radians(lng2 - lng1)
        
        a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng/2)**2
        c = 2 * math.asin(math.sqrt(a))
        
        return R * c


# 单例实例
_trajectory_history = None


def get_trajectory_history() -> TrajectoryHistory:
    """获取历史轨迹实例"""
    global _trajectory_history
    if _trajectory_history is None:
        _trajectory_history = TrajectoryHistory()
    return _trajectory_history
