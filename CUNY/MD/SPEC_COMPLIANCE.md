# College0 — Spec Compliance Map

This document traces **every requirement from the project specification** to its
implementation in the codebase. Use this as a checklist for grading.

> Legend: ✅ implemented · 📍 location (file:section) · 🧪 how to verify

---

## 1. Four user roles

| Role | Login | Lands on |
|------|-------|----------|
| Visitor | none | Home page + Apply page + AI assistant |
| Student | S101–S110 / `pass123` | Student dashboard |
| Instructor | I01–I03 / `pass123` | Instructor dashboard |
| Registrar | REG01 / `admin` | Registrar overview |

✅ Implemented · 📍 `Backend/database.py:_seed` + `Frontend/src/components/Layout.jsx:NAV_ROLE`

---

## 2. Semester phases

Spec: SETUP → REGISTRATION → RUNNING → GRADING → CLOSED → next semester SETUP

✅ Implemented · 📍 `Backend/app.py:_advance_to_running`, `_advance_to_closed`, `_roll_over_semester` · 🧪 the **Registrar Overview** page advances through them; the returned `actions` array shows automatic rules being applied.

### Automatic rules at each transition

| Transition | Rule | Implemented? |
|-----------|------|--------------|
| REGISTRATION → RUNNING | Students enrolled in <2 courses → warning | ✅ `_advance_to_running` step 1 |
| REGISTRATION → RUNNING | Courses with <3 students → cancelled | ✅ step 2 |
| REGISTRATION → RUNNING | Displaced students get **special registration** window | ✅ step 4 |
| REGISTRATION → RUNNING | Instructors of cancelled courses → warning | ✅ step 3 |
| REGISTRATION → RUNNING | Instructors with ALL their courses cancelled → suspended | ✅ step 3 (after totaling) |
| GRADING → CLOSED | Ungraded students → instructor warned | ✅ `_advance_to_closed` step 1 |
| GRADING → CLOSED | Class GPA outside [2.5, 3.5] → instructor flagged for registrar review | ✅ step 2 |
| GRADING → CLOSED | Student GPA < 2.0 → terminated | ✅ step 3b |
| GRADING → CLOSED | Same course failed twice → terminated | ✅ step 3a |
| GRADING → CLOSED | Student GPA in [2.0, 2.25] → warning + interview flag | ✅ step 3c |
| GRADING → CLOSED | Semester GPA > 3.75 OR cumulative > 3.5 (after >1 sem) → honor roll (−1 warning) | ✅ step 3d |
| CLOSED → SETUP | Graded enrollments marked completed; ungraded dropped | ✅ `_roll_over_semester` |
| CLOSED → SETUP | Suspension lifted if `suspended_until` reached AND fine paid | ✅ `_roll_over_semester` |

---

## 3. Application & approval

Spec: visitor applies to be student or instructor. Students with GPA > 3.0 should be **automatically accepted** subject to program quota. Approving below-threshold or over-quota applicants requires justification. Rejecting a qualified applicant also requires justification.

| Behavior | Implemented? |
|----------|--------------|
| Apply form for student or instructor | ✅ `Frontend/.../ApplyPage` → POST `/api/apply` |
| Auto-accept rule (GPA > 3.0 + quota OK) | ✅ `registrar_approve_app` |
| Justification required to approve below threshold | ✅ same |
| Justification required to reject a qualified applicant | ✅ `registrar_reject_app` |
| Program quota is configurable | ✅ `/api/registrar/program-quota` + UI on Registrar Overview |
| New student receives default password + must change on first login | ✅ `users.must_change_pw=1` + LoginModal first-login flow |
| Tutorial shown after first login | ✅ `TutorialModal` (App.jsx triggers on `wasFirstLogin`) |

---

## 4. Registration phase rules

| Rule | Implemented? |
|------|--------------|
| Students may register for 2–4 courses | ✅ upper bound enforced in `student_register`; lower bound enforced at REGISTRATION→RUNNING |
| Time-conflict checking blocks overlapping courses | ✅ `_slots_conflict` checked before insertion |
| Full courses → first-come-first-served waitlist | ✅ `student_register` + `instructor_admit_waitlist` |
| Cannot re-register for a course already passed (grade != F) | ✅ `student_register` check |
| Failed (F) courses CAN be retaken | ✅ same check (excludes F from "passed" set) |
| Suspended students cannot register | ✅ `student_register` eligibility check |

---

## 5. Reviews & taboo words

Spec: anonymous reviews are submitted during the Grading phase, before the instructor posts the student's grade. Reviews with 1–2 taboo words → shown with asterisks + 1 warning to author. Reviews with ≥3 taboo words → hidden + 2 warnings.

| Behavior | Implemented? |
|----------|--------------|
| Reviews are anonymous to students/visitors (only registrar sees student_id) | ✅ `/api/public/course-reviews/<code>` doesn't return student_id |
| Reviews only during GRADING phase, before grade posted | ✅ `student_review` check |
| `_scan_taboo` counts occurrences AND returns asterisked text | ✅ `Backend/app.py` |
| 1–2 taboo → asterisks + 1 warning | ✅ `student_review` |
| ≥3 taboo → hidden from public + 2 warnings | ✅ `student_review` |
| Registrar can add/remove taboo words; existing reviews re-scan | ✅ `registrar_taboo`, `registrar_taboo_delete` |
| Public can read reviews for any course | ✅ `/api/public/course-reviews/<code>` + Read Reviews tab |

---

## 6. Warning & suspension system

Spec: 3 warnings → suspended for one semester + must pay a fine to the registrar.

