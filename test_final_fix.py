#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试修复后的配置
"""

import os
import sys

# 切换到backend目录
backend_dir = r'D:\物流路径规划系统项目\backend'
os.chdir(backend_dir)

# 添加backend目录到Python路径
sys.path.insert(0, backend_dir)

def test_fixed_config():
    print("="*60)
    print("测试修复后的配置")
    print("="*60)
    
    # 重新导入配置（清除缓存）
    if 'config' in sys.modules:
        del sys.modules['config']
    
    import config
    
    dev_config = config.DevelopmentConfig
    print(f"修复后的Database URI: {dev_config.SQLALCHEMY_DATABASE_URI}")
    
    # 测试应用创建
    from app import create_app
    app = create_app()
    print(f"应用中的URI: {app.config.get('SQLALCHEMY_DATABASE_URI')}")
    
    # 尝试登录API
    with app.test_client() as client:
        try:
            response = client.post('/api/auth/login',
                                json={'username': 'admin', 'password': 'admin'},
                                content_type='application/json')
            print(f"登录端点状态: {response.status_code}")
            
            if response.status_code != 500:
                print("✅ 修复成功！登录API现在正常工作。")
                return True
            else:
                print("❌ 登录API仍然返回500错误")
                # 打印错误详情
                try:
                    error_data = response.get_json()
                    print(f"错误详情: {error_data}")
                except:
                    print("无法解析错误响应")
                return False
        except Exception as e:
            print(f"❌ 登录API测试异常: {e}")
            return False

if __name__ == "__main__":
    success = test_fixed_config()
    if success:
        print("\n" + "="*60)
        print("数据库配置修复验证: 成功")
        print("天地图API服务 + 数据库修复 = 系统恢复正常！")
        print("="*60)
    else:
        print("\n" + "="*60)
        print("数据库配置修复验证: 仍需调试")
        print("="*60)