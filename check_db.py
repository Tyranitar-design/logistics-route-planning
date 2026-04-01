import sqlite3

conn = sqlite3.connect(r'D:\物流路径规划系统项目\database\logistics.db')
cursor = conn.cursor()

# 查看 orders 表结构
cursor.execute("PRAGMA table_info(orders)")
columns = cursor.fetchall()
print("orders 表结构:")
for col in columns:
    print(f"  {col[1]} ({col[2]})")

print()

# 查看 users 表结构
cursor.execute("PRAGMA table_info(users)")
columns = cursor.fetchall()
print("users 表结构:")
for col in columns:
    print(f"  {col[1]} ({col[2]})")

conn.close()
