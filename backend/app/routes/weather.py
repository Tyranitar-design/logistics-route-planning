#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
天气相关路由
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from app.services.weather_service import get_weather_service

weather_bp = Blueprint('weather', __name__)


@weather_bp.route('/now', methods=['GET'])
@jwt_required()
def get_weather_now():
    """
    获取实时天气
    
    Query params:
        city: 城市名称或 adcode（如：北京、110000、上海）
    
    Returns:
        {
            "success": true,
            "data": {
                "province": "北京",
                "city": "北京市",
                "weather": "晴",
                "temperature": "21",
                "wind_direction": "北",
                "wind_power": "3",
                "humidity": "11",
                "report_time": "2026-03-22 13:03:41"
            }
        }
    """
    try:
        city = request.args.get('city')
        
        if not city:
            return jsonify({
                'success': False,
                'error': '请提供城市名称'
            }), 400
        
        service = get_weather_service()
        result = service.get_weather_now(city)
        
        return jsonify(result)
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@weather_bp.route('/forecast', methods=['GET'])
@jwt_required()
def get_weather_forecast():
    """
    获取天气预报（未来4天）
    
    Query params:
        city: 城市名称或 adcode
    
    Returns:
        {
            "success": true,
            "data": {
                "city": "北京市",
                "forecast": [
                    {
                        "date": "2026-03-22",
                        "week": "6",
                        "day_weather": "晴",
                        "night_weather": "晴",
                        "day_temp": "22",
                        "night_temp": "8",
                        ...
                    },
                    ...
                ]
            }
        }
    """
    try:
        city = request.args.get('city')
        
        if not city:
            return jsonify({
                'success': False,
                'error': '请提供城市名称'
            }), 400
        
        service = get_weather_service()
        result = service.get_weather_forecast(city)
        
        return jsonify(result)
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@weather_bp.route('/impact', methods=['GET'])
@jwt_required()
def analyze_weather_impact():
    """
    分析天气对运输的影响
    
    Query params:
        weather: 天气状况（如：晴、小雨、大雨）
        temperature: 温度（可选）
    
    Returns:
        {
            "success": true,
            "data": {
                "impact_level": "轻微影响",
                "speed_reduction": 0.1,
                "delay_risk": 0.2,
                "safety_warning": "",
                "suggestions": [
                    "建议适当降低车速，保持安全距离",
                    "雨天路滑，注意防滑，开启雾灯"
                ]
            }
        }
    """
    try:
        weather = request.args.get('weather')
        temperature = request.args.get('temperature')
        
        if not weather:
            return jsonify({
                'success': False,
                'error': '请提供天气状况'
            }), 400
        
        service = get_weather_service()
        impact = service.analyze_transport_impact(weather, temperature)
        
        return jsonify({
            'success': True,
            'data': impact.to_dict()
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@weather_bp.route('/route', methods=['GET'])
@jwt_required()
def get_route_weather():
    """
    获取沿途天气情况
    
    Query params:
        cities: 城市名称列表，逗号分隔（如：北京,天津,济南,上海）
    
    Returns:
        {
            "success": true,
            "data": {
                "route_weather": [
                    {
                        "city": "北京",
                        "weather": "晴",
                        "temperature": "21",
                        "transport_impact": {...}
                    },
                    ...
                ],
                "overall_impact": {
                    "level": "轻微",
                    "max_speed_reduction": 0.1,
                    "max_delay_risk": 0.2,
                    "severe_weather_cities": [],
                    "suggestion": "沿途天气有小幅影响，建议适当降低车速"
                }
            }
        }
    """
    try:
        cities_str = request.args.get('cities')
        
        if not cities_str:
            return jsonify({
                'success': False,
                'error': '请提供城市列表（逗号分隔）'
            }), 400
        
        cities = [c.strip() for c in cities_str.split(',') if c.strip()]
        
        if not cities:
            return jsonify({
                'success': False,
                'error': '城市列表不能为空'
            }), 400
        
        service = get_weather_service()
        result = service.get_route_weather(cities)
        
        return jsonify(result)
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@weather_bp.route('/node/<int:node_id>', methods=['GET'])
@jwt_required()
def get_node_weather(node_id):
    """
    获取节点位置的天气
    
    通过节点 ID 查询该节点所在城市的天气
    """
    try:
        from app.models import Node
        import re
        
        node = Node.query.get(node_id)
        if not node:
            return jsonify({
                'success': False,
                'error': '节点不存在'
            }), 404
        
        # 优先使用城市名，其次使用省份
        city = node.city or node.province
        
        # 如果没有城市信息，尝试从名称或地址中提取
        if not city:
            # 常见城市名列表
            city_patterns = [
                '北京', '上海', '天津', '重庆',  # 直辖市
                '广州', '深圳', '杭州', '南京', '苏州', '武汉', '成都', '西安', 
                '郑州', '长沙', '济南', '青岛', '大连', '沈阳', '哈尔滨', '长春',
                '福州', '厦门', '宁波', '无锡', '合肥', '南昌', '昆明', '贵阳',
                '南宁', '海口', '兰州', '银川', '西宁', '乌鲁木齐', '拉萨',
                '呼和浩特', '太原', '石家庄', '唐山', '温州', '珠海', '东莞',
                '佛山', '中山', '惠州', '常州', '南通', '嘉兴', '绍兴', '台州'
            ]
            
            # 从名称中提取
            name = node.name or ''
            address = node.address or ''
            
            for c in city_patterns:
                if c in name or c in address:
                    city = c
                    break
        
        # 如果还是没有，使用地址中的省份信息
        if not city and node.address:
            # 匹配省名（去掉"省"字）
            province_match = re.search(r'([\u4e00-\u9fa5]+)(?:省|自治区)', node.address)
            if province_match:
                city = province_match.group(1)
        
        # 最后的回退：根据经纬度推断城市（简单的经纬度范围判断）
        if not city and node.longitude and node.latitude:
            lat, lng = node.latitude, node.longitude
            
            # 简单的城市经纬度范围判断
            if 39.4 <= lat <= 41.0 and 115.7 <= lng <= 117.4:
                city = '北京'
            elif 30.6 <= lat <= 31.9 and 120.8 <= lng <= 122.2:
                city = '上海'
            elif 22.4 <= lat <= 23.5 and 113.0 <= lng <= 114.5:
                city = '广州'
            elif 22.4 <= lat <= 22.9 and 113.7 <= lng <= 114.7:
                city = '深圳'
            elif 29.9 <= lat <= 30.6 and 119.9 <= lng <= 120.8:
                city = '杭州'
            elif 30.0 <= lat <= 32.5 and 118.0 <= lng <= 119.5:
                city = '南京'
        
        if not city:
            return jsonify({
                'success': False,
                'error': '无法确定节点所在城市，请为节点添加城市信息'
            }), 400
        
        service = get_weather_service()
        weather_result = service.get_weather_now(city)
        
        if weather_result['success']:
            # 分析影响
            weather_data = weather_result['data']
            impact = service.analyze_transport_impact(
                weather_data['weather'],
                weather_data['temperature']
            )
            
            return jsonify({
                'success': True,
                'data': {
                    **weather_data,
                    'node_id': node_id,
                    'node_name': node.name,
                    'resolved_city': city,  # 返回解析出的城市
                    'transport_impact': impact.to_dict()
                }
            })
        else:
            return jsonify(weather_result)
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
