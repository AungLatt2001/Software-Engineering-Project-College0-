# College0 / CUNY0 — Quick Start Guide

Get the app running on your Mac in 5 minutes.

## Prerequisites

- **Python 3.10+**: `python3 --version`
- **Node 18+**: `node --version`
- **Git** (to clone if needed)

If you don't have them:
- Python: `brew install python@3.12`
- Node: `brew install node`

## Step 1: Terminal 1 — Start the Backend

```bash
cd Backend
pip install -r requirements.txt
python app.py
```

You should see:
```
 * Running on http://127.0.0.1:5001
```

**Note:** Port 5001 is used because macOS Airplay occupies 5000. You can override with `PORT=5000 python app.py` if you disable Airplay.

The first run auto-creates `college0.db` and seeds demo users.

## Step 2: Terminal 2 — Start the Frontend

```bash
cd Frontend
npm install
npm start
```

You should see:
```
Compiled successfully!
On Your Network: http://192.x.x.x:3000
```

Open http://localhost:3000 in your browser.

## Demo Login Credentials

All passwords are **`pass123`** except the registrar (**`admin`**).

| Role       | User ID | Password  |
| ---------- | ------- | --------- |
| Student    | S101    | pass123   |
| Instructor | I01     | pass123   |
| Registrar  | REG01   | admin     |

Try S101 first — you'll see the student dashboard with courses and registration.

## Reset the Database

The database lives at `Backend/college0.db`. To start fresh:

```bash
rm Backend/college0.db
# Then restart the backend (it'll recreate everything)
```

## Troubleshooting

### "Port 5001 is already in use"

```bash
# Find what's using it
lsof -i :5001
# Kill it (if safe)
kill -9 <PID>
# Or use a different port
PORT=5002 python app.py
```

### "npm ERR! ERESOLVE unable to resolve dependency tree"

```bash
cd Frontend
npm install --legacy-peer-deps
npm start
```

### "ModuleNotFoundError" or "ImportError" in the backend

```bash
cd Backend
pip install --break-system-packages -r requirements.txt
```

### Frontend shows "Backend build not found"

This is expected in dev mode — the frontend dev server proxies to the backend. Make sure both are running (see Step 1 and 2).

## Next Steps

- **Deploy:** See `../render.yaml` for one-click deployment to Render
- **Modify schema:** Edit `Backend/database.py` and restart
- **Add features:** New endpoints in `Backend/app.py`, new pages in `Frontend/src/pages/Pages.jsx`
- **Run tests:** `cd Backend && python test_e2e.py` (136 passing tests)

## Architecture

```
┌─ Frontend (React SPA) ─────────────────────┐
│ http://localhost:3000                      │
│ ├─ Pages.jsx (all role dashboards)        │
│ ├─ AuthContext.js (JWT login)             │
│ └─ Components (Layout, UI, Tables, etc.)   │
└────────────────────────────────────────────┘
          ↑
          │ proxies /api/* to
          ↓
┌─ Backend (Flask API) ──────────────────────┐
│ http://localhost:5001                      │
│ ├─ app.py (33 endpoints)                  │
│ ├─ database.py (SQLite schema + seed)     │
│ └─ JWT auth + role-based access control   │
└────────────────────────────────────────────┘
          ↓
┌─ SQLite Database ─────────────────────────┐
│ Backend/college0.db                       │
│ ├─ users, students, instructors           │
│ ├─ courses, enrollments, waitlist         │
│ ├─ reviews, complaints, applications      │
│ └─ semester_state (phase, semester #)     │
└────────────────────────────────────────────┘
```

## Common Tasks

### View current semester phase
```bash
sqlite3 Backend/college0.db "SELECT phase, semester FROM semester_state;"
```

### List all enrolled students
```bash
sqlite3 Backend/college0.db "SELECT u.user_id, u.name, COUNT(*) FROM enrollments e JOIN users u ON u.user_id = e.student_id GROUP BY e.student_id;"
```

### Manually advance the semester
Use the Registrar dashboard (REG01 / admin), click "Advance Phase →". This cycles:
SETUP → REGISTRATION → RUNNING → GRADING → CLOSED → (next semester SETUP)

### Back up your data
```bash
cp Backend/college0.db Backend/college0.db.backup
```

---

**Questions?** Check `Backend/README.md` for deployment, or look at `Backend/app.py` (well-commented, ~990 lines) for the full API contract.

**Ready to deploy?** Push to GitHub and use Render's Blueprint feature with `render.yaml` — you'll have a public HTTPS URL in ~3 minutes.
