# ============================================================
# College0 — Seed Real CUNY Course Data
# File: seed_from_cuny.py
#
# Loads cuny_sections.json into college0.db.
# Run AFTER: python3 reset_db.py
# Run AFTER: python3 scrape_cuny.py
#
# What this does:
#   1. Reads cuny_sections.json
#   2. Inserts unique courses into the courses table
#   3. Inserts class sections into class_sections table
#   4. Inserts timeslots into section_timeslots table
#   5. Creates placeholder instructor accounts if needed
# ============================================================

import sqlite3
import json
import os
import re

DB_PATH   = "college0.db"
JSON_PATH = "cuny_sections.json"

# The semester we are loading data into
# Make sure this semester_id exists in your semesters table
SEMESTER_ID = 1

# Core courses based on CCNY CS curriculum
# These count toward graduation requirements
CORE_COURSE_CODES = {
    "CSC 10300",  # Intro to Computing
    "CSC 21200",  # Data Structures
    "CSC 21700",  # Discrete Structures
    "CSC 22000",  # Computer Architecture
    "CSC 22100",  # Fundamentals Computer Systems
    "CSC 30100",  # Theory of Computation
}


def clean_instructor(raw):
    """
    Clean up instructor names.
    'Jun Wu\nAnshuman Kumar' → 'Jun Wu'  (take first name only)
    Strips extra whitespace.
    """
    if not raw or raw == 'TBA':
        return 'TBA'
    # Take only the first line if multiple instructors listed
    first = raw.split('\n')[0].strip()
    # Remove extra internal whitespace
    first = re.sub(r'\s+', ' ', first)
    return first or 'TBA'


def clean_course_code(raw):
    """
    Normalize course code spacing.
    'CSC10300' → 'CSC 10300'
    'CSC 10300' → 'CSC 10300'
    """
    m = re.match(r'([A-Z]+)\s*(\d+)', raw.strip())
    if m:
        return f"{m.group(1)} {m.group(2)}"
    return raw.strip()


def clean_title(raw):
    """
    Clean up course titles.
    Remove stray P prefix: 'P Artificial Intelligence' → 'Artificial Intelligence'
    """
    title = raw.strip()
    # Remove leading 'P ' that CUNY sometimes adds
    title = re.sub(r'^P\s+', '', title)
    return title


def get_or_create_instructor(cursor, name):
    """
    Finds an instructor by name in the users table.
    If not found, creates a placeholder account.
    Returns the instructor's user_id.
    """
    if not name or name == 'TBA':
        # Use the default placeholder instructor (id=2 from seed data)
        return 2

    # Clean name for email generation
    clean = re.sub(r'\s+', ' ', name).strip()
    parts = clean.split()

    if len(parts) >= 2:
        email = f"{parts[0][0].lower()}.{parts[-1].lower()}@college0.edu"
    else:
        email = f"{clean.lower().replace(' ', '.')}@college0.edu"

    # Make email safe (remove special chars)
    email = re.sub(r'[^a-z0-9.@]', '', email)

    # Check if this instructor already exists
    cursor.execute(
        "SELECT user_id FROM users WHERE email = ?", (email,)
    )
    existing = cursor.fetchone()
    if existing:
        return existing[0]

    # Create new user + instructor record
    cursor.execute("""
        INSERT INTO users
            (first_name, last_name, email,
             password_hash, role, status)
        VALUES (?, ?, ?, '$2b$12$cuny_placeholder_hash',
                'instructor', 'active')
    """, (
        parts[0] if parts else clean,
        ' '.join(parts[1:]) if len(parts) > 1 else '',
        email
    ))
    user_id = cursor.lastrowid

    cursor.execute("""
        INSERT INTO instructors (instructor_id, specialization)
        VALUES (?, 'Computer Science')
    """, (user_id,))

    return user_id


