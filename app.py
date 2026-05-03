from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from werkzeug.security import check_password_hash
from database import get_db, init_db
import sqlite3

app = Flask(__name__)
app.secret_key = "collegeo-secret-2024"

def get_semester_config():
    db = get_db()
    cfg = db.execute("SELECT * FROM semester_config WHERE id=1").fetchone()
    db.close()
    return cfg

def get_current_user():
    if "user_id" not in session:
        return None
    db = get_db()
    user = db.execute("SELECT * FROM users WHERE user_id=?", (session["user_id"],)).fetchone()
    db.close()
    return user

def get_course_ratings(db):
    rows = db.execute("""
        SELECT course_id, AVG(rating) as avg_rating, COUNT(*) as cnt
        FROM reviews GROUP BY course_id
    """).fetchall()
    return {r["course_id"]: {"avg": round(r["avg_rating"], 1), "cnt": r["cnt"]} for r in rows}

def compute_student_gpa(db, student_id):
    rows = db.execute(
        "SELECT grade_points FROM enrollments WHERE student_id=? AND grade_points IS NOT NULL",
        (student_id,)
    ).fetchall()
    if not rows:
        return 0.0
    return round(sum(r["grade_points"] for r in rows) / len(rows), 2)

@app.route("/")
def home():
    cfg = get_semester_config()
    user = get_current_user()
    db = get_db()

    total_students = db.execute("SELECT COUNT(*) as c FROM students").fetchone()["c"]
    total_courses  = db.execute("SELECT COUNT(*) as c FROM courses").fetchone()["c"]
    total_faculty  = db.execute("SELECT COUNT(*) as c FROM users WHERE role='instructor'").fetchone()["c"]

    gpas = db.execute("SELECT gpa FROM students").fetchall()
    campus_gpa = round(sum(r["gpa"] for r in gpas) / len(gpas), 2) if gpas else 0.0

    ratings = get_course_ratings(db)
    courses  = db.execute("SELECT * FROM courses ORDER BY code").fetchall()
    courses_list = []
    for c in courses:
        enrolled = db.execute(
            "SELECT COUNT(*) as n FROM enrollments WHERE course_id=? AND semester=?",
            (c["code"], cfg["current_semester"])
        ).fetchone()["n"]
        r = ratings.get(c["code"])
        courses_list.append({
            "code": c["code"],
            "name": c["name"],
            "instructor_id": c["instructor_id"],
            "time_slot": c["time_slot"],
            "enrolled": enrolled,
            "max_enrolled": c["max_enrolled"],
            "is_core": c["is_core"],
            "status": c["status"],
            "avg_rating": r["avg"] if r else None,
            "rating_count": r["cnt"] if r else 0,
        })

    rated = sorted([c for c in courses_list if c["avg_rating"]], key=lambda x: -x["avg_rating"])
    top_rated  = rated[:3]
    needs_imp  = sorted([c for c in courses_list if c["avg_rating"]], key=lambda x: x["avg_rating"])[:3]

    top_gpa_students = db.execute("""
        SELECT u.name, u.user_id, s.gpa
        FROM students s JOIN users u ON s.user_id = u.user_id
        ORDER BY s.gpa DESC LIMIT 4
    """).fetchall()

    db.close()
    return render_template("home.html",
        cfg=cfg, user=user,
        total_students=total_students, total_courses=total_courses,
        total_faculty=total_faculty, campus_gpa=campus_gpa,
        courses=courses_list, top_rated=top_rated,
        needs_imp=needs_imp, top_gpa_students=top_gpa_students,
    )

@app.route("/login", methods=["POST"])
def login():
    uid = request.form.get("user_id", "").strip()
    pw  = request.form.get("password", "").strip()
    db  = get_db()
    user = db.execute("SELECT * FROM users WHERE user_id=?", (uid,)).fetchone()
    db.close()
    if user and check_password_hash(user["password"], pw):
        session["user_id"] = user["user_id"]
        session["role"]    = user["role"]
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
    cfg  = get_semester_config()
    user = get_current_user()
    success = False
    error   = None
    if request.method == "POST":
        name      = request.form.get("name", "").strip()
        email     = request.form.get("email", "").strip()
        role      = request.form.get("role", "student")
        gpa_str   = request.form.get("gpa", "0").strip()
        statement = request.form.get("statement", "").strip()
        try:
            gpa = float(gpa_str)
        except ValueError:
            gpa = 0.0
        if role == "student" and gpa < 3.0:
            error = "Students require GPA > 3.0 for admission."
        elif not name or not email:
            error = "Please fill in all required fields."
        else:
            db = get_db()
            db.execute(
                "INSERT INTO applications (name,email,role,gpa,statement) VALUES (?,?,?,?,?)",
                (name, email, role, gpa, statement)
            )
            db.commit()
            db.close()
            success = True
    return render_template("apply.html", cfg=cfg, user=user, success=success, error=error)

