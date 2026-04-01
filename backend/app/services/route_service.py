#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
路线服务
管理路线的创建、查询、更新等操作
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime
from app.models import db
from app.models import Route, Node
from app.services.path_algorithm import get_path_service
from app.services.amap_service import get_amap_service

logger = logging.getLogger(__name__)


class RouteService:
    """路线服务"""
    
    def create_route(self, data: Dict) -> Route:
        """
        创建路线
        
        Args:
            data: 路线数据
        
        Returns:
            创建的路线对象
        """
        route = Route(
            name=data.get('name'),
            start_node_id=data.get('start_node_id'),
            end_node_id=data.get('end_node_id'),
            distance=data.get('distance'),
            duration=data.get('duration'),
            total_cost=data.get('total_cost'),
            notes=data.get('notes'),
            status='active'
        )
        
        db.session.add(route)
        db.session.commit()
        
        return route
    
    def update_route(self, route_id: int, data: Dict) -> Optional[Route]:
        """更新路线"""
        route = Route.query.get(route_id)
        if not route:
            return None
        
        if 'name' in data:
            route.name = data['name']
        if 'start_node_id' in data:
            route.start_node_id = data['start_node_id']
        if 'end_node_id' in data:
            route.end_node_id = data['end_node_id']
        if 'distance' in data:
            route.distance = data['distance']
        if 'duration' in data:
            route.duration = data['duration']
        if 'total_cost' in data:
            route.total_cost = data['total_cost']
        if 'notes' in data:
            route.notes = data['notes']
        if 'status' in data:
            route.status = data['status']
        
        route.updated_at = datetime.utcnow()
        db.session.commit()
        
        return route
    
    def delete_route(self, route_id: int) -> bool:
        """删除路线"""
        route = Route.query.get(route_id)
        if not route:
            return False
        
        db.session.delete(route)
        db.session.commit()
        
        return True
    
    def get_route(self, route_id: int) -> Optional[Route]:
        """获取单个路线"""
        return Route.query.get(route_id)
    
    def get_routes(self, filters: Dict = None) -> List[Route]:
        """获取路线列表"""
        query = Route.query
        
        if filters:
            if filters.get('status'):
                query = query.filter_by(status=filters['status'])
            if filters.get('start_node_id'):
                query = query.filter_by(start_node_id=filters['start_node_id'])
            if filters.get('end_node_id'):
                query = query.filter_by(end_node_id=filters['end_node_id'])
        
        return query.order_by(Route.created_at.desc()).all()
    
    def calculate_route(self, start_node_id: int, end_node_id: int, use_amap: bool = False) -> Dict:
        """
        计算路线
        
        Args:
            start_node_id: 起点节点ID
            end_node_id: 终点节点ID
            use_amap: 是否使用高德地图API
        
        Returns:
            路线计算结果
        """
        start_node = Node.query.get(start_node_id)
        end_node = Node.query.get(end_node_id)
        
        if not start_node or not end_node:
            return {'success': False, 'error': '节点不存在'}
        
        result = {
            'success': True,
            'start_node': start_node.to_dict(),
            'end_node': end_node.to_dict(),
            'distance': 0,
            'duration': 0,
            'cost': 0
        }
        
        # 本地算法计算
        try:
            path_service = get_path_service()
            path_result = path_service.dijkstra(start_node_id, end_node_id, 'comprehensive')
            
            if path_result.success:
                result['local'] = {
                    'distance': path_result.total_distance,
                    'duration': path_result.total_time * 60,  # 转换为分钟
                    'cost': path_result.total_cost,
                    'path': path_result.path
                }
        except Exception as e:
            logger.warning(f"本地算法计算失败: {e}")
        
        # 高德地图计算
        if use_amap and start_node.latitude and end_node.latitude:
            try:
                amap_service = get_amap_service()
                amap_result = amap_service.get_route(
                    (start_node.longitude, start_node.latitude),
                    (end_node.longitude, end_node.latitude)
                )
                
                if amap_result.get('success'):
                    route = amap_result.get('route', {})
                    result['amap'] = {
                        'distance': route.get('distance', 0) / 1000,  # 转换为公里
                        'duration': route.get('duration', 0) / 60,  # 转换为分钟
                        'tolls': route.get('tolls', 0),
                        'roads': route.get('roads', [])
                    }
            except Exception as e:
                logger.warning(f"高德地图计算失败: {e}")
        
        # 使用高德数据作为主要结果（如果可用）
        if 'amap' in result:
            result['distance'] = result['amap']['distance']
            result['duration'] = result['amap']['duration']
            result['cost'] = self._estimate_cost(
                result['amap']['distance'] * 1000,
                result['amap']['duration'] * 60,
                result['amap'].get('tolls', 0)
            )
        elif 'local' in result:
            result['distance'] = result['local']['distance']
            result['duration'] = result['local']['duration']
            result['cost'] = result['local']['cost']
        
        return result
    
    def _estimate_cost(self, distance_m: float, duration_s: float, tolls: float) -> float:
        """估算运输成本"""
        distance_km = distance_m / 1000
        duration_h = duration_s / 3600
        
        # 成本构成
        fuel_cost = distance_km * 0.8  # 油费
        toll_cost = tolls  # 过路费
        labor_cost = duration_h * 50  # 人工成本
        depreciation = distance_km * 0.3  # 折旧
        
        return round(fuel_cost + toll_cost + labor_cost + depreciation, 2)
    
    def get_route_stats(self) -> Dict:
        """获取路线统计"""
        total = Route.query.count()
        active = Route.query.filter_by(status='active').count()
        inactive = Route.query.filter_by(status='inactive').count()
        
        return {
            'total': total,
            'active': active,
            'inactive': inactive
        }


# 单例实例
_route_service = None


def get_route_service() -> RouteService:
    """获取路线服务实例"""
    global _route_service
    if _route_service is None:
        _route_service = RouteService()
    return _route_service
