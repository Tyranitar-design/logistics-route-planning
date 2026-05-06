#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
直接从项目根目录测试Flask应用
"""

import os
import sys

# 确保工作目录是项目根目录
project_dir = r'D:\物流路径规划系统项目'
os.chdir(project_dir)

# 添加项目路径到sys.path
sys.path.insert(0, os.path.join(project_dir, 'backend'))

def test_flask_app():
    print("="*60)
    print("测试Flask应用初始化")
    print("="*60)
    
    try:
        # 直接从app模块导入应用实例
        from backend.app import create_app
        app = create_app()
        
        print("Flask应用创建成功!")
        print(f"数据库URI: {app.config['SQLALCHEMY_DATABASE_URI']}")
        
        # 尝试初始化数据库
        with app.app_context():
            from backend.app.models import db
            print("数据库上下文创建成功!")
            
            # 检查数据库连接
            with db.engine.connect() as conn:
                result = conn.execute(db.text("SELECT 1"))
                print("数据库连接测试成功!")
                
            # 检查表
            inspector = db.inspect(db.engine)
            tables = inspector.get_table_names()
            print(f"数据库表: {tables}")
            
        print("\nSUCCESS: Flask应用和数据库连接正常!")
        return True
        
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_flask_app()
    if success:
        print("\n" + "="*60)
        print("FLASK APP VALIDATION: PASSED")
        print("Flask应用和数据库配置正常工作")
        print("="*60)
    else:
        print("\n" + "="*60)
        print("FLASK APP VALIDATION: FAILED")
        print("="*60)