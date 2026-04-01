#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""检查数据库表结构"""

import sqlite3
import os

db_path = os.path.join(os.path.dirname(__file__), 'database', 'logistics.db')
print(f'Database path: {db_path}')
print(f'Exists: {os.path.exists(db_path)}')

if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    print(f'Tables: {tables}')

    for table in tables:
        table_name = table[0]
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()
        print(f'\n{table_name}:')
        for col in columns:
            print(f'  {col[1]} ({col[2]})')

    conn.close()
else:
    print('Database file not found!')
