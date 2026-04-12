"""
节点相关 Schema
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from . import BaseSchema


# ==================== 基础 Schema ====================

class NodeBase(BaseSchema):
    """节点基础字段"""
    name: str = Field(..., max_length=100, description="节点名称")
    code: Optional[str] = Field(None, max_length=50, description="节点编码")
    type: str = Field(..., description="类型: warehouse/distribution/customer")
    province: Optional[str] = Field(None, max_length=50, description="省")
    city: Optional[str] = Field(None, max_length=50, description="市")
    district: Optional[str] = Field(None, max_length=50, description="区")
    address: Optional[str] = Field(None, max_length=200, description="详细地址")
    longitude: Optional[float] = Field(None, ge=-180, le=180, description="经度")
    latitude: Optional[float] = Field(None, ge=-90, le=90, description="纬度")
    contact_name: Optional[str] = Field(None, max_length=50, description="联系人")
    contact_phone: Optional[str] = Field(None, max_length=20, description="联系电话")
    capacity: Optional[float] = Field(None, ge=0, description="容量")
    notes: Optional[str] = Field(None, description="备注")


# ==================== 请求 Schema ====================

class NodeCreate(NodeBase):
    """创建节点请求"""
    pass


class NodeUpdate(BaseSchema):
    """更新节点请求"""
    name: Optional[str] = Field(None, max_length=100)
    code: Optional[str] = Field(None, max_length=50)
    type: Optional[str] = None
    province: Optional[str] = None
    city: Optional[str] = None
    district: Optional[str] = None
    address: Optional[str] = None
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    contact_name: Optional[str] = None
    contact_phone: Optional[str] = None
    capacity: Optional[float] = Field(None, ge=0)
    notes: Optional[str] = None
    status: Optional[str] = None


# ==================== 响应 Schema ====================

class NodeResponse(NodeBase):
    """节点响应"""
    id: int
    status: str = Field(default="active")
    created_at: Optional[datetime] = None


class NodeBrief(BaseSchema):
    """节点简要信息（用于关联显示）"""
    id: int
    name: str
    city: Optional[str] = None
    type: Optional[str] = None
