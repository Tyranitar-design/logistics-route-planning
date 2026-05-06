#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试数据库连接修复
"""

import os
import sys

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_db_connection():
    print("="*60)
    print("测试数据库连接修复")
    print("="*60)
    
    try:
        from config import config
        cfg = config['development']
        print(f"Development DB URI: {cfg.SQLALCHEMY_DATABASE_URI}")
        
        # 提取数据库文件路径
        db_file_path = cfg.SQLALCHEMY_DATABASE_URI.replace("sqlite:///", "")
        print(f"Database file path: {db_file_path}")
        print(f"DB file exists: {os.path.exists(db_file_path)}")
        print(f"DB file dir exists: {os.path.exists(os.path.dirname(db_file_path))}")
        
        # 测试应用创建
        from app import create_app
        app = create_app('development')
        print("Application created successfully with corrected DB path")
        
        # 测试数据库连接
        with app.app_context():
            from app.models import db
            # 简单测试是否能访问数据库
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            print(f"Database connected successfully, tables: {len(tables)}")
            if tables:
                print(f"Table names: {tables[:5]}...")  # 显示前5个表名
        
        print("\n" + "="*60)
        print("DATABASE CONNECTION TEST PASSED")
        print("="*60)
        
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        print("\n" + "="*60)
        print("DATABASE CONNECTION TEST FAILED")
        print("="*60)

if __name__ == "__main__":
    test_db_connection()