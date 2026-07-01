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
from app.models.layered_data import ShipmentFact
from app.services.path_algorithm import get_path_service
from app.services.amap_service import get_amap_service

logger = logging.getLogger(__name__)


@dataclass
class OrderRouteRecommendation:
    """订单路线推荐结果"""
    success: bool
    order_id: int = None
    order_number: str = None
    data_source: str = None
    origin: Dict = None
    destination: Dict = None
    
    # 本地算法结果
    local_route: Dict = None
    
    # 高德地图结果
    amap_route: Dict = None
    
    # 推荐结果
    recommended_route: Dict = None
    recommendation_reason: str = None
    provider_status: str = None
    fallback_reason: str = None
    
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
        data_source = 'manual_nodes'
        order_number = None
        origin_name = None
        destination_name = None
        origin_lng = None
        origin_lat = None
        dest_lng = None
        dest_lat = None

        # 获取节点信息
        if order_id:
            order = Order.query.get(order_id)
            if order:
                data_source = 'orders'
                order_number = order.order_number
                origin_id = order.pickup_node_id
                destination_id = order.delivery_node_id
                # 回退：如果没有节点 ID，用名称构建
                origin_name = order.origin_name
                destination_name = order.destination_name
                origin_lng = order.origin_lng
                origin_lat = order.origin_lat
                dest_lng = order.destination_lng
                dest_lat = order.destination_lat
            else:
                fact = self._find_shipment_fact_order(order_id)
                if not fact:
                    return OrderRouteRecommendation(success=False, error='订单不存在')
                data_source = 'shipment_fact'
                order_number = fact.external_order_id or fact.external_shipment_id or f'SHIP-{fact.id}'
                origin_name = fact.origin_city_std or fact.origin_city_raw
                destination_name = fact.destination_city_std or fact.destination_city_raw
                origin_lng = fact.origin_lng
                origin_lat = fact.origin_lat
                dest_lng = fact.destination_lng
                dest_lat = fact.destination_lat
                weight = weight or fact.weight_kg or 0
                origin_node = self._find_node_by_city(origin_name)
                destination_node = self._find_node_by_city(destination_name)
                origin_id = origin_node.id if origin_node else None
                destination_id = destination_node.id if destination_node else None

        origin = Node.query.get(origin_id) if origin_id else None
        destination = Node.query.get(destination_id) if destination_id else None

        # 构建起点终点信息
        if origin:
            result_origin = origin.to_dict()
            result_origin['coordinate_source'] = 'node'
            if data_source == 'shipment_fact' and origin_lng and origin_lat:
                result_origin['shipment_longitude'] = origin_lng
                result_origin['shipment_latitude'] = origin_lat
        elif origin_name:
            result_origin = {
                'id': None,
                'name': origin_name,
                'longitude': origin_lng,
                'latitude': origin_lat,
                'coordinate_source': data_source,
            }
        else:
            return OrderRouteRecommendation(success=False, error='订单没有设置起点')

        if destination:
            result_dest = destination.to_dict()
            result_dest['coordinate_source'] = 'node'
            if data_source == 'shipment_fact' and dest_lng and dest_lat:
                result_dest['shipment_longitude'] = dest_lng
                result_dest['shipment_latitude'] = dest_lat
        elif destination_name:
            result_dest = {
                'id': None,
                'name': destination_name,
                'longitude': dest_lng,
                'latitude': dest_lat,
                'coordinate_source': data_source,
            }
        else:
            return OrderRouteRecommendation(success=False, error='订单没有设置终点')

        result = OrderRouteRecommendation(
            success=True,
            order_id=order_id,
            order_number=order_number,
            data_source=data_source,
            origin=result_origin,
            destination=result_dest
        )

        # 1. 本地算法路线推荐（仅在有节点 ID 时）
        if origin_id and destination_id:
            try:
                local_result = self._get_local_route(origin_id, destination_id)
                if local_result['success']:
                    result.local_route = local_result
            except Exception as e:
                logger.warning(f"本地算法推荐失败: {e}")

        # 2. 高德地图路线推荐（需要有经纬度）
        amap_origin = self._route_point_for_provider(result_origin)
        amap_destination = self._route_point_for_provider(result_dest)
        if amap_origin.get('longitude') and amap_origin.get('latitude') and amap_destination.get('longitude') and amap_destination.get('latitude'):
            try:
                amap_result = self._get_amap_route(amap_origin, amap_destination)
                if amap_result['success']:
                    result.amap_route = amap_result
            except Exception as e:
                logger.warning(f"高德地图推荐失败: {e}")
        else:
            logger.info("起点或终点缺少经纬度，跳过高德地图推荐")
        
        # 3. 综合推荐
        result.recommended_route, result.recommendation_reason = self._select_best_route(
            result.local_route, 
            result.amap_route,
            prefer_source
        )
        provider_route = result.recommended_route or result.amap_route or result.local_route or {}
        result.provider_status = provider_route.get('provider_status') or provider_route.get('source')
        result.fallback_reason = provider_route.get('fallback_reason')
        
        return result

    def _find_shipment_fact_order(self, order_id: int):
        return ShipmentFact.query.filter(
            db.or_(
                ShipmentFact.id == order_id,
                ShipmentFact.external_order_id == str(order_id),
                ShipmentFact.external_shipment_id == str(order_id),
            )
        ).first()

    @staticmethod
    def _normalize_place_name(value: str) -> str:
        text = (value or '').strip()
        for token in ['市', '特别行政区', '物流节点', '（由真实运单网络自动生成）', '(由真实运单网络自动生成)']:
            text = text.replace(token, '')
        return text.strip()

    def _find_node_by_city(self, city_name: str):
        if not city_name:
            return None

        candidates = []
        for value in [city_name, self._normalize_place_name(city_name)]:
            value = (value or '').strip()
            if value and value not in candidates:
                candidates.append(value)

        for candidate in candidates:
            node = Node.query.filter(
                db.or_(
                    Node.city == candidate,
                    Node.name.contains(candidate),
                    Node.address.contains(candidate),
                )
            ).first()
            if node:
                return node
        return None

    @staticmethod
    def _route_point_for_provider(point: Dict) -> Dict:
        longitude = point.get('shipment_longitude') or point.get('longitude')
        latitude = point.get('shipment_latitude') or point.get('latitude')
        return {
            'id': point.get('id'),
            'name': point.get('name'),
            'longitude': longitude,
            'latitude': latitude,
            'coordinate_source': point.get('coordinate_source'),
        }
    
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
            'provider_status': 'ok',
            'distance_source': 'route_table_or_haversine_fallback',
            'path_source': 'local_route_graph',
            'fallback_reason': None,
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
    
    def _get_amap_route(self, origin, destination) -> Dict:
        """获取高德地图路线（支持 Node 对象或 dict）"""
        # 兼容 Node 对象和 dict
        o_lng = getattr(origin, 'longitude', None) or origin.get('longitude')
        o_lat = getattr(origin, 'latitude', None) or origin.get('latitude')
        d_lng = getattr(destination, 'longitude', None) or destination.get('longitude')
        d_lat = getattr(destination, 'latitude', None) or destination.get('latitude')
        o_name = getattr(origin, 'name', None) or origin.get('name', '未知')
        d_name = getattr(destination, 'name', None) or destination.get('name', '未知')

        if not all([o_lng, o_lat, d_lng, d_lat]):
            return {'success': False, 'error': '起点或终点缺少经纬度'}

        service = get_amap_service()

        result = service.multi_route(
            (o_lng, o_lat),
            (d_lng, d_lat)
        )

        if not result.get('success'):
            return {'success': False, 'error': result.get('error', '高德地图路线规划失败')}

        routes = result.get('routes', [])
        if not routes:
            return {'success': False, 'error': '未找到可用路线'}

        amap_result = {
            'success': True,
            'source': 'amap',
            'provider': result.get('provider'),
            'provider_status': result.get('provider_status'),
            'degraded': result.get('degraded'),
            'fallback_reason': result.get('fallback_reason'),
            'authenticity': result.get('authenticity'),
            'distance_source': 'haversine_corrected' if result.get('degraded') else 'amap_driving_route',
            'path_source': 'fallback_endpoint_polyline' if result.get('degraded') else 'amap_driving_route',
            'routes': [],
            'origin_name': o_name,
            'destination_name': d_name
        }
        
        for i, route in enumerate(routes):
            route_info = {
                'index': i + 1,
                'distance_km': round(route['distance'] / 1000, 2),
                'duration_minutes': round(route['duration'] / 60, 1),
                'tolls': route.get('tolls', 0),
                'toll_distance_km': round(route.get('toll_distance', 0) / 1000, 2),
                'strategy': route.get('strategy'),
                'main_roads': route.get('main_roads', []),
                'provider': route.get('provider', result.get('provider')),
                'provider_status': route.get('provider_status', result.get('provider_status')),
                'degraded': route.get('degraded', result.get('degraded')),
                'fallback_reason': route.get('fallback_reason', result.get('fallback_reason')),
                'authenticity': route.get('authenticity', result.get('authenticity')),
                'distance_source': 'haversine_corrected' if route.get('degraded') else 'amap_driving_route',
                'path_source': 'fallback_endpoint_polyline' if route.get('degraded') else 'amap_driving_route',
                'polyline': route.get('polyline'),
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
            amap_result['polyline'] = routes[0].get('polyline')
        
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
            fact = self._find_shipment_fact_order(order_id)
            if fact:
                return {
                    'success': True,
                    'message': '真实运单保持只读，推荐路线已生成但未写回 shipment_facts',
                    'data_source': 'shipment_fact',
                    'order_id': fact.id,
                    'order_number': fact.external_order_id or fact.external_shipment_id,
                    'applied': False,
                }
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
