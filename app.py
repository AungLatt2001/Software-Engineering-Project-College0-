from flask import Flask, jsonify, request, session, send_from_directory
from werkzeug.security import check_password_hash
from database import get_db, init_db
import sqlite3
import os

app = Flask(__name__, static_folder="client/build", static_url_path="")
app.secret_key = "collegeo-secret-2024"

BUILD_DIR = os.path.join(os.path.dirname(__file__), "client", "build")

# ─── Helpers ────────────────────────────────────────────────────────────────

def get_active_semester(db):
    sem = db.execute(
        "SELECT * FROM Semester WHERE phase != 'closed' ORDER BY semester_id DESC LIMIT 1"
    ).fetchone()
    if not sem:
        sem = db.execute("SELECT * FROM Semester ORDER BY semester_id DESC LIMIT 1").fetchone()
    return sem

def sem_dict(sem):
    return dict(sem) if sem else None

def user_dict(u):
    return {k: u[k] for k in u.keys()} if u else None

def recalc_gpa(db, student_id):
    rows = db.execute("""
        SELECT gr.grade_points FROM GradeRecord gr
        JOIN Enrollment e ON gr.enrollment_id=e.enrollment_id
        WHERE e.student_id=?
    """, (student_id,)).fetchall()
    if not rows:
        return 0.0
    return round(sum(r["grade_points"] for r in rows) / len(rows), 3)

def issue_warning(db, user_id, reason, source):
    db.execute("INSERT INTO WarningRecord (user_id,reason,source_module) VALUES (?,?,?)",
               (user_id, reason, source))
    db.execute("UPDATE User SET warning_count=warning_count+1 WHERE user_id=?", (user_id,))
    count = db.execute("SELECT warning_count FROM User WHERE user_id=?", (user_id,)).fetchone()["warning_count"]
    if count >= 3:
        db.execute("UPDATE User SET status='suspended' WHERE user_id=?", (user_id,))

def run_phase_trigger(db, semester_id):
    """Called when phase changes to 'running'. Applies all business rules."""
    details = []
    students_warned = 0
    sections_cancelled = 0
    instructors_warned = 0
    instructors_suspended = 0
    special_reg_granted = 0

    # Step 1: cancel sections with < 3 enrolled students
    sections = db.execute("""
        SELECT cs.section_id, cs.instructor_id, c.code, c.title,
               (SELECT COUNT(*) FROM Enrollment e WHERE e.section_id=cs.section_id
                AND e.enrollment_status='enrolled') as enrolled_count
        FROM ClassSection cs
        JOIN Course c ON cs.course_id=c.course_id
        WHERE cs.semester_id=? AND cs.status IN ('open','full')
    """, (semester_id,)).fetchall()

    cancelled_section_ids = set()
    affected_instructor_ids = set()

    for sec in sections:
        if sec["enrolled_count"] < 3:
            db.execute("UPDATE ClassSection SET status='cancelled' WHERE section_id=?", (sec["section_id"],))
            cancelled_section_ids.add(sec["section_id"])
            affected_instructor_ids.add(sec["instructor_id"])
            sections_cancelled += 1
            details.append(f"Section {sec['code']} cancelled ({sec['enrolled_count']} students enrolled).")

            # Grant special re-registration to students in this section
            enrolled_students = db.execute("""
                SELECT student_id FROM Enrollment
                WHERE section_id=? AND enrollment_status='enrolled'
            """, (sec["section_id"],)).fetchall()
            for s in enrolled_students:
                db.execute("UPDATE Student SET special_reg_eligible=1 WHERE student_id=?", (s["student_id"],))
                special_reg_granted += 1

    # Step 2: warn instructors of cancelled sections; suspend if ALL sections cancelled
    for instr_id in affected_instructor_ids:
        all_sections = db.execute("""
            SELECT COUNT(*) as total FROM ClassSection
            WHERE instructor_id=? AND semester_id=? AND status != 'cancelled'
        """, (instr_id, semester_id)).fetchone()["total"]

        instr_name = db.execute(
            "SELECT first_name||' '||last_name as n FROM User WHERE user_id=?", (instr_id,)
        ).fetchone()["n"]

        issue_warning(db, instr_id, "One or more assigned course sections were cancelled due to low enrollment.", "phase_trigger")
        instructors_warned += 1
        details.append(f"Instructor {instr_name} warned for cancelled section(s).")

        if all_sections == 0:
            db.execute("UPDATE Instructor SET suspension_next_semester=1 WHERE instructor_id=?", (instr_id,))
            instructors_suspended += 1
            details.append(f"Instructor {instr_name} flagged for suspension next semester (all courses cancelled).")

    # Step 3: warn students with fewer than 2 enrolled courses (after cancellations)
    all_students = db.execute("SELECT student_id FROM Student").fetchall()
    for row in all_students:
        sid = row["student_id"]
        user_row = db.execute("SELECT status FROM User WHERE user_id=?", (sid,)).fetchone()
        if user_row and user_row["status"] == "suspended":
            continue
        count = db.execute("""
            SELECT COUNT(*) as n FROM Enrollment e
            JOIN ClassSection cs ON e.section_id=cs.section_id
            WHERE e.student_id=? AND cs.semester_id=? AND e.enrollment_status='enrolled'
            AND cs.status NOT IN ('cancelled')
        """, (sid, semester_id)).fetchone()["n"]
        if count < 2:
            issue_warning(db, sid, f"Enrolled in fewer than 2 courses this semester ({count} active course(s)).", "phase_trigger")
            students_warned += 1
            sname = db.execute("SELECT first_name||' '||last_name as n FROM User WHERE user_id=?", (sid,)).fetchone()["n"]
            details.append(f"Student {sname} warned (only {count} active course(s)).")

    db.commit()
    return {
        "students_warned": students_warned,
        "sections_cancelled": sections_cancelled,
        "instructors_warned": instructors_warned,
        "instructors_suspended": instructors_suspended,
        "special_reg_granted": special_reg_granted,
        "details": details,
    }

