# ============================================================
# College0 / CUNY0 — All Database Queries
# File: queries.py
#
# How to use this file:
#   from queries import get_user_by_email, enroll_student
#   user = get_user_by_email('alice@college0.edu')
#
# Every function follows the same pattern:
#   1. Open a connection
#   2. Run the query with ? placeholders (never string formatting)
#   3. Fetch and return results
#   4. Close the connection
# ============================================================

import sqlite3
import re

DB_PATH = "college0.db"


# ============================================================
# CONNECTION HELPER
# Called at the top of every function in this file.
# Sets two important options every time:
#   - foreign_keys = ON  (SQLite ignores FK rules by default)
#   - row_factory        (lets you access columns by name)
# ============================================================

def get_connection():
    """
    Returns a database connection with:
    - foreign keys enforced
    - rows returned as dict-like objects (column_name: value)
      so you can access results like row['first_name']
      instead of row[0]
    """
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")

    # This makes every row return as a dict-like object
    # so you can do: row['email'] instead of row[2]
    conn.row_factory = sqlite3.Row
    return conn


# ============================================================
# GROUP 1 — AUTHENTICATION
# These queries run every time a user tries to log in
# or the system needs to load a user's profile.
# ============================================================

def get_user_by_email(email):
    """
    Used during login. Returns the user record if the email
    exists, or None if not found.
    The application then compares the provided password
    against the stored password_hash.
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            u.user_id,
            u.first_name,
            u.last_name,
            u.email,
            u.password_hash,    -- application compares this
            u.role,
            u.status,
            u.warning_count,
            u.must_change_pwd
        FROM users u
        WHERE u.email = ?       -- ? is a placeholder for the value
    """, (email,))              # the tuple (email,) fills in the ?

    user = cursor.fetchone()    # fetchone() returns one row or None
    conn.close()
    return user

# HOW TO USE:
# user = get_user_by_email('a.chen@college0.edu')
# if user is None:
#     print("Email not found")
# elif user['status'] == 'suspended':
#     print("Account suspended")
# else:
#     # compare password hash here
#     pass


def get_student_profile(user_id):
    """
    After login is confirmed, fetch the student's full profile
    by joining the users and students tables.
    This is what populates the student dashboard on load.
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            u.user_id,
            u.first_name,
            u.last_name,
            u.email,
            u.status            AS account_status,
            u.warning_count,
            u.must_change_pwd,
            s.student_code,
            s.cumulative_gpa,
            s.semester_gpa,
            s.honor_count,
            s.fine_amount_due,
            s.first_login_done
        FROM users u
        JOIN students s         -- JOIN connects the two tables
            ON u.user_id = s.student_id
        WHERE u.user_id = ?
    """, (user_id,))

    profile = cursor.fetchone()
    conn.close()
    return profile

# HOW TO USE:
# profile = get_student_profile(7)
# print(profile['first_name'])    # Alice
# print(profile['cumulative_gpa']) # 3.9


def get_instructor_profile(user_id):
    """
    Loads an instructor's profile after login.
    Joins users and instructors tables.
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            u.user_id,
            u.first_name,
            u.last_name,
            u.email,
            u.status            AS account_status,
            u.warning_count,
            i.specialization,
            i.rating_average,
            i.suspended_next_sem
        FROM users u
        JOIN instructors i
            ON u.user_id = i.instructor_id
        WHERE u.user_id = ?
    """, (user_id,))

    profile = cursor.fetchone()
    conn.close()
    return profile


# ============================================================
# GROUP 2 — PUBLIC DASHBOARD
# These run every time the home screen loads.
# No login required — returns only public-safe data.
# Never returns emails, password hashes, or internal IDs.
# ============================================================

def get_top_gpa_students(limit=5):
    """
    Returns the top students by cumulative GPA.
    Shown on the public dashboard — visible to all users
    including unauthenticated visitors.
    Only shows active students (hides suspended/terminated).
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            u.first_name,
            u.last_name,
            s.student_code,
            s.cumulative_gpa
        FROM users u
        JOIN students s ON u.user_id = s.student_id
        WHERE u.status = 'active'       -- hide suspended/terminated
        ORDER BY s.cumulative_gpa DESC  -- highest GPA first
        LIMIT ?                         -- only return the top N
    """, (limit,))

    results = cursor.fetchall()
    conn.close()
    return results

# HOW TO USE:
# top = get_top_gpa_students()
# for student in top:
#     print(f"{student['first_name']}: {student['cumulative_gpa']}")


