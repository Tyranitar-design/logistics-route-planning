#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
天地图 API 测试脚本
"""

import os
import sys

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 加载环境变量
from dotenv import load_dotenv
load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'backend', '.env'))

def test_tianditu_api():
    """测试天地图 API 端点"""
    print("="*60)
    print("天地图 API 测试")
    print("="*60)
    
    try:
        from app import create_app
        from flask import json
        
        # 创建应用实例
        app = create_app()
        client = app.test_client()
        
        print("[OK] Flask app created successfully")
        
        # 测试获取 Keys 配置信息
        print("\nTesting keys configuration endpoint...")
        try:
            response = client.get('/api/tianditu/keys', headers={
                'Authorization': 'Bearer fake-token'  # 这个端点不检查真实token
            })
            print("[OK] Keys endpoint test completed")
            print("  - Status: %s" % response.status_code)
            if response.status_code == 200:
                data = response.get_json()
                print("  - Response: %s" % data)
            print()
        except Exception as e:
            print("[ERROR] Keys endpoint test failed: %s" % e)
            print()
        
        # 测试路径规划（使用坐标方式，避免依赖数据库节点）
        print("Testing coordinate-based driving route endpoint...")
        try:
            data = {
                'origin_lng': 116.39129,
                'origin_lat': 39.90709,
                'dest_lng': 116.45129,
                'dest_lat': 39.95709,
                'strategy': '0'
            }
            response = client.post('/api/tianditu/drive/coords', 
                                 json=data, 
                                 headers={'Authorization': 'Bearer fake-token'})
            print("[OK] Coordinate route endpoint test completed")
            print("  - Status: %s" % response.status_code)
            if response.status_code == 200:
                data = response.get_json()
                print("  - Success: %s" % data.get('success', False))
                if data.get('success'):
                    print("  - Distance: %s km" % data.get('distance_km'))
                    print("  - Duration: %s min" % data.get('duration_minutes'))
                    print("  - Coordinates: %s points" % data.get('coordinates_count'))
            print()
        except Exception as e:
            print("[ERROR] Coordinate route endpoint test failed: %s" % e)
            print()
        
        # 测试路线对比功能
        print("Testing route comparison endpoint...")
        try:
            # 这个需要真实的节点ID，我们先跳过
            print("[SKIP] Route comparison test (requires valid node IDs)")
            print()
        except Exception as e:
            print("[ERROR] Route comparison test failed: %s" % e)
            print()
        
        print("="*60)
        print("Tianditu API Test Completed")
        print("="*60)
        
    except Exception as e:
        print("[ERROR] Tianditu API test setup failed: %s" % e)
        return False
    
    return True

if __name__ == "__main__":
    test_tianditu_api()