def handle_ai(question, user_id, db):
    q = question.lower()
    if "graduation" in q and "requirement" in q:
        return ("To graduate from College0, you must complete all required core courses "
                "(CSC101, CSC201, CSC301, CSC401, MTH101, MTH201, ENG101, CSC499), "
                "maintain a cumulative GPA ≥ 2.0, have 0 active warnings, no outstanding fines, "
                "and submit a graduation application during the grading phase.")
    if "warning" in q:
        return ("Warnings are issued for low GPA, having fewer than 2 courses, or policy violations. "
                "Each student may accumulate up to 3 warnings before facing suspension. "
                "Earning an Honor removes one active warning. "
                "Instructors whose courses are all cancelled will be suspended from teaching next semester.")
    if "cancel" in q or "fewer than" in q or "minimum" in q:
        return ("Courses with fewer than 3 enrolled students will be cancelled when the semester moves to Running phase. "
                "Students in cancelled courses receive a special re-registration opportunity to join another open section. "
                "The instructor of any cancelled course receives a warning; if all their courses are cancelled, "
                "they are suspended from teaching next semester.")
    if "special registration" in q or "special reg" in q:
        return ("Special re-registration is granted to students whose courses were cancelled due to low enrollment. "
                "These students can enroll in other open sections even during the Running phase. "
                "Check your My Courses page — a banner will appear if you are eligible.")
    if "phase" in q or "semester" in q:
        return ("Each semester has 5 phases: Setup (admin configures sections), "
                "Registration (students enroll), Running (classes in session — low-enrollment courses are auto-cancelled), "
                "Grading (instructors post grades, students submit reviews), "
                "and Closed (semester archived).")
    if "review" in q:
        return ("Course reviews are anonymous and can only be submitted during the Grading phase. "
                "Rate your section 1–5 stars and leave optional comments. "
                "Reviews with inappropriate language may be flagged by the Registrar.")
    if "waitlist" in q:
        return ("If a section is full, you can join the waitlist. "
                "You are automatically enrolled when a seat opens up, in order of your waitlist position.")
    if "complaint" in q:
        return ("Students can file complaints against any user via the Reviews & More page. "
                "Instructors can file complaints against students in their classes, requesting a warning or de-registration. "
                "Registrars must act on instructor complaints by either punishing the student or warning the instructor.")
    if "fine" in q:
        return ("Outstanding fines must be paid before you can register for new courses or apply for graduation. "
                "Contact the Registrar's office to resolve any fines.")
    if "suspend" in q:
        return ("Student suspension occurs after 3 warnings or a severe violation. "
                "Instructor suspension (from teaching next semester) occurs when all of their courses are cancelled. "
                "A suspended student cannot enroll in courses until the suspension is lifted.")
    if "gpa" in q:
        if user_id:
            st = db.execute("SELECT cumulative_gpa, semester_gpa FROM Student WHERE student_id=?", (user_id,)).fetchone()
            if st:
                return (f"Your cumulative GPA is {st['cumulative_gpa']:.3f} and your semester GPA is "
                        f"{st['semester_gpa']:.3f}. A minimum of 2.0 is required to remain in good standing.")
        return ("GPA is calculated as the average grade points across all completed courses. "
                "Grade scale: A/A+ = 4.0, A- = 3.67, B+ = 3.33, B = 3.0, B- = 2.67, "
                "C+ = 2.33, C = 2.0, D = 1.0, F = 0.0.")
    if "tutorial" in q or "how to use" in q or "new student" in q:
        return ("New students see an interactive tutorial when they first log in. "
                "It covers the Dashboard, My Courses, Transcript, Reviews, and the important academic rules. "
                "You can always ask me questions here anytime!")
    if "instructor" in q and "complain" in q:
        return ("Instructors can file complaints against students in their classes from the My Classes page. "
                "They can request the student be warned or de-registered. "
                "The Registrar must then take action — either punish the student or warn the instructor.")
    if "enroll" in q or "register" in q:
        return ("Course enrollment is only available during the Registration phase, or during a special re-registration period. "
                "Go to My Courses to browse available sections. You must have at least 2 courses to avoid a warning.")
    if "core" in q or "required" in q:
        return ("Core (required) courses: CSC101, CSC201, CSC301, CSC401, MTH101, MTH201, ENG101, CSC499. "
                "All must be completed to apply for graduation.")
    return ("I can answer questions about College0. Try asking about graduation requirements, "
            "GPA, semester phases, course cancellation rules, special registration, "
            "warnings, complaints, or the tutorial.")