def get_highest_rated_sections(limit=3):
    """
    Returns sections with the best average student rating.
    Only includes published and moderated reviews (not blocked).
    Uses AVG() to compute the average across all visible reviews
    for each section.
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            c.course_code,
            c.title                             AS course_title,
            u.first_name || ' ' || u.last_name  AS instructor_name,
            ROUND(AVG(r.rating), 2)             AS avg_rating,
            COUNT(r.review_id)                  AS review_count
        FROM reviews r
        JOIN class_sections cs  ON r.section_id    = cs.section_id
        JOIN courses c          ON cs.course_id     = c.course_id
        JOIN instructors i      ON cs.instructor_id = i.instructor_id
        JOIN users u            ON i.instructor_id  = u.user_id
        WHERE r.visibility_status IN ('published', 'moderated')
        GROUP BY r.section_id           -- compute average per section
        HAVING COUNT(r.review_id) >= 1  -- only sections with reviews
        ORDER BY avg_rating DESC        -- best rating first
        LIMIT ?
    """, (limit,))

    results = cursor.fetchall()
    conn.close()
    return results

# HOW TO USE:
# sections = get_highest_rated_sections()
# for s in sections:
#     print(f"{s['course_code']}: {s['avg_rating']} stars")


def get_lowest_rated_sections(limit=3):
    """
    Same as get_highest_rated_sections() but ordered ascending
    so the worst-rated sections appear first.
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            c.course_code,
            c.title                             AS course_title,
            u.first_name || ' ' || u.last_name  AS instructor_name,
            ROUND(AVG(r.rating), 2)             AS avg_rating,
            COUNT(r.review_id)                  AS review_count
        FROM reviews r
        JOIN class_sections cs  ON r.section_id    = cs.section_id
        JOIN courses c          ON cs.course_id     = c.course_id
        JOIN instructors i      ON cs.instructor_id = i.instructor_id
        JOIN users u            ON i.instructor_id  = u.user_id
        WHERE r.visibility_status IN ('published', 'moderated')
        GROUP BY r.section_id
        HAVING COUNT(r.review_id) >= 1
        ORDER BY avg_rating ASC         -- worst rating first
        LIMIT ?
    """, (limit,))

    results = cursor.fetchall()
    conn.close()
    return results


# ============================================================
# GROUP 3 — COURSE REGISTRATION
# The four gates run in order for every enrollment attempt.
# Gate 1: Is the semester in registration phase?
# Gate 2: Is the student below the 4-course limit?
# Gate 3: Is there no schedule conflict?
# Gate 4: Is there capacity available?
# All four must pass before an enrollment record is created.
# ============================================================

def get_available_sections(semester_id):
    """
    Returns all sections for the given semester with course
    info, instructor name, room, capacity, and seat count.
    This populates the course browser screen.
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            cs.section_id,
            c.course_code,
            c.title,
            c.is_core,
            u.first_name || ' ' || u.last_name  AS instructor_name,
            cs.room,
            cs.capacity,
            cs.current_enrollment,
            cs.capacity - cs.current_enrollment AS seats_remaining,
            cs.status
        FROM class_sections cs
        JOIN courses     c  ON cs.course_id     = c.course_id
        JOIN instructors i  ON cs.instructor_id  = i.instructor_id
        JOIN users       u  ON i.instructor_id   = u.user_id
        WHERE cs.semester_id = ?
        ORDER BY c.course_code
    """, (semester_id,))

    results = cursor.fetchall()
    conn.close()
    return results

# HOW TO USE:
# sections = get_available_sections(1)
# for s in sections:
#     print(f"{s['course_code']} | {s['seats_remaining']} seats | {s['status']}")


def get_student_enrollment_count(student_id, semester_id):
    """
    Gate 2 of registration.
    Counts how many sections a student is currently enrolled in
    for the given semester. If this returns 4, block registration.
    Only counts status = 'enrolled' (not dropped or cancelled).
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT COUNT(*) AS enrolled_count
        FROM enrollments e
        JOIN class_sections cs ON e.section_id = cs.section_id
        WHERE e.student_id  = ?
          AND cs.semester_id = ?
          AND e.status = 'enrolled'   -- only count active enrollments
    """, (student_id, semester_id))

    result = cursor.fetchone()
    conn.close()
    return result['enrolled_count']

# HOW TO USE:
# count = get_student_enrollment_count(7, 1)
# if count >= 4:
#     print("Maximum course load reached — cannot add more")


