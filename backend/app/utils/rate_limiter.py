#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
API 速率限制器
防止恶意请求和 DDoS 攻击
"""

import time
from functools import wraps
from collections import defaultdict
from threading import Lock
from flask import request, jsonify, g


class RateLimiter:
    """基于内存的速率限制器"""
    
    def __init__(self):
        self.requests = defaultdict(list)
        self.lock = Lock()
    
    def _cleanup_old_requests(self, key, window_seconds):
        """清理过期的请求记录"""
        current_time = time.time()
        cutoff_time = current_time - window_seconds
        self.requests[key] = [t for t in self.requests[key] if t > cutoff_time]
    
    def is_allowed(self, key, max_requests, window_seconds):
        """检查是否允许请求"""
        with self.lock:
            self._cleanup_old_requests(key, window_seconds)
            
            if len(self.requests[key]) >= max_requests:
                return False, len(self.requests[key])
            
            self.requests[key].append(time.time())
            return True, len(self.requests[key])
    
    def get_remaining(self, key, max_requests, window_seconds):
        """获取剩余请求次数"""
        with self.lock:
            self._cleanup_old_requests(key, window_seconds)
            return max(0, max_requests - len(self.requests[key]))


# 全局速率限制器实例
rate_limiter = RateLimiter()


def get_client_ip():
    """获取客户端 IP 地址"""
    # 支持代理服务器
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    elif request.headers.get('X-Real-IP'):
        return request.headers.get('X-Real-IP')
    return request.remote_addr or '127.0.0.1'


def rate_limit(max_requests=100, window_seconds=60, key_func=None):
    """
    速率限制装饰器
    
    Args:
        max_requests: 时间窗口内最大请求数
        window_seconds: 时间窗口（秒）
        key_func: 自定义键函数，默认使用 IP
    
    Usage:
        @rate_limit(max_requests=10, window_seconds=60)
        def some_api():
            ...
    """
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            # 生成限制键
            if key_func:
                key = key_func()
            else:
                ip = get_client_ip()
                endpoint = request.endpoint or 'unknown'
                key = f"{ip}:{endpoint}"
            
            # 检查是否允许
            allowed, current_count = rate_limiter.is_allowed(key, max_requests, window_seconds)
            
            if not allowed:
                retry_after = window_seconds
                return jsonify({
                    'error': '请求过于频繁',
                    'message': f'请在 {retry_after} 秒后重试',
                    'retry_after': retry_after
                }), 429
            
            # 添加速率限制头
            g.rate_limit_remaining = rate_limiter.get_remaining(key, max_requests, window_seconds)
            g.rate_limit_limit = max_requests
            
            return f(*args, **kwargs)
        return wrapped
    return decorator


# 预定义的限制规则
class RateLimits:
    """预定义的速率限制规则"""
    
    # 登录接口：每分钟最多 5 次
    LOGIN = {'max_requests': 5, 'window_seconds': 60}
    
    # API 接口：每分钟最多 100 次
    API = {'max_requests': 100, 'window_seconds': 60}
    
    # 敏感操作：每分钟最多 10 次
    SENSITIVE = {'max_requests': 10, 'window_seconds': 60}
    
    # 数据导出：每分钟最多 5 次
    EXPORT = {'max_requests': 5, 'window_seconds': 60}
    
    # WebSocket 连接：每分钟最多 10 次
    WEBSOCKET = {'max_requests': 10, 'window_seconds': 60}


def add_rate_limit_headers(response):
    """添加速率限制响应头"""
    if hasattr(g, 'rate_limit_remaining'):
        response.headers['X-RateLimit-Limit'] = str(g.rate_limit_limit)
        response.headers['X-RateLimit-Remaining'] = str(g.rate_limit_remaining)
        response.headers['X-RateLimit-Reset'] = str(int(time.time()) + 60)
    return response
