#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
高德地图 API 服务
支持：地理编码、逆地理编码、路线规划、实时路况
"""

import requests
import logging
import math
import socket
import time
from contextlib import contextmanager
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
    provider: str = 'amap'
    provider_status: str = 'ok'
    degraded: bool = False
    fallback_reason: str = None
    authenticity: Dict = None
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
    provider: str = 'amap'
    provider_status: str = 'ok'
    degraded: bool = False
    fallback_reason: str = None
    authenticity: Dict = None
    error: str = None


@dataclass
class AmapTrafficResult:
    """实时路况结果"""
    success: bool
    status: str = None  # 1-畅通, 2-缓行, 3-拥堵, 4-严重拥堵
    evaluation: str = None  # 路况评价
    roads: List[Dict] = None  # 路段详情
    provider: str = 'amap'
    provider_status: str = 'ok'
    degraded: bool = False
    fallback_reason: str = None
    authenticity: Dict = None
    error: str = None


class AmapService:
    """高德地图 API 服务"""
    
    BASE_URL = "https://restapi.amap.com/v3"
    API_HOST = "restapi.amap.com"
    
    def __init__(self, web_key: str = None, service_key: str = None):
        """
        初始化服务
        
        Args:
            web_key: 高德 Web 服务 API Key
            service_key: 高德 Web 服务 API Key（备用）
        """
        self.web_key = web_key
        self.service_key = service_key
    
    def _get_key(self) -> str:
        """获取有效的 API Key"""
        return self.service_key or self.web_key

    def _build_authenticity(
        self,
        message: str,
        exact_ratio: float = 1.0,
        approx_ratio: float = 0.0,
    ) -> Dict:
        return {
            'mode': 'prefer_real',
            'level': 'A',
            'is_strict': False,
            'allow_fallback': False,
            'has_real_distance': True,
            'has_real_duration': True,
            'used_fallback': False,
            'used_simulation': False,
            'distance_source': 'amap',
            'duration_source': 'amap',
            'exact_ratio': exact_ratio,
            'approx_ratio': approx_ratio,
            'message': message,
        }

    def _build_fallback_authenticity(self, message: str) -> Dict:
        return {
            'mode': 'prefer_real',
            'level': 'C',
            'is_strict': False,
            'allow_fallback': True,
            'has_real_distance': False,
            'has_real_duration': False,
            'used_fallback': True,
            'used_simulation': False,
            'distance_source': 'haversine_corrected',
            'duration_source': 'estimated_speed',
            'exact_ratio': 0.0,
            'approx_ratio': 1.0,
            'message': message,
        }

    def _build_provider_failure(self, reason: str, provider_status: str = 'degraded') -> Dict:
        return {
            'status': '0',
            'info': reason,
            'provider': 'amap',
            'provider_status': provider_status,
            'degraded': True,
            'fallback_reason': reason,
        }

    @contextmanager
    def _prefer_ipv4_for_amap(self):
        original_getaddrinfo = socket.getaddrinfo

        def getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
            records = original_getaddrinfo(host, port, family, type, proto, flags)
            if host == self.API_HOST:
                ipv4_records = [record for record in records if record[0] == socket.AF_INET]
                ipv6_records = [record for record in records if record[0] == socket.AF_INET6]
                if ipv4_records:
                    return ipv4_records + [record for record in records if record[0] not in (socket.AF_INET, socket.AF_INET6)] + ipv6_records
            return records

        socket.getaddrinfo = getaddrinfo
        try:
            yield
        finally:
            socket.getaddrinfo = original_getaddrinfo

    def _haversine_meters(self, origin: Tuple[float, float], destination: Tuple[float, float]) -> float:
        lng1, lat1 = origin
        lng2, lat2 = destination
        radius_m = 6371000
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lng2 - lng1)
        a = (
            math.sin(delta_phi / 2) ** 2
            + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
        )
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return radius_m * c

    def _estimate_driving_route(
        self,
        origin: Tuple[float, float],
        destination: Tuple[float, float],
        waypoints: Optional[List[Tuple[float, float]]] = None,
        strategy: int = 0,
        reason: str = 'AMAP_PROVIDER_UNAVAILABLE',
    ) -> AmapRouteResult:
        points = [origin] + (waypoints or []) + [destination]
        straight_distance = 0.0
        for idx in range(len(points) - 1):
            straight_distance += self._haversine_meters(points[idx], points[idx + 1])

        # 城配/干线混合场景用折线修正系数估算路网距离，避免第三方不可达时页面中断。
        distance = int(round(straight_distance * 1.28))
        average_speed_mps = 55 * 1000 / 3600
        duration = int(round(distance / average_speed_mps)) if distance else 0
        polyline = [[float(lng), float(lat)] for lng, lat in points]
        message = '高德路线服务当前不可达，系统已使用节点坐标和哈弗辛距离进行降级估算；仅用于页面连续展示和应急参考。'

        return AmapRouteResult(
            success=True,
            distance=distance,
            duration=duration,
            tolls=0,
            toll_distance=0,
            steps=[{
                'instruction': '高德路线服务不可达，使用起终点直连估算路线',
                'road': 'fallback-estimated-route',
                'distance': distance,
                'duration': duration,
                'action': None,
                'assistant_action': None,
                'toll_road': False,
            }],
            polyline=polyline,
            traffic_info={
                'available': False,
                'evaluation': '实时路况暂不可用',
                'congestion_ratio': None,
            },
            provider='amap',
            provider_status='degraded',
            degraded=True,
            fallback_reason=reason,
            authenticity=self._build_fallback_authenticity(message),
            error=None,
        )
    
    def _make_request(self, endpoint: str, params: Dict) -> Dict:
        """
        发送请求到高德 API
        
        Args:
            endpoint: API 端点
            params: 请求参数
        
        Returns:
            API 响应
        """
        key = self._get_key()
        if not key:
            return self._build_provider_failure('AMAP_KEY_MISSING', provider_status='unavailable')

        params['key'] = key
        params['output'] = 'json'
        
        url = f"{self.BASE_URL}/{endpoint}"
        
        last_error = None
        for attempt in range(2):
            try:
                with self._prefer_ipv4_for_amap():
                    response = requests.get(url, params=params, timeout=(4, 8))
                response.raise_for_status()
                payload = response.json()
                payload.setdefault('provider', 'amap')
                payload.setdefault('provider_status', 'ok' if payload.get('status') == '1' else 'degraded')
                payload.setdefault('degraded', payload.get('status') != '1')
                payload.setdefault('fallback_reason', None if payload.get('status') == '1' else payload.get('info'))
                return payload
            except requests.RequestException as e:
                last_error = e
                logger.warning(f"高德 API 请求失败，第 {attempt + 1} 次: {e}")
                if attempt == 0:
                    time.sleep(0.3)

        logger.error(f"高德 API 请求最终失败: {last_error}")
        return self._build_provider_failure(str(last_error))
    
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
                provider='amap',
                provider_status=result.get('provider_status', 'degraded'),
                degraded=True,
                fallback_reason=result.get('fallback_reason') or result.get('info', '地理编码失败'),
                authenticity=self._build_authenticity('地理编码来自高德官方地理编码服务。'),
                error=result.get('info', '地理编码失败')
            )
        
        geocodes = result.get('geocodes', [])
        if not geocodes:
            return AmapGeocodeResult(
                success=False,
                provider='amap',
                provider_status='degraded',
                degraded=True,
                fallback_reason='AMAP_GEOCODE_EMPTY',
                authenticity=self._build_authenticity('地理编码来自高德官方地理编码服务。'),
                error='未找到匹配的坐标'
            )
        
        geo = geocodes[0]
        location = geo.get('location', '').split(',')
        
        if len(location) != 2:
            return AmapGeocodeResult(
                success=False,
                provider='amap',
                provider_status='degraded',
                degraded=True,
                fallback_reason='AMAP_GEOCODE_LOCATION_INVALID',
                authenticity=self._build_authenticity('地理编码来自高德官方地理编码服务。'),
                error='坐标解析失败'
            )
        
        return AmapGeocodeResult(
            success=True,
            longitude=float(location[0]),
            latitude=float(location[1]),
            formatted_address=geo.get('formatted_address'),
            province=geo.get('province'),
            city=geo.get('city'),
            district=geo.get('district'),
            provider='amap',
            provider_status='ok',
            degraded=False,
            fallback_reason=None,
            authenticity=self._build_authenticity('地理编码来自高德官方地理编码服务。')
        )
    
    def place_text_search(self, keywords: str, city: str = None, types: str = None) -> AmapGeocodeResult:
        """POI 关键词搜索（place/text），返回第一个 POI 坐标。

        用于 geocode 失败的地名（如"大兴安岭"等非常规地址）。
        """
        params = {"keywords": keywords, "offset": 1, "page": 1, "extensions": "base"}
        if city:
            params["city"] = city
        if types:
            params["types"] = types
        result = self._make_request("place/text", params)
        if result.get("status") != "1":
            return AmapGeocodeResult(
                success=False, provider="amap", provider_status=result.get("provider_status", "degraded"),
                degraded=True, fallback_reason=result.get("fallback_reason") or result.get("info", "POI 搜索失败"),
                authenticity=self._build_authenticity("POI 搜索来自高德官方。"),
                error=result.get("info", "POI 搜索失败"),
            )
        pois = result.get("pois", [])
        if not pois:
            return AmapGeocodeResult(
                success=False, provider="amap", provider_status="degraded",
                degraded=True, fallback_reason="AMAP_POI_EMPTY",
                authenticity=self._build_authenticity("POI 搜索来自高德官方。"),
                error="未找到 POI",
            )
        poi = pois[0]
        location = str(poi.get("location", "")).split(",")
        if len(location) != 2:
            return AmapGeocodeResult(
                success=False, provider="amap", provider_status="degraded",
                degraded=True, fallback_reason="AMAP_POI_LOCATION_INVALID",
                authenticity=self._build_authenticity("POI 搜索来自高德官方。"),
                error="POI 坐标解析失败",
            )
        return AmapGeocodeResult(
            success=True, longitude=float(location[0]), latitude=float(location[1]),
            formatted_address=poi.get("name") or poi.get("address"),
            province=poi.get("pname"), city=poi.get("cityname"), district=poi.get("adname"),
            provider="amap", provider_status="ok", degraded=False, fallback_reason=None,
            authenticity=self._build_authenticity("POI 搜索来自高德官方。"),
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
                provider='amap',
                provider_status=result.get('provider_status', 'degraded'),
                degraded=True,
                fallback_reason=result.get('fallback_reason') or result.get('info', '逆地理编码失败'),
                authenticity=self._build_authenticity('逆地理编码来自高德官方地理编码服务。'),
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
            district=address_component.get('district'),
            provider='amap',
            provider_status='ok',
            degraded=False,
            fallback_reason=None,
            authenticity=self._build_authenticity('逆地理编码来自高德官方地理编码服务。')
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
            return self._estimate_driving_route(
                origin,
                destination,
                waypoints,
                strategy,
                result.get('fallback_reason') or result.get('info', '路线规划失败'),
            )
        
        route = result.get('route', {})
        paths = route.get('paths', [])
        
        if not paths:
            return self._estimate_driving_route(origin, destination, waypoints, strategy, 'AMAP_NO_ROUTE')
        
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
            traffic_info=traffic_info if show_traffic else None,
            provider='amap',
            provider_status='ok',
            degraded=False,
            fallback_reason=None,
            authenticity=self._build_authenticity(f'路线来自高德真实路网路线服务（策略：{strategy}）。')
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
            fallback = self._estimate_driving_route(
                origin,
                destination,
                None,
                5,
                result.get('fallback_reason') or result.get('info', '路线规划失败'),
            )
            return {
                'success': True,
                'routes': [{
                    'route_index': 0,
                    'distance': fallback.distance,
                    'duration': fallback.duration,
                    'tolls': fallback.tolls,
                    'strategy': 'fallback_estimated',
                    'toll_distance': fallback.toll_distance,
                    'steps_count': len(fallback.steps or []),
                    'distance_km': round(fallback.distance / 1000, 2),
                    'duration_minutes': round(fallback.duration / 60, 1),
                    'provider': 'amap',
                    'provider_status': 'degraded',
                    'degraded': True,
                    'fallback_reason': fallback.fallback_reason,
                    'authenticity': fallback.authenticity,
                    'main_roads': ['fallback-estimated-route'],
                    'polyline': fallback.polyline,
                }],
                'total_count': 1,
                'provider': 'amap',
                'provider_status': result.get('provider_status', 'degraded'),
                'degraded': True,
                'fallback_reason': result.get('fallback_reason') or result.get('info', '路线规划失败'),
                'authenticity': fallback.authenticity,
            }
        
        route = result.get('route', {})
        paths = route.get('paths', [])
        
        routes = []
        for idx, path in enumerate(paths):
            route_info = {
                'route_index': idx,
                'distance': int(path.get('distance', 0)),
                'duration': int(path.get('duration', 0)),
                'tolls': float(path.get('tolls', 0)),
                'strategy': path.get('strategy'),
                'toll_distance': int(path.get('toll_distance', 0)),
                'steps_count': len(path.get('steps', [])),
                'distance_km': round(int(path.get('distance', 0)) / 1000, 2),
                'duration_minutes': round(int(path.get('duration', 0)) / 60, 1),
                'provider': 'amap',
                'provider_status': 'ok',
                'degraded': False,
                'fallback_reason': None,
                'authenticity': self._build_authenticity(f'路线{idx + 1}来自高德真实路网路线服务。'),
            }
            
            # 提取简要路段信息
            roads = []
            polyline_points = []
            for step in path.get('steps', []):
                if step.get('road'):
                    roads.append(step.get('road'))
                polyline_str = step.get('polyline', '')
                if polyline_str:
                    for point_str in polyline_str.split(';'):
                        coords = point_str.split(',')
                        if len(coords) >= 2:
                            polyline_points.append([float(coords[0]), float(coords[1])])
            route_info['main_roads'] = list(set(roads))[:5]
            route_info['polyline'] = polyline_points if polyline_points else None
            
            routes.append(route_info)
        
        return {
            'success': True,
            'routes': routes,
            'total_count': len(routes),
            'provider': 'amap',
            'provider_status': 'ok',
            'degraded': False,
            'fallback_reason': None,
            'authenticity': self._build_authenticity('多路线结果均来自高德真实路网路线服务。'),
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
                provider='amap',
                provider_status=result.get('provider_status', 'degraded'),
                degraded=True,
                fallback_reason=result.get('fallback_reason') or result.get('info', '路况查询失败'),
                authenticity=self._build_authenticity('路况结果来自高德官方路况服务。'),
                error=result.get('info', '路况查询失败')
            )
        
        traffic = result.get('trafficinfo', {})
        evaluation = traffic.get('evaluation', {})
        
        return AmapTrafficResult(
            success=True,
            status=evaluation.get('status'),
            evaluation=evaluation.get('description'),
            roads=traffic.get('roads', []),
            provider='amap',
            provider_status='ok',
            degraded=False,
            fallback_reason=None,
            authenticity=self._build_authenticity('路况结果来自高德官方路况服务。')
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
        end_point = (simplified[-1][0], simplified[-1][1])
        
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
        
        高德距离接口更稳的调用方式是：
        - 多起点 × 单终点
        - 多终点场景在服务层逐终点拆分调用，再聚合结果
        
        Args:
            origins: 起点列表
            destinations: 终点列表
            strategy: 路线策略
        
        Returns:
            {
                'success': bool,
                'results': [
                    {
                        'origin_id': '1',
                        'dest_id': '1',
                        'distance': 123,
                        'duration': 456
                    },
                    ...
                ]
            }
        """
        if not origins or not destinations:
            return {
                'success': False,
                'error': 'origins/destinations 不能为空',
                'provider': 'amap',
                'provider_status': 'degraded',
                'degraded': True,
                'fallback_reason': 'EMPTY_DISTANCE_MATRIX_INPUT',
                'authenticity': self._build_authenticity('距离矩阵来自高德官方距离服务。'),
            }

        origin_strs = [f"{o[0]},{o[1]}" for o in origins]
        results = []

        for dest_idx, dest in enumerate(destinations, start=1):
            params = {
                'origins': '|'.join(origin_strs),
                'destination': f"{dest[0]},{dest[1]}",
                'type': '1',  # 驾车距离
                'strategy': strategy
            }

            result = self._make_request('distance', params)

            if result.get('status') != '1':
                for origin_idx, source in enumerate(origins, start=1):
                    estimated_distance = int(round(self._haversine_meters(source, dest) * 1.28))
                    estimated_duration = int(round(estimated_distance / (55 * 1000 / 3600))) if estimated_distance else 0
                    results.append({
                        'origin_id': str(origin_idx),
                        'dest_id': str(dest_idx),
                        'distance': estimated_distance,
                        'duration': estimated_duration,
                        'degraded': True,
                    })
                continue

            raw_results = result.get('results', []) or []
            for origin_idx, item in enumerate(raw_results, start=1):
                results.append({
                    'origin_id': item.get('origin_id') or str(origin_idx),
                    'dest_id': item.get('dest_id') or str(dest_idx),
                    'distance': int(item.get('distance', 0)),
                    'duration': int(item.get('duration', 0))
                })

        degraded = any(item.get('degraded') for item in results)
        if degraded:
            return {
                'success': True,
                'results': results,
                'provider': 'amap',
                'provider_status': 'degraded',
                'degraded': True,
                'fallback_reason': 'AMAP_DISTANCE_PROVIDER_UNAVAILABLE',
                'authenticity': self._build_fallback_authenticity(
                    '高德距离矩阵服务当前不可达，系统已使用节点坐标和哈弗辛距离进行降级估算。'
                ),
            }

        return {
            'success': True,
            'results': results,
            'provider': 'amap',
            'provider_status': 'ok',
            'degraded': False,
            'fallback_reason': None,
            'authenticity': self._build_authenticity('距离矩阵来自高德官方距离服务。'),
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
        from app.services.provider_key_resolver import get_amap_keys
        keys = get_amap_keys()
        _amap_service = AmapService(keys.get('web_key'), keys.get('service_key'))
    return _amap_service
