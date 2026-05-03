from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import check_password_hash
from database import get_db, init_db
import sqlite3

app = Flask(__name__)
app.secret_key = "collegeo-secret-2024"

# ─── Helpers ────────────────────────────────────────────────────────────────

def get_active_semester(db):
    sem = db.execute(
        "SELECT * FROM Semester WHERE phase != 'closed' ORDER BY semester_id DESC LIMIT 1"
    ).fetchone()
    if not sem:
        sem = db.execute("SELECT * FROM Semester ORDER BY semester_id DESC LIMIT 1").fetchone()
    return sem

def get_current_user():
    if "user_id" not in session:
        return None
    db = get_db()
    user = db.execute("SELECT * FROM User WHERE user_id=?", (session["user_id"],)).fetchone()
    db.close()
    return user

def get_course_ratings(db):
    rows = db.execute("""
        SELECT c.course_id, c.code, c.title,
               AVG(r.rating) as avg_rating, COUNT(r.review_id) as cnt
        FROM Review r
        JOIN ClassSection cs ON r.section_id = cs.section_id
        JOIN Course c ON cs.course_id = c.course_id
        WHERE r.visibility_status = 'visible'
        GROUP BY c.course_id
    """).fetchall()
    return {r["course_id"]: {"avg": round(r["avg_rating"],1), "cnt": r["cnt"],
                              "code": r["code"], "title": r["title"]} for r in rows}

def recalc_student_gpa(db, student_id):
    rows = db.execute("""
        SELECT gr.grade_points FROM GradeRecord gr
        JOIN Enrollment e ON gr.enrollment_id = e.enrollment_id
        WHERE e.student_id = ?
    """, (student_id,)).fetchall()
    if not rows:
        return 0.0
    return round(sum(r["grade_points"] for r in rows) / len(rows), 3)

# ─── Public Routes ───────────────────────────────────────────────────────────

@app.route("/")
def home():
    user = get_current_user()
    db   = get_db()
    sem  = get_active_semester(db)

    total_students = db.execute("SELECT COUNT(*) as c FROM Student").fetchone()["c"]
    total_faculty  = db.execute("SELECT COUNT(*) as c FROM Instructor").fetchone()["c"]
    total_sections = db.execute(
        "SELECT COUNT(*) as c FROM ClassSection WHERE semester_id=?", (sem["semester_id"],)
    ).fetchone()["c"]

    gpas = db.execute("SELECT cumulative_gpa FROM Student").fetchall()
    campus_gpa = round(sum(r["cumulative_gpa"] for r in gpas) / len(gpas), 2) if gpas else 0.0

    ratings    = get_course_ratings(db)
    rated_list = sorted(ratings.values(), key=lambda x: -x["avg"])
    top_rated  = rated_list[:3]
    needs_imp  = sorted(ratings.values(), key=lambda x: x["avg"])[:3]

    top_gpa = db.execute("""
        SELECT u.first_name||' '||u.last_name as name, u.user_id, s.cumulative_gpa
        FROM Student s JOIN User u ON s.student_id=u.user_id
        ORDER BY s.cumulative_gpa DESC LIMIT 4
    """).fetchall()

    sections = db.execute("""
        SELECT cs.section_id, cs.schedule_slot, cs.room, cs.capacity, cs.status,
               c.code, c.title, c.is_core, c.credit_hours,
               u.first_name||' '||u.last_name as instructor_name,
               (SELECT COUNT(*) FROM Enrollment e WHERE e.section_id=cs.section_id
                AND e.enrollment_status IN ('enrolled','completed')) as enrolled_count
        FROM ClassSection cs
        JOIN Course c ON cs.course_id=c.course_id
        JOIN User u ON cs.instructor_id=u.user_id
        WHERE cs.semester_id=?
        ORDER BY c.code
    """, (sem["semester_id"],)).fetchall()

    db.close()
    return render_template("home.html",
        sem=sem, user=user,
        total_students=total_students, total_faculty=total_faculty,
        total_sections=total_sections, campus_gpa=campus_gpa,
        top_rated=top_rated, needs_imp=needs_imp,
        top_gpa=top_gpa, sections=sections,
    )

