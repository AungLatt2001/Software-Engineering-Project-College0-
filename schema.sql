-- ============================================================
-- College0 / CUNY0 — Complete Database Schema
-- File: schema.sql
-- Run with: python initialize_db.py
--           OR open in DB Browser for SQLite and execute
-- SQLite version — foreign keys must be enabled per connection
-- ============================================================

-- IMPORTANT: This must be the first statement in every
-- connection. SQLite disables foreign key enforcement by
-- default. Without this, FK violations are silently ignored.
PRAGMA foreign_keys = ON;


-- ============================================================
-- TABLE 1: users
-- The parent identity table for all authenticated users.
-- Every student, instructor, and registrar has a row here.
-- Visitors do NOT have rows here — they only have rows in
-- visitor_applications until admitted.
-- ============================================================
CREATE TABLE IF NOT EXISTS users (
    user_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    first_name      TEXT    NOT NULL,
    last_name       TEXT    NOT NULL,
    email           TEXT    NOT NULL UNIQUE,
    password_hash   TEXT    NOT NULL,

    -- Role determines which extension table this user has
    -- and which screens/functions they can access
    role            TEXT    NOT NULL
                    CHECK (role IN ('student', 'instructor', 'registrar')),

    -- Status tracks the user's current lifecycle state
    status          TEXT    NOT NULL DEFAULT 'active'
                    CHECK (status IN ('active', 'suspended',
                                      'terminated', 'graduated')),

    -- Cached count of active warnings for fast threshold checks.
    -- Source of truth is always warning_records (active_flag = 1).
    -- This cache is updated every time a warning is issued or removed.
    warning_count   INTEGER NOT NULL DEFAULT 0,

    -- When 1, the system forces a password change on next login.
    -- Set to 1 for all newly admitted students.
    -- Set back to 0 after successful password change.
    must_change_pwd INTEGER NOT NULL DEFAULT 0
                    CHECK (must_change_pwd IN (0, 1)),

    created_at      TEXT    NOT NULL DEFAULT (datetime('now'))
);


-- ============================================================
-- TABLE 2: students
-- Extends users for student-specific data.
-- student_id is both PK and FK — the same integer that
-- identifies this student in users also identifies them here.
-- There is no AUTOINCREMENT because we supply the user_id.
-- ============================================================
CREATE TABLE IF NOT EXISTS students (
    student_id          INTEGER PRIMARY KEY
                        REFERENCES users(user_id)
                        ON DELETE CASCADE,

    -- Human-readable ID shown to the student (e.g. "STU-2026-0042")
    -- The internal student_id integer is used in SQL joins only
    student_code        TEXT    NOT NULL UNIQUE,

    -- GPA fields are cached for performance.
    -- Recomputed from grade_records after each grading period.
    cumulative_gpa      REAL    NOT NULL DEFAULT 0.0,
    semester_gpa        REAL    NOT NULL DEFAULT 0.0,

    -- Incremented each time student qualifies for honor roll.
    -- Each honor can remove one active warning.
    honor_count         INTEGER NOT NULL DEFAULT 0,

    -- If suspended, this stores the semester_id after which
    -- they may return. NULL means not currently suspended.
    suspension_end_sem  INTEGER REFERENCES semesters(semester_id),

    -- Outstanding fine owed by the student (from suspension).
    -- Must be paid (set to 0.0) before reinstatement.
    fine_amount_due     REAL    NOT NULL DEFAULT 0.0,

    -- Tracks whether first-login tutorial has been completed
    first_login_done    INTEGER NOT NULL DEFAULT 0
                        CHECK (first_login_done IN (0, 1))
);


-- ============================================================
-- TABLE 3: instructors
-- Extends users for instructor-specific data.
-- Same PK-as-FK pattern as students.
-- ============================================================
CREATE TABLE IF NOT EXISTS instructors (
    instructor_id       INTEGER PRIMARY KEY
                        REFERENCES users(user_id)
                        ON DELETE CASCADE,

    specialization      TEXT,

    -- Cached average of all review ratings across all sections.
    -- Updated after each grading period closes.
    -- If this drops below 2.0, a warning is issued.
    rating_average      REAL    NOT NULL DEFAULT 0.0,

    -- When 1, this instructor cannot be assigned to sections
    -- in the next semester. Set when all their sections
    -- were cancelled during the running period.
    suspended_next_sem  INTEGER NOT NULL DEFAULT 0
                        CHECK (suspended_next_sem IN (0, 1))
);


