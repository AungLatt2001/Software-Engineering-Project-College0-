# ============================================================
# College0 — Full Database Reset
# File: reset_db.py
# Run with: python3 reset_db.py
#
# This script:
#   1. Deletes college0.db if it exists
#   2. Rebuilds all 18 tables from schema.sql
#   3. Inserts all seed data from seed_data.sql
#   4. Applies all 5 triggers from triggers.sql
#
# Use this when you want a clean slate.
# ============================================================

import sqlite3
import os

DB_PATH       = "college0.db"
SCHEMA_PATH   = "schema.sql"
SEED_PATH     = "seed_data.sql"
TRIGGERS_PATH = "triggers.sql"

def reset():
    print("=" * 50)
    print("College0 — Full Database Reset")
    print("=" * 50)

    # Step 1: Delete existing database
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        print(f"\n✓ Deleted existing {DB_PATH}")
    else:
        print(f"\n  No existing database found — building fresh")

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")

    # Step 2: Build schema
    with open(SCHEMA_PATH) as f:
        conn.executescript(f.read())
    conn.commit()
    print("✓ Schema applied — 18 tables created")

    # Step 3: Insert seed data
    with open(SEED_PATH) as f:
        conn.executescript(f.read())
    conn.commit()

    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users")
    print(f"✓ Seed data inserted — "
          f"{cursor.fetchone()[0]} users loaded")

    # Step 4: Apply triggers
    with open(TRIGGERS_PATH) as f:
        conn.executescript(f.read())
    conn.commit()

    cursor.execute("""
        SELECT COUNT(*) FROM sqlite_master
        WHERE type = 'trigger'
    """)
    print(f"✓ Triggers applied — "
          f"{cursor.fetchone()[0]} triggers active")

    conn.close()

    print("\n" + "=" * 50)
    print("Database ready. Run: python3 app.py")
    print("=" * 50)

if __name__ == "__main__":
    reset()