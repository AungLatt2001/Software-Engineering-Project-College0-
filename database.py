import sqlite3
from werkzeug.security import generate_password_hash

DB_PATH = "collegeo.db"

SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS User (
    user_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    first_name    TEXT    NOT NULL,
    last_name     TEXT    NOT NULL,
    email         TEXT    NOT NULL UNIQUE,
    password_hash TEXT    NOT NULL,
    role          TEXT    NOT NULL CHECK(role IN ('student','instructor','registrar')),
    status        TEXT    NOT NULL DEFAULT 'active',
    warning_count INTEGER NOT NULL DEFAULT 0,
    created_at    TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS Registrar (
    registrar_id INTEGER PRIMARY KEY,
    admin_level  INTEGER NOT NULL DEFAULT 1,
    FOREIGN KEY (registrar_id) REFERENCES User(user_id) ON DELETE CASCADE ON UPDATE CASCADE
);

CREATE TABLE IF NOT EXISTS Instructor (
    instructor_id            INTEGER PRIMARY KEY,
    specialization           TEXT,
    suspension_next_semester INTEGER NOT NULL DEFAULT 0,
    rating_average           REAL    NOT NULL DEFAULT 0.00,
    FOREIGN KEY (instructor_id) REFERENCES User(user_id) ON DELETE CASCADE ON UPDATE CASCADE
);

CREATE TABLE IF NOT EXISTS Semester (
    semester_id INTEGER PRIMARY KEY AUTOINCREMENT,
    term_name   TEXT    NOT NULL,
    year        INTEGER NOT NULL,
    phase       TEXT    NOT NULL DEFAULT 'setup',
    start_date  TEXT    NOT NULL,
    end_date    TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS Student (
    student_id              INTEGER PRIMARY KEY,
    cumulative_gpa          REAL    NOT NULL DEFAULT 0.000,
    semester_gpa            REAL    NOT NULL DEFAULT 0.000,
    honor_count             INTEGER NOT NULL DEFAULT 0,
    suspension_end_semester INTEGER,
    fine_due                REAL    NOT NULL DEFAULT 0.00,
    first_login_required    INTEGER NOT NULL DEFAULT 1,
    FOREIGN KEY (student_id) REFERENCES User(user_id) ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY (suspension_end_semester) REFERENCES Semester(semester_id) ON DELETE SET NULL ON UPDATE CASCADE
);

CREATE TABLE IF NOT EXISTS VisitorApplication (
    application_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    applicant_name   TEXT NOT NULL,
    email            TEXT NOT NULL,
    application_type TEXT NOT NULL CHECK(application_type IN ('student','instructor')),
    prior_gpa        REAL,
    justification    TEXT,
    status           TEXT NOT NULL DEFAULT 'pending',
    reviewed_by      INTEGER,
    reviewed_at      TEXT,
    FOREIGN KEY (reviewed_by) REFERENCES Registrar(registrar_id) ON DELETE SET NULL ON UPDATE CASCADE
);

CREATE TABLE IF NOT EXISTS Course (
    course_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    code         TEXT    NOT NULL UNIQUE,
    title        TEXT    NOT NULL,
    credit_hours INTEGER NOT NULL DEFAULT 3,
    is_core      INTEGER NOT NULL DEFAULT 0,
    description  TEXT
);

CREATE TABLE IF NOT EXISTS ClassSection (
    section_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    semester_id   INTEGER NOT NULL,
    course_id     INTEGER NOT NULL,
    instructor_id INTEGER NOT NULL,
    room          TEXT,
    schedule_slot TEXT,
    capacity      INTEGER NOT NULL DEFAULT 30,
    status        TEXT    NOT NULL DEFAULT 'open',
    FOREIGN KEY (semester_id)   REFERENCES Semester(semester_id)     ON DELETE RESTRICT ON UPDATE CASCADE,
    FOREIGN KEY (course_id)     REFERENCES Course(course_id)         ON DELETE RESTRICT ON UPDATE CASCADE,
    FOREIGN KEY (instructor_id) REFERENCES Instructor(instructor_id) ON DELETE RESTRICT ON UPDATE CASCADE
);

CREATE TABLE IF NOT EXISTS Enrollment (
    enrollment_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id        INTEGER NOT NULL,
    section_id        INTEGER NOT NULL,
    enrollment_status TEXT    NOT NULL DEFAULT 'enrolled',
    enrolled_at       TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (student_id, section_id),
    FOREIGN KEY (student_id) REFERENCES Student(student_id) ON DELETE RESTRICT ON UPDATE CASCADE,
    FOREIGN KEY (section_id) REFERENCES ClassSection(section_id) ON DELETE RESTRICT ON UPDATE CASCADE
);

CREATE TABLE IF NOT EXISTS WaitlistEntry (
    waitlist_id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id  INTEGER NOT NULL,
    section_id  INTEGER NOT NULL,
    position    INTEGER NOT NULL,
    created_at  TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (student_id, section_id),
    FOREIGN KEY (student_id) REFERENCES Student(student_id) ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY (section_id) REFERENCES ClassSection(section_id) ON DELETE CASCADE ON UPDATE CASCADE
);

CREATE TABLE IF NOT EXISTS GradeRecord (
    grade_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    enrollment_id INTEGER NOT NULL UNIQUE,
    letter_grade  TEXT    NOT NULL,
    grade_points  REAL    NOT NULL,
    posted_at     TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (enrollment_id) REFERENCES Enrollment(enrollment_id) ON DELETE RESTRICT ON UPDATE CASCADE
);

CREATE TABLE IF NOT EXISTS Review (
    review_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    section_id        INTEGER NOT NULL,
    student_id        INTEGER NOT NULL,
    rating            INTEGER NOT NULL CHECK(rating BETWEEN 1 AND 5),
    review_text       TEXT,
    taboo_count       INTEGER NOT NULL DEFAULT 0,
    visibility_status TEXT    NOT NULL DEFAULT 'visible',
    created_at        TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (section_id, student_id),
    FOREIGN KEY (section_id) REFERENCES ClassSection(section_id) ON DELETE RESTRICT ON UPDATE CASCADE,
    FOREIGN KEY (student_id) REFERENCES Student(student_id)      ON DELETE RESTRICT ON UPDATE CASCADE
);

CREATE TABLE IF NOT EXISTS Complaint (
    complaint_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    filed_by_user_id INTEGER NOT NULL,
    target_user_id   INTEGER NOT NULL,
    complaint_text   TEXT    NOT NULL,
    status           TEXT    NOT NULL DEFAULT 'open',
    resolution_note  TEXT,
    resolved_by      INTEGER,
    FOREIGN KEY (filed_by_user_id) REFERENCES User(user_id)        ON DELETE RESTRICT ON UPDATE CASCADE,
    FOREIGN KEY (target_user_id)   REFERENCES User(user_id)        ON DELETE RESTRICT ON UPDATE CASCADE,
    FOREIGN KEY (resolved_by)      REFERENCES Registrar(registrar_id) ON DELETE SET NULL ON UPDATE CASCADE
);

CREATE TABLE IF NOT EXISTS WarningRecord (
    warning_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id       INTEGER NOT NULL,
    reason        TEXT    NOT NULL,
    source_module TEXT    NOT NULL,
    issued_at     TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    active_flag   INTEGER NOT NULL DEFAULT 1,
    FOREIGN KEY (user_id) REFERENCES User(user_id) ON DELETE CASCADE ON UPDATE CASCADE
);

CREATE TABLE IF NOT EXISTS GraduationApplication (
    graduation_app_id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id        INTEGER NOT NULL,
    submitted_at      TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    decision_status   TEXT    NOT NULL DEFAULT 'pending',
    reviewed_by       INTEGER,
    reviewed_at       TEXT,
    FOREIGN KEY (student_id)  REFERENCES Student(student_id)         ON DELETE RESTRICT ON UPDATE CASCADE,
    FOREIGN KEY (reviewed_by) REFERENCES Registrar(registrar_id)     ON DELETE SET NULL ON UPDATE CASCADE
);

CREATE TABLE IF NOT EXISTS AIQuery (
    query_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id           INTEGER,
    question_text     TEXT NOT NULL,
    answer_text       TEXT NOT NULL,
    answer_source     TEXT NOT NULL DEFAULT 'vectordb',
    warning_displayed INTEGER NOT NULL DEFAULT 0,
    created_at        TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES User(user_id) ON DELETE SET NULL ON UPDATE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_cs_semester        ON ClassSection  (semester_id);
CREATE INDEX IF NOT EXISTS idx_cs_instructor      ON ClassSection  (instructor_id);
CREATE INDEX IF NOT EXISTS idx_enroll_student     ON Enrollment    (student_id);
CREATE INDEX IF NOT EXISTS idx_enroll_section     ON Enrollment    (section_id);
CREATE INDEX IF NOT EXISTS idx_wl_section_pos     ON WaitlistEntry (section_id, position);
CREATE INDEX IF NOT EXISTS idx_warning_user_active ON WarningRecord (user_id, active_flag);
CREATE INDEX IF NOT EXISTS idx_review_section     ON Review        (section_id);
CREATE INDEX IF NOT EXISTS idx_va_status          ON VisitorApplication (status);
CREATE INDEX IF NOT EXISTS idx_complaint_status   ON Complaint     (status);
CREATE INDEX IF NOT EXISTS idx_aiq_user           ON AIQuery       (user_id);
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

    if conn.execute("SELECT COUNT(*) as c FROM User").fetchone()["c"] > 0:
        conn.close()
        return

    pw = generate_password_hash("Password123!")

    users = [
        (1, 'Diana',  'Morgan',  'diana.morgan@college0.edu',   pw, 'registrar',  'active',    0, '2024-08-01 08:00:00'),
        (2, 'Carlos', 'Reyes',   'carlos.reyes@college0.edu',   pw, 'registrar',  'active',    0, '2024-08-01 08:00:00'),
        (3, 'Alan',   'Brooks',  'alan.brooks@college0.edu',    pw, 'instructor', 'active',    0, '2024-08-05 09:00:00'),
        (4, 'Sandra', 'Kim',     'sandra.kim@college0.edu',     pw, 'instructor', 'active',    0, '2024-08-05 09:00:00'),
        (5, 'Robert', 'Nguyen',  'robert.nguyen@college0.edu',  pw, 'instructor', 'active',    0, '2024-08-05 09:00:00'),
        (6, 'Fatima', 'Hassan',  'fatima.hassan@college0.edu',  pw, 'instructor', 'active',    1, '2024-08-05 09:00:00'),
        (7, 'Liam',   'Turner',  'liam.turner@college0.edu',    pw, 'student',    'active',    0, '2024-08-10 10:00:00'),
        (8, 'Aisha',  'Patel',   'aisha.patel@college0.edu',    pw, 'student',    'active',    0, '2024-08-10 10:00:00'),
        (9, 'Marcus', 'Johnson', 'marcus.johnson@college0.edu', pw, 'student',    'active',    1, '2024-08-10 10:00:00'),
        (10,'Sofia',  'Diaz',    'sofia.diaz@college0.edu',     pw, 'student',    'active',    0, '2024-08-10 10:00:00'),
        (11,'Ethan',  'Lee',     'ethan.lee@college0.edu',      pw, 'student',    'active',    2, '2024-08-10 10:00:00'),
        (12,'Priya',  'Sharma',  'priya.sharma@college0.edu',   pw, 'student',    'active',    0, '2024-08-10 10:00:00'),
        (13,'Noah',   'Wilson',  'noah.wilson@college0.edu',    pw, 'student',    'suspended', 1, '2024-08-10 10:00:00'),
        (14,'Chloe',  'Adams',   'chloe.adams@college0.edu',    pw, 'student',    'active',    0, '2024-08-10 10:00:00'),
        (15,'James',  'Clark',   'james.clark@college0.edu',    pw, 'student',    'active',    0, '2023-01-15 10:00:00'),
    ]
    conn.executemany(
        "INSERT INTO User (user_id,first_name,last_name,email,password_hash,role,status,warning_count,created_at) VALUES (?,?,?,?,?,?,?,?,?)",
        users
    )

    conn.executemany("INSERT INTO Registrar (registrar_id,admin_level) VALUES (?,?)", [(1,2),(2,1)])

    conn.executemany(
        "INSERT INTO Instructor (instructor_id,specialization,suspension_next_semester,rating_average) VALUES (?,?,?,?)",
        [(3,'Computer Science',0,4.75),(4,'Mathematics',0,4.50),(5,'Software Engineering',0,4.20),(6,'Data Science',0,3.80)]
    )

    conn.executemany(
        "INSERT INTO Semester (semester_id,term_name,year,phase,start_date,end_date) VALUES (?,?,?,?,?,?)",
        [
            (1,'Fall',  2024,'closed',      '2024-09-01','2024-12-20'),
            (2,'Spring',2025,'closed',      '2025-01-15','2025-05-10'),
            (3,'Summer',2025,'grading',     '2025-06-01','2025-07-31'),
            (4,'Fall',  2025,'registration','2025-09-01','2025-12-20'),
        ]
    )

    conn.executemany(
        "INSERT INTO Student (student_id,cumulative_gpa,semester_gpa,honor_count,suspension_end_semester,fine_due,first_login_required) VALUES (?,?,?,?,?,?,?)",
        [
            (7,  3.800,3.800,1,None,  0.00,0),
            (8,  3.950,4.000,2,None,  0.00,0),
            (9,  2.500,2.300,0,None, 50.00,0),
            (10, 3.600,3.700,1,None,  0.00,0),
            (11, 1.800,1.500,0,None,100.00,0),
            (12, 4.000,4.000,3,None,  0.00,0),
            (13, 2.000,1.800,0,2,    75.00,0),
            (14, 3.200,3.100,0,None,  0.00,1),
            (15, 3.900,3.850,2,None,  0.00,0),
        ]
    )

    conn.executemany(
        "INSERT INTO VisitorApplication (application_id,applicant_name,email,application_type,prior_gpa,justification,status,reviewed_by,reviewed_at) VALUES (?,?,?,?,?,?,?,?,?)",
        [
            (1,'Kevin Hart',  'kevin.hart@gmail.com',  'student',   3.20,'Interested in CS program.',        'approved',1,'2024-08-12 10:00:00'),
            (2,'Laura Chen',  'laura.chen@gmail.com',  'instructor',None,'PhD in AI, 5 years teaching.',     'approved',1,'2024-08-12 11:00:00'),
            (3,'Mark Davis',  'mark.davis@gmail.com',  'student',   2.10,'Seeking second chance after gap.', 'rejected',2,'2024-08-13 09:00:00'),
            (4,'Nina Petrova','nina.petrova@gmail.com','student',   3.80,'Transfer from State University.',  'pending', None,None),
            (5,'Omar Farouk', 'omar.farouk@gmail.com', 'instructor',None,'MSc in Mathematics, 3 years exp.','pending', None,None),
            (6,'Rachel Green','rachel.green@gmail.com','student',   2.90,'Recent high school graduate.',     'approved',1,'2024-08-14 14:00:00'),
        ]
    )

    conn.executemany(
        "INSERT INTO Course (course_id,code,title,credit_hours,is_core,description) VALUES (?,?,?,?,?,?)",
        [
            (1, 'CSC101','Introduction to Computer Science',3,1,'Fundamentals of computing and programming.'),
            (2, 'CSC201','Data Structures',                 3,1,'Arrays, linked lists, trees, graphs, and algorithms.'),
            (3, 'CSC301','Database Systems',                3,1,'Relational databases, SQL, and E-R modeling.'),
            (4, 'CSC401','Software Engineering',            3,1,'SDLC, design patterns, and agile methodologies.'),
            (5, 'CSC450','Machine Learning',                3,0,'Supervised and unsupervised learning techniques.'),
            (6, 'MTH101','Calculus I',                      4,1,'Limits, derivatives, and integration.'),
            (7, 'MTH201','Discrete Mathematics',            3,1,'Logic, sets, combinatorics, and graph theory.'),
            (8, 'MTH301','Linear Algebra',                  3,0,'Vectors, matrices, and linear transformations.'),
            (9, 'ENG101','English Composition',             3,1,'Academic writing and critical thinking.'),
            (10,'CSC499','Capstone Project',                3,1,'Culminating project demonstrating program competencies.'),
        ]
    )

    conn.executemany(
        "INSERT INTO ClassSection (section_id,semester_id,course_id,instructor_id,room,schedule_slot,capacity,status) VALUES (?,?,?,?,?,?,?,?)",
        [
            (1, 1,1,3,'Room 101','MWF 08:00-09:00',  30,'completed'),
            (2, 1,2,3,'Room 102','MWF 10:00-11:00',  25,'completed'),
            (3, 1,6,4,'Room 201','TTH 09:00-10:30',  35,'completed'),
            (4, 1,9,5,'Room 305','MWF 13:00-14:00',  30,'completed'),
            (5, 2,3,3,'Room 101','MWF 09:00-10:00',  28,'completed'),
            (6, 2,7,4,'Room 202','TTH 11:00-12:30',  30,'completed'),
            (7, 2,4,5,'Room 303','MWF 14:00-15:00',  25,'completed'),
            (8, 2,8,6,'Room 204','TTH 13:00-14:30',  25,'completed'),
            (9, 3,5,6,'Room 101','MTWTH 10:00-11:30',20,'open'),
            (10,3,2,3,'Room 102','MTWTH 13:00-14:30',20,'open'),
            (11,4,1,3,'Room 101','MWF 08:00-09:00',  30,'open'),
            (12,4,3,3,'Room 102','MWF 10:00-11:00',  25,'open'),
            (13,4,6,4,'Room 201','TTH 09:00-10:30',  35,'open'),
            (14,4,5,6,'Room 204','TTH 14:00-15:30',  20,'full'),
            (15,4,4,5,'Room 303','MWF 13:00-14:00',  25,'open'),
            (16,4,10,5,'Room 305','TTH 11:00-12:30', 15,'open'),
        ]
    )

    conn.executemany(
        "INSERT INTO Enrollment (enrollment_id,student_id,section_id,enrollment_status,enrolled_at) VALUES (?,?,?,?,?)",
        [
            (1, 7, 1,'completed','2024-08-20 10:00:00'),
            (2, 7, 2,'completed','2024-08-20 10:05:00'),
            (3, 7, 3,'completed','2024-08-20 10:10:00'),
            (4, 8, 1,'completed','2024-08-20 11:00:00'),
            (5, 8, 3,'completed','2024-08-20 11:05:00'),
            (6, 8, 4,'completed','2024-08-20 11:10:00'),
            (7, 9, 1,'completed','2024-08-21 09:00:00'),
            (8, 9, 4,'completed','2024-08-21 09:10:00'),
            (9, 10,2,'completed','2024-08-21 10:00:00'),
            (10,10,3,'completed','2024-08-21 10:10:00'),
            (11,12,1,'completed','2024-08-21 11:00:00'),
            (12,12,2,'completed','2024-08-21 11:05:00'),
            (13,12,3,'completed','2024-08-21 11:10:00'),
            (14,12,4,'completed','2024-08-21 11:15:00'),
            (15,15,1,'completed','2024-08-22 09:00:00'),
            (16,15,2,'completed','2024-08-22 09:05:00'),
            (17,7, 5,'completed','2025-01-05 10:00:00'),
            (18,7, 6,'completed','2025-01-05 10:05:00'),
            (19,8, 5,'completed','2025-01-05 11:00:00'),
            (20,8, 7,'completed','2025-01-05 11:05:00'),
            (21,8, 8,'completed','2025-01-05 11:10:00'),
            (22,10,5,'completed','2025-01-06 10:00:00'),
            (23,10,6,'completed','2025-01-06 10:05:00'),
            (24,11,5,'completed','2025-01-06 11:00:00'),
            (25,11,7,'completed','2025-01-06 11:05:00'),
            (26,12,5,'completed','2025-01-06 12:00:00'),
            (27,12,6,'completed','2025-01-06 12:05:00'),
            (28,12,7,'completed','2025-01-06 12:10:00'),
            (29,14,6,'completed','2025-01-07 09:00:00'),
            (30,14,8,'completed','2025-01-07 09:05:00'),
            (31,15,5,'completed','2025-01-07 10:00:00'),
            (32,15,7,'completed','2025-01-07 10:05:00'),
            (33,7, 9,'enrolled', '2025-05-20 10:00:00'),
            (34,8, 9,'enrolled', '2025-05-20 11:00:00'),
            (35,10,9,'enrolled', '2025-05-21 10:00:00'),
            (36,12,9,'enrolled', '2025-05-21 11:00:00'),
            (37,14,10,'enrolled','2025-05-22 09:00:00'),
            (38,15,10,'enrolled','2025-05-22 10:00:00'),
            (39,7, 11,'enrolled','2025-08-15 10:00:00'),
            (40,7, 15,'enrolled','2025-08-15 10:05:00'),
            (41,8, 12,'enrolled','2025-08-15 11:00:00'),
            (42,8, 13,'enrolled','2025-08-15 11:05:00'),
            (43,10,11,'enrolled','2025-08-16 10:00:00'),
            (44,10,13,'enrolled','2025-08-16 10:05:00'),
            (45,12,12,'enrolled','2025-08-16 11:00:00'),
            (46,12,16,'enrolled','2025-08-16 11:05:00'),
            (47,14,11,'enrolled','2025-08-17 09:00:00'),
            (48,14,15,'enrolled','2025-08-17 09:05:00'),
            (49,15,16,'enrolled','2025-08-17 10:00:00'),
        ]
    )

    conn.executemany(
        "INSERT INTO WaitlistEntry (waitlist_id,student_id,section_id,position,created_at) VALUES (?,?,?,?,?)",
        [(1,9,14,1,'2025-08-18 10:00:00'),(2,11,14,2,'2025-08-18 10:30:00'),(3,13,14,3,'2025-08-18 11:00:00')]
    )

    conn.executemany(
        "INSERT INTO GradeRecord (grade_id,enrollment_id,letter_grade,grade_points,posted_at) VALUES (?,?,?,?,?)",
        [
            (1, 1, 'A',  4.00,'2024-12-22 10:00:00'),
            (2, 2, 'A-', 3.67,'2024-12-22 10:05:00'),
            (3, 3, 'B+', 3.33,'2024-12-22 10:10:00'),
            (4, 4, 'A',  4.00,'2024-12-22 11:00:00'),
            (5, 5, 'A',  4.00,'2024-12-22 11:05:00'),
            (6, 6, 'A-', 3.67,'2024-12-22 11:10:00'),
            (7, 7, 'C+', 2.33,'2024-12-22 12:00:00'),
            (8, 8, 'C',  2.00,'2024-12-22 12:05:00'),
            (9, 9, 'B',  3.00,'2024-12-22 13:00:00'),
            (10,10,'B+', 3.33,'2024-12-22 13:05:00'),
            (11,11,'A',  4.00,'2024-12-22 14:00:00'),
            (12,12,'A',  4.00,'2024-12-22 14:05:00'),
            (13,13,'A',  4.00,'2024-12-22 14:10:00'),
            (14,14,'A',  4.00,'2024-12-22 14:15:00'),
            (15,15,'A-', 3.67,'2024-12-22 15:00:00'),
            (16,16,'A',  4.00,'2024-12-22 15:05:00'),
            (17,17,'A',  4.00,'2025-05-12 10:00:00'),
            (18,18,'B+', 3.33,'2025-05-12 10:05:00'),
            (19,19,'A',  4.00,'2025-05-12 11:00:00'),
            (20,20,'A-', 3.67,'2025-05-12 11:05:00'),
            (21,21,'A',  4.00,'2025-05-12 11:10:00'),
            (22,22,'B+', 3.33,'2025-05-12 12:00:00'),
            (23,23,'A-', 3.67,'2025-05-12 12:05:00'),
            (24,24,'D',  1.00,'2025-05-12 13:00:00'),
            (25,25,'D+', 1.33,'2025-05-12 13:05:00'),
            (26,26,'A',  4.00,'2025-05-12 14:00:00'),
            (27,27,'A',  4.00,'2025-05-12 14:05:00'),
            (28,28,'A',  4.00,'2025-05-12 14:10:00'),
            (29,29,'B',  3.00,'2025-05-12 15:00:00'),
            (30,30,'B+', 3.33,'2025-05-12 15:05:00'),
            (31,31,'A',  4.00,'2025-05-12 16:00:00'),
            (32,32,'A-', 3.67,'2025-05-12 16:05:00'),
        ]
    )

    conn.executemany(
        "INSERT INTO Review (review_id,section_id,student_id,rating,review_text,taboo_count,visibility_status,created_at) VALUES (?,?,?,?,?,?,?,?)",
        [
            (1, 1, 7, 5,'Prof. Brooks explains concepts clearly. Great intro course.',      0,'visible','2024-12-25 10:00:00'),
            (2, 1, 8, 5,'Very engaging and well-structured. Highly recommend.',             0,'visible','2024-12-25 11:00:00'),
            (3, 1, 9, 3,'Decent course but pace was too fast for beginners.',               0,'visible','2024-12-26 09:00:00'),
            (4, 2, 7, 4,'Challenging but rewarding. Good coverage of data structures.',     0,'visible','2024-12-26 10:00:00'),
            (5, 3, 7, 4,'Prof. Kim is very knowledgeable. Calculus was tough but fair.',    0,'visible','2024-12-27 10:00:00'),
            (6, 3, 8, 5,'Best math professor I have had. Clear explanations.',              0,'visible','2024-12-27 11:00:00'),
            (7, 4, 8, 4,'Good writing course. Improved my academic writing significantly.', 0,'visible','2024-12-28 09:00:00'),
            (8, 5, 7, 5,'Databases course was excellent. Real-world examples were great.',  0,'visible','2025-05-15 10:00:00'),
            (9, 5, 8, 5,'Prof. Brooks again. Consistent quality. Love this instructor.',    0,'visible','2025-05-15 11:00:00'),
            (10,7, 8, 4,'Software Engineering was practical and industry-relevant.',        0,'visible','2025-05-16 10:00:00'),
            (11,8, 8, 3,'Linear Algebra was hard. Prof. Hassan needs clearer explanations.',1,'visible','2025-05-16 11:00:00'),
            (12,6, 10,4,'Discrete Math was interesting. Good logical thinking practice.',   0,'visible','2025-05-17 09:00:00'),
        ]
    )

    conn.executemany(
        "INSERT INTO Complaint (complaint_id,filed_by_user_id,target_user_id,complaint_text,status,resolution_note,resolved_by) VALUES (?,?,?,?,?,?,?)",
        [
            (1,9, 6,'Prof. Hassan was dismissive when I asked questions during office hours.','resolved','Instructor was counseled. Behavior noted in record.',1),
            (2,11,3,'I believe my grade was calculated incorrectly in CSC101.','resolved','Grade reviewed and confirmed accurate by registrar.',1),
            (3,7, 9,'Fellow student Marcus disrupted the class multiple times.','resolved','Warning issued to the student.',2),
            (4,14,6,'Instructor did not return graded work within stated timeframe.','open',None,None),
            (5,12,11,'Student Ethan made inappropriate remarks in group project.','under_review',None,None),
        ]
    )

    conn.executemany(
        "INSERT INTO WarningRecord (warning_id,user_id,reason,source_module,issued_at,active_flag) VALUES (?,?,?,?,?,?)",
        [
            (1,9, 'Low semester GPA below 2.5 threshold.',            'grade_engine',     '2024-12-23 08:00:00',1),
            (2,11,'GPA dropped below 2.0 — academic probation.',      'grade_engine',     '2025-05-13 08:00:00',1),
            (3,11,'Inappropriate behavior in collaborative setting.',  'complaint_module', '2025-05-18 09:00:00',1),
            (4,13,'Repeated low GPA leading to suspension.',          'grade_engine',     '2025-01-10 08:00:00',1),
            (5,6, 'Review complaints received from multiple students.','complaint_module', '2025-05-17 10:00:00',1),
        ]
    )

    conn.executemany(
        "INSERT INTO GraduationApplication (graduation_app_id,student_id,submitted_at,decision_status,reviewed_by,reviewed_at) VALUES (?,?,?,?,?,?)",
        [
            (1,15,'2025-05-01 09:00:00','approved',1,'2025-05-05 14:00:00'),
            (2,12,'2025-05-02 10:00:00','pending', None,None),
        ]
    )

    conn.executemany(
        "INSERT INTO AIQuery (query_id,user_id,question_text,answer_text,answer_source,warning_displayed,created_at) VALUES (?,?,?,?,?,?,?)",
        [
            (1,None,'What programs does College0 offer?','College0 offers programs in Computer Science, Mathematics, and Software Engineering.','vectordb',0,'2024-08-01 09:00:00'),
            (2,7,  'How do I register for courses?','Log in, navigate to Registration, select your semester, and choose available sections.','vectordb',0,'2024-08-20 08:30:00'),
            (3,8,  'What is the minimum GPA to avoid academic probation?','Students must maintain a cumulative GPA of at least 2.0 to remain in good standing.','vectordb',0,'2024-12-23 09:00:00'),
            (4,9,  'Can I retake a course I failed?','Yes, you may retake a course. The new grade replaces the old one in GPA calculations.','llm_fallback',1,'2025-01-06 10:00:00'),
            (5,11, 'What happens if I get 3 warnings?','Accumulating 3 active warnings may result in suspension or termination depending on severity.','vectordb',0,'2025-05-14 11:00:00'),
            (6,12, 'How do I apply for graduation?','Navigate to the Graduation section in your student portal and submit your application.','vectordb',0,'2025-04-30 10:00:00'),
            (7,None,'How can I apply to join the college?','Visit the Admissions page and complete the visitor application form.','vectordb',0,'2025-06-01 08:00:00'),
            (8,14, 'What is the waitlist process?','If a section is full, you are added to the waitlist. You are auto-enrolled when a seat opens.','llm_fallback',1,'2025-08-17 10:00:00'),
        ]
    )

    conn.commit()
    conn.close()
    print("Database initialized and seeded from official schema.")
