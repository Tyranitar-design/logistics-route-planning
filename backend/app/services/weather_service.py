#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
天气服务 - 高德天气 API 集成
支持：实时天气、天气预报、天气对运输影响分析
"""

import requests
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class WeatherCondition(Enum):
    """天气状况"""
    SUNNY = '晴'
    CLOUDY = '多云'
    OVERCAST = '阴'
    LIGHT_RAIN = '小雨'
    MODERATE_RAIN = '中雨'
    HEAVY_RAIN = '大雨'
    RAINSTORM = '暴雨'
    LIGHT_SNOW = '小雪'
    MODERATE_SNOW = '中雪'
    HEAVY_SNOW = '大雪'
    FOG = '雾'
    HAZE = '霾'
    SANDSTORM = '沙尘暴'
    UNKNOWN = '未知'


class TransportImpact(Enum):
    """运输影响等级"""
    NONE = '无影响'
    MINOR = '轻微影响'
    MODERATE = '中度影响'
    SEVERE = '严重影响'
    EXTREME = '极端影响，建议暂停运输'


@dataclass
class WeatherInfo:
    """天气信息"""
    province: str
    city: str
    adcode: str
    weather: str
    temperature: str
    wind_direction: str
    wind_power: str
    humidity: str
    report_time: str
    # 预报数据（可选）
    forecast: List[Dict] = None
    
    def to_dict(self):
        return {
            'province': self.province,
            'city': self.city,
            'adcode': self.adcode,
            'weather': self.weather,
            'temperature': self.temperature,
            'wind_direction': self.wind_direction,
            'wind_power': self.wind_power,
            'humidity': self.humidity,
            'report_time': self.report_time,
            'forecast': self.forecast
        }


@dataclass
class WeatherImpact:
    """天气对运输的影响"""
    impact_level: str
    speed_reduction: float  # 速度降低比例 0-1
    delay_risk: float  # 延误风险 0-1
    safety_warning: str
    suggestions: List[str]
    
    def to_dict(self):
        return {
            'impact_level': self.impact_level,
            'speed_reduction': self.speed_reduction,
            'delay_risk': self.delay_risk,
            'safety_warning': self.safety_warning,
            'suggestions': self.suggestions
        }


class WeatherService:
    """天气服务"""
    
    BASE_URL = "https://restapi.amap.com/v3"
    
    # 天气对运输的影响配置
    WEATHER_IMPACT_CONFIG = {
        # 晴天
        '晴': {'impact': '无影响', 'speed_reduction': 0, 'delay_risk': 0.05},
        '多云': {'impact': '无影响', 'speed_reduction': 0, 'delay_risk': 0.05},
        '阴': {'impact': '无影响', 'speed_reduction': 0, 'delay_risk': 0.1},
        
        # 雨天
        '小雨': {'impact': '轻微影响', 'speed_reduction': 0.1, 'delay_risk': 0.2},
        '中雨': {'impact': '中度影响', 'speed_reduction': 0.2, 'delay_risk': 0.4},
        '大雨': {'impact': '严重影响', 'speed_reduction': 0.3, 'delay_risk': 0.6},
        '暴雨': {'impact': '极端影响，建议暂停运输', 'speed_reduction': 0.5, 'delay_risk': 0.9},
        '大暴雨': {'impact': '极端影响，建议暂停运输', 'speed_reduction': 0.6, 'delay_risk': 0.95},
        '特大暴雨': {'impact': '极端影响，建议暂停运输', 'speed_reduction': 0.7, 'delay_risk': 1.0},
        '阵雨': {'impact': '轻微影响', 'speed_reduction': 0.1, 'delay_risk': 0.15},
        '雷阵雨': {'impact': '中度影响', 'speed_reduction': 0.15, 'delay_risk': 0.3},
        
        # 雪天
        '小雪': {'impact': '轻微影响', 'speed_reduction': 0.15, 'delay_risk': 0.25},
        '中雪': {'impact': '中度影响', 'speed_reduction': 0.25, 'delay_risk': 0.45},
        '大雪': {'impact': '严重影响', 'speed_reduction': 0.4, 'delay_risk': 0.7},
        '暴雪': {'impact': '极端影响，建议暂停运输', 'speed_reduction': 0.6, 'delay_risk': 0.9},
        '雨夹雪': {'impact': '中度影响', 'speed_reduction': 0.2, 'delay_risk': 0.35},
        
        # 特殊天气
        '雾': {'impact': '严重影响', 'speed_reduction': 0.35, 'delay_risk': 0.5},
        '浓雾': {'impact': '极端影响，建议暂停运输', 'speed_reduction': 0.5, 'delay_risk': 0.8},
        '霾': {'impact': '轻微影响', 'speed_reduction': 0.05, 'delay_risk': 0.1},
        '沙尘暴': {'impact': '严重影响', 'speed_reduction': 0.3, 'delay_risk': 0.6},
        '浮尘': {'impact': '轻微影响', 'speed_reduction': 0.05, 'delay_risk': 0.1},
        '扬沙': {'impact': '中度影响', 'speed_reduction': 0.15, 'delay_risk': 0.3},
        
        # 其他
        '台风': {'impact': '极端影响，建议暂停运输', 'speed_reduction': 0.7, 'delay_risk': 0.95},
    }
    
    def __init__(self, api_key: str):
        self.api_key = api_key
    
    def _make_request(self, endpoint: str, params: Dict) -> Dict:
        """发送请求到高德 API"""
        params['key'] = self.api_key
        params['output'] = 'json'
        
        url = f"{self.BASE_URL}/{endpoint}"
        
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"天气 API 请求失败: {e}")
            return {'status': '0', 'info': str(e)}
    
    def get_weather_now(self, city: str) -> Dict:
        """
        获取实时天气
        
        Args:
            city: 城市名称或 adcode（如：北京、110000）
        
        Returns:
            天气信息
        """
        params = {
            'city': city,
            'extensions': 'base'  # base=实况天气, all=预报天气
        }
        
        result = self._make_request('weather/weatherInfo', params)
        
        if result.get('status') != '1':
            return {
                'success': False,
                'error': result.get('info', '天气查询失败')
            }
        
        lives = result.get('lives', [])
        if not lives:
            return {
                'success': False,
                'error': '未获取到天气数据'
            }
        
        live = lives[0]
        
        weather_info = WeatherInfo(
            province=live.get('province', ''),
            city=live.get('city', ''),
            adcode=live.get('adcode', ''),
            weather=live.get('weather', '未知'),
            temperature=live.get('temperature', '0'),
            wind_direction=live.get('winddirection', '未知'),
            wind_power=live.get('windpower', '未知'),
            humidity=live.get('humidity', '0'),
            report_time=live.get('reporttime', '')
        )
        
        return {
            'success': True,
            'data': weather_info.to_dict()
        }
    
    def get_weather_forecast(self, city: str) -> Dict:
        """
        获取天气预报（未来4天）
        
        Args:
            city: 城市名称或 adcode
        
        Returns:
            天气预报信息
        """
        params = {
            'city': city,
            'extensions': 'all'  # 获取预报天气
        }
        
        result = self._make_request('weather/weatherInfo', params)
        
        if result.get('status') != '1':
            return {
                'success': False,
                'error': result.get('info', '天气预报查询失败')
            }
        
        forecasts = result.get('forecasts', [])
        if not forecasts:
            return {
                'success': False,
                'error': '未获取到天气预报数据'
            }
        
        forecast_data = forecasts[0]
        casts = forecast_data.get('casts', [])
        
        forecast_list = []
        for cast in casts:
            day_info = {
                'date': cast.get('date', ''),
                'week': cast.get('week', ''),
                'day_weather': cast.get('dayweather', '未知'),
                'night_weather': cast.get('nightweather', '未知'),
                'day_temp': cast.get('daytemp', '0'),
                'night_temp': cast.get('nighttemp', '0'),
                'day_wind': cast.get('daywind', '未知'),
                'night_wind': cast.get('nightwind', '未知'),
                'day_power': cast.get('daypower', '未知'),
                'night_power': cast.get('nightpower', '未知'),
            }
            forecast_list.append(day_info)
        
        return {
            'success': True,
            'data': {
                'city': forecast_data.get('city', ''),
                'forecast': forecast_list
            }
        }
    
    def analyze_transport_impact(self, weather: str, temperature: str = None) -> WeatherImpact:
        """
        分析天气对运输的影响
        
        Args:
            weather: 天气状况
            temperature: 温度（可选，用于额外判断）
        
        Returns:
            运输影响分析
        """
        # 获取基础影响配置
        config = self.WEATHER_IMPACT_CONFIG.get(weather, {
            'impact': '未知',
            'speed_reduction': 0.1,
            'delay_risk': 0.2
        })
        
        impact_level = config['impact']
        speed_reduction = config['speed_reduction']
        delay_risk = config['delay_risk']
        
        # 根据温度调整（极端温度增加风险）
        temp_adjustments = []
        if temperature:
            try:
                temp = float(temperature)
                if temp >= 35:
                    temp_adjustments.append('高温天气，注意防暑')
                    speed_reduction += 0.05
                    delay_risk += 0.1
                elif temp <= -10:
                    temp_adjustments.append('低温冰冻，道路可能结冰')
                    speed_reduction += 0.1
                    delay_risk += 0.15
                elif temp <= 0:
                    temp_adjustments.append('低温天气，注意防寒保暖')
            except ValueError:
                pass
        
        # 生成建议
        suggestions = self._generate_suggestions(weather, impact_level)
        suggestions.extend(temp_adjustments)
        
        # 安全警告
        safety_warning = self._get_safety_warning(weather, impact_level)
        
        return WeatherImpact(
            impact_level=impact_level,
            speed_reduction=min(speed_reduction, 1.0),
            delay_risk=min(delay_risk, 1.0),
            safety_warning=safety_warning,
            suggestions=suggestions
        )
    
    def _generate_suggestions(self, weather: str, impact_level: str) -> List[str]:
        """生成运输建议"""
        suggestions = []
        
        if impact_level == '无影响':
            suggestions.append('天气良好，可正常运输')
        elif impact_level == '轻微影响':
            suggestions.append('建议适当降低车速，保持安全距离')
        elif impact_level == '中度影响':
            suggestions.append('建议减速慢行，增加行车距离')
            suggestions.append('关注天气变化，必要时选择安全地点暂停')
        elif impact_level == '严重影响':
            suggestions.append('建议暂停运输或选择更安全的路线')
            suggestions.append('如必须运输，请配备专业司机和应急设备')
        elif '极端影响' in impact_level:
            suggestions.append('⚠️ 强烈建议暂停运输！')
            suggestions.append('如遇紧急情况，请联系当地交通部门')
        
        # 特定天气建议
        if '雨' in weather:
            suggestions.append('雨天路滑，注意防滑，开启雾灯')
        if '雪' in weather:
            suggestions.append('雪天路滑，建议使用防滑链')
        if '雾' in weather or '霾' in weather:
            suggestions.append('能见度低，开启雾灯和双闪，保持安全距离')
        if '沙' in weather:
            suggestions.append('沙尘天气，注意保护车辆和货物')
        
        return suggestions
    
    def _get_safety_warning(self, weather: str, impact_level: str) -> str:
        """获取安全警告"""
        warnings = {
            '暴雨': '⚠️ 暴雨预警：可能造成道路积水，能见度降低',
            '大暴雨': '🚨 暴雨红色预警：强烈建议暂停运输',
            '特大暴雨': '🚨 极端天气预警：请立即寻找安全地点避险',
            '暴雪': '🚨 暴雪预警：道路可能封闭，建议暂停运输',
            '雾': '⚠️ 大雾预警：能见度严重降低，请减速慢行',
            '浓雾': '🚨 浓雾预警：能见度极低，建议暂停运输',
            '台风': '🚨 台风预警：强烈建议暂停运输，寻找安全地点避险',
            '沙尘暴': '⚠️ 沙尘暴预警：能见度低，注意保护车辆',
        }
        
        return warnings.get(weather, '')
    
    def get_route_weather(
        self,
        cities: List[str]
    ) -> Dict:
        """
        获取沿途多个城市的天气情况
        
        Args:
            cities: 城市名称列表（如：['北京', '天津', '上海']）
        
        Returns:
            沿途天气信息
        """
        route_weather = []
        
        for city in cities:
            weather_result = self.get_weather_now(city)
            
            if weather_result['success']:
                weather_data = weather_result['data']
                
                # 分析影响
                impact = self.analyze_transport_impact(
                    weather_data['weather'],
                    weather_data['temperature']
                )
                
                route_weather.append({
                    **weather_data,
                    'transport_impact': impact.to_dict()
                })
            else:
                route_weather.append({
                    'city': city,
                    'error': weather_result.get('error', '获取天气失败')
                })
        
        # 综合分析
        overall_impact = self._analyze_overall_impact(route_weather)
        
        return {
            'success': True,
            'data': {
                'route_weather': route_weather,
                'overall_impact': overall_impact,
                'total_cities': len(cities),
                'cities_with_weather': len([w for w in route_weather if 'weather' in w])
            }
        }
    
    def _analyze_overall_impact(self, route_weather: List[Dict]) -> Dict:
        """分析沿途整体天气影响"""
        if not route_weather:
            return {'level': '未知', 'suggestion': '无法获取天气信息'}
        
        # 找出最严重的影响
        max_speed_reduction = 0
        max_delay_risk = 0
        severe_weather = []
        
        for w in route_weather:
            if 'transport_impact' in w:
                impact = w['transport_impact']
                max_speed_reduction = max(max_speed_reduction, impact['speed_reduction'])
                max_delay_risk = max(max_delay_risk, impact['delay_risk'])
                
                if impact['impact_level'] in ['严重影响', '极端影响，建议暂停运输']:
                    severe_weather.append({
                        'city': w.get('city'),
                        'weather': w.get('weather'),
                        'impact': impact['impact_level']
                    })
        
        # 确定整体影响等级
        if max_delay_risk >= 0.8:
            level = '严重'
        elif max_delay_risk >= 0.5:
            level = '中度'
        elif max_delay_risk >= 0.2:
            level = '轻微'
        else:
            level = '无'
        
        return {
            'level': level,
            'max_speed_reduction': max_speed_reduction,
            'max_delay_risk': max_delay_risk,
            'severe_weather_cities': severe_weather,
            'suggestion': self._get_overall_suggestion(level, severe_weather)
        }
    
    def _get_overall_suggestion(self, level: str, severe_weather: List[Dict]) -> str:
        """获取整体建议"""
        if level == '严重':
            cities = ', '.join([w['city'] for w in severe_weather])
            return f"⚠️ 沿途 {cities} 天气恶劣，建议调整运输计划或暂停运输"
        elif level == '中度':
            return "沿途部分路段天气不佳，建议减速慢行并做好应急准备"
        elif level == '轻微':
            return "沿途天气有小幅影响，建议适当降低车速"
        else:
            return "沿途天气良好，可正常运输"


# 单例实例
_weather_service = None


def get_weather_service() -> WeatherService:
    """获取天气服务实例"""
    global _weather_service
    if _weather_service is None:
        try:
            from flask import current_app
            api_key = current_app.config.get('AMAP_WEB_KEY')
            _weather_service = WeatherService(api_key)
        except:
            # 在应用上下文外使用环境变量
            import os
            api_key = os.environ.get('AMAP_WEB_KEY')
            _weather_service = WeatherService(api_key)
    return _weather_service
