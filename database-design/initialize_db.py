import sqlite3
import os

DB_PATH = "college0.db"
SCHEMA_PATH = "schema.sql"

def initialize_database():
    """
    Creates college0.db and runs schema.sql to build all tables.
    Safe to run multiple times — IF NOT EXISTS prevents re-creation.
    To fully reset: delete college0.db and run this script again.
    """

    # Read the schema file
    if not os.path.exists(SCHEMA_PATH):
        print(f"ERROR: {SCHEMA_PATH} not found.")
        return

    with open(SCHEMA_PATH, "r") as f:
        schema_sql = f.read()

    # Connect to (or create) the database file
    conn = sqlite3.connect(DB_PATH)

    # CRITICAL: Enable foreign key enforcement
    # Without this line, all REFERENCES constraints are ignored
    conn.execute("PRAGMA foreign_keys = ON")

    try:
        # executescript() runs multiple SQL statements at once
        conn.executescript(schema_sql)
        conn.commit()
        print(f"Database initialized: {DB_PATH}")
        print(f"Tables created successfully.")

        # Verify by listing all tables
        cursor = conn.cursor()
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type = 'table'
            ORDER BY name
        """)
        tables = cursor.fetchall()
        print(f"\nTables in database ({len(tables)} total):")
        for table in tables:
            print(f"  - {table[0]}")

    except sqlite3.Error as e:
        print(f"ERROR: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    initialize_database()