#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
实时数据 WebSocket 服务
使用 Flask-SocketIO 实现实时通信
"""

import json
from datetime import datetime
from flask_socketio import SocketIO, emit
from app.services.data_generator import get_data_generator


# 初始化 SocketIO
socketio = None


def init_socketio(app):
    """初始化 SocketIO"""
    global socketio
    
    socketio = SocketIO(
        app,
        cors_allowed_origins="*",
        async_mode='threading',
        ping_timeout=60,
        ping_interval=25
    )
    
    # 注册事件处理
    @socketio.on('connect')
    def handle_connect():
        """客户端连接"""
        print(f"[WebSocket] 客户端连接")
        emit('connected', {'message': '连接成功', 'timestamp': datetime.now().isoformat()})
    
    @socketio.on('disconnect')
    def handle_disconnect():
        """客户端断开"""
        print(f"[WebSocket] 客户端断开")
    
    @socketio.on('subscribe')
    def handle_subscribe(data):
        """订阅数据频道"""
        channels = data.get('channels', [])
        print(f"[WebSocket] 订阅频道: {channels}")
        emit('subscribed', {'channels': channels})
    
    @socketio.on('request_stats')
    def handle_request_stats():
        """请求统计数据"""
        from app import create_app, db
        from app.models import Order, Vehicle, Node
        
        app = create_app()
        with app.app_context():
            try:
                stats = {
                    'total_orders': Order.query.count(),
                    'pending_orders': Order.query.filter_by(status='pending').count(),
                    'in_transit': Order.query.filter_by(status='in_transit').count(),
                    'delivered': Order.query.filter_by(status='delivered').count(),
                    'available_vehicles': Vehicle.query.filter_by(status='available').count(),
                    'total_vehicles': Vehicle.query.count(),
                    'total_nodes': Node.query.count(),
                    'timestamp': datetime.now().isoformat()
                }
                emit('stats_update', stats)
            except Exception as e:
                emit('error', {'message': str(e)})
    
    @socketio.on('request_vehicle_locations')
    def handle_request_locations():
        """请求车辆位置"""
        generator = get_data_generator()
        locations = generator.get_vehicle_locations()
        emit('vehicle_locations', {'locations': locations})
    
    # 启动数据生成器并添加监听器
    generator = get_data_generator()
    generator.add_listener(broadcast_event)
    generator.start()
    
    return socketio


def broadcast_event(event_type, data):
    """广播事件到所有客户端"""
    global socketio
    
    if socketio is None:
        return
    
    try:
        if event_type == 'new_order':
            socketio.emit('new_order', {
                'order_id': data.order_id,
                'order_number': data.order_number,
                'customer_name': data.customer_name,
                'cargo_name': data.cargo_name,
                'priority': data.priority,
                'status': data.status,
                'timestamp': data.timestamp
            })
        elif event_type == 'vehicle_location':
            socketio.emit('vehicle_location', {
                'vehicle_id': data.vehicle_id,
                'plate_number': data.plate_number,
                'latitude': data.latitude,
                'longitude': data.longitude,
                'speed': data.speed,
                'heading': data.heading,
                'status': data.status,
                'timestamp': data.timestamp
            })
    except Exception as e:
        print(f"[广播错误] {e}")


def broadcast_stats():
    """广播统计数据"""
    global socketio
    
    if socketio is None:
        return
    
    from app import create_app, db
    from app.models import Order, Vehicle, Node
    
    app = create_app()
    with app.app_context():
        try:
            stats = {
                'total_orders': Order.query.count(),
                'pending_orders': Order.query.filter_by(status='pending').count(),
                'in_transit': Order.query.filter_by(status='in_transit').count(),
                'delivered': Order.query.filter_by(status='delivered').count(),
                'available_vehicles': Vehicle.query.filter_by(status='available').count(),
                'total_vehicles': Vehicle.query.count(),
                'total_nodes': Node.query.count(),
                'timestamp': datetime.now().isoformat()
            }
            socketio.emit('stats_update', stats)
        except Exception as e:
            print(f"[统计广播错误] {e}")


def get_socketio():
    """获取 SocketIO 实例"""
    return socketio