# ─── Auth ───────────────────────────────────────────────────────────────────

@app.route("/api/me")
def api_me():
    if "user_id" not in session:
        return jsonify({"user": None}), 200
    db = get_db()
    user = db.execute("SELECT * FROM User WHERE user_id=?", (session["user_id"],)).fetchone()
    sem  = get_active_semester(db)
    first_login = False
    if user and user["role"] == "student":
        st = db.execute("SELECT first_login_required FROM Student WHERE student_id=?", (user["user_id"],)).fetchone()
        first_login = bool(st and st["first_login_required"])
    db.close()
    return jsonify({"user": user_dict(user), "sem": sem_dict(sem), "first_login_required": first_login})

@app.route("/api/sem")
def api_sem():
    db  = get_db()
    sem = get_active_semester(db)
    db.close()
    return jsonify(sem_dict(sem))

@app.route("/api/login", methods=["POST"])
def api_login():
    data  = request.get_json()
    email = (data.get("email") or "").strip().lower()
    pw    = (data.get("password") or "").strip()
    db    = get_db()
    user  = db.execute("SELECT * FROM User WHERE LOWER(email)=?", (email,)).fetchone()
    sem   = get_active_semester(db)
    first_login = False
    if user and user["role"] == "student":
        st = db.execute("SELECT first_login_required FROM Student WHERE student_id=?", (user["user_id"],)).fetchone()
        first_login = bool(st and st["first_login_required"])
    db.close()
    if user and check_password_hash(user["password_hash"], pw):
        session["user_id"] = user["user_id"]
        session["role"]    = user["role"]
        return jsonify({"user": user_dict(user), "sem": sem_dict(sem), "first_login_required": first_login})
    return jsonify({"error": "Invalid credentials"}), 401

@app.route("/api/logout", methods=["POST"])
def api_logout():
    session.clear()
    return jsonify({"ok": True})

@app.route("/api/tutorial/dismiss", methods=["POST"])
def api_tutorial_dismiss():
    uid = session.get("user_id")
    if uid:
        db = get_db()
        db.execute("UPDATE Student SET first_login_required=0 WHERE student_id=?", (uid,))
        db.commit()
        db.close()
    return jsonify({"ok": True})

# ─── Home ───────────────────────────────────────────────────────────────────

@app.route("/api/home")
def api_home():
    db  = get_db()
    sem = get_active_semester(db)
    sid = sem["semester_id"]

    total_students = db.execute("SELECT COUNT(*) as c FROM Student").fetchone()["c"]
    total_faculty  = db.execute("SELECT COUNT(*) as c FROM Instructor").fetchone()["c"]
    total_sections = db.execute(
        "SELECT COUNT(*) as c FROM ClassSection WHERE semester_id=? AND status != 'cancelled'", (sid,)
    ).fetchone()["c"]
    gpas = db.execute("SELECT cumulative_gpa FROM Student").fetchall()
    campus_gpa = round(sum(r["cumulative_gpa"] for r in gpas) / len(gpas), 2) if gpas else 0.0

    ratings_rows = db.execute("""
        SELECT c.course_id, c.code, c.title, AVG(r.rating) as avg_rating
        FROM Review r
        JOIN ClassSection cs ON r.section_id=cs.section_id
        JOIN Course c ON cs.course_id=c.course_id
        WHERE r.visibility_status='visible'
        GROUP BY c.course_id
    """).fetchall()
    ratings = [{"course_id": r["course_id"], "code": r["code"], "title": r["title"], "avg": round(r["avg_rating"],1)} for r in ratings_rows]
    top_rated = sorted(ratings, key=lambda x: -x["avg"])[:3]
    needs_imp = sorted(ratings, key=lambda x: x["avg"])[:3]

    top_gpa = [dict(r) for r in db.execute("""
        SELECT u.first_name||' '||u.last_name as name, u.user_id, s.cumulative_gpa
        FROM Student s JOIN User u ON s.student_id=u.user_id
        ORDER BY s.cumulative_gpa DESC LIMIT 4
    """).fetchall()]

    sections = [dict(r) for r in db.execute("""
        SELECT cs.section_id, cs.schedule_slot, cs.room, cs.capacity, cs.status,
               c.code, c.title, c.is_core, c.credit_hours,
               u.first_name||' '||u.last_name as instructor_name,
               (SELECT COUNT(*) FROM Enrollment e WHERE e.section_id=cs.section_id
                AND e.enrollment_status IN ('enrolled','completed')) as enrolled_count
        FROM ClassSection cs
        JOIN Course c ON cs.course_id=c.course_id
        JOIN User u ON cs.instructor_id=u.user_id
        WHERE cs.semester_id=? ORDER BY c.code
    """, (sid,)).fetchall()]

    db.close()
    return jsonify({
        "total_students": total_students, "total_faculty": total_faculty,
        "total_sections": total_sections, "campus_gpa": campus_gpa,
        "top_rated": top_rated, "needs_imp": needs_imp,
        "top_gpa": top_gpa, "sections": sections, "sem": sem_dict(sem),
    })

