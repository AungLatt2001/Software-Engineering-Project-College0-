-- =============================================================
--  College0 System — Complete MySQL Database Schema
--  Based on E-R Design (Section 3)
-- =============================================================

CREATE DATABASE IF NOT EXISTS college0;
USE college0;

-- =============================================================
-- 1. USER (Parent / Generalization Root)
-- =============================================================
CREATE TABLE User (
    user_id         INT             NOT NULL AUTO_INCREMENT,
    first_name      VARCHAR(100)    NOT NULL,
    last_name       VARCHAR(100)    NOT NULL,
    email           VARCHAR(255)    NOT NULL,
    password_hash   VARCHAR(255)    NOT NULL,
    role            ENUM('student', 'instructor', 'registrar') NOT NULL,
    status          ENUM('active', 'suspended', 'terminated', 'graduated') NOT NULL DEFAULT 'active',
    warning_count   INT             NOT NULL DEFAULT 0,
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT pk_user          PRIMARY KEY (user_id),
    CONSTRAINT uq_user_email    UNIQUE      (email)
);

-- =============================================================
-- 2. STUDENT  (Specialization of User)
-- =============================================================
CREATE TABLE Student (
    student_id              INT             NOT NULL,
    cumulative_gpa          DECIMAL(4,3)    NOT NULL DEFAULT 0.000,
    semester_gpa            DECIMAL(4,3)    NOT NULL DEFAULT 0.000,
    honor_count             INT             NOT NULL DEFAULT 0,
    suspension_end_semester INT             NULL,          -- FK added after Semester table
    fine_due                DECIMAL(10,2)   NOT NULL DEFAULT 0.00,
    first_login_required    TINYINT(1)      NOT NULL DEFAULT 1,

    CONSTRAINT pk_student   PRIMARY KEY (student_id),
    CONSTRAINT fk_student_user
        FOREIGN KEY (student_id) REFERENCES User(user_id)
        ON DELETE CASCADE ON UPDATE CASCADE
);

-- =============================================================
-- 3. INSTRUCTOR  (Specialization of User)
-- =============================================================
CREATE TABLE Instructor (
    instructor_id           INT             NOT NULL,
    specialization          VARCHAR(200)    NULL,
    suspension_next_semester TINYINT(1)     NOT NULL DEFAULT 0,
    rating_average          DECIMAL(3,2)    NOT NULL DEFAULT 0.00,

    CONSTRAINT pk_instructor    PRIMARY KEY (instructor_id),
    CONSTRAINT fk_instructor_user
        FOREIGN KEY (instructor_id) REFERENCES User(user_id)
        ON DELETE CASCADE ON UPDATE CASCADE
);

-- =============================================================
-- 4. REGISTRAR  (Specialization of User)
-- =============================================================
CREATE TABLE Registrar (
    registrar_id    INT             NOT NULL,
    admin_level     INT             NOT NULL DEFAULT 1,

    CONSTRAINT pk_registrar     PRIMARY KEY (registrar_id),
    CONSTRAINT fk_registrar_user
        FOREIGN KEY (registrar_id) REFERENCES User(user_id)
        ON DELETE CASCADE ON UPDATE CASCADE
);

-- =============================================================
-- 5. VISITOR APPLICATION
-- =============================================================
CREATE TABLE VisitorApplication (
    application_id      INT             NOT NULL AUTO_INCREMENT,
    applicant_name      VARCHAR(200)    NOT NULL,
    email               VARCHAR(255)    NOT NULL,
    application_type    ENUM('student', 'instructor') NOT NULL,
    prior_gpa           DECIMAL(4,3)    NULL,
    justification       TEXT            NULL,
    status              ENUM('pending', 'approved', 'rejected') NOT NULL DEFAULT 'pending',
    reviewed_by         INT             NULL,
    reviewed_at         DATETIME        NULL,

    CONSTRAINT pk_visitor_app   PRIMARY KEY (application_id),
    CONSTRAINT fk_visitor_app_registrar
        FOREIGN KEY (reviewed_by) REFERENCES Registrar(registrar_id)
        ON DELETE SET NULL ON UPDATE CASCADE
);

-- =============================================================
-- 6. SEMESTER
-- =============================================================
CREATE TABLE Semester (
    semester_id     INT             NOT NULL AUTO_INCREMENT,
    term_name       VARCHAR(50)     NOT NULL,   -- e.g. 'Fall', 'Spring', 'Summer'
    year            YEAR            NOT NULL,
    phase           ENUM('setup', 'registration', 'running', 'grading', 'closed') NOT NULL DEFAULT 'setup',
    start_date      DATE            NOT NULL,
    end_date        DATE            NOT NULL,

    CONSTRAINT pk_semester      PRIMARY KEY (semester_id)
);

-- Add deferred FK: Student.suspension_end_semester → Semester.semester_id
ALTER TABLE Student
    ADD CONSTRAINT fk_student_suspension_semester
        FOREIGN KEY (suspension_end_semester) REFERENCES Semester(semester_id)
        ON DELETE SET NULL ON UPDATE CASCADE;

