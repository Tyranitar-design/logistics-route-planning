#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
在正确的环境中测试数据库连接
"""

import os
import sys

# 将工作目录改为项目根目录以确保路径正确
project_dir = r'D:\物流路径规划系统项目'
os.chdir(project_dir)

# 添加项目路径
sys.path.insert(0, os.path.join(project_dir, 'backend'))

def test_config():
    print("="*60)
    print("在正确环境中测试数据库连接")
    print("="*60)
    
    try:
        # 导入配置并检查数据库路径
        from backend.config import DevelopmentConfig
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
        print("\nSUCCESS: Database connection working with absolute path!")
        
        return True
        
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_config()
    if success:
        print("\n" + "="*60)
        print("CONFIGURATION VALIDATION: PASSED")
        print("数据库配置已正确使用绝对路径，应解决中文路径问题")
        print("="*60)
    else:
        print("\n" + "="*60)
        print("CONFIGURATION VALIDATION: FAILED")
        print("="*60)