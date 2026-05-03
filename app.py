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
    if not sem:
        return None
    return dict(sem)

def get_current_user_row():
    if "user_id" not in session:
        return None
    db = get_db()
    user = db.execute("SELECT * FROM User WHERE user_id=?", (session["user_id"],)).fetchone()
    db.close()
    return user

def user_dict(u):
    if not u:
        return None
    return {k: u[k] for k in u.keys()}

def recalc_gpa(db, student_id):
    rows = db.execute("""
        SELECT gr.grade_points FROM GradeRecord gr
        JOIN Enrollment e ON gr.enrollment_id=e.enrollment_id
        WHERE e.student_id=?
    """, (student_id,)).fetchall()
    if not rows:
        return 0.0
    return round(sum(r["grade_points"] for r in rows) / len(rows), 3)

def handle_ai(question, user_id, db):
    q = question.lower()
    if "graduation" in q and "requirement" in q:
        return ("To graduate from College0, you must complete all required core courses "
                "(CSC101, CSC201, CSC301, CSC401, MTH101, MTH201, ENG101, CSC499), "
                "maintain a cumulative GPA ≥ 2.0, have 0 active warnings, no outstanding fines, "
                "and submit a graduation application during the grading phase.")
    if "warning" in q:
        return ("Warnings are issued for low GPA (below 2.5) or policy violations. "
                "Each student may accumulate up to 3 warnings before facing suspension or termination. "
                "Earning an Honor removes one active warning from your record.")
    if "phase" in q or "semester" in q:
        return ("Each semester has 5 phases: Setup (admin configures sections), "
                "Registration (students enroll), Running (classes in session), "
                "Grading (instructors post grades, students submit reviews), "
                "and Closed (semester archived).")
    if "review" in q:
        return ("Course reviews are anonymous and can only be submitted during the Grading phase. "
                "Rate your section 1–5 stars and leave optional comments. "
                "Reviews with inappropriate language may be flagged or hidden by the Registrar.")
    if "waitlist" in q:
        return ("If a section is full, you can join the waitlist. "
                "You are automatically enrolled when a seat opens up, in order of your waitlist position.")
    if "fine" in q:
        return ("Outstanding fines must be paid before you can register for new courses or apply for graduation. "
                "Contact the Registrar's office to resolve any fines on your account.")
    if "gpa" in q:
        if user_id:
            st = db.execute("SELECT cumulative_gpa, semester_gpa FROM Student WHERE student_id=?", (user_id,)).fetchone()
            if st:
                return (f"Your cumulative GPA is {st['cumulative_gpa']:.3f} and your semester GPA is "
                        f"{st['semester_gpa']:.3f}. A minimum of 2.0 is required to remain in good standing.")
        return ("GPA is calculated as the average grade points across all completed courses. "
                "Grade scale: A/A+ = 4.0, A- = 3.67, B+ = 3.33, B = 3.0, B- = 2.67, "
                "C+ = 2.33, C = 2.0, D = 1.0, F = 0.0.")
    if "enroll" in q or "register" in q:
        return ("Course enrollment is only available during the Registration phase. "
                "Go to My Courses to browse available sections and enroll. "
                "If a section is full, you can join the waitlist.")
    if "apply" in q or "admission" in q:
        return ("Visit the Apply page to submit a visitor application. "
                "Students need a prior GPA > 3.0 for admission consideration.")
    if "core" in q or "required" in q:
        return ("Core (required) courses: CSC101 (Intro to CS), CSC201 (Data Structures), "
                "CSC301 (Database Systems), CSC401 (Software Engineering), MTH101 (Calculus I), "
                "MTH201 (Discrete Math), ENG101 (English Composition), CSC499 (Capstone Project).")
    if "suspend" in q:
        return ("Suspension occurs after accumulating 3 warnings or a severe academic violation. "
                "A suspended student cannot enroll in courses until the suspension period ends.")
    return ("I can answer questions about College0. Try asking about graduation requirements, "
            "GPA calculation, semester phases, course enrollment, waitlists, warnings, or fines.")

# ─── Auth ───────────────────────────────────────────────────────────────────

