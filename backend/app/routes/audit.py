#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
审计日志 API 路由
"""

from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from app.services.audit_service import audit_service
from app.utils.rate_limiter import rate_limit, RateLimits

audit_bp = Blueprint('audit', __name__)


@audit_bp.route('/logs', methods=['GET'])
@jwt_required()
@rate_limit(**RateLimits.API)
def get_logs():
    """获取审计日志列表"""
    # 获取查询参数
    user_id = request.args.get('user_id', type=int)
    module = request.args.get('module')
    action = request.args.get('action')
    status = request.args.get('status')
    resource_type = request.args.get('resource_type')
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    
    # 解析日期
    start_date = None
    end_date = None
    if start_date_str:
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        except ValueError:
            pass
    if end_date_str:
        try:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
            end_date = end_date + timedelta(days=1)  # 包含当天
        except ValueError:
            pass
    
    # 查询
    pagination = audit_service.get_logs(
        user_id=user_id,
        module=module,
        action=action,
        status=status,
        resource_type=resource_type,
        start_date=start_date,
        end_date=end_date,
        page=page,
        per_page=min(per_page, 100)
    )
    
    return jsonify({
        'logs': [log.to_dict() for log in pagination.items],
        'total': pagination.total,
        'page': page,
        'per_page': per_page,
        'pages': pagination.pages
    })


@audit_bp.route('/statistics', methods=['GET'])
@jwt_required()
@rate_limit(**RateLimits.API)
def get_statistics():
    """获取审计日志统计"""
    days = request.args.get('days', 7, type=int)
    days = min(days, 30)  # 最多 30 天
    
    stats = audit_service.get_statistics(days=days)
    
    return jsonify(stats)


@audit_bp.route('/modules', methods=['GET'])
@jwt_required()
def get_modules():
    """获取可用模块列表"""
    from app.models.audit import AuditModule
    
    modules = [
        {'value': AuditModule.AUTH, 'label': '用户认证'},
        {'value': AuditModule.USER, 'label': '用户管理'},
        {'value': AuditModule.NODE, 'label': '节点管理'},
        {'value': AuditModule.ROUTE, 'label': '路线管理'},
        {'value': AuditModule.VEHICLE, 'label': '车辆管理'},
        {'value': AuditModule.ORDER, 'label': '订单管理'},
        {'value': AuditModule.DISPATCH, 'label': '调度管理'},
        {'value': AuditModule.COST, 'label': '成本分析'},
        {'value': AuditModule.ANALYTICS, 'label': '数据分析'},
        {'value': AuditModule.SYSTEM, 'label': '系统'},
        {'value': AuditModule.SUPPLIER, 'label': '供应商管理'},
        {'value': AuditModule.DRIVER, 'label': '司机管理'},
    ]
    
    return jsonify(modules)


@audit_bp.route('/actions', methods=['GET'])
@jwt_required()
def get_actions():
    """获取可用操作类型列表"""
    from app.models.audit import AuditAction
    
    actions = [
        {'value': AuditAction.LOGIN, 'label': '登录'},
        {'value': AuditAction.LOGOUT, 'label': '登出'},
        {'value': AuditAction.LOGIN_FAILED, 'label': '登录失败'},
        {'value': AuditAction.CREATE, 'label': '创建'},
        {'value': AuditAction.UPDATE, 'label': '更新'},
        {'value': AuditAction.DELETE, 'label': '删除'},
        {'value': AuditAction.VIEW, 'label': '查看'},
        {'value': AuditAction.IMPORT, 'label': '导入'},
        {'value': AuditAction.EXPORT, 'label': '导出'},
        {'value': AuditAction.RATE_LIMIT_HIT, 'label': '速率限制'},
        {'value': AuditAction.ACCESS_DENIED, 'label': '访问拒绝'},
    ]
    
    return jsonify(actions)