| Behavior | Implemented? |
|----------|--------------|
| 3 active warnings → automatic suspension | ✅ `_issue_warning` |
| Suspension lasts one semester | ✅ `suspended_until = sem + 1` |
| $250 fine due upon suspension | ✅ `SUSPENSION_FINE = 250.0` |
| Student must pay fine before suspension lifts | ✅ `_roll_over_semester` requires `fine_paid=1` |
| Student-facing fine-payment UI | ✅ `StudentDashboard` Pay Fine button |
| Honor roll designation removes one warning | ✅ `_advance_to_closed` step 3d |

---

## 7. Complaints

| Behavior | Implemented? |
|----------|--------------|
| Student → student complaint | ✅ `/api/student/complaint` |
| Student → instructor complaint | ✅ same (auto-typed by target role) |
| Instructor → student complaint | ✅ `/api/instructor/complaint` |
| **Instructor complaints cannot be plain-dismissed** — registrar must punish or warn the instructor | ✅ `registrar_resolve_complaint` |
| Unjustified instructor complaint → warning issued to filer | ✅ `warn_instructor` action |

---

## 8. Instructor oversight

Spec: "extreme class GPAs (>3.5 or <2.5) get questioned by registrars; without adequate justifications, the instructor will be warned or fired right away."

| Behavior | Implemented? |
|----------|--------------|
| Extreme class GPA flags instructor at GRADING→CLOSED | ✅ `_advance_to_closed` step 2 (`review_pending=1`) |
| Registrar can clear / warn / fire flagged instructors | ✅ `/api/registrar/instructor-action` + Faculty Review page |
| Fired instructors: their courses get `instructor_id=NULL` for reassignment | ✅ same handler |
| 3 instructor warnings → suspended (no fine per spec) | ✅ `_issue_warning` for Instructor role |
| Suspended/fired instructors can't be assigned to new courses | ✅ `registrar_create_course` check |

---

## 9. Grading

| Behavior | Implemented? |
|----------|--------------|
| Only during GRADING phase | ✅ `instructor_grade` |
| Only for own courses | ✅ same |
| Failing to grade everyone → warning to instructor at phase close | ✅ `_advance_to_closed` step 1 |
| Grades recompute student GPA immediately | ✅ `_recompute_gpa` |

---

## 10. Graduation

Spec: 8 courses including 4 core; cumulative GPA ≥ 2.0. Reckless applications get a warning.

| Behavior | Implemented? |
|----------|--------------|
| Requirements checked | ✅ `student_graduate` |
| Reckless application (requirements unmet) → warning | ✅ `student_graduate` issues warning when not eligible |

---

## 11. AI Assistant

Spec: "An AI-enabled text area for users to ask questions about this system: visitors can ask general questions about classes and requirements; students can ask additional questions on classes s/he is taking; instructors can ask additional questions about students in his/her class(es). If no answers can be found in the local information store (vector DB), send it to the LLM for a possible answer (with a warning for possible hallucinations)."

| Behavior | Implemented? |
|----------|--------------|
| Local vector DB (TF-IDF cosine) over 13 College0 documents | ✅ `KB_DOCUMENTS`, `_build_kb_index`, `_kb_search` |
| Personalized live-data answers for students (my GPA, my classes, my warnings) | ✅ `_personalized_answer` |
| Personalized live-data answers for instructors (my students, my class average) | ✅ same |
| Visitors get general questions only (no live-data lookups) | ✅ `_personalized_answer` only runs when authenticated |
| LLM fallback via Anthropic API if `ANTHROPIC_API_KEY` set | ✅ `_llm_fallback` |
| LLM responses tagged with hallucination warning | ✅ `warning` field on response + `Frontend AIPage` LLM-source badge |
| If no LLM key set, honest "no answer" instead of hallucination | ✅ `api_ai` |

The AI page shows different badges based on the source:
- **Personalized · Live Data** (green) — answered from your own record
- **Knowledge Base** (navy) — TF-IDF retrieval from local docs
- **LLM Fallback** (amber, with hallucination warning) — when no local match
- **No Answer** (red) — honest fallback when LLM is not configured

---

## 12. Creative feature: Study Buddy Matcher

A College0-exclusive: students opt in by sharing a short bio + availability tokens, and the system suggests classmates in the same courses ranked by:

- **10 pts** per shared current-semester course
- **2 pts** per shared availability token (e.g. "evenings", "weekends")

Available at `/api/student/study-buddy` (GET / POST / DELETE) and as a tab inside Reviews & More.

---

## 13. New student tutorial

Spec: "Once approved, the system provides a tutorial to introduce the functionalities to the student/instructor."

✅ Implemented · 📍 `TutorialModal` shown after first-login password change. Role-specific content with multi-step navigation. Can be replayed from the dashboard.

---

## 14. Authentication

| Behavior | Implemented? |
|----------|--------------|
| JWT in `Authorization: Bearer <token>` header | ✅ `_make_token`, `auth_required` decorator |
| 24-hour token TTL | ✅ `JWT_TTL_HOURS = 24` |
| Default password = `pass123`; new users get `must_change_pw=1` | ✅ `database.DEFAULT_PASSWORD` |
| First-login flow: change password before anything else | ✅ `LoginModal` `firstLogin` state |
| Passwords hashed with PBKDF2 (werkzeug) | ✅ `generate_password_hash` / `check_password_hash` |

---

## 15. Sample data

Pre-seeded on first boot of an empty database:

- 1 Registrar (REG01)
- 3 Instructors (I01–I03)
- 10 Students (S101–S110) with varied GPAs (1.90–3.92), warnings (0–2), honors (0–2)
- 8 Courses including the 4 cores expected by the frontend's graduation check
- 4 taboo words: damn, stupid, idiot, hate