@app.route("/dashboard")
def dashboard():
    if session.get("role") != "student":
        return redirect(url_for("home"))
    cfg  = get_semester_config()
    user = get_current_user()
    db   = get_db()
    st   = db.execute("SELECT * FROM students WHERE user_id=?", (user["user_id"],)).fetchone()
    enrolled = db.execute(
        "SELECT COUNT(*) as n FROM enrollments WHERE student_id=? AND semester=?",
        (user["user_id"], cfg["current_semester"])
    ).fetchone()["n"]
    completed = db.execute(
        "SELECT COUNT(*) as n FROM enrollments WHERE student_id=? AND grade IS NOT NULL",
        (user["user_id"],)
    ).fetchone()["n"]
    db.close()
    return render_template("dashboard.html",
        cfg=cfg, user=user, st=st,
        enrolled=enrolled, completed=completed
    )

@app.route("/my-courses", methods=["GET", "POST"])
def my_courses():
    if session.get("role") != "student":
        return redirect(url_for("home"))
    cfg  = get_semester_config()
    user = get_current_user()
    db   = get_db()
    msg  = None

    if request.method == "POST":
        action    = request.form.get("action")
        course_id = request.form.get("course_id")
        if cfg["phase"] != "Registration":
            msg = f"Registration is closed (Phase: {cfg['phase']}). Registrations open during the Registration period."
        elif action == "enroll":
            try:
                db.execute(
                    "INSERT INTO enrollments (student_id,course_id,semester) VALUES (?,?,?)",
                    (user["user_id"], course_id, cfg["current_semester"])
                )
                db.commit()
            except sqlite3.IntegrityError:
                msg = "You are already enrolled in this course."
        elif action == "drop":
            db.execute(
                "DELETE FROM enrollments WHERE student_id=? AND course_id=? AND semester=?",
                (user["user_id"], course_id, cfg["current_semester"])
            )
            db.commit()

    current_enrollments = db.execute("""
        SELECT e.*, c.name as course_name, c.time_slot, c.instructor_id
        FROM enrollments e JOIN courses c ON e.course_id=c.code
        WHERE e.student_id=? AND e.semester=?
    """, (user["user_id"], cfg["current_semester"])).fetchall()

    all_courses = db.execute("SELECT * FROM courses ORDER BY code").fetchall()
    enrolled_ids = {e["course_id"] for e in current_enrollments}
    db.close()

    if not msg and cfg["phase"] != "Registration":
        msg = f"Registration is closed (Phase: {cfg['phase']}). Registrations open during the Registration period."

    return render_template("my_courses.html",
        cfg=cfg, user=user,
        current_enrollments=current_enrollments,
        all_courses=all_courses,
        enrolled_ids=enrolled_ids,
        msg=msg
    )

@app.route("/transcript")
def transcript():
    if session.get("role") != "student":
        return redirect(url_for("home"))
    cfg  = get_semester_config()
    user = get_current_user()
    db   = get_db()
    st   = db.execute("SELECT * FROM students WHERE user_id=?", (user["user_id"],)).fetchone()

    history = db.execute("""
        SELECT e.*, c.name as course_name
        FROM enrollments e JOIN courses c ON e.course_id=c.code
        WHERE e.student_id=? AND e.grade IS NOT NULL
        ORDER BY e.semester, c.code
    """, (user["user_id"],)).fetchall()

    db.close()
    return render_template("transcript.html",
        cfg=cfg, user=user, st=st, history=history
    )

