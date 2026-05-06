#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试更新后的配置
"""

import os
import sys

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_updated_config():
    print("="*60)
    print("测试更新后的配置")
    print("="*60)
    
    try:
        # 导入配置并检查数据库路径
        from config import DevelopmentConfig
        print(f"SQLALCHEMY_DATABASE_URI: {DevelopmentConfig.SQLALCHEMY_DATABASE_URI}")
        
        # 检查路径是否存在
        db_path = DevelopmentConfig.SQLALCHEMY_DATABASE_URI.replace('sqlite:///', '')
        print(f"Database path: {db_path}")
        print(f"Path exists: {os.path.exists(db_path)}")
        print(f"Directory exists: {os.path.exists(os.path.dirname(db_path))}")
        
        # 测试 Flask-SQLAlchemy 连接
        from app import create_app
        from app.models import db, User
        import sqlite3
        
        # 创建应用
        app = create_app('development')
        print("Flask app created successfully")
        
        # 检查配置
        print(f"App SQLALCHEMY_DATABASE_URI: {app.config['SQLALCHEMY_DATABASE_URI']}")
        
        # 在应用上下文中测试数据库连接
        with app.app_context():
            print("In application context...")
            
            # 检查是否有表
            from sqlalchemy import text
            result = db.session.execute(text("SELECT name FROM sqlite_master WHERE type='table';"))
            tables = [row[0] for row in result]
            print(f"Tables in database: {tables}")
            
            # 检查用户表记录数
            user_count = db.session.query(User).count()
            print(f"User count: {user_count}")
            
            print("SUCCESS: Database connection working!")
            
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_updated_config()