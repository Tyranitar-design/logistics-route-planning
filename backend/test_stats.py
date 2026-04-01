#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试统计API
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models import Order, Node, Route, Vehicle
from datetime import datetime, timedelta
from sqlalchemy import func

app = create_app()

with app.app_context():
    print("=== 测试统计查询 ===\n")
    
    # 测试基本统计
    print("1. 基本统计:")
    print(f"   订单总数: {Order.query.count()}")
    print(f"   节点总数: {Node.query.count()}")
    print(f"   路线总数: {Route.query.count()}")
    print(f"   车辆总数: {Vehicle.query.count()}")
    
    # 测试订单趋势
    print("\n2. 订单趋势（最近7天）:")
    today = datetime.utcnow().date()
    for i in range(6, -1, -1):
        date = today - timedelta(days=i)
        try:
            count = Order.query.filter(
                Order.created_at.isnot(None),
                func.date(Order.created_at) == date
            ).count()
            print(f"   {date.strftime('%Y-%m-%d')}: {count} 个订单")
        except Exception as e:
            print(f"   {date.strftime('%Y-%m-%d')}: 查询失败 - {e}")
    
    # 测试订单状态分布
    print("\n3. 订单状态分布:")
    try:
        distribution = db.session.query(
            Order.status,
            func.count(Order.id).label('count')
        ).group_by(Order.status).all()
        
        for status, count in distribution:
            print(f"   {status}: {count}")
    except Exception as e:
        print(f"   查询失败: {e}")
    
    # 测试车辆状态
    print("\n4. 车辆状态分布:")
    try:
        status_count = db.session.query(
            Vehicle.status,
            func.count(Vehicle.id).label('count')
        ).group_by(Vehicle.status).all()
        
        for status, count in status_count:
            print(f"   {status}: {count}")
    except Exception as e:
        print(f"   查询失败: {e}")
    
    # 检查订单的 created_at 字段
    print("\n5. 检查订单 created_at 字段:")
    orders = Order.query.limit(5).all()
    for order in orders:
        print(f"   订单 {order.order_number}: created_at = {order.created_at}")