#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""临时脚本：添加天地图路由"""

import re

file_path = r'D:\物流路径规划系统项目\backend\app\__init__.py'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 添加 tianditu_bp 导入
if 'from app.routes.tianditu_route import tianditu_bp' not in content:
    content = content.replace(
        'from app.routes.network import network_bp',
        'from app.routes.network import network_bp\nfrom app.routes.tianditu_route import tianditu_bp'
    )

# 注册 tianditu_bp 蓝图
if "app.register_blueprint(tianditu_bp" not in content:
    content = content.replace(
        "app.register_blueprint(network_bp, url_prefix='/api/network')",
        "app.register_blueprint(network_bp, url_prefix='/api/network')\n    app.register_blueprint(tianditu_bp, url_prefix='/api/tianditu')"
    )

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Successfully added tianditu routes!")
