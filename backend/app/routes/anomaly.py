"""
实时异常检测 API 路由
"""

from flask import Blueprint, request, jsonify
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from app.services.realtime_anomaly_detection import (
    realtime_anomaly_service,
    AlertType,
    AlertLevel
)
from app.models import db
from app.models import Order, Vehicle
from sqlalchemy import func, case

anomaly_bp = Blueprint('anomaly', __name__, url_prefix='/api/anomaly')


@anomaly_bp.route('/detect', methods=['POST'])
def run_detection():
    """
    运行全量异常检测
    
    Request Body (可选):
        order_ids: 指定订单ID列表
        vehicle_ids: 指定车辆ID列表
    """
    try:
        data = request.get_json() or {}
        order_ids = data.get('order_ids')
        vehicle_ids = data.get('vehicle_ids')
        
        # 获取订单数据
        orders = []
        order_query = Order.query
        if order_ids:
            order_query = order_query.filter(Order.id.in_(order_ids))
        else:
            # 获取最近7天的活跃订单
            week_ago = datetime.now() - timedelta(days=7)
            order_query = order_query.filter(
                Order.created_at >= week_ago,
                Order.status.in_(['pending', 'assigned', 'in_transit'])
            )
        
        for o in order_query.limit(100).all():
            orders.append({
                'id': o.id,
                'order_number': o.order_number,
                'status': o.status,
                'priority': o.priority,
                'created_at': o.created_at.isoformat() if o.created_at else None,
                'actual_cost': float(o.actual_cost) if o.actual_cost else None,
                'estimated_cost': float(o.estimated_cost) if o.estimated_cost else None,
                'vehicle_id': o.vehicle_id
            })
        
        # 获取车辆数据
        vehicles = []
        vehicle_query = Vehicle.query
        if vehicle_ids:
            vehicle_query = vehicle_query.filter(Vehicle.id.in_(vehicle_ids))
        
        for v in vehicle_query.limit(50).all():
            vehicles.append({
                'id': v.id,
                'plate_number': v.plate_number,
                'status': v.status,
                'total_mileage': getattr(v, 'total_mileage', 50000),  # 默认值
                'purchase_date': getattr(v, 'purchase_date', None) or (datetime.now() - timedelta(days=730)).isoformat(),
                'last_maintenance': getattr(v, 'last_maintenance', None) or (datetime.now() - timedelta(days=30)).isoformat()
            })
        
        # 模拟车辆位置数据
        import random
        vehicle_positions = []
        for v in vehicles[:10]:
            vehicle_positions.append({
                'vehicle_id': v['id'],
                'plate_number': v['plate_number'],
                'total_distance': random.uniform(50, 500),
                'latitude': 39.9 + random.uniform(-0.5, 0.5),
                'longitude': 116.4 + random.uniform(-0.5, 0.5)
            })
        
        # 模拟天气数据
        regions = ['北京', '上海', '广州', '深圳', '成都']
        weather_types = ['sunny', 'cloudy', 'rain', 'heavy_rain', 'storm', 'snow']
        weather_data = {}
        for region in regions:
            weather_data[region] = {
                'weather': random.choice(weather_types),
                'temperature': random.randint(15, 35),
                'humidity': random.randint(30, 90)
            }
        
        # 运行检测
        result = realtime_anomaly_service.run_full_detection(
            orders=orders,
            vehicles=vehicles,
            vehicle_positions=vehicle_positions,
            weather_data=weather_data
        )
        
        # 添加健康度评分
        result['health_score'] = max(0, 100 - result['summary']['total_anomalies'] * 5)
        
        # 添加建议
        result['recommendations'] = _generate_recommendations(result['summary'])
        
        return jsonify(result)
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'检测失败: {str(e)}'
        }), 500


