#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
网络场景模型 - 用于保存和管理物流网络设计场景
"""

from datetime import datetime
from app.models import db
import json


class NetworkScenario(db.Model):
    """网络场景模型"""
    __tablename__ = "network_scenarios"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    
    # 算法类型: p-median, covering, cflp
    algorithm = db.Column(db.String(50), nullable=False)
    
    # 输入数据 (JSON)
    customers = db.Column(db.Text)  # JSON 格式的客户数据
    candidates = db.Column(db.Text)  # JSON 格式的候选位置数据
    
    # 求解参数 (JSON)
    parameters = db.Column(db.Text)  # JSON 格式的参数
    
    # 求解结果 (JSON)
    selected_facilities = db.Column(db.Text)  # 选中的设施
    assignments = db.Column(db.Text)  # 客户-设施分配
    total_cost = db.Column(db.Float)
    total_distance = db.Column(db.Float)
    total_fixed_cost = db.Column(db.Float)
    transport_cost = db.Column(db.Float)
    solve_time = db.Column(db.Float)
    solver = db.Column(db.String(50))
    
    # 服务水平指标
    avg_distance = db.Column(db.Float)  # 平均配送距离
    max_distance = db.Column(db.Float)  # 最大配送距离
    service_level = db.Column(db.Float)  # 服务水平 (0-1)
    
    # 元数据
    status = db.Column(db.String(20), default="draft")  # draft, active, archived
    is_favorite = db.Column(db.Boolean, default=False)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "algorithm": self.algorithm,
            "customers": json.loads(self.customers) if self.customers else [],
            "candidates": json.loads(self.candidates) if self.candidates else [],
            "parameters": json.loads(self.parameters) if self.parameters else {},
            "selected_facilities": json.loads(self.selected_facilities) if self.selected_facilities else [],
            "assignments": json.loads(self.assignments) if self.assignments else {},
            "total_cost": self.total_cost,
            "total_distance": self.total_distance,
            "total_fixed_cost": self.total_fixed_cost,
            "transport_cost": self.transport_cost,
            "solve_time": self.solve_time,
            "solver": self.solver,
            "avg_distance": self.avg_distance,
            "max_distance": self.max_distance,
            "service_level": self.service_level,
            "status": self.status,
            "is_favorite": self.is_favorite,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class NetworkNode(db.Model):
    """网络节点模型 - 用于真实数据导入"""
    __tablename__ = "network_nodes"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), nullable=False)
    code = db.Column(db.String(50), unique=True)
    
    # 节点类型
    node_type = db.Column(db.String(30), nullable=False)  
    # 可选: supplier, factory, warehouse, dc, customer
    
    # 网络层级
    node_level = db.Column(db.Integer, default=1)
    # 1=供应商, 2=工厂, 3=中央仓, 4=区域DC, 5=客户
    
    # 位置信息
    province = db.Column(db.String(50))
    city = db.Column(db.String(50))
    address = db.Column(db.String(200))
    longitude = db.Column(db.Float)
    latitude = db.Column(db.Float)
    
    # 容量和成本
    capacity = db.Column(db.Float, default=0)  # 容量限制
    fixed_cost = db.Column(db.Float, default=0)  # 固定成本
    variable_cost = db.Column(db.Float, default=0)  # 变动成本
    
    # 需求（仅客户节点）
    demand = db.Column(db.Float, default=0)
    demand_variability = db.Column(db.Float, default=0)  # 需求波动系数
    
    # 服务参数
    service_radius = db.Column(db.Float, default=0)  # 服务半径
    lead_time_days = db.Column(db.Float, default=0)  # 提前期
    
    # 状态
    status = db.Column(db.String(20), default="active")
    is_candidate = db.Column(db.Boolean, default=False)  # 是否可作为候选位置
    
    # 元数据
    contact_name = db.Column(db.String(50))
    contact_phone = db.Column(db.String(20))
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "code": self.code,
            "node_type": self.node_type,
            "node_level": self.node_level,
            "province": self.province,
            "city": self.city,
            "address": self.address,
            "longitude": self.longitude,
            "latitude": self.latitude,
            "capacity": self.capacity,
            "fixed_cost": self.fixed_cost,
            "variable_cost": self.variable_cost,
            "demand": self.demand,
            "demand_variability": self.demand_variability,
            "service_radius": self.service_radius,
            "lead_time_days": self.lead_time_days,
            "status": self.status,
            "is_candidate": self.is_candidate,
            "contact_name": self.contact_name,
            "contact_phone": self.contact_phone,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class NetworkEdge(db.Model):
    """网络边模型 - 节点之间的连接关系"""
    __tablename__ = "network_edges"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    
    source_node_id = db.Column(db.Integer, db.ForeignKey('network_nodes.id'), nullable=False)
    target_node_id = db.Column(db.Integer, db.ForeignKey('network_nodes.id'), nullable=False)
    
    # 运输模式
    transport_mode = db.Column(db.String(30))  # road, rail, air, sea
    
    # 成本和时间
    unit_cost = db.Column(db.Float, default=0)  # 单位运输成本
    fixed_cost = db.Column(db.Float, default=0)  # 固定成本
    lead_time_days = db.Column(db.Float, default=0)  # 提前期
    
    # 容量
    capacity_limit = db.Column(db.Float, default=0)  # 容量限制
    
    # 距离
    distance_km = db.Column(db.Float, default=0)
    
    # 状态
    status = db.Column(db.String(20), default="active")
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            "id": self.id,
            "source_node_id": self.source_node_id,
            "target_node_id": self.target_node_id,
            "transport_mode": self.transport_mode,
            "unit_cost": self.unit_cost,
            "fixed_cost": self.fixed_cost,
            "lead_time_days": self.lead_time_days,
            "capacity_limit": self.capacity_limit,
            "distance_km": self.distance_km,
            "status": self.status,
        }
