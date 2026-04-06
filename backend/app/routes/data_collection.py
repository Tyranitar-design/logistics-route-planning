#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
数据采集路由 - 整合爬虫数据源
油价、天气、路况、快递价格
"""

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required
import sys
import os

# 添加爬虫模块路径
sys.path.insert(0, r'D:\物流大数据分析智能分析平台\crawler')

data_collection_bp = Blueprint('data_collection', __name__)


@data_collection_bp.route('/oil', methods=['GET'])
@jwt_required()
def get_oil_prices():
    """
    获取全国油价数据
    
    Returns:
        {
            "success": true,
            "source": "模拟数据",
            "data": {
                "list": [
                    {"province": "北京", "p92": "7.82", "p95": "8.33", ...}
                ]
            }
        }
    """
    try:
        from data_collector import OilPriceCollector
        
        collector = OilPriceCollector()
        result = collector.get_prices()
        
        return jsonify(result)
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@data_collection_bp.route('/weather/<city>', methods=['GET'])
@jwt_required()
def get_weather_data(city):
    """
    获取城市天气数据
    
    Args:
        city: 城市名称（如：北京、上海、广州）
    
    Returns:
        {
            "success": true,
            "city": "北京",
            "lives": [...],
            "forecasts": [...]
        }
    """
    try:
        from data_collector import WeatherCollector
        
        collector = WeatherCollector()
        result = collector.get_weather(city)
        
        return jsonify(result)
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@data_collection_bp.route('/traffic/<city>', methods=['GET'])
@jwt_required()
def get_traffic_data(city):
    """
    获取城市路况数据
    
    Args:
        city: 城市名称
    
    Returns:
        {
            "success": true,
            "city": "北京",
            "trafficinfo": {...}
        }
    """
    try:
        from data_collector import TrafficCollector
        
        collector = TrafficCollector()
        result = collector.get_traffic(city)
        
        return jsonify(result)
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@data_collection_bp.route('/express/compare', methods=['POST'])
@jwt_required()
def compare_express_prices():
    """
    对比快递价格
    
    Body:
        origin: 寄件城市
        destination: 收件城市
        weight: 重量(kg)
    
    Returns:
        {
            "success": true,
            "results": [
                {"company": "圆通速递", "total_price": 20.64, ...}
            ]
        }
    """
    try:
        from express_price_crawler import ExpressPriceCrawler
        
        data = request.get_json()
        origin = data.get('origin', '北京')
        destination = data.get('destination', '上海')
        weight = data.get('weight', 1.0)
        
        crawler = ExpressPriceCrawler()
        results = crawler.compare_prices(origin, destination, weight)
        
        return jsonify({
            'success': True,
            'origin': origin,
            'destination': destination,
            'weight': weight,
            'results': results,
            'cheapest': results[0] if results else None,
            'fastest': min(results, key=lambda x: x['delivery_days']) if results else None
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@data_collection_bp.route('/express/recommend', methods=['POST'])
@jwt_required()
def recommend_express():
    """
    推荐最优快递
    
    Body:
        origin: 寄件城市
        destination: 收件城市
        weight: 重量(kg)
        priority: 优先级 (price | speed | balanced)
    
    Returns:
        {
            "success": true,
            "recommendation": {...}
        }
    """
    try:
        from express_price_crawler import ExpressPriceCrawler
        
        data = request.get_json()
        origin = data.get('origin', '北京')
        destination = data.get('destination', '上海')
        weight = data.get('weight', 1.0)
        priority = data.get('priority', 'balanced')
        
        crawler = ExpressPriceCrawler()
        result = crawler.get_recommended(origin, destination, weight, priority)
        
        return jsonify({
            'success': True,
            'priority': priority,
            'recommendation': result
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@data_collection_bp.route('/all', methods=['GET'])
@jwt_required()
def collect_all_data():
    """
    一次性采集所有数据
    
    Query params:
        cities: 城市列表（逗号分隔）
    
    Returns:
        {
            "success": true,
            "data": {
                "oil": {...},
                "weather": {...},
                "traffic": {...}
            }
        }
    """
    try:
        from data_collector import UnifiedDataCollector
        
        cities_str = request.args.get('cities', '北京,上海,广州,深圳')
        cities = [c.strip() for c in cities_str.split(',') if c.strip()]
        
        collector = UnifiedDataCollector()
        result = collector.collect_all(cities)
        
        return jsonify(result)
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@data_collection_bp.route('/status', methods=['GET'])
@jwt_required()
def get_collection_status():
    """
    获取数据采集状态
    
    Returns:
        {
            "success": true,
            "sources": [
                {"name": "油价", "status": "available", "type": "模拟数据"},
                {"name": "天气", "status": "available", "type": "高德API"},
                ...
            ]
        }
    """
    return jsonify({
        'success': True,
        'sources': [
            {'name': '油价数据', 'status': 'available', 'type': '模拟数据', 'provider': '天行数据API(待配置)'},
            {'name': '天气数据', 'status': 'available', 'type': '真实数据', 'provider': '高德地图API'},
            {'name': '路况数据', 'status': 'available', 'type': '真实数据', 'provider': '高德地图API'},
            {'name': '快递价格', 'status': 'available', 'type': '模拟数据', 'provider': '模拟算法'}
        ]
    })
