#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
初始化演示用户
创建 admin、user、driver 三个演示账号
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models import db, User
from app import create_app


def init_demo_users():
    """初始化演示用户"""
    app = create_app()
    
    with app.app_context():
        # 检查是否已存在
        admin_exists = User.query.filter_by(username='admin').first()
        user_exists = User.query.filter_by(username='user').first()
        driver_exists = User.query.filter_by(username='driver').first()
        
        if not admin_exists:
            admin = User(
                username='admin',
                email='admin@example.com',
                real_name='系统管理员',
                role='admin',
                status='active'
            )
            admin.password = 'admin123'
            db.session.add(admin)
            print('[OK] 创建管理员账号: admin / admin123')
        else:
            print('[INFO] 管理员账号已存在: admin')
        
        if not user_exists:
            user = User(
                username='user',
                email='user@example.com',
                real_name='演示用户',
                role='user',
                status='active'
            )
            user.password = 'user123'
            db.session.add(user)
            print('[OK] 创建普通用户账号: user / user123')
        else:
            print('[INFO] 普通用户账号已存在: user')
        
        if not driver_exists:
            driver = User(
                username='driver',
                email='driver@example.com',
                real_name='张师傅',
                phone='13800138000',
                role='driver',
                status='active'
            )
            driver.password = 'driver123'
            db.session.add(driver)
            print('[OK] 创建司机账号: driver / driver123')
        else:
            print('[INFO] 司机账号已存在: driver')
        
        db.session.commit()
        print('\n[SUCCESS] 演示账号初始化完成！')
        print('=' * 50)
        print('Web 管理后台:')
        print('  管理员: admin / admin123 (可编辑)')
        print('  普通用户: user / user123 (仅查看)')
        print('')
        print('司机小程序:')
        print('  司机: driver / driver123')
        print('=' * 50)


if __name__ == '__main__':
    init_demo_users()