"""
app.py — College0 / CUNY0 backend.

Rewritten from scratch to match the React frontend's contract:
  • All responses are JSON under /api/*
  • String IDs everywhere (S101, I01, REG01, course codes like "CSC 22000")
  • JWT auth in Authorization header (matches AuthContext.js)
  • Phase labels in CAPS: SETUP / REGISTRATION / RUNNING / GRADING / CLOSED
  • Response shape matches what each page in Pages.jsx reads from r.data

To run locally:
    pip install -r requirements.txt
    python app.py
Then start the React dev server in ../Frontend (it proxies to localhost:5000).

To deploy:
    gunicorn app:app  (the wsgi callable is `app`)
"""

import os
import re
import secrets
import time
from datetime import datetime, timedelta
from functools import wraps

import jwt
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from werkzeug.security import check_password_hash, generate_password_hash

import database
from database import get_db


# ─── App setup ──────────────────────────────────────────────────────────────

app = Flask(__name__, static_folder=None)

# Secret key — MUST be set via env in production. Falls back to a random
# value in dev so a misconfigured prod deploy doesn't silently use a known key.
SECRET_KEY = os.environ.get("COLLEGE0_SECRET")
if not SECRET_KEY:
    SECRET_KEY = secrets.token_hex(32)
    app.logger.warning("COLLEGE0_SECRET not set; using ephemeral random key. "
                       "Tokens will be invalidated on every restart.")

JWT_ALGO = "HS256"
JWT_TTL_HOURS = 24

# CORS — open during dev. In prod, set COLLEGE0_CORS_ORIGINS to a comma-list.
_cors_origins = os.environ.get("COLLEGE0_CORS_ORIGINS", "*")
CORS(app, resources={r"/api/*": {"origins": _cors_origins}})

# Wire in the database (creates tables + seeds if needed).
database.init_app(app)


# ─── Auth helpers ───────────────────────────────────────────────────────────

def _make_token(user_id: str) -> str:
    payload = {
        "sub": user_id,
        "iat": int(time.time()),
        "exp": int(time.time()) + JWT_TTL_HOURS * 3600,
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=JWT_ALGO)


def _decode_token(token: str):
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[JWT_ALGO])
    except jwt.PyJWTError:
        return None


def _current_user():
    """Look up the authenticated user from the Authorization header.
    Returns the users-row dict, or None if not authenticated.
    """
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return None
    payload = _decode_token(auth[7:])
    if not payload:
        return None
    db = get_db()
    row = db.execute("SELECT * FROM users WHERE user_id=?", (payload["sub"],)).fetchone()
    return dict(row) if row else None


def auth_required(*roles):
    """Decorator: require JWT and (optionally) a specific role."""
    def deco(fn):
        @wraps(fn)
        def wrapper(*a, **kw):
            user = _current_user()
            if not user:
                return jsonify({"error": "Authentication required."}), 401
            if roles and user["role"] not in roles:
                return jsonify({"error": "Forbidden."}), 403
            request.user = user  # stash for the handler
            return fn(*a, **kw)
        return wrapper
    return deco


# ─── Domain helpers ─────────────────────────────────────────────────────────

PHASE_LABELS = {
    "SETUP":        "Class Setup",
    "REGISTRATION": "Registration",
    "RUNNING":      "Classes Running",
    "GRADING":      "Grading",
    "CLOSED":       "Semester Closed",
}

GRADE_POINTS = {
    "A+": 4.0, "A": 4.0, "A-": 3.7,
    "B+": 3.3, "B": 3.0, "B-": 2.7,
    "C+": 2.3, "C": 2.0, "C-": 1.7,
    "D":  1.0, "F":  0.0,
}

CORE_REQUIRED = ("CSC 10100", "CSC 10200", "CSC 21700", "CSC 22000")


def _state(db):
    """Return the singleton semester_state row as a dict."""
    return dict(db.execute("SELECT * FROM semester_state WHERE id=1").fetchone())


def _gen_id(db, table: str, id_col: str, prefix: str, width: int = 3) -> str:
    """Generate the next id of the form PREFIX###, e.g. C001, A042."""
    rows = db.execute(f"SELECT {id_col} FROM {table} WHERE {id_col} LIKE ?",
                      (prefix + "%",)).fetchall()
    nums = []
    for r in rows:
        m = re.match(rf"{re.escape(prefix)}(\d+)$", r[id_col])
        if m:
            nums.append(int(m.group(1)))
    return f"{prefix}{(max(nums) + 1 if nums else 1):0{width}d}"


def _course_to_dict(row, enrolled_count=None, rating=None):
    """Shape a courses row the way the frontend expects."""
    out = {
        "code":         row["code"],
        "name":         row["name"],
        "instructorId": row["instructor_id"],
        "timeSlot":     row["time_slot"],
        "capacity":     row["capacity"],
        "isCore":       bool(row["is_core"]),
        "cancelled":    bool(row["cancelled"]),
    }
    if enrolled_count is not None:
        out["enrolled"] = enrolled_count
    if rating is not None:
        out["rating"] = rating
    return out


def _enrolled_count(db, code, semester):
    return db.execute(
        "SELECT COUNT(*) AS c FROM enrollments "
        "WHERE course_code=? AND semester=? AND status IN ('enrolled','completed')",
        (code, semester),
    ).fetchone()["c"]


def _course_rating(db, code):
    row = db.execute(
        "SELECT AVG(rating) AS r FROM reviews WHERE course_code=? AND flagged=0",
        (code,),
    ).fetchone()
    return round(row["r"], 1) if row["r"] is not None else None


def _student_completed_codes(db, student_id):
    rows = db.execute(
        "SELECT DISTINCT course_code FROM enrollments "
        "WHERE student_id=? AND status='completed'",
        (student_id,),
    ).fetchall()
    return [r["course_code"] for r in rows]


def _recompute_gpa(db, student_id):
    rows = db.execute(
        "SELECT grade FROM enrollments WHERE student_id=? AND grade IS NOT NULL",
        (student_id,),
    ).fetchall()
    if not rows:
        return 0.0
    pts = [GRADE_POINTS.get(r["grade"], 0.0) for r in rows]
    return round(sum(pts) / len(pts), 2)


