#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
实时路况服务 - 集成高德地图路况 API
"""

import requests
import math
from datetime import datetime
from flask import current_app


class TrafficService:
    """实时路况服务"""
    
    # 高德地图 API Key
    AMAP_KEY = 'e471e7d99965ef1f1a0d4113f580f5db'
    
    # 路况等级
    TRAFFIC_LEVELS = {
        0: {'name': '未知', 'color': '#999', 'speed_ratio': 1.0},
        1: {'name': '畅通', 'color': '#00ff88', 'speed_ratio': 1.0},
        2: {'name': '基本畅通', 'color': '#88ff00', 'speed_ratio': 0.85},
        3: {'name': '轻度拥堵', 'color': '#ffcc00', 'speed_ratio': 0.6},
        4: {'name': '中度拥堵', 'color': '#ff9900', 'speed_ratio': 0.4},
        5: {'name': '严重拥堵', 'color': '#ff0000', 'speed_ratio': 0.2}
    }
    
    def get_road_traffic(self, city, road_name=None):
        """
        获取道路实时路况
        
        Args:
            city: 城市名称
            road_name: 道路名称（可选）
        
        Returns:
            路况信息
        """
        try:
            url = 'https://restapi.amap.com/v3/traffic/status/road'
            params = {
                'key': self.AMAP_KEY,
                'city': city,
                'name': road_name,
                'extensions': 'all'
            }
            
            response = requests.get(url, params=params, timeout=10)
            data = response.json()
            
            if data.get('status') == '1':
                return {
                    'success': True,
                    'traffic': self._parse_traffic_data(data)
                }
            else:
                return {
                    'success': False,
                    'error': data.get('info', '获取路况失败')
                }
        
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_rectangle_traffic(self, location, level=5):
        """
        获取区域路况（通过坐标范围）
        
        Args:
            location: 左下角经纬度,右上角经纬度 (如: "116.35,39.85,116.45,39.95")
            level: 返回路况等级
        
        Returns:
            路况信息
        """
        try:
            url = 'https://restapi.amap.com/v3/traffic/status/rectangle'
            params = {
                'key': self.AMAP_KEY,
                'rectangle': location,
                'level': level,
                'extensions': 'all'
            }
            
            response = requests.get(url, params=params, timeout=10)
            data = response.json()
            
            if data.get('status') == '1':
                return {
                    'success': True,
                    'traffic': self._parse_rectangle_data(data)
                }
            else:
                return {
                    'success': False,
                    'error': data.get('info', '获取路况失败')
                }
        
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def check_route_traffic(self, origin, destination, waypoints=None):
        """
        检查路线沿途路况
        
        Args:
            origin: 起点 (lng,lat)
            destination: 终点 (lng,lat)
            waypoints: 途经点列表
        
        Returns:
            路线路况信息
        """
        try:
            url = 'https://restapi.amap.com/v3/direction/driving'
            params = {
                'key': self.AMAP_KEY,
                'origin': origin,
                'destination': destination,
                'waypoints': waypoints,
                'extensions': 'all',
                'strategy': 10  # 返回多条路径
            }
            
            response = requests.get(url, params=params, timeout=15)
            data = response.json()
            
            if data.get('status') == '1':
                return self._parse_route_traffic(data)
            else:
                return {
                    'success': False,
                    'error': data.get('info', '获取路线路况失败')
                }
        
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def analyze_traffic_and_avoid(self, origin, destination, waypoints=None, threshold=4):
        """
        分析路况并自动规避拥堵路段
        
        Args:
            origin: 起点 (lng,lat)
            destination: 终点 (lng,lat)
            waypoints: 途经点列表
            threshold: 拥堵阈值（超过此等级触发规避，1-5）
        
        Returns:
            分析结果和推荐路线
        """
        # 获取当前路线及路况
        route_traffic = self.check_route_traffic(origin, destination, waypoints)
        
        if not route_traffic.get('success'):
            return route_traffic
        
        # 分析拥堵路段
        congestions = []
        for i, step in enumerate(route_traffic.get('steps', [])):
            traffic_level = step.get('traffic_level', 0)
            if traffic_level >= threshold:
                congestions.append({
                    'index': i,
                    'road': step.get('road', '未知道路'),
                    'level': traffic_level,
                    'level_name': self.TRAFFIC_LEVELS.get(traffic_level, {}).get('name', '未知'),
                    'description': step.get('instruction', ''),
                    'distance': step.get('distance', 0)
                })
        
        # 如果有拥堵，尝试获取备选路线
        alternatives = []
        if congestions:
            alternatives = self._get_alternative_routes(origin, destination, threshold)
        
        return {
            'success': True,
            'has_congestion': len(congestions) > 0,
            'congestions': congestions,
            'original_route': route_traffic.get('route', {}),
            'alternatives': alternatives,
            'recommendation': self._generate_recommendation(congestions, alternatives)
        }
    
    def _parse_traffic_data(self, data):
        """解析道路路况数据"""
        result = {
            'city': data.get('city', ''),
            'roads': []
        }
        
        for road in data.get('trafficinfo', {}).get('evaluation', []):
            result['roads'].append({
                'name': road.get('name', ''),
                'status': road.get('status', 0),
                'status_name': self.TRAFFIC_LEVELS.get(int(road.get('status', 0)), {}).get('name', '未知'),
                'direction': road.get('direction', ''),
                'angle': road.get('angle', 0),
                'speed': road.get('speed', 0)
            })
        
        return result
    
    def _parse_rectangle_data(self, data):
        """解析区域路况数据"""
        result = {
            'evaluation': data.get('trafficinfo', {}).get('evaluation', {}),
            'roads': []
        }
        
        for road in data.get('trafficinfo', {}).get('roads', []):
            result['roads'].append({
                'name': road.get('name', ''),
                'status': road.get('status', 0),
                'status_name': self.TRAFFIC_LEVELS.get(int(road.get('status', 0)), {}).get('name', '未知'),
                'polyline': road.get('polyline', ''),
                'speed': road.get('speed', 0)
            })
        
        return result
    
    def _parse_route_traffic(self, data):
        """解析路线路况"""
        route = data.get('route', {})
        paths = route.get('paths', [])
        
        if not paths:
            return {'success': False, 'error': '未找到路径'}
        
        result = {
            'success': True,
            'distance': 0,
            'duration': 0,
            'traffic_lights': 0,
            'steps': [],
            'traffic_overview': {
                '畅通': 0,
                '基本畅通': 0,
                '轻度拥堵': 0,
                '中度拥堵': 0,
                '严重拥堵': 0
            }
        }
        
        # 取第一条路径
        path = paths[0]
        result['distance'] = int(path.get('distance', 0))
        result['duration'] = int(path.get('duration', 0))
        result['traffic_lights'] = int(path.get('traffic_light_count', 0))
        
        # 解析每一步的路况
        for step in path.get('steps', []):
            # 获取路况等级
            tmcs = step.get('tmcs', [])
            traffic_level = 0
            if tmcs:
                # 计算平均路况
                total_level = sum(int(tmc.get('status', 0)) for tmc in tmcs)
                traffic_level = min(5, max(1, total_level // len(tmcs) if tmcs else 1))
            
            step_info = {
                'instruction': step.get('instruction', ''),
                'road': step.get('road', ''),
                'distance': int(step.get('distance', 0)),
                'duration': int(step.get('duration', 0)),
                'traffic_level': traffic_level,
                'traffic_name': self.TRAFFIC_LEVELS.get(traffic_level, {}).get('name', '未知'),
                'polyline': step.get('polyline', '')
            }
            
            result['steps'].append(step_info)
            
            # 统计路况分布
            level_name = self.TRAFFIC_LEVELS.get(traffic_level, {}).get('name', '未知')
            if level_name in result['traffic_overview']:
                result['traffic_overview'][level_name] += int(step.get('distance', 0))
        
        result['route'] = {
            'distance': result['distance'],
            'duration': result['duration'],
            'polyline': path.get('polyline', '')
        }
        
        return result
    
    def _get_alternative_routes(self, origin, destination, threshold):
        """获取备选路线（避开拥堵）"""
        try:
            url = 'https://restapi.amap.com/v3/direction/driving'
            
            # 尝试不同的策略
            strategies = [
                {'strategy': 2, 'name': '距离最短'},
                {'strategy': 4, 'name': '躲避拥堵'},
                {'strategy': 6, 'name': '多策略组合'}
            ]
            
            alternatives = []
            
            for strategy in strategies:
                params = {
                    'key': self.AMAP_KEY,
                    'origin': origin,
                    'destination': destination,
                    'strategy': strategy['strategy'],
                    'extensions': 'all'
                }
                
                response = requests.get(url, params=params, timeout=10)
                data = response.json()
                
                if data.get('status') == '1' and data.get('route', {}).get('paths'):
                    path = data['route']['paths'][0]
                    
                    # 检查这条路线的路况
                    traffic_score = self._calculate_traffic_score(path)
                    
                    if traffic_score >= (6 - threshold) * 20:  # 路况评分阈值
                        alternatives.append({
                            'strategy': strategy['name'],
                            'distance': int(path.get('distance', 0)),
                            'duration': int(path.get('duration', 0)),
                            'traffic_lights': int(path.get('traffic_light_count', 0)),
                            'traffic_score': traffic_score,
                            'polyline': path.get('polyline', ''),
                            'tolls': float(path.get('tolls', 0))
                        })
            
            # 按路况评分排序
            alternatives.sort(key=lambda x: x['traffic_score'], reverse=True)
            return alternatives[:3]  # 最多返回3条备选路线
        
        except Exception as e:
            return []
    
    def _calculate_traffic_score(self, path):
        """计算路线的路况评分（满分100）"""
        total_distance = int(path.get('distance', 1))
        weighted_distance = 0
        
        for step in path.get('steps', []):
            tmcs = step.get('tmcs', [])
            distance = int(step.get('distance', 0))
            
            if tmcs:
                # 计算该路段的加权路况
                level_sum = sum(int(tmc.get('status', 1)) for tmc in tmcs)
                avg_level = level_sum / len(tmcs) if tmcs else 1
                
                # 畅通得高分
                weighted_distance += distance * (6 - avg_level) / 5
            else:
                weighted_distance += distance * 0.8  # 默认假设基本畅通
        
        score = (weighted_distance / total_distance) * 100
        return min(100, max(0, score))
    
    def _generate_recommendation(self, congestions, alternatives):
        """生成路况建议"""
        if not congestions:
            return {
                'action': 'proceed',
                'message': '当前路况良好，建议按原路线行驶'
            }
        
        if not alternatives:
            return {
                'action': 'caution',
                'message': f'检测到{len(congestions)}处拥堵路段，暂无更好的备选路线，请谨慎驾驶'
            }
        
        best = alternatives[0]
        return {
            'action': 'reroute',
            'message': f'检测到{len(congestions)}处拥堵路段，建议切换至"{best["strategy"]}"路线',
            'alternative': best,
            'savings': {
                'distance': f'{best["distance"]}米',
                'duration': f'{int(best["duration"]/60)}分钟',
                'traffic_score': f'{best["traffic_score"]:.0f}分'
            }
        }


# 单例实例
_traffic_service = None


def get_traffic_service():
    """获取路况服务实例"""
    global _traffic_service
    if _traffic_service is None:
        _traffic_service = TrafficService()
    return _traffic_service
