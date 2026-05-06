#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试配置和数据库连接
"""

import os
import sys
from urllib.parse import urlparse

# 切换到backend目录
backend_dir = r'D:\物流路径规划系统项目\backend'
os.chdir(backend_dir)
print(f"Current directory: {os.getcwd()}")

# 添加backend目录到Python路径
sys.path.insert(0, backend_dir)

try:
    # 测试数据库URI的处理
    from config import DevelopmentConfig
    db_uri = DevelopmentConfig.SQLALCHEMY_DATABASE_URI
    print(f"原始数据库URI: {db_uri}")
    
    # 解析SQLite URI
    parsed = urlparse(db_uri)
    print(f"Parsed path: {parsed.path}")
    
    # 获取文件路径部分（去掉开头的/）
    file_path = parsed.path.lstrip('/')
    print(f"文件路径部分: {file_path}")
    
    # 转换为绝对路径（基于当前工作目录）
    abs_path = os.path.abspath(file_path)
    print(f"绝对路径: {abs_path}")
    print(f"文件是否存在: {os.path.exists(abs_path)}")
    
    # 检查父目录是否存在
    parent_dir = os.path.dirname(abs_path)
    print(f"父目录: {parent_dir}")
    print(f"父目录是否存在: {parent_dir and os.path.exists(parent_dir)}")
    
    # 尝试直接使用sqlite3连接
    import sqlite3
    print("\n尝试直接使用sqlite3连接:")
    try:
        conn = sqlite3.connect(abs_path)
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        print(f"SQLite3连接成功: {result}")
        conn.close()
        print("SQLite3连接关闭成功")
    except Exception as e:
        print(f"SQLite3连接失败: {e}")
    
    # 从app.py导入create_app并检查它如何获取配置
    print("\n测试应用创建过程:")
    from app import create_app
    app = create_app()
    
    # 检查应用的实际配置
    actual_uri = app.config.get('SQLALCHEMY_DATABASE_URI')
    print(f"应用中的数据库URI: {actual_uri}")
    
    # 解析应用中的URI
    if actual_uri:
        parsed_actual = urlparse(actual_uri)
        actual_file_path = parsed_actual.path.lstrip('/')
        actual_abs_path = os.path.abspath(actual_file_path)
        print(f"应用中解析的绝对路径: {actual_abs_path}")
        print(f"应用中文件是否存在: {os.path.exists(actual_abs_path)}")
    
    print("\n配置测试完成!")
    
except Exception as e:
    print(f"错误: {e}")
    import traceback
    traceback.print_exc()