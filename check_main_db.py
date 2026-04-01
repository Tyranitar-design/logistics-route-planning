import sqlite3

conn = sqlite3.connect('database/logistics.db')
cursor = conn.cursor()

# 查看所有表
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()
print('数据库中的表:', [t[0] for t in tables])

# 检查每个表的记录数
for table in tables:
    table_name = table[0]
    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
    count = cursor.fetchone()[0]
    print(f'  {table_name}: {count} 条记录')

conn.close()
