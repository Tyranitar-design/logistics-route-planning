#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
数据采集路由 - 自包含版本（不依赖外部爬虫项目）
整合项目内部已有的：油价服务、天气服务、路况服务
适配前端 DataCollectionView.vue 期望的数据格式
"""

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required
from datetime import datetime
import random

data_collection_bp = Blueprint('data_collection', __name__)

AMAP_KEY = 'e471e7d99965ef1f1a0d4113f580f5db'

# 城市名 -> 高德 adcode 映射
CITY_ADCODE = {
    '北京': '110000', '上海': '310000', '广州': '440100', '深圳': '440300',
    '杭州': '330100', '成都': '510100', '武汉': '420100', '南京': '320100',
    '重庆': '500000', '西安': '610100', '天津': '120000', '苏州': '320500',
    '长沙': '430100', '郑州': '410100', '济南': '370100', '青岛': '370200',
    '大连': '210200', '宁波': '330200', '厦门': '350200', '福州': '350100',
    '合肥': '340100', '昆明': '530100', '贵阳': '520100', '南宁': '450100',
    '沈阳': '210100', '哈尔滨': '230100', '长春': '220100', '石家庄': '130100',
    '太原': '140100', '南昌': '360100', '兰州': '620100', '海口': '460100',
    '银川': '640100', '西宁': '630100', '呼和浩特': '150100', '拉萨': '540100',
    '乌鲁木齐': '650100',
    'Beijing': '110000', 'Shanghai': '310000', 'Guangzhou': '440100',
    'Shenzhen': '440300', 'Hangzhou': '330100', 'Chengdu': '510100',
    'Wuhan': '420100', 'Nanjing': '320100', 'Chongqing': '500000',
    'Xian': '610100', 'Tianjin': '120000',
}

# 城市名 -> 中心坐标（用于矩形路况查询）
CITY_CENTER = {
    '北京': '116.20,39.70,116.50,40.00', '上海': '121.20,31.00,121.60,31.40',
    '广州': '113.00,23.00,113.40,23.30', '深圳': '113.80,22.40,114.30,22.70',
    '杭州': '120.00,30.10,120.30,30.40', '成都': '103.90,30.50,104.20,30.80',
    '武汉': '114.10,30.30,114.50,30.60', '南京': '118.60,31.90,119.00,32.10',
    '重庆': '106.30,29.30,106.70,29.60', '西安': '108.80,34.10,109.10,34.40',
    '天津': '117.00,39.00,117.40,39.30', '苏州': '120.40,31.10,120.70,31.40',
    '长沙': '112.80,28.10,113.10,28.30', '郑州': '113.40,34.60,113.70,34.80',
    '济南': '116.90,36.50,117.20,36.70', '青岛': '120.10,36.00,120.50,36.30',
    'Beijing': '116.20,39.70,116.50,40.00', 'Shanghai': '121.20,31.00,121.60,31.40',
    'Guangzhou': '113.00,23.00,113.40,23.30', 'Shenzhen': '113.80,22.40,114.30,22.70',
    'Hangzhou': '120.00,30.10,120.30,30.40', 'Chengdu': '103.90,30.50,104.20,30.80',
}


@data_collection_bp.route('/status', methods=['GET'])
def get_collection_status():
    """获取数据采集状态（无需登录）"""
    return jsonify({
        'success': True,
        'sources': [
            {'name': '油价数据', 'status': 'available', 'type': '模拟+API', 'provider': '天行数据API + 发改委参考'},
            {'name': '天气数据', 'status': 'available', 'type': '真实数据', 'provider': '高德地图API'},
            {'name': '路况数据', 'status': 'available', 'type': '真实数据', 'provider': '高德地图API'},
            {'name': '快递价格', 'status': 'available', 'type': '模拟数据', 'provider': '模拟算法'}
        ],
        'timestamp': datetime.now().isoformat()
    })


@data_collection_bp.route('/oil', methods=['GET'])
@jwt_required()
def get_oil_prices():
    """获取全国油价数据 - 返回前端期望的 list 格式"""
    try:
        from app.services.oil_crawler import fetch_reference_prices
        records = fetch_reference_prices()

        # 按省份聚合为前端表格格式
        province_data = {}
        for r in records:
            prov = r['province'].replace('省', '').replace('市', '').replace('自治区', '').replace('壮族', '').replace('维吾尔', '').replace('回族', '')
            if prov not in province_data:
                province_data[prov] = {'province': prov, 'p92': '--', 'p95': '--', 'p98': '--', 'p0': '--'}
            fuel = r['fuel_type']
            price = str(r['price'])
            if '92号' in fuel:
                province_data[prov]['p92'] = price
            elif '95号' in fuel:
                province_data[prov]['p95'] = price
            elif '98号' in fuel:
                province_data[prov]['p98'] = price
            elif '0号柴油' in fuel:
                province_data[prov]['p0'] = price

        oil_list = list(province_data.values())

        return jsonify({
            'success': True,
            'source': '发改委参考数据',
            'data': {'list': oil_list}
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@data_collection_bp.route('/weather/<city>', methods=['GET'])
@jwt_required()
def get_weather_data(city):
    """获取城市天气数据 - 返回前端期望的 lives 数组格式"""
    try:
        from app.services.weather_service import WeatherService
        service = WeatherService(AMAP_KEY)
        result = service.get_weather_now(city)

        if result and result.get('success'):
            info = result.get('data', {})
            # 转换为前端期望的 lives 格式
            lives = [{
                'province': info.get('province', city),
                'city': info.get('city', city),
                'adcode': info.get('adcode', ''),
                'weather': info.get('weather', '未知'),
                'temperature': info.get('temperature', '--'),
                'temperature_low': info.get('temperature', '--'),
                'temperature_high': info.get('temperature', '--'),
                'winddirection': info.get('wind_direction', info.get('winddirection', '未知')),
                'windpower': info.get('wind_power', info.get('windpower', '未知')),
                'humidity': info.get('humidity', '未知'),
                'reporttime': info.get('report_time', info.get('reporttime', ''))
            }]
            return jsonify({
                'success': True,
                'lives': lives,
                'forecasts': []
            })
        else:
            # 降级：返回模拟数据
            return jsonify({
                'success': True,
                'lives': [{
                    'province': city, 'city': city, 'adcode': '',
                    'weather': '晴', 'temperature': str(random.randint(15, 30)),
                    'temperature_low': str(random.randint(10, 20)),
                    'temperature_high': str(random.randint(25, 35)),
                    'winddirection': '东南风', 'windpower': '3级',
                    'humidity': str(random.randint(30, 70)),
                    'reporttime': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }],
                'forecasts': []
            })
    except Exception as e:
        # 降级返回模拟数据
        return jsonify({
            'success': True,
            'lives': [{
                'province': city, 'city': city, 'adcode': '',
                'weather': '多云', 'temperature': str(random.randint(15, 30)),
                'temperature_low': str(random.randint(10, 20)),
                'temperature_high': str(random.randint(25, 35)),
                'winddirection': '北风', 'windpower': '2级',
                'humidity': str(random.randint(30, 70)),
                'reporttime': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }],
            'forecasts': [],
            'fallback': True,
            'error': str(e)
        })


@data_collection_bp.route('/forecast/<city>', methods=['GET'])
@jwt_required()
def get_weather_forecast(city):
    """获取城市天气预报"""
    try:
        from app.services.weather_service import WeatherService
        service = WeatherService(AMAP_KEY)
        result = service.get_weather_forecast(city)

        if result and result.get('success'):
            return jsonify({
                'success': True,
                'forecasts': result.get('data', [])
            })
        else:
            # 模拟预报数据
            forecasts = []
            import hashlib
            for i in range(4):
                random.seed(hash(city) + i)
                forecasts.append({
                    'date': f'{datetime.now().year}-{(datetime.now().month + 1) % 12 + 1:02d}-{random.randint(1,28):02d}',
                    'dayweather': random.choice(['晴', '多云', '阴', '小雨', '中雨']),
                    'nightweather': random.choice(['晴', '多云', '阴']),
                    'daytemp': str(random.randint(20, 35)),
                    'nighttemp': str(random.randint(10, 22)),
                    'daywind': random.choice(['东风', '南风', '西风', '北风']),
                    'daypower': f'{random.randint(1, 5)}级'
                })
            return jsonify({'success': True, 'forecasts': forecasts})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@data_collection_bp.route('/traffic/<city>', methods=['GET'])
@jwt_required()
def get_traffic_data(city):
    """获取城市路况数据 - 返回前端期望的 trafficinfo 格式"""
    try:
        from app.services.traffic_service import TrafficService
        service = TrafficService()

        # 城市名转坐标范围
        rect = CITY_CENTER.get(city)
        if not rect:
            # 降级返回模拟数据
            return jsonify({
                'success': True,
                'trafficinfo': {
                    'evaluation': {'expedite': '85%', 'congested': '10%', 'slow': '4%', 'blocked': '1%'},
                    'speed': '32km/h',
                    'roads': [
                        {'name': '中山路', 'status': '畅通'},
                        {'name': '人民路', 'status': '畅通'},
                        {'name': '解放大道', 'status': '缓行'},
                    ]
                },
                'fallback': True
            })

        result = service.get_rectangle_traffic(rect)

        if result and result.get('success'):
            traffic = result.get('traffic', {})
            # 转换为前端期望的格式
            roads = []
            for t in traffic.get('traffics', []):
                roads.append({
                    'name': t.get('name', '未知路段'),
                    'status': t.get('status', '未知'),
                })
            eval_data = traffic.get('evaluation', {})
            return jsonify({
                'success': True,
                'trafficinfo': {
                    'evaluation': {
                        'expedite': eval_data.get('expedite', '--'),
                        'congested': eval_data.get('congested', '--'),
                        'slow': eval_data.get('slow', '--'),
                        'blocked': eval_data.get('blocked', '--'),
                    },
                    'speed': traffic.get('speed', '--km/h'),
                    'roads': roads
                }
            })
        else:
            # 降级返回模拟数据
            return jsonify({
                'success': True,
                'trafficinfo': {
                    'evaluation': {'expedite': '80%', 'congested': '12%', 'slow': '6%', 'blocked': '2%'},
                    'speed': '28km/h',
                    'roads': [
                        {'name': '主干道', 'status': '畅通'},
                        {'name': '环城路', 'status': '缓行'},
                        {'name': '快速路', 'status': '畅通'},
                    ]
                },
                'fallback': True
            })
    except Exception as e:
        return jsonify({
            'success': True,
            'trafficinfo': {
                'evaluation': {'expedite': '75%', 'congested': '15%', 'slow': '7%', 'blocked': '3%'},
                'speed': '25km/h',
                'roads': []
            },
            'fallback': True,
            'error': str(e)
        })


@data_collection_bp.route('/transport-impact/<city>', methods=['GET'])
@jwt_required()
def get_transport_impact(city):
    """获取天气对运输的影响分析"""
    try:
        from app.services.weather_service import WeatherService
        service = WeatherService(AMAP_KEY)
        result = service.analyze_transport_impact(city)

        if result:
            return jsonify({
                'success': True,
                'city': city,
                'data': result.to_dict() if hasattr(result, 'to_dict') else result
            })
        else:
            return jsonify({'success': False, 'error': '无法获取运输影响分析'}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@data_collection_bp.route('/fuel-cost', methods=['POST'])
@jwt_required()
def calculate_fuel_cost():
    """计算燃油成本"""
    try:
        data = request.get_json()
        from app.services.oil_price_service import get_oil_price_service
        service = get_oil_price_service()
        result = service.calculate_fuel_cost(
            distance_km=data.get('distance_km', 0),
            fuel_type=data.get('fuel_type', '0'),
            province=data.get('province', '北京')
        )
        return jsonify({'success': True, 'data': result})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@data_collection_bp.route('/express/compare', methods=['POST'])
@jwt_required()
def compare_express():
    """对比快递价格（模拟数据）"""
    try:
        data = request.get_json()
        origin = data.get('origin', '北京')
        destination = data.get('destination', '上海')
        weight = data.get('weight', 1)

        companies = [
            {'company': '顺丰速运', 'base_price': 18, 'delivery_days': 1, 'weight_limit': 20},
            {'company': '中通快递', 'base_price': 8, 'delivery_days': 3, 'weight_limit': 30},
            {'company': '圆通速递', 'base_price': 9, 'delivery_days': 3, 'weight_limit': 30},
            {'company': '韵达快递', 'base_price': 8, 'delivery_days': 3, 'weight_limit': 30},
            {'company': '申通快递', 'base_price': 9, 'delivery_days': 3, 'weight_limit': 30},
            {'company': '百世快递', 'base_price': 7, 'delivery_days': 4, 'weight_limit': 30},
            {'company': '极兔速递', 'base_price': 8, 'delivery_days': 3, 'weight_limit': 30},
            {'company': '京东物流', 'base_price': 12, 'delivery_days': 1, 'weight_limit': 50},
            {'company': 'EMS', 'base_price': 15, 'delivery_days': 2, 'weight_limit': 30},
            {'company': '德邦快递', 'base_price': 10, 'delivery_days': 2, 'weight_limit': 60},
        ]

        results = []
        for c in companies:
            price = round(c['base_price'] + max(0, weight - 1) * c['base_price'] * 0.5 + random.uniform(-2, 2), 2)
            is_rec = (c['company'] == '顺丰速运')
            results.append({
                'company': c['company'],
                'total_price': price,
                'delivery_days': c['delivery_days'],
                'weight_limit': c['weight_limit'],
                'base_price': c['base_price'],
                'is_recommended': is_rec
            })

        results.sort(key=lambda x: x['total_price'])
        return jsonify({'success': True, 'results': results})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@data_collection_bp.route('/all', methods=['GET'])
@jwt_required()
def collect_all_data():
    """一次性采集所有数据"""
    try:
        cities_str = request.args.get('cities', '北京,上海,广州,深圳')
        cities = [c.strip() for c in cities_str.split(',') if c.strip()]

        result = {'success': True, 'timestamp': datetime.now().isoformat(), 'data': {}}

        # 油价
        try:
            from app.services.oil_crawler import fetch_reference_prices
            oil_records = fetch_reference_prices()
            province_data = {}
            for r in oil_records:
                prov = r['province'].replace('省', '').replace('市', '').replace('自治区', '').replace('壮族', '').replace('维吾尔', '').replace('回族', '')
                if prov not in province_data:
                    province_data[prov] = {'province': prov, 'p92': '--', 'p95': '--', 'p98': '--', 'p0': '--'}
                fuel = r['fuel_type']
                if '92号' in fuel: province_data[prov]['p92'] = str(r['price'])
                elif '95号' in fuel: province_data[prov]['p95'] = str(r['price'])
                elif '98号' in fuel: province_data[prov]['p98'] = str(r['price'])
                elif '0号柴油' in fuel: province_data[prov]['p0'] = str(r['price'])
            result['data']['oil'] = {'status': 'success', 'total_provinces': len(province_data), 'provinces': province_data}
        except Exception as e:
            result['data']['oil'] = {'status': 'failed', 'error': str(e)}

        # 天气
        from app.services.weather_service import WeatherService
        ws = WeatherService(AMAP_KEY)
        weather_data = {}
        for city in cities[:4]:
            try:
                w = ws.get_weather_now(city)
                if w and w.get('success'):
                    weather_data[city] = w.get('data', {})
                else:
                    weather_data[city] = {'weather': '晴', 'temperature': '--', 'fallback': True}
            except Exception as e:
                weather_data[city] = {'error': str(e)}
        result['data']['weather'] = {'status': 'success', 'cities': weather_data}

        # 路况
        from app.services.traffic_service import TrafficService
        ts = TrafficService()
        traffic_data = {}
        for city in cities[:4]:
            rect = CITY_CENTER.get(city)
            if rect:
                try:
                    t = ts.get_rectangle_traffic(rect)
                    traffic_data[city] = t if t else {'fallback': True}
                except Exception as e:
                    traffic_data[city] = {'error': str(e)}
            else:
                traffic_data[city] = {'fallback': True, 'reason': 'no coordinates'}
        result['data']['traffic'] = {'status': 'success', 'cities': traffic_data}

        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