-- =============================================================
-- 7. COURSE
-- =============================================================
CREATE TABLE Course (
    course_id       INT             NOT NULL AUTO_INCREMENT,
    code            VARCHAR(20)     NOT NULL,
    title           VARCHAR(200)    NOT NULL,
    credit_hours    INT             NOT NULL DEFAULT 3,
    is_core         TINYINT(1)      NOT NULL DEFAULT 0,
    description     TEXT            NULL,

    CONSTRAINT pk_course        PRIMARY KEY (course_id),
    CONSTRAINT uq_course_code   UNIQUE      (code)
);

-- =============================================================
-- 8. CLASS SECTION
-- =============================================================
CREATE TABLE ClassSection (
    section_id      INT             NOT NULL AUTO_INCREMENT,
    semester_id     INT             NOT NULL,
    course_id       INT             NOT NULL,
    instructor_id   INT             NOT NULL,
    room            VARCHAR(50)     NULL,
    schedule_slot   VARCHAR(100)    NULL,   -- e.g. 'MWF 09:00-10:00'
    capacity        INT             NOT NULL DEFAULT 30,
    status          ENUM('open', 'full', 'cancelled', 'completed') NOT NULL DEFAULT 'open',

    CONSTRAINT pk_class_section     PRIMARY KEY (section_id),
    CONSTRAINT fk_cs_semester
        FOREIGN KEY (semester_id) REFERENCES Semester(semester_id)
        ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT fk_cs_course
        FOREIGN KEY (course_id) REFERENCES Course(course_id)
        ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT fk_cs_instructor
        FOREIGN KEY (instructor_id) REFERENCES Instructor(instructor_id)
        ON DELETE RESTRICT ON UPDATE CASCADE
);

-- =============================================================
-- 9. ENROLLMENT  (Student M:N ClassSection)
-- =============================================================
CREATE TABLE Enrollment (
    enrollment_id       INT             NOT NULL AUTO_INCREMENT,
    student_id          INT             NOT NULL,
    section_id          INT             NOT NULL,
    enrollment_status   ENUM('enrolled', 'dropped', 'completed', 'failed') NOT NULL DEFAULT 'enrolled',
    enrolled_at         DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT pk_enrollment    PRIMARY KEY (enrollment_id),
    CONSTRAINT uq_enrollment    UNIQUE (student_id, section_id),
    CONSTRAINT fk_enroll_student
        FOREIGN KEY (student_id) REFERENCES Student(student_id)
        ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT fk_enroll_section
        FOREIGN KEY (section_id) REFERENCES ClassSection(section_id)
        ON DELETE RESTRICT ON UPDATE CASCADE
);