@app.route("/api/me")
def api_me():
    user = get_current_user_row()
    if not user:
        return jsonify({"user": None}), 200
    db  = get_db()
    sem = get_active_semester(db)
    db.close()
    return jsonify({"user": user_dict(user), "sem": sem_dict(sem)})

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
    db.close()
    if user and check_password_hash(user["password_hash"], pw):
        session["user_id"] = user["user_id"]
        session["role"]    = user["role"]
        return jsonify({"user": user_dict(user), "sem": sem_dict(sem)})
    return jsonify({"error": "Invalid credentials"}), 401

@app.route("/api/logout", methods=["POST"])
def api_logout():
    session.clear()
    return jsonify({"ok": True})

# ─── Home ───────────────────────────────────────────────────────────────────

@app.route("/api/home")
def api_home():
    db  = get_db()
    sem = get_active_semester(db)
    sid = sem["semester_id"]

    total_students = db.execute("SELECT COUNT(*) as c FROM Student").fetchone()["c"]
    total_faculty  = db.execute("SELECT COUNT(*) as c FROM Instructor").fetchone()["c"]
    total_sections = db.execute("SELECT COUNT(*) as c FROM ClassSection WHERE semester_id=?", (sid,)).fetchone()["c"]
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
        "top_gpa": top_gpa, "sections": sections,
        "sem": sem_dict(sem),
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

    if request.method == "POST":
        data      = request.get_json()
        action    = data.get("action")
        section_id = int(data.get("section_id", 0))
        if sem["phase"] != "registration":
            db.close()
            return jsonify({"msg": f"Registration is closed (Phase: {sem['phase']}). Opens during Registration period."}), 200
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
                    db.commit()
                    db.close()
                    return jsonify({"msg": "Enrolled successfully!"})
                except sqlite3.IntegrityError:
                    db.close()
                    return jsonify({"msg": "Already enrolled in this section."})
        elif action == "drop":
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
        WHERE cs.semester_id=? AND cs.status != 'completed' ORDER BY c.code
    """, (sid,)).fetchall()]

    db.close()
    return jsonify({
        "current_enrollments": current,
        "all_sections": all_sections,
        "enrolled_section_ids": enrolled_ids,
        "waitlisted_ids": waitlisted,
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
    db.execute("INSERT INTO Complaint (filed_by_user_id,target_user_id,complaint_text) VALUES (?,?,?)",
               (uid, int(data["target_user_id"]), data["complaint_text"]))
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
                   gr.letter_grade, gr.grade_points
            FROM Enrollment e
            JOIN User u ON e.student_id=u.user_id
            LEFT JOIN GradeRecord gr ON gr.enrollment_id=e.enrollment_id
            WHERE e.section_id=? AND e.enrollment_status IN ('enrolled','completed')
            ORDER BY u.last_name
        """, (sec["section_id"],)).fetchall()]
        sections_data.append({"section": dict(sec), "students": students})

    db.close()
    return jsonify({"sections_data": sections_data})

@app.route("/api/instructor/grade", methods=["POST"])
def api_grade():
    if session.get("role") != "instructor":
        return jsonify({"error": "Forbidden"}), 403
    data = request.get_json()
    eid  = int(data.get("enrollment_id", 0))
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
        SELECT w.*, u.first_name||' '||u.last_name as user_name
        FROM WarningRecord w JOIN User u ON w.user_id=u.user_id
        WHERE w.active_flag=1 ORDER BY w.issued_at DESC
    """).fetchall()]

    db.close()
    return jsonify({
        "students": students, "applications": applications,
        "complaints": complaints, "grad_apps": grad_apps,
        "all_semesters": all_semesters, "warnings": warnings,
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
    sem = get_active_semester(db)
    db.close()
    return jsonify({"msg": f"Phase updated to {phase}.", "sem": sem_dict(sem)})

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
    status = data.get("status","resolved")
    note   = (data.get("resolution_note") or "").strip()
    db = get_db()
    db.execute("UPDATE Complaint SET status=?, resolution_note=?, resolved_by=? WHERE complaint_id=?",
               (status, note or None, session["user_id"], cid))
    db.commit()
    db.close()
    return jsonify({"msg": f"Complaint marked as {status}."})

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
    db.execute("INSERT INTO WarningRecord (user_id,reason,source_module) VALUES (?,?,'registrar_manual')", (uid, reason))
    db.execute("UPDATE User SET warning_count=warning_count+1 WHERE user_id=?", (uid,))
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
