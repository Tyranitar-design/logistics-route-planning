"""
多式联运优化服务
- 多种运输方式组合优化（公路、铁路、水路、航空）
- 成本-时间权衡优化
- 路径规划与转运节点选择
- 最后一公里配送优化
"""

import os
import json
import random
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
import pandas as pd


class TransportMode:
    """运输方式配置"""
    
    # 运输方式特性
    MODES = {
        'road': {
            'name': '公路运输',
            'speed_km_h': 60,  # 平均速度 km/h
            'cost_per_km': 3.5,  # 每公里成本
            'fixed_cost': 100,  # 固定成本
            'capacity': 25,  # 载重吨
            'reliability': 0.95,  # 可靠性
            'flexibility': 1.0,  # 灵活性系数
            'co2_per_km': 0.12  # 碳排放 kg/km
        },
        'rail': {
            'name': '铁路运输',
            'speed_km_h': 80,
            'cost_per_km': 1.5,
            'fixed_cost': 500,
            'capacity': 2000,
            'reliability': 0.90,
            'flexibility': 0.6,
            'co2_per_km': 0.03
        },
        'water': {
            'name': '水路运输',
            'speed_km_h': 20,
            'cost_per_km': 0.8,
            'fixed_cost': 800,
            'capacity': 5000,
            'reliability': 0.85,
            'flexibility': 0.4,
            'co2_per_km': 0.02
        },
        'air': {
            'name': '航空运输',
            'speed_km_h': 600,
            'cost_per_km': 15,
            'fixed_cost': 1000,
            'capacity': 50,
            'reliability': 0.92,
            'flexibility': 0.8,
            'co2_per_km': 0.5
        }
    }
    
    @classmethod
    def get_mode(cls, mode: str) -> Dict:
        """获取运输方式信息"""
        return cls.MODES.get(mode, cls.MODES['road'])
    
    @classmethod
    def list_modes(cls) -> List[Dict]:
        """列出所有运输方式"""
        return [{'id': k, **v} for k, v in cls.MODES.items()]


