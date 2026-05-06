#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试数据库连接
"""

import os
import sys
from sqlalchemy import create_engine, inspect
from sqlalchemy.exc import OperationalError

def test_direct_db_connection():
    print("="*60)
    print("直接测试数据库连接")
    print("="*60)
    
    # 获取正确的数据库路径
    current_dir = os.getcwd()
    project_root = os.path.dirname(current_dir)
    db_path = os.path.join(project_root, 'data', 'logistics.db')
    
    print(f"Current directory: {current_dir}")
    print(f"Project root: {project_root}")
    print(f"Database path: {db_path}")
    print(f"Database exists: {os.path.exists(db_path)}")
    print(f"Database file size: {os.path.getsize(db_path) if os.path.exists(db_path) else 'N/A'} bytes")
    
    # 测试SQLite直接连接
    try:
        import sqlite3
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        print(f"SQLite direct connection successful!")
        print(f"Tables in database: {[table[0] for table in tables]}")
        conn.close()
        print("SQLite connection closed")
    except Exception as e:
        print(f"SQLite direct connection failed: {e}")
    
    # 测试SQLAlchemy连接
    try:
        from sqlalchemy import create_engine
        engine_url = f"sqlite:///{db_path}"
        print(f"Engine URL: {engine_url}")
        
        engine = create_engine(engine_url)
        
        # 测试连接
        with engine.connect() as conn:
            result = conn.execute("SELECT 1")
            print(f"SQLAlchemy connection successful! Result: {result.fetchone()}")
        
        # 检查表
        inspector = inspect(engine)
        table_names = inspector.get_table_names()
        print(f"SQLAlchemy tables: {table_names}")
        
    except Exception as e:
        print(f"SQLAlchemy connection failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_direct_db_connection()