@app.route("/reviews", methods=["GET", "POST"])
def reviews():
    if session.get("role") != "student":
        return redirect(url_for("home"))
    cfg  = get_semester_config()
    user = get_current_user()
    db   = get_db()
    msg  = None
    tab  = request.args.get("tab", "review")

    if request.method == "POST":
        form_type = request.form.get("form_type")
        if form_type == "review":
            course_id   = request.form.get("course_id")
            rating      = request.form.get("rating", 5)
            review_text = request.form.get("review_text", "")
            if cfg["phase"] != "Grading":
                msg = "Reviews are only available during the Grading period."
            elif course_id:
                db.execute(
                    "INSERT INTO reviews (student_id,course_id,rating,review_text,semester) VALUES (?,?,?,?,?)",
                    (user["user_id"], course_id, int(rating), review_text, cfg["current_semester"])
                )
                db.commit()
                msg = "Review submitted successfully!"
        elif form_type == "graduation":
            message = request.form.get("message", "")
            db.execute(
                "INSERT INTO graduation_requests (student_id,message) VALUES (?,?)",
                (user["user_id"], message)
            )
            db.commit()
            msg = "Graduation request submitted!"
        elif form_type == "complaint":
            subject     = request.form.get("subject", "")
            description = request.form.get("description", "")
            db.execute(
                "INSERT INTO complaints (student_id,subject,description) VALUES (?,?,?)",
                (user["user_id"], subject, description)
            )
            db.commit()
            msg = "Complaint submitted successfully!"

    my_courses = db.execute("""
        SELECT e.course_id, c.name FROM enrollments e
        JOIN courses c ON e.course_id=c.code
        WHERE e.student_id=?
    """, (user["user_id"],)).fetchall()

    db.close()
    return render_template("reviews.html",
        cfg=cfg, user=user, msg=msg,
        my_courses=my_courses, tab=tab
    )

@app.route("/ai-assistant", methods=["GET", "POST"])
def ai_assistant():
    cfg  = get_semester_config()
    user = get_current_user()
    answer = None
    question = ""

    if request.method == "POST":
        question = request.form.get("question", "").strip()
        answer   = handle_ai_question(question, user)

    return render_template("ai_assistant.html",
        cfg=cfg, user=user, question=question, answer=answer
    )

def handle_ai_question(q, user):
    q_lower = q.lower()
    if "graduation" in q_lower and "requirement" in q_lower:
        return ("To graduate from Collegeo, you must: complete all required Core courses "
                "(CSC 10100, 10200, 21700, 22000), maintain a cumulative GPA of at least 2.0, "
                "have 0 active warnings, and submit a graduation request during the Grading phase.")
    if "warning" in q_lower:
        return ("Warnings are issued when a student fails to meet academic standards. "
                "Each student may have up to 3 warnings. Earning an Honor removes one warning. "
                "3 warnings results in academic probation.")
    if "semester" in q_lower or "phase" in q_lower:
        return ("Each academic year has multiple semesters. Each semester goes through 3 phases: "
                "Setup (admin configures courses), Registration (students enroll), "
                "and Grading (grades and reviews are submitted).")
    if "review" in q_lower and "work" in q_lower:
        return ("Course reviews are anonymous and can only be submitted during the Grading phase. "
                "Ratings are 1–5 stars. Reviews help improve course quality and inform future students.")
    if "gpa" in q_lower:
        if user and session.get("role") == "student":
            db = get_db()
            st = db.execute("SELECT gpa FROM students WHERE user_id=?", (user["user_id"],)).fetchone()
            db.close()
            if st:
                return f"Your current cumulative GPA is {st['gpa']:.2f}. GPA is calculated as the average of all grade points from completed courses."
        return ("GPA is calculated as the average of all grade points earned. "
                "A+ = 4.0, A = 4.0, A- = 3.7, B+ = 3.3, B = 3.0, B- = 2.7, C+ = 2.3, C = 2.0. "
                "A GPA of 2.0 or above is required to remain in good standing.")
    if "enroll" in q_lower or "register" in q_lower:
        return ("Course enrollment is only available during the Registration phase. "
                "Navigate to My Courses to see available courses and enroll. "
                "Core courses are required for all students.")
    if "apply" in q_lower or "admission" in q_lower:
        return ("To apply to Collegeo, visit the Apply page. Students must have a GPA > 3.0 "
                "for admission. Instructors can also apply. All applications are reviewed by the Registrar.")
    if "core" in q_lower or "required" in q_lower:
        return ("Core courses are mandatory for all students: CSC 10100 (Intro to CS), "
                "CSC 10200 (Discrete Math), CSC 21700 (Data Structures), CSC 22000 (Algorithms). "
                "These must be completed before graduation.")
    return ("I can answer questions about Collegeo's academic system. Try asking about "
            "graduation requirements, warnings, GPA calculation, semester phases, "
            "course enrollment, or how reviews work.")

