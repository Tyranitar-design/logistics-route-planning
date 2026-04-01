#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
订单路线推荐服务
整合本地算法和高德地图API，为订单提供最优路线推荐
"""

import logging
from typing import Dict, List, Optional
from dataclasses import dataclass
from app.models import db
from app.models import Node, Route, Order, Vehicle
from app.services.path_algorithm import get_path_service
from app.services.amap_service import get_amap_service

logger = logging.getLogger(__name__)


@dataclass
class OrderRouteRecommendation:
    """订单路线推荐结果"""
    success: bool
    order_id: int = None
    origin: Dict = None
    destination: Dict = None
    
    # 本地算法结果
    local_route: Dict = None
    
    # 高德地图结果
    amap_route: Dict = None
    
    # 推荐结果
    recommended_route: Dict = None
    recommendation_reason: str = None
    
    error: str = None


class OrderRouteService:
    """订单路线推荐服务"""
    
    def recommend_for_order(
        self, 
        order_id: int = None,
        origin_id: int = None,
        destination_id: int = None,
        weight: float = 0,
        prefer_source: str = 'auto'  # auto, local, amap
    ) -> OrderRouteRecommendation:
        """
        为订单推荐路线
        
        Args:
            order_id: 订单ID（可选）
            origin_id: 起点节点ID
            destination_id: 终点节点ID
            weight: 货物重量（影响成本计算）
            prefer_source: 偏好数据源
        
        Returns:
            订单路线推荐结果
        """
        # 获取节点信息
        if order_id:
            order = Order.query.get(order_id)
            if not order:
                return OrderRouteRecommendation(success=False, error='订单不存在')
            origin_id = order.pickup_node_id
            destination_id = order.delivery_node_id
        
        origin = Node.query.get(origin_id)
        destination = Node.query.get(destination_id)
        
        if not origin or not destination:
            return OrderRouteRecommendation(success=False, error='起点或终点不存在')
        
        result = OrderRouteRecommendation(
            success=True,
            order_id=order_id,
            origin=origin.to_dict(),
            destination=destination.to_dict()
        )
        
        # 1. 本地算法路线推荐
        try:
            local_result = self._get_local_route(origin_id, destination_id)
            if local_result['success']:
                result.local_route = local_result
        except Exception as e:
            logger.warning(f"本地算法推荐失败: {e}")
        
        # 2. 高德地图路线推荐
        if origin.longitude and origin.latitude and destination.longitude and destination.latitude:
            try:
                amap_result = self._get_amap_route(origin, destination)
                if amap_result['success']:
                    result.amap_route = amap_result
            except Exception as e:
                logger.warning(f"高德地图推荐失败: {e}")
        
        # 3. 综合推荐
        result.recommended_route, result.recommendation_reason = self._select_best_route(
            result.local_route, 
            result.amap_route,
            prefer_source
        )
        
        return result
    
    def _get_local_route(self, origin_id: int, destination_id: int) -> Dict:
        """获取本地算法路线"""
        service = get_path_service()
        
        # 多目标优化
        results = service.multi_objective_optimize(origin_id, destination_id)
        
        if not results:
            return {'success': False, 'error': '无法找到路线'}
        
        # 整合结果
        result = {
            'success': True,
            'source': 'local',
            'algorithms': {}
        }
        
        # 最短距离
        if 'best_distance' in results:
            r = results['best_distance']
            result['algorithms']['shortest_distance'] = {
                'path': r['path'],
                'distance_km': r['distance'],
                'duration_minutes': r['time'] * 60,
                'cost': r['cost']
            }
        
        # 最短时间
        if 'best_time' in results:
            r = results['best_time']
            result['algorithms']['shortest_time'] = {
                'path': r['path'],
                'distance_km': r['distance'],
                'duration_minutes': r['time'] * 60,
                'cost': r['cost']
            }
        
        # 最低成本
        if 'best_cost' in results:
            r = results['best_cost']
            result['algorithms']['lowest_cost'] = {
                'path': r['path'],
                'distance_km': r['distance'],
                'duration_minutes': r['time'] * 60,
                'cost': r['cost']
            }
        
        # 综合最优
        if 'comprehensive_best' in results:
            r = results['comprehensive_best']
            result['algorithms']['comprehensive'] = {
                'path': r['path'],
                'distance_km': r['distance'],
                'duration_minutes': r['time'] * 60,
                'cost': r['cost'],
                'weights': r.get('weights')
            }
        
        # 默认推荐综合最优
        if 'comprehensive_best' in results:
            r = results['comprehensive_best']
            result['distance_km'] = r['distance']
            result['duration_minutes'] = r['time'] * 60
            result['cost'] = r['cost']
            result['path'] = r['path']
        
        return result
    
    def _get_amap_route(self, origin: Node, destination: Node) -> Dict:
        """获取高德地图路线"""
        service = get_amap_service()
        
        # 多路线规划
        result = service.multi_route(
            (origin.longitude, origin.latitude),
            (destination.longitude, destination.latitude)
        )
        
        if not result.get('success'):
            return {'success': False, 'error': result.get('error', '高德地图路线规划失败')}
        
        routes = result.get('routes', [])
        if not routes:
            return {'success': False, 'error': '未找到可用路线'}
        
        # 整合结果
        amap_result = {
            'success': True,
            'source': 'amap',
            'routes': [],
            'origin_name': origin.name,
            'destination_name': destination.name
        }
        
        for i, route in enumerate(routes):
            route_info = {
                'index': i + 1,
                'distance_km': round(route['distance'] / 1000, 2),
                'duration_minutes': round(route['duration'] / 60, 1),
                'tolls': route.get('tolls', 0),
                'toll_distance_km': round(route.get('toll_distance', 0) / 1000, 2),
                'strategy': route.get('strategy'),
                'main_roads': route.get('main_roads', [])
            }
            amap_result['routes'].append(route_info)
        
        # 默认取第一条（最优）
        if routes:
            amap_result['distance_km'] = round(routes[0]['distance'] / 1000, 2)
            amap_result['duration_minutes'] = round(routes[0]['duration'] / 60, 1)
            amap_result['tolls'] = routes[0].get('tolls', 0)
            amap_result['cost'] = self._estimate_cost(
                routes[0]['distance'],
                routes[0]['duration'],
                routes[0].get('tolls', 0)
            )
        
        return amap_result
    
    def _estimate_cost(self, distance_m: float, duration_s: float, tolls: float) -> float:
        """
        估算运输成本
        
        Args:
            distance_m: 距离（米）
            duration_s: 时长（秒）
            tolls: 过路费
        
        Returns:
            估算成本（元）
        """
        distance_km = distance_m / 1000
        duration_h = duration_s / 3600
        
        # 成本构成：
        # 1. 油费：约 0.8 元/公里
        fuel_cost = distance_km * 0.8
        
        # 2. 过路费
        toll_cost = tolls
        
        # 3. 人工成本：约 50 元/小时
        labor_cost = duration_h * 50
        
        # 4. 车辆折旧：约 0.3 元/公里
        depreciation = distance_km * 0.3
        
        return round(fuel_cost + toll_cost + labor_cost + depreciation, 2)
    
    def _select_best_route(
        self, 
        local_route: Dict, 
        amap_route: Dict,
        prefer_source: str
    ) -> tuple:
        """
        选择最优路线
        
        Returns:
            (推荐路线, 推荐理由)
        """
        if prefer_source == 'local' and local_route:
            return local_route, '使用本地算法路线（用户偏好）'
        
        if prefer_source == 'amap' and amap_route:
            return amap_route, '使用高德地图路线（用户偏好）'
        
        # 自动选择
        if not local_route and not amap_route:
            return None, '无法获取路线推荐'
        
        if not local_route:
            return amap_route, '使用高德地图路线（本地算法无结果）'
        
        if not amap_route:
            return local_route, '使用本地算法路线（高德地图无结果）'
        
        # 对比选择
        local_cost = local_route.get('cost', float('inf'))
        amap_cost = amap_route.get('cost', float('inf'))
        
        local_time = local_route.get('duration_minutes', float('inf'))
        amap_time = amap_route.get('duration_minutes', float('inf'))
        
        # 综合评分（成本权重0.6，时间权重0.4）
        local_score = local_cost * 0.6 + local_time * 0.4
        amap_score = amap_cost * 0.6 + amap_time * 0.4
        
        if amap_score < local_score * 0.9:  # 高德明显更优（10%以上）
            return amap_route, f'使用高德地图路线（成本更低，预计{amap_cost}元，{amap_time}分钟）'
        elif local_score < amap_score * 0.9:  # 本地明显更优
            return local_route, f'使用本地算法路线（成本更低，预计{local_cost}元，{local_time}分钟）'
        else:
            # 差距不大，优先使用高德（实际路况更准确）
            return amap_route, f'推荐高德地图路线（实时路况更准确，预计{amap_cost}元，{amap_time}分钟）'
    
    def apply_route_to_order(self, order_id: int, route_data: Dict) -> Dict:
        """
        将推荐路线应用到订单
        
        Args:
            order_id: 订单ID
            route_data: 路线数据
        
        Returns:
            更新结果
        """
        order = Order.query.get(order_id)
        if not order:
            return {'success': False, 'error': '订单不存在'}
        
        # 更新订单的预估成本和时间
        order.estimated_cost = route_data.get('cost')
        
        # 可以扩展：创建实际的路线记录
        # route = Route(...)
        # order.recommended_route_id = route.id
        
        db.session.commit()
        
        return {
            'success': True,
            'message': '路线已应用到订单',
            'order': order.to_dict()
        }
    
    def get_available_vehicles_for_route(
        self,
        origin_id: int,
        destination_id: int,
        weight: float = 0,
        volume: float = 0
    ) -> List[Dict]:
        """
        获取适合该路线的可用车辆
        
        Args:
            origin_id: 起点ID
            destination_id: 终点ID
            weight: 货物重量
            volume: 货物体积
        
        Returns:
            可用车辆列表
        """
        query = Vehicle.query.filter_by(status='available')
        
        # 根据载重和体积筛选
        if weight > 0:
            query = query.filter(Vehicle.load_capacity >= weight)
        if volume > 0:
            query = query.filter(Vehicle.volume_capacity >= volume)
        
        vehicles = query.all()
        return [v.to_dict() for v in vehicles]


# 单例实例
_order_route_service = None


def get_order_route_service() -> OrderRouteService:
    """获取订单路线服务实例"""
    global _order_route_service
    if _order_route_service is None:
        _order_route_service = OrderRouteService()
    return _order_route_service
