"""
用户相关 Schema
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, EmailStr
from . import BaseSchema


# ==================== 基础 Schema ====================

class UserBase(BaseSchema):
    """用户基础字段"""
    username: str = Field(..., min_length=2, max_length=80, description="用户名")
    email: Optional[EmailStr] = Field(None, description="邮箱")
    real_name: Optional[str] = Field(None, max_length=50, description="真实姓名")
    phone: Optional[str] = Field(None, max_length=20, description="手机号")
    role: str = Field(default="user", description="角色: admin/user/driver")


# ==================== 请求 Schema ====================

class UserCreate(UserBase):
    """创建用户请求"""
    password: str = Field(..., min_length=6, max_length=100, description="密码")


class UserUpdate(BaseSchema):
    """更新用户请求"""
    email: Optional[EmailStr] = None
    real_name: Optional[str] = Field(None, max_length=50)
    phone: Optional[str] = Field(None, max_length=20)
    role: Optional[str] = None
    status: Optional[str] = None


class UserLogin(BaseSchema):
    """登录请求"""
    username: str = Field(..., description="用户名")
    password: str = Field(..., description="密码")


class PasswordChange(BaseSchema):
    """修改密码请求"""
    old_password: str = Field(..., description="旧密码")
    new_password: str = Field(..., min_length=6, description="新密码")


# ==================== 响应 Schema ====================

class UserResponse(UserBase):
    """用户响应"""
    id: int
    status: str = Field(default="active", description="状态")
    last_login: Optional[datetime] = None
    created_at: Optional[datetime] = None


class UserBrief(BaseSchema):
    """用户简要信息（用于关联）"""
    id: int
    username: str
    real_name: Optional[str] = None


class LoginResponse(BaseSchema):
    """登录响应"""
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    user: UserResponse