-- ============================================================
-- TABLE 4: registrars
-- Extends users for registrar-specific data.
-- Minimal extension — registrars mainly use the users table.
-- ============================================================
CREATE TABLE IF NOT EXISTS registrars (
    registrar_id    INTEGER PRIMARY KEY
                    REFERENCES users(user_id)
                    ON DELETE CASCADE,

    -- Reserved for future multi-tier admin roles
    admin_level     INTEGER NOT NULL DEFAULT 1
);


-- ============================================================
-- TABLE 5: visitor_applications
-- Stores every application submitted by a visitor.
-- When accepted, a users row is created and this row is
-- updated. The application is a historical record — it is
-- never deleted after a decision is made.
-- ============================================================
CREATE TABLE IF NOT EXISTS visitor_applications (
    application_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    applicant_name      TEXT    NOT NULL,
    email               TEXT    NOT NULL,

    -- 'student' or 'instructor'
    application_type    TEXT    NOT NULL
                        CHECK (application_type IN ('student', 'instructor')),

    -- Only required for student applications.
    -- GPA must be > 3.0 for auto-approval.
    -- Nullable because instructor apps have no GPA requirement.
    prior_gpa           REAL,

    personal_statement  TEXT,

    -- Lifecycle of the application
    status              TEXT    NOT NULL DEFAULT 'pending'
                        CHECK (status IN ('pending', 'accepted', 'rejected')),

    -- When registrar admits below-threshold or over-quota student,
    -- they must provide a written justification.
    override_flag       INTEGER NOT NULL DEFAULT 0
                        CHECK (override_flag IN (0, 1)),
    override_reason     TEXT,

    -- Set when registrar reviews the application
    reviewed_by         INTEGER REFERENCES registrars(registrar_id),
    reviewed_at         TEXT,
    submitted_at        TEXT    NOT NULL DEFAULT (datetime('now'))
);


-- ============================================================
-- TABLE 6: semesters
-- One row per semester. The phase field controls which
-- operations the entire system permits at any given time.
-- ============================================================
CREATE TABLE IF NOT EXISTS semesters (
    semester_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    term_name       TEXT    NOT NULL,   -- e.g. "Spring 2026"
    year            INTEGER NOT NULL,

    -- The current phase controls system-wide permissions:
    -- setup        → registrar creates sections, assigns instructors
    -- registration → students register for courses
    -- running      → classes in progress, no normal registration
    -- grading      → instructors submit grades
    -- finalized    → GPA computed, standings updated, semester closed
    phase           TEXT    NOT NULL DEFAULT 'setup'
                    CHECK (phase IN ('setup', 'registration',
                                     'running', 'grading', 'finalized')),

    -- Maximum students to accept this semester via admissions
    student_quota   INTEGER NOT NULL DEFAULT 30,

    start_date      TEXT    NOT NULL,
    end_date        TEXT    NOT NULL,
    created_at      TEXT    NOT NULL DEFAULT (datetime('now'))
);


-- ============================================================
-- TABLE 7: courses
-- Catalog definition of a course, independent of semester.
-- "CSC 21200 — Data Structures" is one course that can be
-- offered as many class sections across many semesters.
-- ============================================================
CREATE TABLE IF NOT EXISTS courses (
    course_id       INTEGER PRIMARY KEY AUTOINCREMENT,

    -- e.g. "CSC 21200" — must be unique across the catalog
    course_code     TEXT    NOT NULL UNIQUE,

    -- e.g. "Data Structures"
    title           TEXT    NOT NULL,

    credit_hours    INTEGER NOT NULL DEFAULT 3
                    CHECK (credit_hours BETWEEN 1 AND 6),

    -- Graduation requires 4 core courses.
    -- 0 = elective, 1 = core (required for graduation)
    is_core         INTEGER NOT NULL DEFAULT 0
                    CHECK (is_core IN (0, 1)),

    description     TEXT
);