def check_schedule_conflict(student_id, new_section_id):
    """
    Gate 3 of registration.
    Detects if the new section's time slots overlap with any
    section the student is already enrolled in.

    THE OVERLAP FORMULA:
    Two time ranges [A_start, A_end] and [B_start, B_end] overlap
    if and only if:
        A_start < B_end   AND   A_end > B_start

    This works because the ONLY way two ranges do NOT overlap is:
        A ends before B starts  →  A_end <= B_start
        OR B ends before A starts  →  B_end <= A_start
    Negating that gives us the overlap condition above.

    Returns a list of conflicting section info rows.
    Empty list means no conflict — safe to proceed.
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT DISTINCT
            st_existing.section_id  AS conflicting_section_id,
            c.course_code           AS conflicting_course,
            st_existing.day_of_week,
            st_existing.time_start,
            st_existing.time_end
        FROM section_timeslots st_new

        -- Join to find existing timeslots that overlap
        JOIN section_timeslots st_existing
            ON  st_new.day_of_week  = st_existing.day_of_week
            AND st_new.time_start   < st_existing.time_end
            AND st_new.time_end     > st_existing.time_start

        -- Only look at sections this student is enrolled in
        JOIN enrollments e
            ON  st_existing.section_id = e.section_id
            AND e.student_id = ?
            AND e.status = 'enrolled'

        -- Get course info for the conflict message shown to user
        JOIN class_sections cs  ON st_existing.section_id = cs.section_id
        JOIN courses c          ON cs.course_id = c.course_id

        -- Only check timeslots belonging to the new section
        WHERE st_new.section_id = ?

        -- Do not flag the section against itself
          AND st_existing.section_id != ?
    """, (student_id, new_section_id, new_section_id))

    conflicts = cursor.fetchall()
    conn.close()
    return conflicts

# HOW TO USE:
# conflicts = check_schedule_conflict(7, 3)
# if conflicts:
#     for c in conflicts:
#         print(f"Conflict: {c['conflicting_course']} "
#               f"on {c['day_of_week']} {c['time_start']}-{c['time_end']}")
# else:
#     print("No conflict — proceed to capacity check")


def check_section_capacity(section_id):
    """
    Gate 4 of registration.
    Returns capacity info for a section.
    If seats_remaining <= 0, offer the waitlist instead.
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            cs.section_id,
            cs.capacity,
            cs.current_enrollment,
            cs.capacity - cs.current_enrollment AS seats_remaining,
            cs.status
        FROM class_sections cs
        WHERE cs.section_id = ?
    """, (section_id,))

    result = cursor.fetchone()
    conn.close()
    return result

# HOW TO USE:
# cap = check_section_capacity(3)
# if cap['seats_remaining'] <= 0:
#     print("Section full — offer waitlist")
# else:
#     print(f"{cap['seats_remaining']} seats available")


def enroll_student(student_id, section_id, semester_id):
    """
    Runs all four registration gates in sequence.
    If all pass, creates the enrollment record and updates
    the section's cached enrollment count.

    Returns a dict:
        {'success': True,  'message': 'Enrollment confirmed.'}
        {'success': False, 'message': 'Reason it failed.'}
        {'success': False, 'message': '...', 'offer_waitlist': True}
    """
    conn = get_connection()
    cursor = conn.cursor()

    try:
        # ── GATE 1: Semester phase check ──────────────────────
        # Registration is only open when phase = 'registration'
        cursor.execute("""
            SELECT phase FROM semesters WHERE semester_id = ?
        """, (semester_id,))
        sem = cursor.fetchone()

        if not sem or sem['phase'] != 'registration':
            return {'success': False,
                    'message': 'Registration is not currently open.'}

        # ── GATE 2: Course load check ──────────────────────────
        # Students may take 2-4 courses per semester
        cursor.execute("""
            SELECT COUNT(*) AS cnt
            FROM enrollments e
            JOIN class_sections cs ON e.section_id = cs.section_id
            WHERE e.student_id  = ?
              AND cs.semester_id = ?
              AND e.status = 'enrolled'
        """, (student_id, semester_id))

        if cursor.fetchone()['cnt'] >= 4:
            return {'success': False,
                    'message': 'Maximum course load of 4 reached.'}

        # ── GATE 3: Conflict check ─────────────────────────────
        # No two enrolled sections can overlap in time on the same day
        cursor.execute("""
            SELECT COUNT(*) AS conflicts
            FROM section_timeslots st_new
            JOIN section_timeslots st_existing
                ON  st_new.day_of_week = st_existing.day_of_week
                AND st_new.time_start  < st_existing.time_end
                AND st_new.time_end    > st_existing.time_start
            JOIN enrollments e
                ON  st_existing.section_id = e.section_id
                AND e.student_id = ?
                AND e.status = 'enrolled'
            WHERE st_new.section_id = ?
              AND st_existing.section_id != ?
        """, (student_id, section_id, section_id))

        if cursor.fetchone()['conflicts'] > 0:
            return {'success': False,
                    'message': 'Schedule conflict with an existing course.'}

        # ── GATE 4: Capacity check ─────────────────────────────
        # If section is full, offer the waitlist instead
        cursor.execute("""
            SELECT capacity, current_enrollment
            FROM class_sections
            WHERE section_id = ?
        """, (section_id,))
        sec = cursor.fetchone()

        if sec['current_enrollment'] >= sec['capacity']:
            return {'success': False,
                    'message': 'Section is full.',
                    'offer_waitlist': True}

        # ── ALL GATES PASSED: Create enrollment ────────────────
        cursor.execute("""
            INSERT INTO enrollments (student_id, section_id, status)
            VALUES (?, ?, 'enrolled')
        """, (student_id, section_id))

        # Update the cached enrollment count on the section.
        # CASE expression sets status to 'full' if now at capacity.
        cursor.execute("""
            UPDATE class_sections
            SET current_enrollment = current_enrollment + 1,
                status = CASE
                    WHEN current_enrollment + 1 >= capacity THEN 'full'
                    ELSE 'open'
                END
            WHERE section_id = ?
        """, (section_id,))

        conn.commit()
        return {'success': True, 'message': 'Enrollment confirmed.'}

    except sqlite3.IntegrityError:
        # UNIQUE constraint (student_id, section_id) was violated
        conn.rollback()
        return {'success': False,
                'message': 'Already enrolled in this section.'}

    finally:
        conn.close()

