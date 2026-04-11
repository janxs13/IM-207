"""
Run this once to add soft-delete columns to the booking table.
Usage: python migrate_soft_delete.py
"""
import sqlite3, os

DB_PATH = os.path.join(os.path.dirname(__file__), "instance", "bus_ticketing.db")

conn = sqlite3.connect(DB_PATH)
cur  = conn.cursor()

# Check existing columns
cur.execute("PRAGMA table_info(booking)")
cols = [row[1] for row in cur.fetchall()]

if "deleted_at" not in cols:
    cur.execute("ALTER TABLE booking ADD COLUMN deleted_at DATETIME")
    print("Added: deleted_at")
else:
    print("Skipped: deleted_at already exists")

if "deleted_by" not in cols:
    cur.execute("ALTER TABLE booking ADD COLUMN deleted_by VARCHAR(100)")
    print("Added: deleted_by")
else:
    print("Skipped: deleted_by already exists")

conn.commit()
conn.close()
print("Migration complete.")
