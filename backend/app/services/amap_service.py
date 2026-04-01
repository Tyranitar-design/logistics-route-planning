#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
高德地图 API 服务
支持：地理编码、逆地理编码、路线规划、实时路况
"""

import requests
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from flask import current_app

logger = logging.getLogger(__name__)


@dataclass
class AmapGeocodeResult:
    """地理编码结果"""
    success: bool
    longitude: float = None
    latitude: float = None
    formatted_address: str = None
    province: str = None
    city: str = None
    district: str = None
    error: str = None


@dataclass
class AmapRouteResult:
    """路线规划结果"""
    success: bool
    distance: float = 0  # 米
    duration: float = 0  # 秒
    tolls: float = 0     # 过路费（元）
    toll_distance: float = 0  # 收费路段距离（米）
    steps: List[Dict] = None  # 路段详情
    polyline: List[List[float]] = None  # 路线坐标点
    traffic_info: Dict = None  # 路况信息
    error: str = None


@dataclass
class AmapTrafficResult:
    """实时路况结果"""
    success: bool
    status: str = None  # 1-畅通, 2-缓行, 3-拥堵, 4-严重拥堵
    evaluation: str = None  # 路况评价
    roads: List[Dict] = None  # 路段详情
    error: str = None


class AmapService:
    """高德地图 API 服务"""
    
    BASE_URL = "https://restapi.amap.com/v3"
    
    def __init__(self, web_key: str = None, service_key: str = None):
        """
        初始化服务
        
        Args:
            web_key: 高德 Web 服务 API Key
            service_key: 高德 Web 服务 API Key（备用）
        """
        self.web_key = web_key
        self.service_key = service_key or web_key
    
    def _get_key(self) -> str:
        """获取有效的 API Key"""
        return self.web_key or self.service_key
    
    def _make_request(self, endpoint: str, params: Dict) -> Dict:
        """
        发送请求到高德 API
        
        Args:
            endpoint: API 端点
            params: 请求参数
        
        Returns:
            API 响应
        """
        params['key'] = self._get_key()
        params['output'] = 'json'
        
        url = f"{self.BASE_URL}/{endpoint}"
        
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"高德 API 请求失败: {e}")
            return {'status': '0', 'info': str(e)}
    
    def geocode(self, address: str, city: str = None) -> AmapGeocodeResult:
        """
        地理编码 - 地址转坐标
        
        Args:
            address: 地址字符串
            city: 城市名称（可选，用于提高精度）
        
        Returns:
            地理编码结果
        """
        params = {'address': address}
        if city:
            params['city'] = city
        
        result = self._make_request('geocode/geo', params)
        
        if result.get('status') != '1':
            return AmapGeocodeResult(
                success=False,
                error=result.get('info', '地理编码失败')
            )
        
        geocodes = result.get('geocodes', [])
        if not geocodes:
            return AmapGeocodeResult(
                success=False,
                error='未找到匹配的坐标'
            )
        
        geo = geocodes[0]
        location = geo.get('location', '').split(',')
        
        if len(location) != 2:
            return AmapGeocodeResult(
                success=False,
                error='坐标解析失败'
            )
        
        return AmapGeocodeResult(
            success=True,
            longitude=float(location[0]),
            latitude=float(location[1]),
            formatted_address=geo.get('formatted_address'),
            province=geo.get('province'),
            city=geo.get('city'),
            district=geo.get('district')
        )
    
    def regeocode(self, longitude: float, latitude: float) -> AmapGeocodeResult:
        """
        逆地理编码 - 坐标转地址
        
        Args:
            longitude: 经度
            latitude: 纬度
        
        Returns:
            逆地理编码结果
        """
        params = {'location': f"{longitude},{latitude}"}
        
        result = self._make_request('geocode/regeo', params)
        
        if result.get('status') != '1':
            return AmapGeocodeResult(
                success=False,
                error=result.get('info', '逆地理编码失败')
            )
        
        regeocode = result.get('regeocode', {})
        address_component = regeocode.get('addressComponent', {})
        
        return AmapGeocodeResult(
            success=True,
            longitude=longitude,
            latitude=latitude,
            formatted_address=regeocode.get('formatted_address'),
            province=address_component.get('province'),
            city=address_component.get('city'),
            district=address_component.get('district')
        )
    
    def driving_route(
        self,
        origin: Tuple[float, float],
        destination: Tuple[float, float],
        waypoints: List[Tuple[float, float]] = None,
        strategy: int = 0,
        show_traffic: bool = True
    ) -> AmapRouteResult:
        """
        驾车路线规划
        
        Args:
            origin: 起点 (经度, 纬度)
            destination: 终点 (经度, 纬度)
            waypoints: 途经点列表（最多16个）
            strategy: 路线策略
                0-速度优先（时间）
                1-费用优先（不走收费路段的最快道路）
                2-距离优先（最短距离）
                3-不走高速
                4-躲避拥堵
                5-多策略（同时使用速度优先、费用优先、距离优先）
                6-不走高速且避免收费
                7-躲避收费和不走高速
                8-躲避拥堵和不走高速
                9-躲避收费和不走高速且躲避拥堵
                10-返回结果会躲避拥堵，路程较远
            show_traffic: 是否返回路况信息
        
        Returns:
            路线规划结果
        """
        params = {
            'origin': f"{origin[0]},{origin[1]}",
            'destination': f"{destination[0]},{destination[1]}",
            'strategy': strategy,
            'extensions': 'all' if show_traffic else 'base'
        }
        
        if waypoints:
            waypoint_strs = [f"{wp[0]},{wp[1]}" for wp in waypoints]
            params['waypoints'] = ';'.join(waypoint_strs)
        
        result = self._make_request('direction/driving', params)
        
        if result.get('status') != '1':
            return AmapRouteResult(
                success=False,
                error=result.get('info', '路线规划失败')
            )
        
        route = result.get('route', {})
        paths = route.get('paths', [])
        
        if not paths:
            return AmapRouteResult(
                success=False,
                error='未找到可用路线'
            )
        
        # 取第一条路线（最优路线）
        path = paths[0]
        
        # 解析路段
        steps = []
        polyline = []
        traffic_info = {}
        
        for step in path.get('steps', []):
            step_info = {
                'instruction': step.get('instruction'),
                'road': step.get('road'),
                'distance': int(step.get('distance', 0)),
                'duration': int(step.get('duration', 0)),
                'action': step.get('action'),
                'assistant_action': step.get('assistant_action'),
                'toll_road': step.get('toll_road', '0') == '1'
            }
            steps.append(step_info)
            
            # 解析坐标点
            polyline_str = step.get('polyline', '')
            if polyline_str:
                points = []
                for point_str in polyline_str.split(';'):
                    coords = point_str.split(',')
                    if len(coords) >= 2:
                        points.append([float(coords[0]), float(coords[1])])
                polyline.extend(points)
            
            # 解析路况信息
            if show_traffic and 'tmcs' in step:
                for tmc in step.get('tmcs', []):
                    road_segment = {
                        'distance': int(tmc.get('distance', 0)),
                        'status': tmc.get('status')  # 1畅通,2缓行,3拥堵,4严重拥堵
                    }
                    if 'traffic_info' not in traffic_info:
                        traffic_info['segments'] = []
                    traffic_info['segments'].append(road_segment)
        
        # 计算整体路况
        if traffic_info.get('segments'):
            total_dist = sum(s['distance'] for s in traffic_info['segments'])
            congestion_dist = sum(
                s['distance'] for s in traffic_info['segments'] 
                if s['status'] in ['3', '4']
            )
            traffic_info['congestion_ratio'] = congestion_dist / total_dist if total_dist > 0 else 0
            traffic_info['evaluation'] = self._evaluate_traffic(traffic_info['congestion_ratio'])
        
        return AmapRouteResult(
            success=True,
            distance=int(path.get('distance', 0)),
            duration=int(path.get('duration', 0)),
            tolls=float(path.get('tolls', 0)),
            toll_distance=int(path.get('toll_distance', 0)),
            steps=steps,
            polyline=polyline,
            traffic_info=traffic_info if show_traffic else None
        )
    
    def multi_route(
        self,
        origin: Tuple[float, float],
        destination: Tuple[float, float]
    ) -> Dict:
        """
        多路线规划（返回多条路线供选择）
        
        Args:
            origin: 起点 (经度, 纬度)
            destination: 终点 (经度, 纬度)
        
        Returns:
            多条路线结果
        """
        params = {
            'origin': f"{origin[0]},{origin[1]}",
            'destination': f"{destination[0]},{destination[1]}",
            'strategy': 5,  # 多策略
            'extensions': 'all'
        }
        
        result = self._make_request('direction/driving', params)
        
        if result.get('status') != '1':
            return {'success': False, 'error': result.get('info', '路线规划失败')}
        
        route = result.get('route', {})
        paths = route.get('paths', [])
        
        routes = []
        for path in paths:
            route_info = {
                'distance': int(path.get('distance', 0)),
                'duration': int(path.get('duration', 0)),
                'tolls': float(path.get('tolls', 0)),
                'strategy': path.get('strategy'),
                'toll_distance': int(path.get('toll_distance', 0)),
                'steps_count': len(path.get('steps', []))
            }
            
            # 提取简要路段信息
            roads = []
            for step in path.get('steps', []):
                if step.get('road'):
                    roads.append(step.get('road'))
            route_info['main_roads'] = list(set(roads))[:5]
            
            routes.append(route_info)
        
        return {
            'success': True,
            'routes': routes,
            'total_count': len(routes)
        }
    
    def traffic_around(
        self,
        center: Tuple[float, float],
        radius: int = 1000
    ) -> AmapTrafficResult:
        """
        获取周边路况
        
        Args:
            center: 中心点 (经度, 纬度)
            radius: 搜索半径（米），最大5000
        
        Returns:
            路况结果
        """
        params = {
            'location': f"{center[0]},{center[1]}",
            'radius': min(radius, 5000),
            'level': 5,  # 道路等级
            'extensions': 'all'
        }
        
        result = self._make_request('traffic/status/around', params)
        
        if result.get('status') != '1':
            return AmapTrafficResult(
                success=False,
                error=result.get('info', '路况查询失败')
            )
        
        traffic = result.get('trafficinfo', {})
        evaluation = traffic.get('evaluation', {})
        
        return AmapTrafficResult(
            success=True,
            status=evaluation.get('status'),
            evaluation=evaluation.get('description'),
            roads=traffic.get('roads', [])
        )
    
    def traffic_on_route(
        self,
        polyline: List[List[float]]
    ) -> Dict:
        """
        获取路线上的路况
        
        Args:
            polyline: 路线坐标点列表 [[lng, lat], ...]
        
        Returns:
            路况信息
        """
        # 简化坐标点（每10个点取1个）
        simplified = polyline[::10] if len(polyline) > 10 else polyline
        
        if len(simplified) < 2:
            return {'success': True, 'traffic': 'unknown'}
        
        # 取起点和终点查询周边路况
        start_point = (simplified[0][0], simplified[0][1])
        end_point = (simplified[-1][0], simplified[-1][-1])
        
        start_traffic = self.traffic_around(start_point, 2000)
        end_traffic = self.traffic_around(end_point, 2000)
        
        return {
            'success': True,
            'start_point': {
                'status': start_traffic.status,
                'evaluation': start_traffic.evaluation
            } if start_traffic.success else None,
            'end_point': {
                'status': end_traffic.status,
                'evaluation': end_traffic.evaluation
            } if end_traffic.success else None
        }
    
    def distance_matrix(
        self,
        origins: List[Tuple[float, float]],
        destinations: List[Tuple[float, float]],
        strategy: int = 0
    ) -> Dict:
        """
        批量距离计算
        
        Args:
            origins: 起点列表
            destinations: 终点列表
            strategy: 路线策略
        
        Returns:
            距离矩阵
        """
        origin_strs = [f"{o[0]},{o[1]}" for o in origins]
        dest_strs = [f"{d[0]},{d[1]}" for d in destinations]
        
        params = {
            'origins': '|'.join(origin_strs),
            'destination': '|'.join(dest_strs),
            'type': '1',  # 驾车距离
            'strategy': strategy
        }
        
        result = self._make_request('distance', params)
        
        if result.get('status') != '1':
            return {'success': False, 'error': result.get('info', '距离计算失败')}
        
        results = []
        for item in result.get('results', []):
            results.append({
                'origin_id': item.get('origin_id'),
                'dest_id': item.get('dest_id'),
                'distance': int(item.get('distance', 0)),
                'duration': int(item.get('duration', 0))
            })
        
        return {
            'success': True,
            'results': results
        }
    
    def _evaluate_traffic(self, congestion_ratio: float) -> str:
        """根据拥堵比例评估路况"""
        if congestion_ratio < 0.1:
            return '畅通'
        elif congestion_ratio < 0.3:
            return '基本畅通'
        elif congestion_ratio < 0.5:
            return '缓行'
        elif congestion_ratio < 0.7:
            return '拥堵'
        else:
            return '严重拥堵'


# 单例实例
_amap_service = None


def get_amap_service() -> AmapService:
    """获取高德地图服务实例"""
    global _amap_service
    if _amap_service is None:
        try:
            from flask import current_app
            web_key = current_app.config.get('AMAP_WEB_KEY')
            service_key = current_app.config.get('AMAP_SERVICE_KEY')
            _amap_service = AmapService(web_key, service_key)
        except:
            # 在应用上下文外使用默认配置
            import os
            web_key = os.environ.get('AMAP_WEB_KEY')
            service_key = os.environ.get('AMAP_SERVICE_KEY')
            _amap_service = AmapService(web_key, service_key)
    return _amap_service