# HOW TO USE:
# result = enroll_student(student_id=10, section_id=2, semester_id=1)
# if result['success']:
#     print(result['message'])
# elif result.get('offer_waitlist'):
#     print("Section full — would you like to join the waitlist?")
# else:
#     print(result['message'])


# ============================================================
# GROUP 4 — GPA CALCULATION
# GPA is computed from grade_records.
# The result is also cached on the students table for speed.
# Always recompute and cache after each grading period closes.
# ============================================================

def calculate_student_gpa(student_id):
    """
    Computes the cumulative GPA directly from grade_records.
    Only includes completed enrollments with real grades
    (excludes W = Withdrawn and I = Incomplete).
    Returns the count and the GPA value.
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            COUNT(gr.grade_id)              AS courses_graded,
            ROUND(AVG(gr.grade_points), 2)  AS cumulative_gpa
        FROM grade_records gr
        JOIN enrollments e ON gr.enrollment_id = e.enrollment_id
        WHERE e.student_id = ?
          AND e.status = 'completed'
          AND gr.letter_grade NOT IN ('W', 'I')  -- exclude non-grades
    """, (student_id,))

    result = cursor.fetchone()
    conn.close()
    return result

# HOW TO USE:
# gpa_data = calculate_student_gpa(7)
# print(f"GPA: {gpa_data['cumulative_gpa']} from {gpa_data['courses_graded']} courses")


def update_student_gpa(student_id):
    """
    Recomputes the GPA and writes it back to the students table.
    Call this after the grading period closes for each student.
    Returns the new GPA value.
    """
    conn = get_connection()
    cursor = conn.cursor()

    # Step 1: Compute the new GPA from grade_records
    cursor.execute("""
        SELECT ROUND(AVG(gr.grade_points), 2) AS new_gpa
        FROM grade_records gr
        JOIN enrollments e ON gr.enrollment_id = e.enrollment_id
        WHERE e.student_id = ?
          AND e.status = 'completed'
          AND gr.letter_grade NOT IN ('W', 'I')
    """, (student_id,))

    # If no grades yet, default to 0.0 instead of None
    new_gpa = cursor.fetchone()['new_gpa'] or 0.0

    # Step 2: Write the new value into the cached field
    cursor.execute("""
        UPDATE students
        SET cumulative_gpa = ?
        WHERE student_id = ?
    """, (new_gpa, student_id))

    conn.commit()
    conn.close()
    return new_gpa

# HOW TO USE:
# new_gpa = update_student_gpa(7)
# print(f"Updated GPA: {new_gpa}")


# ============================================================
# GROUP 5 — ACADEMIC STANDING
# These queries run after the grading period closes.
# They identify which students need warnings, termination,
# or honor roll based on GPA thresholds from the SRS.
# ============================================================