@app.route("/instructor")
def instructor():
    if session.get("role") != "instructor":
        return redirect(url_for("home"))
    cfg  = get_semester_config()
    user = get_current_user()
    db   = get_db()
    my_courses = db.execute(
        "SELECT * FROM courses WHERE instructor_id=? ORDER BY code",
        (user["user_id"],)
    ).fetchall()

    courses_data = []
    for c in my_courses:
        enrolled = db.execute(
            "SELECT COUNT(*) as n FROM enrollments WHERE course_id=? AND semester=?",
            (c["code"], cfg["current_semester"])
        ).fetchone()["n"]
        students = db.execute("""
            SELECT u.user_id, u.name, e.grade, e.grade_points
            FROM enrollments e JOIN users u ON e.student_id=u.user_id
            WHERE e.course_id=? AND e.semester=?
        """, (c["code"], cfg["current_semester"])).fetchall()
        courses_data.append({
            "code": c["code"], "name": c["name"],
            "time_slot": c["time_slot"], "enrolled": enrolled,
            "max_enrolled": c["max_enrolled"], "students": students
        })
    db.close()
    return render_template("instructor.html",
        cfg=cfg, user=user, courses_data=courses_data
    )

@app.route("/instructor/grade", methods=["POST"])
def grade_student():
    if session.get("role") != "instructor":
        return redirect(url_for("home"))
    cfg       = get_semester_config()
    student_id = request.form.get("student_id")
    course_id  = request.form.get("course_id")
    grade      = request.form.get("grade", "").strip().upper()

    GRADE_MAP = {
        "A+": 4.0, "A": 4.0, "A-": 3.7,
        "B+": 3.3, "B": 3.0, "B-": 2.7,
        "C+": 2.3, "C": 2.0, "C-": 1.7,
        "D+": 1.3, "D": 1.0, "F": 0.0
    }
    points = GRADE_MAP.get(grade)
    if grade and points is not None:
        db = get_db()
        db.execute(
            "UPDATE enrollments SET grade=?, grade_points=? WHERE student_id=? AND course_id=? AND semester=?",
            (grade, points, student_id, course_id, cfg["current_semester"])
        )
        new_gpa = compute_student_gpa(db, student_id)
        db.execute("UPDATE students SET gpa=? WHERE user_id=?", (new_gpa, student_id))
        db.commit()
        db.close()
    return redirect(url_for("instructor"))

@app.route("/registrar")
def registrar():
    if session.get("role") != "registrar":
        return redirect(url_for("home"))
    cfg  = get_semester_config()
    user = get_current_user()
    db   = get_db()
    students    = db.execute("SELECT u.*, s.gpa, s.warnings FROM users u JOIN students s ON u.user_id=s.user_id ORDER BY u.user_id").fetchall()
    applications = db.execute("SELECT * FROM applications ORDER BY created_at DESC").fetchall()
    complaints   = db.execute("SELECT c.*, u.name FROM complaints c JOIN users u ON c.student_id=u.user_id ORDER BY c.created_at DESC").fetchall()
    grad_requests = db.execute("SELECT g.*, u.name FROM graduation_requests g JOIN users u ON g.student_id=u.user_id ORDER BY g.created_at DESC").fetchall()
    db.close()
    return render_template("registrar.html",
        cfg=cfg, user=user,
        students=students, applications=applications,
        complaints=complaints, grad_requests=grad_requests
    )

@app.route("/registrar/phase", methods=["POST"])
def set_phase():
    if session.get("role") != "registrar":
        return redirect(url_for("home"))
    phase = request.form.get("phase")
    if phase in ("Setup", "Registration", "Grading"):
        db = get_db()
        db.execute("UPDATE semester_config SET phase=? WHERE id=1", (phase,))
        db.commit()
        db.close()
    return redirect(url_for("registrar"))

@app.route("/registrar/semester", methods=["POST"])
def advance_semester():
    if session.get("role") != "registrar":
        return redirect(url_for("home"))
    db = get_db()
    db.execute("UPDATE semester_config SET current_semester=current_semester+1, phase='Setup' WHERE id=1")
    db.commit()
    db.close()
    return redirect(url_for("registrar"))

@app.route("/registrar/application/<int:app_id>", methods=["POST"])
def decide_application(app_id):
    if session.get("role") != "registrar":
        return redirect(url_for("home"))
    decision = request.form.get("decision")
    if decision in ("Approved", "Rejected"):
        db = get_db()
        db.execute("UPDATE applications SET status=? WHERE id=?", (decision, app_id))
        db.commit()
        db.close()
    return redirect(url_for("registrar"))

if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000, debug=False)
