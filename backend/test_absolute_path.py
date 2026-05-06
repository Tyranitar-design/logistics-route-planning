#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试新配置的数据库连接
"""

import os
import sys

# 添加项目路径
sys.path.insert(0, r'D:\物流路径规划系统项目\backend')

def test_database_connection():
    print("="*60)
    print("测试新配置的数据库连接")
    print("="*60)
    
    try:
        # 导入配置并检查数据库路径
        from config import DevelopmentConfig
        print(f"Database URI: {DevelopmentConfig.SQLALCHEMY_DATABASE_URI}")
        
        # 检查路径
        db_path = DevelopmentConfig.SQLALCHEMY_DATABASE_URI.replace('sqlite:///', '')
        print(f"Database path: {db_path}")
        print(f"Path exists: {os.path.exists(db_path)}")
        print(f"Directory exists: {os.path.exists(os.path.dirname(db_path))}")
        
        # 手动使用SQLite连接进行测试
        import sqlite3
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 检查表
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        print(f"Tables in database: {[table[0] for table in tables]}")
        
        # 检查用户表
        if 'users' in [table[0] for table in tables]:
            cursor.execute("SELECT COUNT(*) FROM users;")
            user_count = cursor.fetchone()[0]
            print(f"User count: {user_count}")
        
        conn.close()
        print("\n✓ SUCCESS: Database connection working with absolute path!")
        
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_database_connection()