"""
订单相关 Schema
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from . import BaseSchema


# ==================== 基础 Schema ====================

class OrderBase(BaseSchema):
    """订单基础字段"""
    order_number: Optional[str] = Field(None, max_length=50, description="订单编号")
    customer_name: Optional[str] = Field(None, max_length=100, description="客户名称")
    customer_phone: Optional[str] = Field(None, max_length=20, description="客户电话")

    # 发货信息
    pickup_node_id: Optional[int] = Field(None, description="发货节点ID")
    origin_name: Optional[str] = Field(None, max_length=100, description="发货地")
    origin_address: Optional[str] = Field(None, max_length=200, description="发货地址")
    origin_lat: Optional[float] = Field(None, description="发货地纬度")
    origin_lng: Optional[float] = Field(None, description="发货地经度")
    sender_name: Optional[str] = Field(None, max_length=50, description="发件人")
    sender_phone: Optional[str] = Field(None, max_length=20, description="发件人电话")

    # 收货信息
    delivery_node_id: Optional[int] = Field(None, description="收货节点ID")
    destination_name: Optional[str] = Field(None, max_length=100, description="收货地")
    destination_address: Optional[str] = Field(None, max_length=200, description="收货地址")
    destination_lat: Optional[float] = Field(None, description="收货地纬度")
    destination_lng: Optional[float] = Field(None, description="收货地经度")
    receiver_name: Optional[str] = Field(None, max_length=50, description="收件人")
    receiver_phone: Optional[str] = Field(None, max_length=20, description="收件人电话")

    # 货物信息
    cargo_name: Optional[str] = Field(None, max_length=100, description="货物名称")
    cargo_type: Optional[str] = Field(None, max_length=50, description="货物类型")
    weight: Optional[float] = Field(None, ge=0, description="重量(kg)")
    volume: Optional[float] = Field(None, ge=0, description="体积(m³)")
    quantity: Optional[int] = Field(None, ge=0, description="数量")

    # 订单状态
    priority: str = Field(default="normal", description="优先级: urgent/normal/low")
    status: str = Field(default="pending", description="状态: pending/assigned/...")

    # 关联
    driver_id: Optional[int] = Field(None, description="司机ID")
    vehicle_id: Optional[int] = Field(None, description="车辆ID")

    # 费用
    freight: Optional[float] = Field(None, ge=0, description="运费")
    estimated_cost: Optional[float] = Field(None, ge=0, description="预估成本")
    actual_cost: Optional[float] = Field(None, ge=0, description="实际成本")

    # 距离/时间
    distance: Optional[float] = Field(None, ge=0, description="距离(km)")
    estimated_duration: Optional[float] = Field(None, ge=0, description="预计时长(分钟)")
    estimated_arrival: Optional[datetime] = Field(None, description="预计到达时间")

    # 备注
    notes: Optional[str] = Field(None, description="备注")


# ==================== 请求 Schema ====================

class OrderCreate(OrderBase):
    """创建订单请求"""
    order_number: str = Field(..., max_length=50, description="订单编号(必须唯一)")
    pickup_node_id: Optional[int] = Field(None, description="发货节点ID")
    delivery_node_id: Optional[int] = Field(None, description="收货节点ID")


class OrderUpdate(BaseSchema):
    """更新订单请求"""
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    origin_name: Optional[str] = None
    origin_address: Optional[str] = None
    origin_lat: Optional[float] = None
    origin_lng: Optional[float] = None
    destination_name: Optional[str] = None
    destination_address: Optional[str] = None
    destination_lat: Optional[float] = None
    destination_lng: Optional[float] = None
    receiver_name: Optional[str] = None
    receiver_phone: Optional[str] = None
    cargo_name: Optional[str] = None
    cargo_type: Optional[str] = None
    weight: Optional[float] = None
    volume: Optional[float] = None
    quantity: Optional[int] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    driver_id: Optional[int] = None
    vehicle_id: Optional[int] = None
    freight: Optional[float] = None
    estimated_cost: Optional[float] = None
    actual_cost: Optional[float] = None
    distance: Optional[float] = None
    estimated_duration: Optional[float] = None
    estimated_arrival: Optional[datetime] = None
    notes: Optional[str] = None


# ==================== 响应 Schema ====================

class OrderResponse(OrderBase):
    """订单响应"""
    id: int
    order_number: str
    pickup_node_id: int
    delivery_node_id: int
    created_at: Optional[datetime] = None
    accepted_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    arrive_pickup_at: Optional[datetime] = None
    pickup_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    rating: Optional[float] = None
    feedback: Optional[str] = None


class OrderDetail(OrderResponse):
    """订单详情（含关联信息）"""
    pickup_node: Optional[dict] = None
    delivery_node: Optional[dict] = None
    driver: Optional[dict] = None
    vehicle: Optional[dict] = None


class OrderBrief(BaseSchema):
    """订单简要信息"""
    id: int
    order_number: str
    status: str
    pickup_node_name: Optional[str] = None
    delivery_node_name: Optional[str] = None
    destination_name: Optional[str] = None
    freight: Optional[float] = None
    created_at: Optional[datetime] = None
