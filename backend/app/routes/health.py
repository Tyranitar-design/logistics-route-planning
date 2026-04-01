#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
健康检查路由 - Docker 部署专用
"""

from flask import Blueprint, jsonify
from datetime import datetime

health_bp = Blueprint('health', __name__)


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
        
        return jsonify({
            'status': 'ready',
            'database': 'connected',
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        }), 200
    except Exception as e:
        return jsonify({
            'status': 'not_ready',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        }), 503
