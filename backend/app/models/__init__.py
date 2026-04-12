"""
数据模型统一出口
"""

from flask_sqlalchemy import SQLAlchemy

# 在 models 中定义唯一的 db 实例
db = SQLAlchemy()

# 导入所有模型
from app.models.user import User
from app.models.node import Node
from app.models.vehicle import Vehicle
from app.models.order import Order
from app.models.route import Route
from app.models.task import Task, LocationHistory, Message, Photo
from app.models.supplier import Supplier, SupplierContract, SupplierSettlement, SupplierRisk
from app.models.audit import AuditLog
from app.models.oil_price import OilPrice
from app.models.network import NetworkScenario, NetworkNode, NetworkEdge

# 导出所有模型
__all__ = [
    'db',
    'User',
    'Node',
    'Vehicle',
    'Order',
    'Route',
    'Task',
    'LocationHistory',
    'Message',
    'Photo',
    'Supplier',
    'SupplierContract',
    'SupplierSettlement',
    'SupplierRisk',
    'AuditLog',
    'OilPrice',
    'NetworkScenario',
    'NetworkNode',
    'NetworkEdge',
]