# ─── Student ─────────────────────────────────────────────────────────────────

@app.route("/api/dashboard")
def api_dashboard():
    if session.get("role") != "student":
        return jsonify({"error": "Forbidden"}), 403
    uid = session["user_id"]
    db  = get_db()
    sem = get_active_semester(db)
    st  = dict(db.execute("SELECT * FROM Student WHERE student_id=?", (uid,)).fetchone())
    enrolled = db.execute("""
        SELECT COUNT(*) as n FROM Enrollment e
        JOIN ClassSection cs ON e.section_id=cs.section_id
        WHERE e.student_id=? AND cs.semester_id=? AND e.enrollment_status='enrolled'
    """, (uid, sem["semester_id"])).fetchone()["n"]
    completed = db.execute(
        "SELECT COUNT(*) as n FROM Enrollment WHERE student_id=? AND enrollment_status='completed'", (uid,)
    ).fetchone()["n"]
    db.close()
    return jsonify({"st": st, "enrolled": enrolled, "completed": completed})

@app.route("/api/my-courses", methods=["GET","POST"])
def api_my_courses():
    if session.get("role") != "student":
        return jsonify({"error": "Forbidden"}), 403
    uid = session["user_id"]
    db  = get_db()
    sem = get_active_semester(db)
    sid = sem["semester_id"]
    st  = db.execute("SELECT special_reg_eligible FROM Student WHERE student_id=?", (uid,)).fetchone()
    special_reg = bool(st and st["special_reg_eligible"])

    if request.method == "POST":
        data       = request.get_json()
        action     = data.get("action")
        section_id = int(data.get("section_id", 0))
        phase      = sem["phase"]

        can_enroll = phase == "registration" or (phase == "running" and special_reg)
        if not can_enroll:
            db.close()
            return jsonify({"msg": f"Enrollment is closed (Phase: {phase}). Opens during Registration period."}), 200

        if action == "enroll":
            sec = db.execute("SELECT * FROM ClassSection WHERE section_id=?", (section_id,)).fetchone()
            if sec and sec["status"] == "full":
                pos = (db.execute("SELECT MAX(position) as p FROM WaitlistEntry WHERE section_id=?",
                                  (section_id,)).fetchone()["p"] or 0) + 1
                try:
                    db.execute("INSERT INTO WaitlistEntry (student_id,section_id,position) VALUES (?,?,?)",
                               (uid, section_id, pos))
                    db.commit()
                    db.close()
                    return jsonify({"msg": "Section is full — added to waitlist."})
                except sqlite3.IntegrityError:
                    db.close()
                    return jsonify({"msg": "Already on waitlist for this section."})
            else:
                try:
                    db.execute("INSERT INTO Enrollment (student_id,section_id,enrollment_status) VALUES (?,?,?)",
                               (uid, section_id, "enrolled"))
                    # After special reg enrollment, clear the flag
                    if phase == "running" and special_reg:
                        db.execute("UPDATE Student SET special_reg_eligible=0 WHERE student_id=?", (uid,))
                    db.commit()
                    db.close()
                    return jsonify({"msg": "Enrolled successfully!"})
                except sqlite3.IntegrityError:
                    db.close()
                    return jsonify({"msg": "Already enrolled in this section."})
        elif action == "drop":
            if phase != "registration":
                db.close()
                return jsonify({"msg": "Dropping courses is only allowed during the Registration phase."})
            db.execute("DELETE FROM Enrollment WHERE student_id=? AND section_id=? AND enrollment_status='enrolled'",
                       (uid, section_id))
            db.commit()
            db.close()
            return jsonify({"msg": "Dropped successfully."})
        db.close()
        return jsonify({"msg": "Unknown action."})

    current = [dict(r) for r in db.execute("""
        SELECT e.enrollment_id, e.section_id, e.enrollment_status,
               c.code, c.title, c.credit_hours, cs.schedule_slot, cs.room,
               u.first_name||' '||u.last_name as instructor_name
        FROM Enrollment e
        JOIN ClassSection cs ON e.section_id=cs.section_id
        JOIN Course c ON cs.course_id=c.course_id
        JOIN User u ON cs.instructor_id=u.user_id
        WHERE e.student_id=? AND cs.semester_id=? AND e.enrollment_status='enrolled'
    """, (uid, sid)).fetchall()]

    enrolled_ids = [e["section_id"] for e in current]

    waitlisted = [r["section_id"] for r in db.execute(
        "SELECT section_id FROM WaitlistEntry WHERE student_id=?", (uid,)
    ).fetchall()]

    all_sections = [dict(r) for r in db.execute("""
        SELECT cs.section_id, cs.schedule_slot, cs.room, cs.capacity, cs.status,
               c.code, c.title, c.is_core, c.credit_hours,
               u.first_name||' '||u.last_name as instructor_name,
               (SELECT COUNT(*) FROM Enrollment e2 WHERE e2.section_id=cs.section_id
                AND e2.enrollment_status IN ('enrolled','completed')) as enrolled_count
        FROM ClassSection cs
        JOIN Course c ON cs.course_id=c.course_id
        JOIN User u ON cs.instructor_id=u.user_id
        WHERE cs.semester_id=? AND cs.status IN ('open','full') ORDER BY c.code
    """, (sid,)).fetchall()]

    db.close()
    return jsonify({
        "current_enrollments": current,
        "all_sections": all_sections,
        "enrolled_section_ids": enrolled_ids,
        "waitlisted_ids": waitlisted,
        "special_reg": special_reg,
    })

