from database.connection import DatabaseManager
db = DatabaseManager()
tables = db.fetchall("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
for t in tables:
    cols = db.fetchall(f"PRAGMA table_info({t['name']})")
    print(t['name'], "->", [c['name'] for c in cols])
