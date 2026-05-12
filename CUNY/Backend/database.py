"""
database.py — College0 / CUNY0 backend persistence layer.

Owns:
  • SQLite connection management (one connection per request via Flask `g`)
  • Schema creation (idempotent — safe to call on every boot)
  • Seed data (only inserted on a fresh database)

Schema is designed around the frontend's API contract.
Key contract decisions baked in here:
  • user_id is a TEXT primary key (e.g. "S101", "I01", "REG01")
  • course_code is a TEXT primary key (e.g. "CSC 22000")
  • phase labels are stored as CAPS strings: SETUP / REGISTRATION / RUNNING / GRADING / CLOSED
  • passwords are hashed with werkzeug's PBKDF2 (no external bcrypt dep)
"""

import os
import sqlite3
from flask import g
from werkzeug.security import generate_password_hash

DB_PATH = os.environ.get("COLLEGE0_DB_PATH", "college0.db")


# ─── Connection management ──────────────────────────────────────────────────

def get_db():
    """Return a request-scoped SQLite connection with FK enforcement on."""
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.execute("PRAGMA foreign_keys = ON")
        g.db.row_factory = sqlite3.Row
    return g.db


def close_db(_exc=None):
    """Teardown handler — closes the per-request connection."""
    db = g.pop("db", None)
    if db is not None:
        db.close()


# ─── Schema ─────────────────────────────────────────────────────────────────

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    user_id        TEXT PRIMARY KEY,           -- e.g. S101, I01, REG01
    name           TEXT NOT NULL,
    email          TEXT NOT NULL UNIQUE,
    password_hash  TEXT NOT NULL,
    role           TEXT NOT NULL CHECK(role IN ('Student','Instructor','Registrar')),
    must_change_pw INTEGER NOT NULL DEFAULT 0,
    created_at     TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS students (
    user_id             TEXT PRIMARY KEY REFERENCES users(user_id) ON DELETE CASCADE,
    gpa                 REAL NOT NULL DEFAULT 0.0,
    warnings            INTEGER NOT NULL DEFAULT 0,
    honor_count         INTEGER NOT NULL DEFAULT 0,
    suspended           INTEGER NOT NULL DEFAULT 0,
    suspended_until     INTEGER NOT NULL DEFAULT 0,        -- semester after which suspension may lift
    fine_due            REAL NOT NULL DEFAULT 0.0,         -- fine required on suspension
    fine_paid           INTEGER NOT NULL DEFAULT 0,
    terminated          INTEGER NOT NULL DEFAULT 0,
    graduated           INTEGER NOT NULL DEFAULT 0,
    semesters_completed INTEGER NOT NULL DEFAULT 0,
    interview_pending   INTEGER NOT NULL DEFAULT 0         -- GPA 2.0-2.25 → registrar interview
);

CREATE TABLE IF NOT EXISTS instructors (
    user_id        TEXT PRIMARY KEY REFERENCES users(user_id) ON DELETE CASCADE,
    warnings       INTEGER NOT NULL DEFAULT 0,
    suspended      INTEGER NOT NULL DEFAULT 0,
    fired          INTEGER NOT NULL DEFAULT 0,
    review_pending INTEGER NOT NULL DEFAULT 0              -- class GPA out of [2.5, 3.5] → registrar review
);

CREATE TABLE IF NOT EXISTS semester_state (
    id                   INTEGER PRIMARY KEY CHECK (id = 1),
    semester             INTEGER NOT NULL DEFAULT 1,         -- 1, 2, 3... internal sequence number
    season               TEXT NOT NULL DEFAULT 'Spring'      -- 'Spring' / 'Summer' / 'Fall' / 'Winter'
                         CHECK(season IN ('Spring','Summer','Fall','Winter')),
    year                 INTEGER NOT NULL DEFAULT 2025,
    phase                TEXT NOT NULL DEFAULT 'SETUP'
                         CHECK(phase IN ('SETUP','REGISTRATION','RUNNING','GRADING','CLOSED')),
    special_registration INTEGER NOT NULL DEFAULT 0,
    program_quota        INTEGER NOT NULL DEFAULT 50         -- maximum active students in the program
);