class MultimodalOptimizer:
    """多式联运优化器"""
    
    def __init__(self):
        self.modes = TransportMode
        self.transfer_nodes = {}  # 转运节点
    
    def calculate_transport_cost(
        self,
        distance: float,
        mode: str,
        weight: float = 1.0
    ) -> Dict[str, Any]:
        """计算单一运输方式成本"""
        mode_info = self.modes.get_mode(mode)
        
        # 时间成本
        time_hours = distance / mode_info['speed_km_h']
        
        # 运输成本
        variable_cost = distance * mode_info['cost_per_km'] * (weight / mode_info['capacity'])
        total_cost = mode_info['fixed_cost'] + variable_cost
        
        # 碳排放
        co2_emission = distance * mode_info['co2_per_km']
        
        return {
            'mode': mode,
            'mode_name': mode_info['name'],
            'distance_km': distance,
            'time_hours': round(time_hours, 2),
            'time_days': round(time_hours / 24, 2),
            'cost': round(total_cost, 2),
            'co2_emission_kg': round(co2_emission, 2),
            'reliability': mode_info['reliability']
        }
    
    def optimize_route(
        self,
        origin: str,
        destination: str,
        distance: float,
        weight: float = 1.0,
        time_limit: float = None,
        cost_limit: float = None,
        prefer_green: bool = False
    ) -> Dict[str, Any]:
        """
        优化多式联运路线
        
        Args:
            origin: 起点
            destination: 终点
            distance: 总距离
            weight: 货物重量
            time_limit: 时间限制（小时）
            cost_limit: 成本限制
            prefer_green: 是否优先绿色运输
        """
        # 生成多种方案
        options = self._generate_route_options(distance, weight)
        
        # 筛选符合条件的方案
        valid_options = []
        for opt in options:
            if time_limit and opt['total_time'] > time_limit:
                continue
            if cost_limit and opt['total_cost'] > cost_limit:
                continue
            valid_options.append(opt)
        
        if not valid_options:
            valid_options = options  # 如果没有符合的，返回所有方案
        
        # 排序评分
        for opt in valid_options:
            score = self._calculate_score(opt, time_limit, cost_limit, prefer_green)
            opt['score'] = score
        
        # 按分数排序
        valid_options.sort(key=lambda x: x['score'], reverse=True)
        
        # 最佳方案
        best = valid_options[0]
        
        return {
            'origin': origin,
            'destination': destination,
            'total_distance': distance,
            'weight': weight,
            'best_option': best,
            'all_options': valid_options[:5],  # 返回前5个方案
            'recommendation': self._generate_recommendation(best)
        }
    
    def _generate_route_options(self, distance: float, weight: float) -> List[Dict]:
        """生成路线方案"""
        options = []
        
        # 单一运输方式
        for mode in ['road', 'rail', 'water', 'air']:
            cost_info = self.calculate_transport_cost(distance, mode, weight)
            options.append({
                'type': 'single',
                'modes': [mode],
                'segments': [{
                    'mode': mode,
                    'distance': distance,
                    **cost_info
                }],
                'total_cost': cost_info['cost'],
                'total_time': cost_info['time_hours'],
                'total_co2': cost_info['co2_emission_kg'],
                'transfers': 0
            })
        
        # 多式联运方案（公路+铁路/水路）
        # 假设：首段公路30%，中间段铁路/水路60%，末段公路10%
        for main_mode in ['rail', 'water']:
            road_distance = distance * 0.4
            main_distance = distance * 0.6
            
            road_cost = self.calculate_transport_cost(road_distance, 'road', weight)
            main_cost = self.calculate_transport_cost(main_distance, main_mode, weight)
            
            # 转运成本
            transfer_cost = 200  # 每次转运固定成本
            
            options.append({
                'type': 'multimodal',
                'modes': ['road', main_mode, 'road'],
                'segments': [
                    {'mode': 'road', 'distance': road_distance, **road_cost},
                    {'mode': main_mode, 'distance': main_distance, **main_cost},
                    {'mode': 'road', 'distance': road_distance, **road_cost}
                ],
                'total_cost': road_cost['cost'] + main_cost['cost'] + road_cost['cost'] + transfer_cost * 2,
                'total_time': road_cost['time_hours'] + main_cost['time_hours'] + road_cost['time_hours'] + 4,  # 转运等待4小时
                'total_co2': road_cost['co2_emission_kg'] * 2 + main_cost['co2_emission_kg'],
                'transfers': 2
            })
        
        return options
    
    def _calculate_score(
        self,
        option: Dict,
        time_limit: float,
        cost_limit: float,
        prefer_green: bool
    ) -> float:
        """计算方案评分"""
        # 基础分：成本和时间各占40%
        cost_score = 100 / (option['total_cost'] / 1000)  # 成本越低越好
        time_score = 100 / (option['total_time'] / 24)  # 时间越短越好
        
        # 可靠性分数
        reliability_score = np.mean([
            TransportMode.MODES.get(s['mode'], {}).get('reliability', 0.9)
            for s in option.get('segments', [])
        ]) * 100
        
        # 绿色分数
        green_score = 100 / (option['total_co2'] / 100 + 1) if prefer_green else 50
        
        # 综合评分
        score = (
            cost_score * 0.4 +
            time_score * 0.3 +
            reliability_score * 0.2 +
            green_score * (0.1 if prefer_green else 0)
        )
        
        return round(score, 2)
    
    def _generate_recommendation(self, best: Dict) -> str:
        """生成推荐语"""
        if best['type'] == 'single':
            mode_name = TransportMode.MODES[best['modes'][0]]['name']
            return f"推荐使用{mode_name}，预计 {best['total_time']:.1f} 小时到达，成本 ¥{best['total_cost']:.0f}"
        else:
            mode_names = [TransportMode.MODES[m]['name'] for m in best['modes']]
            return f"推荐多式联运：{' → '.join(mode_names)}，预计 {best['total_time']:.1f} 小时，成本 ¥{best['total_cost']:.0f}"
    
    def find_transfer_nodes(
        self,
        origin: Tuple[float, float],
        destination: Tuple[float, float],
        mode_from: str,
        mode_to: str
    ) -> List[Dict]:
        """
        查找最优转运节点
        
        Args:
            origin: 起点坐标 (lat, lon)
            destination: 终点坐标
            mode_from: 起始运输方式
            mode_to: 目标运输方式
        """
        # 模拟转运节点（实际应从数据库查询）
        # 在起点和终点之间生成候选节点
        
        mid_lat = (origin[0] + destination[0]) / 2
        mid_lon = (origin[1] + destination[1]) / 2
        
        # 生成候选节点
        candidates = [
            {'name': f'转运站{i+1}', 'lat': mid_lat + random.uniform(-0.5, 0.5), 
             'lon': mid_lon + random.uniform(-0.5, 0.5), 'capacity': random.randint(100, 500)}
            for i in range(3)
        ]
        
        # 计算距离成本
        for node in candidates:
            # 到起点的距离
            dist_from_origin = self._haversine(origin, (node['lat'], node['lon']))
            # 到终点的距离
            dist_to_dest = self._haversine((node['lat'], node['lon']), destination)
            
            node['dist_from_origin'] = round(dist_from_origin, 2)
            node['dist_to_dest'] = round(dist_to_dest, 2)
            node['total_detour'] = round(dist_from_origin + dist_to_dest, 2)
        
        # 按总绕行距离排序
        candidates.sort(key=lambda x: x['total_detour'])
        
        return candidates
    
    def _haversine(self, coord1: Tuple[float, float], coord2: Tuple[float, float]) -> float:
        """计算两点间距离（公里）"""
        R = 6371  # 地球半径（公里）
        
        lat1, lon1 = np.radians(coord1)
        lat2, lon2 = np.radians(coord2)
        
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        
        a = np.sin(dlat/2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2)**2
        c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1-a))
        
        return R * c


