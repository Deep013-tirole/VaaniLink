# VaaniLink — Development Guide

## 1. Prerequisites
- Python 3.12+ (or 3.14+)
- Node.js 20+ & npm 10+
- PostgreSQL 15+ (or SQLite fallback in local development mode when `DATABASE_URL` is omitted)
- Redis 7+ (optional for basic HTTP tests, required for WebSocket and Celery operations)

---

## 2. Local Environment Setup

### 2.1 Backend Setup
```bash
# 1. Create and activate a Python virtual environment
python -m venv .venv
# On Windows (PowerShell):
.venv\Scripts\Activate.ps1
# On Linux / macOS:
source .venv/bin/activate

# 2. Install backend dependencies
pip install -r backend/requirements.txt -r backend/requirements-dev.txt

# 3. Configure environment
cp .env.example .env

# 4. Run migrations
python backend/manage.py migrate

# 5. Seed Languages Registry (37+ Indic & International languages)
python backend/manage.py seed_languages

# 6. Run development server (ASGI Daphne)
python backend/manage.py runserver
```

### 2.2 Frontend Setup
```bash
# 1. Navigate to frontend
cd frontend

# 2. Install dependencies
npm install

# 3. Start Vite dev server
npm run dev
```

---

## 3. Running Checks & Tests

### Backend:
```bash
# Run pytest test suite
pytest

# Run Ruff linter and formatter checks
ruff check backend
ruff format --check backend

# Run Django system checks
python backend/manage.py check
```

### Frontend:
```bash
cd frontend
# Run TypeScript compilation check
npm run typecheck

# Run linter
npm run lint
```
