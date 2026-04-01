#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
审计日志模型
记录用户操作和系统事件
"""

from datetime import datetime
from app.models import db


class AuditLog(db.Model):
    """审计日志表"""
    
    __tablename__ = 'audit_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # 用户信息
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    username = db.Column(db.String(80), nullable=True)
    
    # 操作信息
    action = db.Column(db.String(50), nullable=False)  # 操作类型
    module = db.Column(db.String(50), nullable=False)  # 模块名称
    description = db.Column(db.String(500), nullable=True)  # 操作描述
    
    # 请求信息
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.String(255), nullable=True)
    request_method = db.Column(db.String(10), nullable=True)
    request_url = db.Column(db.String(500), nullable=True)
    
    # 操作结果
    status = db.Column(db.String(20), default='success')  # success, failed, error
    error_message = db.Column(db.String(500), nullable=True)
    
    # 相关资源
    resource_type = db.Column(db.String(50), nullable=True)  # order, vehicle, node, etc.
    resource_id = db.Column(db.Integer, nullable=True)
    
    # 额外数据（JSON）
    extra_data = db.Column(db.Text, nullable=True)
    
    # 时间戳
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'username': self.username,
            'action': self.action,
            'module': self.module,
            'description': self.description,
            'ip_address': self.ip_address,
            'status': self.status,
            'resource_type': self.resource_type,
            'resource_id': self.resource_id,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    @classmethod
    def log(cls, action, module, description=None, user_id=None, username=None,
            ip_address=None, user_agent=None, request_method=None, request_url=None,
            status='success', error_message=None, resource_type=None, resource_id=None,
            extra_data=None):
        """创建审计日志"""
        log_entry = cls(
            user_id=user_id,
            username=username,
            action=action,
            module=module,
            description=description,
            ip_address=ip_address,
            user_agent=user_agent,
            request_method=request_method,
            request_url=request_url,
            status=status,
            error_message=error_message,
            resource_type=resource_type,
            resource_id=resource_id,
            extra_data=extra_data
        )
        db.session.add(log_entry)
        db.session.commit()
        return log_entry


class AuditAction:
    """操作类型枚举"""
    
    # 用户认证
    LOGIN = 'login'
    LOGOUT = 'logout'
    LOGIN_FAILED = 'login_failed'
    TOKEN_REFRESH = 'token_refresh'
    
    # CRUD 操作
    CREATE = 'create'
    UPDATE = 'update'
    DELETE = 'delete'
    VIEW = 'view'
    
    # 数据操作
    IMPORT = 'import'
    EXPORT = 'export'
    
    # 系统操作
    CONFIG_CHANGE = 'config_change'
    SYSTEM_START = 'system_start'
    SYSTEM_STOP = 'system_stop'
    
    # 安全相关
    RATE_LIMIT_HIT = 'rate_limit_hit'
    SUSPICIOUS_ACTIVITY = 'suspicious_activity'
    ACCESS_DENIED = 'access_denied'


class AuditModule:
    """模块名称枚举"""
    
    AUTH = 'auth'
    USER = 'user'
    NODE = 'node'
    ROUTE = 'route'
    VEHICLE = 'vehicle'
    ORDER = 'order'
    DISPATCH = 'dispatch'
    COST = 'cost'
    ANALYTICS = 'analytics'
    SYSTEM = 'system'
    SUPPLIER = 'supplier'
    DRIVER = 'driver'