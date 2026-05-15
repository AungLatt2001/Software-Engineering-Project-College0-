import sqlite3
import os

DB_PATH = "college0.db"
SEED_PATH = "seed_data.sql"

def seed_database():
    """
    Inserts all sample data from seed_data.sql into college0.db.
    Run AFTER initialize_db.py has already created the tables.
    Safe to run only once — running twice will cause UNIQUE errors.
    To reset: delete college0.db, run initialize_db.py, then this.
    """

    if not os.path.exists(DB_PATH):
        print("ERROR: college0.db not found.")
        print("Run initialize_db.py first.")
        return

    if not os.path.exists(SEED_PATH):
        print(f"ERROR: {SEED_PATH} not found.")
        return

    with open(SEED_PATH, "r") as f:
        seed_sql = f.read()

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")

    try:
        conn.executescript(seed_sql)
        conn.commit()
        print("✓ Seed data inserted successfully.\n")

        # Print a summary of what was inserted
        cursor = conn.cursor()
        summary = [
            ("users",                  "Total users"),
            ("students",               "Students"),
            ("instructors",            "Instructors"),
            ("registrars",             "Registrars"),
            ("semesters",              "Semesters"),
            ("courses",                "Courses"),
            ("class_sections",         "Class sections"),
            ("section_timeslots",      "Timeslots"),
            ("enrollments",            "Enrollments"),
            ("waitlist_entries",       "Waitlist entries"),
            ("grade_records",          "Grade records"),
            ("reviews",                "Reviews"),
            ("taboo_words",            "Taboo words"),
            ("warning_records",        "Warning records"),
            ("complaints",             "Complaints"),
            ("graduation_applications","Graduation applications"),
            ("visitor_applications",   "Visitor applications"),
            ("ai_queries",             "AI query logs"),
        ]

        print(f"{'Table':<30} {'Count':>6}")
        print("-" * 38)
        for table, label in summary:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            print(f"{label:<30} {count:>6}")

    except sqlite3.IntegrityError as e:
        print(f"INTEGRITY ERROR: {e}")
        print("\nThis usually means you ran seed_db.py twice.")
        print("To fix: delete college0.db, run initialize_db.py, then seed_db.py again.")
        conn.rollback()

    except sqlite3.Error as e:
        print(f"DATABASE ERROR: {e}")
        conn.rollback()

    finally:
        conn.close()

if __name__ == "__main__":
    seed_database()