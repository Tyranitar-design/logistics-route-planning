#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
调试路径生成逻辑
"""

import os

print("="*60)
print("调试路径生成逻辑")
print("="*60)

# 模拟配置文件中的路径生成逻辑
current_file = os.path.abspath(__file__)  # 当前文件的绝对路径
print(f"当前文件路径: {current_file}")

backend_dir = os.path.dirname(os.path.abspath(__file__))  # 当前文件所在的目录
print(f"当前文件目录: {backend_dir}")

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # 项目根目录
print(f"项目根目录: {project_root}")

# 但这不是正确的，因为我们是在不同位置运行这个脚本
# 应该指向真正的backend目录
true_backend_dir = r"D:\物流路径规划系统项目\backend"
true_project_root = r"D:\物流路径规划系统项目"

print(f"真实Backend目录: {true_backend_dir}")
print(f"真实项目根目录: {true_project_root}")

# 按照真实路径计算
data_dir = os.path.join(true_project_root, 'data')
print(f"数据目录: {data_dir}")

database_path = os.path.abspath(os.path.join(data_dir, 'logistics.db'))
print(f"数据库绝对路径: {database_path}")

sqlalchemy_uri = f'sqlite:///{database_path}'
print(f"SQLAlchemy URI: {sqlalchemy_uri}")

# 检查路径存在性
print(f"数据库文件存在: {os.path.exists(database_path)}")

# 现在检查相对路径
relative_db_path = "../data/logistics.db"
calculated_relative_path = os.path.abspath(os.path.join(backend_dir, relative_db_path))
print(f"相对路径解析结果: {calculated_relative_path}")
print(f"相对路径计算的文件存在: {os.path.exists(calculated_relative_path)}")