@app.route("/login", methods=["POST"])
def login():
    email = request.form.get("email","").strip().lower()
    pw    = request.form.get("password","").strip()
    db    = get_db()
    user  = db.execute("SELECT * FROM User WHERE LOWER(email)=?", (email,)).fetchone()
    db.close()
    if user and check_password_hash(user["password_hash"], pw):
        session["user_id"] = user["user_id"]
        session["role"]    = user["role"]
        session["name"]    = f"{user['first_name']} {user['last_name']}"
        if user["role"] == "student":
            return redirect(url_for("dashboard"))
        elif user["role"] == "instructor":
            return redirect(url_for("instructor"))
        else:
            return redirect(url_for("registrar"))
    return redirect(url_for("home") + "?login_error=1")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))

@app.route("/apply", methods=["GET", "POST"])
def apply():
    db   = get_db()
    sem  = get_active_semester(db)
    user = get_current_user()
    success, error = False, None

    if request.method == "POST":
        name      = request.form.get("name","").strip()
        email     = request.form.get("email","").strip()
        app_type  = request.form.get("role","student")
        justify   = request.form.get("statement","").strip()
        try:
            gpa = float(request.form.get("gpa","0") or 0)
        except ValueError:
            gpa = 0.0
        if app_type == "student" and gpa < 3.0:
            error = "Students require a prior GPA > 3.0 for admission."
        elif not name or not email:
            error = "Please fill in all required fields."
        else:
            db.execute(
                "INSERT INTO VisitorApplication (applicant_name,email,application_type,prior_gpa,justification) VALUES (?,?,?,?,?)",
                (name, email, app_type, gpa or None, justify)
            )
            db.commit()
            success = True
    db.close()
    return render_template("apply.html", sem=sem, user=user, success=success, error=error)

# ─── Student Routes ──────────────────────────────────────────────────────────

@app.route("/dashboard")
def dashboard():
    if session.get("role") != "student":
        return redirect(url_for("home"))
    user = get_current_user()
    db   = get_db()
    sem  = get_active_semester(db)
    st   = db.execute("SELECT * FROM Student WHERE student_id=?", (user["user_id"],)).fetchone()

    enrolled = db.execute("""
        SELECT COUNT(*) as n FROM Enrollment e
        JOIN ClassSection cs ON e.section_id=cs.section_id
        WHERE e.student_id=? AND cs.semester_id=? AND e.enrollment_status='enrolled'
    """, (user["user_id"], sem["semester_id"])).fetchone()["n"]

    completed = db.execute(
        "SELECT COUNT(*) as n FROM Enrollment WHERE student_id=? AND enrollment_status='completed'",
        (user["user_id"],)
    ).fetchone()["n"]

    db.close()
    return render_template("dashboard.html",
        sem=sem, user=user, st=st, enrolled=enrolled, completed=completed
    )

