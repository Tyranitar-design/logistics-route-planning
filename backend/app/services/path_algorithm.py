#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
高级路径规划算法服务
支持 Dijkstra、A*、多目标优化等算法
"""

import math
import heapq
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
from app.models import db
from app.models import Node, Route


class OptimizeTarget(Enum):
    """优化目标"""
    DISTANCE = 'distance'      # 最短距离
    TIME = 'time'              # 最短时间
    COST = 'cost'              # 最低成本
    COMPREHENSIVE = 'comprehensive'  # 综合最优


@dataclass
class PathResult:
    """路径结果"""
    success: bool
    path: List[Dict]
    total_distance: float
    total_time: float
    total_cost: float
    algorithm: str
    optimize_by: str
    visited_nodes: int
    computation_time: float
    error: str = None


class PathAlgorithmService:
    """路径算法服务"""
    
    def __init__(self):
        self.nodes_cache = {}
        self.adjacency_list = {}
        self._load_data()
    
    def _load_data(self):
        """加载节点和路线数据构建图"""
        # 加载所有活跃节点
        nodes = Node.query.filter_by(status='active').all()
        for node in nodes:
            self.nodes_cache[node.id] = {
                'id': node.id,
                'name': node.name,
                'type': node.type,
                'latitude': node.latitude,
                'longitude': node.longitude,
                'address': node.address,
                'province': node.province,
                'city': node.city
            }
        
        # 构建邻接表
        routes = Route.query.filter_by(status='active').all()
        for route in routes:
            if route.start_node_id and route.end_node_id:
                # 正向边
                if route.start_node_id not in self.adjacency_list:
                    self.adjacency_list[route.start_node_id] = []
                self.adjacency_list[route.start_node_id].append({
                    'target': route.end_node_id,
                    'distance': route.distance or self._calculate_direct_distance(
                        route.start_node_id, route.end_node_id
                    ),
                    'time': route.duration or 1.0,
                    'cost': getattr(route, 'total_cost', None) or (route.distance * 0.8 if route.distance else 100.0),
                    'route_id': route.id,
                    'route_name': route.name
                })
                
                # 反向边（假设是双向道路）
                if route.end_node_id not in self.adjacency_list:
                    self.adjacency_list[route.end_node_id] = []
                self.adjacency_list[route.end_node_id].append({
                    'target': route.start_node_id,
                    'distance': route.distance or self._calculate_direct_distance(
                        route.start_node_id, route.end_node_id
                    ),
                    'time': route.duration or 1.0,
                    'cost': getattr(route, 'total_cost', None) or (route.distance * 0.8 if route.distance else 100.0),
                    'route_id': route.id,
                    'route_name': route.name
                })
    
    def _calculate_direct_distance(self, node_id1: int, node_id2: int) -> float:
        """计算两节点之间的直线距离（Haversine公式）"""
        node1 = self.nodes_cache.get(node_id1)
        node2 = self.nodes_cache.get(node_id2)
        
        if not node1 or not node2:
            return float('inf')
        
        lat1, lng1 = float(node1['latitude'] or 0), float(node1['longitude'] or 0)
        lat2, lng2 = float(node2['latitude'] or 0), float(node2['longitude'] or 0)
        
        R = 6371  # 地球半径（公里）
        dlat = math.radians(lat2 - lat1)
        dlng = math.radians(lng2 - lng1)
        a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng/2)**2
        c = 2 * math.asin(math.sqrt(a))
        
        return R * c
    
    def _heuristic(self, node_id: int, target_id: int) -> float:
        """A*算法的启发函数 - 使用直线距离"""
        return self._calculate_direct_distance(node_id, target_id)
    
    def _get_weight(self, edge: Dict, optimize_by: str) -> float:
        """根据优化目标获取边的权重"""
        weight_map = {
            'distance': edge['distance'],
            'time': edge['time'],
            'cost': edge['cost'],
            'comprehensive': edge['distance'] * 0.4 + edge['time'] * 0.3 + edge['cost'] * 0.003
        }
        return weight_map.get(optimize_by, edge['distance'])
    
    def dijkstra(self, start_id: int, end_id: int, optimize_by: str = 'distance') -> PathResult:
        """
        Dijkstra算法 - 经典最短路径算法
        
        时间复杂度: O((V + E) log V)
        特点: 保证找到最优解，适合非负权重图
        """
        import time
        start_time = time.time()
        
        if start_id not in self.nodes_cache or end_id not in self.nodes_cache:
            return PathResult(
                success=False, path=[], total_distance=0, total_time=0, total_cost=0,
                algorithm='Dijkstra', optimize_by=optimize_by, visited_nodes=0,
                computation_time=0, error='起点或终点不存在'
            )
        
        # 初始化
        distances = {node_id: float('inf') for node_id in self.nodes_cache}
        distances[start_id] = 0
        previous = {node_id: None for node_id in self.nodes_cache}
        visited = set()
        visited_count = 0
        
        # 优先队列: (distance, node_id)
        pq = [(0, start_id)]
        
        while pq:
            current_dist, current_id = heapq.heappop(pq)
            
            if current_id in visited:
                continue
            
            visited.add(current_id)
            visited_count += 1
            
            # 到达终点
            if current_id == end_id:
                break
            
            # 遍历邻居
            for edge in self.adjacency_list.get(current_id, []):
                neighbor_id = edge['target']
                if neighbor_id in visited:
                    continue
                
                weight = self._get_weight(edge, optimize_by)
                new_dist = current_dist + weight
                
                if new_dist < distances[neighbor_id]:
                    distances[neighbor_id] = new_dist
                    previous[neighbor_id] = (current_id, edge)
                    heapq.heappush(pq, (new_dist, neighbor_id))
        
        # 构建路径
        if distances[end_id] == float('inf'):
            return PathResult(
                success=False, path=[], total_distance=0, total_time=0, total_cost=0,
                algorithm='Dijkstra', optimize_by=optimize_by, visited_nodes=visited_count,
                computation_time=time.time() - start_time, error='无法找到路径'
            )
        
        # 回溯路径
        path = []
        current = end_id
        total_distance = 0
        total_time = 0
        total_cost = 0
        
        while current is not None:
            node_data = self.nodes_cache.get(current, {})
            path.insert(0, node_data)
            
            prev = previous[current]
            if prev:
                prev_id, edge = prev
                total_distance += edge['distance']
                total_time += edge['time']
                total_cost += edge['cost']
                current = prev_id
            else:
                current = None
        
        return PathResult(
            success=True,
            path=path,
            total_distance=round(total_distance, 2),
            total_time=round(total_time, 2),
            total_cost=round(total_cost, 2),
            algorithm='Dijkstra',
            optimize_by=optimize_by,
            visited_nodes=visited_count,
            computation_time=round(time.time() - start_time, 4)
        )
    
    def a_star(self, start_id: int, end_id: int, optimize_by: str = 'distance') -> PathResult:
        """
        A*算法 - 启发式搜索算法
        
        时间复杂度: O(E) 平均情况
        特点: 使用启发函数引导搜索，通常比Dijkstra更快
        """
        import time
        start_time = time.time()
        
        if start_id not in self.nodes_cache or end_id not in self.nodes_cache:
            return PathResult(
                success=False, path=[], total_distance=0, total_time=0, total_cost=0,
                algorithm='A*', optimize_by=optimize_by, visited_nodes=0,
                computation_time=0, error='起点或终点不存在'
            )
        
        # 初始化
        g_score = {node_id: float('inf') for node_id in self.nodes_cache}
        g_score[start_id] = 0
        
        f_score = {node_id: float('inf') for node_id in self.nodes_cache}
        f_score[start_id] = self._heuristic(start_id, end_id)
        
        previous = {node_id: None for node_id in self.nodes_cache}
        visited = set()
        visited_count = 0
        
        # 优先队列: (f_score, node_id)
        pq = [(f_score[start_id], start_id)]
        
        while pq:
            _, current_id = heapq.heappop(pq)
            
            if current_id in visited:
                continue
            
            visited.add(current_id)
            visited_count += 1
            
            # 到达终点
            if current_id == end_id:
                break
            
            # 遍历邻居
            for edge in self.adjacency_list.get(current_id, []):
                neighbor_id = edge['target']
                if neighbor_id in visited:
                    continue
                
                weight = self._get_weight(edge, optimize_by)
                tentative_g = g_score[current_id] + weight
                
                if tentative_g < g_score[neighbor_id]:
                    g_score[neighbor_id] = tentative_g
                    f_score[neighbor_id] = tentative_g + self._heuristic(neighbor_id, end_id)
                    previous[neighbor_id] = (current_id, edge)
                    heapq.heappush(pq, (f_score[neighbor_id], neighbor_id))
        
        # 构建路径
        if g_score[end_id] == float('inf'):
            return PathResult(
                success=False, path=[], total_distance=0, total_time=0, total_cost=0,
                algorithm='A*', optimize_by=optimize_by, visited_nodes=visited_count,
                computation_time=time.time() - start_time, error='无法找到路径'
            )
        
        # 回溯路径
        path = []
        current = end_id
        total_distance = 0
        total_time = 0
        total_cost = 0
        
        while current is not None:
            node_data = self.nodes_cache.get(current, {})
            path.insert(0, node_data)
            
            prev = previous[current]
            if prev:
                prev_id, edge = prev
                total_distance += edge['distance']
                total_time += edge['time']
                total_cost += edge['cost']
                current = prev_id
            else:
                current = None
        
        return PathResult(
            success=True,
            path=path,
            total_distance=round(total_distance, 2),
            total_time=round(total_time, 2),
            total_cost=round(total_cost, 2),
            algorithm='A*',
            optimize_by=optimize_by,
            visited_nodes=visited_count,
            computation_time=round(time.time() - start_time, 4)
        )
    
    def multi_objective_optimize(
        self, 
        start_id: int, 
        end_id: int,
        weights: Dict[str, float] = None
    ) -> Dict:
        """
        多目标优化 - 同时考虑距离、时间、成本
        
        Args:
            start_id: 起点ID
            end_id: 终点ID
            weights: 各目标的权重 {'distance': 0.4, 'time': 0.3, 'cost': 0.3}
        """
        if weights is None:
            weights = {'distance': 0.4, 'time': 0.3, 'cost': 0.3}
        
        results = {}
        
        # 分别计算三种优化目标的结果
        for target in ['distance', 'time', 'cost']:
            result = self.dijkstra(start_id, end_id, target)
            if result.success:
                results[f'best_{target}'] = {
                    'path': result.path,
                    'distance': result.total_distance,
                    'time': result.total_time,
                    'cost': result.total_cost,
                    'algorithm': result.algorithm
                }
        
        # 计算综合最优
        import time
        start_time = time.time()
        
        # 使用加权和法
        g_score = {node_id: float('inf') for node_id in self.nodes_cache}
        g_score[start_id] = 0
        previous = {node_id: None for node_id in self.nodes_cache}
        visited = set()
        pq = [(0, start_id)]
        
        while pq:
            current_score, current_id = heapq.heappop(pq)
            
            if current_id in visited:
                continue
            
            visited.add(current_id)
            
            if current_id == end_id:
                break
            
            for edge in self.adjacency_list.get(current_id, []):
                neighbor_id = edge['target']
                if neighbor_id in visited:
                    continue
                
                # 加权综合得分
                score = (
                    edge['distance'] * weights.get('distance', 0.4) +
                    edge['time'] * weights.get('time', 0.3) +
                    edge['cost'] * 0.01 * weights.get('cost', 0.3)
                )
                new_score = current_score + score
                
                if new_score < g_score[neighbor_id]:
                    g_score[neighbor_id] = new_score
                    previous[neighbor_id] = (current_id, edge)
                    heapq.heappush(pq, (new_score, neighbor_id))
        
        # 构建综合最优路径
        if g_score[end_id] != float('inf'):
            path = []
            current = end_id
            total_distance = 0
            total_time = 0
            total_cost = 0
            
            while current is not None:
                node_data = self.nodes_cache.get(current, {})
                path.insert(0, node_data)
                
                prev = previous[current]
                if prev:
                    prev_id, edge = prev
                    total_distance += edge['distance']
                    total_time += edge['time']
                    total_cost += edge['cost']
                    current = prev_id
                else:
                    current = None
            
            results['comprehensive_best'] = {
                'path': path,
                'distance': round(total_distance, 2),
                'time': round(total_time, 2),
                'cost': round(total_cost, 2),
                'algorithm': 'Multi-objective Optimization',
                'weights': weights,
                'computation_time': round(time.time() - start_time, 4)
            }
        
        return results
    
    def get_all_routes_between(
        self, 
        start_id: int, 
        end_id: int, 
        max_routes: int = 3
    ) -> List[PathResult]:
        """获取两点之间的多条路线供用户选择"""
        routes = []
        
        # 1. 最短距离
        result = self.dijkstra(start_id, end_id, 'distance')
        if result.success:
            routes.append(result)
        
        # 2. 最短时间
        result = self.a_star(start_id, end_id, 'time')
        if result.success and result.path != routes[0].path if routes else True:
            routes.append(result)
        
        # 3. 最低成本
        result = self.dijkstra(start_id, end_id, 'cost')
        if result.success and result.path not in [r.path for r in routes]:
            routes.append(result)
        
        return routes[:max_routes]


# 单例实例
_path_service = None

def get_path_service() -> PathAlgorithmService:
    """获取路径服务实例"""
    global _path_service
    if _path_service is None:
        _path_service = PathAlgorithmService()
    return _path_service