def _scan_taboo(db, text: str) -> bool:
    """Return True if any taboo word appears in `text` (case-insensitive)."""
    words = [r["word"].lower() for r in db.execute("SELECT word FROM taboo_words").fetchall()]
    if not words:
        return False
    lt = text.lower()
    return any(w in lt for w in words)


def _issue_warning(db, user_id, reason):
    """Record a warning and update the cached counter; cascade to suspension."""
    db.execute("INSERT INTO warnings (user_id,reason) VALUES (?,?)", (user_id, reason))
    role = db.execute("SELECT role FROM users WHERE user_id=?", (user_id,)).fetchone()
    if not role:
        return
    if role["role"] == "Student":
        db.execute(
            "UPDATE students SET warnings = warnings + 1, "
            "suspended = CASE WHEN warnings + 1 >= 3 THEN 1 ELSE suspended END "
            "WHERE user_id=?",
            (user_id,),
        )
    elif role["role"] == "Instructor":
        db.execute(
            "UPDATE instructors SET warnings = warnings + 1, "
            "suspended = CASE WHEN warnings + 1 >= 3 THEN 1 ELSE suspended END "
            "WHERE user_id=?",
            (user_id,),
        )


# ─── Public ────────────────────────────────────────────────────────────────

@app.route("/api/public", methods=["GET"])
def public_home():
    """Home page payload — no auth required."""
    db = get_db()
    state = _state(db)

    student_count = db.execute("SELECT COUNT(*) AS c FROM students").fetchone()["c"]
    instructor_count = db.execute("SELECT COUNT(*) AS c FROM instructors").fetchone()["c"]

    courses_rows = db.execute("SELECT * FROM courses ORDER BY code").fetchall()
    courses = []
    active_count = 0
    for c in courses_rows:
        cnt = _enrolled_count(db, c["code"], state["semester"])
        rating = _course_rating(db, c["code"])
        courses.append(_course_to_dict(c, enrolled_count=cnt, rating=rating))
        if not c["cancelled"]:
            active_count += 1

    rated = [c for c in courses if c.get("rating") is not None]
    top_rated = sorted(rated, key=lambda c: -c["rating"])[:3]
    lowest_rated = sorted(rated, key=lambda c: c["rating"])[:3]

    avg_gpa_row = db.execute("SELECT AVG(gpa) AS g FROM students").fetchone()
    avg_gpa = round(avg_gpa_row["g"], 2) if avg_gpa_row["g"] is not None else 0.0

    top_gpa_rows = db.execute(
        "SELECT u.user_id, u.name, s.gpa "
        "FROM students s JOIN users u ON u.user_id = s.user_id "
        "ORDER BY s.gpa DESC LIMIT 5"
    ).fetchall()
    top_gpa = [{"userId": r["user_id"], "name": r["name"], "gpa": r["gpa"]} for r in top_gpa_rows]

    return jsonify({
        "phaseLabel":          PHASE_LABELS[state["phase"]],
        "phase":               state["phase"],
        "semester":            state["semester"],
        "studentCount":        student_count,
        "instructorCount":     instructor_count,
        "activeCoursesCount":  active_count,
        "avgGpa":              avg_gpa,
        "courses":             courses,
        "topRated":            top_rated,
        "lowestRated":         lowest_rated,
        "topGpa":              top_gpa,
    })


# ─── Auth ──────────────────────────────────────────────────────────────────