-- ============================================================
-- TABLE 8: class_sections
-- A specific offering of a course in one semester.
-- This is what students actually enroll in — not the course.
-- ============================================================
CREATE TABLE IF NOT EXISTS class_sections (
    section_id          INTEGER PRIMARY KEY AUTOINCREMENT,

    -- Which semester this section runs in
    semester_id         INTEGER NOT NULL
                        REFERENCES semesters(semester_id),

    -- Which catalog course this section is an offering of
    course_id           INTEGER NOT NULL
                        REFERENCES courses(course_id),

    -- Which instructor teaches this section
    instructor_id       INTEGER NOT NULL
                        REFERENCES instructors(instructor_id),

    room                TEXT,

    -- Maximum students allowed in this section
    capacity            INTEGER NOT NULL DEFAULT 30
                        CHECK (capacity > 0),

    -- Cached enrollment count. Authoritative count is always:
    -- SELECT COUNT(*) FROM enrollments
    -- WHERE section_id = ? AND status = 'enrolled'
    -- This cache updates on every enrollment change.
    current_enrollment  INTEGER NOT NULL DEFAULT 0,

    -- open      → accepting enrollments
    -- full      → at capacity, waitlist available
    -- cancelled → fewer than 3 students during running period
    -- completed → grading period finished
    status              TEXT    NOT NULL DEFAULT 'open'
                        CHECK (status IN ('open', 'full',
                                          'cancelled', 'completed'))
);


-- ============================================================
-- TABLE 9: section_timeslots
-- One row per day per section.
-- A section meeting MWF 10:00-10:50 has THREE rows here:
--   (section_id, 'Monday',    '10:00', '10:50')
--   (section_id, 'Wednesday', '10:00', '10:50')
--   (section_id, 'Friday',    '10:00', '10:50')
-- This structure enables SQL-based schedule conflict detection.
-- ============================================================
CREATE TABLE IF NOT EXISTS section_timeslots (
    timeslot_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    section_id      INTEGER NOT NULL
                    REFERENCES class_sections(section_id)
                    ON DELETE CASCADE,

    day_of_week     TEXT    NOT NULL
                    CHECK (day_of_week IN ('Monday', 'Tuesday', 'Wednesday',
                                           'Thursday', 'Friday', 'Saturday')),

    -- Times stored as "HH:MM" 24-hour strings.
    -- String comparison works for time ordering because
    -- "09:00" < "10:00" as strings (left-aligned, zero-padded).
    time_start      TEXT    NOT NULL,
    time_end        TEXT    NOT NULL,

    -- A section cannot have two timeslots on the same day
    UNIQUE (section_id, day_of_week)
);


-- ============================================================
-- TABLE 10: enrollments
-- Junction table: resolves the many-to-many relationship
-- between students and class_sections.
-- One row = one student in one section.
-- ============================================================
CREATE TABLE IF NOT EXISTS enrollments (
    enrollment_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id      INTEGER NOT NULL
                    REFERENCES students(student_id),
    section_id      INTEGER NOT NULL
                    REFERENCES class_sections(section_id),

    -- enrolled   → currently active enrollment
    -- dropped    → student dropped the course
    -- cancelled  → section was cancelled (running period)
    -- completed  → grading has been posted for this enrollment
    status          TEXT    NOT NULL DEFAULT 'enrolled'
                    CHECK (status IN ('enrolled', 'dropped',
                                      'cancelled', 'completed')),

    enrolled_at     TEXT    NOT NULL DEFAULT (datetime('now')),

    -- Prevents double-enrollment: one student, one section
    UNIQUE (student_id, section_id)
);


-- ============================================================
-- TABLE 11: waitlist_entries
-- Stores students queued for a section that is at capacity.
-- Position 1 is first in line.
-- Only the instructor of that section may admit a student.
-- ============================================================
CREATE TABLE IF NOT EXISTS waitlist_entries (
    waitlist_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id      INTEGER NOT NULL
                    REFERENCES students(student_id),
    section_id      INTEGER NOT NULL
                    REFERENCES class_sections(section_id),

    -- Queue position. Position 1 = next to be admitted.
    -- Positions shift down when someone ahead is admitted.
    position        INTEGER NOT NULL,

    -- waiting  → in queue
    -- admitted → instructor admitted this student
    --            (enrollment record created, this status set)
    -- removed  → student removed themselves from waitlist
    status          TEXT    NOT NULL DEFAULT 'waiting'
                    CHECK (status IN ('waiting', 'admitted', 'removed')),

    added_at        TEXT    NOT NULL DEFAULT (datetime('now')),

    -- One student cannot be on the waitlist twice for the same section
    UNIQUE (student_id, section_id)
);