def get_students_needing_standing_review():
    """
    Returns every active student along with their required
    standing action based on GPA rules from the SRS:

    TERMINATE   → cumulative GPA < 2.0
    WARNING     → cumulative GPA between 2.0 and 2.25
    HONOR_ROLL  → semester GPA > 3.75 OR cumulative GPA > 3.5
    OK          → no action needed

    The CASE expression evaluates conditions top to bottom
    and returns the first match — so TERMINATE is checked
    before WARNING before HONOR_ROLL.
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            u.user_id,
            u.first_name || ' ' || u.last_name AS full_name,
            u.status,
            s.cumulative_gpa,
            s.semester_gpa,
            s.honor_count,
            u.warning_count,
            CASE
                WHEN s.cumulative_gpa < 2.0
                    THEN 'TERMINATE'
                WHEN s.cumulative_gpa >= 2.0
                 AND s.cumulative_gpa <= 2.25
                    THEN 'WARNING'
                WHEN s.semester_gpa > 3.75
                  OR s.cumulative_gpa > 3.5
                    THEN 'HONOR_ROLL'
                ELSE 'OK'
            END AS standing_action
        FROM users u
        JOIN students s ON u.user_id = s.student_id
        WHERE u.status = 'active'
        ORDER BY s.cumulative_gpa ASC   -- worst GPAs first
    """)

    results = cursor.fetchall()
    conn.close()
    return results

# HOW TO USE:
# students = get_students_needing_standing_review()
# for s in students:
#     print(f"{s['full_name']}: GPA {s['cumulative_gpa']} → {s['standing_action']}")


def check_graduation_eligibility(student_id):
    """
    Checks all three graduation rules from the SRS:
      Rule 1: At least 8 courses completed with passing grades
      Rule 2: All 4 core courses completed
      Rule 3: Cumulative GPA > 2.0

    Returns a dict with the full breakdown so the application
    can show the student exactly what they are missing.
    """
    conn = get_connection()
    cursor = conn.cursor()

    # Rule 1: Count total completed courses with passing grades
    cursor.execute("""
        SELECT COUNT(*) AS total_completed
        FROM grade_records gr
        JOIN enrollments e      ON gr.enrollment_id = e.enrollment_id
        JOIN class_sections cs  ON e.section_id     = cs.section_id
        WHERE e.student_id = ?
          AND e.status = 'completed'
          AND gr.letter_grade NOT IN ('F', 'W', 'I')
    """, (student_id,))
    total = cursor.fetchone()['total_completed']

    # Rule 2: Count completed CORE courses with passing grades
    cursor.execute("""
        SELECT COUNT(*) AS core_completed
        FROM grade_records gr
        JOIN enrollments e      ON gr.enrollment_id = e.enrollment_id
        JOIN class_sections cs  ON e.section_id     = cs.section_id
        JOIN courses c          ON cs.course_id      = c.course_id
        WHERE e.student_id = ?
          AND e.status = 'completed'
          AND gr.letter_grade NOT IN ('F', 'W', 'I')
          AND c.is_core = 1       -- only count core courses
    """, (student_id,))
    core = cursor.fetchone()['core_completed']

    # Rule 3: Get the cached GPA from the students table
    cursor.execute("""
        SELECT cumulative_gpa FROM students WHERE student_id = ?
    """, (student_id,))
    gpa = cursor.fetchone()['cumulative_gpa']

    conn.close()

    # Eligible only if ALL three rules pass
    eligible = (total >= 8 and core >= 4 and gpa > 2.0)

    return {
        'eligible':        eligible,
        'total_completed': total,
        'core_completed':  core,
        'cumulative_gpa':  gpa,
        'needs_courses':   max(0, 8 - total),   # how many more needed
        'needs_core':      max(0, 4 - core),     # how many core needed
        'gpa_ok':          gpa > 2.0
    }

# HOW TO USE:
# result = check_graduation_eligibility(13)
# if result['eligible']:
#     print("Student qualifies to graduate")
# else:
#     print(f"Needs {result['needs_courses']} more courses")
#     print(f"Needs {result['needs_core']} more core courses")
#     print(f"GPA ok: {result['gpa_ok']}")


# ============================================================
# GROUP 6 — REVIEWS AND MODERATION
# Reviews are stored with TWO text fields:
#   original_text → what the student typed (registrar-only)
#   display_text  → masked version shown publicly
# Student identity is stored but hidden from public queries.
# Only the registrar view exposes who wrote each review.
# ============================================================

def get_public_reviews(section_id):
    """
    Returns visible reviews for a section for public display.
    Uses display_text (the masked version), NOT original_text.
    Does NOT return student_id — fully anonymous to viewers.
    Only returns published and moderated reviews (not blocked).
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            r.review_id,
            r.rating,
            r.display_text,         -- masked version only
            r.visibility_status,
            r.submitted_at
        FROM reviews r
        WHERE r.section_id = ?
          AND r.visibility_status IN ('published', 'moderated')
        ORDER BY r.submitted_at DESC
    """, (section_id,))

    results = cursor.fetchall()
    conn.close()
    return results

