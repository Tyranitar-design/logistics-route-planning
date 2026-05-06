#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
生成正确的数据库URL
"""

import os
import urllib.parse

# 获取数据库路径
project_root = r'D:\物流路径规划系统项目'
data_dir = os.path.join(project_root, 'data')
db_path = os.path.abspath(os.path.join(data_dir, 'logistics.db'))

print(f"原始路径: {db_path}")

# 将Windows路径转换为URL格式
# 1. 将反斜杠替换为正斜杠
db_path_forward_slash = db_path.replace("\\", "/")
print(f"转换斜杠: {db_path_forward_slash}")

# 2. URL编码路径
encoded_path = urllib.parse.quote(db_path_forward_slash, safe="/:")
print(f"URL编码后: {encoded_path}")

# 3. 创建SQLite URL
sqlite_url = f"sqlite:///{encoded_path}"
print(f"SQLite URL: {sqlite_url}")

# 验证SQLite可以使用此URL
import sqlite3
try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT 1")
    result = cursor.fetchone()
    print(f"SQLite连接测试: {result}")
    conn.close()
    print("SQLite连接成功!")
except Exception as e:
    print(f"SQLite连接失败: {e}")

print("\n正确的URL格式应该是: sqlite:///D:/path/to/database.db")
print("其中D:/path/to/database.db部分需要URL编码")