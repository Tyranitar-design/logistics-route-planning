"""
WebSocket 实时推送服务
- 车辆位置实时推送（延迟<1秒）
- 订单状态变化实时通知
- 预警信息弹窗（天气/拥堵/异常）
"""

import threading
import time
import random
from datetime import datetime
from flask_socketio import SocketIO, emit
from flask import current_app, request

# 创建 SocketIO 实例（延迟初始化）
socketio = None

# 模拟车辆数据
vehicles_data = {
    '京A12345': {'lat': 39.90, 'lng': 116.41, 'status': 'in_transit', 'speed': 60, 'order_id': 1},
    '京B67890': {'lat': 31.23, 'lng': 121.47, 'status': 'in_transit', 'speed': 55, 'order_id': 2},
    '京C24680': {'lat': 23.13, 'lng': 113.26, 'status': 'idle', 'speed': 0, 'order_id': None},
    '京D13579': {'lat': 22.53, 'lng': 113.93, 'status': 'in_transit', 'speed': 70, 'order_id': 3},
    '京E86420': {'lat': 30.27, 'lng': 120.16, 'status': 'maintenance', 'speed': 0, 'order_id': None},
}

# 目标位置（模拟配送路线）
vehicle_routes = {
    '京A12345': {'target_lat': 31.23, 'target_lng': 121.47, 'name': '北京→上海'},
    '京B67890': {'target_lat': 30.27, 'target_lng': 120.16, 'name': '上海→杭州'},
    '京D13579': {'target_lat': 23.13, 'target_lng': 113.26, 'name': '深圳→广州'},
}

# 连接的客户端
connected_clients = set()

# 后台线程标志
running = False


def init_socketio(app):
    """初始化 SocketIO"""
    global socketio, running
    
    # 配置 CORS 允许所有来源
    socketio = SocketIO(
        app, 
        cors_allowed_origins="*", 
        async_mode='threading',
        logger=True,
        engineio_logger=True
    )
    
    return socketio


def get_all_vehicle_positions():
    """获取所有车辆位置"""
    positions = []
    for plate, data in vehicles_data.items():
        positions.append({
            'plate_number': plate,
            'lat': data['lat'],
            'lng': data['lng'],
            'status': data['status'],
            'speed': data['speed'],
            'order_id': data['order_id'],
            'last_update': datetime.now().isoformat()
        })
    return positions


def update_vehicle_position(plate_number, lat, lng, speed=None):
    """更新车辆位置"""
    if plate_number in vehicles_data:
        vehicles_data[plate_number]['lat'] = lat
        vehicles_data[plate_number]['lng'] = lng
        if speed is not None:
            vehicles_data[plate_number]['speed'] = speed
        vehicles_data[plate_number]['last_update'] = datetime.now().isoformat()


def simulate_vehicle_movement():
    """模拟车辆移动"""
    for plate, data in vehicles_data.items():
        if data['status'] != 'in_transit':
            continue
        
        route = vehicle_routes.get(plate)
        if not route:
            continue
        
        # 模拟移动（向目标靠近）
        lat_diff = route['target_lat'] - data['lat']
        lng_diff = route['target_lng'] - data['lng']
        
        # 每次移动约 0.01 度（约 1km）
        move_speed = 0.005 + random.uniform(-0.002, 0.002)
        
        if abs(lat_diff) > 0.01:
            data['lat'] += move_speed * (1 if lat_diff > 0 else -1)
        if abs(lng_diff) > 0.01:
            data['lng'] += move_speed * (1 if lng_diff > 0 else -1)
        
        # 更新速度
        data['speed'] = random.randint(50, 80)
        
        # 如果到达目标，重置到起点
        if abs(lat_diff) <= 0.02 and abs(lng_diff) <= 0.02:
            if plate == '京A12345':
                data['lat'], data['lng'] = 39.90, 116.41  # 北京
            elif plate == '京B67890':
                data['lat'], data['lng'] = 31.23, 121.47  # 上海
            elif plate == '京D13579':
                data['lat'], data['lng'] = 22.53, 113.93  # 深圳


def broadcast_vehicle_positions():
    """广播车辆位置"""
    if socketio:
        simulate_vehicle_movement()
        socketio.emit('vehicle_positions', get_all_vehicle_positions())