@app.route("/api/transcript")
def api_transcript():
    if session.get("role") != "student":
        return jsonify({"error": "Forbidden"}), 403
    uid = session["user_id"]
    db  = get_db()
    st  = dict(db.execute("SELECT * FROM Student WHERE student_id=?", (uid,)).fetchone())
    history = [dict(r) for r in db.execute("""
        SELECT gr.letter_grade, gr.grade_points, c.code, c.title, c.credit_hours,
               s.term_name, s.year
        FROM GradeRecord gr
        JOIN Enrollment e ON gr.enrollment_id=e.enrollment_id
        JOIN ClassSection cs ON e.section_id=cs.section_id
        JOIN Course c ON cs.course_id=c.course_id
        JOIN Semester s ON cs.semester_id=s.semester_id
        WHERE e.student_id=? ORDER BY s.semester_id, c.code
    """, (uid,)).fetchall()]
    db.close()
    return jsonify({"st": st, "history": history})

@app.route("/api/reviews/data")
def api_reviews_data():
    if session.get("role") != "student":
        return jsonify({"error": "Forbidden"}), 403
    uid = session["user_id"]
    db  = get_db()
    my_sections = [dict(r) for r in db.execute("""
        SELECT cs.section_id, c.code, c.title, s.term_name, s.year
        FROM Enrollment e
        JOIN ClassSection cs ON e.section_id=cs.section_id
        JOIN Course c ON cs.course_id=c.course_id
        JOIN Semester s ON cs.semester_id=s.semester_id
        WHERE e.student_id=? ORDER BY s.semester_id DESC, c.code
    """, (uid,)).fetchall()]
    targets = [dict(r) for r in db.execute("""
        SELECT user_id, first_name||' '||last_name as name, role
        FROM User WHERE user_id != ? AND role IN ('instructor','registrar','student')
        ORDER BY role, first_name
    """, (uid,)).fetchall()]
    db.close()
    return jsonify({"my_sections": my_sections, "potential_targets": targets})

@app.route("/api/reviews/review", methods=["POST"])
def api_submit_review():
    if session.get("role") != "student":
        return jsonify({"error": "Forbidden"}), 403
    uid  = session["user_id"]
    data = request.get_json()
    db   = get_db()
    sem  = get_active_semester(db)
    if sem["phase"] != "grading":
        db.close()
        return jsonify({"msg": f"Reviews only available during Grading phase (current: {sem['phase']})."}), 200
    try:
        db.execute("INSERT INTO Review (section_id,student_id,rating,review_text) VALUES (?,?,?,?)",
                   (int(data["section_id"]), uid, int(data["rating"]), data.get("review_text","")))
        db.commit()
        db.close()
        return jsonify({"msg": "Review submitted successfully!"})
    except sqlite3.IntegrityError:
        db.close()
        return jsonify({"msg": "You already reviewed this section."})

@app.route("/api/reviews/graduation", methods=["POST"])
def api_submit_graduation():
    if session.get("role") != "student":
        return jsonify({"error": "Forbidden"}), 403
    uid = session["user_id"]
    db  = get_db()
    existing = db.execute(
        "SELECT graduation_app_id FROM GraduationApplication WHERE student_id=? AND decision_status='pending'", (uid,)
    ).fetchone()
    if existing:
        db.close()
        return jsonify({"msg": "You already have a pending graduation application."})
    db.execute("INSERT INTO GraduationApplication (student_id) VALUES (?)", (uid,))
    db.commit()
    db.close()
    return jsonify({"msg": "Graduation application submitted! The Registrar will review it."})

@app.route("/api/reviews/complaint", methods=["POST"])
def api_submit_complaint():
    if session.get("role") != "student":
        return jsonify({"error": "Forbidden"}), 403
    uid  = session["user_id"]
    data = request.get_json()
    if not data.get("complaint_text") or not data.get("target_user_id"):
        return jsonify({"msg": "Please fill in all required fields."}), 400
    db = get_db()
    db.execute(
        "INSERT INTO Complaint (filed_by_user_id,target_user_id,complaint_text,complaint_type) VALUES (?,?,?,?)",
        (uid, int(data["target_user_id"]), data["complaint_text"], "general")
    )
    db.commit()
    db.close()
    return jsonify({"msg": "Complaint submitted and will be reviewed confidentially."})

@app.route("/api/ai", methods=["POST"])
def api_ai():
    data     = request.get_json()
    question = (data.get("question") or "").strip()
    uid      = session.get("user_id")
    db       = get_db()
    answer   = handle_ai(question, uid, db)
    db.execute("INSERT INTO AIQuery (user_id,question_text,answer_text,answer_source) VALUES (?,?,?,?)",
               (uid, question, answer, "vectordb"))
    db.commit()
    db.close()
    return jsonify({"answer": answer})

# ─── Instructor ──────────────────────────────────────────────────────────────

