# ─── Stage 1: build the React frontend ─────────────────────────────────
FROM node:20-alpine AS frontend
WORKDIR /app/Frontend
COPY Frontend/package.json Frontend/package-lock.json* ./
RUN npm ci --no-audit --no-fund
COPY Frontend/ ./
RUN npm run build

# ─── Stage 2: Python backend serving everything ────────────────────────
FROM python:3.12-slim
WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=5000 \
    COLLEGE0_DB_PATH=/data/college0.db

# System tooling kept minimal — only what we need to install pip wheels safely.
RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps first for layer caching
COPY Backend/requirements.txt /app/Backend/requirements.txt
RUN pip install --no-cache-dir -r /app/Backend/requirements.txt

# Backend code
COPY Backend/ /app/Backend/

# Frontend build artifacts (the backend reads ../Frontend/build relative to Backend/app.py)
COPY --from=frontend /app/Frontend/build /app/Frontend/build

# Persist the SQLite file across restarts
RUN mkdir -p /data
VOLUME ["/data"]

WORKDIR /app/Backend
EXPOSE 5000

# 2 workers, 4 threads — fine for a small SQLite-backed app. Tune in prod.
CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:${PORT} --workers 2 --threads 4 --access-logfile - --error-logfile - app:app"]
