#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
智能预警中心 API 路由
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.services.alert_center_service import get_alert_center_service
import logging

logger = logging.getLogger(__name__)

alert_bp = Blueprint('alert', __name__)


@alert_bp.route('/dashboard', methods=['GET'])
@jwt_required()
def get_dashboard():
    """
    获取预警仪表盘数据
    
    Returns:
        {
            "success": true,
            "alerts": [...],
            "statistics": {...},
            "summary": {...}
        }
    """
    try:
        service = get_alert_center_service()
        data = service.get_dashboard_data()
        
        return jsonify({
            'success': True,
            **data
        })
    
    except Exception as e:
        logger.error(f"获取预警仪表盘失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@alert_bp.route('/alerts', methods=['GET'])
@jwt_required()
def get_alerts():
    """
    获取预警列表
    
    Query params:
        type: 预警类型 (order, vehicle, route, supply_chain)
        level: 预警级别 (critical, high, medium, low)
        limit: 返回数量 (默认20)
    
    Returns:
        预警列表
    """
    try:
        alert_type = request.args.get('type')
        level = request.args.get('level')
        limit = request.args.get('limit', 20, type=int)
        
        service = get_alert_center_service()
        
        if alert_type:
            alerts = service.get_alerts_by_type(alert_type)
        elif level:
            alerts = service.get_alerts_by_level(level)
        else:
            alerts = service.check_all_alerts()
        
        return jsonify({
            'success': True,
            'alerts': [
                {
                    'id': a.id,
                    'type': a.type,
                    'level': a.level,
                    'title': a.title,
                    'message': a.message,
                    'source': a.source,
                    'source_id': a.source_id,
                    'created_at': a.created_at.isoformat(),
                    'is_read': a.is_read,
                    'actions': a.actions,
                    'metadata': a.metadata
                }
                for a in alerts[:limit]
            ],
            'total': len(alerts)
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@alert_bp.route('/statistics', methods=['GET'])
@jwt_required()
def get_statistics():
    """获取预警统计"""
    try:
        service = get_alert_center_service()
        stats = service.get_alert_statistics()
        
        return jsonify({
            'success': True,
            'statistics': {
                'total': stats.total,
                'critical': stats.critical,
                'high': stats.high,
                'medium': stats.medium,
                'low': stats.low,
                'unread': stats.unread,
                'by_type': stats.by_type
            }
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@alert_bp.route('/alerts/<alert_id>/read', methods=['POST'])
@jwt_required()
def mark_read(alert_id: str):
    """标记预警为已读"""
    try:
        service = get_alert_center_service()
        result = service.mark_as_read(alert_id)
        
        return jsonify({
            'success': result,
            'message': '已标记为已读'
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@alert_bp.route('/alerts/<alert_id>/resolve', methods=['POST'])
@jwt_required()
def mark_resolved(alert_id: str):
    """标记预警为已解决"""
    try:
        service = get_alert_center_service()
        result = service.mark_as_resolved(alert_id)
        
        return jsonify({
            'success': result,
            'message': '已标记为已解决'
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@alert_bp.route('/rules', methods=['GET'])
@jwt_required()
def get_rules():
    """获取预警规则配置"""
    from app.services.alert_center_service import AlertRules
    
    rules = AlertRules()
    
    return jsonify({
        'success': True,
        'rules': {
            'order': [
                {'id': k, 'name': v['name'], 'level': v['level']}
                for k, v in rules.ORDER_RULES.items()
            ],
            'vehicle': [
                {'id': k, 'name': v['name'], 'level': v['level']}
                for k, v in rules.VEHICLE_RULES.items()
            ],
            'route': [
                {'id': k, 'name': v['name'], 'level': v['level']}
                for k, v in rules.ROUTE_RULES.items()
            ],
            'supply_chain': [
                {'id': k, 'name': v['name'], 'level': v['level']}
                for k, v in rules.SUPPLY_CHAIN_RULES.items()
            ]
        }
    })