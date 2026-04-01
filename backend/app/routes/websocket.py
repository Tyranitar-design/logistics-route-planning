"""
WebSocket 路由
"""

from flask import request
from app.services.websocket_service import (
    socketio, 
    broadcast_vehicle_positions,
    broadcast_alert,
    notify_order_created,
    notify_weather_alert,
    notify_traffic_alert
)


def register_socketio_events(socketio_instance):
    """注册 SocketIO 事件"""
    
    @socketio_instance.on('connect')
    def handle_connect():
        """客户端连接"""
        from flask import request as flask_request
        print(f"[WS] 客户端连接: {flask_request.sid}")
        socketio_instance.emit('connected', {
            'message': 'WebSocket 连接成功',
            'time': __import__('datetime').datetime.now().isoformat()
        }, room=flask_request.sid)
    
    @socketio_instance.on('disconnect')
    def handle_disconnect():
        """客户端断开"""
        from flask import request as flask_request
        print(f"[WS] 客户端断开: {flask_request.sid}")
    
    @socketio_instance.on('subscribe_vehicles')
    def handle_subscribe_vehicles():
        """订阅车辆位置"""
        from flask import request as flask_request
        socketio_instance.emit('subscribed', {'channel': 'vehicles'}, room=flask_request.sid)
    
    @socketio_instance.on('subscribe_orders')
    def handle_subscribe_orders():
        """订阅订单更新"""
        from flask import request as flask_request
        socketio_instance.emit('subscribed', {'channel': 'orders'}, room=flask_request.sid)
    
    @socketio_instance.on('subscribe_alerts')
    def handle_subscribe_alerts():
        """订阅预警信息"""
        from flask import request as flask_request
        socketio_instance.emit('subscribed', {'channel': 'alerts'}, room=flask_request.sid)
    
    @socketio_instance.on('ping')
    def handle_ping():
        """心跳"""
        from flask import request as flask_request
        socketio_instance.emit('pong', {'time': __import__('datetime').datetime.now().isoformat()}, room=flask_request.sid)


# 手动触发预警的 API（用于测试）
def trigger_weather_alert(city, weather_type, description):
    """触发天气预警"""
    notify_weather_alert(city, weather_type, description)
    return {'success': True, 'message': '预警已发送'}


def trigger_traffic_alert(route_name, description):
    """触发路况预警"""
    notify_traffic_alert(route_name, description)
    return {'success': True, 'message': '预警已发送'}


def trigger_custom_alert(title, message, level='warning'):
    """触发自定义预警"""
    broadcast_alert('system', title, message, level)
    return {'success': True, 'message': '预警已发送'}