# HOW TO USE:
# reviews = get_public_reviews(2)
# for r in reviews:
#     print(f"Rating: {r['rating']}/5 — {r['display_text']}")


def get_reviews_registrar_view(section_id):
    """
    Registrar-only version of the reviews query.
    Includes student name, student code, and original_text
    (the unmasked, deanonymized version).
    Never show this data to students or instructors.
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            r.review_id,
            r.rating,
            r.original_text,        -- full unmasked text (registrar only)
            r.display_text,         -- what the public sees
            r.taboo_count,
            r.visibility_status,
            r.submitted_at,
            u.first_name || ' ' || u.last_name AS student_name,
            s.student_code
        FROM reviews r
        JOIN students s ON r.student_id  = s.student_id
        JOIN users u    ON s.student_id  = u.user_id
        WHERE r.section_id = ?
        ORDER BY r.submitted_at DESC
    """, (section_id,))

    results = cursor.fetchall()
    conn.close()
    return results


def scan_for_taboo_words(review_text):
    """
    Loads the taboo word list from the database and checks
    the review text against every word in it.
    Comparison is case-insensitive ('TERRIBLE' matches 'terrible').
    Returns a list of matched taboo words found in the text.
    """
    conn = get_connection()
    cursor = conn.cursor()

    # Load the full taboo word list managed by the registrar
    cursor.execute("SELECT word FROM taboo_words")
    taboo_list = [row['word'].lower() for row in cursor.fetchall()]
    conn.close()

    # Split the review text into individual words, lowercase
    words_in_review = re.findall(r'\b\w+\b', review_text.lower())

    # Return only the words that appear in the taboo list
    found = [w for w in words_in_review if w in taboo_list]
    return found

# HOW TO USE:
# found = scan_for_taboo_words("The pacing was terrible.")
# print(found)   # ['terrible']


def mask_taboo_words(text, found_words):
    """
    Replaces each taboo word in the text with asterisks
    of the same length, preserving original word length.
    Example: 'terrible' (8 chars) → '********' (8 asterisks)
    Replacement is case-insensitive so 'TERRIBLE' also gets masked.
    """
    masked = text
    for word in set(found_words):       # set() removes duplicates
        pattern = re.compile(re.escape(word), re.IGNORECASE)
        masked = pattern.sub('*' * len(word), masked)
    return masked

# HOW TO USE:
# text = "The pacing was terrible and lectures were awful."
# found = scan_for_taboo_words(text)
# print(f"Found {len(found)} taboo words: {found}")
#
# if len(found) == 0:
#     status, display = 'published', text
# elif len(found) <= 2:
#     status, display = 'moderated', mask_taboo_words(text, found)
# else:
#     status, display = 'blocked', None