@app.route("/api/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    user_id = (data.get("userId") or "").strip()
    password = data.get("password") or ""

    if not user_id or not password:
        return jsonify({"error": "User ID and password are required."}), 400

    db = get_db()
    row = db.execute(
        "SELECT * FROM users WHERE user_id = ? COLLATE NOCASE",
        (user_id,),
    ).fetchone()
    if not row or not check_password_hash(row["password_hash"], password):
        return jsonify({"error": "Invalid credentials."}), 401

    token = _make_token(row["user_id"])
    return jsonify({
        "token": token,
        "firstLogin": bool(row["must_change_pw"]),
        "user": {
            "userId": row["user_id"],
            "name":   row["name"],
            "email":  row["email"],
            "role":   row["role"],
        },
    })


@app.route("/api/change-password", methods=["POST"])
@auth_required()
def change_password():
    data = request.get_json(silent=True) or {}
    new_pw = data.get("newPassword") or ""
    if len(new_pw) < 4:
        return jsonify({"error": "Password must be at least 4 characters."}), 400
    db = get_db()
    db.execute(
        "UPDATE users SET password_hash=?, must_change_pw=0 WHERE user_id=?",
        (generate_password_hash(new_pw), request.user["user_id"]),
    )
    db.commit()
    return jsonify({"ok": True})


# ─── Apply (public) ────────────────────────────────────────────────────────

@app.route("/api/apply", methods=["POST"])
def apply():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip()
    role = data.get("role") or "Student"
    notes = (data.get("notes") or "").strip()
    try:
        gpa = float(data.get("gpa") or 0)
    except (TypeError, ValueError):
        gpa = 0.0

    if not name or not email:
        return jsonify({"error": "Name and email are required."}), 400
    if role not in ("Student", "Instructor"):
        return jsonify({"error": "Invalid role."}), 400

    db = get_db()
    app_id = _gen_id(db, "applications", "app_id", "A")
    db.execute(
        "INSERT INTO applications (app_id,name,email,role,gpa,notes) "
        "VALUES (?,?,?,?,?,?)",
        (app_id, name, email, role, gpa if role == "Student" else None, notes),
    )
    db.commit()
    return jsonify({"appId": app_id})


# ─── Student ───────────────────────────────────────────────────────────────

@app.route("/api/student/me", methods=["GET"])
@auth_required("Student")
def student_me():
    db = get_db()
    uid = request.user["user_id"]
    state = _state(db)
    s = dict(db.execute("SELECT * FROM students WHERE user_id=?", (uid,)).fetchone())

    enrolled = [r["course_code"] for r in db.execute(
        "SELECT course_code FROM enrollments "
        "WHERE student_id=? AND semester=? AND status='enrolled'",
        (uid, state["semester"])).fetchall()]

    completed = _student_completed_codes(db, uid)

    return jsonify({
        "userId":              uid,
        "name":                request.user["name"],
        "gpa":                 s["gpa"],
        "warnings":            s["warnings"],
        "honorCount":          s["honor_count"],
        "suspended":           bool(s["suspended"]),
        "graduated":           bool(s["graduated"]),
        "terminated":          bool(s["terminated"]),
        "semestersCompleted":  s["semesters_completed"],
        "currentEnrollment":   enrolled,
        "completedCourses":    completed,
        "phase":               state["phase"],
    })


@app.route("/api/student/courses", methods=["GET"])
@auth_required("Student")
def student_courses():
    db = get_db()
    uid = request.user["user_id"]
    state = _state(db)
    sem = state["semester"]

    enrolled_codes = [r["course_code"] for r in db.execute(
        "SELECT course_code FROM enrollments "
        "WHERE student_id=? AND semester=? AND status='enrolled'",
        (uid, sem)).fetchall()]

    enrolled = []
    for code in enrolled_codes:
        c = db.execute("SELECT * FROM courses WHERE code=?", (code,)).fetchone()
        if c:
            enrolled.append(_course_to_dict(c))

    all_courses = db.execute("SELECT * FROM courses WHERE cancelled=0 ORDER BY code").fetchall()
    available = []
    for c in all_courses:
        if c["code"] in enrolled_codes:
            continue
        enrolled_list = [r["student_id"] for r in db.execute(
            "SELECT student_id FROM enrollments "
            "WHERE course_code=? AND semester=? AND status='enrolled'",
            (c["code"], sem)).fetchall()]
        d = _course_to_dict(c)
        d["enrolled"] = enrolled_list
        available.append(d)

    return jsonify({
        "phase":               state["phase"],
        "specialRegistration": bool(state["special_registration"]),
        "enrolled":            enrolled,
        "available":           available,
    })


@app.route("/api/student/register", methods=["POST"])
@auth_required("Student")
def student_register():
    data = request.get_json(silent=True) or {}
    code = (data.get("courseCode") or "").strip()
    db = get_db()
    state = _state(db)

    if state["phase"] not in ("REGISTRATION",) and not (
        state["phase"] == "RUNNING" and state["special_registration"]
    ):
        return jsonify({"ok": False, "msg": f"Registration is closed (phase: {state['phase']})."})

    s = db.execute("SELECT * FROM students WHERE user_id=?", (request.user["user_id"],)).fetchone()
    if s and (s["suspended"] or s["terminated"] or s["graduated"]):
        return jsonify({"ok": False, "msg": "Your account is not eligible to register."})

    course = db.execute("SELECT * FROM courses WHERE code=?", (code,)).fetchone()
    if not course:
        return jsonify({"ok": False, "msg": f"Course {code} not found."})
    if course["cancelled"]:
        return jsonify({"ok": False, "msg": f"Course {code} has been cancelled."})

    uid = request.user["user_id"]
    sem = state["semester"]

    # Already enrolled this semester?
    existing = db.execute(
        "SELECT status FROM enrollments WHERE student_id=? AND course_code=? AND semester=?",
        (uid, code, sem)).fetchone()
    if existing and existing["status"] in ("enrolled", "waitlist"):
        return jsonify({"ok": False, "msg": "Already registered or on waitlist for this course."})

    # Already passed it before? Don't let them re-enroll.
    passed = db.execute(
        "SELECT 1 FROM enrollments WHERE student_id=? AND course_code=? AND status='completed' "
        "AND (grade IS NOT NULL AND grade <> 'F')",
        (uid, code)).fetchone()
    if passed:
        return jsonify({"ok": False, "msg": "You have already completed this course."})

    # Enrollment count rule: at most 4 enrolled this semester
    cur_count = db.execute(
        "SELECT COUNT(*) AS c FROM enrollments WHERE student_id=? AND semester=? AND status='enrolled'",
        (uid, sem)).fetchone()["c"]
    if cur_count >= 4:
        return jsonify({"ok": False, "msg": "Maximum of 4 courses per semester."})

    enrolled_now = _enrolled_count(db, code, sem)
    if enrolled_now >= course["capacity"]:
        # join waitlist instead
        pos_row = db.execute(
            "SELECT COALESCE(MAX(position), 0) AS p FROM waitlist WHERE course_code=?", (code,)
        ).fetchone()
        new_pos = pos_row["p"] + 1
        db.execute(
            "INSERT OR REPLACE INTO waitlist (course_code,student_id,position) VALUES (?,?,?)",
            (code, uid, new_pos))
        db.commit()
        return jsonify({"ok": True, "msg": f"Course is full — added to waitlist (position {new_pos})."})

    db.execute(
        "INSERT OR REPLACE INTO enrollments (student_id,course_code,semester,status) "
        "VALUES (?,?,?,?)",
        (uid, code, sem, "enrolled"))
    db.commit()
    return jsonify({"ok": True, "msg": f"Successfully registered for {code}."})


@app.route("/api/student/drop", methods=["POST"])
@auth_required("Student")
def student_drop():
    data = request.get_json(silent=True) or {}
    code = (data.get("courseCode") or "").strip()
    db = get_db()
    state = _state(db)
    if state["phase"] != "REGISTRATION":
        return jsonify({"ok": False, "msg": "Courses can only be dropped during the Registration phase."})
    db.execute(
        "DELETE FROM enrollments WHERE student_id=? AND course_code=? AND semester=? AND status='enrolled'",
        (request.user["user_id"], code, state["semester"]))
    db.commit()
    return jsonify({"ok": True, "msg": f"Dropped {code}."})


@app.route("/api/student/grades", methods=["GET"])
@auth_required("Student")
def student_grades():
    db = get_db()
    uid = request.user["user_id"]
    s = dict(db.execute("SELECT * FROM students WHERE user_id=?", (uid,)).fetchone())

    rows = db.execute("""
        SELECT e.course_code, c.name AS course_name, e.grade, e.semester
        FROM enrollments e JOIN courses c ON c.code = e.course_code
        WHERE e.student_id=? AND e.grade IS NOT NULL
        ORDER BY e.semester
    """, (uid,)).fetchall()
    grades = [{
        "courseCode": r["course_code"],
        "courseName": r["course_name"],
        "grade":      r["grade"],
        "semester":   r["semester"],
    } for r in rows]

    return jsonify({
        "gpa":         s["gpa"],
        "warnings":    s["warnings"],
        "honorCount":  s["honor_count"],
        "grades":      grades,
    })


@app.route("/api/student/review", methods=["POST"])
@auth_required("Student")
def student_review():
    data = request.get_json(silent=True) or {}
    code = (data.get("courseCode") or "").strip()
    text = (data.get("text") or "").strip()
    rating = int(data.get("rating") or 5)
    if not code or not text:
        return jsonify({"ok": False, "msg": "Course and review text are required."})
    if rating < 1 or rating > 5:
        return jsonify({"ok": False, "msg": "Rating must be 1–5."})

    db = get_db()
    state = _state(db)
    if state["phase"] != "GRADING":
        return jsonify({"ok": False, "msg": "Reviews can only be submitted during the Grading phase."})

    uid = request.user["user_id"]
    sem = state["semester"]

    enr = db.execute(
        "SELECT grade FROM enrollments WHERE student_id=? AND course_code=? AND semester=?",
        (uid, code, sem)).fetchone()
    if not enr:
        return jsonify({"ok": False, "msg": "You are not enrolled in this course."})
    if enr["grade"] is not None:
        return jsonify({"ok": False, "msg": "Reviews must be submitted before your grade is posted."})

    flagged = 1 if _scan_taboo(db, text) else 0
    db.execute(
        "INSERT INTO reviews (course_code,student_id,semester,rating,text,flagged) "
        "VALUES (?,?,?,?,?,?)",
        (code, uid, sem, rating, text, flagged))
    db.commit()
    msg = "Review submitted." + (" (flagged for taboo language)" if flagged else "")
    return jsonify({"ok": True, "msg": msg})


@app.route("/api/student/graduate", methods=["POST"])
@auth_required("Student")
def student_graduate():
    db = get_db()
    uid = request.user["user_id"]
    s = dict(db.execute("SELECT * FROM students WHERE user_id=?", (uid,)).fetchone())

    completed = set(_student_completed_codes(db, uid))
    total = len(completed)
    core_done = sum(1 for c in CORE_REQUIRED if c in completed)
    eligible = total >= 8 and core_done == 4 and s["gpa"] >= 2.0

    if eligible:
        db.execute("UPDATE students SET graduated=1 WHERE user_id=?", (uid,))
        db.commit()
        return jsonify({"ok": True, "msg": "🎓 Congratulations, you have graduated!"})

    # Reckless application — issue a warning
    _issue_warning(db, uid, "Reckless graduation application (requirements not met).")
    db.commit()
    missing = []
    if total < 8:
        missing.append(f"{8 - total} more course(s)")
    if core_done < 4:
        missing.append(f"{4 - core_done} core course(s)")
    if s["gpa"] < 2.0:
        missing.append(f"GPA below 2.0 (currently {s['gpa']})")
    return jsonify({"ok": False, "msg": "Requirements not met: " + "; ".join(missing) +
                                       ". A warning has been issued for the reckless application."})


@app.route("/api/student/complaint", methods=["POST"])
@auth_required("Student")
def student_complaint():
    data = request.get_json(silent=True) or {}
    against = (data.get("againstId") or "").strip()
    desc = (data.get("description") or "").strip()
    if not against or not desc:
        return jsonify({"error": "Both target ID and description are required."}), 400

    db = get_db()
    target = db.execute("SELECT role FROM users WHERE user_id=?", (against,)).fetchone()
    if not target:
        return jsonify({"error": f"User {against} not found."}), 404

    cid = _gen_id(db, "complaints", "complaint_id", "C")
    ctype = "student_vs_instructor" if target["role"] == "Instructor" else "student_vs_student"
    db.execute(
        "INSERT INTO complaints (complaint_id,from_id,against_id,type,description) "
        "VALUES (?,?,?,?,?)",
        (cid, request.user["user_id"], against, ctype, desc))
    db.commit()
    return jsonify({"complaintId": cid})


# ─── Instructor ────────────────────────────────────────────────────────────

@app.route("/api/instructor/me", methods=["GET"])
@auth_required("Instructor")
def instructor_me():
    db = get_db()
    uid = request.user["user_id"]
    state = _state(db)
    inst = dict(db.execute("SELECT * FROM instructors WHERE user_id=?", (uid,)).fetchone())

    course_rows = db.execute(
        "SELECT * FROM courses WHERE instructor_id=? ORDER BY code", (uid,)).fetchall()
    courses = []
    for c in course_rows:
        sem = state["semester"]
        # Enrolled students with grades
        students = []
        student_rows = db.execute("""
            SELECT u.user_id, u.name, s.gpa, s.warnings, e.grade
            FROM enrollments e
            JOIN users u ON u.user_id = e.student_id
            JOIN students s ON s.user_id = e.student_id
            WHERE e.course_code=? AND e.semester=? AND e.status='enrolled'
            ORDER BY u.name
        """, (c["code"], sem)).fetchall()
        for r in student_rows:
            students.append({
                "userId":   r["user_id"],
                "name":     r["name"],
                "gpa":      r["gpa"],
                "warnings": r["warnings"],
                "grade":    r["grade"],
            })

        wl_rows = db.execute(
            "SELECT student_id FROM waitlist WHERE course_code=? ORDER BY position",
            (c["code"],)).fetchall()
        waitlist = [r["student_id"] for r in wl_rows]

        cd = _course_to_dict(c)
        cd["students"] = students
        cd["enrolled"] = [s["userId"] for s in students]  # so .length works
        cd["waitlist"] = waitlist
        courses.append(cd)

    return jsonify({
        "instructor": {
            "userId":   uid,
            "name":     request.user["name"],
            "warnings": inst["warnings"],
            "suspended": bool(inst["suspended"]),
        },
        "courses": courses,
        "phase":   state["phase"],
    })


@app.route("/api/instructor/grade", methods=["POST"])
@auth_required("Instructor")
def instructor_grade():
    data = request.get_json(silent=True) or {}
    student_id = (data.get("studentId") or "").strip()
    code = (data.get("courseCode") or "").strip()
    grade = (data.get("grade") or "").strip().upper()

    if grade not in GRADE_POINTS:
        return jsonify({"ok": False, "msg": "Invalid grade."})

    db = get_db()
    state = _state(db)
    if state["phase"] != "GRADING":
        return jsonify({"ok": False, "msg": "Grades can only be submitted during the Grading phase."})

    # Verify the instructor owns this course
    course = db.execute("SELECT * FROM courses WHERE code=?", (code,)).fetchone()
    if not course or course["instructor_id"] != request.user["user_id"]:
        return jsonify({"ok": False, "msg": "You don't teach this course."})

    enr = db.execute(
        "SELECT * FROM enrollments WHERE student_id=? AND course_code=? AND semester=?",
        (student_id, code, state["semester"])).fetchone()
    if not enr:
        return jsonify({"ok": False, "msg": "Student is not enrolled in this course."})

    db.execute(
        "UPDATE enrollments SET grade=? WHERE student_id=? AND course_code=? AND semester=?",
        (grade, student_id, code, state["semester"]))
    new_gpa = _recompute_gpa(db, student_id)
    db.execute("UPDATE students SET gpa=? WHERE user_id=?", (new_gpa, student_id))
    db.commit()
    return jsonify({"ok": True, "msg": f"Grade {grade} submitted for {student_id}."})


@app.route("/api/instructor/admit-waitlist", methods=["POST"])
@auth_required("Instructor")
def instructor_admit_waitlist():
    data = request.get_json(silent=True) or {}
    code = (data.get("courseCode") or "").strip()
    db = get_db()
    state = _state(db)

    course = db.execute("SELECT * FROM courses WHERE code=?", (code,)).fetchone()
    if not course or course["instructor_id"] != request.user["user_id"]:
        return jsonify({"ok": False, "msg": "You don't teach this course."})

    next_row = db.execute(
        "SELECT student_id FROM waitlist WHERE course_code=? ORDER BY position LIMIT 1",
        (code,)).fetchone()
    if not next_row:
        return jsonify({"ok": False, "msg": "Waitlist is empty."})

    enrolled = _enrolled_count(db, code, state["semester"])
    if enrolled >= course["capacity"]:
        # Force-admit anyway by bumping capacity by 1 (instructor discretion)
        db.execute("UPDATE courses SET capacity = capacity + 1 WHERE code=?", (code,))

    sid = next_row["student_id"]
    db.execute(
        "INSERT OR REPLACE INTO enrollments (student_id,course_code,semester,status) "
        "VALUES (?,?,?,?)",
        (sid, code, state["semester"], "enrolled"))
    db.execute("DELETE FROM waitlist WHERE course_code=? AND student_id=?", (code, sid))
    db.commit()
    return jsonify({"ok": True, "msg": f"Admitted {sid} from the waitlist."})


@app.route("/api/instructor/complaint", methods=["POST"])
@auth_required("Instructor")
def instructor_complaint():
    data = request.get_json(silent=True) or {}
    against = (data.get("againstId") or "").strip()
    desc = (data.get("description") or "").strip()
    if not against or not desc:
        return jsonify({"error": "Both target ID and description are required."}), 400

    db = get_db()
    target = db.execute("SELECT role FROM users WHERE user_id=?", (against,)).fetchone()
    if not target:
        return jsonify({"error": f"User {against} not found."}), 404
    if target["role"] != "Student":
        return jsonify({"error": "Instructors can only file complaints against students."}), 400

    cid = _gen_id(db, "complaints", "complaint_id", "C")
    db.execute(
        "INSERT INTO complaints (complaint_id,from_id,against_id,type,description) "
        "VALUES (?,?,?,?,?)",
        (cid, request.user["user_id"], against, "instructor_vs_student", desc))
    db.commit()
    return jsonify({"complaintId": cid})


# ─── Registrar ─────────────────────────────────────────────────────────────

@app.route("/api/registrar/overview", methods=["GET"])
@auth_required("Registrar")
def registrar_overview():
    db = get_db()
    state = _state(db)
    student_count = db.execute(
        "SELECT COUNT(*) AS c FROM students WHERE suspended=0 AND terminated=0 AND graduated=0"
    ).fetchone()["c"]
    pending = db.execute(
        "SELECT COUNT(*) AS c FROM applications WHERE status='Pending'"
    ).fetchone()["c"]
    open_complaints = db.execute(
        "SELECT COUNT(*) AS c FROM complaints WHERE resolved=0"
    ).fetchone()["c"]
    active_courses = db.execute(
        "SELECT COUNT(*) AS c FROM courses WHERE cancelled=0"
    ).fetchone()["c"]
    return jsonify({
        "phaseLabel":          PHASE_LABELS[state["phase"]],
        "phase":               state["phase"],
        "semester":            state["semester"],
        "specialRegistration": bool(state["special_registration"]),
        "studentCount":        student_count,
        "pendingApps":         pending,
        "openComplaints":      open_complaints,
        "activeCourses":       active_courses,
    })


@app.route("/api/registrar/advance-phase", methods=["POST"])
@auth_required("Registrar")
def registrar_advance_phase():
    """Cycle SETUP → REGISTRATION → RUNNING → GRADING → CLOSED → SETUP (next sem)."""
    db = get_db()
    state = _state(db)
    order = ["SETUP", "REGISTRATION", "RUNNING", "GRADING", "CLOSED"]
    idx = order.index(state["phase"])

    if state["phase"] == "CLOSED":
        # Roll over to next semester. Mark all enrolled-with-grade as completed,
        # bump semestersCompleted for active students, recompute GPA.
        db.execute("UPDATE enrollments SET status='completed' WHERE status='enrolled' AND grade IS NOT NULL")
        # Drop any ungraded enrollments at semester close (clean slate)
        db.execute("UPDATE enrollments SET status='dropped' WHERE status='enrolled' AND grade IS NULL")
        db.execute("UPDATE students SET semesters_completed = semesters_completed + 1 "
                   "WHERE suspended=0 AND terminated=0 AND graduated=0")
        # Honor roll: students with semester GPA >= 3.7 get an honor (and -1 warning)
        # (Approximated as cumulative GPA threshold for simplicity.)
        for r in db.execute("SELECT user_id, gpa, warnings FROM students").fetchall():
            if r["gpa"] >= 3.7:
                new_warns = max(0, r["warnings"] - 1)
                db.execute(
                    "UPDATE students SET honor_count = honor_count + 1, warnings=? WHERE user_id=?",
                    (new_warns, r["user_id"]))
        db.execute("UPDATE semester_state SET semester = semester + 1, phase='SETUP', "
                   "special_registration=0 WHERE id=1")
        db.commit()
        new_state = _state(db)
        return jsonify({
            "ok": True,
            "msg": f"Semester closed. Now in Semester {new_state['semester']} ({PHASE_LABELS[new_state['phase']]}).",
            "phase": new_state["phase"],
            "semester": new_state["semester"],
        })

    next_phase = order[idx + 1]
    db.execute("UPDATE semester_state SET phase=? WHERE id=1", (next_phase,))
    db.commit()
    return jsonify({
        "ok": True,
        "msg": f"Phase advanced to {PHASE_LABELS[next_phase]}.",
        "phase": next_phase,
    })


@app.route("/api/registrar/close-special-reg", methods=["POST"])
@auth_required("Registrar")
def registrar_close_special_reg():
    db = get_db()
    db.execute("UPDATE semester_state SET special_registration=0 WHERE id=1")
    db.commit()
    return jsonify({"ok": True})


@app.route("/api/registrar/courses", methods=["GET"])
@auth_required("Registrar")
def registrar_courses():
    db = get_db()
    state = _state(db)
    rows = db.execute("SELECT * FROM courses ORDER BY code").fetchall()
    out = []
    for c in rows:
        enrolled_list = [r["student_id"] for r in db.execute(
            "SELECT student_id FROM enrollments "
            "WHERE course_code=? AND semester=? AND status='enrolled'",
            (c["code"], state["semester"])).fetchall()]
        d = _course_to_dict(c)
        d["enrolled"] = enrolled_list
        out.append(d)
    return jsonify(out)


@app.route("/api/registrar/instructors", methods=["GET"])
@auth_required("Registrar")
def registrar_instructors():
    db = get_db()
    rows = db.execute(
        "SELECT u.user_id, u.name FROM users u "
        "JOIN instructors i ON i.user_id = u.user_id "
        "WHERE i.suspended=0 ORDER BY u.name"
    ).fetchall()
    return jsonify([{"userId": r["user_id"], "name": r["name"]} for r in rows])


@app.route("/api/registrar/create-course", methods=["POST"])
@auth_required("Registrar")
def registrar_create_course():
    data = request.get_json(silent=True) or {}
    code = (data.get("code") or "").strip()
    name = (data.get("name") or "").strip()
    instr = (data.get("instructorId") or "").strip()
    slot = (data.get("timeSlot") or "").strip()
    try:
        cap = int(data.get("capacity") or 20)
    except (TypeError, ValueError):
        cap = 20
    is_core = 1 if data.get("isCore") in (True, "true", 1) else 0

    if not code or not name or not instr or not slot:
        return jsonify({"ok": False, "msg": "Code, name, instructor and time slot are required."})
    if cap < 3 or cap > 60:
        return jsonify({"ok": False, "msg": "Capacity must be between 3 and 60."})

    db = get_db()
    if db.execute("SELECT 1 FROM courses WHERE code=?", (code,)).fetchone():
        return jsonify({"ok": False, "msg": f"Course {code} already exists."})
    if not db.execute("SELECT 1 FROM instructors WHERE user_id=?", (instr,)).fetchone():
        return jsonify({"ok": False, "msg": f"Instructor {instr} not found."})

    db.execute(
        "INSERT INTO courses (code,name,instructor_id,time_slot,capacity,is_core) "
        "VALUES (?,?,?,?,?,?)",
        (code, name, instr, slot, cap, is_core))
    db.commit()
    return jsonify({"ok": True, "msg": f"Course {code} created."})


@app.route("/api/registrar/students", methods=["GET"])
@auth_required("Registrar")
def registrar_students():
    db = get_db()
    rows = db.execute("""
        SELECT u.user_id, u.name, s.gpa, s.warnings, s.honor_count,
               s.suspended, s.terminated, s.graduated
        FROM users u JOIN students s ON s.user_id = u.user_id
        ORDER BY u.user_id
    """).fetchall()
    return jsonify([{
        "userId":     r["user_id"],
        "name":       r["name"],
        "gpa":        r["gpa"],
        "warnings":   r["warnings"],
        "honorCount": r["honor_count"],
        "suspended":  bool(r["suspended"]),
        "terminated": bool(r["terminated"]),
        "graduated":  bool(r["graduated"]),
    } for r in rows])


@app.route("/api/registrar/warn", methods=["POST"])
@auth_required("Registrar")
def registrar_warn():
    data = request.get_json(silent=True) or {}
    uid = (data.get("userId") or "").strip()
    reason = (data.get("reason") or "").strip()
    if not uid or not reason:
        return jsonify({"error": "User ID and reason are required."}), 400

    db = get_db()
    target = db.execute("SELECT role FROM users WHERE user_id=?", (uid,)).fetchone()
    if not target:
        return jsonify({"error": f"User {uid} not found."}), 404
    if target["role"] == "Registrar":
        return jsonify({"error": "Cannot warn a registrar."}), 400

    _issue_warning(db, uid, reason)
    db.commit()
    return jsonify({"msg": f"Warning issued to {uid}."})


@app.route("/api/registrar/applications", methods=["GET"])
@auth_required("Registrar")
def registrar_applications():
    db = get_db()
    rows = db.execute("SELECT * FROM applications ORDER BY app_id DESC").fetchall()
    return jsonify([{
        "appId":  r["app_id"],
        "name":   r["name"],
        "email":  r["email"],
        "role":   r["role"],
        "gpa":    r["gpa"] if r["gpa"] is not None else 0.0,
        "notes":  r["notes"] or "",
        "status": r["status"],
    } for r in rows])


@app.route("/api/registrar/approve-app", methods=["POST"])
@auth_required("Registrar")
def registrar_approve_app():
    data = request.get_json(silent=True) or {}
    app_id = (data.get("appId") or "").strip()
    justification = (data.get("justification") or "").strip()

    db = get_db()
    a = db.execute("SELECT * FROM applications WHERE app_id=?", (app_id,)).fetchone()
    if not a:
        return jsonify({"ok": False, "msg": "Application not found."})
    if a["status"] != "Pending":
        return jsonify({"ok": False, "msg": f"Application is already {a['status']}."})
    if a["role"] == "Student" and (a["gpa"] or 0) < 3.0 and not justification:
        return jsonify({"ok": False, "msg": "Justification required for student GPA below 3.0."})

    # Generate a new user account
    if a["role"] == "Student":
        new_uid = _gen_id(db, "users", "user_id", "S", width=3)
    else:
        new_uid = _gen_id(db, "users", "user_id", "I", width=2)

    pw_hash = generate_password_hash(database.DEFAULT_PASSWORD)
    db.execute(
        "INSERT INTO users (user_id,name,email,password_hash,role,must_change_pw) "
        "VALUES (?,?,?,?,?,1)",
        (new_uid, a["name"], a["email"], pw_hash, a["role"]))
    if a["role"] == "Student":
        db.execute(
            "INSERT INTO students (user_id,gpa) VALUES (?,?)",
            (new_uid, a["gpa"] or 0.0))
    else:
        db.execute("INSERT INTO instructors (user_id) VALUES (?)", (new_uid,))

    db.execute(
        "UPDATE applications SET status='Approved', justification=? WHERE app_id=?",
        (justification or None, app_id))
    db.commit()
    return jsonify({
        "ok": True,
        "msg": f"Approved. New {a['role']} account created: {new_uid} (default password: {database.DEFAULT_PASSWORD})."
    })


@app.route("/api/registrar/reject-app", methods=["POST"])
@auth_required("Registrar")
def registrar_reject_app():
    data = request.get_json(silent=True) or {}
    app_id = (data.get("appId") or "").strip()
    db = get_db()
    db.execute("UPDATE applications SET status='Rejected' WHERE app_id=?", (app_id,))
    db.commit()
    return jsonify({"ok": True})


@app.route("/api/registrar/complaints", methods=["GET"])
@auth_required("Registrar")
def registrar_complaints():
    db = get_db()
    rows = db.execute("SELECT * FROM complaints ORDER BY complaint_id DESC").fetchall()
    return jsonify([{
        "complaintId": r["complaint_id"],
        "fromId":      r["from_id"],
        "againstId":   r["against_id"],
        "type":        r["type"],
        "description": r["description"],
        "resolved":    bool(r["resolved"]),
        "resolution":  r["resolution"],
    } for r in rows])


@app.route("/api/registrar/resolve-complaint", methods=["POST"])
@auth_required("Registrar")
def registrar_resolve_complaint():
    data = request.get_json(silent=True) or {}
    cid = (data.get("complaintId") or "").strip()
    action = (data.get("action") or "").strip()  # dismiss | punish | warn_instructor

    if action not in ("dismiss", "punish", "warn_instructor"):
        return jsonify({"ok": False, "msg": "Unknown action."})

    db = get_db()
    c = db.execute("SELECT * FROM complaints WHERE complaint_id=?", (cid,)).fetchone()
    if not c:
        return jsonify({"ok": False, "msg": "Complaint not found."})
    if c["resolved"]:
        return jsonify({"ok": False, "msg": "Complaint already resolved."})

    # Instructor-vs-student complaints cannot be plain-dismissed.
    if c["type"] == "instructor_vs_student" and action == "dismiss":
        return jsonify({"ok": False, "msg": "Instructor complaints require mandatory action — pick punish or warn_instructor."})

    if action == "punish":
        _issue_warning(db, c["against_id"], f"Complaint {cid}: {c['description'][:80]}")
        resolution = f"Punished {c['against_id']}"
    elif action == "warn_instructor":
        if c["type"] != "instructor_vs_student":
            return jsonify({"ok": False, "msg": "warn_instructor only applies to instructor complaints."})
        _issue_warning(db, c["from_id"], f"Unjustified complaint {cid}")
        resolution = f"Warned filer {c['from_id']} (unjustified complaint)"
    else:
        resolution = "Dismissed"

    db.execute(
        "UPDATE complaints SET resolved=1, resolution=? WHERE complaint_id=?",
        (resolution, cid))
    db.commit()
    return jsonify({"ok": True, "msg": f"Complaint {cid} resolved: {resolution}."})


@app.route("/api/registrar/reviews", methods=["GET"])
@auth_required("Registrar")
def registrar_reviews():
    db = get_db()
    rows = db.execute("""
        SELECT r.review_id, r.course_code, r.student_id, r.rating, r.text, r.flagged
        FROM reviews r
        ORDER BY r.review_id DESC
    """).fetchall()
    return jsonify([{
        "reviewId":   r["review_id"],
        "courseCode": r["course_code"],
        "studentId":  r["student_id"],
        "rating":     r["rating"],
        "text":       r["text"],
        "flagged":    bool(r["flagged"]),
    } for r in rows])


@app.route("/api/registrar/taboo", methods=["GET", "POST"])
@auth_required("Registrar")
def registrar_taboo():
    db = get_db()
    if request.method == "GET":
        words = [r["word"] for r in db.execute("SELECT word FROM taboo_words ORDER BY word").fetchall()]
        return jsonify(words)
    data = request.get_json(silent=True) or {}
    word = (data.get("word") or "").strip().lower()
    if not word:
        return jsonify({"error": "Word required."}), 400
    db.execute("INSERT OR IGNORE INTO taboo_words (word) VALUES (?)", (word,))
    # Re-flag existing reviews containing this word
    rows = db.execute("SELECT review_id, text FROM reviews WHERE flagged=0").fetchall()
    for r in rows:
        if word in r["text"].lower():
            db.execute("UPDATE reviews SET flagged=1 WHERE review_id=?", (r["review_id"],))
    db.commit()
    words = [r["word"] for r in db.execute("SELECT word FROM taboo_words ORDER BY word").fetchall()]
    return jsonify({"tabooWords": words})


@app.route("/api/registrar/taboo/<word>", methods=["DELETE"])
@auth_required("Registrar")
def registrar_taboo_delete(word):
    db = get_db()
    db.execute("DELETE FROM taboo_words WHERE word=?", (word.lower(),))
    db.commit()
    words = [r["word"] for r in db.execute("SELECT word FROM taboo_words ORDER BY word").fetchall()]
    return jsonify({"tabooWords": words})


# ─── AI ─────────────────────────────────────────────────────────────────────

KB = [
    (("graduation", "graduate", "requirement"),
     "Graduation requires: 8 completed courses, all 4 core courses (CSC 10100, CSC 10200, CSC 21700, CSC 22000), "
     "and a cumulative GPA of at least 2.0. Apply during any phase from your Reviews & More page."),
    (("warning", "warn"),
     "Students may receive up to 3 active warnings. A 3rd warning suspends the account. "
     "Each Honor (semester GPA ≥ 3.7) removes one warning at semester close."),
    (("phase", "semester"),
     "Each semester cycles through 5 phases: Class Setup → Registration → Classes Running → Grading → Closed. "
     "The registrar advances phases manually."),
    (("review",),
     "Course reviews are anonymous and submitted during the Grading phase, before your grade is posted. "
     "Reviews containing taboo words are auto-flagged for the registrar."),
    (("waitlist",),
     "When a course is full, registering puts you on the waitlist. The instructor admits the next student "
     "manually when capacity allows."),
    (("gpa",),
     "GPA is the average of your grade points across all graded courses. Scale: A/A+=4.0, A-=3.7, B+=3.3, "
     "B=3.0, B-=2.7, C+=2.3, C=2.0, C-=1.7, D=1.0, F=0.0."),
    (("register", "registration", "enroll"),
     "Register for 2–4 courses during the Registration phase. Drop is also allowed in that phase. "
     "If a course is cancelled mid-semester, a Special Registration window opens to pick a replacement."),
    (("apply", "admission", "applic"),
     "Visit the Apply page to submit a visitor application. Students need a prior GPA above 3.0 — "
     "the registrar may approve below-threshold applicants with a written justification."),
    (("complaint",),
     "Both students and instructors can file complaints. Instructor complaints against students "
     "require mandatory registrar action — they cannot simply be dismissed."),
    (("suspend", "suspension"),
     "Three active warnings result in immediate suspension. A suspended student cannot register or graduate."),
]


@app.route("/api/ai", methods=["POST"])
def api_ai():
    data = request.get_json(silent=True) or {}
    q = (data.get("question") or "").lower()
    if not q.strip():
        return jsonify({"answer": "Please ask a question.", "local": True})

    # Personal GPA query (only if logged in)
    user = _current_user()
    if user and user["role"] == "Student" and "my" in q and "gpa" in q:
        db = get_db()
        s = db.execute("SELECT gpa FROM students WHERE user_id=?", (user["user_id"],)).fetchone()
        if s:
            return jsonify({
                "answer": f"Your current cumulative GPA is {s['gpa']:.2f}. "
                          f"A minimum GPA of 2.0 is required to remain in good standing.",
                "local": True,
            })

    for keys, ans in KB:
        if any(k in q for k in keys):
            return jsonify({"answer": ans, "local": True})

    return jsonify({
        "answer": "I can answer questions about graduation requirements, warnings, semester phases, "
                  "course reviews, waitlists, GPA calculation, registration, applications, complaints, "
                  "and suspensions. Try one of those topics — or check with your registrar for anything else.",
        "local": False,
    })


# ─── Static React build (for unified deployment) ────────────────────────────
# In production we serve the React build from the same origin so cookies/CORS
# stay simple. The build output is expected at ../Frontend/build.

FRONTEND_BUILD = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "Frontend", "build")
)


