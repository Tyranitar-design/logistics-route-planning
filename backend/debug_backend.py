#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
调试后端启动问题
"""

import sys
import os
import traceback

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def debug_app_creation():
    print("="*60)
    print("后端应用启动调试")
    print("="*60)
    
    try:
        print("1. 正在导入配置...")
        from config import config
        print("   ✅ 配置导入成功")
        
        print("2. 正在导入数据库实例...")
        from app.models import db
        print("   ✅ 数据库实例导入成功")
        
        print("3. 正在创建应用...")
        from app import create_app
        app = create_app('development')
        print("   ✅ 应用创建成功")
        
        print("4. 正在检查蓝图注册...")
        blueprint_names = list(app.blueprints.keys())
        print(f"   ✅ 已注册蓝图数量: {len(blueprint_names)}")
        
        # 检查关键路由是否存在
        print("5. 正在检查关键路由...")
        routes = [str(rule.rule) for rule in app.url_map.iter_rules()]
        
        login_routes = [r for r in routes if 'login' in r.lower()]
        print(f"   ✅ 登录路由: {len(login_routes)} 个")
        
        auth_routes = [r for r in routes if 'auth' in r.lower()]
        print(f"   ✅ 认证路由: {len(auth_routes)} 个")
        
        print("6. 正在检查所有路由...")
        tianditu_routes = [r for r in routes if 'tianditu' in r.lower()]
        print(f"   ✅ 天地图路由: {len(tianditu_routes)} 个")
        
        if len(routes) < 10:  # 如果路由数量异常少，说明有问题
            print("   ⚠️  路由数量异常，请检查应用初始化")
        else:
            print(f"   ✅ 总路由数量: {len(routes)} 个 (正常)")
        
        print("\n" + "="*60)
        print("调试结果: ✅ 应用启动正常")
        print("如果仍有问题，可能是服务端运行时错误，请检查数据库连接或其他服务")
        print("="*60)
        
        return True
        
    except Exception as e:
        print(f"\n❌ 启动失败: {e}")
        print("\n详细错误信息:")
        traceback.print_exc()
        print("\n" + "="*60)
        print("调试结果: ❌ 应用启动失败")
        print("="*60)
        
        return False

if __name__ == "__main__":
    debug_app_creation()