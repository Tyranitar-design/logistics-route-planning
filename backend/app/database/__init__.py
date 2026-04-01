"""
数据库模块
提供数据库路径解析和初始化功能
"""
import os
import sqlite3
from typing import Optional

# 从 models 导入统一的 db 实例，避免创建多个 SQLAlchemy 实例
from app.models import db

# 项目根目录（backend 的上级目录）
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DATABASE_DIR = os.path.join(PROJECT_ROOT, "backend", "database")


def get_db_path(db_name: str) -> str:
    """
    获取数据库文件的完整路径

    Args:
        db_name: 数据库文件名（如 Price.db、app.db）

    Returns:
        数据库文件的完整路径
    """
    os.makedirs(DATABASE_DIR, exist_ok=True)
    return os.path.join(DATABASE_DIR, db_name)


def get_connection(db_name: str):
    """获取数据库连接（便捷函数）"""
    return sqlite3.connect(get_db_path(db_name))


# 导出 db 实例，供 from app.database import db 使用
__all__ = ["db", "get_db_path", "get_connection"]
