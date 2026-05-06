#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试run.py文件是否能正常工作
"""

import os
import sys

# 切换到backend目录
backend_dir = r'D:\物流路径规划系统项目\backend'
os.chdir(backend_dir)
print(f"Current directory: {os.getcwd()}")

# 添加backend目录到Python路径
sys.path.insert(0, backend_dir)

try:
    print("Attempting to import run.py...")
    
    # 导入run模块
    import run
    
    print("run.py imported successfully!")
    
    # 检查app创建
    print("Creating Flask app...")
    app = run.create_app()
    
    print("Flask app created successfully!")
    print(f"Database URI in app: {app.config.get('SQLALCHEMY_DATABASE_URI', 'NOT SET')}")
    
    # 测试数据库连接
    print("Testing database connection...")
    with app.app_context():
        # 尝试访问数据库
        from app.models import db
        
        # 测试基本连接
        with db.engine.connect() as conn:
            result = conn.execute(db.text("SELECT 1")).fetchone()
            print(f"Database connection test result: {result}")
    
    print("\n" + "="*60)
    print("RUN.PY TEST: PASSED")
    print("run.py文件可以正常导入和使用")
    print("="*60)
    
except Exception as e:
    print(f"Error importing or using run.py: {e}")
    import traceback
    traceback.print_exc()