def broadcast_order_update(order_id, status, message):
    """广播订单状态更新"""
    if socketio:
        socketio.emit('order_update', {
            'order_id': order_id,
            'status': status,
            'message': message,
            'time': datetime.now().isoformat()
        })


def broadcast_alert(alert_type, title, message, level='warning'):
    """
    广播预警信息
    alert_type: weather / traffic / order / system
    level: info / warning / danger
    """
    if socketio:
        socketio.emit('alert', {
            'type': alert_type,
            'title': title,
            'message': message,
            'level': level,
            'time': datetime.now().isoformat()
        })


def generate_random_alert():
    """生成随机预警（演示用）"""
    alerts = [
        {'type': 'weather', 'title': '天气预警', 'message': '广州地区即将有大雨，请注意运输安全', 'level': 'warning'},
        {'type': 'traffic', 'title': '路况提醒', 'message': 'G2高速上海段拥堵，建议绕行', 'level': 'warning'},
        {'type': 'order', 'title': '订单异常', 'message': '订单 #15 配送延迟，已超时30分钟', 'level': 'danger'},
        {'type': 'vehicle', 'title': '车辆提醒', 'message': '京A12345 油量不足20%，请及时加油', 'level': 'warning'},
        {'type': 'system', 'title': '系统通知', 'message': '新订单 #28 已创建，等待分配车辆', 'level': 'info'},
    ]
    return random.choice(alerts)


def background_push_thread():
    """后台推送线程"""
    global running
    running = True
    alert_counter = 0
    
    print("[WebSocket] 后台推送线程已启动")
    
    while running:
        try:
            # 每 0.5 秒推送车辆位置
            broadcast_vehicle_positions()
            
            # 每 30 秒生成一条随机预警
            alert_counter += 1
            if alert_counter >= 60:  # 30 秒
                alert = generate_random_alert()
                broadcast_alert(alert['type'], alert['title'], alert['message'], alert['level'])
                alert_counter = 0
            
            time.sleep(0.5)
            
        except Exception as e:
            print(f"[WebSocket] 推送异常: {e}")
            time.sleep(1)


def start_background_push():
    """启动后台推送"""
    thread = threading.Thread(target=background_push_thread, daemon=True)
    thread.start()
    print("[WebSocket] 后台推送服务已启动")


def stop_background_push():
    """停止后台推送"""
    global running
    running = False
    print("[WebSocket] 后台推送服务已停止")


# 订单状态变更通知
def notify_order_created(order_id, customer_name, origin, destination):
    """通知新订单创建"""
    broadcast_order_update(
        order_id, 
        'pending',
        f'新订单 #{order_id} 已创建：{customer_name}，{origin} → {destination}'
    )
    broadcast_alert('order', '新订单', f'订单 #{order_id} 已创建，等待分配车辆', 'info')


def notify_order_assigned(order_id, plate_number):
    """通知订单已分配车辆"""
    broadcast_order_update(
        order_id,
        'assigned',
        f'订单 #{order_id} 已分配给车辆 {plate_number}'
    )


def notify_order_in_transit(order_id, plate_number):
    """通知订单开始运输"""
    broadcast_order_update(
        order_id,
        'in_transit',
        f'订单 #{order_id} 已由 {plate_number} 开始运输'
    )


def notify_order_delivered(order_id):
    """通知订单已送达"""
    broadcast_order_update(
        order_id,
        'delivered',
        f'订单 #{order_id} 已送达完成'
    )
    broadcast_alert('order', '订单完成', f'订单 #{order_id} 已成功送达', 'info')


# 天气预警
def notify_weather_alert(city, weather_type, description):
    """推送天气预警"""
    level = 'warning' if weather_type in ['大雨', '暴雨', '大风', '雾霾'] else 'info'
    broadcast_alert('weather', f'{city}天气预警', f'{city}地区{weather_type}，{description}', level)


# 路况预警
def notify_traffic_alert(route_name, description):
    """推送路况预警"""
    broadcast_alert('traffic', '路况提醒', f'{route_name}：{description}', 'warning')


# 车辆预警
def notify_vehicle_alert(plate_number, alert_type, description):
    """推送车辆预警"""
    level = 'danger' if alert_type in ['故障', '事故'] else 'warning'
    broadcast_alert('vehicle', f'{plate_number}提醒', description, level)