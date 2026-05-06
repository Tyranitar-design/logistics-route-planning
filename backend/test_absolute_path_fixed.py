#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试使用绝对路径连接数据库
"""

import os
import sys
import sqlite3
from urllib.parse import quote

def test_absolute_path():
    print("="*60)
    print("测试使用绝对路径连接数据库")
    print("="*60)
    
    # 获取绝对路径
    current_dir = os.getcwd()
    project_root = os.path.dirname(current_dir)
    db_path = os.path.join(project_root, 'data', 'logistics.db')
    
    print(f"Original path: {db_path}")
    print(f"Exists: {os.path.exists(db_path)}")
    
    # 使用 pathlib 获取绝对路径
    import pathlib
    abs_path = pathlib.Path(db_path).resolve()
    print(f"Absolute path: {abs_path}")
    
    # 使用正向斜杠的绝对路径
    abs_path_str = str(abs_path).replace('\\', '/')
    print(f"Abs path with forward slashes: {abs_path_str}")
    
    # 测试不同的URI格式
    uris_to_test = [
        f'sqlite:///{abs_path_str}',  # 原始格式
        f'sqlite:///{quote(abs_path_str)}',  # URL编码
    ]
    
    for i, uri in enumerate(uris_to_test):
        print(f"\nTest {i+1}: {uri}")
        try:
            from sqlalchemy import create_engine
            engine = create_engine(uri)
            with engine.connect() as conn:
                result = conn.execute("SELECT 1 as test")
                print(f"  SUCCESS: {result.fetchone()}")
        except Exception as e:
            print(f"  FAILED: {e}")

def test_working_solution():
    print("\n" + "="*60)
    print("测试可行的解决方案")
    print("="*60)
    
    # 获取绝对路径
    current_dir = os.getcwd()
    project_root = os.path.dirname(current_dir)
    db_path = os.path.join(project_root, 'data', 'logistics.db')
    
    import pathlib
    abs_path = pathlib.Path(db_path).resolve()
    abs_path_str = str(abs_path).replace('\\', '/')
    
    # 使用三斜线格式（对于Windows绝对路径）
    sqlite_uri = f'sqlite:///{abs_path_str}'
    print(f"Using URI: {sqlite_uri}")
    
    try:
        from sqlalchemy import create_engine
        from sqlalchemy import text
        
        engine = create_engine(sqlite_uri)
        print("Engine created successfully")
        
        with engine.connect() as conn:
            result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table';"))
            tables = [row[0] for row in result]
            print(f"Tables: {tables[:10]}")  # 显示前10个表
            
            # 测试查询用户表
            result = conn.execute(text("SELECT COUNT(*) FROM users;"))
            user_count = result.scalar()
            print(f"User count: {user_count}")
            
        print("SUCCESS: Database connection works with absolute path!")
        return sqlite_uri
        
    except Exception as e:
        print(f"FAILED: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    test_absolute_path()
    final_uri = test_working_solution()
    if final_uri:
        print(f"\n建议使用的数据库URI: {final_uri}")