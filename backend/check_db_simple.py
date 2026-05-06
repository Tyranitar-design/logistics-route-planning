import sqlite3
import os

os.chdir(r"D:\物流路径规划系统项目\backend")
conn = sqlite3.connect('logistics.db')
cursor = conn.cursor()
cursor.execute('SELECT name FROM sqlite_master WHERE type="table"')
tables = [row[0] for row in cursor.fetchall()]
print("Tables:", tables)

# Check if user table exists
if 'user' in tables:
    cursor.execute('SELECT id, username, role FROM user')
    users = cursor.fetchall()
    print("Users:", users)
else:
    print("No user table found!")

conn.close()
