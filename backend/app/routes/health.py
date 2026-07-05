#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
健康检查路由 - Docker 部署专用
"""

from flask import Blueprint, current_app, jsonify
from datetime import datetime

health_bp = Blueprint('health', __name__)


def _database_runtime_summary():
    from app.models import Order, db
    from app.models.layered_data import ShipmentFact

    uri = current_app.config.get('SQLALCHEMY_DATABASE_URI') or ''
    backend = 'postgresql' if str(uri).startswith(('postgresql://', 'postgresql+')) else 'sqlite' if str(uri).startswith('sqlite') else 'unknown'
    shipment_facts, shipment_fact_error = _safe_model_count(ShipmentFact)
    legacy_orders, legacy_order_error = _safe_model_count(Order)
    warning = None
    if backend == 'sqlite' and not shipment_facts:
        warning = '当前连接为空 SQLite 兜底库；真实 5 万 shipment_facts 需要设置 POSTGRES_DATABASE_URL 或 DATABASE_URL 后重启后端。'

    return {
        'backend': backend,
        'primary_order_source': 'shipment_fact' if shipment_facts > 0 else 'orders' if legacy_orders > 0 else 'empty',
        'shipment_facts': shipment_facts,
        'legacy_orders': legacy_orders,
        'count_errors': {
            'shipment_facts': shipment_fact_error,
            'legacy_orders': legacy_order_error,
        },
        'warning': warning,
    }


def _safe_model_count(model):
    try:
        return model.query.count(), None
    except Exception as exc:
        return 0, type(exc).__name__


@health_bp.route('/health', methods=['GET'])
def health_check():
    """
    健康检查接口 - Docker HEALTHCHECK 使用
    返回服务状态、时间戳
    """
    return jsonify({
        'status': 'healthy',
        'service': 'logistics-backend',
        'version': '2.0',
        'features': 43,
        'timestamp': datetime.utcnow().isoformat() + 'Z'
    }), 200


@health_bp.route('/ready', methods=['GET'])
def readiness_check():
    """
    就绪检查 - 检查数据库连接等
    """
    try:
        from app.models import db
        
        # 尝试执行简单查询
        db.session.execute(db.text('SELECT 1'))
        
        try:
            from app.services.runtime_capability_service import registered_capabilities_summary
            registered_capabilities = registered_capabilities_summary()
        except Exception as capability_exc:
            registered_capabilities = {
                'provider_status': 'degraded',
                'fallback_reason': f'RUNTIME_CAPABILITY_SUMMARY_FAILED:{capability_exc.__class__.__name__}',
                'registered': {},
                'missing': [],
            }

        return jsonify({
            'status': 'ready',
            'database': 'connected',
            'database_runtime': _database_runtime_summary(),
            'registered_capabilities': registered_capabilities,
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        }), 200
    except Exception as e:
        return jsonify({
            'status': 'not_ready',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        }), 503
