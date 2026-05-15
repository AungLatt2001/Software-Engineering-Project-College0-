-- ============================================================
-- College0 — Database Triggers
-- File: triggers.sql
-- Run with: python3 apply_triggers.py
-- Must be applied AFTER initialize_db.py has run.
-- ============================================================

PRAGMA foreign_keys = ON;


-- ============================================================
-- TRIGGER 1
-- When a new enrollment is inserted with status = 'enrolled',
-- increment the section's current_enrollment count.
-- Also updates the section status to 'full' if now at capacity.
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
-- TRIGGER 2
-- When an enrollment changes from 'enrolled' to 'dropped'
-- or 'cancelled', decrement the section count.
-- MAX(0, ...) prevents the count going below zero.
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
            ELSE status
        END
    WHERE section_id = NEW.section_id;
END;


-- ============================================================
-- TRIGGER 3
-- When a new active warning is inserted, increment the
-- user's cached warning_count on the users table.
-- This keeps the cache in sync automatically.
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
-- TRIGGER 4
-- When a warning is deactivated (active_flag 1 → 0),
-- decrement the cached warning_count.
-- This fires when honor roll removes a warning.
-- MAX(0, ...) prevents the count going below zero.
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
-- TRIGGER 5
-- Before inserting a review, check that the instructor
-- has not already posted a grade for this student in this
-- section. Aborts the insert if a grade record exists.
-- RAISE(ABORT, msg) rolls back the insert and throws an error
-- that the application catches and shows to the user.
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