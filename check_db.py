import sqlite3
import json

db_path = "/home/md_soriful_islam/.local/share/posting/manual/tasks.db"
conn = sqlite3.connect(db_path)
cur = conn.cursor()
rows = cur.execute("SELECT status, count(*) FROM tasks GROUP BY status").fetchall()
print("Task status summary:", rows)