@anomaly_bp.route('/detect/orders', methods=['POST'])
def detect_orders():
    """
    检测订单异常（超时、成本飙升）
    """
    try:
        data = request.get_json() or {}
        order_ids = data.get('order_ids')
        
        # 获取订单
        query = Order.query
        if order_ids:
            query = query.filter(Order.id.in_(order_ids))
        else:
            week_ago = datetime.now() - timedelta(days=7)
            query = query.filter(Order.created_at >= week_ago)
        
        orders = []
        for o in query.limit(100).all():
            orders.append({
                'id': o.id,
                'order_number': o.order_number,
                'status': o.status,
                'priority': o.priority,
                'created_at': o.created_at.isoformat() if o.created_at else None,
                'actual_cost': float(o.actual_cost) if o.actual_cost else None,
                'estimated_cost': float(o.estimated_cost) if o.estimated_cost else None
            })
        
        # 检测超时
        from app.services.realtime_anomaly_detection import OrderTimeoutDetector
        timeout_detector = OrderTimeoutDetector()
        timeout_anomalies = timeout_detector.batch_detect(orders)
        
        # 检测成本
        from app.services.realtime_anomaly_detection import CostAnomalyDetector
        cost_detector = CostAnomalyDetector()
        cost_anomalies = cost_detector.detect_batch(orders)
        
        return jsonify({
            'success': True,
            'timeout_anomalies': len(timeout_anomalies),
            'cost_anomalies': len(cost_anomalies),
            'anomalies': [
                {
                    'id': a.id,
                    'type': a.type.value,
                    'level': a.level.value,
                    'message': a.message,
                    'actions': a.actions
                }
                for a in timeout_anomalies + cost_anomalies
            ]
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@anomaly_bp.route('/detect/vehicles', methods=['POST'])
def detect_vehicles():
    """
    检测车辆异常（故障预测）
    """
    try:
        data = request.get_json() or {}
        vehicle_ids = data.get('vehicle_ids')
        
        # 获取车辆
        query = Vehicle.query
        if vehicle_ids:
            query = query.filter(Vehicle.id.in_(vehicle_ids))
        
        vehicles = []
        for v in query.limit(50).all():
            vehicles.append({
                'id': v.id,
                'plate_number': v.plate_number,
                'status': v.status,
                'total_mileage': v.total_mileage or 0,
                'purchase_date': v.purchase_date.isoformat() if v.purchase_date else None,
                'last_maintenance': v.last_maintenance.isoformat() if v.last_maintenance else None
            })
        
        # 故障预测
        from app.services.realtime_anomaly_detection import VehicleFaultPredictor
        predictor = VehicleFaultPredictor()
        anomalies = predictor.batch_predict(vehicles)
        
        return jsonify({
            'success': True,
            'total_vehicles': len(vehicles),
            'anomaly_count': len(anomalies),
            'anomalies': [
                {
                    'id': a.id,
                    'vehicle_id': a.source_id,
                    'level': a.level.value,
                    'risk_score': a.value,
                    'message': a.message,
                    'actions': a.actions
                }
                for a in anomalies
            ]
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@anomaly_bp.route('/detect/weather', methods=['POST'])
def detect_weather():
    """
    检测天气影响
    """
    try:
        data = request.get_json() or {}
        weather_data = data.get('weather_data', {})
        
        # 如果没有提供天气数据，使用模拟数据
        if not weather_data:
            import random
            regions = ['北京', '上海', '广州', '深圳', '成都', '武汉', '西安']
            weather_types = ['sunny', 'cloudy', 'rain', 'heavy_rain', 'storm', 'snow', 'fog']
            
            for region in regions:
                weather_data[region] = {
                    'weather': random.choice(weather_types),
                    'temperature': random.randint(-5, 40),
                    'humidity': random.randint(20, 95)
                }
        
        # 检测
        from app.services.realtime_anomaly_detection import WeatherImpactDetector
        detector = WeatherImpactDetector()
        anomalies = detector.check_regions(weather_data)
        
        return jsonify({
            'success': True,
            'regions_checked': len(weather_data),
            'anomaly_count': len(anomalies),
            'anomalies': [
                {
                    'id': a.id,
                    'region': a.metadata.get('region'),
                    'level': a.level.value,
                    'weather': a.metadata.get('weather', {}).get('weather'),
                    'delay_percent': a.deviation,
                    'message': a.message,
                    'actions': a.actions
                }
                for a in anomalies
            ]
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@anomaly_bp.route('/detect/route', methods=['POST'])
def detect_route():
    """
    检测路线偏离
    """
    try:
        data = request.get_json() or {}
        vehicle_positions = data.get('vehicle_positions', [])
        
        if not vehicle_positions:
            return jsonify({
                'success': True,
                'message': '无车辆位置数据'
            })
        
        # 检测
        from app.services.realtime_anomaly_detection import RouteDeviationDetector
        detector = RouteDeviationDetector()
        anomalies = detector.check_realtime(vehicle_positions)
        
        return jsonify({
            'success': True,
            'vehicles_checked': len(vehicle_positions),
            'anomaly_count': len(anomalies),
            'anomalies': [
                {
                    'id': a.id,
                    'vehicle_id': a.source_id,
                    'level': a.level.value,
                    'deviation_percent': a.deviation,
                    'actual_distance': a.value,
                    'planned_distance': a.threshold,
                    'message': a.message,
                    'actions': a.actions
                }
                for a in anomalies
            ]
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@anomaly_bp.route('/history', methods=['GET'])
def get_history():
    """
    获取检测历史
    """
    limit = request.args.get('limit', 10, type=int)
    
    history = realtime_anomaly_service.get_detection_history(limit)
    
    return jsonify({
        'success': True,
        'count': len(history),
        'history': history
    })


@anomaly_bp.route('/trends', methods=['GET'])
def get_trends():
    """
    获取异常趋势
    """
    hours = request.args.get('hours', 24, type=int)
    
    trends = realtime_anomaly_service.get_anomaly_trends(hours)
    
    return jsonify({
        'success': True,
        'trends': trends
    })


@anomaly_bp.route('/dashboard', methods=['GET'])
def get_dashboard():
    """
    获取异常检测仪表盘数据
    """
    try:
        # 运行一次快速检测
        import random
        
        # 模拟订单数据
        orders = []
        for i in range(20):
            status = random.choice(['pending', 'assigned', 'in_transit', 'delivered'])
            priority = random.choice(['normal', 'urgent', 'scheduled'])
            created_hours_ago = random.randint(1, 72)
            
            orders.append({
                'id': i + 1,
                'order_number': f'ORD{1000 + i}',
                'status': status,
                'priority': priority,
                'created_at': (datetime.now() - timedelta(hours=created_hours_ago)).isoformat(),
                'actual_cost': random.randint(100, 1000) if status == 'delivered' else None,
                'estimated_cost': random.randint(100, 800)
            })
        
        # 模拟车辆数据
        vehicles = []
        for i in range(15):
            vehicles.append({
                'id': i + 1,
                'plate_number': f'京A{10000 + i}',
                'status': random.choice(['available', 'busy', 'maintenance']),
                'total_mileage': random.randint(50000, 250000),
                'purchase_date': (datetime.now() - timedelta(days=random.randint(365, 3650))).isoformat(),
                'last_maintenance': (datetime.now() - timedelta(days=random.randint(10, 200))).isoformat()
            })
        
        # 运行检测
        result = realtime_anomaly_service.run_full_detection(
            orders=orders,
            vehicles=vehicles
        )
        
        # 构建仪表盘数据
        return jsonify({
            'success': True,
            'summary': result['summary'],
            'latest_anomalies': result['anomalies'][:10],
            'detection_time': result['detection_time'],
            'health_score': max(0, 100 - result['summary']['total_anomalies'] * 5),
            'recommendations': _generate_recommendations(result['summary'])
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


def _generate_recommendations(summary: dict) -> List[str]:
    """生成建议"""
    recommendations = []
    
    by_type = summary.get('by_type', {})
    
    if by_type.get('order_timeout', 0) > 3:
        recommendations.append('⚠️ 订单超时较多，建议检查调度效率或增加运力')
    
    if by_type.get('cost_spike', 0) > 2:
        recommendations.append('💰 成本异常增多，建议审核近期路线规划')
    
    if by_type.get('route_deviation', 0) > 0:
        recommendations.append('🗺️ 存在路线偏离，建议检查司机导航设备')
    
    if by_type.get('weather_impact', 0) > 0:
        recommendations.append('🌧️ 天气影响预警，建议调整配送计划')
    
    if by_type.get('vehicle_fault', 0) > 2:
        recommendations.append('🚗 车辆故障风险较高，建议安排集中检修')
    
    if not recommendations:
        recommendations.append('✅ 系统运行正常，各项指标健康')
    
    return recommendations


def register_anomaly_routes(app):
    """注册异常检测路由"""
    app.register_blueprint(anomaly_bp)