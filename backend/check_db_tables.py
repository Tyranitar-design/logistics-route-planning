import sqlite3
conn = sqlite3.connect('database/logistics.db')
cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
print("Tables:", [row for row in cursor])

for table in ['users', 'nodes', 'orders', 'vehicles', 'routes']:
    cursor = conn.execute(f"PRAGMA table_info({table})")
    print(f"\n{table} columns:", [row for row in cursor])
