#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试数据库连接和API
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models import User, Node, Vehicle, Order, Route

def test_database():
    """测试数据库连接"""
    app = create_app()
    
    with app.app_context():
        print('=' * 50)
        print('数据库连接测试')
        print('=' * 50)
        
        # 测试数据库连接
        try:
            # 查询用户
            users = User.query.all()
            print(f'\n用户数量: {len(users)}')
            for user in users:
                print(f'  - {user.username} ({user.role})')
            
            # 查询节点
            nodes = Node.query.all()
            print(f'\n节点数量: {len(nodes)}')
            for node in nodes[:5]:
                print(f'  - {node.name} ({node.type})')
            
            # 查询车辆
            vehicles = Vehicle.query.all()
            print(f'\n车辆数量: {len(vehicles)}')
            for vehicle in vehicles[:5]:
                print(f'  - {vehicle.plate_number} ({vehicle.status})')
            
            # 查询订单
            orders = Order.query.all()
            print(f'\n订单数量: {len(orders)}')
            for order in orders[:5]:
                print(f'  - 订单#{order.id}: {order.status}')
            
            # 查询路线
            routes = Route.query.all()
            print(f'\n路线数量: {len(routes)}')
            for route in routes[:5]:
                print(f'  - 路线#{route.id}: {route.name}')
            
            print('\n' + '=' * 50)
            print('数据库连接正常！所有表都可以访问。')
            print('=' * 50)
            
        except Exception as e:
            print(f'\n错误: {e}')
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    test_database()