-- =============================================================
-- 10. WAITLIST ENTRY  (Student M:N ClassSection — waitlist)
-- =============================================================
CREATE TABLE WaitlistEntry (
    waitlist_id     INT             NOT NULL AUTO_INCREMENT,
    student_id      INT             NOT NULL,
    section_id      INT             NOT NULL,
    position        INT             NOT NULL,
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT pk_waitlist      PRIMARY KEY (waitlist_id),
    CONSTRAINT uq_waitlist      UNIQUE (student_id, section_id),
    CONSTRAINT fk_wl_student
        FOREIGN KEY (student_id) REFERENCES Student(student_id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_wl_section
        FOREIGN KEY (section_id) REFERENCES ClassSection(section_id)
        ON DELETE CASCADE ON UPDATE CASCADE
);

-- =============================================================
-- 11. GRADE RECORD  (Enrollment 1:0..1)
-- =============================================================
CREATE TABLE GradeRecord (
    grade_id        INT             NOT NULL AUTO_INCREMENT,
    enrollment_id   INT             NOT NULL,
    letter_grade    CHAR(2)         NOT NULL,   -- e.g. 'A', 'B+', 'C-', 'F'
    grade_points    DECIMAL(3,2)    NOT NULL,   -- e.g. 4.00, 3.33, 1.00
    posted_at       DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT pk_grade_record  PRIMARY KEY (grade_id),
    CONSTRAINT uq_grade_enrollment UNIQUE (enrollment_id),
    CONSTRAINT fk_grade_enrollment
        FOREIGN KEY (enrollment_id) REFERENCES Enrollment(enrollment_id)
        ON DELETE RESTRICT ON UPDATE CASCADE
);

-- =============================================================
-- 12. REVIEW  (Student M:N ClassSection)
-- =============================================================
CREATE TABLE Review (
    review_id           INT             NOT NULL AUTO_INCREMENT,
    section_id          INT             NOT NULL,
    student_id          INT             NOT NULL,
    rating              TINYINT         NOT NULL CHECK (rating BETWEEN 1 AND 5),
    review_text         TEXT            NULL,
    taboo_count         INT             NOT NULL DEFAULT 0,
    visibility_status   ENUM('visible', 'hidden', 'flagged') NOT NULL DEFAULT 'visible',
    created_at          DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT pk_review        PRIMARY KEY (review_id),
    CONSTRAINT uq_review        UNIQUE (section_id, student_id),
    CONSTRAINT fk_review_section
        FOREIGN KEY (section_id) REFERENCES ClassSection(section_id)
        ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT fk_review_student
        FOREIGN KEY (student_id) REFERENCES Student(student_id)
        ON DELETE RESTRICT ON UPDATE CASCADE
);

-- =============================================================
-- 13. COMPLAINT
-- =============================================================
CREATE TABLE Complaint (
    complaint_id        INT             NOT NULL AUTO_INCREMENT,
    filed_by_user_id    INT             NOT NULL,
    target_user_id      INT             NOT NULL,
    complaint_text      TEXT            NOT NULL,
    status              ENUM('open', 'under_review', 'resolved', 'dismissed') NOT NULL DEFAULT 'open',
    resolution_note     TEXT            NULL,
    resolved_by         INT             NULL,

    CONSTRAINT pk_complaint     PRIMARY KEY (complaint_id),
    CONSTRAINT fk_complaint_filer
        FOREIGN KEY (filed_by_user_id) REFERENCES User(user_id)
        ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT fk_complaint_target
        FOREIGN KEY (target_user_id) REFERENCES User(user_id)
        ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT fk_complaint_registrar
        FOREIGN KEY (resolved_by) REFERENCES Registrar(registrar_id)
        ON DELETE SET NULL ON UPDATE CASCADE
);

-- =============================================================
-- 14. WARNING RECORD
-- =============================================================
CREATE TABLE WarningRecord (
    warning_id      INT             NOT NULL AUTO_INCREMENT,
    user_id         INT             NOT NULL,
    reason          TEXT            NOT NULL,
    source_module   VARCHAR(100)    NOT NULL,   -- e.g. 'grade_engine', 'review_moderation'
    issued_at       DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    active_flag     TINYINT(1)      NOT NULL DEFAULT 1,

    CONSTRAINT pk_warning       PRIMARY KEY (warning_id),
    CONSTRAINT fk_warning_user
        FOREIGN KEY (user_id) REFERENCES User(user_id)
        ON DELETE CASCADE ON UPDATE CASCADE
);

-- =============================================================
-- 15. GRADUATION APPLICATION
-- =============================================================
CREATE TABLE GraduationApplication (
    graduation_app_id   INT             NOT NULL AUTO_INCREMENT,
    student_id          INT             NOT NULL,
    submitted_at        DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    decision_status     ENUM('pending', 'approved', 'rejected') NOT NULL DEFAULT 'pending',
    reviewed_by         INT             NULL,
    reviewed_at         DATETIME        NULL,

    CONSTRAINT pk_graduation_app    PRIMARY KEY (graduation_app_id),
    CONSTRAINT fk_grad_student
        FOREIGN KEY (student_id) REFERENCES Student(student_id)
        ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT fk_grad_registrar
        FOREIGN KEY (reviewed_by) REFERENCES Registrar(registrar_id)
        ON DELETE SET NULL ON UPDATE CASCADE
);

-- =============================================================
-- 16. AI QUERY
-- =============================================================
CREATE TABLE AIQuery (
    query_id            INT             NOT NULL AUTO_INCREMENT,
    user_id             INT             NULL,   -- NULL for anonymous visitor queries
    question_text       TEXT            NOT NULL,
    answer_text         TEXT            NOT NULL,
    answer_source       ENUM('vectordb', 'llm_fallback') NOT NULL,
    warning_displayed   TINYINT(1)      NOT NULL DEFAULT 0,
    created_at          DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT pk_ai_query      PRIMARY KEY (query_id),
    CONSTRAINT fk_ai_query_user
        FOREIGN KEY (user_id) REFERENCES User(user_id)
        ON DELETE SET NULL ON UPDATE CASCADE
);

-- =============================================================
-- INDEXES  (performance helpers beyond the FK indexes)
-- =============================================================

-- Fast lookup of all sections in a semester
CREATE INDEX idx_cs_semester        ON ClassSection (semester_id);
-- Fast lookup of all sections taught by an instructor
CREATE INDEX idx_cs_instructor      ON ClassSection (instructor_id);
-- Fast lookup of all enrollments for a student
CREATE INDEX idx_enroll_student     ON Enrollment   (student_id);
-- Fast lookup of enrollments by section (seat-count queries)
CREATE INDEX idx_enroll_section     ON Enrollment   (section_id);
-- Fast lookup of waitlist by section + position
CREATE INDEX idx_wl_section_pos     ON WaitlistEntry (section_id, position);
-- Active warnings per user
CREATE INDEX idx_warning_user_active ON WarningRecord (user_id, active_flag);
-- Reviews by section
CREATE INDEX idx_review_section     ON Review       (section_id);
-- Applications by status (pending queue)
CREATE INDEX idx_va_status          ON VisitorApplication (status);
-- Complaints by status
CREATE INDEX idx_complaint_status   ON Complaint    (status);
-- AI queries by user
CREATE INDEX idx_aiq_user           ON AIQuery      (user_id);

-- =============================================================
-- END OF SCHEMA
-- =============================================================
