#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试更新后的配置 - 重写版
"""

import os
import sys
import importlib

# 清理可能的缓存
if 'config' in sys.modules:
    del sys.modules['config']

# 切换到backend目录
backend_dir = r'D:\物流路径规划系统项目\backend'
os.chdir(backend_dir)

# 添加backend目录到Python路径
sys.path.insert(0, backend_dir)

def test_updated_config():
    print("="*60)
    print("测试更新后的配置")
    print("="*60)
    
    # 现在导入更新后的配置
    import config
    importlib.reload(config)  # 确保重新加载
    
    dev_config = config.DevelopmentConfig
    print(f"Database URI: {dev_config.SQLALCHEMY_DATABASE_URI}")
    
    # 测试应用创建
    from app import create_app
    app = create_app()
    print(f"App created, actual URI in app: {app.config.get('SQLALCHEMY_DATABASE_URI')}")
    
    # 测试登录接口
    with app.test_client() as client:
        try:
            response = client.post('/api/auth/login',
                                json={'username': 'admin', 'password': 'admin'},
                                content_type='application/json')
            print(f"Login endpoint status: {response.status_code}")
            
            if response.status_code != 500:
                print("✅ 登录API现在工作正常！问题已解决。")
                return True
            else:
                print("❌ 登录API仍然返回500错误")
                return False
        except Exception as e:
            print(f"❌ 登录API测试异常: {e}")
            return False

if __name__ == "__main__":
    success = test_updated_config()
    if success:
        print("\n" + "="*60)
        print("数据库配置修复验证: 成功")
        print("后端服务应该现在可以正常工作了")
        print("="*60)
    else:
        print("\n" + "="*60)
        print("数据库配置修复验证: 失败")
        print("="*60)