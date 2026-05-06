#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
天地图服务测试脚本
"""

import os
import sys
import django
from pprint import pprint

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 设置 Django 环境
os.environ.setdefault('FLASK_APP', 'app/__init__.py')
os.environ.setdefault('FLASK_ENV', 'development')

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
        print(f"✓ 服务实例创建成功")
        print(f"  - 浏览器 Key: {'已配置' if service.browser_key else '未配置'}")
        print(f"  - 服务端 Key: {'已配置' if service.server_key else '未配置'}")
        print()
    except Exception as e:
        print(f"✗ 服务实例创建失败: {e}")
        return False
    
    # 测试地理编码
    print("测试地理编码功能...")
    try:
        result = service.geocode("北京市天安门")
        print(f"✓ 地理编码测试完成")
        print(f"  - 成功: {result.success}")
        if result.success:
            print(f"  - 经度: {result.longitude}")
            print(f"  - 纬度: {result.latitude}")
            print(f"  - 地址: {result.formatted_address}")
        else:
            print(f"  - 错误: {result.error}")
        print()
    except Exception as e:
        print(f"✗ 地理编码测试失败: {e}")
        print()
    
    # 测试驾车路线规划
    print("测试驾车路线规划功能...")
    try:
        # 北京市中心到望京的路线
        origin = (116.39129, 39.90709)  # 天安门附近
        destination = (116.45129, 39.95709)  # 望京附近
        
        route_result = service.driving_route(origin, destination, strategy='0')
        print(f"✓ 驾车路线规划测试完成")
        print(f"  - 成功: {route_result.success}")
        if route_result.success:
            print(f"  - 距离: {route_result.distance} 公里")
            print(f"  - 时长: {route_result.duration} 秒 ({route_result.duration/60:.1f} 分钟)")
            print(f"  - 坐标点数量: {len(route_result.polyline)}")
            print(f"  - 详细步骤: {len(route_result.steps)} 个")
            print(f"  - 简化步骤: {len(route_result.simple_steps)} 个")
        else:
            print(f"  - 错误: {route_result.error}")
        print()
    except Exception as e:
        print(f"✗ 驾车路线规划测试失败: {e}")
        print()
    
    # 测试前端友好格式的路线
    print("测试前端友好路线数据...")
    try:
        origin = (116.39129, 39.90709)
        destination = (116.45129, 39.95709)
        
        frontend_result = service.get_route_for_frontend(origin, destination, strategy='0')
        print(f"✓ 前端友好格式测试完成")
        print(f"  - 成功: {frontend_result['success']}")
        if frontend_result['success']:
            print(f"  - 距离: {frontend_result['distance_km']} 公里")
            print(f"  - 时长: {frontend_result['duration_minutes']} 分钟")
            print(f"  - 坐标点数量: {frontend_result['coordinates_count']}")
            print(f"  - 数据源: {frontend_result['source']}")
        else:
            print(f"  - 错误: {frontend_result.get('error')}")
        print()
    except Exception as e:
        print(f"✗ 前端友好格式测试失败: {e}")
        print()
    
    # 测试地名搜索
    print("测试地名搜索功能...")
    try:
        search_result = service.search_poi("北京天安门")
        print(f"✓ 地名搜索测试完成")
        print(f"  - 成功: {search_result.success}")
        print(f"  - 结果数量: {search_result.total}")
        if search_result.items:
            first_item = search_result.items[0]
            print(f"  - 第一个结果: {first_item.get('name', 'N/A')}")
        print()
    except Exception as e:
        print(f"✗ 地名搜索测试失败: {e}")
        print()
    
    print("="*60)
    print("天地图服务测试完成")
    print("="*60)
    
    return True

if __name__ == "__main__":
    test_tianditu_service()