-- History of every (semester, season, year) combination the system has seen.
-- Lets the registrar jump back to view past semesters.
CREATE TABLE IF NOT EXISTS semester_history (
    semester  INTEGER PRIMARY KEY,
    season    TEXT NOT NULL CHECK(season IN ('Spring','Summer','Fall','Winter')),
    year      INTEGER NOT NULL,
    closed_at TEXT
);

CREATE TABLE IF NOT EXISTS courses (
    code           TEXT PRIMARY KEY,           -- e.g. "CSC 22000"
    name           TEXT NOT NULL,
    instructor_id  TEXT REFERENCES users(user_id) ON DELETE SET NULL,
    time_slot      TEXT NOT NULL DEFAULT '',
    capacity       INTEGER NOT NULL DEFAULT 20,
    is_core        INTEGER NOT NULL DEFAULT 0,
    cancelled      INTEGER NOT NULL DEFAULT 0,
    prerequisites  TEXT NOT NULL DEFAULT '',   -- comma-separated course codes, e.g. "CSC 10100,CSC 10200"
    created_at     TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Trigger: when an instructor is removed (fired/deleted), null out their courses
-- so they can be reassigned. This emulates the MySQL pattern of disabling FK checks
-- around a multi-table update; SQLite enforces this declaratively via the trigger.
CREATE TRIGGER IF NOT EXISTS instructor_reassign_courses
AFTER UPDATE OF fired ON instructors
WHEN NEW.fired = 1 AND OLD.fired = 0
BEGIN
    UPDATE courses SET instructor_id = NULL WHERE instructor_id = NEW.user_id;
END;

-- Trigger: when a user is renamed, propagate to applications (denormalised name).
CREATE TRIGGER IF NOT EXISTS user_name_propagate
AFTER UPDATE OF name ON users
WHEN OLD.name <> NEW.name
BEGIN
    UPDATE applications SET name = NEW.name WHERE email = NEW.email;
END;

CREATE TABLE IF NOT EXISTS enrollments (
    student_id   TEXT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    course_code  TEXT NOT NULL REFERENCES courses(code) ON DELETE CASCADE,
    semester     INTEGER NOT NULL,
    status       TEXT NOT NULL DEFAULT 'enrolled'
                 CHECK(status IN ('enrolled','completed','dropped','waitlist','cancelled')),
    grade        TEXT,                          -- A+, A, A-, ..., F (NULL until graded)
    PRIMARY KEY (student_id, course_code, semester)
);

CREATE TABLE IF NOT EXISTS waitlist (
    course_code  TEXT NOT NULL REFERENCES courses(code) ON DELETE CASCADE,
    student_id   TEXT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    position     INTEGER NOT NULL,
    PRIMARY KEY (course_code, student_id)
);

CREATE TABLE IF NOT EXISTS reviews (
    review_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    course_code  TEXT NOT NULL REFERENCES courses(code) ON DELETE CASCADE,
    student_id   TEXT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    semester     INTEGER NOT NULL,
    rating       INTEGER NOT NULL CHECK(rating BETWEEN 1 AND 5),
    text         TEXT NOT NULL,                 -- original text (for the registrar)
    visible_text TEXT NOT NULL,                 -- text with taboo→* if shown
    taboo_count  INTEGER NOT NULL DEFAULT 0,
    hidden       INTEGER NOT NULL DEFAULT 0,    -- ≥3 taboo words → hidden from public
    flagged      INTEGER NOT NULL DEFAULT 0,    -- legacy: 1 if any taboo found
    created_at   TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS complaints (
    complaint_id  TEXT PRIMARY KEY,             -- e.g. "C001"
    from_id       TEXT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    against_id    TEXT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    type          TEXT NOT NULL CHECK(type IN ('student_vs_student','student_vs_instructor','instructor_vs_student')),
    description   TEXT NOT NULL,
    resolved      INTEGER NOT NULL DEFAULT 0,
    resolution    TEXT,
    created_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS applications (
    app_id      TEXT PRIMARY KEY,                -- e.g. "A001"
    name        TEXT NOT NULL,
    email       TEXT NOT NULL,
    role        TEXT NOT NULL CHECK(role IN ('Student','Instructor')),
    gpa         REAL,
    notes       TEXT,
    status      TEXT NOT NULL DEFAULT 'Pending'
                CHECK(status IN ('Pending','Approved','Rejected')),
    justification TEXT,
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS taboo_words (
    word TEXT PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS warnings (
    warning_id  INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     TEXT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    reason      TEXT NOT NULL,
    issued_at   TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Creative feature: Study Buddy Matcher — students opt-in and the system
-- suggests classmates in the same courses with compatible availability.
CREATE TABLE IF NOT EXISTS study_buddy_optins (
    student_id   TEXT PRIMARY KEY REFERENCES users(user_id) ON DELETE CASCADE,
    bio          TEXT NOT NULL DEFAULT '',
    availability TEXT NOT NULL DEFAULT '',     -- e.g. "evenings, weekends"
    opted_in_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Helpful indices
CREATE INDEX IF NOT EXISTS idx_enrollments_student ON enrollments(student_id);
CREATE INDEX IF NOT EXISTS idx_enrollments_course  ON enrollments(course_code);
CREATE INDEX IF NOT EXISTS idx_reviews_course      ON reviews(course_code);
"""


# ─── Initialization & seeding ───────────────────────────────────────────────

# Default password for all seeded users (mentioned in the LoginModal).
DEFAULT_PASSWORD = "pass123"


def _ensure_column(conn: sqlite3.Connection, table: str, column: str, ddl: str):
    """Add a column if it doesn't exist yet — for upgrading existing databases.
    SQLite's ALTER TABLE only supports a small subset of operations; column add
    is one of them. ddl is the column-definition fragment, e.g.
    "TEXT NOT NULL DEFAULT ''".
    """
    cols = [r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()]
    if column not in cols:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}")


def init_db(force_seed: bool = False):
    """Create the schema and seed sample data on a fresh DB.

    Idempotent for the schema (CREATE TABLE IF NOT EXISTS).
    Seeding only happens when the users table is empty, unless `force_seed`
    is True (only used by tests).
    """
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    try:
        conn.executescript(SCHEMA)
        # Lightweight migrations — for DBs created before these columns existed.
        _ensure_column(conn, "semester_state", "season", "TEXT NOT NULL DEFAULT 'Spring'")
        _ensure_column(conn, "semester_state", "year",   "INTEGER NOT NULL DEFAULT 2025")
        _ensure_column(conn, "courses",        "prerequisites", "TEXT NOT NULL DEFAULT ''")
        # Ensure the singleton row in semester_state exists (Spring 2025 by default)
        conn.execute(
            "INSERT OR IGNORE INTO semester_state (id, semester, season, year, phase, special_registration, program_quota) "
            "VALUES (1, 1, 'Spring', 2025, 'SETUP', 0, 50)"
        )
        conn.execute(
            "INSERT OR IGNORE INTO semester_history (semester, season, year) VALUES (1, 'Spring', 2025)"
        )
        existing = conn.execute("SELECT COUNT(*) AS c FROM users").fetchone()["c"]
        if existing == 0 or force_seed:
            _seed(conn)
        conn.commit()
    finally:
        conn.close()


def _hash(pw: str) -> str:
    # PBKDF2-SHA256 — stdlib + werkzeug, no external dep.
    return generate_password_hash(pw)


def _seed(conn: sqlite3.Connection):
    """Insert demo data matching the LoginModal hint:
       Students S101–S110, Instructors I01–I03, Registrar REG01."""
    pw = _hash(DEFAULT_PASSWORD)
    admin_pw = _hash("admin")

    # Registrar
    conn.execute(
        "INSERT OR IGNORE INTO users (user_id,name,email,password_hash,role) "
        "VALUES (?,?,?,?,?)",
        ("REG01", "Diana Morgan", "registrar@college0.edu", admin_pw, "Registrar"),
    )

    # Instructors
    instructors = [
        ("I01", "Alan Turing",   "a.turing@college0.edu"),
        ("I02", "Grace Hopper",  "g.hopper@college0.edu"),
        ("I03", "Barbara Liskov","b.liskov@college0.edu"),
    ]
    for uid, name, email in instructors:
        conn.execute(
            "INSERT OR IGNORE INTO users (user_id,name,email,password_hash,role) "
            "VALUES (?,?,?,?,?)",
            (uid, name, email, pw, "Instructor"),
        )
        conn.execute("INSERT OR IGNORE INTO instructors (user_id) VALUES (?)", (uid,))

    # Students — varied GPAs/warnings/honors so the UI has something to show
    students = [
        ("S101", "Alice Chen",   "alice@college0.edu",   3.85, 0, 1),
        ("S102", "Bob Kim",      "bob@college0.edu",     2.95, 1, 0),
        ("S103", "Carol Diaz",   "carol@college0.edu",   3.40, 0, 0),
        ("S104", "David Park",   "david@college0.edu",   2.10, 2, 0),
        ("S105", "Emma Russo",   "emma@college0.edu",    3.92, 0, 2),
        ("S106", "Frank Lee",    "frank@college0.edu",   3.55, 0, 0),
        ("S107", "Grace Wang",   "grace@college0.edu",   2.75, 1, 0),
        ("S108", "Henry Okafor", "henry@college0.edu",   3.20, 0, 0),
        ("S109", "Iris Patel",   "iris@college0.edu",    3.65, 0, 1),
        ("S110", "Jack Brown",   "jack@college0.edu",    1.90, 2, 0),
    ]
    for uid, name, email, gpa, warns, honors in students:
        conn.execute(
            "INSERT OR IGNORE INTO users (user_id,name,email,password_hash,role) "
            "VALUES (?,?,?,?,?)",
            (uid, name, email, pw, "Student"),
        )
        conn.execute(
            "INSERT OR IGNORE INTO students (user_id,gpa,warnings,honor_count,semesters_completed) "
            "VALUES (?,?,?,?,?)",
            (uid, gpa, warns, honors, 0),
        )

    # Courses — a small CS department-ish catalog.
    # Four cores match what the frontend's StudentActions expects:
    #   ['CSC 10100','CSC 10200','CSC 21700','CSC 22000']
    # Tuple: (code, name, instructor_id, time_slot, capacity, is_core, prerequisites)
    courses = [
        ("CSC 10100", "Intro to Computing",      "I01", "MWF 9-10",     30, 1, ""),
        ("CSC 10200", "Intro to CS",             "I01", "MWF 10-11",    30, 1, "CSC 10100"),
        ("CSC 21700", "Probability & Statistics","I02", "TTh 11-12.30", 25, 1, ""),
        ("CSC 22000", "Algorithms",              "I02", "TTh 1-2.30",   25, 1, "CSC 10200"),
        ("CSC 30100", "Software Engineering",    "I03", "MW 2-3.30",    20, 0, "CSC 10200"),
        ("CSC 32200", "Software Eng. II",        "I03", "MW 4-5.30",    20, 0, "CSC 30100"),
        ("CSC 33200", "Operating Systems",       "I02", "TTh 9-10.30",  25, 0, "CSC 22000"),
        ("CSC 47100", "Artificial Intelligence", "I03", "F 1-4",        15, 0, "CSC 22000,CSC 21700"),
    ]
    for code, name, inst, slot, cap, core, prereqs in courses:
        conn.execute(
            "INSERT OR IGNORE INTO courses (code,name,instructor_id,time_slot,capacity,is_core,prerequisites) "
            "VALUES (?,?,?,?,?,?,?)",
            (code, name, inst, slot, cap, core, prereqs),
        )

    # Default taboo words list
    for w in ("damn", "stupid", "idiot", "hate"):
        conn.execute("INSERT OR IGNORE INTO taboo_words (word) VALUES (?)", (w,))


# ─── App integration ────────────────────────────────────────────────────────

def init_app(app):
    """Register the teardown handler and ensure the DB exists on first boot."""
    app.teardown_appcontext(close_db)
    init_db()
