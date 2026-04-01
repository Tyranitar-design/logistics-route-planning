#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""创建测试订单"""

from app import create_app, db
from app.models import Order, Node
from datetime import datetime
import random

app = create_app()
with app.app_context():
    # 获取节点
    nodes = Node.query.all()
    if len(nodes) < 2:
        print('节点不足')
    else:
        # 创建测试订单
        customers = ['张三', '李四', '王五', '赵六', '钱七', '孙八', '周九', '吴十']
        cargos = ['电子产品', '服装', '食品', '家具', '机械配件', '日用品', '建材', '化工原料']
        priorities = ['normal', 'normal', 'normal', 'express', 'urgent']

        for i in range(10):
            order = Order(
                order_number='TEST{}{}'.format(datetime.now().strftime("%Y%m%d"), 100+i),
                customer_name=random.choice(customers),
                customer_phone='138{}'.format(random.randint(10000000, 99999999)),
                pickup_node_id=random.choice(nodes).id,
                delivery_node_id=random.choice(nodes).id,
                cargo_name=random.choice(cargos),
                weight=round(random.uniform(0.5, 5.0), 2),
                volume=round(random.uniform(1.0, 20.0), 2),
                priority=random.choice(priorities),
                status='pending',
                created_at=datetime.utcnow()
            )
            db.session.add(order)

        db.session.commit()
        print('已创建 10 个测试订单')
