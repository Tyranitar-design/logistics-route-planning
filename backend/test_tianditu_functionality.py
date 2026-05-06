#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试天地图服务功能
"""

def test_tianditu_functionality():
    print('Testing Tianditu functionality...')
    
    # 测试服务创建
    try:
        from app.services.tianditu_service import get_tianditu_service
        service = get_tianditu_service()
        print('[SUCCESS] Tianditu service created')
        print(f'  - Browser key: {"Configured" if service.browser_key else "Not configured"}')
        print(f'  - Server key: {"Configured" if service.server_key else "Not configured"}')
    except Exception as e:
        print(f'[ERROR] Service creation failed: {e}')
        return
    
    # 测试路线规划功能
    try:
        result = service.get_route_for_frontend(
            (116.39129, 39.90709),  # 北京天安门
            (116.45129, 39.95709),  # 北京望京
            '0'  # 推荐路线
        )
        print(f'[SUCCESS] Route planning works: {result["success"]}')
        if result["success"]:
            print(f'  - Distance: {result["distance_km"]} km')
            print(f'  - Duration: {result["duration_minutes"]} min')
            print(f'  - Coordinates: {result["coordinates_count"]} points')
            print(f'  - Data source: {result["source"]}')
    except Exception as e:
        print(f'[ERROR] Route planning failed: {e}')
    
    # 测试地理编码功能
    try:
        result = service.geocode("北京市天安门")
        print(f'[SUCCESS] Geocoding works: {result.success}')
        if result.success:
            print(f'  - Location: {result.longitude}, {result.latitude}')
            print(f'  - Address: {result.formatted_address}')
    except Exception as e:
        print(f'[ERROR] Geocoding failed: {e}')
    
    print('Tianditu functionality test completed!')

if __name__ == "__main__":
    test_tianditu_functionality()