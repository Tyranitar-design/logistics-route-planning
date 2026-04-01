#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
供应链风险管理 API 路由
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.services.supply_chain_risk_service import get_supply_chain_risk_service
import logging

logger = logging.getLogger(__name__)

risk_bp = Blueprint('risk', __name__)


# ==================== 仪表盘 ====================

@risk_bp.route('/dashboard', methods=['GET'])
@jwt_required()
def get_dashboard():
    """
    获取风险管理仪表盘数据
    
    Returns:
        {
            "success": true,
            "kraljic_matrix": {...},
            "risk_matrix": {...},
            "crisis_zones": [...]
        }
    """
    try:
        service = get_supply_chain_risk_service()
        data = service.get_dashboard_data()
        
        return jsonify({
            'success': True,
            **data
        })
    
    except Exception as e:
        logger.error(f"获取风险管理仪表盘失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== 卡拉杰克矩阵 ====================

@risk_bp.route('/kraljic/classify', methods=['POST'])
@jwt_required()
def classify_item():
    """
    卡拉杰克矩阵物资分类
    
    Body:
        item_id: 物资ID
        item_name: 物资名称
        profit_impact: 利润影响度 (0-100)
        supply_risk: 供应风险度 (0-100)
    
    Returns:
        分类结果
    """
    try:
        data = request.get_json()
        
        service = get_supply_chain_risk_service()
        result = service.kraljic.classify_item(
            item_id=data.get('item_id'),
            item_name=data.get('item_name', ''),
            profit_impact=data.get('profit_impact', 50),
            supply_risk=data.get('supply_risk', 50)
        )
        
        return jsonify({
            'success': True,
            'classification': {
                'item_id': result.item_id,
                'item_name': result.item_name,
                'profit_impact': result.profit_impact,
                'supply_risk': result.supply_risk,
                'category': result.category,
                'category_name': service.kraljic.CATEGORY_STRATEGIES[result.category]['name'],
                'strategy': result.strategy,
                'color': result.color
            }
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@risk_bp.route('/kraljic/orders', methods=['GET'])
@jwt_required()
def classify_orders():
    """
    对所有待处理订单进行卡拉杰克矩阵分类
    
    Returns:
        分类结果列表和统计信息
    """
    try:
        from app.models import Order
        
        orders = Order.query.filter(Order.status.in_(['pending', 'assigned'])).all()
        
        service = get_supply_chain_risk_service()
        items = service.kraljic.classify_orders(orders)
        stats = service.kraljic.get_matrix_statistics(items)
        
        return jsonify({
            'success': True,
            'items': [
                {
                    'item_id': item.item_id,
                    'item_name': item.item_name,
                    'profit_impact': item.profit_impact,
                    'supply_risk': item.supply_risk,
                    'category': item.category,
                    'strategy': item.strategy,
                    'color': item.color
                }
                for item in items
            ],
            'statistics': stats
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@risk_bp.route('/kraljic/categories', methods=['GET'])
@jwt_required()
def get_categories():
    """获取卡拉杰克矩阵分类说明"""
    service = get_supply_chain_risk_service()
    
    return jsonify({
        'success': True,
        'categories': [
            {
                'id': cat_id,
                'name': info['name'],
                'strategy': info['strategy'],
                'color': info['color'],
                'risk_level': info['risk_level']
            }
            for cat_id, info in service.kraljic.CATEGORY_STRATEGIES.items()
        ]
    })


# ==================== 风险评估矩阵 ====================

@risk_bp.route('/assessment/route/<int:route_id>', methods=['GET'])
@jwt_required()
def assess_route(route_id: int):
    """
    评估指定路线的风险
    
    Query params:
        weather_factor: 天气风险因子 (0-1)
        traffic_factor: 交通风险因子 (0-1)
        geopolitical_factor: 地缘政治风险因子 (0-1)
    
    Returns:
        风险评估结果
    """
    try:
        from app.models import Route
        
        route = Route.query.get(route_id)
        if not route:
            return jsonify({'success': False, 'error': '路线不存在'}), 404
        
        weather_factor = request.args.get('weather_factor', 1.0, type=float)
        traffic_factor = request.args.get('traffic_factor', 1.0, type=float)
        geopolitical_factor = request.args.get('geopolitical_factor', 1.0, type=float)
        
        service = get_supply_chain_risk_service()
        assessment = service.risk_assessment.assess_route_risk(
            route,
            weather_factor,
            traffic_factor,
            geopolitical_factor
        )
        
        return jsonify({
            'success': True,
            'assessment': {
                'risk_level': assessment.risk_level,
                'probability': assessment.probability,
                'impact': assessment.impact,
                'score': assessment.score,
                'recommendation': assessment.recommendation,
                'mitigation_strategies': assessment.mitigation_strategies
            }
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@risk_bp.route('/assessment/matrix', methods=['GET'])
@jwt_required()
def get_risk_matrix():
    """
    获取风险评估矩阵可视化数据
    
    Returns:
        矩阵数据和项目列表
    """
    try:
        from app.models import Route, Order
        
        routes = Route.query.limit(20).all()
        orders = Order.query.filter(Order.status.in_(['pending', 'assigned'])).limit(50).all()
        
        service = get_supply_chain_risk_service()
        data = service.risk_assessment.get_matrix_data(routes, orders)
        
        return jsonify({
            'success': True,
            **data
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@risk_bp.route('/assessment/levels', methods=['GET'])
@jwt_required()
def get_risk_levels():
    """获取风险等级说明"""
    service = get_supply_chain_risk_service()
    
    return jsonify({
        'success': True,
        'levels': [
            {
                'id': level_id,
                'name': info['name'],
                'color': info['color'],
                'min_score': info['min']
            }
            for level_id, info in service.risk_assessment.RISK_LEVELS.items()
        ]
    })


# ==================== CBA决策模型 ====================

@risk_bp.route('/cba/calculate', methods=['POST'])
@jwt_required()
def calculate_cba():
    """
    成本效益分析决策计算
    
    Body:
        cargo_value: 货物价值
        fixed_loss: 固定损失
        daily_loss: 每日损失
        transfer_cost: 转运成本
        waiting_days: 已等待天数（可选）
    
    Returns:
        决策结果
    """
    try:
        data = request.get_json()
        
        service = get_supply_chain_risk_service()
        decision = service.cba.calculate_decision(
            cargo_value=data.get('cargo_value', 0),
            fixed_loss=data.get('fixed_loss', 0),
            daily_loss=data.get('daily_loss', 0),
            transfer_cost=data.get('transfer_cost', 0),
            waiting_days=data.get('waiting_days', 0)
        )
        
        return jsonify({
            'success': True,
            'decision': {
                'scenario': decision.scenario,
                'wait_cost': decision.wait_cost,
                'transfer_cost': decision.transfer_cost,
                'critical_days': decision.critical_days,
                'recommendation': decision.recommendation,
                'cost_breakdown': decision.cost_breakdown
            }
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@risk_bp.route('/cba/batch', methods=['POST'])
@jwt_required()
def batch_cba():
    """
    批量CBA分析
    
    Body:
        scenarios: 场景列表
    
    Returns:
        批量分析结果
    """
    try:
        data = request.get_json()
        scenarios = data.get('scenarios', [])
        
        service = get_supply_chain_risk_service()
        results = service.cba.batch_analyze(scenarios)
        
        return jsonify({
            'success': True,
            'results': results
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== AWRP成本估算 ====================

@risk_bp.route('/awrp/estimate', methods=['POST'])
@jwt_required()
def estimate_awrp():
    """
    AWRP战争附加费估算
    
    Body:
        cargo_value: 货物价值（美元）
        zone: 危机区域代码
        is_crisis: 是否处于危机状态
    
    Returns:
        成本估算结果
    """
    try:
        data = request.get_json()
        
        service = get_supply_chain_risk_service()
        estimate = service.awrp.estimate_cost(
            cargo_value=data.get('cargo_value', 0),
            zone=data.get('zone', 'normal'),
            is_crisis=data.get('is_crisis', False)
        )
        
        return jsonify({
            'success': True,
            'estimate': {
                'cargo_value': estimate.cargo_value,
                'route_type': estimate.route_type,
                'base_awrp_rate': estimate.base_awrp_rate,
                'current_awrp_rate': estimate.current_awrp_rate,
                'insurance_cost_before': estimate.insurance_cost_before,
                'insurance_cost_after': estimate.insurance_cost_after,
                'cost_increase_ratio': estimate.cost_increase_ratio
            }
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@risk_bp.route('/awrp/compare', methods=['POST'])
@jwt_required()
def compare_awrp_routes():
    """
    AWRP路线对比
    
    Body:
        cargo_value: 货物价值
        route_a: 路线A参数 (穿越风险区域)
        route_b: 路线B参数 (绕行方案)
    
    Returns:
        对比结果和决策建议
    """
    try:
        data = request.get_json()
        
        service = get_supply_chain_risk_service()
        comparison = service.awrp.compare_routes(
            cargo_value=data.get('cargo_value', 0),
            route_a=data.get('route_a', {}),
            route_b=data.get('route_b', {})
        )
        
        return jsonify({
            'success': True,
            **comparison
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@risk_bp.route('/awrp/zones', methods=['GET'])
@jwt_required()
def get_crisis_zones():
    """获取危机区域列表"""
    service = get_supply_chain_risk_service()
    zones = service.awrp.get_zone_list()
    
    return jsonify({
        'success': True,
        'zones': zones
    })


@risk_bp.route('/awrp/rates', methods=['GET'])
@jwt_required()
def get_awrp_rates():
    """获取AWRP费率表"""
    service = get_supply_chain_risk_service()
    
    return jsonify({
        'success': True,
        'rates': service.awrp.RISK_RATES,
        'zones': service.awrp.CRISIS_ZONES
    })