#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试数据生成服务
生成模拟的节点、车辆、订单等数据
"""

import random
from datetime import datetime, timedelta
from app.models import db
from app.models import Node, Vehicle, Order, Route, User
from app.models.audit import AuditLog


class TestDataGenerator:
    """测试数据生成器"""
    
    # 中国主要城市坐标
    CITIES = [
        {'name': '北京', 'province': '北京市', 'city': '北京市', 'district': '朝阳区', 
         'lon': 116.457470, 'lat': 39.908823},
        {'name': '上海', 'province': '上海市', 'city': '上海市', 'district': '浦东新区', 
         'lon': 121.544, 'lat': 31.230},
        {'name': '广州', 'province': '广东省', 'city': '广州市', 'district': '天河区', 
         'lon': 113.330, 'lat': 23.135},
        {'name': '深圳', 'province': '广东省', 'city': '深圳市', 'district': '南山区', 
         'lon': 114.057, 'lat': 22.543},
        {'name': '杭州', 'province': '浙江省', 'city': '杭州市', 'district': '西湖区', 
         'lon': 120.155, 'lat': 30.274},
        {'name': '成都', 'province': '四川省', 'city': '成都市', 'district': '武侯区', 
         'lon': 104.066, 'lat': 30.573},
        {'name': '武汉', 'province': '湖北省', 'city': '武汉市', 'district': '洪山区', 
         'lon': 114.305, 'lat': 30.593},
        {'name': '西安', 'province': '陕西省', 'city': '西安市', 'district': '雁塔区', 
         'lon': 108.940, 'lat': 34.342},
        {'name': '南京', 'province': '江苏省', 'city': '南京市', 'district': '鼓楼区', 
         'lon': 118.796, 'lat': 32.060},
        {'name': '重庆', 'province': '重庆市', 'city': '重庆市', 'district': '渝北区', 
         'lon': 106.551, 'lat': 29.563},
        {'name': '苏州', 'province': '江苏省', 'city': '苏州市', 'district': '工业园区', 
         'lon': 120.619, 'lat': 31.299},
        {'name': '天津', 'province': '天津市', 'city': '天津市', 'district': '和平区', 
         'lon': 117.200, 'lat': 39.084},
    ]
    
    # 节点类型
    NODE_TYPES = ['warehouse', 'distribution', 'customer', 'supplier']
    
    # 车牌前缀
    PLATE_PREFIXES = ['京', '沪', '粤', '浙', '苏', '川', '鄂', '陕', '渝', '津']
    
    # 车辆品牌
    VEHICLE_BRANDS = [
        ('东风', '天龙'),
        ('解放', 'J6'),
        ('福田', '奥铃'),
        ('重汽', '豪沃'),
        ('陕汽', '德龙'),
        ('江淮', '骏铃'),
        ('五十铃', 'ELF'),
        ('奔驰', 'Actros'),
        ('沃尔沃', 'FH'),
    ]
    
    # 司机姓名
    DRIVER_NAMES = [
        '张师傅', '李师傅', '王师傅', '赵师傅', '刘师傅',
        '陈师傅', '杨师傅', '黄师傅', '周师傅', '吴师傅',
        '郑师傅', '孙师傅', '马师傅', '朱师傅', '胡师傅'
    ]
    
    # 货物类型
    CARGO_TYPES = ['电子产品', '服装鞋帽', '食品饮料', '日用百货', '建材家居', 
                   '机械设备', '化工原料', '医药用品', '生鲜水果', '图书文具']
    
    # 车辆状态
    VEHICLE_STATUSES = ['available', 'in_use', 'maintenance', 'offline']
    
    # 订单状态
    ORDER_STATUSES = ['pending', 'in_transit', 'delivered', 'cancelled']
    
    # 优先级
    PRIORITIES = ['low', 'normal', 'high', 'urgent']
    
    def __init__(self):
        self.created_nodes = []
        self.created_vehicles = []
        self.created_orders = []
    
    def generate_nodes(self, count=20, clear_existing=False):
        """生成节点数据"""
        import time
        
        if clear_existing:
            Node.query.delete()
            db.session.commit()
        
        # 使用时间戳生成唯一代码
        base_code = int(time.time()) % 100000
        
        nodes = []
        
        for i in range(count):
            city = random.choice(self.CITIES)
            node_type = random.choice(self.NODE_TYPES)
            
            # 类型名称映射
            type_names = {
                'warehouse': '仓库',
                'distribution': '配送站',
                'customer': '客户',
                'supplier': '供应商'
            }
            
            # 类型前缀
            type_prefix = {
                'warehouse': 'WH',
                'distribution': 'DS',
                'customer': 'CU',
                'supplier': 'SU'
            }
            
            # 根据类型生成名称
            if node_type == 'warehouse':
                name = f"{city['name']}{type_names[node_type]}{random.randint(1, 5)}号"
            elif node_type == 'distribution':
                name = f"{city['name']}{city['district']}{type_names[node_type]}"
            elif node_type == 'customer':
                name = f"{random.choice(['华为', '阿里', '腾讯', '京东', '美团', '小米', '字节', '百度'])}科技"
            else:
                name = f"{random.choice(['顺丰', '京东', '菜鸟', '中通', '圆通'])}供应链"
            
            # 坐标偏移（模拟实际位置分布）
            lon_offset = random.uniform(-0.1, 0.1)
            lat_offset = random.uniform(-0.05, 0.05)
            
            # 生成唯一代码
            unique_code = f"{type_prefix[node_type]}-{base_code + i}"
            
            node = Node(
                name=name,
                code=unique_code,
                type=node_type,
                province=city['province'],
                city=city['city'],
                district=city['district'],
                address=f"{city['district']}{random.randint(1, 999)}号",
                longitude=city['lon'] + lon_offset,
                latitude=city['lat'] + lat_offset,
                contact_phone=f"1{random.choice(['3', '5', '8'])}{random.randint(100000000, 999999999)}",
                status='active'
            )
            
            db.session.add(node)
            nodes.append(node)
        
        db.session.commit()
        self.created_nodes = nodes
        return nodes
    
    def generate_vehicles(self, count=15, clear_existing=False):
        """生成车辆数据"""
        import time
        
        if clear_existing:
            Vehicle.query.delete()
            db.session.commit()
        
        # 使用时间戳生成唯一车牌
        base_num = int(time.time()) % 100000
        
        vehicles = []
        
        for i in range(count):
            prefix = random.choice(self.PLATE_PREFIXES)
            brand, model = random.choice(self.VEHICLE_BRANDS)
            
            # 载重 (吨)
            load_capacity = random.choice([2, 5, 8, 10, 15, 20, 30])
            
            vehicle = Vehicle(
                plate_number=f"{prefix}A{base_num + i}",
                vehicle_type='truck' if load_capacity > 10 else 'van',
                brand=brand,
                model=model,
                load_capacity=load_capacity,
                capacity=load_capacity * 1.2,  # 体积
                driver_name=random.choice(self.DRIVER_NAMES),
                driver_phone=f"1{random.choice(['3', '5', '8'])}{random.randint(100000000, 999999999)}",
                status=random.choices(
                    self.VEHICLE_STATUSES,
                    weights=[0.5, 0.3, 0.1, 0.1]
                )[0]
            )
            
            db.session.add(vehicle)
            vehicles.append(vehicle)
        
        db.session.commit()
        self.created_vehicles = vehicles
        return vehicles
    
    def generate_orders(self, count=50, clear_existing=False):
        """生成订单数据"""
        import time
        
        if clear_existing:
            Order.query.delete()
            db.session.commit()
        
        # 使用时间戳生成唯一订单号
        base_num = int(time.time()) % 100000
        
        # 确保有节点数据
        if not self.created_nodes:
            self.created_nodes = Node.query.all()
        
        if len(self.created_nodes) < 2:
            raise ValueError("至少需要 2 个节点才能生成订单")
        
        orders = []
        
        for i in range(count):
            # 随机选择起点和终点
            nodes = random.sample(self.created_nodes, 2)
            start_node, end_node = nodes[0], nodes[1]
            
            # 计算距离（简化计算）
            distance = self._calculate_distance(
                start_node.latitude, start_node.longitude,
                end_node.latitude, end_node.longitude
            )
            
            # 生成订单日期（最近 30 天）
            days_ago = random.randint(0, 30)
            order_date = datetime.now() - timedelta(days=days_ago)
            
            # 根据日期确定状态
            if days_ago > 7:
                status = random.choices(
                    self.ORDER_STATUSES,
                    weights=[0.05, 0.1, 0.8, 0.05]
                )[0]
            elif days_ago > 3:
                status = random.choices(
                    self.ORDER_STATUSES,
                    weights=[0.1, 0.4, 0.45, 0.05]
                )[0]
            else:
                status = random.choices(
                    self.ORDER_STATUSES,
                    weights=[0.3, 0.5, 0.15, 0.05]
                )[0]
            
            cargo_type = random.choice(self.CARGO_TYPES)
            weight = round(random.uniform(0.5, 20), 2)
            
            order = Order(
                order_number=f"ORD{base_num + i}",
                cargo_name=cargo_type,
                cargo_type=cargo_type,
                weight=weight,
                volume=weight * random.uniform(0.8, 1.5),
                pickup_node_id=start_node.id,
                origin_name=start_node.name,
                origin_address=start_node.address,
                origin_lat=start_node.latitude,
                origin_lng=start_node.longitude,
                delivery_node_id=end_node.id,
                destination_name=end_node.name,
                destination_address=end_node.address,
                destination_lat=end_node.latitude,
                destination_lng=end_node.longitude,
                sender_name=f"{random.choice(['张', '李', '王', '赵', '刘'])}{random.choice(['先生', '女士'])}",
                sender_phone=f"1{random.choice(['3', '5', '8'])}{random.randint(100000000, 999999999)}",
                receiver_name=f"{random.choice(['陈', '杨', '黄', '周', '吴'])}{random.choice(['先生', '女士'])}",
                receiver_phone=f"1{random.choice(['3', '5', '8'])}{random.randint(100000000, 999999999)}",
                status=status,
                priority=random.choices(
                    self.PRIORITIES,
                    weights=[0.2, 0.5, 0.2, 0.1]
                )[0],
                distance=distance,
                estimated_cost=distance * random.uniform(3, 8),
                created_at=order_date,
                started_at=order_date + timedelta(hours=random.randint(2, 24)) if status != 'pending' else None,
                completed_at=order_date + timedelta(hours=random.randint(24, 72)) if status == 'delivered' else None
            )
            
            db.session.add(order)
            orders.append(order)
        
        db.session.commit()
        self.created_orders = orders
        return orders
    
    def generate_routes(self, count=30, clear_existing=False):
        """生成路线数据"""
        import time
        
        if clear_existing:
            Route.query.delete()
            db.session.commit()
        
        # 确保有节点数据
        if not self.created_nodes:
            self.created_nodes = Node.query.all()
        
        if len(self.created_nodes) < 2:
            raise ValueError("至少需要 2 个节点才能生成路线")
        
        routes = []
        existing_pairs = set()  # 避免重复路线
        
        for i in range(count):
            # 随机选择起点和终点（确保不同）
            attempts = 0
            while attempts < 10:
                nodes = random.sample(self.created_nodes, 2)
                start_node, end_node = nodes[0], nodes[1]
                pair = (start_node.id, end_node.id)
                if pair not in existing_pairs:
                    existing_pairs.add(pair)
                    break
                attempts += 1
            else:
                continue
            
            # 计算距离
            distance = self._calculate_distance(
                start_node.latitude, start_node.longitude,
                end_node.latitude, end_node.longitude
            )
            
            # 估算时间（假设平均时速 60km/h）
            duration = round(distance / 60, 2)
            
            # 计算成本
            fuel_cost = distance * 0.8  # 约 0.8 元/km 油费
            toll_cost = distance * 0.5  # 约 0.5 元/km 过路费
            
            route = Route(
                name=f"{start_node.name} → {end_node.name}",
                start_node_id=start_node.id,
                end_node_id=end_node.id,
                origin=start_node.name,
                destination=end_node.name,
                distance=distance,
                duration=duration,
                estimated_time=duration,
                fuel_cost=fuel_cost,
                toll_cost=toll_cost,
                status='active'
            )
            
            db.session.add(route)
            routes.append(route)
        
        db.session.commit()
        self.created_routes = routes
        return routes
    
    def generate_all(self, nodes_count=20, vehicles_count=15, orders_count=50, routes_count=30, clear_existing=False):
        """生成所有测试数据"""
        result = {
            'nodes': [],
            'vehicles': [],
            'orders': [],
            'routes': [],
            'success': False,
            'message': ''
        }
        
        try:
            nodes = self.generate_nodes(nodes_count, clear_existing)
            vehicles = self.generate_vehicles(vehicles_count, clear_existing)
            routes = self.generate_routes(routes_count, clear_existing)
            orders = self.generate_orders(orders_count, clear_existing)
            
            result['nodes'] = [{'id': n.id, 'name': n.name, 'type': n.type} for n in nodes]
            result['vehicles'] = [{'id': v.id, 'plate_number': v.plate_number, 'status': v.status} for v in vehicles]
            result['orders'] = [{'id': o.id, 'order_number': o.order_number, 'status': o.status} for o in orders]
            result['routes'] = [{'id': r.id, 'name': r.name, 'distance': r.distance} for r in routes]
            result['success'] = True
            result['message'] = f"成功生成: {len(nodes)} 个节点, {len(vehicles)} 辆车, {len(routes)} 条路线, {len(orders)} 个订单"
        except Exception as e:
            import traceback
            traceback.print_exc()
            result['success'] = False
            result['error'] = str(e)
        
        return result
    
    def _calculate_distance(self, lat1, lon1, lat2, lon2):
        """计算两点间距离（公里）- 使用 Haversine 公式简化版"""
        from math import radians, sin, cos, sqrt, atan2
        
        R = 6371  # 地球半径（公里）
        
        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * atan2(sqrt(a), sqrt(1-a))
        
        return round(R * c, 2)


# 全局实例
test_data_generator = TestDataGenerator()
