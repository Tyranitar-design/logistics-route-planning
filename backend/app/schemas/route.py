"""
路线相关 Schema
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from . import BaseSchema


# ==================== 基础 Schema ====================

class RouteBase(BaseSchema):
    """路线基础字段"""
    name: str = Field(..., max_length=100, description="路线名称")
    start_node_id: Optional[int] = Field(None, description="起点节点ID")
    end_node_id: Optional[int] = Field(None, description="终点节点ID")
    origin: Optional[str] = Field(None, max_length=100, description="起点名称")
    destination: Optional[str] = Field(None, max_length=100, description="终点名称")
    distance: Optional[float] = Field(None, ge=0, description="距离(km)")
    duration: Optional[float] = Field(None, ge=0, description="预计时长(小时)")
    toll_cost: Optional[float] = Field(None, ge=0, description="过路费")
    fuel_cost: Optional[float] = Field(None, ge=0, description="油费")
    route_data: Optional[str] = Field(None, description="路线JSON数据")


# ==================== 请求 Schema ====================

class RouteCreate(RouteBase):
    """创建路线请求"""
    pass


class RouteUpdate(BaseSchema):
    """更新路线请求"""
    name: Optional[str] = Field(None, max_length=100)
    start_node_id: Optional[int] = None
    end_node_id: Optional[int] = None
    origin: Optional[str] = None
    destination: Optional[str] = None
    distance: Optional[float] = Field(None, ge=0)
    duration: Optional[float] = Field(None, ge=0)
    toll_cost: Optional[float] = Field(None, ge=0)
    fuel_cost: Optional[float] = Field(None, ge=0)
    route_data: Optional[str] = None
    status: Optional[str] = None


# ==================== 响应 Schema ====================

class RouteResponse(RouteBase):
    """路线响应"""
    id: int
    estimated_time: Optional[float] = None
    status: str = Field(default="active")
    created_at: Optional[datetime] = None


class RouteDetail(RouteResponse):
    """路线详情（含节点信息）"""
    start_node: Optional[dict] = None
    end_node: Optional[dict] = None

    @property
    def total_cost(self) -> float:
        return (self.toll_cost or 0) + (self.fuel_cost or 0)


class RouteBrief(BaseSchema):
    """路线简要信息"""
    id: int
    name: str
    origin: Optional[str] = None
    destination: Optional[str] = None
    distance: Optional[float] = None
