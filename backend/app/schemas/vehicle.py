"""
车辆相关 Schema
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from . import BaseSchema


# ==================== 基础 Schema ====================

class VehicleBase(BaseSchema):
    """车辆基础字段"""
    plate_number: str = Field(..., max_length=20, description="车牌号")
    vehicle_type: Optional[str] = Field(None, max_length=20, description="车辆类型")
    brand: Optional[str] = Field(None, max_length=50, description="品牌")
    model: Optional[str] = Field(None, max_length=50, description="型号")
    load_capacity: Optional[float] = Field(None, ge=0, description="载重(吨)")
    volume_capacity: Optional[float] = Field(None, ge=0, description="容积(m³)")
    driver_name: Optional[str] = Field(None, max_length=50, description="司机姓名")
    driver_phone: Optional[str] = Field(None, max_length=20, description="司机电话")
    current_location: Optional[str] = Field(None, max_length=100, description="当前位置")
    current_lat: Optional[float] = Field(None, description="当前纬度")
    current_lng: Optional[float] = Field(None, description="当前经度")
    notes: Optional[str] = Field(None, description="备注")


# ==================== 请求 Schema ====================

class VehicleCreate(VehicleBase):
    """创建车辆请求"""
    pass


class VehicleUpdate(BaseSchema):
    """更新车辆请求"""
    plate_number: Optional[str] = Field(None, max_length=20)
    vehicle_type: Optional[str] = None
    brand: Optional[str] = None
    model: Optional[str] = None
    load_capacity: Optional[float] = Field(None, ge=0)
    volume_capacity: Optional[float] = Field(None, ge=0)
    driver_id: Optional[int] = None
    driver_name: Optional[str] = None
    driver_phone: Optional[str] = None
    current_location: Optional[str] = None
    current_lat: Optional[float] = None
    current_lng: Optional[float] = None
    status: Optional[str] = None
    notes: Optional[str] = None


class VehicleLocationUpdate(BaseSchema):
    """更新车辆位置"""
    latitude: float = Field(..., ge=-90, le=90, description="纬度")
    longitude: float = Field(..., ge=-180, le=180, description="经度")
    location_name: Optional[str] = Field(None, description="位置名称")


# ==================== 响应 Schema ====================

class VehicleResponse(VehicleBase):
    """车辆响应"""
    id: int
    driver_id: Optional[int] = None
    status: str = Field(default="available", description="状态")
    last_update: Optional[datetime] = None
    created_at: Optional[datetime] = None


class VehicleBrief(BaseSchema):
    """车辆简要信息"""
    id: int
    plate_number: str
    vehicle_type: Optional[str] = None
    status: str
    driver_name: Optional[str] = None
