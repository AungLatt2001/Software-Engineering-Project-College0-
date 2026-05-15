# ============================================================
# College0 — Apply Triggers
# File: apply_triggers.py
# Run AFTER initialize_db.py.
# Safe to run multiple times — IF NOT EXISTS prevents errors.
# ============================================================

import sqlite3
import os

DB_PATH      = "college0.db"
TRIGGERS_PATH = "triggers.sql"

def apply_triggers():

    if not os.path.exists(DB_PATH):
        print("ERROR: college0.db not found. Run initialize_db.py first.")
        return

    if not os.path.exists(TRIGGERS_PATH):
        print(f"ERROR: {TRIGGERS_PATH} not found.")
        return

    with open(TRIGGERS_PATH, "r") as f:
        trigger_sql = f.read()

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")

    try:
        conn.executescript(trigger_sql)
        conn.commit()
        print("✓ Triggers applied successfully.\n")

        # List all triggers now in the database
        cursor = conn.cursor()
        cursor.execute("""
            SELECT name, tbl_name, sql
            FROM sqlite_master
            WHERE type = 'trigger'
            ORDER BY name
        """)
        triggers = cursor.fetchall()
        print(f"{'Trigger':<35} {'On Table':<20}")
        print("-" * 55)
        for t in triggers:
            print(f"{t[0]:<35} {t[1]:<20}")

    except sqlite3.Error as e:
        print(f"ERROR: {e}")
        conn.rollback()

    finally:
        conn.close()

if __name__ == "__main__":
    apply_triggers()