@app.route("/api/instructor")
def api_instructor():
    if session.get("role") != "instructor":
        return jsonify({"error": "Forbidden"}), 403
    uid = session["user_id"]
    db  = get_db()
    sem = get_active_semester(db)
    instr = dict(db.execute("SELECT * FROM Instructor WHERE instructor_id=?", (uid,)).fetchone())

    my_sections = db.execute("""
        SELECT cs.section_id, cs.schedule_slot, cs.room, cs.capacity, cs.status,
               c.code, c.title, c.credit_hours,
               (SELECT COUNT(*) FROM Enrollment e WHERE e.section_id=cs.section_id
                AND e.enrollment_status IN ('enrolled','completed')) as enrolled_count
        FROM ClassSection cs JOIN Course c ON cs.course_id=c.course_id
        WHERE cs.instructor_id=? AND cs.semester_id=? ORDER BY c.code
    """, (uid, sem["semester_id"])).fetchall()

    sections_data = []
    for sec in my_sections:
        students = [dict(r) for r in db.execute("""
            SELECT e.enrollment_id, e.student_id, e.enrollment_status,
                   u.first_name||' '||u.last_name as name,
                   u.warning_count, st.cumulative_gpa, st.semester_gpa, st.honor_count,
                   gr.letter_grade, gr.grade_points
            FROM Enrollment e
            JOIN User u ON e.student_id=u.user_id
            JOIN Student st ON e.student_id=st.student_id
            LEFT JOIN GradeRecord gr ON gr.enrollment_id=e.enrollment_id
            WHERE e.section_id=? AND e.enrollment_status IN ('enrolled','completed')
            ORDER BY u.last_name
        """, (sec["section_id"],)).fetchall()]

        # Attach full grade history for each student
        for s in students:
            s["grade_history"] = [dict(r) for r in db.execute("""
                SELECT c.code, c.title, gr.letter_grade, s2.term_name, s2.year
                FROM GradeRecord gr
                JOIN Enrollment e2 ON gr.enrollment_id=e2.enrollment_id
                JOIN ClassSection cs2 ON e2.section_id=cs2.section_id
                JOIN Course c ON cs2.course_id=c.course_id
                JOIN Semester s2 ON cs2.semester_id=s2.semester_id
                WHERE e2.student_id=?
                ORDER BY s2.semester_id, c.code
            """, (s["student_id"],)).fetchall()]

        sections_data.append({"section": dict(sec), "students": students})

    db.close()
    return jsonify({"sections_data": sections_data, "instructor": instr})

@app.route("/api/instructor/grade", methods=["POST"])
def api_grade():
    if session.get("role") != "instructor":
        return jsonify({"error": "Forbidden"}), 403
    data   = request.get_json()
    eid    = int(data.get("enrollment_id", 0))
    letter = (data.get("grade") or "").strip().upper()
    GRADE_MAP = {"A+":4.0,"A":4.0,"A-":3.67,"B+":3.33,"B":3.0,"B-":2.67,
                 "C+":2.33,"C":2.0,"C-":1.67,"D+":1.33,"D":1.0,"F":0.0}
    pts = GRADE_MAP.get(letter)
    if not letter or pts is None:
        return jsonify({"msg": "Invalid grade."}), 400
    db = get_db()
    db.execute(
        "INSERT INTO GradeRecord (enrollment_id,letter_grade,grade_points) VALUES (?,?,?) "
        "ON CONFLICT(enrollment_id) DO UPDATE SET letter_grade=excluded.letter_grade, grade_points=excluded.grade_points",
        (eid, letter, pts)
    )
    enr = db.execute("SELECT student_id FROM Enrollment WHERE enrollment_id=?", (eid,)).fetchone()
    if enr:
        new_gpa = recalc_gpa(db, enr["student_id"])
        db.execute("UPDATE Student SET cumulative_gpa=? WHERE student_id=?", (new_gpa, enr["student_id"]))
    db.commit()
    db.close()
    return jsonify({"msg": f"Grade {letter} saved."})

@app.route("/api/instructor/student-complaint", methods=["POST"])
def api_instructor_complaint():
    if session.get("role") != "instructor":
        return jsonify({"error": "Forbidden"}), 403
    uid  = session["user_id"]
    data = request.get_json()
    student_id      = int(data.get("student_id", 0))
    section_id      = int(data.get("section_id", 0))
    requested_action = data.get("requested_action", "warn")
    complaint_text  = (data.get("complaint_text") or "").strip()
    if not complaint_text:
        return jsonify({"msg": "Please describe the issue."}), 400
    if requested_action not in ("warn", "deregister"):
        return jsonify({"msg": "Invalid requested action."}), 400
    db = get_db()
    # Verify the student is in the instructor's class
    enrolled = db.execute("""
        SELECT e.enrollment_id FROM Enrollment e
        JOIN ClassSection cs ON e.section_id=cs.section_id
        WHERE e.student_id=? AND e.section_id=? AND cs.instructor_id=?
        AND e.enrollment_status IN ('enrolled','completed')
    """, (student_id, section_id, uid)).fetchone()
    if not enrolled:
        db.close()
        return jsonify({"msg": "Student not found in your class."}), 400
    db.execute("""
        INSERT INTO Complaint (filed_by_user_id, target_user_id, complaint_text, complaint_type, requested_action, section_id)
        VALUES (?,?,?,?,?,?)
    """, (uid, student_id, complaint_text, "instructor_vs_student", requested_action, section_id))
    db.commit()
    db.close()
    return jsonify({"msg": "Complaint filed. The Registrar will review it and take action."})

