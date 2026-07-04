import sqlite3
conn = sqlite3.connect('pharma.db')
cur = conn.cursor()
cur.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='products'")
row = cur.fetchone()
if row:
    print(row[0])
else:
    print("Table not found")
conn.close()
