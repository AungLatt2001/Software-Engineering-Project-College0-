-- ============================================================
-- College0 — Seed Data
-- File: seed_data.sql
-- Run with: python3 seed_db.py
-- ============================================================

PRAGMA foreign_keys = ON;

-- ============================================================
-- BLOCK 1: USERS
-- We insert all users first because every other role table
-- (students, instructors, registrars) references users(user_id).
-- Password hashes here are fake placeholders.
-- In your real app, use bcrypt to hash before inserting.
-- Plain text meaning:
--   registrar  → "Admin@123"
--   instructors → "Teach@123"
--   students   → "Study@123"
-- ============================================================

INSERT INTO users
    (user_id, first_name, last_name, email,
     password_hash, role, status, warning_count, must_change_pwd)
VALUES
    -- Registrar
    (1, 'Diana',   'Morgan',  'diana.morgan@college0.edu',
     '$2b$12$registrar_hash_placeholder',   'registrar',  'active', 0, 0),

    -- Instructors (user_id 2-6)
    (2, 'Alan',    'Turing',  'a.turing@college0.edu',
     '$2b$12$instructor_hash_placeholder',  'instructor', 'active', 0, 0),
    (3, 'Grace',   'Hopper',  'g.hopper@college0.edu',
     '$2b$12$instructor_hash_placeholder',  'instructor', 'active', 0, 0),
    (4, 'Donald',  'Knuth',   'd.knuth@college0.edu',
     '$2b$12$instructor_hash_placeholder',  'instructor', 'active', 1, 0),
    (5, 'Barbara', 'Liskov',  'b.liskov@college0.edu',
     '$2b$12$instructor_hash_placeholder',  'instructor', 'active', 0, 0),
    (6, 'Linus',   'Torvalds','l.torvalds@college0.edu',
     '$2b$12$instructor_hash_placeholder',  'instructor', 'active', 0, 0),

    -- Students (user_id 7-16)
    -- Varied statuses, GPAs, and warning counts to test all rules
    (7,  'Alice',   'Chen',   'a.chen@college0.edu',
     '$2b$12$student_hash_placeholder', 'student', 'active',     0, 0),
    (8,  'Bob',     'Kim',    'b.kim@college0.edu',
     '$2b$12$student_hash_placeholder', 'student', 'active',     1, 0),
    (9,  'Carol',   'Diaz',   'c.diaz@college0.edu',
     '$2b$12$student_hash_placeholder', 'student', 'active',     2, 0),
    (10, 'David',   'Park',   'd.park@college0.edu',
     '$2b$12$student_hash_placeholder', 'student', 'active',     0, 0),
    (11, 'Emma',    'Russo',  'e.russo@college0.edu',
     '$2b$12$student_hash_placeholder', 'student', 'active',     0, 0),
    (12, 'Frank',   'Lee',    'f.lee@college0.edu',
     '$2b$12$student_hash_placeholder', 'student', 'suspended',  3, 0),
    (13, 'Grace',   'Wang',   'g.wang@college0.edu',
     '$2b$12$student_hash_placeholder', 'student', 'active',     0, 0),
    (14, 'Henry',   'Okafor', 'h.okafor@college0.edu',
     '$2b$12$student_hash_placeholder', 'student', 'active',     0, 1),
    (15, 'Iris',    'Patel',  'i.patel@college0.edu',
     '$2b$12$student_hash_placeholder', 'student', 'active',     1, 0),
    (16, 'James',   'Torres', 'j.torres@college0.edu',
     '$2b$12$student_hash_placeholder', 'student', 'terminated', 0, 0);


-- ============================================================
-- BLOCK 2: ROLE EXTENSION TABLES
-- One row per user in their role-specific table.
-- student_code follows format: STU-YYYY-NNNN
-- ============================================================

-- Registrar
INSERT INTO registrars (registrar_id, admin_level)
VALUES (1, 1);

-- Instructors
INSERT INTO instructors
    (instructor_id, specialization, rating_average, suspended_next_sem)
VALUES
    (2, 'Theory of Computation',    4.2, 0),
    (3, 'Programming Languages',    4.5, 0),
    (4, 'Algorithms',               3.1, 0),  -- has 1 warning, rating borderline
    (5, 'Software Engineering',     4.8, 0),
    (6, 'Operating Systems',        4.0, 0);

