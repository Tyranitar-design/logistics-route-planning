#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试登录API
"""

import os
import sys

# 切换到backend目录
backend_dir = r'D:\物流路径规划系统项目\backend'
os.chdir(backend_dir)

# 添加backend目录到Python路径
sys.path.insert(0, backend_dir)

def test_login_api():
    print("="*60)
    print("测试登录API")
    print("="*60)
    
    from app import create_app
    app = create_app()
    
    with app.test_client() as client:
        # 尝试获取登录页面或进行登录测试
        try:
            # 测试获取认证相关的端点
            print("1. 测试获取认证端点信息...")
            response = client.get('/api/auth/config')
            print(f"   GET /api/auth/config -> Status: {response.status_code}")
            
            # 如果上述端点不存在，测试登录端点
            print("2. 测试登录端点...")
            login_response = client.post('/api/auth/login',
                                      json={'username': 'admin', 'password': 'admin'},
                                      content_type='application/json')
            print(f"   POST /api/auth/login -> Status: {login_response.status_code}")
            
            # 打印响应内容（限制长度）
            response_text = login_response.get_data(as_text=True)
            print(f"   Response preview: {response_text[:200]}...")
            
            if login_response.status_code == 200:
                print("   ✓ 登录API工作正常")
            elif login_response.status_code == 401:
                print("   ⚠ 登录API可达但凭据不正确（这是正常的）")
            elif login_response.status_code == 500:
                print("   ✗ 登录API内部错误")
            else:
                print(f"   ? 登录API返回其他状态码: {login_response.status_code}")
                
        except Exception as e:
            print(f"   ✗ 登录API测试失败: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "="*60)
    print("登录API测试完成")
    print("="*60)

if __name__ == "__main__":
    test_login_api()