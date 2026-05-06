#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
检查配置文件
"""

import os
import sys

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def check_config():
    print("检查配置文件...")
    
    try:
        from config import DevelopmentConfig
        print(f"SQLALCHEMY_DATABASE_URI: {DevelopmentConfig.SQLALCHEMY_DATABASE_URI}")
        
        # 检查数据库路径是否为绝对路径
        db_path = DevelopmentConfig.SQLALCHEMY_DATABASE_URI.replace('sqlite:///', '')
        print(f"数据库路径: {db_path}")
        print(f"是否为绝对路径: {os.path.isabs(db_path)}")
        
        # 解析绝对路径（如果是相对路径的话）
        if not os.path.isabs(db_path):
            # 这是一个相对路径，需要解析
            current_dir = os.getcwd()
            abs_path = os.path.abspath(os.path.join(current_dir, db_path))
            print(f"解析后的绝对路径: {abs_path}")
            print(f"文件存在: {os.path.exists(abs_path)}")
            print(f"所在目录存在: {os.path.exists(os.path.dirname(abs_path))}")
        else:
            print(f"文件存在: {os.path.exists(db_path)}")
            print(f"所在目录存在: {os.path.exists(os.path.dirname(db_path))}")
            
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_config()