# ─── Registrar ───────────────────────────────────────────────────────────────

@app.route("/api/registrar")
def api_registrar():
    if session.get("role") != "registrar":
        return jsonify({"error": "Forbidden"}), 403
    db = get_db()

    students = [dict(r) for r in db.execute("""
        SELECT u.user_id, u.first_name||' '||u.last_name as name, u.email,
               u.status, u.warning_count,
               s.cumulative_gpa, s.semester_gpa, s.honor_count, s.fine_due
        FROM Student s JOIN User u ON s.student_id=u.user_id ORDER BY u.last_name
    """).fetchall()]

    instructors = [dict(r) for r in db.execute("""
        SELECT u.user_id, u.first_name||' '||u.last_name as name, u.status, u.warning_count,
               i.specialization, i.rating_average, i.suspension_next_semester
        FROM Instructor i JOIN User u ON i.instructor_id=u.user_id ORDER BY u.last_name
    """).fetchall()]

    applications = [dict(r) for r in db.execute(
        "SELECT * FROM VisitorApplication ORDER BY application_id DESC"
    ).fetchall()]

    complaints = [dict(r) for r in db.execute("""
        SELECT c.*, uf.first_name||' '||uf.last_name as filer_name,
               ut.first_name||' '||ut.last_name as target_name
        FROM Complaint c
        JOIN User uf ON c.filed_by_user_id=uf.user_id
        JOIN User ut ON c.target_user_id=ut.user_id
        ORDER BY c.complaint_id DESC
    """).fetchall()]

    grad_apps = [dict(r) for r in db.execute("""
        SELECT ga.*, u.first_name||' '||u.last_name as student_name, s.cumulative_gpa
        FROM GraduationApplication ga
        JOIN User u ON ga.student_id=u.user_id
        JOIN Student s ON ga.student_id=s.student_id
        ORDER BY ga.graduation_app_id DESC
    """).fetchall()]

    all_semesters = [dict(r) for r in db.execute("SELECT * FROM Semester ORDER BY semester_id").fetchall()]

    warnings = [dict(r) for r in db.execute("""
        SELECT w.*, u.first_name||' '||u.last_name as user_name, u.role as user_role
        FROM WarningRecord w JOIN User u ON w.user_id=u.user_id
        WHERE w.active_flag=1 ORDER BY w.issued_at DESC
    """).fetchall()]

    special_reg_students = [dict(r) for r in db.execute("""
        SELECT u.user_id, u.first_name||' '||u.last_name as name
        FROM Student s JOIN User u ON s.student_id=u.user_id
        WHERE s.special_reg_eligible=1
    """).fetchall()]

    db.close()
    return jsonify({
        "students": students, "instructors": instructors,
        "applications": applications, "complaints": complaints,
        "grad_apps": grad_apps, "all_semesters": all_semesters,
        "warnings": warnings, "special_reg_students": special_reg_students,
    })

@app.route("/api/registrar/phase", methods=["POST"])
def api_set_phase():
    if session.get("role") != "registrar":
        return jsonify({"error": "Forbidden"}), 403
    data    = request.get_json()
    sem_id  = int(data.get("semester_id", 0))
    phase   = data.get("phase", "")
    valid   = ("setup","registration","running","grading","closed")
    if phase not in valid:
        return jsonify({"msg": "Invalid phase."}), 400
    db = get_db()
    db.execute("UPDATE Semester SET phase=? WHERE semester_id=?", (phase, sem_id))
    db.commit()

    trigger_result = None
    if phase == "running":
        trigger_result = run_phase_trigger(db, sem_id)

    sem = get_active_semester(db)
    db.close()
    return jsonify({"msg": f"Phase updated to {phase}.", "sem": sem_dict(sem), "trigger_result": trigger_result})

@app.route("/api/registrar/application/<int:app_id>", methods=["POST"])
def api_decide_application(app_id):
    if session.get("role") != "registrar":
        return jsonify({"error": "Forbidden"}), 403
    data     = request.get_json()
    decision = data.get("decision","")
    if decision not in ("approved","rejected"):
        return jsonify({"msg": "Invalid decision."}), 400
    db = get_db()
    db.execute(
        "UPDATE VisitorApplication SET status=?, reviewed_by=?, reviewed_at=CURRENT_TIMESTAMP WHERE application_id=?",
        (decision, session["user_id"], app_id)
    )
    db.commit()
    db.close()
    return jsonify({"msg": f"Application {decision}."})