class LastMileOptimizer:
    """最后一公里配送优化"""
    
    def __init__(self):
        self.vehicle_types = {
            'van': {'capacity': 100, 'cost_per_km': 2.5, 'speed': 40},
            'motorcycle': {'capacity': 20, 'cost_per_km': 1.0, 'speed': 30},
            'bike': {'capacity': 10, 'cost_per_km': 0.5, 'speed': 15},
            'drone': {'capacity': 5, 'cost_per_km': 3.0, 'speed': 50}
        }
    
    def optimize_last_mile(
        self,
        depot: Dict[str, float],
        customers: List[Dict[str, Any]],
        vehicle_type: str = 'van'
    ) -> Dict[str, Any]:
        """
        优化最后一公里配送路线
        
        使用贪心算法 + 2-opt 优化
        
        Args:
            depot: 仓库位置 {'lat': x, 'lon': y}
            customers: 客户列表 [{'id': 1, 'lat': x, 'lon': y, 'demand': d}]
            vehicle_type: 车辆类型
        """
        if not customers:
            return {'error': '无客户数据'}
        
        vehicle = self.vehicle_types.get(vehicle_type, self.vehicle_types['van'])
        
        # 计算距离矩阵
        n = len(customers)
        distances = np.zeros((n+1, n+1))  # 包含仓库
        
        for i in range(n+1):
            for j in range(n+1):
                if i == j:
                    continue
                if i == 0:
                    p1 = (depot['lat'], depot['lon'])
                else:
                    p1 = (customers[i-1]['lat'], customers[i-1]['lon'])
                
                if j == 0:
                    p2 = (depot['lat'], depot['lon'])
                else:
                    p2 = (customers[j-1]['lat'], customers[j-1]['lon'])
                
                distances[i][j] = self._haversine(p1, p2)
        
        # 贪心构建初始解
        route = [0]  # 从仓库开始
        remaining = list(range(1, n+1))
        
        while remaining:
            current = route[-1]
            nearest = min(remaining, key=lambda x: distances[current][x])
            route.append(nearest)
            remaining.remove(nearest)
        
        route.append(0)  # 返回仓库
        
        # 2-opt 优化
        route, improvement = self._two_opt(route, distances)
        
        # 计算路径详情
        total_distance = sum(distances[route[i]][route[i+1]] for i in range(len(route)-1))
        total_time = total_distance / vehicle['speed']
        total_cost = total_distance * vehicle['cost_per_km']
        
        # 构建路径详情
        route_details = []
        for i, node in enumerate(route):
            if node == 0:
                route_details.append({
                    'seq': i,
                    'type': 'depot',
                    'name': '仓库',
                    'lat': depot['lat'],
                    'lon': depot['lon']
                })
            else:
                customer = customers[node-1]
                route_details.append({
                    'seq': i,
                    'type': 'customer',
                    'id': customer.get('id'),
                    'name': customer.get('name', f'客户{node}'),
                    'lat': customer['lat'],
                    'lon': customer['lon'],
                    'demand': customer.get('demand', 1)
                })
        
        return {
            'vehicle_type': vehicle_type,
            'route': route,
            'route_details': route_details,
            'total_distance_km': round(total_distance, 2),
            'total_time_hours': round(total_time, 2),
            'total_cost': round(total_cost, 2),
            'customers_served': n,
            'improvement_from_2opt': round(improvement, 2),
            'optimization_method': 'greedy + 2-opt'
        }
    
    def _two_opt(self, route: List[int], distances: np.ndarray) -> Tuple[List[int], float]:
        """2-opt 局部优化"""
        improved = True
        improvement = 0
        
        while improved:
            improved = False
            for i in range(1, len(route) - 2):
                for j in range(i + 1, len(route) - 1):
                    # 计算交换前后的距离差
                    before = distances[route[i-1]][route[i]] + distances[route[j]][route[j+1]]
                    after = distances[route[i-1]][route[j]] + distances[route[i]][route[j+1]]
                    
                    if after < before:
                        # 执行交换
                        route[i:j+1] = route[i:j+1][::-1]
                        improvement += before - after
                        improved = True
        
        return route, improvement
    
    def _haversine(self, coord1: Tuple[float, float], coord2: Tuple[float, float]) -> float:
        """计算两点间距离"""
        R = 6371
        lat1, lon1 = np.radians(coord1)
        lat2, lon2 = np.radians(coord2)
        
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        
        a = np.sin(dlat/2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2)**2
        c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1-a))
        
        return R * c
    
    def compare_vehicle_options(
        self,
        depot: Dict[str, float],
        customers: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """比较不同车辆类型的效果"""
        results = []
        
        for v_type, v_config in self.vehicle_types.items():
            opt_result = self.optimize_last_mile(depot, customers, v_type)
            
            if 'error' not in opt_result:
                results.append({
                    'vehicle_type': v_type,
                    'config': v_config,
                    'result': opt_result
                })
        
        # 按成本排序
        results.sort(key=lambda x: x['result']['total_cost'])
        
        return {
            'comparison': results,
            'recommendation': f"推荐使用 {results[0]['vehicle_type']}，成本最低 ¥{results[0]['result']['total_cost']:.0f}"
        }
    
    def optimize_multi_vehicle(
        self,
        depot: Dict[str, float],
        customers: List[Dict[str, Any]],
        num_vehicles: int = 3,
        vehicle_capacity: int = 50
    ) -> Dict[str, Any]:
        """
        多车辆配送优化
        
        将客户分配给多辆车辆
        """
        # 使用简单的区域划分（实际应使用更复杂的算法）
        # 按角度划分
        
        n = len(customers)
        routes = [[] for _ in range(num_vehicles)]
        
        # 计算每个客户相对于仓库的角度
        angles = []
        for i, c in enumerate(customers):
            angle = np.arctan2(
                c['lat'] - depot['lat'],
                c['lon'] - depot['lon']
            )
            angles.append((i, angle))
        
        # 按角度排序
        angles.sort(key=lambda x: x[1])
        
        # 分配客户
        for idx, (i, angle) in enumerate(angles):
            vehicle_idx = idx % num_vehicles
            routes[vehicle_idx].append(customers[i])
        
        # 优化每条路线
        optimized_routes = []
        for v_idx, route_customers in enumerate(routes):
            if route_customers:
                opt = self.optimize_last_mile(depot, route_customers, 'van')
                opt['vehicle_id'] = v_idx + 1
                optimized_routes.append(opt)
        
        # 汇总
        total_distance = sum(r['total_distance_km'] for r in optimized_routes)
        total_cost = sum(r['total_cost'] for r in optimized_routes)
        total_time = max(r['total_time_hours'] for r in optimized_routes)  # 最长路线决定总时间
        
        return {
            'routes': optimized_routes,
            'summary': {
                'total_vehicles': num_vehicles,
                'total_customers': n,
                'total_distance_km': round(total_distance, 2),
                'total_cost': round(total_cost, 2),
                'max_route_time_hours': round(total_time, 2)
            }
        }


class MultimodalTransportService:
    """多式联运综合服务"""
    
    def __init__(self):
        self.multimodal = MultimodalOptimizer()
        self.last_mile = LastMileOptimizer()
    
    def plan_shipment(
        self,
        origin: str,
        destination: str,
        distance: float,
        weight: float,
        time_limit: float = None,
        priority: str = 'balanced'
    ) -> Dict[str, Any]:
        """
        综合运输规划
        
        Args:
            priority: 'fast' - 最快, 'cheap' - 最便宜, 'balanced' - 平衡, 'green' - 环保
        """
        # 设置优化偏好
        prefer_green = priority == 'green'
        cost_limit = None if priority == 'fast' else None
        time_limit = time_limit if priority == 'fast' else None
        
        # 多式联运优化
        route_opt = self.multimodal.optimize_route(
            origin, destination, distance, weight,
            time_limit, cost_limit, prefer_green
        )
        
        return {
            'origin': origin,
            'destination': destination,
            'distance': distance,
            'weight': weight,
            'priority': priority,
            'route_plan': route_opt,
            'transport_modes': TransportMode.list_modes()
        }
    
    def estimate_all_modes(
        self,
        distance: float,
        weight: float
    ) -> Dict[str, Any]:
        """估算所有运输方式的成本和时间"""
        estimates = []
        
        for mode in ['road', 'rail', 'water', 'air']:
            cost_info = self.multimodal.calculate_transport_cost(distance, mode, weight)
            estimates.append(cost_info)
        
        return {
            'distance': distance,
            'weight': weight,
            'estimates': estimates,
            'comparison': {
                'cheapest': min(estimates, key=lambda x: x['cost']),
                'fastest': min(estimates, key=lambda x: x['time_hours']),
                'greenest': min(estimates, key=lambda x: x['co2_emission_kg'])
            }
        }


# 全局实例
multimodal_service = MultimodalTransportService()