-- Students
-- Note: Alice (7) is a high achiever (GPA 3.9, honor_count 1)
--       Bob (8) is average (GPA 3.1)
--       Carol (9) is on probation (GPA 2.1, 2 warnings)
--       David (10) is new (GPA 0.0, first semester)
--       Emma (11) is solid (GPA 3.5)
--       Frank (12) is suspended (3 warnings, fine due)
--       Grace (13) qualifies for graduation (GPA 3.2)
--       Henry (14) is new, must change password
--       Iris (15) is average (GPA 2.8)
--       James (16) is terminated (GPA was below 2.0)
INSERT INTO students
    (student_id, student_code, cumulative_gpa, semester_gpa,
     honor_count, fine_amount_due, first_login_done)
VALUES
    (7,  'STU-2026-0001', 3.90, 4.00, 1, 0.00, 1),
    (8,  'STU-2026-0002', 3.10, 3.00, 0, 0.00, 1),
    (9,  'STU-2026-0003', 2.10, 2.00, 0, 0.00, 1),
    (10, 'STU-2026-0004', 0.00, 0.00, 0, 0.00, 1),
    (11, 'STU-2026-0005', 3.50, 3.50, 1, 0.00, 1),
    (12, 'STU-2026-0006', 2.50, 2.50, 0, 150.00, 1),  -- owes fine
    (13, 'STU-2026-0007', 3.20, 3.20, 0, 0.00, 1),
    (14, 'STU-2026-0008', 0.00, 0.00, 0, 0.00, 0),    -- never logged in
    (15, 'STU-2026-0009', 2.80, 2.80, 0, 0.00, 1),
    (16, 'STU-2026-0010', 1.80, 1.80, 0, 0.00, 1);    -- terminated


-- ============================================================
-- BLOCK 3: SEMESTER
-- One semester in 'registration' phase so we can test
-- enrollment logic. student_quota set to 10 (our demo size).
-- ============================================================

INSERT INTO semesters
    (semester_id, term_name, year, phase, student_quota,
     start_date, end_date)
VALUES
    (1, 'Spring 2026', 2026, 'registration', 10,
     '2026-01-20', '2026-05-20');


-- ============================================================
-- BLOCK 4: COURSES
-- 8 courses total: 4 core (is_core=1), 4 elective (is_core=0)
-- Course codes follow real CCNY Computer Science style.
-- Graduation requires completing all 4 core courses.
-- ============================================================

INSERT INTO courses
    (course_id, course_code, title, credit_hours, is_core, description)
VALUES
    -- Core courses (required for graduation)
    (1, 'CSC 10300', 'Introduction to Computing',
     3, 1, 'Fundamentals of programming and computational thinking.'),
    (2, 'CSC 21700', 'Discrete Structures',
     3, 1, 'Logic, sets, relations, graphs, and proof techniques.'),
    (3, 'CSC 21200', 'Data Structures',
     3, 1, 'Arrays, linked lists, trees, heaps, and hash tables.'),
    (4, 'CSC 30100', 'Theory of Computation',
     3, 1, 'Automata, formal languages, and computability.'),

    -- Elective courses
    (5, 'CSC 22000', 'Computer Architecture',
     3, 0, 'Instruction sets, memory hierarchy, and pipelining.'),
    (6, 'CSC 33500', 'Algorithm Design',
     3, 0, 'Sorting, dynamic programming, graph algorithms.'),
    (7, 'CSC 44800', 'Operating Systems',
     3, 0, 'Processes, threads, memory management, file systems.'),
    (8, 'CSC 34300', 'Software Engineering',
     3, 0, 'SDLC, design patterns, testing, and agile methods.');


-- ============================================================
-- BLOCK 5: CLASS SECTIONS
-- 6 sections for Spring 2026.
-- Section 3 is set to 'full' to test the waitlist feature.
-- current_enrollment is pre-filled to match the enrollments
-- we insert in Block 7.
-- ============================================================

INSERT INTO class_sections
    (section_id, semester_id, course_id, instructor_id,
     room, capacity, current_enrollment, status)
VALUES
    -- SEC-001: CSC 10300 intro, taught by Alan Turing, MWF morning
    (1, 1, 1, 2, 'NAC 7/107', 5, 4, 'open'),

    -- SEC-002: CSC 21200 data structures, Grace Hopper, TR afternoon
    (2, 1, 3, 3, 'NAC 6/116', 5, 3, 'open'),

    -- SEC-003: CSC 21700 discrete, Donald Knuth, MWF midday — FULL
    (3, 1, 2, 4, 'NAC 5/110', 3, 3, 'full'),

    -- SEC-004: CSC 30100 theory, Barbara Liskov, TR morning
    (4, 1, 4, 5, 'Shep 180',  5, 2, 'open'),

    -- SEC-005: CSC 33500 algorithms, Linus Torvalds, MW evening
    (5, 1, 6, 6, 'NAC 7/118', 5, 2, 'open'),

    -- SEC-006: CSC 44800 OS, Linus Torvalds, TR evening
    (6, 1, 7, 6, 'NAC 8/101', 5, 1, 'open');