-- ============================================================
-- TABLE 12: grade_records
-- Stores the final grade for one enrollment.
-- Created by the instructor during the grading period.
-- One enrollment can have at most one grade record (UNIQUE).
-- ============================================================
CREATE TABLE IF NOT EXISTS grade_records (
    grade_id        INTEGER PRIMARY KEY AUTOINCREMENT,

    -- Each enrollment gets at most one grade
    enrollment_id   INTEGER NOT NULL UNIQUE
                    REFERENCES enrollments(enrollment_id),

    -- Valid letter grades
    -- W = Withdrawn, I = Incomplete
    letter_grade    TEXT    NOT NULL
                    CHECK (letter_grade IN ('A', 'B', 'C', 'D', 'F', 'W', 'I')),

    -- Numeric value for GPA computation
    -- A=4.0  B=3.0  C=2.0  D=1.0  F=0.0  W=0.0  I=0.0
    grade_points    REAL    NOT NULL
                    CHECK (grade_points BETWEEN 0.0 AND 4.0),

    posted_at       TEXT    NOT NULL DEFAULT (datetime('now'))
);


-- ============================================================
-- TABLE 13: reviews
-- Anonymous student ratings and text reviews for sections.
-- The student identity IS stored (for registrar deanonymization)
-- but is hidden from all non-registrar queries.
-- Two text columns:
--   original_text → what the student typed (registrar-only)
--   display_text  → masked version shown publicly
-- ============================================================
CREATE TABLE IF NOT EXISTS reviews (
    review_id           INTEGER PRIMARY KEY AUTOINCREMENT,
    section_id          INTEGER NOT NULL
                        REFERENCES class_sections(section_id),
    student_id          INTEGER NOT NULL
                        REFERENCES students(student_id),

    -- Star rating 1 to 5
    rating              INTEGER NOT NULL
                        CHECK (rating BETWEEN 1 AND 5),

    -- What the student actually wrote (never shown except to registrar)
    original_text       TEXT,

    -- Masked version with taboo words replaced by asterisks.
    -- This is what appears in the public review display.
    display_text        TEXT,

    -- Count of taboo words found (0, 1, 2, or 3+)
    taboo_count         INTEGER NOT NULL DEFAULT 0,

    -- pending   → just submitted, awaiting moderation
    -- published → clean, shown as-is
    -- moderated → taboo words masked, shown with warning note
    -- blocked   → 3+ taboo words, never shown publicly
    visibility_status   TEXT    NOT NULL DEFAULT 'pending'
                        CHECK (visibility_status IN ('pending', 'published',
                                                     'moderated', 'blocked')),

    submitted_at        TEXT    NOT NULL DEFAULT (datetime('now')),

    -- One review per student per section
    UNIQUE (student_id, section_id)
);


-- ============================================================
-- TABLE 14: taboo_words
-- Registrar-managed list of prohibited words.
-- The review moderation system scans submitted text against
-- every word in this table.
-- ============================================================
CREATE TABLE IF NOT EXISTS taboo_words (
    word_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    word        TEXT    NOT NULL UNIQUE,
    added_by    INTEGER NOT NULL
                REFERENCES registrars(registrar_id),
    added_at    TEXT    NOT NULL DEFAULT (datetime('now'))
);


-- ============================================================
-- TABLE 15: warning_records
-- Full audit trail of every warning issued in the system.
-- Never deleted — even removed warnings are kept for history.
-- active_flag = 1 means this warning is currently counting
--               toward the suspension threshold.
-- active_flag = 0 means honor roll removed this warning.
-- ============================================================
CREATE TABLE IF NOT EXISTS warning_records (
    warning_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL
                    REFERENCES users(user_id),
    reason          TEXT    NOT NULL,

    -- Which subsystem issued this warning
    source_module   TEXT    NOT NULL
                    CHECK (source_module IN ('review', 'academic',
                                             'disciplinary', 'grading',
                                             'graduation', 'complaint')),

    issued_at       TEXT    NOT NULL DEFAULT (datetime('now')),

    -- 1 = counting toward suspension threshold
    -- 0 = deactivated by honor roll
    active_flag     INTEGER NOT NULL DEFAULT 1
                    CHECK (active_flag IN (0, 1)),

    -- Set when honor roll removes this warning
    removed_at      TEXT
);


