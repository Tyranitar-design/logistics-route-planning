#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
数据库初始化脚本
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models import User, Node, Route, Vehicle, Order
from werkzeug.security import generate_password_hash
from datetime import datetime, timedelta


def init_database():
    """初始化数据库"""
    app = create_app()
    
    with app.app_context():
        # 创建所有表
        print('正在创建数据库表...')
        db.create_all()
        print('数据库表创建完成!')
        
        # 检查是否已有数据
        if User.query.first() is not None:
            print('数据库已有数据，跳过初始化')
            return
        
        print('正在初始化基础数据...')
        
        # 创建管理员用户
        admin = User(
            username='admin',
            password_hash=generate_password_hash('admin123'),
            email='admin@logistics.com',
            real_name='系统管理员',
            phone='13800138000',
            role='admin',
            status='active'
        )
        db.session.add(admin)
        
        # 创建示例节点
        nodes_data = [
            {'name': '北京仓库', 'type': 'warehouse', 'address': '北京市朝阳区', 'longitude': 116.4074, 'latitude': 39.9042, 'contact_name': '张经理', 'contact_phone': '13800000001'},
            {'name': '上海仓库', 'type': 'warehouse', 'address': '上海市浦东新区', 'longitude': 121.4737, 'latitude': 31.2304, 'contact_name': '李经理', 'contact_phone': '13800000002'},
            {'name': '广州仓库', 'type': 'warehouse', 'address': '广州市天河区', 'longitude': 113.2644, 'latitude': 23.1291, 'contact_name': '王经理', 'contact_phone': '13800000003'},
            {'name': '深圳客户A', 'type': 'customer', 'address': '深圳市南山区', 'longitude': 113.9301, 'latitude': 22.5329, 'contact_name': '赵先生', 'contact_phone': '13800000004'},
            {'name': '杭州客户B', 'type': 'customer', 'address': '杭州市西湖区', 'longitude': 120.1551, 'latitude': 30.2741, 'contact_name': '钱女士', 'contact_phone': '13800000005'},
        ]
        
        nodes = []
        for data in nodes_data:
            node = Node(**data, status='active')
            db.session.add(node)
            nodes.append(node)
        
        # 创建示例车辆
        vehicles_data = [
            {'plate_number': '京A12345', 'vehicle_type': '货车', 'brand': '东风', 'model': '天龙', 'load_capacity': 10.0, 'volume_capacity': 50.0, 'driver_name': '司机甲', 'driver_phone': '13900000001'},
            {'plate_number': '沪B67890', 'vehicle_type': '货车', 'brand': '解放', 'model': 'J6', 'load_capacity': 15.0, 'volume_capacity': 70.0, 'driver_name': '司机乙', 'driver_phone': '13900000002'},
            {'plate_number': '粤C11111', 'vehicle_type': '厢式货车', 'brand': '福田', 'model': '欧马可', 'load_capacity': 5.0, 'volume_capacity': 30.0, 'driver_name': '司机丙', 'driver_phone': '13900000003'},
        ]
        
        vehicles = []
        for data in vehicles_data:
            vehicle = Vehicle(**data, status='available')
            db.session.add(vehicle)
            vehicles.append(vehicle)
        
        # 创建示例路线
        routes_data = [
            {'name': '北京-上海', 'origin_id': 1, 'destination_id': 2, 'distance': 1200, 'estimated_time': 14, 'fuel_cost': 800, 'toll_cost': 500, 'total_cost': 1300},
            {'name': '上海-广州', 'origin_id': 2, 'destination_id': 3, 'distance': 1500, 'estimated_time': 18, 'fuel_cost': 1000, 'toll_cost': 600, 'total_cost': 1600},
            {'name': '广州-深圳', 'origin_id': 3, 'destination_id': 4, 'distance': 150, 'estimated_time': 2, 'fuel_cost': 100, 'toll_cost': 50, 'total_cost': 150},
        ]
        
        for data in routes_data:
            route = Route(**data, status='active')
            db.session.add(route)
        
        # 创建示例订单
        orders_data = [
            {'order_number': 'ORD20260317001', 'customer_name': '测试客户1', 'customer_phone': '13800000006', 'pickup_node_id': 1, 'delivery_node_id': 4, 'cargo_name': '电子产品', 'cargo_type': '普货', 'weight': 500, 'volume': 2, 'priority': 'normal', 'status': 'pending'},
            {'order_number': 'ORD20260317002', 'customer_name': '测试客户2', 'customer_phone': '13800000007', 'pickup_node_id': 2, 'delivery_node_id': 5, 'cargo_name': '服装', 'cargo_type': '普货', 'weight': 200, 'volume': 1, 'priority': 'high', 'status': 'pending'},
        ]
        
        for data in orders_data:
            order = Order(**data, estimated_delivery=datetime.now() + timedelta(days=2))
            db.session.add(order)
        
        # 提交所有更改
        db.session.commit()
        print('基础数据初始化完成!')
        
        # 打印统计信息
        print(f'\n数据统计:')
        print(f'  用户: {User.query.count()} 条')
        print(f'  节点: {Node.query.count()} 条')
        print(f'  车辆: {Vehicle.query.count()} 条')
        print(f'  路线: {Route.query.count()} 条')
        print(f'  订单: {Order.query.count()} 条')


if __name__ == '__main__':
    init_database()