-- ============================================================
-- BLOCK 6: SECTION TIMESLOTS
-- One row per day per section.
-- SEC-001 meets MWF → 3 rows
-- SEC-002 meets TR  → 2 rows
-- etc.
-- Times stored as "HH:MM" (24-hour, zero-padded) so that
-- string comparison works correctly for overlap detection.
-- ============================================================

INSERT INTO section_timeslots
    (section_id, day_of_week, time_start, time_end)
VALUES
    -- SEC-001: MWF 09:00-09:50
    (1, 'Monday',    '09:00', '09:50'),
    (1, 'Wednesday', '09:00', '09:50'),
    (1, 'Friday',    '09:00', '09:50'),

    -- SEC-002: TR 14:00-15:15
    (2, 'Tuesday',   '14:00', '15:15'),
    (2, 'Thursday',  '14:00', '15:15'),

    -- SEC-003: MWF 11:00-11:50
    (3, 'Monday',    '11:00', '11:50'),
    (3, 'Wednesday', '11:00', '11:50'),
    (3, 'Friday',    '11:00', '11:50'),

    -- SEC-004: TR 09:30-10:45
    (4, 'Tuesday',   '09:30', '10:45'),
    (4, 'Thursday',  '09:30', '10:45'),

    -- SEC-005: MW 18:00-19:15
    (5, 'Monday',    '18:00', '19:15'),
    (5, 'Wednesday', '18:00', '19:15'),

    -- SEC-006: TR 18:00-19:15
    (6, 'Tuesday',   '18:00', '19:15'),
    (6, 'Thursday',  '18:00', '19:15');


-- ============================================================
-- BLOCK 7: ENROLLMENTS
-- Each active student enrolled in 2-4 sections.
-- James (16) is terminated — no enrollments.
-- Frank (12) is suspended — no enrollments.
-- Henry (14) has not logged in yet — no enrollments.
-- ============================================================

INSERT INTO enrollments
    (enrollment_id, student_id, section_id, status)
VALUES
    -- Alice (7): enrolled in SEC-001, SEC-002, SEC-004 (3 courses)
    (1,  7, 1, 'enrolled'),
    (2,  7, 2, 'enrolled'),
    (3,  7, 4, 'enrolled'),

    -- Bob (8): enrolled in SEC-001, SEC-003, SEC-005 (3 courses)
    (4,  8, 1, 'enrolled'),
    (5,  8, 3, 'enrolled'),
    (6,  8, 5, 'enrolled'),

    -- Carol (9): enrolled in SEC-002, SEC-004 (2 courses — minimum)
    (7,  9, 2, 'enrolled'),
    (8,  9, 4, 'enrolled'),

    -- David (10): enrolled in SEC-001, SEC-006 (2 courses — new student)
    (9,  10, 1, 'enrolled'),
    (10, 10, 6, 'enrolled'),

    -- Emma (11): enrolled in SEC-002, SEC-005 (2 courses)
    (11, 11, 2, 'enrolled'),
    (12, 11, 5, 'enrolled'),

    -- Grace (13): enrolled in SEC-003, SEC-006 (2 courses)
    (13, 13, 3, 'enrolled'),
    (14, 13, 6, 'enrolled'),

    -- Iris (15): enrolled in SEC-003, SEC-004 (2 courses)
    (15, 15, 3, 'enrolled'),
    (16, 15, 4, 'enrolled');


-- ============================================================
-- BLOCK 8: WAITLIST ENTRIES
-- SEC-003 is full (capacity 3, enrollment 3).
-- Alice tried to add it but was waitlisted.
-- ============================================================

INSERT INTO waitlist_entries
    (student_id, section_id, position, status)
VALUES
    (7, 3, 1, 'waiting');  -- Alice is #1 on the SEC-003 waitlist


-- ============================================================
-- BLOCK 9: GRADE RECORDS
-- We add some grades from a previous semester to give
-- students their GPA history.
-- These are linked to completed enrollments from a prior term.
-- For simplicity we add them directly to current enrollments
-- that we mark as 'completed' below.
-- ============================================================

-- First update some enrollments to 'completed' to simulate
-- previously graded work
UPDATE enrollments SET status = 'completed' WHERE enrollment_id IN (1, 4, 7);

-- Now insert grade records for those completed enrollments
INSERT INTO grade_records
    (enrollment_id, letter_grade, grade_points)
VALUES
    (1, 'A',  4.0),   -- Alice in SEC-001: A
    (4, 'B',  3.0),   -- Bob   in SEC-001: B
    (7, 'C',  2.0);   -- Carol in SEC-002: C


