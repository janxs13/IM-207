"""
Run this once to apply any pending schema changes to your existing DB.
Usage:  python migrate_db.py
"""
import sqlite3
import os

DB_PATH = os.path.join("instance", "bus_ticketing.db")

def column_exists(cursor, table, column):
    cursor.execute(f"PRAGMA table_info({table})")
    return any(row[1] == column for row in cursor.fetchall())

def migrate():
    if not os.path.exists(DB_PATH):
        print(f"DB not found at {DB_PATH} — it will be created fresh when you run app.py")
        return

    conn = sqlite3.connect(DB_PATH)
    cur  = conn.cursor()

    migrations = [
        # (table, column, sql_to_add)
        ("user", "reset_token", "ALTER TABLE user ADD COLUMN reset_token VARCHAR(20)"),
        # Expand seat_number to hold multi-seat strings like "A1, B2, C3, D4, A5, B6"
        # SQLite ALTER COLUMN not supported — we recreate if needed (handled in app.py)
        # Add future migrations here
    ]

    for table, column, sql in migrations:
        if not column_exists(cur, table, column):
            print(f"  Adding column: {table}.{column}")
            cur.execute(sql)
            conn.commit()
        else:
            print(f"  Already exists: {table}.{column}")

    conn.close()
    print("Migration complete.")

if __name__ == "__main__":
    migrate()
