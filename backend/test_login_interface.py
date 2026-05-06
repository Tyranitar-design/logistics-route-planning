#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试登录接口
"""

import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_login_endpoint():
    print("="*60)
    print("测试登录接口")
    print("="*60)
    
    try:
        from app import create_app
        app = create_app()
        
        with app.test_client() as client:
            # 测试登录接口是否存在
            try:
                resp = client.post('/api/auth/login', 
                                  headers={'Content-Type': 'application/json'},
                                  json={'username': 'dummy', 'password': 'dummy'})
                
                print(f"Login endpoint accessible: {resp.status_code}")
                
                # 获取响应数据
                try:
                    response_data = resp.get_json()
                    print(f"Response: {response_data}")
                except:
                    print(f"Response (non-JSON): {resp.get_data(as_text=True)[:200]}")
                    
            except Exception as e:
                print(f"Login endpoint test error: {e}")
                
            # 测试其他认证相关接口
            try:
                resp_register = client.post('/api/auth/register', 
                                          headers={'Content-Type': 'application/json'},
                                          json={'username': 'test', 'password': 'test'})
                print(f"Register endpoint accessible: {resp_register.status_code}")
            except Exception as e:
                print(f"Register endpoint test error: {e}")
        
        print("\n" + "="*60)
        print("LOGIN INTERFACE TEST COMPLETED")
        print("="*60)
        
    except Exception as e:
        print(f"\nERROR: Login interface test failed: {e}")
        import traceback
        traceback.print_exc()
        print("\n" + "="*60)
        print("LOGIN INTERFACE TEST FAILED")
        print("="*60)

if __name__ == "__main__":
    test_login_endpoint()