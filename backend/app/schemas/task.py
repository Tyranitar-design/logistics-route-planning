"""
任务相关 Schema（司机端）
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from . import BaseSchema


# ==================== 基础 Schema ====================

class TaskBase(BaseSchema):
    """任务基础字段"""
    order_id: int = Field(..., description="订单ID")
    driver_id: Optional[int] = Field(None, description="司机ID")
    vehicle_id: Optional[int] = Field(None, description="车辆ID")
    status: str = Field(default="pending", description="状态")


# ==================== 请求 Schema ====================

class TaskCreate(TaskBase):
    """创建任务请求"""
    pass


class TaskUpdate(BaseSchema):
    """更新任务请求"""
    status: Optional[str] = None
    pickup_lat: Optional[float] = None
    pickup_lng: Optional[float] = None
    delivery_lat: Optional[float] = None
    delivery_lng: Optional[float] = None
    pickup_photo: Optional[str] = None
    delivery_photo: Optional[str] = None
    delivery_remark: Optional[str] = None
    actual_receiver: Optional[str] = None
    receiver_phone_confirm: Optional[str] = None
    signature: Optional[str] = None
    rating: Optional[float] = Field(None, ge=1, le=5)
    feedback: Optional[str] = None


class TaskStatusUpdate(BaseSchema):
    """更新任务状态"""
    status: str = Field(..., description="新状态")
    latitude: Optional[float] = Field(None, description="当前纬度")
    longitude: Optional[float] = Field(None, description="当前经度")
    photo: Optional[str] = Field(None, description="照片(base64)")
    remark: Optional[str] = Field(None, description="备注")


# ==================== 响应 Schema ====================

class TaskResponse(TaskBase):
    """任务响应"""
    id: int
    accepted_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    arrive_pickup_at: Optional[datetime] = None
    pickup_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    pickup_lat: Optional[float] = None
    pickup_lng: Optional[float] = None
    delivery_lat: Optional[float] = None
    delivery_lng: Optional[float] = None
    actual_receiver: Optional[str] = None
    rating: Optional[float] = None
    feedback: Optional[str] = None
    created_at: Optional[datetime] = None


class TaskDetail(TaskResponse):
    """任务详情"""
    order: Optional[dict] = None
    driver: Optional[dict] = None
    vehicle: Optional[dict] = None
