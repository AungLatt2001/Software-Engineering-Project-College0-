# College0 — Academic Portal (CUNYFirst Clone)

## Project Overview
A full-stack academic management portal built as the CSC32200 final project. Replicates the CUNYFirst experience under the "College0" brand.

## Tech Stack
- **Backend**: Python 3 + Flask (JSON REST API)
- **Database**: SQLite (via `database.py`, schema matches official `schema_1777831771141.sql`)
- **Frontend**: React 18 + React Router v6 + Axios (built into `client/build/`)
- **Auth**: Flask sessions + Werkzeug password hashing (login by email)
- **Server**: Flask serves both the `/api/` JSON routes AND the built React SPA on port 5000

## Demo Credentials (all passwords: `Password123!`)
| Role | Email |
|------|-------|
| Student | liam.turner@college0.edu |
| Student | aisha.patel@college0.edu |
| Student | priya.sharma@college0.edu |
| Instructor | alan.brooks@college0.edu |
| Registrar | diana.morgan@college0.edu |

## All Users
| ID | Name | Role |
|----|------|------|
| 1 | Diana Morgan | registrar |
| 2 | Carlos Reyes | registrar |
| 3 | Alan Brooks | instructor |
| 4 | Sandra Kim | instructor |
| 5 | Robert Nguyen | instructor |
| 6 | Fatima Hassan | instructor |
| 7 | Liam Turner | student |
| 8 | Aisha Patel | student |
| 9 | Marcus Johnson | student |
| 10 | Sofia Diaz | student |
| 11 | Ethan Lee | student |
| 12 | Priya Sharma | student |
| 13 | Noah Wilson | student (suspended) |
| 14 | Chloe Adams | student |
| 15 | James Clark | student |

## React Pages (client/src/pages/)
| Route | Component | Description |
|-------|-----------|-------------|
| `/` | Home.jsx | Stats, top rated, course catalogue |
| `/apply` | Apply.jsx | Public visitor application form |
| `/ai-assistant` | AIAssistant.jsx | AI Q&A about the portal |
| `/dashboard` | Dashboard.jsx | Student dashboard (GPA, warnings, enrolled) |
| `/my-courses` | MyCourses.jsx | Enrollment management |
| `/transcript` | Transcript.jsx | Grade history + GPA stats |
| `/reviews` | Reviews.jsx | Course reviews, graduation, complaints (tabbed) |
| `/instructor` | Instructor.jsx | Instructor classes + grade entry |
| `/registrar` | Registrar.jsx | Admin panel — phase, students, applications, complaints |

## Flask API Routes (/api/...)
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/me` | GET | Current session user + active semester |
| `/api/sem` | GET | Active semester info |
| `/api/login` | POST | Login with email + password |
| `/api/logout` | POST | Clear session |
| `/api/home` | GET | Home page stats + sections |
| `/api/dashboard` | GET | Student dashboard data |
| `/api/my-courses` | GET/POST | Enrollment data; enroll/drop |
| `/api/transcript` | GET | Grade history |
| `/api/reviews/data` | GET | Sections + potential complaint targets |
| `/api/reviews/review` | POST | Submit course review |
| `/api/reviews/graduation` | POST | Submit graduation application |
| `/api/reviews/complaint` | POST | Submit complaint |
| `/api/ai` | POST | AI assistant query |
| `/api/instructor` | GET | Instructor's sections + enrolled students |
| `/api/instructor/grade` | POST | Post/update student grade |
| `/api/registrar` | GET | All registrar data |
| `/api/registrar/phase` | POST | Change semester phase |
| `/api/registrar/application/<id>` | POST | Approve/reject visitor application |
| `/api/registrar/complaint/<id>` | POST | Resolve/dismiss complaint |
| `/api/registrar/graduation/<id>` | POST | Approve/reject graduation app |
| `/api/registrar/warning` | POST | Issue manual warning |
| `/api/apply` | POST | Public visitor application submission |

## File Structure
```
app.py              Flask app — JSON API routes + serves React build
database.py         Official schema (16 tables) + seed data
collegeo.db         SQLite database (auto-created on startup)
requirements.txt    Flask, Werkzeug
client/
  package.json      React 18 + react-router-dom + axios + react-scripts
  src/
    App.jsx         Router setup + AuthContext
    api.js          Axios instance (baseURL=/api, withCredentials)
    index.css       All styles (Inter font, navy theme)
    components/
      Layout.jsx    Topbar + sidebar navigation
      LoginModal.jsx Email/password login modal
    pages/          One component per page (see table above)
  build/            Production build (served by Flask)
attached_assets/
  schema_1777831771141.sql   Official 16-table MySQL schema
  sample_1777831766120.sql   Official seed data
GUI/                Original UI mockup PNGs (reference)
```

## Official Database Schema (16 Tables)
User → Student / Instructor / Registrar (generalization)
- `User` — all users with email, role, status, warning_count
- `Student` — cumulative_gpa, semester_gpa, honor_count, fine_due
- `Instructor` — specialization, rating_average
- `Registrar` — admin_level
- `Semester` — term_name, year, phase (setup/registration/running/grading/closed)
- `Course` — code, title, credit_hours, is_core
- `ClassSection` — links Semester + Course + Instructor, capacity, status
- `Enrollment` — Student ↔ ClassSection (enrolled/dropped/completed/failed)
- `WaitlistEntry` — Student ↔ ClassSection with position
- `GradeRecord` — letter_grade, grade_points per Enrollment (1:0..1)
- `Review` — Student rates ClassSection (1–5 stars, visibility_status)
- `Complaint` — filed_by_user_id → target_user_id, status
- `WarningRecord` — user_id, reason, source_module, active_flag
- `GraduationApplication` — student_id, decision_status
- `VisitorApplication` — public applications (student/instructor)
- `AIQuery` — logs all AI assistant queries

## Rebuilding the React Frontend
```bash
cd client
npm install --legacy-peer-deps
npm install ajv@8 --legacy-peer-deps
GENERATE_SOURCEMAP=false npm run build
```
Then restart the workflow (`python app.py`).

## Semester Phases
- **setup** — Admin configures sections; no enrollment
- **registration** — Students can enroll/drop courses
- **running** — Classes in session
- **grading** — Instructors post grades; students submit reviews
- **closed** — Semester archived
