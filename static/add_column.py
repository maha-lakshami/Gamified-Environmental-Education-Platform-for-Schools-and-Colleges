import sqlite3

conn = sqlite3.connect("database.db")

try:
    conn.execute(
        "ALTER TABLE users ADD COLUMN verification_status TEXT DEFAULT 'pending'"
    )
    print("✅ verification_status column added")
except Exception as e:
    print("⚠️ Column may already exist:", e)

conn.commit()
conn.close()