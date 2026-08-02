import sqlite3, os, json

db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "cityestate.db")
results = {}
results['exists'] = os.path.exists(db_path)
results['size'] = os.path.getsize(db_path) if os.path.exists(db_path) else 0

conn = sqlite3.connect(db_path)
c = conn.cursor()

c.execute('SELECT name, type FROM sqlite_master')
results['master'] = c.fetchall()

c.execute('SELECT name FROM sqlite_master WHERE type="table"')
tables = c.fetchall()
results['tables'] = [t[0] for t in tables]

for t in tables:
    tname = t[0]
    c.execute(f'PRAGMA table_info("{tname}")')
    results[tname + '_cols'] = [list(r) for r in c.fetchall()]
    c.execute(f'PRAGMA index_list("{tname}")')
    results[tname + '_indexes'] = [list(r) for r in c.fetchall()]

out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "schema_output.json")
with open(out_path, 'w') as f:
    json.dump(results, f, indent=2, default=str)

print(f"Wrote {os.path.getsize(out_path)} bytes to {out_path}")
print(f"Tables found: {results['tables']}")
