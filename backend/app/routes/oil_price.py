#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
油价查询路由
"""

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required
from app.services.oil_price_service import get_oil_price_service

oil_price_bp = Blueprint('oil_price', __name__)


@oil_price_bp.route('/current', methods=['GET'])
@jwt_required()
def get_current_prices():
    """
    获取当前油价
    
    Query params:
        province: 省份名称（默认：北京）
    """
    try:
        province = request.args.get('province', '北京')
        service = get_oil_price_service()
        prices = service.get_current_prices(province)
        
        return jsonify({
            'success': True,
            'data': prices
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@oil_price_bp.route('/history', methods=['GET'])
@jwt_required()
def get_price_history():
    """
    获取油价历史趋势
    
    Query params:
        province: 省份名称
        days: 天数（默认：30）
    """
    try:
        province = request.args.get('province', '北京')
        days = request.args.get('days', 30, type=int)
        
        service = get_oil_price_service()
        history = service.get_price_history(province, days)
        
        return jsonify({
            'success': True,
            'data': history
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@oil_price_bp.route('/calculate', methods=['POST'])
@jwt_required()
def calculate_fuel_cost():
    """
    计算燃油成本
    
    Body:
        distance_km: 距离（公里）
        fuel_type: 油品类型（92/95/98/0）
        province: 省份
        consumption: 百公里油耗（可选）
    """
    try:
        data = request.get_json()
        distance_km = data.get('distance_km', 0)
        fuel_type = data.get('fuel_type', '0')
        province = data.get('province', '北京')
        consumption = data.get('consumption')
        
        service = get_oil_price_service()
        result = service.calculate_fuel_cost(distance_km, fuel_type, province, consumption)
        
        return jsonify({
            'success': True,
            'data': result
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@oil_price_bp.route('/provinces', methods=['GET'])
@jwt_required()
def get_supported_provinces():
    """获取支持的省份列表"""
    service = get_oil_price_service()
    provinces = list(service.PROVINCE_FACTORS.keys())
    
    return jsonify({
        'success': True,
        'data': provinces
    })


@oil_price_bp.route('/refresh-cache', methods=['POST'])
@jwt_required()
def refresh_cache():
    """刷新缓存（管理员功能）"""
    try:
        service = get_oil_price_service()
        result = service.refresh_cache()
        
        return jsonify({
            'success': True,
            'message': result['message']
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
