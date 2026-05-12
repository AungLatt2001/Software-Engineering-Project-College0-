# 🚀 College0 Ready-to-Go Checklist

## ✅ Installation Complete

- [x] `Backend/app.py` — Rewritten (50 KB, 990 lines, 33 endpoints)
- [x] `Backend/database.py` — Created (12 KB, SQLite schema + seed)
- [x] `Backend/requirements.txt` — Created
- [x] `Frontend/package.json` — Updated (proxy → :5001)
- [x] All Python dependencies installed
- [x] All 136 end-to-end tests passing
- [x] Port changed from 5000 to 5001 (macOS Airplay fix)

## 🎯 Launch Immediately

### On Your Mac (Two Terminals)

**Terminal 1:**
```bash
cd CUNY0/Backend
python app.py
```
(Wait for: `Running on http://127.0.0.1:5001`)

**Terminal 2:**
```bash
cd CUNY0/Frontend
npm install  # First time only
npm start
```
(Wait for: `Compiled successfully!`)

**Then:** Open http://localhost:3000 in your browser

### Demo Login
- User: **S101**
- Password: **pass123**

## 📋 What Works Out of the Box

### Students
- ✅ View dashboard, GPA, warnings, honors
- ✅ Register/drop courses (max 4 per semester)
- ✅ Enroll in courses, join waitlist
- ✅ View grades and transcript
- ✅ Submit course reviews (anonymous, during Grading phase)
- ✅ Apply for graduation
- ✅ File complaints
- ✅ Change password
- ✅ Ask AI questions (personal GPA lookup)

### Instructors
- ✅ View assigned courses and enrolled students
- ✅ Submit grades (during Grading phase)
- ✅ Admit students from waitlist
- ✅ File complaints against students
- ✅ View their course sections

### Registrar
- ✅ Advance semester phases (SETUP → REGISTRATION → RUNNING → GRADING → CLOSED)
- ✅ View all students, courses, applications, complaints
- ✅ Approve/reject visitor applications (with justification for low GPA)
- ✅ Create courses, assign instructors
- ✅ Issue warnings, resolve complaints
- ✅ Manage taboo word list (auto-flags flagged reviews)
- ✅ View course reviews and ratings

## 🔌 Port Configuration

**Default: 5001** (to avoid macOS Airplay on 5000)

To change: `PORT=5002 python app.py`

Frontend automatically uses correct port via `package.json` proxy.

## 🗄️ Database

**File:** `CUNY0/Backend/college0.db` (SQLite, auto-created on first run)

**Reset:** `rm CUNY0/Backend/college0.db` then restart backend

**Data:** 10 students, 3 instructors, 1 registrar, 8 courses (all seeded)

## 🌐 Deploy to Internet

### Render (Easiest — 3 minutes)

1. Push CUNY0 to GitHub
2. Go to Render.com
3. New → Blueprint
4. Select this GitHub repository
5. Render reads `render.yaml` and deploys automatically
6. → You get a public HTTPS URL

### Docker (Any Host)

```bash
cd CUNY0
docker build -t college0 .
docker run -p 5001:5001 \
  -e COLLEGE0_SECRET="$(openssl rand -hex 32)" \
  college0
```

Then share the URL with anyone on the internet.

## 🧪 Verify Everything Works

```bash
cd CUNY0/Backend && python test_e2e.py
```

Expected: `Result: 136 passed, 0 failed`

## 📚 Documentation

- **Quick start:** `QUICK_START.md` (Mac-specific)
- **Backend API:** `Backend/README.md`
- **Installation:** `INSTALLATION_COMPLETE.md` (this folder)
- **Code:** `Backend/app.py` (well-commented throughout)

## 🚨 Important Notes

### Development Mode

- Backend runs on **:5001**
- Frontend runs on **:3000**
- Frontend proxies `/api/*` calls to `:5001` automatically
- Hot reload enabled on both

### Production Mode

- Single process (gunicorn)
- Serves both API and React build from one origin
- Set `COLLEGE0_SECRET` to a long random string (required)
- Use persistent volume for `college0.db`

### Demo Users

All passwords: **`pass123`** (except Registrar: **`admin`**)

```
Students:     S101, S102, ..., S110
Instructors:  I01, I02, I03
Registrar:    REG01
```

## ⚡ Quick Commands

| Task | Command |
|------|---------|
| Start backend | `cd CUNY0/Backend && python app.py` |
| Start frontend | `cd CUNY0/Frontend && npm start` |
| Reset database | `rm CUNY0/Backend/college0.db` |
| Run tests | `cd CUNY0/Backend && python test_e2e.py` |
| Build Docker | `cd CUNY0 && docker build -t college0 .` |
| Change port | `PORT=5002 python app.py` |
| View database | `sqlite3 CUNY0/Backend/college0.db` |

## 🎓 Demo Workflow (5 minutes)

1. Login as **S101 / pass123** (student)
2. Click **My Courses** → **Register** for 2–3 courses
3. Logout, login as **REG01 / admin** (registrar)
4. Click **Advance Phase** to move from SETUP → REGISTRATION → RUNNING → GRADING
5. Logout, login as **I01 / pass123** (instructor)
6. Click **Submit Grades** → grade the students
7. Logout, login as **S101 / pass123** again
8. Click **Transcript** → see your grades updated in real-time
9. Ask the **AI Assistant** "What are the graduation requirements?"

## ✨ You're All Set!

Everything is installed, tested, and ready to use. Just run the two commands above and you're live.

Questions? Check the README files or look at `Backend/app.py` — it's well-documented.

**Ready to share with the world?** Deploy to Render (3 minutes) and you'll have a public URL.

---

**Status:** 🟢 **READY TO LAUNCH**
