#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
在正确环境中检查数据库配置
"""

import os
import sys

# 保存当前目录
original_dir = os.getcwd()
print(f"Original directory: {original_dir}")

try:
    # 改变到项目根目录
    project_dir = r'D:\物流路径规划系统项目'
    os.chdir(project_dir)
    print(f"Changed to project directory: {os.getcwd()}")
    
    # 添加项目路径
    backend_path = os.path.join(project_dir, 'backend')
    sys.path.insert(0, backend_path)
    
    # 检查文件是否存在
    config_path = os.path.join(backend_path, 'config.py')
    print(f"Config file exists: {os.path.exists(config_path)}")
    
    # 从backend目录导入配置
    os.chdir(backend_path)
    print(f"Changed to backend directory: {os.getcwd()}")
    
    # 现在导入配置
    import config
    dev_config = config.DevelopmentConfig
    print(f"Database URI: {dev_config.SQLALCHEMY_DATABASE_URI}")
    
    # 解析数据库路径
    db_uri = dev_config.SQLALCHEMY_DATABASE_URI
    if db_uri.startswith('sqlite:///'):
        db_path = db_uri.replace('sqlite:///', '')
        # 如果是相对路径，则相对于当前工作目录计算
        if not os.path.isabs(db_path):
            abs_db_path = os.path.abspath(db_path)
        else:
            abs_db_path = db_path
            
        print(f"Relative path part: {db_path}")
        print(f"Absolute path computed: {abs_db_path}")
        print(f"File exists: {os.path.exists(abs_db_path)}")
        
        # 检查父目录
        parent_dir = os.path.dirname(abs_db_path)
        print(f"Parent directory exists: {os.path.exists(parent_dir)}")
        
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
finally:
    # 恢复原始目录
    os.chdir(original_dir)
    print(f"Restored to original directory: {os.getcwd()}")