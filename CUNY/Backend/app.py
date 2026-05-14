"""
app.py — College0 / CUNY0 backend.

Matches the React frontend's contract:
  • All responses are JSON under /api/*
  • String IDs everywhere (S101, I01, REG01, course codes like "CSC 22000")
  • JWT auth in Authorization header (matches AuthContext.js)
  • Phase labels in CAPS: SETUP / REGISTRATION / RUNNING / GRADING / CLOSED
  • Response shape matches what each page in Pages.jsx reads from r.data

To run locally:
    pip install -r requirements.txt
    python app.py
Then start the React dev server in ../Frontend (it proxies to localhost:5001).

To deploy:
    gunicorn app:app  (the wsgi callable is `app`)
"""

import json
import math
import os
import re
import secrets
import time
from collections import Counter
from functools import wraps

import jwt
import requests
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from werkzeug.security import check_password_hash, generate_password_hash

import database
from database import get_db, DEFAULT_PASSWORD, _hash as _hash_password


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

# Order of seasons within a year. Roll-over: after Winter <year>, next is Spring <year+1>.
SEASON_ORDER = ("Spring", "Summer", "Fall", "Winter")


def _next_season_year(season: str, year: int):
    """Given a season+year, return the (next_season, next_year)."""
    try:
        i = SEASON_ORDER.index(season)
    except ValueError:
        return ("Spring", year + 1)
    if i == len(SEASON_ORDER) - 1:
        return (SEASON_ORDER[0], year + 1)
    return (SEASON_ORDER[i + 1], year)


def _semester_label(season: str, year) -> str:
    """e.g. 'Spring 2025'."""
    if not season or year is None:
        return "Spring 2025"
    return f"{season} {year}"

GRADE_POINTS = {
    "A+": 4.0, "A": 4.0, "A-": 3.7,
    "B+": 3.3, "B": 3.0, "B-": 2.7,
    "C+": 2.3, "C": 2.0, "C-": 1.7,
    "D":  1.0, "F":  0.0,
}

CORE_REQUIRED = ("CSC 10100", "CSC 10200", "CSC 21700", "CSC 22000")

# Spec: students with up to 3 warnings → suspended for 1 semester + fine
SUSPENSION_FINE = 250.0


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


def _course_to_dict(row, enrolled_count=None, rating=None, instructor_name=None):
    """Shape a courses row the way the frontend expects.

    `instructor_name` is optional — when supplied, it's emitted alongside
    `instructorId` so the UI can render the human-readable name.
    """
    # row["prerequisites"] only exists if the DB has the column (post-migration).
    try:
        prereq_str = row["prerequisites"] or ""
    except (IndexError, KeyError):
        prereq_str = ""
    out = {
        "code":           row["code"],
        "name":           row["name"],
        "instructorId":   row["instructor_id"],
        "instructorName": instructor_name,
        "timeSlot":       row["time_slot"],
        "capacity":       row["capacity"],
        "isCore":         bool(row["is_core"]),
        "cancelled":      bool(row["cancelled"]),
        "prerequisites":  _parse_prereqs(prereq_str),
    }
    if enrolled_count is not None:
        out["enrolled"] = enrolled_count
    if rating is not None:
        out["rating"] = rating
    return out


def _instructor_name(db, instructor_id):
    """Look up an instructor's display name (or None)."""
    if not instructor_id:
        return None
    row = db.execute("SELECT name FROM users WHERE user_id=?", (instructor_id,)).fetchone()
    return row["name"] if row else None


def _enrolled_count(db, code, semester):
    return db.execute(
        "SELECT COUNT(*) AS c FROM enrollments "
        "WHERE course_code=? AND semester=? AND status IN ('enrolled','completed')",
        (code, semester),
    ).fetchone()["c"]


