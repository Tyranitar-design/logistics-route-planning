#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
天地图服务测试脚本
"""

import os
import sys

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 加载环境变量
from dotenv import load_dotenv
load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'backend', '.env'))

def test_tianditu_service():
    """测试天地图服务"""
    print("="*60)
    print("天地图服务测试")
    print("="*60)
    
    # 测试服务实例创建
    try:
        from app.services.tianditu_service import get_tianditu_service
        service = get_tianditu_service()
        print("[OK] Service instance created successfully")
        print("  - Browser Key: %s" % ("Configured" if service.browser_key else "Not configured"))
        print("  - Server Key: %s" % ("Configured" if service.server_key else "Not configured"))
        print()
    except Exception as e:
        print("[ERROR] Service instance creation failed: %s" % e)
        return False
    
    # 测试地理编码
    print("Testing geocode functionality...")
    try:
        result = service.geocode("北京市天安门")
        print("[OK] Geocode test completed")
        print("  - Success: %s" % result.success)
        if result.success:
            print("  - Longitude: %s" % result.longitude)
            print("  - Latitude: %s" % result.latitude)
            print("  - Address: %s" % result.formatted_address)
        else:
            print("  - Error: %s" % result.error)
        print()
    except Exception as e:
        print("[ERROR] Geocode test failed: %s" % e)
        print()
    
    # 测试驾车路线规划
    print("Testing driving route functionality...")
    try:
        # 北京市中心到望京的路线
        origin = (116.39129, 39.90709)  # 天安门附近
        destination = (116.45129, 39.95709)  # 望京附近
        
        route_result = service.driving_route(origin, destination, strategy='0')
        print("[OK] Driving route test completed")
        print("  - Success: %s" % route_result.success)
        if route_result.success:
            print("  - Distance: %s km" % route_result.distance)
            print("  - Duration: %s sec (%.1f min)" % (route_result.duration, route_result.duration/60))
            print("  - Coordinates count: %s" % len(route_result.polyline))
            print("  - Detailed steps: %s" % len(route_result.steps))
            print("  - Simple steps: %s" % len(route_result.simple_steps))
        else:
            print("  - Error: %s" % route_result.error)
        print()
    except Exception as e:
        print("[ERROR] Driving route test failed: %s" % e)
        print()
    
    print("="*60)
    print("Tianditu Service Test Completed")
    print("="*60)
    
    return True

if __name__ == "__main__":
    test_tianditu_service()