@app.route("/my-courses", methods=["GET","POST"])
def my_courses():
    if session.get("role") != "student":
        return redirect(url_for("home"))
    user = get_current_user()
    db   = get_db()
    sem  = get_active_semester(db)
    msg  = None

    if request.method == "POST":
        action     = request.form.get("action")
        section_id = int(request.form.get("section_id",0))
        if sem["phase"] != "registration":
            msg = f"Registration is closed (Phase: {sem['phase'].title()}). Registrations open during the Registration period."
        elif action == "enroll":
            sec = db.execute("SELECT * FROM ClassSection WHERE section_id=?", (section_id,)).fetchone()
            if sec and sec["status"] == "full":
                pos = (db.execute("SELECT MAX(position) as p FROM WaitlistEntry WHERE section_id=?",
                                  (section_id,)).fetchone()["p"] or 0) + 1
                try:
                    db.execute("INSERT INTO WaitlistEntry (student_id,section_id,position) VALUES (?,?,?)",
                               (user["user_id"], section_id, pos))
                    db.commit()
                    msg = "Section is full — you have been added to the waitlist."
                except sqlite3.IntegrityError:
                    msg = "You are already on the waitlist for this section."
            else:
                try:
                    db.execute("INSERT INTO Enrollment (student_id,section_id,enrollment_status) VALUES (?,?,?)",
                               (user["user_id"], section_id, "enrolled"))
                    db.commit()
                except sqlite3.IntegrityError:
                    msg = "You are already enrolled in this section."
        elif action == "drop":
            db.execute(
                "DELETE FROM Enrollment WHERE student_id=? AND section_id=? AND enrollment_status='enrolled'",
                (user["user_id"], section_id)
            )
            db.commit()

    current_enrollments = db.execute("""
        SELECT e.enrollment_id, e.section_id, e.enrollment_status,
               c.code, c.title, c.credit_hours,
               cs.schedule_slot, cs.room,
               u.first_name||' '||u.last_name as instructor_name
        FROM Enrollment e
        JOIN ClassSection cs ON e.section_id=cs.section_id
        JOIN Course c ON cs.course_id=c.course_id
        JOIN User u ON cs.instructor_id=u.user_id
        WHERE e.student_id=? AND cs.semester_id=? AND e.enrollment_status='enrolled'
    """, (user["user_id"], sem["semester_id"])).fetchall()

    enrolled_section_ids = {e["section_id"] for e in current_enrollments}

    waitlisted = db.execute(
        "SELECT section_id FROM WaitlistEntry WHERE student_id=?", (user["user_id"],)
    ).fetchall()
    waitlisted_ids = {w["section_id"] for w in waitlisted}

    all_sections = db.execute("""
        SELECT cs.section_id, cs.schedule_slot, cs.room, cs.capacity, cs.status,
               c.code, c.title, c.is_core, c.credit_hours,
               u.first_name||' '||u.last_name as instructor_name,
               (SELECT COUNT(*) FROM Enrollment e2 WHERE e2.section_id=cs.section_id
                AND e2.enrollment_status IN ('enrolled','completed')) as enrolled_count
        FROM ClassSection cs
        JOIN Course c ON cs.course_id=c.course_id
        JOIN User u ON cs.instructor_id=u.user_id
        WHERE cs.semester_id=? AND cs.status != 'completed'
        ORDER BY c.code
    """, (sem["semester_id"],)).fetchall()

    db.close()
    if not msg and sem["phase"] != "registration":
        msg = f"Registration is closed (Phase: {sem['phase'].title()}). Registrations open during the Registration period."

    return render_template("my_courses.html",
        sem=sem, user=user, msg=msg,
        current_enrollments=current_enrollments,
        all_sections=all_sections,
        enrolled_section_ids=enrolled_section_ids,
        waitlisted_ids=waitlisted_ids,
    )

@app.route("/transcript")
def transcript():
    if session.get("role") != "student":
        return redirect(url_for("home"))
    user = get_current_user()
    db   = get_db()
    sem  = get_active_semester(db)
    st   = db.execute("SELECT * FROM Student WHERE student_id=?", (user["user_id"],)).fetchone()

    history = db.execute("""
        SELECT gr.letter_grade, gr.grade_points, gr.posted_at,
               c.code, c.title, c.credit_hours,
               s.term_name, s.year
        FROM GradeRecord gr
        JOIN Enrollment e ON gr.enrollment_id=e.enrollment_id
        JOIN ClassSection cs ON e.section_id=cs.section_id
        JOIN Course c ON cs.course_id=c.course_id
        JOIN Semester s ON cs.semester_id=s.semester_id
        WHERE e.student_id=?
        ORDER BY s.semester_id, c.code
    """, (user["user_id"],)).fetchall()

    db.close()
    return render_template("transcript.html", sem=sem, user=user, st=st, history=history)