-- ============================================================
-- TABLE 16: complaints
-- Stores the full lifecycle of a complaint from filing
-- through resolution. Both filer and target reference users.
-- ============================================================
CREATE TABLE IF NOT EXISTS complaints (
    complaint_id        INTEGER PRIMARY KEY AUTOINCREMENT,

    -- The user who filed the complaint (student or instructor)
    filed_by_user_id    INTEGER NOT NULL
                        REFERENCES users(user_id),

    -- The user being complained about (student or instructor)
    target_user_id      INTEGER NOT NULL
                        REFERENCES users(user_id),

    complaint_text      TEXT    NOT NULL,

    -- pending       → just filed, awaiting review
    -- investigating → registrar is reviewing
    -- resolved      → decision made
    status              TEXT    NOT NULL DEFAULT 'pending'
                        CHECK (status IN ('pending',
                                          'investigating',
                                          'resolved')),

    -- What action the registrar took after investigating
    resolution_note     TEXT,
    penalty_applied     TEXT,

    -- Which registrar resolved this complaint
    resolved_by         INTEGER REFERENCES registrars(registrar_id),
    filed_at            TEXT    NOT NULL DEFAULT (datetime('now')),
    resolved_at         TEXT
);


-- ============================================================
-- TABLE 17: graduation_applications
-- Stores graduation requests submitted by students.
-- Registrar verifies: 8 courses completed, 4 core courses,
-- cumulative GPA > 2.0.
-- If requirements not met → warning for reckless application.
-- ============================================================
CREATE TABLE IF NOT EXISTS graduation_applications (
    graduation_app_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id          INTEGER NOT NULL
                        REFERENCES students(student_id),

    submitted_at        TEXT    NOT NULL DEFAULT (datetime('now')),

    -- pending  → awaiting registrar review
    -- approved → graduation granted, student offboarded
    -- rejected → requirements not met
    decision_status     TEXT    NOT NULL DEFAULT 'pending'
                        CHECK (decision_status IN ('pending',
                                                   'approved',
                                                   'rejected')),

    -- Reason provided when rejected
    rejection_reason    TEXT,

    -- 1 = a reckless graduation warning was issued for this application
    -- Prevents issuing the same warning twice on re-review
    warning_issued      INTEGER NOT NULL DEFAULT 0
                        CHECK (warning_issued IN (0, 1)),

    reviewed_by         INTEGER REFERENCES registrars(registrar_id),
    reviewed_at         TEXT
);


-- ============================================================
-- TABLE 18: ai_queries
-- Logs every question asked to the AI assistant and the
-- answer provided. user_id is nullable — visitors can ask
-- questions without an account.
-- ============================================================
CREATE TABLE IF NOT EXISTS ai_queries (
    query_id            INTEGER PRIMARY KEY AUTOINCREMENT,

    -- Nullable: visitors have no user_id
    user_id             INTEGER REFERENCES users(user_id),

    question_text       TEXT    NOT NULL,
    answer_text         TEXT,

    -- vector_db → answered from local knowledge base (no warning needed)
    -- llm       → answered by external LLM (show hallucination warning)
    -- none      → neither source could answer
    answer_source       TEXT    NOT NULL
                        CHECK (answer_source IN ('vector_db', 'llm', 'none')),

    -- 1 = the hallucination warning banner was shown to the user
    warning_displayed   INTEGER NOT NULL DEFAULT 0
                        CHECK (warning_displayed IN (0, 1)),

    created_at          TEXT    NOT NULL DEFAULT (datetime('now'))
);


-- ============================================================
-- INDEXES
-- Indexes speed up queries on columns that are frequently
-- used in WHERE clauses and JOINs.
-- SQLite automatically creates indexes for PRIMARY KEY and
-- UNIQUE columns. We add indexes for common FK lookups.
-- ============================================================

