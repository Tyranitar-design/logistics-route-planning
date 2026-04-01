#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
数据库迁移脚本：修改 orders 表结构以匹配代码模型
"""

import sqlite3
import os

DB_PATH = r'D:\物流路径规划系统项目\database\logistics.db'

def migrate_orders_table():
    """迁移 orders 表"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print("开始迁移 orders 表...")
    
    # 1. 备份现有数据
    cursor.execute("SELECT * FROM orders")
    old_data = cursor.fetchall()
    print(f"备份了 {len(old_data)} 条订单记录")
    
    # 2. 获取旧表列信息
    cursor.execute("PRAGMA table_info(orders)")
    old_columns = [col[1] for col in cursor.fetchall()]
    print(f"旧表列: {old_columns}")
    
    # 3. 创建新表（匹配代码模型）
    cursor.execute("""
        CREATE TABLE orders_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_number VARCHAR(50) UNIQUE NOT NULL,
            customer_name VARCHAR(100),
            customer_phone VARCHAR(20),
            pickup_node_id INTEGER,
            delivery_node_id INTEGER,
            cargo_name VARCHAR(100),
            cargo_type VARCHAR(50),
            weight FLOAT DEFAULT 0,
            volume FLOAT DEFAULT 0,
            priority VARCHAR(20) DEFAULT 'normal',
            status VARCHAR(20) DEFAULT 'pending',
            vehicle_id INTEGER,
            estimated_delivery DATETIME,
            actual_delivery DATETIME,
            notes TEXT,
            created_at DATETIME,
            updated_at DATETIME,
            FOREIGN KEY (pickup_node_id) REFERENCES nodes (id),
            FOREIGN KEY (delivery_node_id) REFERENCES nodes (id),
            FOREIGN KEY (vehicle_id) REFERENCES vehicles (id)
        )
    """)
    print("创建新表 orders_new")
    
    # 4. 迁移数据（只迁移共有的列）
    # 共有列: id, order_number, customer_name, customer_phone, pickup_node_id, delivery_node_id,
    #         cargo_name, cargo_type, weight, volume, priority, status, vehicle_id, created_at, updated_at
    common_columns = [
        'id', 'order_number', 'customer_name', 'customer_phone', 
        'pickup_node_id', 'delivery_node_id', 'cargo_name', 'cargo_type',
        'weight', 'volume', 'priority', 'status', 'vehicle_id',
        'created_at', 'updated_at'
    ]
    
    # 从旧表读取数据并插入新表
    cursor.execute(f"SELECT {','.join(common_columns)} FROM orders")
    rows = cursor.fetchall()
    
    placeholders = ','.join(['?' for _ in common_columns])
    insert_sql = f"INSERT INTO orders_new ({','.join(common_columns)}) VALUES ({placeholders})"
    
    for row in rows:
        cursor.execute(insert_sql, row)
    
    print(f"迁移了 {len(rows)} 条记录到新表")
    
    # 5. 删除旧表
    cursor.execute("DROP TABLE orders")
    print("删除旧表 orders")
    
    # 6. 重命名新表
    cursor.execute("ALTER TABLE orders_new RENAME TO orders")
    print("重命名 orders_new 为 orders")
    
    # 7. 提交更改
    conn.commit()
    print("✅ 迁移完成！")
    
    # 验证
    cursor.execute("PRAGMA table_info(orders)")
    new_columns = [col[1] for col in cursor.fetchall()]
    print(f"\n新表列: {new_columns}")
    
    cursor.execute("SELECT COUNT(*) FROM orders")
    count = cursor.fetchone()[0]
    print(f"新表记录数: {count}")
    
    conn.close()

if __name__ == '__main__':
    migrate_orders_table()
