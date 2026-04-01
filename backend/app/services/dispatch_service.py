#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
智能调度服务
自动分配订单到最优车辆，支持多种调度策略
"""

import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass
from app.models import db
from app.models import Order, Vehicle, Node, Route
from app.services.path_algorithm import get_path_service

logger = logging.getLogger(__name__)


@dataclass
class DispatchResult:
    """调度结果"""
    success: bool
    order_id: int
    vehicle_id: int = None
    vehicle_plate: str = None
    estimated_arrival: float = None  # 预计到达时间（分钟）
    estimated_cost: float = None
    route_info: Dict = None
    reason: str = None
    error: str = None


@dataclass
class VehicleScore:
    """车辆评分"""
    vehicle_id: int
    plate_number: str
    score: float
    distance: float
    capacity_match: bool
    current_load: float


class DispatchService:
    """智能调度服务"""
    
    # 调度策略
    STRATEGY_NEAREST = 'nearest'          # 最近优先
    STRATEGY_CAPACITY = 'capacity'        # 容量优先
    STRATEGY_COST = 'cost'               # 成本优先
    STRATEGY_BALANCED = 'balanced'        # 均衡策略
    
    def __init__(self):
        self._strategy = self.STRATEGY_BALANCED
        
    def set_strategy(self, strategy: str):
        """设置调度策略"""
        if strategy in [self.STRATEGY_NEAREST, self.STRATEGY_CAPACITY, 
                        self.STRATEGY_COST, self.STRATEGY_BALANCED]:
            self._strategy = strategy
            
    def dispatch_order(self, order_id: int, vehicle_id: int = None) -> DispatchResult:
        """
        调度订单
        
        Args:
            order_id: 订单ID
            vehicle_id: 指定车辆ID（可选，不指定则自动选择）
        
        Returns:
            调度结果
        """
        order = Order.query.get(order_id)
        if not order:
            return DispatchResult(success=False, order_id=order_id, error='订单不存在')
        
        if order.status not in ['pending', 'assigned']:
            return DispatchResult(success=False, order_id=order_id, error='订单状态不允许调度')
        
        # 获取取货点和送货点
        pickup_node = Node.query.get(order.pickup_node_id)
        delivery_node = Node.query.get(order.delivery_node_id)
        
        if not pickup_node or not delivery_node:
            return DispatchResult(success=False, order_id=order_id, error='订单节点信息不完整')
        
        # 获取可用车辆
        if vehicle_id:
            vehicle = Vehicle.query.get(vehicle_id)
            if not vehicle:
                return DispatchResult(success=False, order_id=order_id, error='指定车辆不存在')
            if vehicle.status != 'available':
                return DispatchResult(success=False, order_id=order_id, error='指定车辆不可用')
            candidates = [vehicle]
        else:
            candidates = self._get_available_vehicles(order.weight, order.volume)
            
        if not candidates:
            return DispatchResult(success=False, order_id=order_id, error='没有可用车辆')
        
        # 根据策略选择最优车辆
        best_vehicle = self._select_best_vehicle(
            candidates, pickup_node, delivery_node, order.weight, order.volume
        )
        
        if not best_vehicle:
            return DispatchResult(success=False, order_id=order_id, error='无法找到合适车辆')
        
        # 计算路线
        try:
            path_service = get_path_service()
            route_result = path_service.dijkstra(
                pickup_node.id, delivery_node.id, 'comprehensive'
            )
            
            if route_result.success:
                route_info = {
                    'distance_km': route_result.total_distance,
                    'duration_minutes': route_result.total_time * 60,
                    'cost': route_result.total_cost,
                    'path': route_result.path
                }
            else:
                route_info = None
                
        except Exception as e:
            logger.warning(f"计算路线失败: {e}")
            route_info = None
        
        # 更新订单和车辆状态
        order.vehicle_id = best_vehicle.id
        order.status = 'assigned'
        order.assigned_at = datetime.utcnow()
        
        best_vehicle.status = 'busy'
        
        db.session.commit()
        
        return DispatchResult(
            success=True,
            order_id=order_id,
            vehicle_id=best_vehicle.id,
            vehicle_plate=best_vehicle.plate_number,
            estimated_arrival=route_info['duration_minutes'] if route_info else None,
            estimated_cost=route_info['cost'] if route_info else None,
            route_info=route_info,
            reason=f'已分配到车辆 {best_vehicle.plate_number}'
        )
        
    def batch_dispatch(self, order_ids: List[int]) -> List[DispatchResult]:
        """批量调度订单"""
        results = []
        for order_id in order_ids:
            result = self.dispatch_order(order_id)
            results.append(result)
        return results
    
    def auto_dispatch_pending_orders(self) -> List[DispatchResult]:
        """自动调度所有待处理订单"""
        pending_orders = Order.query.filter_by(status='pending').all()
        results = []
        for order in pending_orders:
            result = self.dispatch_order(order.id)
            results.append(result)
        return results
    
    def _get_available_vehicles(self, weight: float = 0, volume: float = 0) -> List[Vehicle]:
        """获取满足条件的可用车辆"""
        query = Vehicle.query.filter_by(status='available')
        
        if weight > 0:
            query = query.filter(Vehicle.load_capacity >= weight)
        if volume > 0:
            query = query.filter(Vehicle.volume_capacity >= volume)
            
        return query.all()
    
    def _select_best_vehicle(
        self, 
        vehicles: List[Vehicle], 
        pickup: Node, 
        delivery: Node,
        weight: float,
        volume: float
    ) -> Optional[Vehicle]:
        """根据策略选择最优车辆"""
        if not vehicles:
            return None
            
        if self._strategy == self.STRATEGY_NEAREST:
            return self._select_nearest(vehicles, pickup)
        elif self._strategy == self.STRATEGY_CAPACITY:
            return self._select_best_capacity(vehicles, weight, volume)
        elif self._strategy == self.STRATEGY_COST:
            return self._select_lowest_cost(vehicles, pickup, delivery)
        else:
            return self._select_balanced(vehicles, pickup, delivery, weight, volume)
    
    def _select_nearest(self, vehicles: List[Vehicle], pickup: Node) -> Vehicle:
        """选择距离最近的车辆"""
        # 简化：随机返回（实际应该计算车辆当前位置到取货点的距离）
        return vehicles[0] if vehicles else None
    
    def _select_best_capacity(self, vehicles: List[Vehicle], weight: float, volume: float) -> Vehicle:
        """选择容量最匹配的车辆"""
        best = None
        best_diff = float('inf')
        
        for v in vehicles:
            weight_diff = abs(v.load_capacity - weight) if v.load_capacity else 0
            volume_diff = abs(v.volume_capacity - volume) if v.volume_capacity else 0
            total_diff = weight_diff + volume_diff
            
            if total_diff < best_diff:
                best_diff = total_diff
                best = v
                
        return best
    
    def _select_lowest_cost(self, vehicles: List[Vehicle], pickup: Node, delivery: Node) -> Vehicle:
        """选择成本最低的车辆"""
        # 简化：返回第一个
        return vehicles[0] if vehicles else None
    
    def _select_balanced(
        self, 
        vehicles: List[Vehicle], 
        pickup: Node, 
        delivery: Node,
        weight: float,
        volume: float
    ) -> Vehicle:
        """均衡选择（综合考虑距离、容量、成本）"""
        # 简化：返回容量最匹配的
        return self._select_best_capacity(vehicles, weight, volume)
    
    def release_vehicle(self, vehicle_id: int):
        """释放车辆（完成配送后）"""
        vehicle = Vehicle.query.get(vehicle_id)
        if vehicle:
            vehicle.status = 'available'
            db.session.commit()
            
    def get_dispatch_stats(self) -> Dict:
        """获取调度统计"""
        total_orders = Order.query.count()
        pending = Order.query.filter_by(status='pending').count()
        assigned = Order.query.filter_by(status='assigned').count()
        in_transit = Order.query.filter_by(status='in_transit').count()
        
        available_vehicles = Vehicle.query.filter_by(status='available').count()
        busy_vehicles = Vehicle.query.filter_by(status='busy').count()
        
        return {
            'orders': {
                'total': total_orders,
                'pending': pending,
                'assigned': assigned,
                'in_transit': in_transit
            },
            'vehicles': {
                'available': available_vehicles,
                'busy': busy_vehicles
            }
        }
    
    def suggest_merge_orders(
        self, 
        order_ids: List[int] = None, 
        max_merge_distance: float = 50
    ) -> List[Dict]:
        """
        建议可合并的订单
        
        基于地理位置聚类，找出距离相近、适合一起配送的订单
        
        Args:
            order_ids: 指定订单ID列表（可选，默认查询所有待分配订单）
            max_merge_distance: 最大合并距离（公里）
        
        Returns:
            订单聚类列表
        """
        import math
        from collections import defaultdict
        
        # 查询待分配订单
        query = Order.query.filter(Order.status.in_(['pending', 'assigned']))
        if order_ids:
            query = query.filter(Order.id.in_(order_ids))
        
        orders = query.all()
        
        if not orders:
            return []
        
        # 获取订单的取货点信息
        order_nodes = {}
        for order in orders:
            if order.pickup_node_id:
                node = Node.query.get(order.pickup_node_id)
                if node:
                    order_nodes[order.id] = {
                        'order': order,
                        'node': node,
                        'lat': node.latitude,
                        'lng': node.longitude
                    }
        
        if not order_nodes:
            return []
        
        def haversine_distance(lat1, lng1, lat2, lng2):
            """计算两点间的距离（公里）"""
            R = 6371  # 地球半径（公里）
            lat1, lng1, lat2, lng2 = map(math.radians, [lat1, lng1, lat2, lng2])
            dlat = lat2 - lat1
            dlng = lng2 - lng1
            a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng/2)**2
            c = 2 * math.asin(math.sqrt(a))
            return R * c
        
        # 简单聚类：基于距离的贪心算法
        clusters = []
        assigned = set()
        
        order_ids_list = list(order_nodes.keys())
        
        for i, order_id in enumerate(order_ids_list):
            if order_id in assigned:
                continue
            
            info_i = order_nodes[order_id]
            cluster_orders = [info_i['order']]
            cluster_ids = [order_id]
            total_weight = info_i['order'].weight or 0
            total_volume = info_i['order'].volume or 0
            assigned.add(order_id)
            
            # 查找附近的其他订单
            for j in range(i + 1, len(order_ids_list)):
                other_id = order_ids_list[j]
                if other_id in assigned:
                    continue
                
                info_j = order_nodes[other_id]
                distance = haversine_distance(
                    info_i['lat'], info_i['lng'],
                    info_j['lat'], info_j['lng']
                )
                
                if distance <= max_merge_distance:
                    cluster_orders.append(info_j['order'])
                    cluster_ids.append(other_id)
                    total_weight += info_j['order'].weight or 0
                    total_volume += info_j['order'].volume or 0
                    assigned.add(other_id)
            
            # 计算聚类中心
            if cluster_orders:
                avg_lat = sum(order_nodes[oid]['lat'] for oid in cluster_ids) / len(cluster_ids)
                avg_lng = sum(order_nodes[oid]['lng'] for oid in cluster_ids) / len(cluster_ids)
                
                clusters.append({
                    'orders': [
                        {
                            'id': o.id,
                            'order_number': o.order_number,
                            'pickup_address': o.pickup_node.address if o.pickup_node else None,
                            'delivery_address': o.delivery_node.address if o.delivery_node else None,
                            'weight': o.weight,
                            'volume': o.volume
                        }
                        for o in cluster_orders
                    ],
                    'order_ids': cluster_ids,
                    'center': {
                        'latitude': avg_lat,
                        'longitude': avg_lng
                    },
                    'total_weight': total_weight,
                    'total_volume': total_volume,
                    'order_count': len(cluster_orders)
                })
        
        return clusters
    
    def auto_dispatch(
        self,
        order_ids: List[int] = None,
        vehicle_ids: List[int] = None,
        consider_weather: bool = True,
        consider_traffic: bool = True,
        max_orders_per_vehicle: int = 5
    ):
        """
        自动调度
        
        Args:
            order_ids: 订单ID列表（可选）
            vehicle_ids: 车辆ID列表（可选）
            consider_weather: 是否考虑天气
            consider_traffic: 是否考虑路况
            max_orders_per_vehicle: 每车最大订单数
        
        Returns:
            调度结果
        """
        from dataclasses import dataclass
        
        @dataclass
        class PlanResult:
            success: bool
            plans: list = None
            unassigned_orders: list = None
            summary: dict = None
            error: str = None
        
        try:
            # 查询待分配订单
            query = Order.query.filter(Order.status.in_(['pending']))
            if order_ids:
                query = query.filter(Order.id.in_(order_ids))
            orders = query.all()
            
            if not orders:
                return PlanResult(
                    success=True,
                    plans=[],
                    unassigned_orders=[],
                    summary={'message': '没有待分配的订单'}
                )
            
            # 查询可用车辆
            v_query = Vehicle.query.filter(Vehicle.status == 'available')
            if vehicle_ids:
                v_query = v_query.filter(Vehicle.id.in_(vehicle_ids))
            vehicles = v_query.all()
            
            if not vehicles:
                return PlanResult(
                    success=False,
                    error='没有可用的车辆'
                )
            
            # 简单分配策略：轮流分配
            plans = []
            unassigned = []
            
            @dataclass
            class DispatchPlan:
                vehicle_id: int
                vehicle_info: dict
                orders: list
                route_sequence: list
                total_distance: float
                total_duration: float
                total_cost: float
                weather_impact: dict
                score: float
                suggestions: list
            
            vehicle_idx = 0
            for order in orders:
                if vehicle_idx >= len(vehicles):
                    unassigned.append({
                        'id': order.id,
                        'order_number': order.order_number,
                        'reason': '车辆不足'
                    })
                    continue
                
                vehicle = vehicles[vehicle_idx]
                
                # 计算路线距离和成本
                total_distance = 0
                total_duration = 0
                total_cost = 0
                
                # 辅助函数：Haversine距离计算
                def haversine_distance(lat1, lng1, lat2, lng2):
                    import math
                    R = 6371
                    lat1, lng1, lat2, lng2 = map(math.radians, [lat1, lng1, lat2, lng2])
                    dlat = lat2 - lat1
                    dlng = lng2 - lng1
                    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng/2)**2
                    return R * 2 * math.asin(math.sqrt(a))
                
                try:
                    if order.pickup_node_id and order.delivery_node_id:
                        path_service = get_path_service()
                        route_result = path_service.dijkstra(
                            order.pickup_node_id, 
                            order.delivery_node_id, 
                            'comprehensive'
                        )
                        if route_result.success:
                            total_distance = route_result.total_distance
                            total_duration = route_result.total_time * 60  # 转为分钟
                            total_cost = route_result.total_cost
                        else:
                            # 没找到路径，使用直线距离估算
                            if order.pickup_node and order.delivery_node:
                                lat1 = order.pickup_node.latitude or 0
                                lng1 = order.pickup_node.longitude or 0
                                lat2 = order.delivery_node.latitude or 0
                                lng2 = order.delivery_node.longitude or 0
                                
                                if lat1 and lng1 and lat2 and lng2:
                                    total_distance = haversine_distance(lat1, lng1, lat2, lng2)
                                    total_duration = total_distance / 60 * 60  # 假设平均时速60km
                                    total_cost = total_distance * 5  # 假设每公里5元
                except Exception as e:
                    logger.warning(f"计算路线失败: {e}")
                    # 使用估算值
                    if order.pickup_node and order.delivery_node:
                        lat1 = order.pickup_node.latitude or 0
                        lng1 = order.pickup_node.longitude or 0
                        lat2 = order.delivery_node.latitude or 0
                        lng2 = order.delivery_node.longitude or 0
                        
                        if lat1 and lng1 and lat2 and lng2:
                            total_distance = haversine_distance(lat1, lng1, lat2, lng2)
                            total_duration = total_distance / 60 * 60
                            total_cost = total_distance * 5
                
                # 创建调度计划
                plan = DispatchPlan(
                    vehicle_id=vehicle.id,
                    vehicle_info={
                        'id': vehicle.id,
                        'plate_number': vehicle.plate_number,
                        'type': vehicle.vehicle_type,
                        'load_capacity': vehicle.load_capacity
                    },
                    orders=[{
                        'id': order.id,
                        'order_number': order.order_number,
                        'pickup_address': order.pickup_node.address if order.pickup_node else None,
                        'delivery_address': order.delivery_node.address if order.delivery_node else None,
                        'weight': order.weight,
                        'volume': order.volume
                    }],
                    route_sequence=[
                        order.pickup_node.address if order.pickup_node else 'Unknown',
                        order.delivery_node.address if order.delivery_node else 'Unknown'
                    ],
                    total_distance=round(total_distance, 2),
                    total_duration=round(total_duration, 2),
                    total_cost=round(total_cost, 2),
                    weather_impact={},
                    score=80 + (20 if total_distance > 0 else 0),
                    suggestions=[]
                )
                plans.append(plan)
                
                vehicle_idx = (vehicle_idx + 1) % len(vehicles)
            
            # 计算汇总数据
            total_distance_sum = sum(p.total_distance for p in plans)
            total_duration_sum = sum(p.total_duration for p in plans)
            total_cost_sum = sum(p.total_cost for p in plans)
            
            return PlanResult(
                success=True,
                plans=plans,
                unassigned_orders=unassigned,
                summary={
                    'total_orders': len(orders),
                    'assigned_orders': len(plans),
                    'unassigned_orders': len(unassigned),
                    'vehicles_used': min(len(plans), len(vehicles)),
                    'total_distance': round(total_distance_sum, 2),
                    'total_duration': round(total_duration_sum, 2),
                    'total_cost': round(total_cost_sum, 2),
                    'avg_cost_per_order': round(total_cost_sum / len(plans), 2) if plans else 0
                }
            )
            
        except Exception as e:
            logger.error(f"自动调度失败: {e}")
            return PlanResult(success=False, error=str(e))


# 单例实例
_dispatch_service = None


def get_dispatch_service() -> DispatchService:
    """获取调度服务实例"""
    global _dispatch_service
    if _dispatch_service is None:
        _dispatch_service = DispatchService()
    return _dispatch_service
