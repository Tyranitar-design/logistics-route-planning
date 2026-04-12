"""
Pydantic Schema 分层设计
用于 API 请求验证和响应序列化

分层结构：
- Base: 基础字段
- Create: 创建请求
- Update: 更新请求
- Response: 响应数据
- List: 列表响应（带分页）
"""

from datetime import datetime
from typing import Optional, List, Generic, TypeVar
from pydantic import BaseModel, Field, ConfigDict

T = TypeVar('T')


class BaseSchema(BaseModel):
    """Schema 基类"""
    model_config = ConfigDict(from_attributes=True)


class PaginationMeta(BaseModel):
    """分页元数据"""
    total: int = Field(description="总数")
    page: int = Field(description="当前页")
    per_page: int = Field(description="每页条数")
    total_pages: int = Field(description="总页数")


class PaginatedResponse(BaseModel, Generic[T]):
    """分页响应"""
    success: bool = True
    data: List[T]
    pagination: PaginationMeta


# 导出所有 Schema
from .user import (
    UserBase, UserCreate, UserUpdate, UserLogin, PasswordChange,
    UserResponse, UserBrief, LoginResponse
)
from .node import (
    NodeBase, NodeCreate, NodeUpdate, NodeResponse, NodeBrief
)
from .order import (
    OrderBase, OrderCreate, OrderUpdate, OrderResponse, OrderDetail, OrderBrief
)
from .vehicle import (
    VehicleBase, VehicleCreate, VehicleUpdate, VehicleLocationUpdate,
    VehicleResponse, VehicleBrief
)
from .route import (
    RouteBase, RouteCreate, RouteUpdate, RouteResponse, RouteDetail, RouteBrief
)
from .supplier import (
    SupplierBase, SupplierCreate, SupplierUpdate, SupplierEvaluation,
    SupplierResponse, SupplierBrief, SupplierRiskBase, SupplierRiskCreate, SupplierRiskResponse
)
from .task import (
    TaskBase, TaskCreate, TaskUpdate, TaskStatusUpdate,
    TaskResponse, TaskDetail
)

__all__ = [
    # 基础类
    'BaseSchema', 'PaginationMeta', 'PaginatedResponse',
    # 用户
    'UserBase', 'UserCreate', 'UserUpdate', 'UserLogin', 'PasswordChange',
    'UserResponse', 'UserBrief', 'LoginResponse',
    # 节点
    'NodeBase', 'NodeCreate', 'NodeUpdate', 'NodeResponse', 'NodeBrief',
    # 订单
    'OrderBase', 'OrderCreate', 'OrderUpdate', 'OrderResponse', 'OrderDetail', 'OrderBrief',
    # 车辆
    'VehicleBase', 'VehicleCreate', 'VehicleUpdate', 'VehicleLocationUpdate',
    'VehicleResponse', 'VehicleBrief',
    # 路线
    'RouteBase', 'RouteCreate', 'RouteUpdate', 'RouteResponse', 'RouteDetail', 'RouteBrief',
    # 供应商
    'SupplierBase', 'SupplierCreate', 'SupplierUpdate', 'SupplierEvaluation',
    'SupplierResponse', 'SupplierBrief', 'SupplierRiskBase', 'SupplierRiskCreate', 'SupplierRiskResponse',
    # 任务
    'TaskBase', 'TaskCreate', 'TaskUpdate', 'TaskStatusUpdate', 'TaskResponse', 'TaskDetail',
]
