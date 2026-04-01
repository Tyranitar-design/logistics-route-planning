#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
数据库迁移脚本 - 添加成本分析相关字段
"""

import sqlite3
import os

def migrate_database():
    """迁移数据库，添加缺失字段"""
    db_path = os.path.join(os.path.dirname(__file__), 'logistics.db')

    if not os.path.exists(db_path):
        print(f'数据库文件不存在: {db_path}')
        return False

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 获取 orders 表的现有列
    cursor.execute("PRAGMA table_info(orders)")
    existing_columns = {row[1] for row in cursor.fetchall()}

    print(f'现有字段: {existing_columns}')

    # 需要添加的字段
    new_columns = {
        'recommended_route_id': 'INTEGER REFERENCES routes(id)',
        'actual_route_id': 'INTEGER REFERENCES routes(id)',
        'estimated_cost': 'REAL',
        'actual_cost': 'REAL',
        'pickup_time': 'DATETIME',
        'delivery_time': 'DATETIME',
        'created_by': 'INTEGER REFERENCES users(id)'
    }

    # 添加缺失的字段
    added = []
    for column, col_type in new_columns.items():
        if column not in existing_columns:
            try:
                sql = f'ALTER TABLE orders ADD COLUMN {column} {col_type}'
                cursor.execute(sql)
                print(f'✓ 添加字段: {column}')
                added.append(column)
            except sqlite3.OperationalError as e:
                print(f'✗ 添加字段 {column} 失败: {e}')

    # 检查 routes 表是否需要添加字段
    cursor.execute("PRAGMA table_info(routes)")
    route_columns = {row[1] for row in cursor.fetchall()}

    route_new_columns = {
        'toll_cost': 'REAL',
        'fuel_cost': 'REAL'
    }

    for column, col_type in route_new_columns.items():
        if column not in route_columns:
            try:
                sql = f'ALTER TABLE routes ADD COLUMN {column} {col_type}'
                cursor.execute(sql)
                print(f'✓ 添加 routes 字段: {column}')
                added.append(column)
            except sqlite3.OperationalError as e:
                print(f'✗ 添加 routes 字段 {column} 失败: {e}')

    conn.commit()
    conn.close()

    if added:
        print(f'\n迁移完成！共添加 {len(added)} 个字段')
    else:
        print('\n无需迁移，所有字段已存在')

    return True

if __name__ == '__main__':
    migrate_database()