@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_react(path):
    # API routes are handled above; this catch-all only fires for non-/api/* paths.
    if path.startswith("api/"):
        return jsonify({"error": "Not found."}), 404
    if path and os.path.exists(os.path.join(FRONTEND_BUILD, path)):
        return send_from_directory(FRONTEND_BUILD, path)
    index = os.path.join(FRONTEND_BUILD, "index.html")
    if os.path.exists(index):
        return send_from_directory(FRONTEND_BUILD, "index.html")
    return (
        "Frontend build not found. Run `cd ../Frontend && npm install && npm run build`, "
        "or run the React dev server with `npm start` and use http://localhost:3000.",
        503,
    )


# ─── Errors ─────────────────────────────────────────────────────────────────

@app.errorhandler(404)
def not_found(_e):
    if request.path.startswith("/api/"):
        return jsonify({"error": "Not found."}), 404
    # Fall through to SPA
    index = os.path.join(FRONTEND_BUILD, "index.html")
    if os.path.exists(index):
        return send_from_directory(FRONTEND_BUILD, "index.html")
    return jsonify({"error": "Not found."}), 404


@app.errorhandler(500)
def server_error(e):
    app.logger.exception("Server error: %s", e)
    return jsonify({"error": "Internal server error."}), 500


# ─── Entry ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))  # 5001 instead of 5000 (5000 used by macOS Airplay)
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    app.run(host="0.0.0.0", port=port, debug=debug)
