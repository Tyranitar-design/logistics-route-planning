#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
最终测试 - 验证修复
"""

import os
import sys

# 切换到backend目录
backend_dir = r'D:\物流路径规划系统项目\backend'
os.chdir(backend_dir)

# 添加backend目录到Python路径
sys.path.insert(0, backend_dir)

def final_test():
    print("="*60)
    print("最终验证测试")
    print("="*60)
    
    # 导入配置验证新的URI
    import config
    print(f"Database URI: {config.DevelopmentConfig.SQLALCHEMY_DATABASE_URI}")
    
    # 创建应用并测试登录
    from app import create_app
    app = create_app()
    
    print(f"App database URI: {app.config.get('SQLALCHEMY_DATABASE_URI')}")
    
    # 测试登录API
    with app.test_client() as client:
        try:
            response = client.post('/api/auth/login',
                                json={'username': 'admin', 'password': 'admin'},
                                content_type='application/json')
            print(f"Login status code: {response.status_code}")
            
            if response.status_code == 500:
                print("Login still returns 500 error")
                try:
                    error_resp = response.get_json()
                    print(f"Error details: {error_resp}")
                except:
                    print(f"Error response (raw): {response.get_data(as_text=True)[:200]}...")
                return False
            elif response.status_code == 401:
                print("✅ Login API is working! (401 Unauthorized - wrong credentials, which is expected)")
                return True
            elif response.status_code == 200:
                print("✅ Login API is working! (200 OK - logged in)")
                return True
            else:
                print(f"Login API returned unexpected status: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"Exception during login test: {e}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == "__main__":
    success = final_test()
    if success:
        print("\n" + "="*60)
        print("🎉 修复成功！登录API现在正常工作！")
        print("天地图API + 数据库修复 = 物流系统恢复正常！")
        print("="*60)
    else:
        print("\n" + "="*60)
        print("修复未完全成功，仍需进一步调试")
        print("="*60)