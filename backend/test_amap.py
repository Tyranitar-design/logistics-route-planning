#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""测试高德地图服务"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app

# 创建应用
app = create_app()

with app.app_context():
    print("Flask app created successfully!")
    
    # 测试高德地图服务
    from app.services.amap_service import get_amap_service
    
    service = get_amap_service()
    print(f"AMap Service initialized with key: {service._get_key()[:10]}...")
    
    # 测试地理编码
    result = service.geocode("北京市朝阳区")
    print(f"Geocode test: success={result.success}, coords=({result.longitude}, {result.latitude})")
    
print("All tests passed!")