def seed():
    print("=" * 55)
    print("College0 — Seeding CUNY Course Data")
    print("=" * 55)
    print()

    # ── Load JSON ─────────────────────────────────────────────
    if not os.path.exists(JSON_PATH):
        print(f"ERROR: {JSON_PATH} not found.")
        print("Run python3 scrape_cuny.py first.")
        return

    with open(JSON_PATH) as f:
        sections = json.load(f)

    print(f"Loaded {len(sections)} sections from {JSON_PATH}")
    print()

    # ── Connect to database ───────────────────────────────────
    if not os.path.exists(DB_PATH):
        print(f"ERROR: {DB_PATH} not found.")
        print("Run python3 reset_db.py first.")
        return

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # ── Verify semester exists ────────────────────────────────
    cursor.execute(
        "SELECT semester_id, term_name FROM semesters "
        "WHERE semester_id = ?", (SEMESTER_ID,)
    )
    sem = cursor.fetchone()
    if not sem:
        print(f"ERROR: semester_id {SEMESTER_ID} not found.")
        print("Make sure reset_db.py has been run.")
        conn.close()
        return

    print(f"Loading into semester: {sem['term_name']}")
    print()

    # ── Track what we insert ──────────────────────────────────
    courses_added    = 0
    sections_added   = 0
    timeslots_added  = 0
    instructors_added = 0
    skipped          = 0

    course_cache     = {}  # code → course_id
    instructor_cache = {}  # name → user_id

    for s in sections:
        code  = clean_course_code(s.get('course_code', ''))
        title = clean_title(s.get('course_title', ''))
        instructor_raw = clean_instructor(
            s.get('instructor', 'TBA')
        )
        days       = s.get('days', [])
        time_start = s.get('time_start', 'TBA')
        time_end   = s.get('time_end', 'TBA')
        room       = s.get('room', 'TBA')
        capacity   = s.get('capacity', 30)
        timeslots  = s.get('all_timeslots', [])

        # Skip sections with no real schedule
        if not days or time_start == 'TBA':
            skipped += 1
            continue

        # ── Insert course if new ──────────────────────────────
        if code not in course_cache:
            is_core = 1 if code in CORE_COURSE_CODES else 0

            cursor.execute(
                "SELECT course_id FROM courses WHERE course_code = ?",
                (code,)
            )
            existing = cursor.fetchone()

            if existing:
                course_cache[code] = existing['course_id']
            else:
                cursor.execute("""
                    INSERT INTO courses
                        (course_code, title,
                         credit_hours, is_core)
                    VALUES (?, ?, 3, ?)
                """, (code, title or code, is_core))
                course_cache[code] = cursor.lastrowid
                courses_added += 1

        course_id = course_cache[code]

        # ── Get or create instructor ──────────────────────────
        if instructor_raw not in instructor_cache:
            before = cursor.execute(
                "SELECT COUNT(*) FROM instructors"
            ).fetchone()[0]

            instr_id = get_or_create_instructor(
                cursor, instructor_raw
            )
            instructor_cache[instructor_raw] = instr_id

            after = cursor.execute(
                "SELECT COUNT(*) FROM instructors"
            ).fetchone()[0]
            if after > before:
                instructors_added += 1

        instructor_id = instructor_cache[instructor_raw]

        # ── Insert class section ──────────────────────────────
        # Build a schedule slot string for display
        days_short = {
            'Monday': 'Mo', 'Tuesday': 'Tu', 'Wednesday': 'We',
            'Thursday': 'Th', 'Friday': 'Fr', 'Saturday': 'Sa'
        }
        day_str = ''.join(
            days_short.get(d, d[:2]) for d in days
        )
        schedule_slot = f"{day_str} {time_start}-{time_end}"

        try:
            cursor.execute("""
                INSERT INTO class_sections
                    (semester_id, course_id, instructor_id,
                     room, capacity,
                     current_enrollment, status)
                VALUES (?, ?, ?, ?, ?, 0, 'open')
            """, (
                SEMESTER_ID,
                course_id,
                instructor_id,
                room,
                capacity,
            ))
            section_id = cursor.lastrowid
            sections_added += 1

        except sqlite3.IntegrityError as e:
            skipped += 1
            continue

        # ── Insert timeslots ──────────────────────────────────
        for ts in timeslots:
            try:
                cursor.execute("""
                    INSERT OR IGNORE INTO section_timeslots
                        (section_id, day_of_week,
                         time_start, time_end)
                    VALUES (?, ?, ?, ?)
                """, (
                    section_id,
                    ts['day'],
                    ts['start'],
                    ts['end'],
                ))
                timeslots_added += 1
            except sqlite3.IntegrityError:
                pass

    conn.commit()

    # ── Final summary ─────────────────────────────────────────
    print(f"{'─'*55}")
    print(f"  New courses inserted    : {courses_added}")
    print(f"  New instructors created : {instructors_added}")
    print(f"  Class sections inserted : {sections_added}")
    print(f"  Timeslots inserted      : {timeslots_added}")
    print(f"  Skipped (no schedule)   : {skipped}")
    print(f"{'─'*55}")
    print()

    # Verify totals in database
    for table in ['courses', 'instructors',
                  'class_sections', 'section_timeslots']:
        count = cursor.execute(
            f"SELECT COUNT(*) FROM {table}"
        ).fetchone()[0]
        print(f"  {table:<25} : {count} rows total")

    print()

    # Show sample of what was loaded
    print("Sample sections now in database:")
    print("-" * 55)
    cursor.execute("""
        SELECT
            c.course_code,
            c.title,
            u.first_name || ' ' || u.last_name AS instructor,
            cs.room,
            GROUP_CONCAT(
                st.day_of_week || ' ' ||
                st.time_start || '-' || st.time_end,
                ' / '
            ) AS schedule
        FROM class_sections cs
        JOIN courses     c  ON cs.course_id     = c.course_id
        JOIN instructors i  ON cs.instructor_id  = i.instructor_id
        JOIN users       u  ON i.instructor_id   = u.user_id
        LEFT JOIN section_timeslots st
                            ON cs.section_id     = st.section_id
        WHERE cs.semester_id = ?
        GROUP BY cs.section_id
        ORDER BY c.course_code
        LIMIT 8
    """, (SEMESTER_ID,))

    for row in cursor.fetchall():
        print(f"{row['course_code']}  {row['title']}")
        print(f"  {row['instructor']} | {row['room']}")
        print(f"  {row['schedule']}")
        print()

    conn.close()
    print("=" * 55)
    print("Done. Run: python3 app.py")
    print("=" * 55)


if __name__ == "__main__":
    seed()