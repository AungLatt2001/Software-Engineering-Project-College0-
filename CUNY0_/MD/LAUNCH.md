# 🚀 College0 / CUNY0 — Launch Instructions

## One-Time Setup (2 minutes)

### 1. Install Python Dependencies

```bash
cd Backend
pip install -r requirements.txt
```

### 2. Install Frontend Dependencies

```bash
cd Frontend
npm install
```

## Launch the App (Every Time)

### Option A: Development Mode (Recommended)

Open **two terminal windows**:

**Terminal 1 — Backend (port 5001):**
```bash
cd CUNY0/Backend
python app.py
```

Wait for: `Running on http://127.0.0.1:5001`

**Terminal 2 — Frontend (port 3000):**
```bash
cd CUNY0/Frontend
npm start
```

Wait for: `Compiled successfully!`

Then open: **http://localhost:3000** in your browser

### Option B: Production Mode (Single Port)

```bash
cd Frontend && npm run build
cd ../Backend && python app.py
```

Then open: **http://localhost:5001**

## Demo Login

| Role | User ID | Password |
|------|---------|----------|
| Student | S101 | pass123 |
| Instructor | I01 | pass123 |
| Registrar | REG01 | admin |

(Also try S102–S110, I02–I03)

## Database

- **Location:** `Backend/college0.db` (auto-created on first run)
- **Reset:** Delete the file and restart the backend

## Troubleshooting

### Port 5001 already in use
```bash
PORT=5002 python app.py
```

### npm ERR! ERESOLVE unable to resolve dependency tree
```bash
cd Frontend
npm install --legacy-peer-deps
npm start
```

### Python dependencies fail
```bash
cd Backend
pip install --break-system-packages -r requirements.txt
```

## Documentation

- **START_HERE.txt** — Quick reference
- **QUICK_START.md** — Detailed Mac guide
- **READY_TO_GO.md** — Full checklist
- **Backend/README.md** — API documentation
- **CHANGES.md** — What's new

## Deploy to Internet

See **QUICK_START.md** for one-click Render deployment (3 minutes to public URL)

---

**That's it! Enjoy.** 🎉
