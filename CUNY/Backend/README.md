# College0 / CUNY0 — Backend

A Flask app that exposes the JSON API consumed by the React frontend in
`../Frontend/`. It also serves the React build in production.

## What's in here

| File              | Purpose                                                                       |
| ----------------- | ----------------------------------------------------------------------------- |
| `app.py`          | Flask app: every endpoint the frontend calls, plus auth and the SPA fallback. |
| `database.py`     | SQLite schema, connection management, and seed data.                          |
| `requirements.txt`| Python dependencies pinned to compatible major versions.                      |

## Run it locally (two-process dev mode)

You need Python 3.10+ and Node 18+.

**Backend:**

```bash
cd Backend
pip install -r requirements.txt
python app.py
```

The first run creates `college0.db` and seeds demo accounts. Subsequent runs
preserve the DB file. To reset everything: delete `college0.db` and restart.

**Frontend (in a second terminal):**

```bash
cd Frontend
npm install
npm start
```

The dev server runs on http://localhost:3000 and proxies `/api/*` calls to
http://localhost:5001 (configured by `Frontend/package.json`'s `proxy`).

## Run it locally (single-process production mode)

Build the frontend once, then run only the Flask app — it serves both the API
and the React build:

```bash
cd Frontend && npm install && npm run build && cd ..
cd Backend && pip install -r requirements.txt && python app.py
```

Open http://localhost:5001.

## Enabling LLM fallback in the AI assistant

The AI assistant tries a local TF-IDF vector search first. If no document
scores above the confidence threshold, it can optionally fall back to a real
LLM. Set `ANTHROPIC_API_KEY` in the environment to enable this:

```bash
export ANTHROPIC_API_KEY=sk-ant-...
python app.py
```

Without the key, the AI honestly reports that it couldn't find a confident
answer in the local KB — no hallucinated guesses.

## Deploy to the internet

The simplest path is the included Dockerfile + `render.yaml` at the project root.

**Render (free tier works for a demo):**
1. Push this repo to GitHub.
2. On Render, click "New → Blueprint", point it at the repo.
3. Render reads `render.yaml`, builds the Docker image, and gives you a
   public HTTPS URL. The included config provisions a 1 GB persistent disk
   for the SQLite file at `/data/college0.db`.

**Any Docker host (Fly.io, Railway, a VPS, Kubernetes, etc.):**
```bash
docker build -t college0 .
docker run -p 8080:5000 \
  -e COLLEGE0_SECRET="$(openssl rand -hex 32)" \
  -v college0_data:/data \
  college0
```

## Demo credentials

All seeded users have password `pass123`, except the registrar whose password
is `admin`.

| Role       | User IDs               |
| ---------- | ---------------------- |
| Student    | S101 – S110            |
| Instructor | I01, I02, I03          |
| Registrar  | REG01                  |

## API surface

All endpoints are under `/api/`. JWT auth is sent in the `Authorization: Bearer <token>`
header — the frontend's `AuthContext.js` does this automatically after login.

| Method     | Path                                       | Role        |
| ---------- | ------------------------------------------ | ----------- |
| GET        | `/api/public`                              | anyone      |
| GET        | `/api/public/course-reviews/<code>`        | anyone      |
| POST       | `/api/login`                               | anyone      |
| POST       | `/api/change-password`                     | any user    |
| POST       | `/api/apply`                               | anyone      |
| POST       | `/api/ai`                                  | anyone      |
| GET        | `/api/student/me`                          | Student     |
| GET        | `/api/student/courses`                     | Student     |
| POST       | `/api/student/register`                    | Student     |
| POST       | `/api/student/drop`                        | Student     |
| GET        | `/api/student/grades`                      | Student     |
| POST       | `/api/student/review`                      | Student     |
| POST       | `/api/student/graduate`                    | Student     |
| POST       | `/api/student/complaint`                   | Student     |
| POST       | `/api/student/pay-fine`                    | Student     |
| GET/POST/DELETE | `/api/student/study-buddy`            | Student     |
| GET        | `/api/instructor/me`                       | Instructor  |
| POST       | `/api/instructor/grade`                    | Instructor  |
| POST       | `/api/instructor/admit-waitlist`           | Instructor  |
| POST       | `/api/instructor/complaint`                | Instructor  |
| GET        | `/api/registrar/overview`                  | Registrar   |
| POST       | `/api/registrar/advance-phase`             | Registrar   |
| POST       | `/api/registrar/close-special-reg`         | Registrar   |
| GET        | `/api/registrar/courses`                   | Registrar   |
| GET        | `/api/registrar/instructors`               | Registrar   |
| POST       | `/api/registrar/create-course`             | Registrar   |
| GET        | `/api/registrar/students`                  | Registrar   |
| POST       | `/api/registrar/warn`                      | Registrar   |
| GET        | `/api/registrar/applications`              | Registrar   |
| POST       | `/api/registrar/approve-app`               | Registrar   |
| POST       | `/api/registrar/reject-app`                | Registrar   |
| GET        | `/api/registrar/complaints`                | Registrar   |
| POST       | `/api/registrar/resolve-complaint`         | Registrar   |
| GET        | `/api/registrar/reviews`                   | Registrar   |
| GET        | `/api/registrar/taboo`                     | Registrar   |
| POST       | `/api/registrar/taboo`                     | Registrar   |
| DELETE     | `/api/registrar/taboo/<word>`              | Registrar   |
| GET        | `/api/registrar/instructor-reviews`        | Registrar   |
| POST       | `/api/registrar/instructor-action`         | Registrar   |
| POST       | `/api/registrar/clear-interview/<uid>`     | Registrar   |
| POST       | `/api/registrar/program-quota`             | Registrar   |
