#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试Flask-SQLAlchemy连接
"""

import os
import sys

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_flask_sqlalchemy():
    print("="*60)
    print("测试 Flask-SQLAlchemy 连接")
    print("="*60)
    
    try:
        from app import create_app
        from app.models import db, User
        import sqlite3
        
        # 创建应用
        app = create_app('development')
        print("Flask app created successfully")
        
        # 测试在应用上下文中访问数据库
        with app.app_context():
            print("In application context...")
            
            # 尝试列出所有表
            from sqlalchemy import text
            result = db.session.execute(text("SELECT name FROM sqlite_master WHERE type='table';"))
            tables = [row[0] for row in result]
            print(f"Tables found: {tables}")
            
            # 尝试查询用户表
            user_count = db.session.query(User).count()
            print(f"User table record count: {user_count}")
            
            # 如果用户表不为空，查询一些用户
            if user_count > 0:
                users = db.session.query(User).limit(5).all()
                print(f"Sample users: {[u.username for u in users]}")
            
            print("Database connection test passed!")
            
    except Exception as e:
        print(f"Flask-SQLAlchemy connection failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_flask_sqlalchemy()