@app.route("/reviews", methods=["GET","POST"])
def reviews():
    if session.get("role") != "student":
        return redirect(url_for("home"))
    user = get_current_user()
    db   = get_db()
    sem  = get_active_semester(db)
    msg  = None
    tab  = request.args.get("tab","review")

    if request.method == "POST":
        form_type = request.form.get("form_type")

        if form_type == "review":
            section_id  = request.form.get("section_id")
            rating      = int(request.form.get("rating",5))
            review_text = request.form.get("review_text","")
            if sem["phase"] != "grading":
                msg = f"Reviews are only available during the Grading phase. Current phase: {sem['phase'].title()}."
            elif section_id:
                try:
                    db.execute(
                        "INSERT INTO Review (section_id,student_id,rating,review_text) VALUES (?,?,?,?)",
                        (int(section_id), user["user_id"], rating, review_text)
                    )
                    db.commit()
                    msg = "Review submitted successfully!"
                except sqlite3.IntegrityError:
                    msg = "You have already submitted a review for this section."

        elif form_type == "graduation":
            existing = db.execute(
                "SELECT graduation_app_id FROM GraduationApplication WHERE student_id=? AND decision_status='pending'",
                (user["user_id"],)
            ).fetchone()
            if existing:
                msg = "You already have a pending graduation application."
            else:
                db.execute(
                    "INSERT INTO GraduationApplication (student_id) VALUES (?)",
                    (user["user_id"],)
                )
                db.commit()
                msg = "Graduation application submitted! The Registrar will review it."

        elif form_type == "complaint":
            target_id      = request.form.get("target_user_id")
            complaint_text = request.form.get("complaint_text","").strip()
            if not complaint_text:
                msg = "Please describe your complaint."
            elif not target_id:
                msg = "Please select who your complaint is about."
            else:
                db.execute(
                    "INSERT INTO Complaint (filed_by_user_id,target_user_id,complaint_text) VALUES (?,?,?)",
                    (user["user_id"], int(target_id), complaint_text)
                )
                db.commit()
                msg = "Complaint submitted and will be reviewed confidentially."

    my_sections = db.execute("""
        SELECT cs.section_id, c.code, c.title, s.term_name, s.year
        FROM Enrollment e
        JOIN ClassSection cs ON e.section_id=cs.section_id
        JOIN Course c ON cs.course_id=c.course_id
        JOIN Semester s ON cs.semester_id=s.semester_id
        WHERE e.student_id=?
        ORDER BY s.semester_id DESC, c.code
    """, (user["user_id"],)).fetchall()

    potential_targets = db.execute("""
        SELECT user_id, first_name||' '||last_name as name, role
        FROM User WHERE user_id != ? AND role IN ('instructor','registrar','student')
        ORDER BY role, first_name
    """, (user["user_id"],)).fetchall()

    db.close()
    return render_template("reviews.html",
        sem=sem, user=user, msg=msg, tab=tab,
        my_sections=my_sections, potential_targets=potential_targets,
    )

@app.route("/ai-assistant", methods=["GET","POST"])
def ai_assistant():
    user     = get_current_user()
    db       = get_db()
    sem      = get_active_semester(db)
    answer   = None
    question = ""

    if request.method == "POST":
        question = request.form.get("question","").strip()
        answer   = handle_ai_question(question, user, db)
        db.execute(
            "INSERT INTO AIQuery (user_id,question_text,answer_text,answer_source) VALUES (?,?,?,?)",
            (user["user_id"] if user else None, question, answer, "vectordb")
        )
        db.commit()

    db.close()
    return render_template("ai_assistant.html", sem=sem, user=user, question=question, answer=answer)