-- ============================================================
-- BLOCK 10: TABOO WORDS
-- Registrar (ID 1) defined these prohibited words.
-- The review moderation system checks against this list.
-- ============================================================

INSERT INTO taboo_words (word, added_by)
VALUES
    ('terrible',  1),
    ('awful',     1),
    ('horrible',  1),
    ('useless',   1),
    ('stupid',    1);




-- ============================================================
-- BLOCK 12: WARNING RECORDS
-- Four warnings across three users to demonstrate the system.
-- source_module tells which subsystem issued each warning.
-- ============================================================

INSERT INTO warning_records
    (user_id, reason, source_module, active_flag)
VALUES
    -- Bob (8): warning for using a taboo word in review
    (8,  'Review contained 1 taboo word in SEC-001 review.',
     'review', 1),

    -- Carol (9): 2 warnings for blocked review (3+ taboo words)
    (9,  'Review blocked: 3 or more taboo words detected.',
     'review', 1),
    (9,  'Second warning issued for severe taboo word violation.',
     'review', 1),

    -- Frank (12): academic warning for low GPA (already suspended)
    (12, 'Cumulative GPA below 2.0 threshold after grading period.',
     'academic', 1),

    -- Iris (15): academic probation warning (GPA between 2.0 and 2.25)
    (15, 'Semester GPA between 2.0 and 2.25. Must interview with registrar.',
     'academic', 1);


-- ============================================================
-- BLOCK 13: COMPLAINTS
-- Two complaints to test the complaint workflow.
-- ============================================================

INSERT INTO complaints
    (filed_by_user_id, target_user_id, complaint_text,
     status, resolution_note, penalty_applied,
     resolved_by, resolved_at)
VALUES
    -- Carol (9) complains about instructor Donald Knuth (4)
    -- Complaint is resolved with a warning issued to instructor
    (9, 4,
     'Professor Knuth returned graded work three weeks late with no explanation.',
     'resolved',
     'Instructor was counseled about timely feedback requirements.',
     'warning issued',
     1, datetime('now', '-5 days')),

    -- Bob (8) complains about Alice (7) — pending investigation
    (8, 7,
     'Alice shared answers during the midterm exam.',
     'investigating',
     NULL, NULL, NULL, NULL);


-- ============================================================
-- BLOCK 14: GRADUATION APPLICATION
-- Grace (13) has completed enough courses and applies.
-- In a real run the system would verify:
--   completed courses >= 8, including 4 core, GPA > 2.0
-- For seed data we insert a pending application to demo the flow.
-- ============================================================

INSERT INTO graduation_applications
    (student_id, decision_status, warning_issued, reviewed_by)
VALUES
    (13, 'pending', 0, NULL);


-- ============================================================
-- BLOCK 15: VISITOR APPLICATIONS
-- Three applications in different states to demo admission flow.
-- ============================================================

INSERT INTO visitor_applications
    (applicant_name, email, application_type, prior_gpa,
     personal_statement, status, reviewed_by, reviewed_at)
VALUES
    -- Pending student application — waiting for registrar review
    ('Maya Singh', 'maya.singh@gmail.com', 'student', 3.6,
     'I am passionate about computer science and eager to join.',
     'pending', NULL, NULL),

    -- Accepted student application — registrar approved
    ('Henry Okafor', 'h.okafor@college0.edu', 'student', 3.8,
     'Strong background in mathematics, excited to start.',
     'accepted', 1, datetime('now', '-10 days')),

    -- Rejected student application — GPA too low, no override
    ('Jake Brown', 'jake.brown@gmail.com', 'student', 2.4,
     'I believe I can succeed despite my GPA.',
     'rejected', 1, datetime('now', '-7 days'));


-- ============================================================
-- BLOCK 16: AI QUERY LOGS
-- Three logged queries to demo all three answer sources.
-- ============================================================

INSERT INTO ai_queries
    (user_id, question_text, answer_text, answer_source, warning_displayed)
VALUES
    -- Alice asks a question answered by local VectorDB
    (7,
     'When does the registration period end?',
     'The registration period for Spring 2026 ends on February 15, 2026.',
     'vector_db', 0),

    -- Bob asks something the VectorDB could not answer — LLM fallback
    (8,
     'What is the best way to study for a theory of computation exam?',
     'Focus on understanding automata proofs and practice reduction problems.',
     'llm', 1),

    -- Visitor asks a general question (user_id NULL = unauthenticated)
    (NULL,
     'How do I apply to the college program?',
     'You can apply by clicking Apply on the home screen and filling out the form.',
     'vector_db', 0);