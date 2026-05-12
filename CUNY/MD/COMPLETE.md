# College0 / CUNY0 — Complete

## Status: 100% Spec Compliant ✅

Every requirement in the project specification has been implemented end-to-end.
See `SPEC_COMPLIANCE.md` for a section-by-section traceability map.

## What Changed in This Pass

### Backend (`Backend/`)

- **`database.py`** — expanded schema:
  - `students` gained `suspended_until`, `fine_due`, `fine_paid`, `interview_pending`
  - `instructors` gained `fired`, `review_pending`
  - `semester_state` gained `program_quota`
  - `reviews` gained `visible_text`, `taboo_count`, `hidden`
  - New `study_buddy_optins` table for the creative feature

- **`app.py`** — 40 endpoints (was 33), all spec-compliant:
  - **Taboo word handling rewritten**: `_scan_taboo` now *counts* occurrences and returns a masked-with-asterisks string. 1–2 taboo words → 1 warning + asterisks; 3+ taboo words → 2 warnings + hidden from public.
  - **Time-conflict detection** added to `student_register`: `_parse_time_slot` + `_slots_conflict` handle strings like `MWF 9-10`, `TTh 1-2.30`.
  - **Auto-acceptance** for student applications (GPA > 3.0 + quota OK) in `registrar_approve_app`. Justifications required to override or to reject qualified applicants.
  - **`_advance_to_running`** implements the full REGISTRATION→RUNNING ruleset: under-enrolled student warnings, course cancellations, special-registration triggering, instructor warnings, instructor suspensions.
  - **`_advance_to_closed`** implements the full GRADING→CLOSED ruleset: ungraded-student warnings, class-GPA review flagging, student termination (GPA < 2.0 or twice-failed), interview flagging (GPA 2.0–2.25), honor roll (semester GPA > 3.75 or cumulative > 3.5 with > 1 sem).
  - **Public review reading** endpoint (`/api/public/course-reviews/<code>`) returns anonymized reviews — asterisked for 1–2 taboo, hidden for ≥3 taboo.
  - **Fine payment** (`/api/student/pay-fine`) lets suspended students pay before rollover.
  - **Instructor questioning workflow**: `/api/registrar/instructor-reviews` lists flagged instructors with their extreme-GPA classes; `/api/registrar/instructor-action` lets the registrar clear, warn, or fire.
  - **Real vector-DB AI assistant**: TF-IDF cosine over 13 College0-specific documents (stopword-filtered). Personalized live-data answers for students (my GPA, my classes, my warnings) and instructors (my students, my class averages). LLM fallback via Anthropic API (when `ANTHROPIC_API_KEY` is set) with hallucination warning. Honest "no answer" when no fallback available.

### Frontend (`Frontend/src/`)

- **New-student tutorial** (`TutorialModal`) shown after first-login password change. Role-specific multi-step content. Replayable from each dashboard.
- **Fine-payment UI** on `StudentDashboard` when suspended with a fine due.
- **Interview-pending banner** on `StudentDashboard` and indicator on `RegistrarStudents`.
- **"Read Reviews" tab** in `StudentActions`: students/visitors browse any course's anonymized reviews with asterisks visible.
- **"Study Buddy" tab** in `StudentActions`: the creative feature.
- **Phase-advance feedback** on `RegistrarDashboard` shows the `actions` array returned by the API — every automatic rule is surfaced to the registrar.
- **Program quota control** on `RegistrarDashboard`.
- **Faculty Review page** (new nav item for registrar): lists flagged instructors with their extreme-GPA classes and clear/warn/fire actions.
- **Reviews table** in `RegistrarActions` now shows the visible (masked) text alongside taboo count and hidden flag; the original text appears on hover.
- **AI assistant** updated with role-aware suggestions and clear source badges (Live Data / Knowledge Base / LLM Fallback / No Answer).

## Verified Behavior

End-to-end tests confirm:
- ✅ Full semester cycle: SETUP → REGISTRATION → RUNNING → GRADING → CLOSED → next-sem SETUP
- ✅ Time conflicts blocked (e.g. registering for `MWF 9.30-10.30` after `MWF 9-10`)
- ✅ Taboo flow: 1 taboo word → asterisks + 1 warning; 3 taboo words → hidden + 2 warnings → suspension + $250 fine; fine payment lifts suspension at rollover
- ✅ Instructor with class GPA = 4.0 correctly flagged for review
- ✅ Student with GPA < 2.0 automatically terminated
- ✅ Honor roll applied to students with semester GPA > 3.75
- ✅ AI: personalized "my GPA?" answered from live data; "what is the weather in Tokyo?" honestly declined
- ✅ Frontend builds cleanly (`npm run build` → 75.6 KB gzipped, zero warnings)

## Running It

See `Backend/README.md` for full setup. Quick start:

```bash
cd Backend
pip install -r requirements.txt
python app.py     # http://localhost:5001

# In a second terminal:
cd Frontend
npm install
npm start         # http://localhost:3000
```

Demo credentials: students `S101`–`S110` / `pass123`, instructors `I01`–`I03` / `pass123`, registrar `REG01` / `admin`.