def handle_ai_question(q, user, db):
    q_lower = q.lower()
    if "graduation" in q_lower and "requirement" in q_lower:
        return ("To graduate from College0, you must complete all required core courses "
                "(CSC101, CSC201, CSC301, CSC401, MTH101, MTH201, ENG101, CSC499), "
                "maintain a cumulative GPA ≥ 2.0, have 0 active warnings, no outstanding fines, "
                "and submit a graduation application during the grading phase.")
    if "warning" in q_lower:
        return ("Warnings are issued for low GPA (below 2.5) or policy violations. "
                "Each student may accumulate up to 3 warnings before facing suspension or termination. "
                "Earning an Honor removes one active warning from your record.")
    if "phase" in q_lower or "semester" in q_lower:
        return ("Each semester has 5 phases: Setup (admin configures sections), "
                "Registration (students enroll), Running (classes in session), "
                "Grading (instructors post grades, students submit reviews), "
                "and Closed (semester archived).")
    if "review" in q_lower and "work" in q_lower:
        return ("Course reviews are anonymous and can only be submitted during the Grading phase. "
                "Rate your section 1–5 stars and leave optional comments. "
                "Reviews with inappropriate language may be flagged or hidden by the Registrar.")
    if "waitlist" in q_lower:
        return ("If a section is full, you can join the waitlist. "
                "You are automatically enrolled when a seat opens up, in order of your waitlist position. "
                "Check My Courses to see your waitlist status.")
    if "fine" in q_lower:
        return ("Outstanding fines must be paid before you can register for new courses or apply for graduation. "
                "Contact the Registrar's office to resolve any fines on your account.")
    if "gpa" in q_lower:
        if user and session.get("role") == "student":
            st = db.execute("SELECT cumulative_gpa, semester_gpa FROM Student WHERE student_id=?",
                            (user["user_id"],)).fetchone()
            if st:
                return (f"Your cumulative GPA is {st['cumulative_gpa']:.3f} and your semester GPA is "
                        f"{st['semester_gpa']:.3f}. A minimum of 2.0 is required to remain in good standing.")
        return ("GPA is calculated as the average grade points across all completed courses. "
                "Grade scale: A/A+ = 4.0, A- = 3.67, B+ = 3.33, B = 3.0, B- = 2.67, "
                "C+ = 2.33, C = 2.0, D = 1.0, F = 0.0.")
    if "enroll" in q_lower or "register" in q_lower:
        return ("Course enrollment is only available during the Registration phase. "
                "Go to My Courses to browse available sections and enroll. "
                "If a section is full, you can join the waitlist.")
    if "apply" in q_lower or "admission" in q_lower:
        return ("Visit the Apply page to submit a visitor application. "
                "Students need a prior GPA > 3.0 for admission consideration. "
                "All applications are reviewed by the Registrar.")
    if "core" in q_lower or "required" in q_lower:
        return ("Core (required) courses for all students: "
                "CSC101 (Intro to CS), CSC201 (Data Structures), CSC301 (Database Systems), "
                "CSC401 (Software Engineering), MTH101 (Calculus I), MTH201 (Discrete Math), "
                "ENG101 (English Composition), CSC499 (Capstone Project).")
    if "suspend" in q_lower:
        return ("Suspension occurs after accumulating 3 warnings or a severe academic violation. "
                "A suspended student cannot enroll in courses until the suspension period ends. "
                "Contact the Registrar to understand the terms of your suspension.")
    return ("I can answer questions about College0. Try asking about graduation requirements, "
            "GPA calculation, semester phases, course enrollment, waitlists, warnings, or fines.")

# ─── Instructor Routes ───────────────────────────────────────────────────────

