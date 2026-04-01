#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
审计日志服务
提供日志记录和查询功能
"""

import json
from datetime import datetime, timedelta
from flask import request, g
from app.models import db
from app.models.audit import AuditLog, AuditAction, AuditModule


class AuditService:
    """审计日志服务"""
    
    @staticmethod
    def get_current_user_info():
        """获取当前用户信息"""
        from flask_jwt_extended import get_jwt_identity, get_jwt
        
        try:
            user_id = get_jwt_identity()
            claims = get_jwt() or {}
            username = claims.get('username', 'unknown')
            return user_id, username
        except Exception:
            return None, None
    
    @staticmethod
    def get_request_info():
        """获取请求信息"""
        # 获取 IP 地址
        ip = '127.0.0.1'
        if request:
            if request.headers.get('X-Forwarded-For'):
                ip = request.headers.get('X-Forwarded-For').split(',')[0].strip()
            elif request.headers.get('X-Real-IP'):
                ip = request.headers.get('X-Real-IP')
            else:
                ip = request.remote_addr or '127.0.0.1'
        
        return {
            'ip_address': ip,
            'user_agent': request.headers.get('User-Agent', '')[:255] if request else None,
            'request_method': request.method if request else None,
            'request_url': request.url[:500] if request else None
        }
    
    @staticmethod
    def log(action, module, description=None, status='success', error_message=None,
            resource_type=None, resource_id=None, extra_data=None):
        """
        记录审计日志
        
        Args:
            action: 操作类型 (AuditAction)
            module: 模块名称 (AuditModule)
            description: 操作描述
            status: 操作状态
            error_message: 错误信息
            resource_type: 资源类型
            resource_id: 资源ID
            extra_data: 额外数据（字典）
        
        Returns:
            AuditLog 实例
        """
        user_id, username = AuditService.get_current_user_info()
        request_info = AuditService.get_request_info()
        
        extra_json = json.dumps(extra_data, ensure_ascii=False) if extra_data else None
        
        return AuditLog.log(
            action=action,
            module=module,
            description=description,
            user_id=user_id,
            username=username,
            ip_address=request_info['ip_address'],
            user_agent=request_info['user_agent'],
            request_method=request_info['request_method'],
            request_url=request_info['request_url'],
            status=status,
            error_message=error_message,
            resource_type=resource_type,
            resource_id=resource_id,
            extra_data=extra_json
        )
    
    @staticmethod
    def log_login(user_id, username, success=True, ip_address=None):
        """记录登录日志"""
        return AuditLog.log(
            action=AuditAction.LOGIN if success else AuditAction.LOGIN_FAILED,
            module=AuditModule.AUTH,
            description=f'用户 {"登录成功" if success else "登录失败"}',
            user_id=user_id if success else None,
            username=username,
            ip_address=ip_address or AuditService.get_request_info()['ip_address'],
            status='success' if success else 'failed'
        )
    
    @staticmethod
    def log_logout(user_id, username):
        """记录登出日志"""
        return AuditLog.log(
            action=AuditAction.LOGOUT,
            module=AuditModule.AUTH,
            description='用户登出',
            user_id=user_id,
            username=username
        )
    
    @staticmethod
    def log_create(module, resource_type, resource_id, description=None, extra_data=None):
        """记录创建操作"""
        return AuditService.log(
            action=AuditAction.CREATE,
            module=module,
            description=description or f'创建 {resource_type}',
            resource_type=resource_type,
            resource_id=resource_id,
            extra_data=extra_data
        )
    
    @staticmethod
    def log_update(module, resource_type, resource_id, description=None, extra_data=None):
        """记录更新操作"""
        return AuditService.log(
            action=AuditAction.UPDATE,
            module=module,
            description=description or f'更新 {resource_type}',
            resource_type=resource_type,
            resource_id=resource_id,
            extra_data=extra_data
        )
    
    @staticmethod
    def log_delete(module, resource_type, resource_id, description=None):
        """记录删除操作"""
        return AuditService.log(
            action=AuditAction.DELETE,
            module=module,
            description=description or f'删除 {resource_type}',
            resource_type=resource_type,
            resource_id=resource_id
        )
    
    @staticmethod
    def log_export(module, description, extra_data=None):
        """记录导出操作"""
        return AuditService.log(
            action=AuditAction.EXPORT,
            module=module,
            description=description,
            extra_data=extra_data
        )
    
    @staticmethod
    def log_rate_limit_hit(endpoint, ip_address):
        """记录速率限制触发"""
        return AuditLog.log(
            action=AuditAction.RATE_LIMIT_HIT,
            module=AuditModule.SYSTEM,
            description=f'速率限制触发: {endpoint}',
            ip_address=ip_address,
            status='warning'
        )
    
    @staticmethod
    def get_logs(user_id=None, module=None, action=None, status=None,
                 resource_type=None, start_date=None, end_date=None,
                 page=1, per_page=50):
        """
        查询审计日志
        
        Args:
            user_id: 用户ID
            module: 模块名称
            action: 操作类型
            status: 操作状态
            resource_type: 资源类型
            start_date: 开始日期
            end_date: 结束日期
            page: 页码
            per_page: 每页数量
        
        Returns:
            分页结果
        """
        query = AuditLog.query
        
        if user_id:
            query = query.filter(AuditLog.user_id == user_id)
        if module:
            query = query.filter(AuditLog.module == module)
        if action:
            query = query.filter(AuditLog.action == action)
        if status:
            query = query.filter(AuditLog.status == status)
        if resource_type:
            query = query.filter(AuditLog.resource_type == resource_type)
        if start_date:
            query = query.filter(AuditLog.created_at >= start_date)
        if end_date:
            query = query.filter(AuditLog.created_at <= end_date)
        
        query = query.order_by(AuditLog.created_at.desc())
        
        return query.paginate(page=page, per_page=per_page, error_out=False)
    
    @staticmethod
    def get_statistics(days=7):
        """
        获取审计日志统计
        
        Args:
            days: 统计天数
        
        Returns:
            统计数据
        """
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # 总操作数
        total = AuditLog.query.filter(AuditLog.created_at >= start_date).count()
        
        # 按模块统计
        module_stats = db.session.query(
            AuditLog.module,
            db.func.count(AuditLog.id).label('count')
        ).filter(
            AuditLog.created_at >= start_date
        ).group_by(AuditLog.module).all()
        
        # 按操作类型统计
        action_stats = db.session.query(
            AuditLog.action,
            db.func.count(AuditLog.id).label('count')
        ).filter(
            AuditLog.created_at >= start_date
        ).group_by(AuditLog.action).all()
        
        # 按状态统计
        status_stats = db.session.query(
            AuditLog.status,
            db.func.count(AuditLog.id).label('count')
        ).filter(
            AuditLog.created_at >= start_date
        ).group_by(AuditLog.status).all()
        
        # 每日统计
        daily_stats = db.session.query(
            db.func.date(AuditLog.created_at).label('date'),
            db.func.count(AuditLog.id).label('count')
        ).filter(
            AuditLog.created_at >= start_date
        ).group_by(db.func.date(AuditLog.created_at)).all()
        
        return {
            'total': total,
            'days': days,
            'by_module': {m: c for m, c in module_stats},
            'by_action': {a: c for a, c in action_stats},
            'by_status': {s: c for s, c in status_stats},
            'daily': [{'date': str(d), 'count': c} for d, c in daily_stats]
        }


# 全局审计服务实例
audit_service = AuditService()