@app.route("/api/registrar/complaint/<int:cid>", methods=["POST"])
def api_resolve_complaint(cid):
    if session.get("role") != "registrar":
        return jsonify({"error": "Forbidden"}), 403
    data   = request.get_json()
    action = data.get("action", "resolve")
    note   = (data.get("resolution_note") or "").strip()
    db     = get_db()

    complaint = db.execute("SELECT * FROM Complaint WHERE complaint_id=?", (cid,)).fetchone()
    if not complaint:
        db.close()
        return jsonify({"msg": "Complaint not found."}), 404

    if action == "warn_student":
        issue_warning(db, complaint["target_user_id"],
                      f"Warning issued following instructor complaint: {complaint['complaint_text'][:80]}",
                      "instructor_complaint")
        db.execute("UPDATE Complaint SET status='resolved', resolution_note=?, resolved_by=? WHERE complaint_id=?",
                   (note or "Student warned.", session["user_id"], cid))
        msg = "Student warned and complaint resolved."
    elif action == "deregister_student":
        section_id = complaint["section_id"]
        if section_id:
            db.execute("DELETE FROM Enrollment WHERE student_id=? AND section_id=? AND enrollment_status='enrolled'",
                       (complaint["target_user_id"], section_id))
        db.execute("UPDATE Complaint SET status='resolved', resolution_note=?, resolved_by=? WHERE complaint_id=?",
                   (note or "Student de-registered from section.", session["user_id"], cid))
        msg = "Student de-registered and complaint resolved."
    elif action == "warn_instructor":
        issue_warning(db, complaint["filed_by_user_id"],
                      f"Instructor complaint deemed unfounded by Registrar: {complaint['complaint_text'][:80]}",
                      "instructor_complaint_reversed")
        db.execute("UPDATE Complaint SET status='dismissed', resolution_note=?, resolved_by=? WHERE complaint_id=?",
                   (note or "Complaint unfounded. Instructor warned.", session["user_id"], cid))
        msg = "Complaint dismissed and instructor warned."
    elif action == "resolve":
        db.execute("UPDATE Complaint SET status='resolved', resolution_note=?, resolved_by=? WHERE complaint_id=?",
                   (note or None, session["user_id"], cid))
        msg = "Complaint resolved."
    elif action == "dismiss":
        db.execute("UPDATE Complaint SET status='dismissed', resolution_note=?, resolved_by=? WHERE complaint_id=?",
                   (note or None, session["user_id"], cid))
        msg = "Complaint dismissed."
    else:
        db.close()
        return jsonify({"msg": "Invalid action."}), 400

    db.commit()
    db.close()
    return jsonify({"msg": msg})

@app.route("/api/registrar/graduation/<int:gid>", methods=["POST"])
def api_decide_graduation(gid):
    if session.get("role") != "registrar":
        return jsonify({"error": "Forbidden"}), 403
    data     = request.get_json()
    decision = data.get("decision","")
    if decision not in ("approved","rejected"):
        return jsonify({"msg": "Invalid decision."}), 400
    db = get_db()
    db.execute(
        "UPDATE GraduationApplication SET decision_status=?, reviewed_by=?, reviewed_at=CURRENT_TIMESTAMP WHERE graduation_app_id=?",
        (decision, session["user_id"], gid)
    )
    if decision == "approved":
        row = db.execute("SELECT student_id FROM GraduationApplication WHERE graduation_app_id=?", (gid,)).fetchone()
        if row:
            db.execute("UPDATE User SET status='graduated' WHERE user_id=?", (row["student_id"],))
    db.commit()
    db.close()
    return jsonify({"msg": f"Graduation application {decision}."})

@app.route("/api/registrar/warning", methods=["POST"])
def api_issue_warning():
    if session.get("role") != "registrar":
        return jsonify({"error": "Forbidden"}), 403
    data   = request.get_json()
    uid    = int(data.get("user_id", 0))
    reason = (data.get("reason") or "").strip()
    if not uid or not reason:
        return jsonify({"msg": "User and reason required."}), 400
    db = get_db()
    issue_warning(db, uid, reason, "registrar_manual")
    db.commit()
    db.close()
    return jsonify({"msg": "Warning issued."})

# ─── Apply (public) ──────────────────────────────────────────────────────────

@app.route("/api/apply", methods=["POST"])
def api_apply():
    data     = request.get_json()
    name     = (data.get("name") or "").strip()
    email    = (data.get("email") or "").strip()
    app_type = data.get("role","student")
    justify  = (data.get("statement") or "").strip()
    try:
        gpa = float(data.get("gpa") or 0)
    except ValueError:
        gpa = 0.0
    if not name or not email:
        return jsonify({"error": "Name and email are required."}), 400
    if app_type == "student" and gpa < 3.0:
        return jsonify({"error": "Students require a prior GPA > 3.0 for admission."}), 400
    db = get_db()
    db.execute(
        "INSERT INTO VisitorApplication (applicant_name,email,application_type,prior_gpa,justification) VALUES (?,?,?,?,?)",
        (name, email, app_type, gpa or None, justify)
    )
    db.commit()
    db.close()
    return jsonify({"ok": True})

# ─── Serve React SPA ─────────────────────────────────────────────────────────

@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_react(path):
    if path and os.path.exists(os.path.join(BUILD_DIR, path)):
        return send_from_directory(BUILD_DIR, path)
    index = os.path.join(BUILD_DIR, "index.html")
    if os.path.exists(index):
        return send_from_directory(BUILD_DIR, "index.html")
    return "React app not built. Run: cd client && npm install && npm run build", 503

# ─── Entry ───────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000, debug=False)