@app.route("/instructor")
def instructor():
    if session.get("role") != "instructor":
        return redirect(url_for("home"))
    user = get_current_user()
    db   = get_db()
    sem  = get_active_semester(db)

    my_sections = db.execute("""
        SELECT cs.section_id, cs.schedule_slot, cs.room, cs.capacity, cs.status,
               c.code, c.title, c.credit_hours,
               (SELECT COUNT(*) FROM Enrollment e WHERE e.section_id=cs.section_id
                AND e.enrollment_status IN ('enrolled','completed')) as enrolled_count
        FROM ClassSection cs
        JOIN Course c ON cs.course_id=c.course_id
        WHERE cs.instructor_id=? AND cs.semester_id=?
        ORDER BY c.code
    """, (user["user_id"], sem["semester_id"])).fetchall()

    sections_data = []
    for sec in my_sections:
        students = db.execute("""
            SELECT e.enrollment_id, e.student_id, e.enrollment_status,
                   u.first_name||' '||u.last_name as name,
                   gr.letter_grade, gr.grade_points
            FROM Enrollment e
            JOIN User u ON e.student_id=u.user_id
            LEFT JOIN GradeRecord gr ON gr.enrollment_id=e.enrollment_id
            WHERE e.section_id=? AND e.enrollment_status IN ('enrolled','completed')
            ORDER BY u.last_name
        """, (sec["section_id"],)).fetchall()
        sections_data.append({"section": sec, "students": students})

    db.close()
    return render_template("instructor.html", sem=sem, user=user, sections_data=sections_data)

@app.route("/instructor/grade", methods=["POST"])
def grade_student():
    if session.get("role") != "instructor":
        return redirect(url_for("home"))
    enrollment_id = int(request.form.get("enrollment_id",0))
    letter        = request.form.get("grade","").strip().upper()
    GRADE_MAP = {
        "A+":4.0,"A":4.0,"A-":3.67,
        "B+":3.33,"B":3.0,"B-":2.67,
        "C+":2.33,"C":2.0,"C-":1.67,
        "D+":1.33,"D":1.0,"F":0.0
    }
    points = GRADE_MAP.get(letter)
    if letter and points is not None:
        db = get_db()
        db.execute(
            "INSERT INTO GradeRecord (enrollment_id,letter_grade,grade_points) VALUES (?,?,?) "
            "ON CONFLICT(enrollment_id) DO UPDATE SET letter_grade=excluded.letter_grade, grade_points=excluded.grade_points",
            (enrollment_id, letter, points)
        )
        enr = db.execute("SELECT student_id FROM Enrollment WHERE enrollment_id=?", (enrollment_id,)).fetchone()
        if enr:
            new_gpa = recalc_student_gpa(db, enr["student_id"])
            db.execute("UPDATE Student SET cumulative_gpa=? WHERE student_id=?",
                       (new_gpa, enr["student_id"]))
        db.commit()
        db.close()
    return redirect(url_for("instructor"))

# ─── Registrar Routes ────────────────────────────────────────────────────────

@app.route("/registrar")
def registrar():
    if session.get("role") != "registrar":
        return redirect(url_for("home"))
    user = get_current_user()
    db   = get_db()
    sem  = get_active_semester(db)

    students = db.execute("""
        SELECT u.user_id, u.first_name||' '||u.last_name as name,
               u.email, u.status, u.warning_count,
               s.cumulative_gpa, s.semester_gpa, s.honor_count, s.fine_due
        FROM Student s JOIN User u ON s.student_id=u.user_id
        ORDER BY u.last_name
    """).fetchall()

    applications = db.execute(
        "SELECT * FROM VisitorApplication ORDER BY application_id DESC"
    ).fetchall()

    complaints = db.execute("""
        SELECT c.*, uf.first_name||' '||uf.last_name as filer_name,
               ut.first_name||' '||ut.last_name as target_name
        FROM Complaint c
        JOIN User uf ON c.filed_by_user_id=uf.user_id
        JOIN User ut ON c.target_user_id=ut.user_id
        ORDER BY c.complaint_id DESC
    """).fetchall()

    grad_apps = db.execute("""
        SELECT ga.*, u.first_name||' '||u.last_name as student_name,
               s.cumulative_gpa
        FROM GraduationApplication ga
        JOIN User u ON ga.student_id=u.user_id
        JOIN Student s ON ga.student_id=s.student_id
        ORDER BY ga.graduation_app_id DESC
    """).fetchall()

    all_semesters = db.execute("SELECT * FROM Semester ORDER BY semester_id").fetchall()
    warnings      = db.execute("""
        SELECT w.*, u.first_name||' '||u.last_name as user_name
        FROM WarningRecord w JOIN User u ON w.user_id=u.user_id
        WHERE w.active_flag=1 ORDER BY w.issued_at DESC
    """).fetchall()

    db.close()
    return render_template("registrar.html",
        sem=sem, user=user,
        students=students, applications=applications,
        complaints=complaints, grad_apps=grad_apps,
        all_semesters=all_semesters, warnings=warnings,
    )