def submit_review(student_id, section_id, rating, review_text):
    """
    Full review submission pipeline:
      1. Verifies student is enrolled in this section
      2. Verifies the instructor has not posted grades yet
      3. Scans for taboo words
      4. Decides status: published / moderated / blocked
      5. Inserts the review record
      6. Issues warnings if needed

    Returns a dict with status and message.
    """
    conn = get_connection()
    cursor = conn.cursor()

    try:
        # Check 1: Student must be enrolled
        cursor.execute("""
            SELECT enrollment_id FROM enrollments
            WHERE student_id = ? AND section_id = ?
              AND status IN ('enrolled', 'completed')
        """, (student_id, section_id))
        if not cursor.fetchone():
            return {'success': False,
                    'message': 'You are not enrolled in this section.'}

        # Check 2: No grade posted yet (cannot review after grading)
        cursor.execute("""
            SELECT gr.grade_id
            FROM grade_records gr
            JOIN enrollments e ON gr.enrollment_id = e.enrollment_id
            WHERE e.student_id = ? AND e.section_id = ?
        """, (student_id, section_id))
        if cursor.fetchone():
            return {'success': False,
                    'message': 'Cannot submit a review after grade is posted.'}

        # Check 3: Taboo word scan
        found_words = scan_for_taboo_words(review_text or '')
        count = len(found_words)

        if count == 0:
            status       = 'published'
            display_text = review_text
            warnings_to_issue = 0
        elif count <= 2:
            status       = 'moderated'
            display_text = mask_taboo_words(review_text, found_words)
            warnings_to_issue = 1
        else:
            status       = 'blocked'
            display_text = None
            warnings_to_issue = 2

        # Insert the review record
        cursor.execute("""
            INSERT INTO reviews
                (section_id, student_id, rating,
                 original_text, display_text,
                 taboo_count, visibility_status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (section_id, student_id, rating,
              review_text, display_text, count, status))

        conn.commit()

        # Issue warnings if needed (outside transaction is fine here)
        for _ in range(warnings_to_issue):
            issue_warning(
                student_id,
                f'Review for section {section_id} contained taboo words.',
                'review'
            )

        messages = {
            'published': 'Review submitted successfully.',
            'moderated': f'{count} word(s) were masked. A warning has been issued.',
            'blocked':   f'Review blocked — {count} prohibited words found. 2 warnings issued.'
        }

        return {'success': True, 'status': status, 'message': messages[status]}

    except sqlite3.IntegrityError:
        conn.rollback()
        return {'success': False,
                'message': 'You have already reviewed this section.'}
    finally:
        conn.close()

# HOW TO USE:
# result = submit_review(8, 1, 2, "The pacing was terrible.")
# print(result['message'])


# ============================================================
# GROUP 7 — WARNINGS AND DISCIPLINE
# Warnings are issued by multiple subsystems (review,
# academic, grading, etc.) but always through issue_warning().
# The honor roll function deactivates one warning when
# a student qualifies.
# ============================================================

def issue_warning(user_id, reason, source_module):
    """
    Issues a warning to a student or instructor.
    Steps:
      1. Inserts a warning_records row
      2. Increments users.warning_count (cached total)
      3. Checks if the suspension threshold (3) is reached
      4. If so, suspends the student or flags the instructor

    source_module must be one of:
      'review', 'academic', 'disciplinary',
      'grading', 'graduation', 'complaint'
    """
    conn = get_connection()
    cursor = conn.cursor()

    try:
        # Step 1: Insert the warning record
        cursor.execute("""
            INSERT INTO warning_records
                (user_id, reason, source_module, active_flag)
            VALUES (?, ?, ?, 1)
        """, (user_id, reason, source_module))



        # Step 2: Check if threshold reached
        cursor.execute("""
            SELECT warning_count, role FROM users WHERE user_id = ?
        """, (user_id,))
        user = cursor.fetchone()

        if user['warning_count'] >= 3:
            if user['role'] == 'student':
                # Suspend student and set fine
                cursor.execute("""
                    UPDATE users SET status = 'suspended'
                    WHERE user_id = ?
                """, (user_id,))
                cursor.execute("""
                    UPDATE students SET fine_amount_due = 150.00
                    WHERE student_id = ?
                """, (user_id,))

            elif user['role'] == 'instructor':
                # Prevent teaching next semester
                cursor.execute("""
                    UPDATE instructors SET suspended_next_sem = 1
                    WHERE instructor_id = ?
                """, (user_id,))

        conn.commit()
        return {'success': True, 'new_count': user['warning_count']}

    finally:
        conn.close()

# HOW TO USE:
# result = issue_warning(8, "Taboo word in review", "review")
# print(f"Warning issued. Total warnings: {result['new_count']}")


def apply_honor_roll(student_id):
    """
    Awards honor roll to a student.
    If the student has any active warnings, deactivates the
    oldest one (the SRS says one honor removes one warning).
    Always increments the honor_count on the students table.
    """
    conn = get_connection()
    cursor = conn.cursor()

    try:
        # Find the oldest active warning for this student
        cursor.execute("""
            SELECT warning_id
            FROM warning_records
            WHERE user_id = ?
              AND active_flag = 1
            ORDER BY issued_at ASC  -- oldest warning first
            LIMIT 1
        """, (student_id,))
        warning = cursor.fetchone()

        if warning:
            # Deactivate the warning
            cursor.execute("""
                UPDATE warning_records
                SET active_flag = 0,
                    removed_at  = datetime('now')
                WHERE warning_id = ?
            """, (warning['warning_id'],))

        # Always increment honor count regardless of warnings
        cursor.execute("""
            UPDATE students
            SET honor_count = honor_count + 1
            WHERE student_id = ?
        """, (student_id,))

        conn.commit()
        return {
            'honor_applied':   True,
            'warning_removed': warning is not None
        }

    finally:
        conn.close()

# HOW TO USE:
# result = apply_honor_roll(7)
# if result['warning_removed']:
#     print("Honor roll applied — one warning removed")
# else:
#     print("Honor roll applied — no warnings to remove")


def get_all_warnings_for_user(user_id):
    """
    Returns the full warning history for a user.
    Active warnings (active_flag=1) count toward suspension.
    Removed warnings (active_flag=0) are kept for audit trail.
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            warning_id,
            reason,
            source_module,
            issued_at,
            active_flag,
            removed_at
        FROM warning_records
        WHERE user_id = ?
        ORDER BY issued_at DESC
    """, (user_id,))

    results = cursor.fetchall()
    conn.close()
    return results


# ============================================================
# GROUP 8 — WAITLIST
# Only the assigned instructor of a section may admit
# a student from the waitlist (SRS requirement).
# The waitlist is ordered by position — position 1 is first.
# ============================================================

def get_waitlist(section_id):
    """
    Returns the full waitlist for a section ordered by position.
    Used by instructors to view who is waiting and select
    who to admit. Only returns entries with status = 'waiting'.
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            we.waitlist_id,
            we.position,
            we.added_at,
            u.first_name || ' ' || u.last_name AS student_name,
            s.student_code
        FROM waitlist_entries we
        JOIN students s ON we.student_id = s.student_id
        JOIN users    u ON s.student_id  = u.user_id
        WHERE we.section_id = ?
          AND we.status = 'waiting'
        ORDER BY we.position ASC    -- position 1 is first in line
    """, (section_id,))

    results = cursor.fetchall()
    conn.close()
    return results

# HOW TO USE:
# waitlist = get_waitlist(3)
# for entry in waitlist:
#     print(f"#{entry['position']}: {entry['student_name']}")


def add_to_waitlist(student_id, section_id):
    """
    Adds a student to the waitlist for a full section.
    Automatically assigns the next available position number.
    Returns failure if student is already on the waitlist.
    """
    conn = get_connection()
    cursor = conn.cursor()

    try:
        # Get the current last position on this waitlist
        cursor.execute("""
            SELECT COALESCE(MAX(position), 0) AS last_position
            FROM waitlist_entries
            WHERE section_id = ? AND status = 'waiting'
        """, (section_id,))
        last_pos = cursor.fetchone()['last_position']
        next_pos = last_pos + 1     # this student goes after the last one

        cursor.execute("""
            INSERT INTO waitlist_entries
                (student_id, section_id, position, status)
            VALUES (?, ?, ?, 'waiting')
        """, (student_id, section_id, next_pos))

        conn.commit()
        return {'success': True, 'position': next_pos}

    except sqlite3.IntegrityError:
        conn.rollback()
        return {'success': False,
                'message': 'Already on the waitlist for this section.'}
    finally:
        conn.close()

# HOW TO USE:
# result = add_to_waitlist(7, 3)
# if result['success']:
#     print(f"Added to waitlist at position #{result['position']}")


def admit_from_waitlist(instructor_id, student_id, section_id):
    """
    Instructor admits a student from the waitlist.
    Verifies three things before proceeding:
      1. This instructor is assigned to this section
      2. A seat is available (someone must have dropped)
      3. The student is actually on the waitlist

    If all pass:
      - Creates an enrollment record
      - Marks the waitlist entry as 'admitted'
      - Updates the section enrollment count
    """
    conn = get_connection()
    cursor = conn.cursor()

    try:
        # Verify 1: Instructor must be assigned to this section
        cursor.execute("""
            SELECT 1 FROM class_sections
            WHERE section_id = ? AND instructor_id = ?
        """, (section_id, instructor_id))
        if not cursor.fetchone():
            return {'success': False,
                    'message': 'You are not the instructor for this section.'}

        # Verify 2: A seat must be open
        cursor.execute("""
            SELECT capacity, current_enrollment
            FROM class_sections WHERE section_id = ?
        """, (section_id,))
        sec = cursor.fetchone()
        if sec['current_enrollment'] >= sec['capacity']:
            return {'success': False,
                    'message': 'No open seat — a student must drop first.'}

        # Verify 3: Student must be on the waitlist
        cursor.execute("""
            SELECT waitlist_id FROM waitlist_entries
            WHERE student_id = ? AND section_id = ?
              AND status = 'waiting'
        """, (student_id, section_id))
        entry = cursor.fetchone()
        if not entry:
            return {'success': False,
                    'message': 'Student is not on the waitlist.'}

        # All checks passed — create the enrollment
        cursor.execute("""
            INSERT INTO enrollments (student_id, section_id, status)
            VALUES (?, ?, 'enrolled')
        """, (student_id, section_id))

        # Mark the waitlist entry as admitted
        cursor.execute("""
            UPDATE waitlist_entries SET status = 'admitted'
            WHERE waitlist_id = ?
        """, (entry['waitlist_id'],))

        # Update the section's cached enrollment count
        cursor.execute("""
            UPDATE class_sections
            SET current_enrollment = current_enrollment + 1
            WHERE section_id = ?
        """, (section_id,))

        conn.commit()
        return {'success': True,
                'message': 'Student admitted from waitlist.'}

    finally:
        conn.close()

# HOW TO USE:
# result = admit_from_waitlist(instructor_id=3, student_id=7, section_id=3)
# print(result['message'])