def _course_rating(db, code):
    """Average rating of *visible* reviews only (hidden=0)."""
    row = db.execute(
        "SELECT AVG(rating) AS r FROM reviews WHERE course_code=? AND hidden=0",
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


def _student_passed_codes(db, student_id):
    """Courses the student has completed with at least a C grade.
    Prerequisites must be passed; C-, D, F do not count.
    """
    rows = db.execute(
        "SELECT DISTINCT course_code FROM enrollments "
        "WHERE student_id=? AND status='completed' AND grade IS NOT NULL "
        "AND grade IN ('A+','A','A-','B+','B','B-','C+','C')",
        (student_id,),
    ).fetchall()
    return {r["course_code"] for r in rows}


def _parse_prereqs(s: str):
    """Split a comma-separated prereq string into a clean list of codes."""
    if not s:
        return []
    return [p.strip() for p in s.split(",") if p.strip()]


def _check_prerequisites(db, student_id: str, course_code: str):
    """Returns (ok, missing_list). ok=True means the student may register."""
    row = db.execute("SELECT prerequisites FROM courses WHERE code=?",
                     (course_code,)).fetchone()
    if not row:
        return True, []
    prereqs = _parse_prereqs(row["prerequisites"] if "prerequisites" in row.keys() else "")
    if not prereqs:
        return True, []
    passed = _student_passed_codes(db, student_id)
    missing = [p for p in prereqs if p not in passed]
    return (len(missing) == 0), missing


def _recompute_gpa(db, student_id):
    rows = db.execute(
        "SELECT grade FROM enrollments WHERE student_id=? AND grade IS NOT NULL",
        (student_id,),
    ).fetchall()
    if not rows:
        return 0.0
    pts = [GRADE_POINTS.get(r["grade"], 0.0) for r in rows]
    return round(sum(pts) / len(pts), 2)


def _semester_gpa(db, student_id, semester):
    """GPA from a single semester's graded enrollments."""
    rows = db.execute(
        "SELECT grade FROM enrollments WHERE student_id=? AND semester=? AND grade IS NOT NULL",
        (student_id, semester),
    ).fetchall()
    if not rows:
        return None
    pts = [GRADE_POINTS.get(r["grade"], 0.0) for r in rows]
    return round(sum(pts) / len(pts), 2)


def _times_failed(db, student_id, course_code):
    """How many times this student has been graded 'F' in this course."""
    row = db.execute(
        "SELECT COUNT(*) AS c FROM enrollments "
        "WHERE student_id=? AND course_code=? AND grade='F'",
        (student_id, course_code),
    ).fetchone()
    return row["c"] if row else 0


# ─── Time-slot conflict detection ──────────────────────────────────────────

_DAY_TOKENS = {
    "M":  ["M"],   "T":  ["T"],   "W":  ["W"],
    "TH": ["TH"],  "F":  ["F"],
}


def _parse_time_slot(slot: str):
    """Parse a string like 'MWF 9-10' or 'TTh 1-2.30' into (days_set, start_h, end_h).

    Returns (None, None, None) if it can't be parsed — meaning we conservatively
    treat the slot as 'unknown' and won't flag it as a conflict.

    Day grammar:
      M, T, W, F are single letters.
      Th (or TH) means Thursday — parse it before T.
    Time grammar:
      Numbers are hours with optional decimal minutes (e.g. 1-2.30 ≡ 1:00–2:30).
      No AM/PM — afternoons assumed when start < end and end <= 12 only by
      the small-hours convention used by the seed data.
    """
    if not slot:
        return None, None, None
    s = slot.strip()
    # Split into [days_part, times_part]
    m = re.match(r"^([MTWFHh]+)\s+([\d.]+)\s*[-–]\s*([\d.]+)$", s)
    if not m:
        return None, None, None
    days_raw = m.group(1).upper()
    try:
        start = _to_decimal_hour(m.group(2))
        end   = _to_decimal_hour(m.group(3))
    except ValueError:
        return None, None, None

    # Normalize PM convention: if both numbers <= 12 and end <= start we assume
    # end crosses noon (e.g. "11-12.30" stays as is; "1-2.30" → 13-14.5).
    # The seed data uses "9-10", "10-11", "11-12.30", "1-2.30" so:
    #   if start < 8 we treat it as PM (start += 12).
    if start < 8:
        start += 12
        end += 12
    elif end < start:
        # crosses noon; assume PM tail
        end += 12

    # Day parsing: scan for "TH" first, then individual letters.
    days = set()
    i = 0
    while i < len(days_raw):
        if days_raw[i:i+2] == "TH":
            days.add("TH"); i += 2; continue
        ch = days_raw[i]
        if ch in ("M", "T", "W", "F"):
            days.add(ch)
        i += 1
    return days, start, end


def _to_decimal_hour(s: str) -> float:
    """Convert '9' → 9.0, '2.30' → 2.5, '12.30' → 12.5"""
    if "." in s:
        whole, frac = s.split(".")
        return int(whole) + int(frac) / 60.0
    return float(s)


def _slots_conflict(slot_a: str, slot_b: str) -> bool:
    """True iff two time slots share at least one day and their hour ranges overlap."""
    da, sa, ea = _parse_time_slot(slot_a)
    db_, sb, eb = _parse_time_slot(slot_b)
    if not da or not db_:
        return False
    if not (da & db_):
        return False
    # Half-open overlap test: [sa,ea) vs [sb,eb)
    return sa < eb and sb < ea


# ─── Taboo word handling (spec: 1-2 → asterisk + 1 warn; ≥3 → hide + 2 warn) ─

def _taboo_words(db):
    return [r["word"].lower() for r in db.execute("SELECT word FROM taboo_words").fetchall()]


def _scan_taboo(db, text: str):
    """Return (count, visible_text) where every taboo word in `text` is
    replaced in `visible_text` with asterisks of the same length, case-insensitively.

    `count` is the total number of taboo-word occurrences found (not distinct).
    """
    words = _taboo_words(db)
    if not words:
        return 0, text
    count = 0
    visible = text
    for w in words:
        # word-boundary, case-insensitive — preserves punctuation around the word
        pattern = re.compile(r"\b" + re.escape(w) + r"\b", re.IGNORECASE)
        def _repl(m):
            return "*" * len(m.group(0))
        # Count first, then substitute
        found = pattern.findall(visible)
        count += len(found)
        visible = pattern.sub(_repl, visible)
    return count, visible


def _issue_warning(db, user_id, reason):
    """Record a warning and update the cached counter; cascade to suspension.

    For students: 3 warnings → suspended for 1 semester + fine due.
    For instructors: 3 warnings → suspended (no fine).
    Returns True if this warning triggered a suspension.
    """
    db.execute("INSERT INTO warnings (user_id,reason) VALUES (?,?)", (user_id, reason))
    role = db.execute("SELECT role FROM users WHERE user_id=?", (user_id,)).fetchone()
    if not role:
        return False
    state = _state(db)
    sem = state["semester"]

    if role["role"] == "Student":
        row = db.execute("SELECT warnings, suspended FROM students WHERE user_id=?",
                         (user_id,)).fetchone()
        new_warn = (row["warnings"] if row else 0) + 1
        suspend_now = new_warn >= 3 and not (row and row["suspended"])
        if suspend_now:
            db.execute(
                "UPDATE students SET warnings=?, suspended=1, suspended_until=?, "
                "fine_due=?, fine_paid=0 WHERE user_id=?",
                (new_warn, sem + 1, SUSPENSION_FINE, user_id),
            )
            return True
        # Only update the counter if NOT already suspended. Once suspended,
        # further warnings don't increment the counter (they're just logged).
        elif not (row and row["suspended"]):
            db.execute("UPDATE students SET warnings=? WHERE user_id=?", (new_warn, user_id))
    elif role["role"] == "Instructor":
        row = db.execute("SELECT warnings, suspended FROM instructors WHERE user_id=?",
                         (user_id,)).fetchone()
        new_warn = (row["warnings"] if row else 0) + 1
        suspend_now = new_warn >= 3 and not (row and row["suspended"])
        if suspend_now:
            db.execute(
                "UPDATE instructors SET warnings=?, suspended=1 WHERE user_id=?",
                (new_warn, user_id),
            )
            return True
        # Only update the counter if NOT already suspended. Once suspended,
        # further warnings don't increment the counter (they're just logged).
        elif not (row and row["suspended"]):
            db.execute("UPDATE instructors SET warnings=? WHERE user_id=?", (new_warn, user_id))
    return False


# ─── Public ────────────────────────────────────────────────────────────────

@app.route("/api/public", methods=["GET"])
def public_home():
    """Home page payload — no auth required."""
    db = get_db()
    state = _state(db)

    student_count = db.execute(
        "SELECT COUNT(*) AS c FROM students WHERE terminated=0 AND graduated=0"
    ).fetchone()["c"]
    instructor_count = db.execute("SELECT COUNT(*) AS c FROM instructors").fetchone()["c"]

    courses_rows = db.execute("SELECT * FROM courses ORDER BY code").fetchall()
    courses = []
    active_count = 0
    for c in courses_rows:
        cnt = _enrolled_count(db, c["code"], state["semester"])
        rating = _course_rating(db, c["code"])
        courses.append(_course_to_dict(
            c, enrolled_count=cnt, rating=rating,
            instructor_name=_instructor_name(db, c["instructor_id"]),
        ))
        if not c["cancelled"]:
            active_count += 1

    rated = [c for c in courses if c.get("rating") is not None]
    top_rated = sorted(rated, key=lambda c: -c["rating"])[:3]
    lowest_rated = sorted(rated, key=lambda c: c["rating"])[:3]

    avg_gpa_row = db.execute("SELECT AVG(gpa) AS g FROM students WHERE terminated=0").fetchone()
    avg_gpa = round(avg_gpa_row["g"], 2) if avg_gpa_row["g"] is not None else 0.0

    top_gpa_rows = db.execute(
        "SELECT u.user_id, u.name, s.gpa "
        "FROM students s JOIN users u ON u.user_id = s.user_id "
        "WHERE s.terminated=0 "
        "ORDER BY s.gpa DESC LIMIT 5"
    ).fetchall()
    top_gpa = [{"userId": r["user_id"], "name": r["name"], "gpa": r["gpa"]} for r in top_gpa_rows]

    return jsonify({
        "phaseLabel":          PHASE_LABELS[state["phase"]],
        "phase":               state["phase"],
        "semester":            state["semester"],
        "season":              state.get("season", "Spring"),
        "year":                state.get("year", 2025),
        "label":               _semester_label(state.get("season", "Spring"), state.get("year", 2025)),
        "studentCount":        student_count,
        "instructorCount":     instructor_count,
        "activeCoursesCount":  active_count,
        "avgGpa":              avg_gpa,
        "courses":             courses,
        "topRated":            top_rated,
        "lowestRated":         lowest_rated,
        "topGpa":              top_gpa,
        "programQuota":        state["program_quota"],
    })


@app.route("/api/public/course-reviews/<path:code>", methods=["GET"])
def public_course_reviews(code):
    """Anonymized reviews for a course — visible to everyone (including visitors).

    Reviews are anonymized (no student_id exposed) and reviews with ≥3 taboo
    words are hidden entirely. 1–2 taboo words → shown with asterisks.
    """
    db = get_db()
    rows = db.execute(
        "SELECT rating, visible_text, taboo_count, created_at "
        "FROM reviews WHERE course_code=? AND hidden=0 "
        "ORDER BY created_at DESC",
        (code,),
    ).fetchall()
    avg = _course_rating(db, code)
    return jsonify({
        "courseCode": code,
        "averageRating": avg,
        "count": len(rows),
        "reviews": [{
            "rating": r["rating"],
            "text":   r["visible_text"],
            "tabooCount": r["taboo_count"],
            "createdAt": r["created_at"],
        } for r in rows],
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
        "suspendedUntil":      s["suspended_until"],
        "fineDue":             s["fine_due"],
        "finePaid":            bool(s["fine_paid"]),
        "interviewPending":    bool(s["interview_pending"]),
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
            enrolled.append(_course_to_dict(
                c, instructor_name=_instructor_name(db, c["instructor_id"]),
            ))

    all_courses = db.execute("SELECT * FROM courses WHERE cancelled=0 ORDER BY code").fetchall()
    available = []
    for c in all_courses:
        if c["code"] in enrolled_codes:
            continue
        enrolled_list = [r["student_id"] for r in db.execute(
            "SELECT student_id FROM enrollments "
            "WHERE course_code=? AND semester=? AND status='enrolled'",
            (c["code"], sem)).fetchall()]
        d = _course_to_dict(c, instructor_name=_instructor_name(db, c["instructor_id"]))
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

    # Already passed it before? Don't let them re-enroll. (F is OK — retake allowed per spec.)
    passed = db.execute(
        "SELECT 1 FROM enrollments WHERE student_id=? AND course_code=? AND status='completed' "
        "AND (grade IS NOT NULL AND grade <> 'F')",
        (uid, code)).fetchone()
    if passed:
        return jsonify({"ok": False, "msg": "You have already completed this course."})

    # Prerequisite check: every listed prereq must have been completed with grade ≥ C.
    ok_pre, missing = _check_prerequisites(db, uid, code)
    if not ok_pre:
        return jsonify({
            "ok": False,
            "msg": (f"Missing prerequisite(s): {', '.join(missing)}. "
                    "You must complete these courses with at least a C grade first.")
        })

    # Spec: time conflict among chosen classes blocks registration.
    current_enrolls = db.execute(
        "SELECT c.code, c.time_slot FROM enrollments e "
        "JOIN courses c ON c.code = e.course_code "
        "WHERE e.student_id=? AND e.semester=? AND e.status='enrolled'",
        (uid, sem),
    ).fetchall()
    for other in current_enrolls:
        if _slots_conflict(course["time_slot"], other["time_slot"]):
            return jsonify({"ok": False,
                            "msg": f"Time conflict with {other['code']} ({other['time_slot']})."})

    # Spec: at most 4 courses per semester (the lower bound of 2 is a soft rule
    # checked at the REGISTRATION→RUNNING transition — see _advance_to_running).
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
    """Submit a course review.

    Spec:
      • Reviews allowed only before instructor posts the grade. (We enforce
        the GRADING phase + null-grade check.)
      • 1-2 taboo words → review is shown with words replaced by *, and the
        author receives 1 warning.
      • ≥3 taboo words → review is NOT shown; the author receives 2 warnings.
    """
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

    taboo_count, visible = _scan_taboo(db, text)
    hidden = 1 if taboo_count >= 3 else 0
    flagged = 1 if taboo_count > 0 else 0

    db.execute(
        "INSERT INTO reviews (course_code,student_id,semester,rating,text,visible_text,taboo_count,hidden,flagged) "
        "VALUES (?,?,?,?,?,?,?,?,?)",
        (code, uid, sem, rating, text, visible, taboo_count, hidden, flagged))

    msg = "Review submitted."
    if taboo_count == 0:
        pass
    elif taboo_count <= 2:
        _issue_warning(db, uid, f"Review contained {taboo_count} taboo word(s); shown with asterisks.")
        msg = f"Review submitted with {taboo_count} taboo word(s) masked. You received 1 warning."
    else:
        # ≥3 taboo words → 2 warnings
        _issue_warning(db, uid, f"Review contained {taboo_count} taboo words; review hidden.")
        _issue_warning(db, uid, f"Review contained {taboo_count} taboo words; review hidden (2nd warning).")
        msg = (f"Review contained {taboo_count} taboo words and was hidden. "
               f"You received 2 warnings.")

    db.commit()
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


@app.route("/api/student/pay-fine", methods=["POST"])
@auth_required("Student")
def student_pay_fine():
    """Spec: 'must pay a fine to the registrar'."""
    db = get_db()
    uid = request.user["user_id"]
    s = db.execute("SELECT * FROM students WHERE user_id=?", (uid,)).fetchone()
    if not s:
        return jsonify({"ok": False, "msg": "Student record not found."})
    if s["fine_due"] <= 0:
        return jsonify({"ok": False, "msg": "No fine due."})
    if s["fine_paid"]:
        return jsonify({"ok": False, "msg": "Fine already paid."})
    db.execute("UPDATE students SET fine_paid=1 WHERE user_id=?", (uid,))
    db.commit()
    return jsonify({"ok": True, "msg": f"Fine of ${s['fine_due']:.2f} paid. Thank you."})


# ─── Study Buddy Matcher (creative feature) ────────────────────────────────

@app.route("/api/student/study-buddy", methods=["GET", "POST", "DELETE"])
@auth_required("Student")
def student_study_buddy():
    db = get_db()
    uid = request.user["user_id"]
    state = _state(db)
    sem = state["semester"]

    if request.method == "POST":
        data = request.get_json(silent=True) or {}
        bio = (data.get("bio") or "").strip()[:500]
        avail = (data.get("availability") or "").strip()[:200]
        db.execute(
            "INSERT INTO study_buddy_optins (student_id,bio,availability) VALUES (?,?,?) "
            "ON CONFLICT(student_id) DO UPDATE SET bio=excluded.bio, availability=excluded.availability",
            (uid, bio, avail),
        )
        db.commit()
        return jsonify({"ok": True, "msg": "You are now opted in to Study Buddy matching."})

    if request.method == "DELETE":
        db.execute("DELETE FROM study_buddy_optins WHERE student_id=?", (uid,))
        db.commit()
        return jsonify({"ok": True, "msg": "You have opted out of Study Buddy matching."})

    # GET — return my opt-in status + a list of compatible matches.
    my = db.execute("SELECT * FROM study_buddy_optins WHERE student_id=?", (uid,)).fetchone()
    opted_in = my is not None

    my_courses = set(r["course_code"] for r in db.execute(
        "SELECT course_code FROM enrollments WHERE student_id=? AND semester=? AND status='enrolled'",
        (uid, sem),
    ).fetchall())

    matches = []
    if opted_in and my_courses:
        rows = db.execute(
            "SELECT o.student_id, o.bio, o.availability, u.name "
            "FROM study_buddy_optins o JOIN users u ON u.user_id=o.student_id "
            "WHERE o.student_id <> ?",
            (uid,),
        ).fetchall()
        my_tokens = set((my["availability"] or "").lower().split()) if my else set()
        for r in rows:
            their_courses = set(c["course_code"] for c in db.execute(
                "SELECT course_code FROM enrollments WHERE student_id=? AND semester=? AND status='enrolled'",
                (r["student_id"], sem),
            ).fetchall())
            shared = sorted(my_courses & their_courses)
            if not shared:
                continue
            their_tokens = set((r["availability"] or "").lower().split())
            overlap_avail = sorted(my_tokens & their_tokens)
            # Match score: 10 points per shared course + 2 points per shared availability token.
            score = 10 * len(shared) + 2 * len(overlap_avail)
            matches.append({
                "userId":       r["student_id"],
                "name":         r["name"],
                "bio":          r["bio"],
                "availability": r["availability"],
                "sharedCourses": shared,
                "sharedAvailability": overlap_avail,
                "score":        score,
            })
        matches.sort(key=lambda m: -m["score"])

    return jsonify({
        "optedIn":     opted_in,
        "bio":         (my["bio"] if my else "") or "",
        "availability": (my["availability"] if my else "") or "",
        "matches":     matches,
        "courses":     sorted(my_courses),
    })


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

        cd = _course_to_dict(c, instructor_name=_instructor_name(db, c["instructor_id"]))
        cd["students"] = students
        cd["enrolled"] = [s["userId"] for s in students]
        cd["waitlist"] = waitlist
        courses.append(cd)

    return jsonify({
        "instructor": {
            "userId":        uid,
            "name":          request.user["name"],
            "warnings":      inst["warnings"],
            "suspended":     bool(inst["suspended"]),
            "fired":         bool(inst["fired"]),
            "reviewPending": bool(inst["review_pending"]),
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
    instr_reviews = db.execute(
        "SELECT COUNT(*) AS c FROM instructors WHERE review_pending=1 AND suspended=0 AND fired=0"
    ).fetchone()["c"]
    interview_pending = db.execute(
        "SELECT COUNT(*) AS c FROM students WHERE interview_pending=1 AND terminated=0"
    ).fetchone()["c"]
    return jsonify({
        "phaseLabel":         PHASE_LABELS[state["phase"]],
        "phase":              state["phase"],
        "semester":           state["semester"],
        "season":             state.get("season", "Spring"),
        "year":               state.get("year", 2025),
        "label":              _semester_label(state.get("season", "Spring"), state.get("year", 2025)),
        "specialRegistration": bool(state["special_registration"]),
        "programQuota":       state["program_quota"],
        "studentCount":       student_count,
        "pendingApps":        pending,
        "openComplaints":     open_complaints,
        "activeCourses":      active_courses,
        "instructorsToReview": instr_reviews,
        "interviewPending":   interview_pending,
    })


# ── Phase transition helpers — implement the spec's automatic rules ────────

def _advance_to_running(db, sem):
    """REGISTRATION → RUNNING.

    Spec actions:
      • Students enrolled in <2 courses → warning.
      • Courses with <3 enrolled → cancelled.
      • Students of cancelled courses → drop the enrollment + open special reg.
      • Instructors of cancelled courses → warning.
      • Instructors whose ALL courses are cancelled → suspended.
    Returns a summary list of actions taken.
    """
    actions = []

    # 1) Warn under-enrolled students (less than 2 active enrollments)
    student_rows = db.execute(
        "SELECT s.user_id FROM students s "
        "WHERE s.suspended=0 AND s.terminated=0 AND s.graduated=0"
    ).fetchall()
    for sr in student_rows:
        cnt = db.execute(
            "SELECT COUNT(*) AS c FROM enrollments "
            "WHERE student_id=? AND semester=? AND status='enrolled'",
            (sr["user_id"], sem),
        ).fetchone()["c"]
        if cnt < 2:
            _issue_warning(db, sr["user_id"],
                           f"Enrolled in only {cnt} course(s); minimum is 2.")
            actions.append(f"Warned {sr['user_id']}: under-enrolled ({cnt} course(s)).")

    # 2) Cancel under-enrolled courses (<3 students); collect affected
    course_rows = db.execute(
        "SELECT * FROM courses WHERE cancelled=0").fetchall()
    cancelled_by_instructor = {}      # instructor_id -> count of their courses cancelled
    instructor_active = {}            # instructor_id -> count of their non-cancelled (any) courses
    students_displaced = set()

    # First, tally each instructor's total non-cancelled course count
    for c in course_rows:
        if c["instructor_id"]:
            instructor_active[c["instructor_id"]] = instructor_active.get(c["instructor_id"], 0) + 1

    for c in course_rows:
        enrolled = _enrolled_count(db, c["code"], sem)
        if enrolled < 3:
            db.execute("UPDATE courses SET cancelled=1 WHERE code=?", (c["code"],))
            # Drop the affected students' enrollments
            displaced_rows = db.execute(
                "SELECT student_id FROM enrollments "
                "WHERE course_code=? AND semester=? AND status='enrolled'",
                (c["code"], sem),
            ).fetchall()
            for d in displaced_rows:
                students_displaced.add(d["student_id"])
            db.execute(
                "UPDATE enrollments SET status='cancelled' "
                "WHERE course_code=? AND semester=? AND status='enrolled'",
                (c["code"], sem),
            )
            if c["instructor_id"]:
                cancelled_by_instructor[c["instructor_id"]] = \
                    cancelled_by_instructor.get(c["instructor_id"], 0) + 1
            actions.append(f"Cancelled {c['code']} ({enrolled} student(s)).")

    # 3) Warn instructors of cancelled courses; suspend if all theirs cancelled
    for inst_id, n_cancelled in cancelled_by_instructor.items():
        _issue_warning(db, inst_id,
                       f"{n_cancelled} of your course(s) cancelled due to low enrollment.")
        actions.append(f"Warned instructor {inst_id}: {n_cancelled} course(s) cancelled.")
        total = instructor_active.get(inst_id, 0)
        if total > 0 and n_cancelled >= total:
            # All courses cancelled → suspended (no fine for instructors per spec)
            db.execute(
                "UPDATE instructors SET suspended=1 WHERE user_id=?", (inst_id,))
            actions.append(f"Suspended instructor {inst_id}: ALL courses cancelled.")

    # 4) Open the special registration window if any students were displaced.
    if students_displaced:
        db.execute("UPDATE semester_state SET special_registration=1 WHERE id=1")
        actions.append(
            f"Special registration opened for {len(students_displaced)} displaced student(s)."
        )

    return actions


def _advance_to_closed(db, sem):
    """GRADING → CLOSED.

    Spec actions:
      • Instructors who didn't grade ALL their students → warning.
      • Instructors with class GPA > 3.5 OR < 2.5 → flagged for registrar review
        (review_pending=1). The registrar then warns or fires them.
      • Students with GPA < 2.0 OR who failed the same course twice → auto-terminated.
      • Students with GPA in [2.0, 2.25] → warning + interview flag.
      • Students with semester GPA > 3.75 OR cumulative GPA > 3.5 (with >1 sem completed)
        → honor roll +1 (used to remove a warning at semester rollover).
    """
    actions = []

    # 1) Instructors who didn't grade all students
    inst_rows = db.execute(
        "SELECT user_id FROM instructors WHERE suspended=0 AND fired=0").fetchall()
    for ir in inst_rows:
        ungraded = db.execute("""
            SELECT COUNT(*) AS c FROM enrollments e
            JOIN courses c ON c.code = e.course_code
            WHERE c.instructor_id=? AND e.semester=? AND e.status='enrolled' AND e.grade IS NULL
        """, (ir["user_id"], sem)).fetchone()["c"]
        if ungraded > 0:
            _issue_warning(db, ir["user_id"],
                           f"Did not grade all students ({ungraded} ungraded) by end of grading.")
            actions.append(f"Warned instructor {ir['user_id']}: {ungraded} ungraded students.")

    # 2) Class-GPA review queue for instructors with extreme averages
    for ir in inst_rows:
        # Per-course average GPA from this semester's grades
        course_rows = db.execute(
            "SELECT code FROM courses WHERE instructor_id=? AND cancelled=0", (ir["user_id"],),
        ).fetchall()
        flag = False
        for cr in course_rows:
            grade_rows = db.execute(
                "SELECT grade FROM enrollments "
                "WHERE course_code=? AND semester=? AND grade IS NOT NULL",
                (cr["code"], sem),
            ).fetchall()
            if not grade_rows:
                continue
            pts = [GRADE_POINTS.get(g["grade"], 0.0) for g in grade_rows]
            avg = sum(pts) / len(pts)
            if avg > 3.5 or avg < 2.5:
                flag = True
                break
        if flag:
            db.execute(
                "UPDATE instructors SET review_pending=1 WHERE user_id=?",
                (ir["user_id"],),
            )
            actions.append(f"Instructor {ir['user_id']} flagged for registrar review (extreme class GPA).")

    # 2b) Spec: "The instructor of any course receiving an average rating <2
    #     will be warned." Issue one warning per low-rated course.
    for ir in inst_rows:
        course_rows = db.execute(
            "SELECT code FROM courses WHERE instructor_id=? AND cancelled=0",
            (ir["user_id"],),
        ).fetchall()
        for cr in course_rows:
            rating = _course_rating(db, cr["code"])
            if rating is not None and rating < 2.0:
                _issue_warning(
                    db, ir["user_id"],
                    f"Course {cr['code']} average rating {rating} below 2.0.",
                )
                actions.append(
                    f"Warned instructor {ir['user_id']}: low rating on {cr['code']} ({rating})."
                )

    # 3) Student GPA outcomes
    student_rows = db.execute(
        "SELECT * FROM students WHERE terminated=0 AND graduated=0"
    ).fetchall()
    for sr in student_rows:
        uid = sr["user_id"]
        # Cumulative GPA already updated by instructor_grade. Use it.
        gpa = sr["gpa"]
        sem_gpa = _semester_gpa(db, uid, sem)

        # 3a) Failed same course twice → terminate
        fail_repeat = db.execute("""
            SELECT course_code, COUNT(*) AS n FROM enrollments
            WHERE student_id=? AND grade='F'
            GROUP BY course_code HAVING COUNT(*) >= 2
        """, (uid,)).fetchone()
        if fail_repeat:
            db.execute(
                "UPDATE students SET terminated=1 WHERE user_id=?", (uid,))
            actions.append(
                f"Terminated student {uid}: failed {fail_repeat['course_code']} twice.")
            continue

        # 3b) GPA < 2.0 → terminate
        if gpa is not None and gpa < 2.0:
            db.execute("UPDATE students SET terminated=1 WHERE user_id=?", (uid,))
            actions.append(f"Terminated student {uid}: GPA {gpa} below 2.0.")
            continue

        # 3c) 2.0 ≤ GPA ≤ 2.25 → warning + interview
        if gpa is not None and 2.0 <= gpa <= 2.25:
            _issue_warning(db, uid, f"GPA {gpa} requires registrar interview.")
            db.execute("UPDATE students SET interview_pending=1 WHERE user_id=?", (uid,))
            actions.append(f"Warned student {uid}: GPA {gpa} (interview required).")

        # 3d) Honor roll: semester GPA > 3.75 OR cumulative GPA > 3.5 with > 1 semester
        is_honor = False
        if sem_gpa is not None and sem_gpa > 3.75:
            is_honor = True
        elif gpa is not None and gpa > 3.5 and sr["semesters_completed"] >= 1:
            is_honor = True
        if is_honor:
            new_warns = max(0, sr["warnings"] - 1)
            db.execute(
                "UPDATE students SET honor_count=honor_count+1, warnings=? WHERE user_id=?",
                (new_warns, uid),
            )
            actions.append(f"Honor roll: {uid} (semester GPA {sem_gpa}, cumulative {gpa}).")

    return actions


def _roll_over_semester(db):
    """CLOSED → next semester SETUP.

    Marks graded enrollments as completed, drops un-graded, bumps semester,
    advances season/year (Spring → Summer → Fall → Winter → Spring of next year),
    lifts suspensions whose suspended_until ≤ next semester (only if fine paid),
    resets cancelled flags on courses so the catalog is fully available again,
    and lifts instructor suspensions so they can be reassigned next semester.
    """
    state = _state(db)
    sem = state["semester"]
    season = state["season"] if "season" in state else "Spring"
    year = state["year"] if "year" in state else 2025

    # Complete the graded ones; drop the rest.
    db.execute("UPDATE enrollments SET status='completed' WHERE status='enrolled' AND grade IS NOT NULL")
    db.execute("UPDATE enrollments SET status='dropped' WHERE status='enrolled' AND grade IS NULL")

    # Bump semesters_completed for active students
    db.execute(
        "UPDATE students SET semesters_completed = semesters_completed + 1 "
        "WHERE suspended=0 AND terminated=0 AND graduated=0"
    )

    # The new sequence number must be strictly greater than anything we have
    # in history. Using `sem + 1` from the *current* state can create collisions
    # if the registrar jumped back to an earlier semester and then rolled
    # forward again — the previously-issued sequence numbers would be re-used
    # with potentially different season/year values, producing duplicate labels
    # in the history dropdown.
    max_row = db.execute(
        "SELECT COALESCE(MAX(semester), 0) AS m FROM semester_history"
    ).fetchone()
    new_sem = max(sem + 1, max_row["m"] + 1)
    new_season, new_year = _next_season_year(season, year)

    # Lift suspension if the suspended_until threshold has been reached AND fine paid.
    db.execute(
        "UPDATE students SET suspended=0, fine_due=0, suspended_until=0 "
        "WHERE suspended=1 AND suspended_until <= ? AND fine_paid=1",
        (new_sem,),
    )

    # Issue 8 fix: reset cancelled flag on all courses so they're available again
    # next semester. Cancellation is per-semester (driven by enrollment), not permanent.
    db.execute("UPDATE courses SET cancelled=0")

    # Lift instructor suspensions: they were suspended for "this semester only"
    # per the spec. After rollover they can teach again. (Fired stays.)
    db.execute(
        "UPDATE instructors SET suspended=0, review_pending=0 WHERE fired=0"
    )

    # Stamp history for the just-closed semester
    db.execute(
        "INSERT OR REPLACE INTO semester_history (semester, season, year, closed_at) "
        "VALUES (?, ?, ?, datetime('now'))",
        (sem, season, year),
    )
    # And register the new semester as known
    db.execute(
        "INSERT OR IGNORE INTO semester_history (semester, season, year) VALUES (?, ?, ?)",
        (new_sem, new_season, new_year),
    )

    db.execute(
        "UPDATE semester_state SET semester=?, season=?, year=?, phase='SETUP', special_registration=0 "
        "WHERE id=1",
        (new_sem, new_season, new_year),
    )


@app.route("/api/registrar/advance-phase", methods=["POST"])
@auth_required("Registrar")
def registrar_advance_phase():
    """Cycle SETUP → REGISTRATION → RUNNING → GRADING → CLOSED → SETUP (next sem)."""
    db = get_db()
    state = _state(db)
    order = ["SETUP", "REGISTRATION", "RUNNING", "GRADING", "CLOSED"]
    idx = order.index(state["phase"])
    sem = state["semester"]
    actions = []

    if state["phase"] == "CLOSED":
        _roll_over_semester(db)
        db.commit()
        new_state = _state(db)
        label = _semester_label(new_state.get("season", "Spring"), new_state.get("year", 2025))
        return jsonify({
            "ok": True,
            "msg": f"Semester closed. Now in {label} ({PHASE_LABELS[new_state['phase']]}).",
            "phase": new_state["phase"],
            "semester": new_state["semester"],
            "season": new_state.get("season"),
            "year":   new_state.get("year"),
            "label":  label,
            "actions": [
                "Semester rolled over. Honor rolls applied at previous CLOSED step.",
                "All courses reactivated for the new semester.",
                "Instructor suspensions lifted (fired instructors remain removed).",
            ],
        })

    next_phase = order[idx + 1]

    if state["phase"] == "REGISTRATION" and next_phase == "RUNNING":
        actions = _advance_to_running(db, sem)
    elif state["phase"] == "GRADING" and next_phase == "CLOSED":
        actions = _advance_to_closed(db, sem)

    db.execute("UPDATE semester_state SET phase=? WHERE id=1", (next_phase,))
    db.commit()
    return jsonify({
        "ok": True,
        "msg": f"Phase advanced to {PHASE_LABELS[next_phase]}.",
        "phase": next_phase,
        "actions": actions,
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
        d = _course_to_dict(
            c, rating=_course_rating(db, c["code"]),
            instructor_name=_instructor_name(db, c["instructor_id"]),
        )
        d["enrolled"] = enrolled_list
        out.append(d)
    return jsonify(out)


@app.route("/api/registrar/instructors", methods=["GET"])
@auth_required("Registrar")
def registrar_instructors():
    db = get_db()
    rows = db.execute(
        "SELECT u.user_id, u.name, i.warnings, i.suspended, i.fired, i.review_pending "
        "FROM users u "
        "JOIN instructors i ON i.user_id = u.user_id "
        "WHERE i.fired=0 "
        "ORDER BY u.name"
    ).fetchall()
    return jsonify([{
        "userId":        r["user_id"],
        "name":          r["name"],
        "warnings":      r["warnings"],
        "suspended":     bool(r["suspended"]),
        "fired":         bool(r["fired"]),
        "reviewPending": bool(r["review_pending"]),
    } for r in rows])


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
    prereqs_raw = data.get("prerequisites")
    if isinstance(prereqs_raw, list):
        prereqs = ",".join(p.strip() for p in prereqs_raw if p and p.strip())
    else:
        prereqs = (prereqs_raw or "").strip()

    if not code or not name or not instr or not slot:
        return jsonify({"ok": False, "msg": "Code, name, instructor and time slot are required."})
    if cap < 3 or cap > 60:
        return jsonify({"ok": False, "msg": "Capacity must be between 3 and 60."})

    db = get_db()
    if db.execute("SELECT 1 FROM courses WHERE code=?", (code,)).fetchone():
        return jsonify({"ok": False, "msg": f"Course {code} already exists."})
    inst_row = db.execute(
        "SELECT suspended, fired FROM instructors WHERE user_id=?", (instr,)).fetchone()
    if not inst_row:
        return jsonify({"ok": False, "msg": f"Instructor {instr} not found."})
    if inst_row["suspended"]:
        return jsonify({"ok": False, "msg": f"Instructor {instr} is suspended and cannot teach this semester."})
    if inst_row["fired"]:
        return jsonify({"ok": False, "msg": f"Instructor {instr} has been removed."})

    # Validate prerequisites exist (skip self-reference + ignore unknown codes cleanly).
    for p in _parse_prereqs(prereqs):
        if p == code:
            return jsonify({"ok": False, "msg": f"A course cannot list itself as a prerequisite."})
        if not db.execute("SELECT 1 FROM courses WHERE code=?", (p,)).fetchone():
            return jsonify({"ok": False, "msg": f"Prerequisite course {p} does not exist."})

    db.execute(
        "INSERT INTO courses (code,name,instructor_id,time_slot,capacity,is_core,prerequisites) "
        "VALUES (?,?,?,?,?,?,?)",
        (code, name, instr, slot, cap, is_core, prereqs))
    db.commit()
    return jsonify({"ok": True, "msg": f"Course {code} created."})


# ── Course update / delete (issue 3, 4) ────────────────────────────────────

@app.route("/api/registrar/update-course", methods=["POST"])
@auth_required("Registrar")
def registrar_update_course():
    """Update any field of a course. Any subset of name, instructorId,
    timeSlot, capacity, isCore, cancelled, prerequisites can be passed."""
    data = request.get_json(silent=True) or {}
    code = (data.get("code") or "").strip()
    if not code:
        return jsonify({"ok": False, "msg": "Course code is required."})

    db = get_db()
    row = db.execute("SELECT * FROM courses WHERE code=?", (code,)).fetchone()
    if not row:
        return jsonify({"ok": False, "msg": f"Course {code} not found."})

    updates = []
    params = []
    if "name" in data and (data["name"] or "").strip():
        updates.append("name=?"); params.append(data["name"].strip())
    if "instructorId" in data:
        new_inst = (data["instructorId"] or "").strip() or None
        if new_inst:
            ir = db.execute(
                "SELECT suspended, fired FROM instructors WHERE user_id=?",
                (new_inst,)).fetchone()
            if not ir:
                return jsonify({"ok": False, "msg": f"Instructor {new_inst} not found."})
            if ir["suspended"]:
                return jsonify({"ok": False, "msg": f"Instructor {new_inst} is suspended."})
            if ir["fired"]:
                return jsonify({"ok": False, "msg": f"Instructor {new_inst} has been removed."})
        updates.append("instructor_id=?"); params.append(new_inst)
    if "timeSlot" in data and (data["timeSlot"] or "").strip():
        updates.append("time_slot=?"); params.append(data["timeSlot"].strip())
    if "capacity" in data:
        try:
            cap = int(data["capacity"])
            if cap < 3 or cap > 60:
                return jsonify({"ok": False, "msg": "Capacity must be 3-60."})
            updates.append("capacity=?"); params.append(cap)
        except (TypeError, ValueError):
            return jsonify({"ok": False, "msg": "Invalid capacity."})
    if "isCore" in data:
        updates.append("is_core=?"); params.append(1 if data["isCore"] in (True, "true", 1) else 0)
    if "cancelled" in data:
        updates.append("cancelled=?"); params.append(1 if data["cancelled"] in (True, "true", 1) else 0)
    if "prerequisites" in data:
        if isinstance(data["prerequisites"], list):
            pre = ",".join(p.strip() for p in data["prerequisites"] if p and p.strip())
        else:
            pre = (data["prerequisites"] or "").strip()
        for p in _parse_prereqs(pre):
            if p == code:
                return jsonify({"ok": False, "msg": "A course cannot list itself as a prerequisite."})
            if not db.execute("SELECT 1 FROM courses WHERE code=?", (p,)).fetchone():
                return jsonify({"ok": False, "msg": f"Prerequisite course {p} does not exist."})
        updates.append("prerequisites=?"); params.append(pre)

    if not updates:
        return jsonify({"ok": False, "msg": "Nothing to update."})

    params.append(code)
    db.execute(f"UPDATE courses SET {', '.join(updates)} WHERE code=?", params)
    db.commit()
    return jsonify({"ok": True, "msg": f"Course {code} updated."})


@app.route("/api/registrar/delete-course/<path:code>", methods=["DELETE"])
@auth_required("Registrar")
def registrar_delete_course(code):
    """Delete a course entirely. FK rules cascade to enrollments / waitlist /
    reviews. We wrap the delete in PRAGMA foreign_keys = OFF then ON, matching
    the MySQL pattern of SET FOREIGN_KEY_CHECKS = 0/1 around bulk operations,
    so the cascade behaves predictably even when triggers exist.
    """
    db = get_db()
    row = db.execute("SELECT 1 FROM courses WHERE code=?", (code,)).fetchone()
    if not row:
        return jsonify({"ok": False, "msg": f"Course {code} not found."}), 404

    # Mirror MySQL "SET FOREIGN_KEY_CHECKS = 0; DELETE; SET FOREIGN_KEY_CHECKS = 1;"
    db.execute("PRAGMA foreign_keys = OFF")
    try:
        # Manually clean up dependents (we want explicit control, not just CASCADE)
        db.execute("DELETE FROM enrollments WHERE course_code=?", (code,))
        db.execute("DELETE FROM waitlist    WHERE course_code=?", (code,))
        db.execute("DELETE FROM reviews     WHERE course_code=?", (code,))
        # Also remove this code from any other course's prerequisites string.
        for r in db.execute("SELECT code, prerequisites FROM courses").fetchall():
            pre = _parse_prereqs(r["prerequisites"] or "")
            if code in pre:
                pre.remove(code)
                db.execute("UPDATE courses SET prerequisites=? WHERE code=?",
                           (",".join(pre), r["code"]))
        db.execute("DELETE FROM courses WHERE code=?", (code,))
        db.commit()
    finally:
        db.execute("PRAGMA foreign_keys = ON")
    return jsonify({"ok": True, "msg": f"Course {code} deleted."})


@app.route("/api/registrar/students", methods=["GET"])
@auth_required("Registrar")
def registrar_students():
    db = get_db()
    rows = db.execute("""
        SELECT u.user_id, u.name, s.gpa, s.warnings, s.honor_count,
               s.suspended, s.terminated, s.graduated, s.interview_pending,
               s.fine_due, s.fine_paid
        FROM users u JOIN students s ON s.user_id = u.user_id
        ORDER BY u.user_id
    """).fetchall()
    return jsonify([{
        "userId":           r["user_id"],
        "name":             r["name"],
        "gpa":              r["gpa"],
        "warnings":         r["warnings"],
        "honorCount":       r["honor_count"],
        "suspended":        bool(r["suspended"]),
        "terminated":       bool(r["terminated"]),
        "graduated":        bool(r["graduated"]),
        "interviewPending": bool(r["interview_pending"]),
        "fineDue":          r["fine_due"],
        "finePaid":         bool(r["fine_paid"]),
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


def _active_student_count(db) -> int:
    return db.execute(
        "SELECT COUNT(*) AS c FROM students "
        "WHERE suspended=0 AND terminated=0 AND graduated=0"
    ).fetchone()["c"]


@app.route("/api/registrar/approve-app", methods=["POST"])
@auth_required("Registrar")
def registrar_approve_app():
    """Approve an application.

    Spec compliance:
      • For STUDENT applications: GPA > 3.0 AND quota not reached → accept
        automatically (no justification needed).
      • Accepting a student with GPA <= 3.0 OR over quota requires justification.
      • Rejecting a student with GPA > 3.0 (where the spec says they 'should
        be accepted') is handled by /reject-app and requires justification.
      • Instructor approvals don't require justification per spec.
    """
    data = request.get_json(silent=True) or {}
    app_id = (data.get("appId") or "").strip()
    justification = (data.get("justification") or "").strip()

    db = get_db()
    a = db.execute("SELECT * FROM applications WHERE app_id=?", (app_id,)).fetchone()
    if not a:
        return jsonify({"ok": False, "msg": "Application not found."})
    if a["status"] != "Pending":
        return jsonify({"ok": False, "msg": f"Application is already {a['status']}."})

    state = _state(db)
    if a["role"] == "Student":
        gpa = a["gpa"] or 0.0
        active = _active_student_count(db)
        quota = state["program_quota"]
        quota_reached = active >= quota

        below_threshold = gpa < 3.0

        # Justification required to override either the GPA rule or the quota rule.
        if (below_threshold or quota_reached) and not justification:
            reasons = []
            if below_threshold:
                reasons.append(f"GPA {gpa} below 3.0")
            if quota_reached:
                reasons.append(f"program quota reached ({active}/{quota})")
            return jsonify({
                "ok": False,
                "msg": "Justification required: " + "; ".join(reasons) + ".",
            })

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
        "msg": f"Approved. New {a['role']} account created: {new_uid} "
               f"(default password: {database.DEFAULT_PASSWORD}).",
    })


@app.route("/api/registrar/reject-app", methods=["POST"])
@auth_required("Registrar")
def registrar_reject_app():
    """Reject an application.

    Spec: rejecting a Student application that meets the auto-accept rule
    (GPA > 3.0 and quota not reached) requires a justification message to the
    applicant.
    """
    data = request.get_json(silent=True) or {}
    app_id = (data.get("appId") or "").strip()
    justification = (data.get("justification") or "").strip()

    db = get_db()
    a = db.execute("SELECT * FROM applications WHERE app_id=?", (app_id,)).fetchone()
    if not a:
        return jsonify({"ok": False, "msg": "Application not found."})
    if a["status"] != "Pending":
        return jsonify({"ok": False, "msg": f"Application is already {a['status']}."})

    if a["role"] == "Student":
        gpa = a["gpa"] or 0.0
        state = _state(db)
        active = _active_student_count(db)
        quota_reached = active >= state["program_quota"]
        # Justification required to override the auto-accept rule
        if gpa > 3.0 and not quota_reached and not justification:
            return jsonify({
                "ok": False,
                "msg": f"Justification required: applicant has GPA {gpa} > 3.0 and quota "
                       f"is not reached ({active}/{state['program_quota']}).",
            })

    db.execute(
        "UPDATE applications SET status='Rejected', justification=? WHERE app_id=?",
        (justification or None, app_id),
    )
    db.commit()
    return jsonify({"ok": True, "msg": "Application rejected." +
                                       (f" Reason recorded: {justification}" if justification else "")})


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
    """Resolve a complaint by taking action.

    Spec: "An instructor can complain to the registrars to warn or de-register
    the student; the registrars must take action: either punish the student
    accordingly or punish the instructor by one warning."

    Actions:
    - dismiss: only for student-vs-student or student-vs-instructor complaints;
      not available for instructor-vs-student complaints (those require action)
    - punish: issue a warning to the target student (or instructor if student is
      filing against instructor)
    - deregister: drop the student from all their enrolled courses this semester
      (only available when complaint target is a student)
    - warn_instructor: issue a warning to the filing instructor (only for
      instructor-vs-student complaints; used when complaint is unjustified)
    """
    data = request.get_json(silent=True) or {}
    cid = (data.get("complaintId") or "").strip()
    action = (data.get("action") or "").strip()

    if action not in ("dismiss", "punish", "deregister", "warn_instructor"):
        return jsonify({"ok": False, "msg": "Unknown action."})

    db = get_db()
    c = db.execute("SELECT * FROM complaints WHERE complaint_id=?", (cid,)).fetchone()
    if not c:
        return jsonify({"ok": False, "msg": "Complaint not found."})
    if c["resolved"]:
        return jsonify({"ok": False, "msg": "Complaint already resolved."})

    # Instructor complaints require mandatory action — must not dismiss
    if c["type"] == "instructor_vs_student" and action == "dismiss":
        return jsonify({
            "ok": False,
            "msg": "Instructor complaints require mandatory action — pick punish, deregister, or warn_instructor."
        })

    # De-registration only applies to student targets
    if action == "deregister":
        # Verify the target is a student
        target_user = db.execute(
            "SELECT role FROM users WHERE user_id=?", (c["against_id"],)
        ).fetchone()
        if not target_user or target_user["role"] != "Student":
            return jsonify({
                "ok": False,
                "msg": "De-registration only applies when the complaint target is a student."
            })
        # Drop student from all enrolled courses this semester
        state = _state(db)
        db.execute(
            "UPDATE enrollments SET status='dropped' "
            "WHERE student_id=? AND semester=? AND status='enrolled'",
            (c["against_id"], state["semester"]),
        )
        resolution = f"De-registered student {c['against_id']} from all courses"
    elif action == "punish":
        _issue_warning(db, c["against_id"], f"Complaint {cid}: {c['description'][:80]}")
        resolution = f"Punished {c['against_id']}"
    elif action == "warn_instructor":
        if c["type"] != "instructor_vs_student":
            return jsonify({
                "ok": False,
                "msg": "warn_instructor only applies to instructor-vs-student complaints."
            })
        _issue_warning(db, c["from_id"], f"Unjustified complaint {cid}")
        resolution = f"Warned filer {c['from_id']} (unjustified complaint)"
    else:
        # action == "dismiss"
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
        SELECT r.review_id, r.course_code, r.student_id, r.rating, r.text, r.visible_text,
               r.taboo_count, r.hidden, r.flagged
        FROM reviews r
        ORDER BY r.review_id DESC
    """).fetchall()
    return jsonify([{
        "reviewId":    r["review_id"],
        "courseCode":  r["course_code"],
        "studentId":   r["student_id"],     # only the registrar sees this
        "rating":      r["rating"],
        "text":        r["text"],
        "visibleText": r["visible_text"],
        "tabooCount":  r["taboo_count"],
        "hidden":      bool(r["hidden"]),
        "flagged":     bool(r["flagged"]),
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
    # Re-scan & re-mask all existing reviews with the new word list.
    rows = db.execute("SELECT review_id, text FROM reviews").fetchall()
    for r in rows:
        cnt, vis = _scan_taboo(db, r["text"])
        db.execute(
            "UPDATE reviews SET taboo_count=?, visible_text=?, hidden=?, flagged=? "
            "WHERE review_id=?",
            (cnt, vis, 1 if cnt >= 3 else 0, 1 if cnt > 0 else 0, r["review_id"]),
        )
    db.commit()
    words = [r["word"] for r in db.execute("SELECT word FROM taboo_words ORDER BY word").fetchall()]
    return jsonify({"tabooWords": words})


@app.route("/api/registrar/taboo/<word>", methods=["DELETE"])
@auth_required("Registrar")
def registrar_taboo_delete(word):
    db = get_db()
    db.execute("DELETE FROM taboo_words WHERE word=?", (word.lower(),))
    # Re-scan reviews — a removed word may no longer be taboo.
    rows = db.execute("SELECT review_id, text FROM reviews").fetchall()
    for r in rows:
        cnt, vis = _scan_taboo(db, r["text"])
        db.execute(
            "UPDATE reviews SET taboo_count=?, visible_text=?, hidden=?, flagged=? "
            "WHERE review_id=?",
            (cnt, vis, 1 if cnt >= 3 else 0, 1 if cnt > 0 else 0, r["review_id"]),
        )
    db.commit()
    words = [r["word"] for r in db.execute("SELECT word FROM taboo_words ORDER BY word").fetchall()]
    return jsonify({"tabooWords": words})


# Instructor review queue (spec: 'questioned by registrars; without adequate
# justifications, the instructor will be warned or fired right away')

@app.route("/api/registrar/instructor-reviews", methods=["GET"])
@auth_required("Registrar")
def registrar_instructor_reviews():
    """List instructors currently flagged for class-GPA review."""
    db = get_db()
    state = _state(db)
    sem = state["semester"]
    rows = db.execute("""
        SELECT u.user_id, u.name, i.warnings, i.suspended, i.fired
        FROM instructors i JOIN users u ON u.user_id = i.user_id
        WHERE i.review_pending=1 AND i.fired=0
        ORDER BY u.name
    """).fetchall()
    out = []
    for r in rows:
        course_rows = db.execute(
            "SELECT code, name FROM courses WHERE instructor_id=? AND cancelled=0",
            (r["user_id"],),
        ).fetchall()
        class_summaries = []
        for c in course_rows:
            grade_rows = db.execute(
                "SELECT grade FROM enrollments "
                "WHERE course_code=? AND semester=? AND grade IS NOT NULL",
                (c["code"], sem),
            ).fetchall()
            if not grade_rows:
                continue
            pts = [GRADE_POINTS.get(g["grade"], 0.0) for g in grade_rows]
            avg = round(sum(pts) / len(pts), 2)
            if avg > 3.5 or avg < 2.5:
                class_summaries.append({
                    "courseCode": c["code"],
                    "courseName": c["name"],
                    "classGpa":   avg,
                    "studentCount": len(pts),
                })
        out.append({
            "userId":         r["user_id"],
            "name":           r["name"],
            "warnings":       r["warnings"],
            "suspended":      bool(r["suspended"]),
            "fired":          bool(r["fired"]),
            "extremeClasses": class_summaries,
        })
    return jsonify(out)


@app.route("/api/registrar/instructor-action", methods=["POST"])
@auth_required("Registrar")
def registrar_instructor_action():
    """Take action on a flagged instructor: clear (accepted justification),
    warn, or fire."""
    data = request.get_json(silent=True) or {}
    uid = (data.get("userId") or "").strip()
    action = (data.get("action") or "").strip()  # clear | warn | fire
    reason = (data.get("reason") or "").strip()

    if action not in ("clear", "warn", "fire"):
        return jsonify({"ok": False, "msg": "Unknown action."})

    db = get_db()
    inst = db.execute("SELECT * FROM instructors WHERE user_id=?", (uid,)).fetchone()
    if not inst:
        return jsonify({"ok": False, "msg": "Instructor not found."})

    if action == "clear":
        db.execute("UPDATE instructors SET review_pending=0 WHERE user_id=?", (uid,))
        db.commit()
        return jsonify({"ok": True, "msg": f"Cleared {uid} — justification accepted."})
    if action == "warn":
        _issue_warning(db, uid, reason or "Class GPA out of [2.5, 3.5] without adequate justification.")
        db.execute("UPDATE instructors SET review_pending=0 WHERE user_id=?", (uid,))
        db.commit()
        return jsonify({"ok": True, "msg": f"Warned {uid}."})
    # fire
    db.execute(
        "UPDATE instructors SET fired=1, review_pending=0, suspended=1 WHERE user_id=?",
        (uid,),
    )
    # Reassign their courses' instructor_id to NULL so the registrar can re-assign.
    db.execute("UPDATE courses SET instructor_id=NULL WHERE instructor_id=?", (uid,))
    db.commit()
    return jsonify({"ok": True, "msg": f"Fired {uid}. Their courses now need a new instructor."})


@app.route("/api/registrar/clear-interview/<uid>", methods=["POST"])
@auth_required("Registrar")
def registrar_clear_interview(uid):
    db = get_db()
    db.execute("UPDATE students SET interview_pending=0 WHERE user_id=?", (uid,))
    db.commit()
    return jsonify({"ok": True, "msg": f"Interview cleared for {uid}."})


@app.route("/api/registrar/program-quota", methods=["POST"])
@auth_required("Registrar")
def registrar_set_quota():
    data = request.get_json(silent=True) or {}
    try:
        quota = int(data.get("quota") or 50)
    except (TypeError, ValueError):
        return jsonify({"ok": False, "msg": "Quota must be an integer."})
    if quota < 1:
        return jsonify({"ok": False, "msg": "Quota must be at least 1."})
    db = get_db()
    db.execute("UPDATE semester_state SET program_quota=? WHERE id=1", (quota,))
    db.commit()
    return jsonify({"ok": True, "msg": f"Program quota set to {quota}."})


# ── Student update / delete (issue 5) ──────────────────────────────────────

@app.route("/api/registrar/update-student", methods=["POST"])
@auth_required("Registrar")
def registrar_update_student():
    """Update any field of a student.

    Accepts (all optional): name, email, gpa, warnings, honorCount, suspended,
    terminated, graduated, interviewPending, fineDue, finePaid.
    """
    data = request.get_json(silent=True) or {}
    uid = (data.get("userId") or "").strip()
    if not uid:
        return jsonify({"ok": False, "msg": "userId is required."})

    db = get_db()
    s = db.execute(
        "SELECT u.user_id FROM users u JOIN students s ON s.user_id = u.user_id WHERE u.user_id=?",
        (uid,),
    ).fetchone()
    if not s:
        return jsonify({"ok": False, "msg": f"Student {uid} not found."}), 404

    # users.* updates
    user_upd, user_params = [], []
    if "name" in data and (data["name"] or "").strip():
        user_upd.append("name=?"); user_params.append(data["name"].strip())
    if "email" in data and (data["email"] or "").strip():
        user_upd.append("email=?"); user_params.append(data["email"].strip())
    if user_upd:
        user_params.append(uid)
        db.execute(f"UPDATE users SET {', '.join(user_upd)} WHERE user_id=?", user_params)

    # students.* updates
    fmap = {
        "gpa":              ("gpa",               float),
        "warnings":         ("warnings",          int),
        "honorCount":       ("honor_count",       int),
        "suspended":        ("suspended",         lambda v: 1 if v in (True, "true", 1) else 0),
        "terminated":       ("terminated",        lambda v: 1 if v in (True, "true", 1) else 0),
        "graduated":        ("graduated",         lambda v: 1 if v in (True, "true", 1) else 0),
        "interviewPending": ("interview_pending", lambda v: 1 if v in (True, "true", 1) else 0),
        "fineDue":          ("fine_due",          float),
        "finePaid":         ("fine_paid",         lambda v: 1 if v in (True, "true", 1) else 0),
        "suspendedUntil":   ("suspended_until",   int),
        "semestersCompleted": ("semesters_completed", int),
    }
    upd, params = [], []
    for key, (col, conv) in fmap.items():
        if key in data and data[key] is not None and data[key] != "":
            try:
                upd.append(f"{col}=?"); params.append(conv(data[key]))
            except (TypeError, ValueError):
                return jsonify({"ok": False, "msg": f"Invalid value for {key}."})
    if upd:
        params.append(uid)
        db.execute(f"UPDATE students SET {', '.join(upd)} WHERE user_id=?", params)

    if not user_upd and not upd:
        return jsonify({"ok": False, "msg": "Nothing to update."})

    db.commit()
    return jsonify({"ok": True, "msg": f"Student {uid} updated."})


@app.route("/api/registrar/delete-student/<uid>", methods=["DELETE"])
@auth_required("Registrar")
def registrar_delete_student(uid):
    """Permanently delete a student. Wraps cascade in PRAGMA toggling, mirroring
    MySQL's SET FOREIGN_KEY_CHECKS = 0/1."""
    db = get_db()
    row = db.execute(
        "SELECT 1 FROM users WHERE user_id=? AND role='Student'", (uid,)
    ).fetchone()
    if not row:
        return jsonify({"ok": False, "msg": f"Student {uid} not found."}), 404

    db.execute("PRAGMA foreign_keys = OFF")
    try:
        db.execute("DELETE FROM enrollments        WHERE student_id=?", (uid,))
        db.execute("DELETE FROM waitlist           WHERE student_id=?", (uid,))
        db.execute("DELETE FROM reviews            WHERE student_id=?", (uid,))
        db.execute("DELETE FROM complaints         WHERE from_id=? OR against_id=?", (uid, uid))
        db.execute("DELETE FROM warnings           WHERE user_id=?", (uid,))
        db.execute("DELETE FROM study_buddy_optins WHERE student_id=?", (uid,))
        db.execute("DELETE FROM students          WHERE user_id=?", (uid,))
        db.execute("DELETE FROM users             WHERE user_id=?", (uid,))
        db.commit()
    finally:
        db.execute("PRAGMA foreign_keys = ON")
    return jsonify({"ok": True, "msg": f"Student {uid} deleted."})


# ── Instructor CRUD (issue 6) ──────────────────────────────────────────────

@app.route("/api/registrar/create-instructor", methods=["POST"])
@auth_required("Registrar")
def registrar_create_instructor():
    """Create a new instructor record. Generates an I## ID and seeds the
    default password. Returns the new user."""
    data = request.get_json(silent=True) or {}
    name  = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip()
    if not name or not email:
        return jsonify({"ok": False, "msg": "Name and email are required."})

    db = get_db()
    if db.execute("SELECT 1 FROM users WHERE email=?", (email,)).fetchone():
        return jsonify({"ok": False, "msg": "Email already in use."})

    # Generate next I## id
    rows = db.execute("SELECT user_id FROM users WHERE user_id LIKE 'I%'").fetchall()
    nums = []
    for r in rows:
        m = re.match(r"I(\d+)$", r["user_id"])
        if m:
            nums.append(int(m.group(1)))
    nxt = (max(nums) if nums else 0) + 1
    uid = f"I{nxt:02d}"

    pw_hash = _hash_password(DEFAULT_PASSWORD)
    db.execute(
        "INSERT INTO users (user_id, name, email, password_hash, role, must_change_pw) "
        "VALUES (?, ?, ?, ?, 'Instructor', 1)",
        (uid, name, email, pw_hash),
    )
    db.execute("INSERT INTO instructors (user_id) VALUES (?)", (uid,))
    db.commit()
    return jsonify({
        "ok": True,
        "msg": f"Instructor {uid} created. Default password: {DEFAULT_PASSWORD}.",
        "userId": uid,
    })


@app.route("/api/registrar/update-instructor", methods=["POST"])
@auth_required("Registrar")
def registrar_update_instructor():
    """Update any field of an instructor.

    Accepts (all optional): name, email, warnings, suspended, fired,
    reviewPending. Triggers in database.py handle FK side-effects on `fired`.
    """
    data = request.get_json(silent=True) or {}
    uid = (data.get("userId") or "").strip()
    if not uid:
        return jsonify({"ok": False, "msg": "userId is required."})

    db = get_db()
    if not db.execute(
        "SELECT 1 FROM users WHERE user_id=? AND role='Instructor'", (uid,)
    ).fetchone():
        return jsonify({"ok": False, "msg": f"Instructor {uid} not found."}), 404

    # users.* updates
    user_upd, user_params = [], []
    if "name" in data and (data["name"] or "").strip():
        user_upd.append("name=?"); user_params.append(data["name"].strip())
    if "email" in data and (data["email"] or "").strip():
        user_upd.append("email=?"); user_params.append(data["email"].strip())
    if user_upd:
        user_params.append(uid)
        db.execute(f"UPDATE users SET {', '.join(user_upd)} WHERE user_id=?", user_params)

    # instructors.* updates
    fmap = {
        "warnings":      ("warnings",       int),
        "suspended":     ("suspended",      lambda v: 1 if v in (True, "true", 1) else 0),
        "fired":         ("fired",          lambda v: 1 if v in (True, "true", 1) else 0),
        "reviewPending": ("review_pending", lambda v: 1 if v in (True, "true", 1) else 0),
    }
    upd, params = [], []
    for key, (col, conv) in fmap.items():
        if key in data and data[key] is not None and data[key] != "":
            try:
                upd.append(f"{col}=?"); params.append(conv(data[key]))
            except (TypeError, ValueError):
                return jsonify({"ok": False, "msg": f"Invalid value for {key}."})
    if upd:
        params.append(uid)
        # The trigger `instructor_reassign_courses` nulls courses.instructor_id
        # when fired flips 0→1. So an UPDATE here may cascade — that's intended.
        db.execute(f"UPDATE instructors SET {', '.join(upd)} WHERE user_id=?", params)

    if not user_upd and not upd:
        return jsonify({"ok": False, "msg": "Nothing to update."})
    db.commit()
    return jsonify({"ok": True, "msg": f"Instructor {uid} updated."})


@app.route("/api/registrar/delete-instructor/<uid>", methods=["DELETE"])
@auth_required("Registrar")
def registrar_delete_instructor(uid):
    """Permanently delete an instructor. Their courses get instructor_id=NULL."""
    db = get_db()
    if not db.execute(
        "SELECT 1 FROM users WHERE user_id=? AND role='Instructor'", (uid,)
    ).fetchone():
        return jsonify({"ok": False, "msg": f"Instructor {uid} not found."}), 404

    db.execute("PRAGMA foreign_keys = OFF")
    try:
        db.execute("UPDATE courses SET instructor_id=NULL WHERE instructor_id=?", (uid,))
        db.execute("DELETE FROM complaints WHERE from_id=? OR against_id=?", (uid, uid))
        db.execute("DELETE FROM warnings WHERE user_id=?", (uid,))
        db.execute("DELETE FROM instructors WHERE user_id=?", (uid,))
        db.execute("DELETE FROM users WHERE user_id=?", (uid,))
        db.commit()
    finally:
        db.execute("PRAGMA foreign_keys = ON")
    return jsonify({"ok": True, "msg": f"Instructor {uid} deleted."})


@app.route("/api/registrar/instructor/<uid>", methods=["GET"])
@auth_required("Registrar")
def registrar_get_instructor(uid):
    """Detailed view of a single instructor for the edit page."""
    db = get_db()
    row = db.execute(
        "SELECT u.user_id, u.name, u.email, i.warnings, i.suspended, i.fired, i.review_pending "
        "FROM users u JOIN instructors i ON i.user_id = u.user_id "
        "WHERE u.user_id=?",
        (uid,),
    ).fetchone()
    if not row:
        return jsonify({"error": "Not found."}), 404
    courses = db.execute(
        "SELECT code, name, time_slot, capacity, is_core, cancelled "
        "FROM courses WHERE instructor_id=? ORDER BY code", (uid,),
    ).fetchall()
    return jsonify({
        "userId":        row["user_id"],
        "name":          row["name"],
        "email":         row["email"],
        "warnings":      row["warnings"],
        "suspended":     bool(row["suspended"]),
        "fired":         bool(row["fired"]),
        "reviewPending": bool(row["review_pending"]),
        "courses": [{
            "code":      c["code"],
            "name":      c["name"],
            "timeSlot":  c["time_slot"],
            "capacity":  c["capacity"],
            "isCore":    bool(c["is_core"]),
            "cancelled": bool(c["cancelled"]),
        } for c in courses],
    })


# ── Semester navigation (issue 2) ──────────────────────────────────────────

@app.route("/api/registrar/semesters", methods=["GET"])
@auth_required("Registrar")
def registrar_semesters():
    """Return the list of all known (semester, season, year) values plus the
    currently active semester id so the registrar can pick from a dropdown.

    Defensive de-duplication: if any two history rows share the same
    (season, year) — which can happen with legacy data created before the
    rollover sequence-number bug was fixed — collapse them to a single entry,
    preferring the row whose sequence number matches the currently active
    semester (so the dropdown's "(current)" tag stays accurate), and otherwise
    the most recent sequence number.
    """
    db = get_db()
    state = _state(db)
    rows = db.execute(
        "SELECT semester, season, year, closed_at FROM semester_history ORDER BY semester"
    ).fetchall()

    # Group by (season, year), preferring the current semester's row if present
    by_label = {}
    for r in rows:
        key = (r["season"], r["year"])
        existing = by_label.get(key)
        prefer = (
            existing is None
            or r["semester"] == state["semester"]
            or (existing["semester"] != state["semester"]
                and r["semester"] > existing["semester"])
        )
        if prefer:
            by_label[key] = r

    deduped = sorted(by_label.values(), key=lambda r: r["semester"])
    return jsonify({
        "current":  state["semester"],
        "semesters": [{
            "semester": r["semester"],
            "season":   r["season"],
            "year":     r["year"],
            "label":    _semester_label(r["season"], r["year"]),
            "closedAt": r["closed_at"],
            "isCurrent": r["semester"] == state["semester"],
        } for r in deduped],
    })


@app.route("/api/registrar/jump-semester", methods=["POST"])
@auth_required("Registrar")
def registrar_jump_semester():
    """Jump the active semester to a previous or future one.

    The semester must already be present in semester_history. Going backward
    is read-only navigation (the registrar can inspect data); going forward
    creates a new SETUP-phase semester if needed.
    """
    data = request.get_json(silent=True) or {}
    try:
        target = int(data.get("semester"))
    except (TypeError, ValueError):
        return jsonify({"ok": False, "msg": "semester (int) is required."})

    db = get_db()
    hist = db.execute(
        "SELECT season, year FROM semester_history WHERE semester=?", (target,)
    ).fetchone()
    if not hist:
        return jsonify({"ok": False, "msg": f"Semester {target} is not in history."})

    db.execute(
        "UPDATE semester_state SET semester=?, season=?, year=? WHERE id=1",
        (target, hist["season"], hist["year"]),
    )
    db.commit()
    return jsonify({
        "ok": True,
        "msg": f"Switched to {_semester_label(hist['season'], hist['year'])}.",
        "semester": target,
        "season":   hist["season"],
        "year":     hist["year"],
        "label":    _semester_label(hist["season"], hist["year"]),
    })


# ─── AI ─────────────────────────────────────────────────────────────────────
#
# Spec requirement: "An AI-enabled text area should be provided for users to
# ask questions about this system: visitors can ask general questions about
# classes and requirements; students can ask additional questions on classes
# s/he is taking; instructors can ask additional questions about students in
# his/her class(es). If no answers can be found in the local information
# store (vector DB), send it to the LLM for a possible answer (with a warning
# for possible hallucinations)."
#
# We implement this as:
#   1. A small "vector DB" of College0-specific documents indexed by
#      TF-IDF cosine similarity (computed lazily on first query).
#   2. Live data lookups for personalized questions (a student's own GPA,
#      an instructor's own students, etc).
#   3. Optional LLM fallback via the Anthropic API (set ANTHROPIC_API_KEY
#      to enable). If no key is set, the fallback honestly reports that no
#      local information matched and no LLM is configured.

# Knowledge base — College0's "local information not available to general LLMs."
# Each entry is (id, scope, document_text). Scope is the audience: "public",
# "student", "instructor".
KB_DOCUMENTS = [
    ("graduation_req", "public",
     "Graduation from College0 requires completing 8 courses including all 4 core courses: "
     "CSC 10100 (Intro to Computing), CSC 10200 (Intro to CS), CSC 21700 (Probability & "
     "Statistics), and CSC 22000 (Algorithms). Students need a cumulative GPA of at least "
     "2.0. Students apply for graduation themselves from the Reviews & More page. A reckless "
     "graduation application — submitting when requirements are not met — results in a warning."),
    ("warning_system", "public",
     "The College0 warning system works as follows. Students may accumulate warnings "
     "for various reasons: under-enrollment, taboo words in reviews, reckless graduation "
     "applications, complaints upheld against them, or instructor complaints. Three active "
     "warnings result in automatic suspension for one semester and a $250 fine that must be "
     "paid to the registrar before the suspension can be lifted at semester rollover. Each "
     "honor roll designation removes one warning from a student's record. Instructors also "
     "receive warnings — three warnings suspend them for the next semester. The system "
     "issues warnings automatically based on charter rules."),
    ("semester_phases", "public",
     "Each College0 semester has four phases plus a closing phase: Class Setup (registrars "
     "create courses and assign instructors), Registration (students register for 2-4 "
     "courses), Classes Running (no new registrations except special registration windows "
     "for displaced students from cancelled courses), Grading (instructors submit grades, "
     "students submit anonymous course reviews), and Closed (registrar advances to next "
     "semester)."),
    ("review_system", "public",
     "Course reviews are anonymous — only the registrar can see who wrote which review. "
     "Reviews must be submitted during the Grading phase, before the instructor posts the "
     "grade. Each review has a rating from 1 (worst) to 5 (best). Reviews containing 1 or 2 "
     "taboo words are shown with those words replaced by asterisks; the author receives one "
     "warning. Reviews with 3 or more taboo words are hidden entirely and the author "
     "receives two warnings."),
    ("waitlist", "public",
     "When a course reaches its capacity, students who try to register are added to a "
     "first-come-first-served waitlist. Only the course's instructor can admit students "
     "from the waitlist into the class."),
    ("gpa", "public",
     "GPA is the average of grade points across all graded courses. The grade scale is: "
     "A+ and A are 4.0, A- is 3.7, B+ is 3.3, B is 3.0, B- is 2.7, C+ is 2.3, C is 2.0, "
     "C- is 1.7, D is 1.0, and F is 0.0. Students may retake a course only if they "
     "previously received an F in it. Failing the same course twice results in automatic "
     "termination from the program. At semester close, students with GPA below 2.0 are "
     "terminated, students with GPA between 2.0 and 2.25 receive a warning and are flagged "
     "for an interview with the registrar."),
    ("registration_rules", "public",
     "During Registration phase, students may register for 2 to 4 courses. No time "
     "conflicts are allowed between chosen courses. If a course is full, the student joins "
     "its waitlist. Students with fewer than 2 enrolled courses at the end of Registration "
     "are warned. Courses with fewer than 3 enrolled students are cancelled, and those "
     "displaced students get a special registration window. Students may retake an F'd "
     "course but may not re-enroll in a course they already passed."),
    ("applications", "public",
     "Visitors apply to become students or instructors through the Apply page. Students "
     "with a current GPA above 3.0 are automatically accepted as long as the program "
     "quota is not reached. Approving below-threshold or over-quota applicants requires "
     "a written justification from the registrar. Rejecting a qualified applicant also "
     "requires justification. Newly approved students receive a tutorial on first login "
     "and must change their default password."),
    ("complaints", "public",
     "Students can file complaints against other students or against instructors. "
     "Instructors can file complaints against students. The registrar investigates each "
     "complaint. Crucially, complaints filed by instructors against students cannot be "
     "simply dismissed — the registrar must either punish the student or, if the "
     "complaint is unjustified, warn the instructor."),
    ("honor_roll", "public",
     "Students with a semester GPA above 3.75, or a cumulative GPA above 3.5 (after more "
     "than one completed semester), are automatically labeled honor roll students at "
     "semester close. Each honor roll status removes one active warning. Honor counts "
     "accumulate on the student's record."),
    ("instructor_oversight", "public",
     "Instructors whose course average GPA exceeds 3.5 or falls below 2.5 are flagged for "
     "registrar review at the end of the Grading phase. The registrar can clear them (with "
     "an accepted justification), warn them, or fire them outright. Instructors whose "
     "class average rating drops below 2 stars receive an automatic warning. Three "
     "warnings suspend an instructor for the next semester; fired instructors cannot teach."),
    ("suspension", "public",
     "A suspended student cannot register for courses, file complaints, or apply for "
     "graduation. Suspension lasts one semester and requires payment of a $250 fine "
     "before the suspension can be lifted at semester rollover. Suspended instructors "
     "cannot be assigned to teach any courses in the affected semester."),
    ("study_buddy", "public",
     "College0 offers a Study Buddy Matcher creative feature: students opt in by sharing "
     "a short bio and their general availability (e.g. 'evenings weekends'). The system "
     "ranks other opted-in classmates by shared courses (10 points each) and shared "
     "availability tokens (2 points each). Matches refresh in real time as students "
     "register for courses."),
]

# Lazy TF-IDF index, computed once and cached.
_KB_INDEX = None


_STOPWORDS = frozenset({
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "i", "you", "he", "she", "it", "we", "they", "me", "my", "your",
    "this", "that", "these", "those", "do", "does", "did", "have", "has",
    "had", "of", "in", "on", "at", "to", "for", "with", "by", "from",
    "and", "or", "but", "if", "then", "so", "as", "what", "where",
    "when", "why", "how", "who", "which", "whose", "would", "could",
    "should", "can", "may", "might", "will", "shall", "must",
})


def _tokenize(s: str):
    toks = re.findall(r"[a-z0-9]+", s.lower())
    return [t for t in toks if t not in _STOPWORDS and len(t) > 1]


def _build_kb_index():
    """Build a TF-IDF vector for each KB document. This is a *real* vector DB —
    each document is mapped to a sparse vector in vocabulary space, and queries
    are scored by cosine similarity. We use stdlib + math.log; no NumPy needed.
    """
    docs = [(doc_id, scope, text) for doc_id, scope, text in KB_DOCUMENTS]
    # Document-frequency
    df = Counter()
    tokenized = []
    for _, _, text in docs:
        toks = _tokenize(text)
        tokenized.append(toks)
        for w in set(toks):
            df[w] += 1
    N = len(docs)
    idf = {w: math.log((N + 1) / (c + 1)) + 1.0 for w, c in df.items()}

    # TF-IDF vectors per doc
    vectors = []
    for toks in tokenized:
        tf = Counter(toks)
        length = len(toks) or 1
        vec = {w: (tf[w] / length) * idf.get(w, 1.0) for w in tf}
        # L2 norm
        norm = math.sqrt(sum(v * v for v in vec.values())) or 1.0
        vec = {w: v / norm for w, v in vec.items()}
        vectors.append(vec)
    return {
        "docs": docs,
        "vectors": vectors,
        "idf": idf,
    }


def _embed_query(idx, q: str):
    toks = _tokenize(q)
    if not toks:
        return {}
    tf = Counter(toks)
    length = len(toks)
    vec = {w: (tf[w] / length) * idx["idf"].get(w, 1.0) for w in tf}
    norm = math.sqrt(sum(v * v for v in vec.values())) or 1.0
    return {w: v / norm for w, v in vec.items()}


def _cosine(a: dict, b: dict) -> float:
    if not a or not b:
        return 0.0
    # Iterate the smaller dict
    if len(a) > len(b):
        a, b = b, a
    return sum(v * b.get(w, 0.0) for w, v in a.items())


def _kb_search(question: str, scope_filter=None, top_k: int = 3):
    """Return top_k (score, doc_id, scope, text) entries from the KB."""
    global _KB_INDEX
    if _KB_INDEX is None:
        _KB_INDEX = _build_kb_index()
    qv = _embed_query(_KB_INDEX, question)
    if not qv:
        return []
    scored = []
    for (doc_id, scope, text), dv in zip(_KB_INDEX["docs"], _KB_INDEX["vectors"]):
        if scope_filter and scope not in scope_filter:
            continue
        s = _cosine(qv, dv)
        scored.append((s, doc_id, scope, text))
    scored.sort(reverse=True)
    return scored[:top_k]


def _personalized_answer(db, user, role, question: str):
    """Handle role-specific personalized questions that need live data lookups.

    Returns (answer_text, source) or (None, None) if no personalized handler matched.
    """
    q = question.lower()

    if role == "Student":
        if "my gpa" in q or ("gpa" in q and "my" in q):
            r = db.execute("SELECT gpa FROM students WHERE user_id=?",
                           (user["user_id"],)).fetchone()
            if r:
                return (f"Your current cumulative GPA is {r['gpa']:.2f}. "
                        f"A minimum GPA of 2.0 is required to remain in good standing.",
                        "live")
        if ("my class" in q or "my course" in q or "what am i taking" in q
                or "what classes am i" in q or "what courses am i" in q
                or "classes i'm taking" in q or "courses i'm taking" in q
                or ("enrolled" in q and "my" in q)):
            state = _state(db)
            rows = db.execute(
                "SELECT c.code, c.name, c.time_slot FROM enrollments e "
                "JOIN courses c ON c.code = e.course_code "
                "WHERE e.student_id=? AND e.semester=? AND e.status='enrolled'",
                (user["user_id"], state["semester"]),
            ).fetchall()
            if not rows:
                return ("You are not currently enrolled in any courses this semester.", "live")
            lines = [f"You are enrolled in {len(rows)} course(s) this semester:"]
            for r in rows:
                lines.append(f"  • {r['code']} — {r['name']} ({r['time_slot']})")
            return ("\n".join(lines), "live")
        if ("my warning" in q or ("warning" in q and "my" in q)
                or "warnings do i" in q or "many warnings" in q
                or "warnings i" in q):
            r = db.execute("SELECT warnings FROM students WHERE user_id=?",
                           (user["user_id"],)).fetchone()
            if r:
                return (f"You currently have {r['warnings']}/3 warnings. "
                        f"Three warnings result in automatic suspension for one semester "
                        f"and a $250 fine.", "live")

    if role == "Instructor":
        if ("my student" in q or "who is in my class" in q or "class roster" in q
                or "enrolled in my" in q):
            state = _state(db)
            rows = db.execute("""
                SELECT u.user_id, u.name, c.code, c.name AS course_name, s.gpa, e.grade
                FROM enrollments e
                JOIN courses c ON c.code = e.course_code
                JOIN users u ON u.user_id = e.student_id
                JOIN students s ON s.user_id = e.student_id
                WHERE c.instructor_id=? AND e.semester=? AND e.status='enrolled'
                ORDER BY c.code, u.name
            """, (user["user_id"], state["semester"])).fetchall()
            if not rows:
                return ("You have no enrolled students this semester.", "live")
            by_course = {}
            for r in rows:
                by_course.setdefault(r["code"], (r["course_name"], [])) [1].append(
                    f"  • {r['user_id']} {r['name']} (GPA {r['gpa']}, grade: {r['grade'] or '—'})"
                )
            lines = []
            for code, (cname, items) in by_course.items():
                lines.append(f"{code} — {cname}:")
                lines.extend(items)
            return ("\n".join(lines), "live")
        if "average" in q and "class" in q:
            state = _state(db)
            rows = db.execute("""
                SELECT c.code, e.grade
                FROM enrollments e JOIN courses c ON c.code = e.course_code
                WHERE c.instructor_id=? AND e.semester=? AND e.grade IS NOT NULL
            """, (user["user_id"], state["semester"])).fetchall()
            if not rows:
                return ("You have not graded any students this semester yet.", "live")
            by_course = {}
            for r in rows:
                by_course.setdefault(r["code"], []).append(GRADE_POINTS.get(r["grade"], 0.0))
            lines = ["Your class averages this semester:"]
            for code, pts in by_course.items():
                avg = sum(pts) / len(pts)
                lines.append(f"  • {code}: {avg:.2f} ({len(pts)} graded)")
            return ("\n".join(lines), "live")

    if role == "Registrar":
        # Spec: "a registrar can see everything." The registrar AI handles
        # cross-cutting administrative questions that need live DB lookups.

        # GPA / record lookup by student name or ID:
        #   "what is S101's GPA", "GPA of John Doe", "show me student S101"
        # Trigger on (gpa | student | record) + a candidate identifier in the
        # question (student ID like S\d+, or a name token that resolves).
        if ("gpa" in q or "record" in q or "student" in q):
            target = None
            # Try student ID pattern first (S followed by digits)
            id_match = re.search(r"\b([Ss]\d{2,4})\b", question)
            if id_match:
                sid = id_match.group(1).upper()
                target = db.execute(
                    "SELECT u.user_id, u.name, s.gpa, s.warnings, s.honor_count, "
                    "s.suspended, s.terminated, s.graduated "
                    "FROM users u JOIN students s ON s.user_id = u.user_id "
                    "WHERE u.user_id = ?", (sid,)).fetchone()
            # If no ID match, try name lookup (any student whose name is a
            # substring of the question, case-insensitive)
            if not target:
                candidates = db.execute(
                    "SELECT u.user_id, u.name, s.gpa, s.warnings, s.honor_count, "
                    "s.suspended, s.terminated, s.graduated "
                    "FROM users u JOIN students s ON s.user_id = u.user_id"
                ).fetchall()
                ql = q
                for c in candidates:
                    if c["name"].lower() in ql:
                        target = c
                        break
            if target:
                status_bits = []
                if target["graduated"]:  status_bits.append("graduated")
                if target["terminated"]: status_bits.append("terminated")
                if target["suspended"]:  status_bits.append("suspended")
                status = ", ".join(status_bits) if status_bits else "active"
                return (f"{target['user_id']} ({target['name']}): "
                        f"GPA {target['gpa']:.2f}, "
                        f"warnings {target['warnings']}/3, "
                        f"honor count {target['honor_count']}, "
                        f"status: {status}.", "live")

        # Pending applications count
        if "pending" in q and ("application" in q or "applicant" in q):
            row = db.execute(
                "SELECT COUNT(*) AS n FROM applications WHERE status='Pending'"
            ).fetchone()
            n = row["n"] if row else 0
            if n == 0:
                return ("There are no pending applications.", "live")
            by_role = db.execute(
                "SELECT role, COUNT(*) AS n FROM applications "
                "WHERE status='Pending' GROUP BY role"
            ).fetchall()
            lines = [f"There are {n} pending application(s):"]
            for r in by_role:
                lines.append(f"  • {r['role']}: {r['n']}")
            return ("\n".join(lines), "live")

        # Instructors with warnings (or specific instructor's warnings)
        if "instructor" in q and ("warning" in q or "warned" in q):
            # Specific instructor by ID?
            id_match = re.search(r"\b([Ii]\d{1,3})\b", question)
            if id_match:
                iid = id_match.group(1).upper()
                r = db.execute(
                    "SELECT u.name, i.warnings, i.suspended, i.fired "
                    "FROM users u JOIN instructors i ON i.user_id = u.user_id "
                    "WHERE u.user_id=?", (iid,)).fetchone()
                if r:
                    status = "fired" if r["fired"] else "suspended" if r["suspended"] else "active"
                    return (f"{iid} ({r['name']}): {r['warnings']}/3 warnings, "
                            f"status: {status}.", "live")
            # Otherwise: list all instructors with ≥1 warning
            rows = db.execute(
                "SELECT u.user_id, u.name, i.warnings, i.suspended, i.fired "
                "FROM users u JOIN instructors i ON i.user_id = u.user_id "
                "WHERE i.warnings > 0 "
                "ORDER BY i.warnings DESC, u.user_id"
            ).fetchall()
            if not rows:
                return ("No instructors currently have any warnings.", "live")
            lines = [f"{len(rows)} instructor(s) with warnings:"]
            for r in rows:
                tag = " [FIRED]" if r["fired"] else " [SUSPENDED]" if r["suspended"] else ""
                lines.append(f"  • {r['user_id']} {r['name']}: {r['warnings']}/3{tag}")
            return ("\n".join(lines), "live")

        # Courses below the 3-student cancellation threshold (running phase only,
        # but we report the count regardless — registrar can act on it)
        if ("course" in q or "class" in q) and (
                "below" in q or "under" in q or "cancel" in q or "low" in q
                or "fewer" in q or "less than" in q or "threshold" in q):
            state = _state(db)
            rows = db.execute("""
                SELECT c.code, c.name, COUNT(e.student_id) AS n_enrolled
                FROM courses c
                LEFT JOIN enrollments e
                  ON e.course_code = c.code
                 AND e.semester = ?
                 AND e.status = 'enrolled'
                WHERE c.cancelled = 0
                GROUP BY c.code, c.name
                HAVING COUNT(e.student_id) < 3
                ORDER BY n_enrolled, c.code
            """, (state["semester"],)).fetchall()
            if not rows:
                return ("All active courses have ≥3 enrolled students. "
                        "No courses are at risk of cancellation.", "live")
            lines = [f"{len(rows)} course(s) below the 3-student threshold "
                     f"(at risk of cancellation):"]
            for r in rows:
                lines.append(f"  • {r['code']} — {r['name']}: {r['n_enrolled']} enrolled")
            return ("\n".join(lines), "live")

        # Open complaint count
        if "complaint" in q and ("open" in q or "unresolved" in q or "pending" in q
                                  or "how many" in q):
            row = db.execute(
                "SELECT COUNT(*) AS n FROM complaints WHERE resolved = 0"
            ).fetchone()
            n = row["n"] if row else 0
            if n == 0:
                return ("There are no open complaints.", "live")
            # Break down by type
            by_type = db.execute(
                "SELECT type, COUNT(*) AS n FROM complaints "
                "WHERE resolved = 0 GROUP BY type"
            ).fetchall()
            lines = [f"There are {n} open complaint(s):"]
            for r in by_type:
                label = {
                    "instructor_vs_student": "instructor → student (mandatory action)",
                    "student_vs_student":    "student → student",
                    "student_vs_instructor": "student → instructor",
                }.get(r["type"], r["type"])
                lines.append(f"  • {label}: {r['n']}")
            return ("\n".join(lines), "live")

        # Waitlist for a specific course: "waitlist for CSC 22000"
        if "waitlist" in q:
            code_match = re.search(r"\b([A-Z]{2,4}\s*\d{3,5})\b", question)
            if code_match:
                code = code_match.group(1).upper().replace("  ", " ")
                rows = db.execute("""
                    SELECT w.position, u.user_id, u.name
                    FROM waitlist w
                    JOIN users u ON u.user_id = w.student_id
                    WHERE w.course_code = ?
                    ORDER BY w.position
                """, (code,)).fetchall()
                if not rows:
                    return (f"Waitlist for {code} is empty.", "live")
                lines = [f"Waitlist for {code} ({len(rows)} student(s)):"]
                for r in rows:
                    lines.append(f"  • #{r['position']}: {r['user_id']} {r['name']}")
                return ("\n".join(lines), "live")

        # Current semester / phase
        if ("current" in q or "what" in q) and ("semester" in q or "phase" in q
                                                  or "period" in q):
            state = _state(db)
            return (f"Current semester: {state.get('season', '')} {state.get('year', '')} "
                    f"(internal #{state['semester']}). "
                    f"Phase: {state['phase']}. "
                    f"Program quota: {state.get('program_quota', 'n/a')}.",
                    "live")

    return None, None


def _llm_fallback(question: str, context_docs):
    """Call Anthropic API (if ANTHROPIC_API_KEY is set) for a hallucination-warned answer.

    The retrieved KB docs are passed in as grounding. Returns (answer_text, ok)."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return (None, False)

    grounding = ""
    if context_docs:
        grounding = "Here is some College0 documentation that may or may not be relevant:\n\n"
        for score, doc_id, scope, text in context_docs:
            grounding += f"[{doc_id}] {text}\n\n"

    system_prompt = (
        "You are an assistant for the College0 student-management system. The information "
        "below is what is known about College0. If the user's question can be answered from "
        "this information, answer concisely and accurately. If it cannot, say so plainly "
        "and explain that you don't have the answer in your knowledge base.\n\n"
        + grounding
    )

    try:
        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": "claude-sonnet-4-5",
                "max_tokens": 400,
                "system": system_prompt,
                "messages": [{"role": "user", "content": question}],
            },
            timeout=15,
        )
        if resp.status_code != 200:
            return (None, False)
        body = resp.json()
        content = body.get("content", [])
        text = "".join(b.get("text", "") for b in content if b.get("type") == "text").strip()
        if not text:
            return (None, False)
        return (text, True)
    except Exception:
        return (None, False)


@app.route("/api/ai", methods=["POST"])
def api_ai():
    """Role-scoped AI assistant.

    Flow:
      1. Try a personalized live-data answer (e.g. "what is my GPA").
      2. Else search the local "vector DB" (TF-IDF) of College0 documents,
         filtered by scope (visitor/student/instructor).
      3. If the best local score is low and an Anthropic API key is set,
         fall back to the LLM with the retrieved docs as grounding.
      4. Otherwise return an honest "no answer found" message.
    """
    data = request.get_json(silent=True) or {}
    question = (data.get("question") or "").strip()
    if not question:
        return jsonify({"answer": "Please ask a question.", "source": "local", "local": True})

    user = _current_user()
    role = user["role"] if user else None

    db = get_db()

    # 1) Personalized live data
    if user:
        ans, src = _personalized_answer(db, user, role, question)
        if ans:
            return jsonify({"answer": ans, "source": "live", "local": True})

    # 2) Vector search over the KB. Scope is built dynamically from the user's
    #    role. Everyone gets "public" docs; authenticated users get their
    #    role-scoped docs as well; registrars get everything. No scoped docs
    #    exist in the KB today, but the filter is wired so they can be added
    #    later without re-plumbing this endpoint.
    scope = {"public"}
    if user:
        if role == "Student":
            scope.add("student")
        elif role == "Instructor":
            scope.add("instructor")
        elif role == "Registrar":
            scope.update({"student", "instructor", "registrar"})

    hits = _kb_search(question, scope_filter=scope, top_k=3)
    best_score = hits[0][0] if hits else 0.0

    # Empirically, TF-IDF cosine on these short docs is ~0.15–0.50 for good
    # matches when stopwords are stripped. Threshold: 0.15.
    if best_score >= 0.15:
        top_doc = hits[0]
        return jsonify({
            "answer": top_doc[3],
            "source": "local",
            "local":  True,
            "docId":  top_doc[1],
            "score":  round(float(best_score), 3),
        })

    # 3) Low confidence — try LLM fallback
    llm_text, ok = _llm_fallback(question, hits)
    if ok:
        return jsonify({
            "answer":  llm_text,
            "source":  "llm",
            "local":   False,
            "warning": "⚠️ This answer is from a general LLM and may include hallucinations. "
                       "Please verify with your registrar for anything policy-related.",
        })

    # 4) Honest "no answer" response
    return jsonify({
        "answer": ("I couldn't find a confident answer in College0's local knowledge base, "
                   "and no LLM fallback is configured. Try rephrasing your question, or "
                   "ask your registrar. Topics I can usually help with: graduation "
                   "requirements, warning system, semester phases, course reviews, "
                   "waitlists, GPA rules, registration, applications, complaints, "
                   "suspensions, instructor oversight, honor roll, and Study Buddy."),
        "source": "none",
        "local": True,
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
