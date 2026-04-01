#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
添加测试数据
"""

import os
import sys
import random

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models import User, Node, Route, Vehicle, Order

def add_test_data():
    """添加测试数据"""
    app = create_app('development')
    
    with app.app_context():
        print('📦 正在添加测试数据...\n')
        
        # 1. 添加节点数据
        print('📍 添加节点数据...')
        nodes_data = [
            {'name': '北京总仓', 'code': 'BJ-WH-001', 'type': 'warehouse', 'province': '北京市', 'city': '北京市', 'address': '朝阳区望京街道', 'longitude': 116.4814, 'latitude': 39.9905, 'capacity': 10000},
            {'name': '上海总仓', 'code': 'SH-WH-001', 'type': 'warehouse', 'province': '上海市', 'city': '上海市', 'address': '浦东新区张江镇', 'longitude': 121.4737, 'latitude': 31.2304, 'capacity': 12000},
            {'name': '广州总仓', 'code': 'GZ-WH-001', 'type': 'warehouse', 'province': '广东省', 'city': '广州市', 'address': '白云区太和镇', 'longitude': 113.2644, 'latitude': 23.1291, 'capacity': 8000},
            {'name': '北京配送站', 'code': 'BJ-ST-001', 'type': 'station', 'province': '北京市', 'city': '北京市', 'address': '海淀区中关村', 'longitude': 116.3114, 'latitude': 39.9755, 'capacity': 500},
            {'name': '上海配送站', 'code': 'SH-ST-001', 'type': 'station', 'province': '上海市', 'city': '上海市', 'address': '徐汇区漕河泾', 'longitude': 121.4037, 'latitude': 31.1804, 'capacity': 600},
            {'name': '南京中转站', 'code': 'NJ-TF-001', 'type': 'transfer', 'province': '江苏省', 'city': '南京市', 'address': '江宁区秣陵街道', 'longitude': 118.7969, 'latitude': 31.9560, 'capacity': 2000},
            {'name': '杭州中转站', 'code': 'HZ-TF-001', 'type': 'transfer', 'province': '浙江省', 'city': '杭州市', 'address': '余杭区仓前街道', 'longitude': 120.1551, 'latitude': 30.2741, 'capacity': 1800},
            {'name': '客户A', 'code': 'CU-001', 'type': 'customer', 'province': '北京市', 'city': '北京市', 'address': '朝阳区建国路88号', 'longitude': 116.4614, 'latitude': 39.9105, 'contact_person': '张三', 'contact_phone': '13800138001'},
            {'name': '客户B', 'code': 'CU-002', 'type': 'customer', 'province': '上海市', 'city': '上海市', 'address': '浦东新区陆家嘴', 'longitude': 121.5037, 'latitude': 31.2404, 'contact_person': '李四', 'contact_phone': '13800138002'},
            {'name': '客户C', 'code': 'CU-003', 'type': 'customer', 'province': '江苏省', 'city': '南京市', 'address': '玄武区新街口', 'longitude': 118.7969, 'latitude': 32.0560, 'contact_person': '王五', 'contact_phone': '13800138003'},
        ]
        
        nodes = []
        for data in nodes_data:
            node = Node(**data)
            db.session.add(node)
            nodes.append(node)
        
        db.session.commit()
        print(f'   ✅ 已添加 {len(nodes)} 个节点\n')
        
        # 2. 添加路线数据
        print('🛣️ 添加路线数据...')
        routes_data = [
            {'name': '北京-上海', 'code': 'R-BJ-SH', 'start_node_id': 1, 'end_node_id': 2, 'distance': 1200, 'duration': 14, 'toll_cost': 600, 'fuel_cost': 800, 'total_cost': 1400},
            {'name': '北京-广州', 'code': 'R-BJ-GZ', 'start_node_id': 1, 'end_node_id': 3, 'distance': 2100, 'duration': 24, 'toll_cost': 1050, 'fuel_cost': 1400, 'total_cost': 2450},
            {'name': '上海-广州', 'code': 'R-SH-GZ', 'start_node_id': 2, 'end_node_id': 3, 'distance': 1500, 'duration': 18, 'toll_cost': 750, 'fuel_cost': 1000, 'total_cost': 1750},
            {'name': '北京-南京', 'code': 'R-BJ-NJ', 'start_node_id': 1, 'end_node_id': 6, 'distance': 1000, 'duration': 12, 'toll_cost': 500, 'fuel_cost': 670, 'total_cost': 1170},
            {'name': '上海-杭州', 'code': 'R-SH-HZ', 'start_node_id': 2, 'end_node_id': 7, 'distance': 180, 'duration': 2.5, 'toll_cost': 90, 'fuel_cost': 120, 'total_cost': 210},
            {'name': '南京-杭州', 'code': 'R-NJ-HZ', 'start_node_id': 6, 'end_node_id': 7, 'distance': 280, 'duration': 3.5, 'toll_cost': 140, 'fuel_cost': 190, 'total_cost': 330},
        ]
        
        routes = []
        for data in routes_data:
            route = Route(**data)
            db.session.add(route)
            routes.append(route)
        
        db.session.commit()
        print(f'   ✅ 已添加 {len(routes)} 条路线\n')
        
        # 3. 添加车辆数据
        print('🚚 添加车辆数据...')
        vehicles_data = [
            {'plate_number': '京A12345', 'vehicle_type': '重型货车', 'brand': '东风', 'model': '天龙', 'capacity_weight': 20, 'capacity_volume': 60, 'driver_name': '赵师傅', 'driver_phone': '13900139001', 'status': 'available'},
            {'plate_number': '沪B67890', 'vehicle_type': '中型货车', 'brand': '解放', 'model': 'J6', 'capacity_weight': 10, 'capacity_volume': 35, 'driver_name': '钱师傅', 'driver_phone': '13900139002', 'status': 'available'},
            {'plate_number': '粤C11111', 'vehicle_type': '轻型货车', 'brand': '福田', 'model': '奥铃', 'capacity_weight': 5, 'capacity_volume': 20, 'driver_name': '孙师傅', 'driver_phone': '13900139003', 'status': 'in_use'},
            {'plate_number': '苏D22222', 'vehicle_type': '重型货车', 'brand': '重汽', 'model': '豪沃', 'capacity_weight': 25, 'capacity_volume': 70, 'driver_name': '周师傅', 'driver_phone': '13900139004', 'status': 'available'},
            {'plate_number': '浙E33333', 'vehicle_type': '中型货车', 'brand': '江淮', 'model': '格尔发', 'capacity_weight': 12, 'capacity_volume': 40, 'driver_name': '吴师傅', 'driver_phone': '13900139005', 'status': 'maintenance'},
        ]
        
        vehicles = []
        for data in vehicles_data:
            vehicle = Vehicle(**data)
            db.session.add(vehicle)
            vehicles.append(vehicle)
        
        db.session.commit()
        print(f'   ✅ 已添加 {len(vehicles)} 辆车\n')
        
        # 4. 添加订单数据
        print('📦 添加订单数据...')
        orders_data = [
            {'customer_name': '测试客户A', 'customer_phone': '13800000001', 'pickup_node_id': 1, 'delivery_node_id': 2, 'cargo_name': '电子产品', 'cargo_type': '普货', 'weight': 5.5, 'volume': 12, 'priority': 'normal', 'status': 'pending'},
            {'customer_name': '测试客户B', 'customer_phone': '13800000002', 'pickup_node_id': 2, 'delivery_node_id': 3, 'cargo_name': '服装', 'cargo_type': '普货', 'weight': 3.2, 'volume': 8, 'priority': 'urgent', 'status': 'pending'},
            {'customer_name': '测试客户C', 'customer_phone': '13800000003', 'pickup_node_id': 1, 'delivery_node_id': 6, 'cargo_name': '食品', 'cargo_type': '冷链', 'weight': 2.0, 'volume': 5, 'priority': 'express', 'status': 'assigned', 'vehicle_id': 1},
            {'customer_name': '测试客户D', 'customer_phone': '13800000004', 'pickup_node_id': 2, 'delivery_node_id': 7, 'cargo_name': '家具', 'cargo_type': '大件', 'weight': 8.0, 'volume': 25, 'priority': 'normal', 'status': 'in_transit', 'vehicle_id': 2},
            {'customer_name': '测试客户E', 'customer_phone': '13800000005', 'pickup_node_id': 6, 'delivery_node_id': 7, 'cargo_name': '建材', 'cargo_type': '普货', 'weight': 15.0, 'volume': 40, 'priority': 'normal', 'status': 'delivered'},
        ]
        
        orders = []
        for i, data in enumerate(orders_data):
            order = Order(
                order_number=f'ORD202603160{i+1}',
                **data
            )
            db.session.add(order)
            orders.append(order)
        
        db.session.commit()
        print(f'   ✅ 已添加 {len(orders)} 个订单\n')
        
        print('🎉 测试数据添加完成！\n')
        print('=' * 50)
        print('📊 数据统计：')
        print(f'   节点：{len(nodes)} 个')
        print(f'   路线：{len(routes)} 条')
        print(f'   车辆：{len(vehicles)} 辆')
        print(f'   订单：{len(orders)} 个')
        print('=' * 50)


if __name__ == '__main__':
    add_test_data()
