"""
供应商相关 Schema
"""

from datetime import datetime, date
from typing import Optional, List
from decimal import Decimal
from pydantic import BaseModel, Field
from . import BaseSchema


# ==================== 基础 Schema ====================

class SupplierBase(BaseSchema):
    """供应商基础字段"""
    code: str = Field(..., max_length=50, description="供应商编码")
    name: str = Field(..., max_length=200, description="供应商名称")
    type: Optional[str] = Field(None, max_length=50, description="类型")
    industry: Optional[str] = Field(None, max_length=100, description="行业")
    address: Optional[str] = Field(None, description="地址")
    phone: Optional[str] = Field(None, max_length=50, description="电话")
    email: Optional[str] = Field(None, max_length=100, description="邮箱")
    contact_person: Optional[str] = Field(None, max_length=100, description="联系人")
    license_no: Optional[str] = Field(None, max_length=100, description="许可证号")
    license_expire: Optional[date] = Field(None, description="许可证到期日")
    qualification_level: Optional[str] = Field(None, max_length=50, description="资质等级")
    bank_name: Optional[str] = Field(None, max_length=100, description="开户银行")
    bank_account: Optional[str] = Field(None, max_length=50, description="银行账号")


# ==================== 请求 Schema ====================

class SupplierCreate(SupplierBase):
    """创建供应商请求"""
    cooperation_start: Optional[date] = Field(None, description="合作开始日期")


class SupplierUpdate(BaseSchema):
    """更新供应商请求"""
    name: Optional[str] = Field(None, max_length=200)
    type: Optional[str] = None
    industry: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    contact_person: Optional[str] = None
    license_no: Optional[str] = None
    license_expire: Optional[date] = None
    qualification_level: Optional[str] = None
    bank_name: Optional[str] = None
    bank_account: Optional[str] = None
    cooperation_start: Optional[date] = None
    kraljic_category: Optional[str] = None
    status: Optional[str] = None


class SupplierEvaluation(BaseSchema):
    """供应商评估请求"""
    quality_score: float = Field(..., ge=0, le=5, description="质量评分")
    delivery_score: float = Field(..., ge=0, le=5, description="交付评分")
    cost_score: float = Field(..., ge=0, le=5, description="成本评分")
    service_score: float = Field(..., ge=0, le=5, description="服务评分")


# ==================== 响应 Schema ====================

class SupplierResponse(SupplierBase):
    """供应商响应"""
    id: int
    cooperation_start: Optional[date] = None
    status: str = Field(default="active")
    kraljic_category: Optional[str] = Field(None, description="Kraljic分类")
    quality_score: Optional[float] = None
    delivery_score: Optional[float] = None
    cost_score: Optional[float] = None
    service_score: Optional[float] = None
    total_score: Optional[float] = None
    risk_level: Optional[str] = None
    last_evaluation_date: Optional[date] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class SupplierBrief(BaseSchema):
    """供应商简要信息"""
    id: int
    code: str
    name: str
    type: Optional[str] = None
    status: str


class SupplierRiskBase(BaseSchema):
    """供应商风险基础字段"""
    risk_type: str = Field(..., max_length=50, description="风险类型")
    risk_level: str = Field(..., max_length=20, description="风险等级")
    risk_score: Optional[float] = Field(None, ge=0, le=100, description="风险分数")
    description: Optional[str] = Field(None, description="风险描述")
    impact: Optional[str] = Field(None, description="影响")
    mitigation: Optional[str] = Field(None, description="缓解措施")


class SupplierRiskCreate(SupplierRiskBase):
    """创建风险记录"""
    supplier_id: int = Field(..., description="供应商ID")


class SupplierRiskResponse(SupplierRiskBase):
    """风险记录响应"""
    id: int
    supplier_id: int
    supplier_name: Optional[str] = None
    status: str
    reported_by: Optional[str] = None
    reported_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[str] = None