-- Fast lookup of all enrollments for a student
CREATE INDEX IF NOT EXISTS idx_enrollments_student
    ON enrollments(student_id);

-- Fast lookup of all enrollments for a section
CREATE INDEX IF NOT EXISTS idx_enrollments_section
    ON enrollments(section_id);

-- Fast lookup of timeslots for conflict checking
CREATE INDEX IF NOT EXISTS idx_timeslots_section
    ON section_timeslots(section_id);

-- Fast lookup of all sections in a semester
CREATE INDEX IF NOT EXISTS idx_sections_semester
    ON class_sections(semester_id);

-- Fast lookup of all warnings for a user
CREATE INDEX IF NOT EXISTS idx_warnings_user
    ON warning_records(user_id);

-- Fast lookup of all reviews for a section
CREATE INDEX IF NOT EXISTS idx_reviews_section
    ON reviews(section_id);

-- Fast lookup of all grade records for GPA computation
CREATE INDEX IF NOT EXISTS idx_grades_enrollment
    ON grade_records(enrollment_id);





    -- ============================================================
-- TRIGGER 1: After a new enrollment is inserted,
-- update the section's current_enrollment count and status.
-- Fires on every INSERT into enrollments.
-- ============================================================
CREATE TRIGGER IF NOT EXISTS trg_enrollment_insert
AFTER INSERT ON enrollments
FOR EACH ROW
WHEN NEW.status = 'enrolled'
BEGIN
    UPDATE class_sections
    SET
        current_enrollment = current_enrollment + 1,
        status = CASE
            WHEN current_enrollment + 1 >= capacity THEN 'full'
            ELSE 'open'
        END
    WHERE section_id = NEW.section_id;
END;


-- ============================================================
-- TRIGGER 2: After an enrollment status changes to dropped
-- or cancelled, decrement the section count.
-- Fires on every UPDATE to enrollments.
-- ============================================================
CREATE TRIGGER IF NOT EXISTS trg_enrollment_status_change
AFTER UPDATE ON enrollments
FOR EACH ROW
WHEN OLD.status = 'enrolled'
  AND NEW.status IN ('dropped', 'cancelled')
BEGIN
    UPDATE class_sections
    SET
        current_enrollment = MAX(0, current_enrollment - 1),
        status = CASE
            WHEN current_enrollment - 1 < capacity THEN 'open'
            ELSE 'full'
        END
    WHERE section_id = NEW.section_id;
END;

-- ============================================================
-- TRIGGER 3: After a warning record is inserted,
-- increment the user's cached warning_count.
-- Fires on every INSERT into warning_records.
-- ============================================================
CREATE TRIGGER IF NOT EXISTS trg_warning_insert
AFTER INSERT ON warning_records
FOR EACH ROW
WHEN NEW.active_flag = 1
BEGIN
    UPDATE users
    SET warning_count = warning_count + 1
    WHERE user_id = NEW.user_id;
END;


-- ============================================================
-- TRIGGER 4: After a warning is deactivated (honor roll),
-- decrement the user's cached warning_count.
-- Fires when active_flag changes from 1 to 0.
-- ============================================================
CREATE TRIGGER IF NOT EXISTS trg_warning_deactivate
AFTER UPDATE ON warning_records
FOR EACH ROW
WHEN OLD.active_flag = 1 AND NEW.active_flag = 0
BEGIN
    UPDATE users
    SET warning_count = MAX(0, warning_count - 1)
    WHERE user_id = NEW.user_id;
END;



-- ============================================================
-- TRIGGER 5: Before a review is inserted, check that the
-- instructor has not already posted a grade for this student
-- in this section. Raises an error if a grade exists.
-- BEFORE INSERT triggers can abort the operation using
-- SELECT RAISE(ABORT, 'message').
-- ============================================================
CREATE TRIGGER IF NOT EXISTS trg_review_no_grade_yet
BEFORE INSERT ON reviews
FOR EACH ROW
BEGIN
    SELECT RAISE(ABORT, 'Cannot review after grade is posted.')
    WHERE EXISTS (
        SELECT 1
        FROM grade_records gr
        JOIN enrollments e ON gr.enrollment_id = e.enrollment_id
        WHERE e.student_id = NEW.student_id
          AND e.section_id = NEW.section_id
    );
END;