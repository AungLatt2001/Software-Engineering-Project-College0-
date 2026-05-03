import sqlite3
import os
from werkzeug.security import generate_password_hash

DB_PATH = "collegeo.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    password TEXT NOT NULL,
    role TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS students (
    user_id TEXT PRIMARY KEY REFERENCES users(user_id),
    gpa REAL DEFAULT 0.0,
    warnings INTEGER DEFAULT 0,
    honor_count INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS courses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    instructor_id TEXT REFERENCES users(user_id),
    time_slot TEXT,
    max_enrolled INTEGER DEFAULT 25,
    is_core INTEGER DEFAULT 0,
    status TEXT DEFAULT 'Available'
);

CREATE TABLE IF NOT EXISTS enrollments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT REFERENCES users(user_id),
    course_id TEXT REFERENCES courses(code),
    semester INTEGER DEFAULT 1,
    grade TEXT,
    grade_points REAL,
    UNIQUE(student_id, course_id, semester)
);

CREATE TABLE IF NOT EXISTS reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT REFERENCES users(user_id),
    course_id TEXT REFERENCES courses(code),
    rating INTEGER,
    review_text TEXT,
    semester INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS complaints (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT REFERENCES users(user_id),
    subject TEXT,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS graduation_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT REFERENCES users(user_id),
    message TEXT,
    status TEXT DEFAULT 'Pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS applications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL,
    role TEXT NOT NULL,
    gpa REAL,
    statement TEXT,
    status TEXT DEFAULT 'Pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS semester_config (
    id INTEGER PRIMARY KEY DEFAULT 1,
    current_semester INTEGER DEFAULT 1,
    phase TEXT DEFAULT 'Setup'
);
"""

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    conn = get_db()
    conn.executescript(SCHEMA)
    conn.commit()

    row = conn.execute("SELECT COUNT(*) as c FROM users").fetchone()
    if row["c"] > 0:
        conn.close()
        return

    pw = generate_password_hash("pass123")

    users = [
        ("S101", "Alice Chen",    pw, "student"),
        ("S102", "Hassan Drop",   pw, "student"),
        ("S103", "David Zhu",     pw, "student"),
        ("S104", "Grace Kim",     pw, "student"),
        ("S105", "Marcus Lee",    pw, "student"),
        ("S106", "Sofia Rivera",  pw, "student"),
        ("S107", "James Park",    pw, "student"),
        ("S108", "Aisha Patel",   pw, "student"),
        ("S109", "Tyler Brooks",  pw, "student"),
        ("S110", "Nadia Ortiz",   pw, "student"),
        ("I01",  "Prof. Johnson", pw, "instructor"),
        ("I02",  "Prof. Martinez",pw, "instructor"),
        ("I03",  "Prof. Williams",pw, "instructor"),
        ("REG01","Admin Registrar",pw,"registrar"),
        ("admin","Admin Registrar",pw,"registrar"),
    ]
    conn.executemany("INSERT OR IGNORE INTO users (user_id,name,password,role) VALUES (?,?,?,?)", users)

    students = [
        ("S101", 3.90, 0, 1),
        ("S102", 4.00, 0, 0),
        ("S103", 3.93, 0, 0),
        ("S104", 3.67, 1, 0),
        ("S105", 2.80, 1, 0),
        ("S106", 3.10, 0, 0),
        ("S107", 2.50, 2, 0),
        ("S108", 3.45, 0, 0),
        ("S109", 2.10, 2, 0),
        ("S110", 3.20, 1, 0),
    ]
    conn.executemany("INSERT OR IGNORE INTO students (user_id,gpa,warnings,honor_count) VALUES (?,?,?,?)", students)

    courses = [
        ("CSC 10100", "Intro to CS",       "I01", "MWF 9-10",   25, 1, "Available"),
        ("CSC 10200", "Discrete Math",     "I01", "MWF 11-12",  25, 1, "Available"),
        ("CSC 21700", "Data Structures",   "I02", "TTh 9-11",   20, 1, "Available"),
        ("CSC 22000", "Algorithms",        "I02", "TTh 2-4",    20, 1, "Available"),
        ("CSC 32200", "Software Eng",      "I03", "MWF 2-3",    20, 0, "Available"),
        ("CSC 33600", "Networks",          "I03", "TTh 11-1",   18, 0, "Available"),
        ("CSC 30400", "OS Concepts",       "I02", "MWF 10-11",  22, 0, "Available"),
        ("CSC 40100", "Machine Learning",  "I01", "TTh 3-5",    15, 0, "Available"),
    ]
    conn.executemany(
        "INSERT OR IGNORE INTO courses (code,name,instructor_id,time_slot,max_enrolled,is_core,status) VALUES (?,?,?,?,?,?,?)",
        courses
    )

    enrollments = [
        ("S101", "CSC 10100", 1, "A+", 4.0),
        ("S101", "CSC 10200", 2, "A",  4.0),
        ("S101", "CSC 21700", 3, "A",  3.7),
        ("S101", "CSC 32200", 4, None, None),
        ("S101", "CSC 33600", 4, None, None),
        ("S102", "CSC 10100", 1, "A+", 4.0),
        ("S102", "CSC 10200", 2, "A+", 4.0),
        ("S103", "CSC 10100", 1, "A+", 4.0),
        ("S103", "CSC 10200", 2, "A",  4.0),
        ("S103", "CSC 21700", 3, "A",  3.7),
        ("S104", "CSC 10100", 1, "A",  4.0),
        ("S104", "CSC 10200", 2, "B+", 3.3),
        ("S105", "CSC 10100", 1, "B",  3.0),
        ("S106", "CSC 21700", 1, "B+", 3.3),
        ("S107", "CSC 22000", 1, "C+", 2.3),
        ("S108", "CSC 33600", 4, None, None),
        ("S109", "CSC 30400", 4, None, None),
        ("S110", "CSC 32200", 4, None, None),
    ]
    conn.executemany(
        "INSERT OR IGNORE INTO enrollments (student_id,course_id,semester,grade,grade_points) VALUES (?,?,?,?,?)",
        enrollments
    )

    reviews = [
        ("S103", "CSC 32200", 5, "Best course ever! Prof. Williams explains everything clearly.", 3),
        ("S104", "CSC 32200", 5, "Really enjoyed the group projects.", 3),
        ("S105", "CSC 32200", 4, "Challenging but rewarding.", 3),
        ("S106", "CSC 32200", 5, "Excellent material and teaching.", 3),
        ("S103", "CSC 33600", 4, "Good overview of networking concepts.", 3),
        ("S104", "CSC 33600", 4, "Solid course, enjoyed the labs.", 3),
        ("S105", "CSC 33600", 5, "Prof. Williams is great!", 3),
        ("S106", "CSC 33600", 3, "A bit rushed at the end.", 3),
        ("S107", "CSC 30400", 2, "Hard to follow lectures.", 3),
        ("S108", "CSC 30400", 2, "Needs better organization.", 3),
        ("S109", "CSC 30400", 3, "Average experience.", 3),
        ("S110", "CSC 30400", 1, "Not enough support for students.", 3),
        ("S102", "CSC 30400", 2, "Difficult without prerequisites.", 3),
    ]
    conn.executemany(
        "INSERT OR IGNORE INTO reviews (student_id,course_id,rating,review_text,semester) VALUES (?,?,?,?,?)",
        reviews
    )

    conn.execute("INSERT OR IGNORE INTO semester_config (id,current_semester,phase) VALUES (1,4,'Setup')")
    conn.commit()
    conn.close()
    print("Database initialized and seeded.")
