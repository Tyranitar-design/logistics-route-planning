import sqlite3

db_path = 'database/logistics.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# 列出所有表
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()
print('数据库中的表:', [t[0] for t in tables])

# 检查 orders 表结构
cursor.execute('PRAGMA table_info(orders)')
orders_columns = cursor.fetchall()
print(f'\norders 表列数: {len(orders_columns)}')

conn.close()