"""
动态定价 API 路由
"""

from flask import Blueprint, request, jsonify
from datetime import datetime
from app.services.dynamic_pricing_service import dynamic_pricing_engine

pricing_bp = Blueprint('pricing', __name__, url_prefix='/api/pricing')


@pricing_bp.route('/calculate', methods=['POST'])
def calculate_price():
    """
    计算动态价格
    
    Request Body:
        distance: 距离（公里）
        weight: 货物重量（吨）
        region: 区域（可选）
        urgency: 紧急程度 (normal, urgent, scheduled)
    """
    data = request.get_json()
    
    if not data or 'distance' not in data:
        return jsonify({
            'success': False,
            'message': '请提供距离参数'
        }), 400
    
    try:
        result = dynamic_pricing_engine.calculate_price(
            distance=data.get('distance'),
            weight=data.get('weight', 1.0),
            region=data.get('region'),
            urgency=data.get('urgency', 'normal')
        )
        return jsonify({
            'success': True,
            'data': result
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'定价失败: {str(e)}'
        }), 500


@pricing_bp.route('/forecast', methods=['GET'])
def get_price_forecast():
    """
    获取价格预测（未来N小时）
    
    Query Parameters:
        distance: 距离（公里）
        region: 区域（可选）
        hours: 预测小时数（默认24）
    """
    distance = request.args.get('distance', 10, type=float)
    region = request.args.get('region', None)
    hours = request.args.get('hours', 24, type=int)
    
    try:
        result = dynamic_pricing_engine.get_price_forecast(distance, region, hours)
        return jsonify({
            'success': True,
            'data': result
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'预测失败: {str(e)}'
        }), 500


@pricing_bp.route('/batch', methods=['POST'])
def batch_pricing():
    """
    批量定价
    
    Request Body:
        orders: 订单列表
    """
    data = request.get_json()
    
    if not data or 'orders' not in data:
        return jsonify({
            'success': False,
            'message': '请提供订单列表'
        }), 400
    
    try:
        result = dynamic_pricing_engine.batch_pricing(data['orders'])
        return jsonify({
            'success': True,
            'data': result
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'定价失败: {str(e)}'
        }), 500


@pricing_bp.route('/statistics', methods=['GET'])
def get_statistics():
    """
    获取定价统计
    """
    try:
        result = dynamic_pricing_engine.get_pricing_statistics()
        return jsonify({
            'success': True,
            'data': result
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'获取统计失败: {str(e)}'
        }), 500


@pricing_bp.route('/time-slots', methods=['GET'])
def get_time_slots():
    """
    获取时段定价信息
    """
    from app.services.dynamic_pricing_service import TimeFactorPricing
    
    time_pricing = TimeFactorPricing()
    current_time = datetime.now()
    time_info = time_pricing.get_time_factor(current_time)
    
    return jsonify({
        'success': True,
        'data': {
            'current_time': current_time.strftime('%Y-%m-%d %H:%M:%S'),
            'time_info': time_info,
            'hourly_factors': time_pricing.hour_factors,
            'weekday_factors': time_pricing.weekday_factors
        }
    })


def register_pricing_routes(app):
    """注册定价路由"""
    app.register_blueprint(pricing_bp)