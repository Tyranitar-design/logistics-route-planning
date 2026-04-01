#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
数据模型定义 - 匹配数据库实际结构
"""

from datetime import datetime
from app import db


class User(db.Model):
    """用户模型"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(100))
    real_name = db.Column(db.String(50))
    phone = db.Column(db.String(20))
    role = db.Column(db.String(20), default='user')  # admin, manager, user
    status = db.Column(db.String(20), default='active')  # active, inactive
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'real_name': self.real_name,
            'phone': self.phone,
            'role': self.role,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None
        }


class Node(db.Model):
    """节点模型 - 仓库、站点、客户位置"""
    __tablename__ = 'nodes'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    code = db.Column(db.String(20), unique=True)
    type = db.Column(db.String(20), nullable=False)  # warehouse, station, customer
    province = db.Column(db.String(50))
    city = db.Column(db.String(50))
    district = db.Column(db.String(50))
    address = db.Column(db.String(200))
    longitude = db.Column(db.Float)
    latitude = db.Column(db.Float)
    contact_person = db.Column(db.String(50))
    contact_phone = db.Column(db.String(20))
    capacity = db.Column(db.Float)  # 容量（吨/立方米）
    status = db.Column(db.String(20), default='active')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'code': self.code,
            'type': self.type,
            'province': self.province,
            'city': self.city,
            'district': self.district,
            'address': self.address,
            'longitude': self.longitude,
            'latitude': self.latitude,
            'contact_person': self.contact_person,
            'contact_phone': self.contact_phone,
            'capacity': self.capacity,
            'status': self.status
        }


class Route(db.Model):
    """路线模型"""
    __tablename__ = 'routes'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    start_node_id = db.Column(db.Integer, db.ForeignKey('nodes.id'), nullable=False)
    end_node_id = db.Column(db.Integer, db.ForeignKey('nodes.id'), nullable=False)
    distance = db.Column(db.Float)  # 公里
    duration = db.Column(db.Float)  # 小时（行驶时间）
    road_type = db.Column(db.String(50))  # highway, national, provincial
    toll_cost = db.Column(db.Float)
    fuel_cost = db.Column(db.Float)
    status = db.Column(db.String(20), default='active')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    start_node = db.relationship('Node', foreign_keys=[start_node_id])
    end_node = db.relationship('Node', foreign_keys=[end_node_id])
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'start_node_id': self.start_node_id,
            'end_node_id': self.end_node_id,
            'start_node': self.start_node.to_dict() if self.start_node else None,
            'end_node': self.end_node.to_dict() if self.end_node else None,
            'distance': self.distance,
            'duration': self.duration,
            'road_type': self.road_type,
            'toll_cost': self.toll_cost,
            'fuel_cost': self.fuel_cost,
            'status': self.status
        }


class Vehicle(db.Model):
    """车辆模型"""
    __tablename__ = 'vehicles'
    
    id = db.Column(db.Integer, primary_key=True)
    plate_number = db.Column(db.String(20), unique=True, nullable=False)
    vehicle_type = db.Column(db.String(50))  # truck, van, etc.
    brand = db.Column(db.String(50))
    model = db.Column(db.String(50))
    capacity_weight = db.Column(db.Float)  # 载重（吨）
    capacity_volume = db.Column(db.Float)  # 容积（立方米）
    driver_name = db.Column(db.String(50))
    driver_phone = db.Column(db.String(20))
    status = db.Column(db.String(20), default='available')  # available, in_use, maintenance
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'plate_number': self.plate_number,
            'vehicle_type': self.vehicle_type,
            'brand': self.brand,
            'model': self.model,
            'capacity_weight': self.capacity_weight,
            'capacity_volume': self.capacity_volume,
            'driver_name': self.driver_name,
            'driver_phone': self.driver_phone,
            'status': self.status
        }


class Order(db.Model):
    """订单模型 - 匹配数据库实际结构"""
    __tablename__ = 'orders'
    
    id = db.Column(db.Integer, primary_key=True)
    order_number = db.Column(db.String(50), unique=True, nullable=False)
    customer_name = db.Column(db.String(100))
    customer_phone = db.Column(db.String(20))
    pickup_node_id = db.Column(db.Integer, db.ForeignKey('nodes.id'))
    delivery_node_id = db.Column(db.Integer, db.ForeignKey('nodes.id'))
    cargo_name = db.Column(db.String(100))
    cargo_type = db.Column(db.String(50))
    weight = db.Column(db.Float)
    volume = db.Column(db.Float)
    priority = db.Column(db.String(20), default='normal')
    status = db.Column(db.String(20), default='pending')
    vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicles.id'))
    estimated_delivery = db.Column(db.DateTime)
    actual_delivery = db.Column(db.DateTime)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    pickup_node = db.relationship('Node', foreign_keys=[pickup_node_id])
    delivery_node = db.relationship('Node', foreign_keys=[delivery_node_id])
    vehicle = db.relationship('Vehicle', backref='orders')
    
    def to_dict(self):
        return {
            'id': self.id,
            'order_number': self.order_number,
            'customer_name': self.customer_name,
            'customer_phone': self.customer_phone,
            'pickup_node_id': self.pickup_node_id,
            'delivery_node_id': self.delivery_node_id,
            'pickup_node': self.pickup_node.to_dict() if self.pickup_node else None,
            'delivery_node': self.delivery_node.to_dict() if self.delivery_node else None,
            'cargo_name': self.cargo_name,
            'cargo_type': self.cargo_type,
            'weight': self.weight,
            'volume': self.volume,
            'priority': self.priority,
            'status': self.status,
            'vehicle_id': self.vehicle_id,
            'vehicle': self.vehicle.to_dict() if self.vehicle else None,
            'estimated_delivery': self.estimated_delivery.isoformat() if self.estimated_delivery else None,
            'actual_delivery': self.actual_delivery.isoformat() if self.actual_delivery else None,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
