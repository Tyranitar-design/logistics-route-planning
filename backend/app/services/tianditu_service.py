#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
天地图 API 服务
支持：地理编码、逆地理编码、路线规划（驾车/步行/公交）
官方文档：https://lbs.tianditu.gov.cn/server/guide.html
"""

import requests
import logging
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from flask import current_app

logger = logging.getLogger(__name__)


@dataclass
class TiandituGeocodeResult:
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
class TiandituRouteResult:
    """路线规划结果"""
    success: bool
    distance: float = 0      # 总距离（公里）
    duration: float = 0      # 总时长（秒）
    polyline: List[List[float]] = field(default_factory=list)  # 路线坐标点 [[lng, lat], ...]
    steps: List[Dict] = field(default_factory=list)  # 路段详情
    simple_steps: List[Dict] = field(default_factory=list)  # 简化路段
    toll_status: int = 0     # 是否收费路段
    error: str = None


@dataclass
class TiandituSearchResult:
    """地名搜索结果"""
    success: bool
    items: List[Dict] = field(default_factory=list)
    total: int = 0
    error: str = None


class TiandituService:
    """天地图 API 服务"""
    
    BASE_URL = "http://api.tianditu.gov.cn"
    
    # 路线策略
    STRATEGY_RECOMMEND = '0'     # 推荐路线
    STRATEGY_SHORTEST = '1'      # 最短距离
    STRATEGY_FASTEST = '2'       # 最短时间
    STRATEGY_NO_HIGHWAY = '3'    # 避开高速
    
    def __init__(self, browser_key: str = None, server_key: str = None):
        """
        初始化服务
        
        Args:
            browser_key: 浏览器端 Key（用于前端直接调用）
            server_key: 服务端 Key（用于后端调用）
        """
        self.browser_key = browser_key
        self.server_key = server_key or browser_key
    
    def _get_server_key(self) -> str:
        """获取服务端 Key"""
        return self.server_key
    
    def _get_browser_key(self) -> str:
        """获取浏览器端 Key"""
        return self.browser_key or self.server_key
    
    def _make_request(self, endpoint: str, post_data: Dict = None, 
                      use_server_key: bool = True) -> str:
        """
        发送请求到天地图 API
        
        Args:
            endpoint: API 端点
            post_data: POST 数据
            use_server_key: 是否使用服务端 Key
            
        Returns:
            API 响应内容
        """
        import json
        
        key = self._get_server_key() if use_server_key else self._get_browser_key()
        
        url = f"{self.BASE_URL}/{endpoint}"
        
        params = {
            'postStr': json.dumps(post_data) if post_data else '',
            'type': endpoint,
            'tk': key
        }
        
        try:
            response = requests.get(url, params=params, timeout=30)
            response.encoding = 'utf-8'
            return response.text
        except requests.RequestException as e:
            logger.error(f"天地图 API 请求失败: {e}")
            return f'{{"error": "{str(e)}"}}'
    
    def driving_route(
        self, 
        origin: Tuple[float, float], 
        destination: Tuple[float, float],
        waypoints: List[Tuple[float, float]] = None,
        strategy: str = '0'
    ) -> TiandituRouteResult:
        """
        驾车路线规划
        
        Args:
            origin: 起点 (经度, 纬度)
            destination: 终点 (经度, 纬度)
            waypoints: 途经点列表（可选）
            strategy: 路线策略
                '0' - 推荐路线
                '1' - 最短距离
                '2' - 最短时间
                '3' - 避开高速
                
        Returns:
            路线规划结果
        """
        # 构建请求参数
        orig_str = f"{origin[0]},{origin[1]}"
        dest_str = f"{destination[0]},{destination[1]}"
        
        # 途经点
        mid_str = ''
        if waypoints:
            mid_str = ';'.join([f"{wp[0]},{wp[1]}" for wp in waypoints])
        
        post_data = {
            'orig': orig_str,
            'dest': dest_str,
            'style': strategy
        }
        
        if mid_str:
            post_data['mid'] = mid_str
        
        response_text = self._make_request('drive', post_data, use_server_key=True)
        
        # 解析 XML 响应
        return self._parse_drive_response(response_text)
    
    def _parse_drive_response(self, xml_text: str) -> TiandituRouteResult:
        """
        解析驾车路线规划的 XML 响应
        
        Args:
            xml_text: XML 响应文本
            
        Returns:
            路线规划结果
        """
        try:
            root = ET.fromstring(xml_text)
            
            # 检查是否有错误
            result = root if root.tag == 'result' else root.find('result')
            if result is None:
                return TiandituRouteResult(
                    success=False,
                    error='响应格式错误'
                )
            
            # 解析基本信息
            distance_elem = result.find('distance')
            duration_elem = result.find('duration')
            routelatlon_elem = result.find('routelatlon')
            
            distance = float(distance_elem.text) if distance_elem is not None else 0
            duration = float(duration_elem.text) if duration_elem is not None else 0
            
            # 解析路线坐标点
            polyline = []
            if routelatlon_elem is not None and routelatlon_elem.text:
                coords_str = routelatlon_elem.text.strip()
                coords_list = coords_str.split(';')
                for coord_str in coords_list:
                    parts = coord_str.split(',')
                    if len(parts) >= 2:
                        try:
                            lng = float(parts[0])
                            lat = float(parts[1])
                            polyline.append([lng, lat])
                        except ValueError:
                            continue
            
            # 解析详细路段
            steps = []
            routes_elem = result.find('routes')
            if routes_elem is not None:
                for item in routes_elem.findall('item'):
                    step = {
                        'id': item.get('id'),
                        'instruction': self._get_elem_text(item.find('strguide')),
                        'road_name': self._get_elem_text(item.find('streetName')),
                        'next_road': self._get_elem_text(item.find('nextStreetName')),
                        'toll_status': self._get_elem_text(item.find('tollStatus')),
                        'turn_point': self._get_elem_text(item.find('turnlatlon'))
                    }
                    steps.append(step)
            
            # 解析简化路段
            simple_steps = []
            simple_elem = result.find('simple')
            if simple_elem is not None:
                for item in simple_elem.findall('item'):
                    simple_step = {
                        'id': item.get('id'),
                        'instruction': self._get_elem_text(item.find('strguide')),
                        'street_names': self._get_elem_text(item.find('streetNames')),
                        'distance': self._get_elem_text(item.find('streetDistance')),
                        'segment_number': self._get_elem_text(item.find('segmentNumber'))
                    }
                    simple_steps.append(simple_step)
            
            return TiandituRouteResult(
                success=True,
                distance=distance,
                duration=duration,
                polyline=polyline,
                steps=steps,
                simple_steps=simple_steps
            )
            
        except ET.ParseError as e:
            logger.error(f"XML 解析失败: {e}")
            return TiandituRouteResult(
                success=False,
                error=f'响应解析失败: {str(e)}'
            )
    
    def _get_elem_text(self, elem) -> str:
        """安全获取元素文本"""
        return elem.text if elem is not None and elem.text else ''
    
    def search_poi(
        self, 
        keywords: str, 
        level: int = 12,
        map_bound: str = None,
        query_type: int = 1
    ) -> TiandituSearchResult:
        """
        地名搜索
        
        Args:
            keywords: 搜索关键词
            level: 地图级别（1-18）
            map_bound: 搜索范围（经纬度边界）"minX,minY,maxX,maxY"
            query_type: 查询类型 1-普通搜索 2-周边搜索
            
        Returns:
            搜索结果
        """
        post_data = {
            'key': keywords,
            'level': level,
            'queryType': query_type
        }
        
        if map_bound:
            post_data['mapBound'] = map_bound
        
        response_text = self._make_request('search', post_data)
        
        try:
            import json
            data = json.loads(response_text)
            
            if 'code' in data and data['code'] != 0:
                return TiandituSearchResult(
                    success=False,
                    error=data.get('msg', '搜索失败')
                )
            
            items = data.get('data', [])
            return TiandituSearchResult(
                success=True,
                items=items,
                total=len(items)
            )
            
        except json.JSONDecodeError:
            return TiandituSearchResult(
                success=False,
                error='响应解析失败'
            )
    
    def geocode(self, address: str, city: str = None) -> TiandituGeocodeResult:
        """
        地理编码 - 地址转坐标
        
        Args:
            address: 地址字符串
            city: 城市名称（可选）
            
        Returns:
            地理编码结果
        """
        # 先搜索地址
        keywords = f"{city}{address}" if city else address
        search_result = self.search_poi(keywords)
        
        if not search_result.success or not search_result.items:
            return TiandituGeocodeResult(
                success=False,
                error='未找到匹配的地址'
            )
        
        # 取第一个结果
        first_item = search_result.items[0]
        
        lon = first_item.get('lon')
        lat = first_item.get('lat')
        
        if lon is None or lat is None:
            return TiandituGeocodeResult(
                success=False,
                error='坐标解析失败'
            )
        
        return TiandituGeocodeResult(
            success=True,
            longitude=float(lon),
            latitude=float(lat),
            formatted_address=first_item.get('name', address),
            province=first_item.get('province'),
            city=first_item.get('city'),
            district=first_item.get('county')
        )
    
    def distance_matrix(
        self, 
        origins: List[Tuple[float, float]], 
        destinations: List[Tuple[float, float]],
        strategy: str = '0'
    ) -> Dict:
        """
        批量距离计算
        
        Args:
            origins: 起点列表 [(lng, lat), ...]
            destinations: 终点列表 [(lng, lat), ...]
            strategy: 路线策略
            
        Returns:
            距离矩阵结果
        """
        results = []
        
        for i, origin in enumerate(origins):
            for j, dest in enumerate(destinations):
                route = self.driving_route(origin, dest, strategy=strategy)
                
                results.append({
                    'origin_id': i,
                    'dest_id': j,
                    'distance': route.distance * 1000 if route.success else -1,  # 转为米
                    'duration': route.duration if route.success else -1,
                    'success': route.success
                })
        
        return {
            'success': True,
            'results': results
        }
    
    def get_route_for_frontend(
        self, 
        origin: Tuple[float, float], 
        destination: Tuple[float, float],
        strategy: str = '0'
    ) -> Dict:
        """
        获取适合前端绘制的路线数据
        
        Args:
            origin: 起点 (经度, 纬度)
            destination: 终点 (经度, 纬度)
            strategy: 路线策略
            
        Returns:
            前端友好的路线数据
        """
        route = self.driving_route(origin, destination, strategy=strategy)
        
        if not route.success:
            return {
                'success': False,
                'error': route.error
            }
        
        return {
            'success': True,
            'source': 'tianditu',
            'distance_km': route.distance,
            'duration_minutes': round(route.duration / 60, 1),
            'polyline': route.polyline,  # [[lng, lat], ...] 格式，前端可直接使用
            'steps': route.steps,
            'simple_steps': route.simple_steps,
            'coordinates_count': len(route.polyline)
        }


# 单例实例
_tianditu_service = None


def get_tianditu_service() -> TiandituService:
    """获取天地图服务实例"""
    global _tianditu_service
    if _tianditu_service is None:
        try:
            from flask import current_app
            browser_key = current_app.config.get('TIANDITU_BROWSER_KEY')
            server_key = current_app.config.get('TIANDITU_SERVER_KEY')
            _tianditu_service = TiandituService(browser_key, server_key)
        except:
            # 在应用上下文外使用默认配置
            import os
            browser_key = os.environ.get('TIANDITU_BROWSER_KEY')
            server_key = os.environ.get('TIANDITU_SERVER_KEY')
            _tianditu_service = TiandituService(browser_key, server_key)
    return _tianditu_service
