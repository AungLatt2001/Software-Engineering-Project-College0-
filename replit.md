# Collegeo — Academic Portal (CUNYFirst Clone)

## Project Overview
A full-stack academic management portal built as the CSC32200 final project. Replicates the CUNYFirst experience under the "Collegeo" brand.

## Tech Stack
- **Backend**: Python 3 + Flask
- **Database**: SQLite (via `database.py`)
- **Frontend**: Jinja2 templates + vanilla CSS/JS
- **Auth**: Flask sessions + Werkzeug password hashing
- **Server**: Flask dev server on port 5000

## User Roles & Demo Credentials (all passwords: `pass123`)
| Role | IDs |
|------|-----|
| Student | S101–S110 |
| Instructor | I01–I03 |
| Registrar | REG01 or admin |

## Pages / Routes
| Route | Description |
|-------|-------------|
| `/` | Public home — stats, top rated courses, course catalogue |
| `/login` (POST) | Login handler → redirects by role |
| `/logout` | Clear session |
| `/apply` | Public application form |
| `/dashboard` | Student dashboard (GPA, warnings, enrolled, completed) |
| `/my-courses` | Student course list + enrollment (Registration phase only) |
| `/transcript` | Student grade history + GPA |
| `/reviews` | Course reviews, graduation request, complaints |
| `/ai-assistant` | AI Q&A about the portal |
| `/instructor` | Instructor's classes + grade entry (Grading phase) |
| `/registrar` | Admin panel — phase control, students, applications, complaints |

## File Structure
```
app.py              Flask app + all routes
database.py         DB schema, init, and seed data
collegeo.db         SQLite database (auto-created)
requirements.txt    Flask, Werkzeug
templates/
  base.html         Shared layout (topbar, sidebar, login modal)
  home.html         Public home page
  apply.html        Application form
  dashboard.html    Student dashboard
  my_courses.html   Enrollment management
  transcript.html   Grade history
  reviews.html      Reviews/Graduation/Complaints tabs
  ai_assistant.html AI Q&A
  instructor.html   Instructor grade panel
  registrar.html    Admin control panel
static/
  css/style.css     All styles (Inter font, navy/white theme)
  js/app.js         Login modal JS
GUI/                Original UI mockup PNGs (reference)
```

## Semester Phases
- **Setup** — Admin configures courses; no enrollment or reviews
- **Registration** — Students can enroll/drop courses
- **Grading** — Instructors assign grades; students submit reviews

## Database Schema
- `users` — all users (students, instructors, registrar)
- `students` — GPA, warnings, honor count per student
- `courses` — course catalogue
- `enrollments` — student ↔ course with grade/points
- `reviews` — anonymous course ratings
- `complaints` — student complaints
- `graduation_requests` — graduation applications
- `applications` — new user applications
- `semester_config` — current semester number + phase