@app.route("/registrar/phase", methods=["POST"])
def set_phase():
    if session.get("role") != "registrar":
        return redirect(url_for("home"))
    semester_id = int(request.form.get("semester_id",0))
    phase       = request.form.get("phase","")
    valid_phases = ("setup","registration","running","grading","closed")
    if phase in valid_phases:
        db = get_db()
        db.execute("UPDATE Semester SET phase=? WHERE semester_id=?", (phase, semester_id))
        db.commit()
        db.close()
    return redirect(url_for("registrar"))

@app.route("/registrar/application/<int:app_id>", methods=["POST"])
def decide_application(app_id):
    if session.get("role") != "registrar":
        return redirect(url_for("home"))
    decision = request.form.get("decision","")
    if decision in ("approved","rejected"):
        db = get_db()
        db.execute(
            "UPDATE VisitorApplication SET status=?, reviewed_by=?, reviewed_at=CURRENT_TIMESTAMP WHERE application_id=?",
            (decision, session["user_id"], app_id)
        )
        db.commit()
        db.close()
    return redirect(url_for("registrar"))

@app.route("/registrar/complaint/<int:cid>", methods=["POST"])
def resolve_complaint(cid):
    if session.get("role") != "registrar":
        return redirect(url_for("home"))
    status = request.form.get("status","resolved")
    note   = request.form.get("resolution_note","").strip()
    db = get_db()
    db.execute(
        "UPDATE Complaint SET status=?, resolution_note=?, resolved_by=? WHERE complaint_id=?",
        (status, note or None, session["user_id"], cid)
    )
    db.commit()
    db.close()
    return redirect(url_for("registrar"))

@app.route("/registrar/graduation/<int:gid>", methods=["POST"])
def decide_graduation(gid):
    if session.get("role") != "registrar":
        return redirect(url_for("home"))
    decision = request.form.get("decision","")
    if decision in ("approved","rejected"):
        db = get_db()
        db.execute(
            "UPDATE GraduationApplication SET decision_status=?, reviewed_by=?, reviewed_at=CURRENT_TIMESTAMP WHERE graduation_app_id=?",
            (decision, session["user_id"], gid)
        )
        if decision == "approved":
            student_id = db.execute(
                "SELECT student_id FROM GraduationApplication WHERE graduation_app_id=?", (gid,)
            ).fetchone()["student_id"]
            db.execute("UPDATE User SET status='graduated' WHERE user_id=?", (student_id,))
        db.commit()
        db.close()
    return redirect(url_for("registrar"))

@app.route("/registrar/warning", methods=["POST"])
def issue_warning():
    if session.get("role") != "registrar":
        return redirect(url_for("home"))
    user_id = int(request.form.get("user_id",0))
    reason  = request.form.get("reason","").strip()
    if user_id and reason:
        db = get_db()
        db.execute(
            "INSERT INTO WarningRecord (user_id,reason,source_module) VALUES (?,?,'registrar_manual')",
            (user_id, reason)
        )
        db.execute("UPDATE User SET warning_count=warning_count+1 WHERE user_id=?", (user_id,))
        db.commit()
        db.close()
    return redirect(url_for("registrar"))

# ─── Entry Point ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000, debug=False)
