# VANA Platform — VM Deployment Guide (DevOps Handover)

This repository is packaged so DevOps can deploy the full VANA stack on a Linux VM using **one `.env` file** and **zero code edits**.

---

## 1. Architecture & Services

The frontend is pure static HTML/JS/CSS and routes all API traffic through same-origin `/proxy/*` paths, so the frontend bundle requires **no build step and no client-side `.env`**.

```text
Internet (HTTPS :443)
   │
   ▼  [VM Host TLS Proxy: Nginx + Certbot / Caddy / Cloud LB]
   │
   ▼  vana-frontend (:8080 -> Nginx :80)
       ├── /                     -> Static UI (index.html, login.html, admin.html)
       ├── /proxy/auth/*         -> vana-auth (:8000 / host loopback :8010)
       ├── /proxy/g1/*           -> vana-masterdb (:8000 / host loopback :8013)
       ├── /proxy/g2/*           -> External Pravah Science API (VANA_G2_URL)
       └── /proxy/g4/*           -> vana-auth (:8000 / host loopback :8010)
                                       │
                                       ▼
                                    vana-db (PostgreSQL 16 + PostGIS 3.4, :5432)
```

| Service | Source / Dockerfile | Health Endpoint | Host Port (Default) |
| :--- | :--- | :--- | :--- |
| `vana-frontend` | `frontend/group5-lineage-dashboard/vana-control-center/Dockerfile` | `GET /nginx-health` | `${VANA_FRONTEND_PORT}` (`8080`) |
| `vana-masterdb` | `backend/group1-masterdb/Dockerfile` | `GET /health` | `127.0.0.1:${VANA_G1_PORT}` (`8013`) |
| `vana-auth` | `backend/Dockerfile.auth` | `GET /health` | `127.0.0.1:${VANA_AUTH_PORT}` (`8010`) |
| `vana-db` | `postgis/postgis:16-3.4` | `pg_isready` | Internal network only (`5432`) |

---

## 2. Environment Configuration (`.env`)

Copy `.env.example` to `.env` on the VM and replace all `CHANGE_ME` placeholders:

```bash
cp .env.example .env
chmod 600 .env
```

### Required Production Variables

| Variable | Description | Example |
| :--- | :--- | :--- |
| `VANA_ENV` | Runtime mode (`production` blocks default passwords) | `production` |
| `POSTGRES_USER` | PostgreSQL username | `vana` |
| `POSTGRES_PASSWORD` | Strong DB password (URL-encode `@ # % :`) | `S3cure%40Pass!` |
| `POSTGRES_DB` | PostgreSQL database name | `vana_masterdb` |
| `VANA_DATABASE_URL` | Full PostgreSQL DSN shared by MasterDB & Auth | `postgresql://vana:S3cure%40Pass!@vana-db:5432/vana_masterdb` |
| `VANA_CORS_ORIGINS` | Allowed frontend origin(s), comma-separated | `https://vana.maharashtra.gov.in` |
| `VANA_ADMIN_EMAIL` / `VANA_ADMIN_PASSWORD` | Seeded Admin RBAC account | `admin@vana.gov.in` / strong password |
| `VANA_FIELD_EMAIL` / `VANA_FIELD_PASSWORD` | Seeded Field Agent RBAC account | `field@vana.gov.in` / strong password |
| `VANA_FOREST_EMAIL` / `VANA_FOREST_PASSWORD` | Seeded Forest Officer RBAC account | `forest@vana.gov.in` / strong password |

### Routing & Port Variables (Optional Overrides)

| Variable | Docker Default | Bare-Metal VM Value |
| :--- | :--- | :--- |
| `VANA_FRONTEND_PORT` | `8080` | `8080` (or `80`/`443` via host Nginx) |
| `VANA_G1_PORT` | `8013` | `8013` |
| `VANA_AUTH_PORT` | `8010` | `8010` |
| `VANA_G1_URL` | `http://vana-masterdb:8000` | `http://127.0.0.1:8013` |
| `VANA_BACKEND_URL` | `http://vana-auth:8000` | `http://127.0.0.1:8010` |
| `VANA_G4_URL` | `http://vana-auth:8000` | `http://127.0.0.1:8010` |
| `VANA_G2_URL` | `https://niyantran.blackholeinfiverse.com` | `https://niyantran.blackholeinfiverse.com` |

---

## 3. Option A: Docker Compose Deployment (Recommended)

A reference `docker-compose.yml` is included in the repository root. DevOps can run it directly or adapt it to existing VM orchestration.

```bash
# 1. Configure environment
cp .env.example .env
nano .env

# 2. Build and start all services
docker compose up -d --build

# 3. Check container health
docker compose ps
```

> **Note:** On first boot, `vana-masterdb` automatically runs `init_db.py` (PostGIS migrations), and `vana-auth` automatically creates `users` + `user_sessions` tables and seeds the three RBAC accounts with bcrypt hashes (idempotent across restarts).

---

## 4. Option B: Bare-Metal VM Deployment (Without Docker)

If DevOps deploys directly on the VM using Python `venv` + `systemd` + host Nginx:

1. **PostgreSQL + PostGIS**: Create database & user matching `VANA_DATABASE_URL` (host `127.0.0.1:5432`).
2. **Group 1 MasterDB** (`backend/group1-masterdb`):
   ```bash
   pip install -r backend/group1-masterdb/requirements.txt
   cd backend/group1-masterdb
   python init_db.py
   uvicorn api.main:app --host 127.0.0.1 --port 8013
   ```
3. **Unified Auth & Group 4 Runtime** (repo root):
   ```bash
   pip install -r backend/requirements.auth.txt
   PYTHONPATH=. uvicorn backend.unified_auth_runtime:app --host 127.0.0.1 --port 8010
   ```
4. **Frontend + Reverse Proxy**:
   - Serve static files from `frontend/group5-lineage-dashboard/vana-control-center/` using host Nginx.
   - Use `frontend/group5-lineage-dashboard/vana-control-center/nginx.conf.template` as the base server block, replacing `${VANA_BACKEND_URL}`, `${VANA_G1_URL}`, `${VANA_G2_URL}`, `${VANA_G4_URL}` with `http://127.0.0.1:8010`, `http://127.0.0.1:8013`, `https://niyantran.blackholeinfiverse.com`, `http://127.0.0.1:8010`.

---

## 5. SSL/TLS & Firewall Recommendations

- Expose only **ports `80` and `443`** publicly on the VM firewall; keep `8010`, `8013`, and `5432` bound to `127.0.0.1` / Docker internal network.
- Terminate TLS (e.g., Certbot / Let's Encrypt on host Nginx, or a cloud load balancer) and proxy to `http://127.0.0.1:${VANA_FRONTEND_PORT}`.

---

## 6. Post-Deployment Verification

```bash
# 1. Frontend & Nginx health
curl -fsS http://127.0.0.1:8080/nginx-health

# 2. Group 1 MasterDB via proxy
curl -fsS http://127.0.0.1:8080/proxy/g1/health

# 3. Unified Auth via proxy (registration must return HTTP 403)
curl -s -o /dev/null -w "%{http_code}\n" -X POST http://127.0.0.1:8080/proxy/auth/register

# 4. Login smoke test (use credentials from .env)
curl -fsS -X POST http://127.0.0.1:8080/proxy/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@vana.gov.in","password":"YOUR_ADMIN_PASSWORD","role":"ADMIN"}'
```
