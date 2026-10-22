# VaaniLink — Deployment Guide

## 1. Production Architecture Overview

In production, VaaniLink runs as a collection of containerized services orchestrated via Docker Compose, Docker Swarm, or Kubernetes:

```
[ Clients / Browsers ]
         │ (HTTPS / WSS)
         ▼
[ Nginx Reverse Proxy (Frontend Container) ]
    ├── Static Assets (SPA dist) ──> / (HTTP 200 / cached assets)
    ├── REST API Requests ──────────> http://backend:8000/api/
    └── WebSocket Connections ──────> http://backend:8000/ws/ (HTTP 101 Upgrade)
                                           │
                        ┌──────────────────┴──────────────────┐
                        ▼                                     ▼
             [ ASGI Backend (Daphne) ]              [ Celery Worker Pool ]
                        │                                     │
           ┌────────────┴────────────┐                        │
           ▼                         ▼                        ▼
  [ PostgreSQL 16 ]            [ Redis 7 ] ◄──────────────────┘
  (Persistent Data)      (Channel Layer, Cache,
                          Celery Broker & Results)
```

1. **Frontend (Nginx Alpine):** Multi-stage build producing compiled Vite assets, serving the SPA and reverse-proxying `/api/` and `/ws/`.
2. **ASGI Application (Daphne):** Python 3.12+ ASGI server running Django Channels 4 and Django REST Framework.
3. **Database (PostgreSQL 16):** Persistent transactional storage with connection pooling.
4. **Cache & Channels (Redis 7):** In-memory broker for Channels pub/sub, translation cache, and Celery task queues.
5. **Asynchronous Workers (Celery):** Offloaded NLP language detection, script analysis, transliteration, and translation fan-out tasks.

---

## 2. Quick Start with Docker Compose

To launch the complete production-configured stack locally or on a virtual machine:

1. **Clone repository and configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env with secure production passwords and secrets
   ```

2. **Start all services with build:**
   ```bash
   docker compose up --build -d
   ```

3. **Verify running containers:**
   ```bash
   docker compose ps
   ```

4. **Verify health status:**
   - Frontend: `curl -I http://localhost/healthz` (200 OK)
   - Backend API: `curl -I http://localhost/api/health/` (200 OK)

5. **Tail application logs:**
   ```bash
   docker compose logs -f backend celery_worker
   ```

---

## 3. Environment Variables Reference

| Variable | Description | Example / Default |
|---|---|---|
| `DJANGO_SETTINGS_MODULE` | Django settings module | `config.settings.production` |
| `DJANGO_SECRET_KEY` | Cryptographic secret for Django | (generate with `openssl rand -hex 32`) |
| `DJANGO_DEBUG` | Debug mode (must be `False` in prod) | `False` |
| `DATABASE_URL` | PostgreSQL connection string | `postgres://user:pass@host:5432/vaanilink` |
| `REDIS_URL` | Redis URL for Channels & Cache | `redis://redis:6379/0` |
| `CELERY_BROKER_URL` | Redis URL for Celery message broker | `redis://redis:6379/1` |
| `CELERY_RESULT_BACKEND` | Redis URL for Celery task results | `redis://redis:6379/2` |
| `ALLOWED_HOSTS` | Comma-separated list of allowed hostnames | `chat.example.com,localhost` |
| `CORS_ALLOWED_ORIGINS` | Permitted cross-origin domains | `https://chat.example.com` |
| `CSRF_TRUSTED_ORIGINS` | Trusted origins for CSRF protection | `https://chat.example.com` |
| `SECURE_SSL_REDIRECT` | Redirect HTTP to HTTPS | `True` (or `False` if behind TLS-terminator) |
| `TRANSLATION_ENGINE` | Active translation engine adapter | `hybrid` / `mock` / `rule_based` / `google_cloud` |
| `TRANSLATION_API_KEY` | External API key (if using Google Cloud) | `AIzaSy...` |

---

## 4. Manual / Bare-Metal Production Setup

### Step 1: Database Setup
```bash
sudo -u postgres psql -c "CREATE USER vaanilink WITH PASSWORD 'secure_password';"
sudo -u postgres psql -c "CREATE DATABASE vaanilink OWNER vaanilink;"
```

### Step 2: Backend ASGI Setup
```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Run database migrations
python manage.py migrate --noinput

# Seed 37+ supported world languages
python manage.py seed_languages

# Collect static assets
python manage.py collectstatic --noinput

# Launch Daphne ASGI service
daphne -b 0.0.0.0 -p 8000 config.asgi:application
```

### Step 3: Celery Background Worker
```bash
cd backend
source .venv/bin/activate
celery -A config worker --loglevel=info --concurrency=4
```

### Step 4: Frontend Production Build
```bash
cd frontend
npm ci
npm run build
# Output directory 'dist/' contains production bundle
```

---

## 5. Reverse Proxy & WebSocket Configuration (Nginx)

When deploying Daphne behind an upstream Nginx or cloud load balancer, WebSocket connection upgrades must be explicitly forwarded:

```nginx
location /ws/ {
    proxy_pass http://127.0.0.1:8000;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_read_timeout 86400s;
    proxy_send_timeout 86400s;
}
```

---

## 6. Scaling & Health Monitoring

- **Horizontal Worker Scaling:** Add more Celery workers by running `docker compose up -d --scale celery_worker=4`.
- **Database Connection Pooling:** For high concurrency (>500 simultaneous users), deploy **PgBouncer** between Daphne/Celery and PostgreSQL.
- **Redis High Availability:** In multi-node deployments, use Redis Sentinel or AWS ElastiCache for replication and failover.
- **Monitoring Endpoints:**
  - `GET /api/health/`: Returns database and cache connectivity status.
  - `GET /healthz`: Nginx ingress live check.
