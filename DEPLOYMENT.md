# VANA Environmental Governance System — Production Deployment Runbook

This document details the complete deployment infrastructure, environment variable specifications, and operational startup procedures for the **VANA Environmental Governance System**.

---

## 1. System Topology & Architecture

The VANA platform operates as an institutional-grade, multi-tier environmental surveillance and decision governance platform. All user traffic enters via the Frontend Control Center & Reverse Proxy Gateway, keeping database and service internals private.

To prevent collision with existing legacy deployments (which occupied ports 8013, 8010, 8080, and 5178), this stack maps to dedicated host ports:
- **Port `8089`** (Frontend UI & Proxy Gateway)
- **Port `8033`** (Group 1 MasterDB)
- **Port `8034`** (Unified Auth & Group 4 Runtime)
- **Port `5185`** (Preserved Lineage Dashboard)

```text
Public / Client (HTTPS :443 or HTTP :8089)
   │
   ▼  [VM Host TLS Termination / Nginx Proxy / Cloud Load Balancer]
   │
   ▼  vana-frontend (:8089 -> Nginx :80)
       ├── /                     -> Static UI (index.html, login.html, admin.html)
       ├── /proxy/auth/*         -> vana-auth (:8000 / host loopback :8034)
       ├── /proxy/g1/*           -> vana-masterdb (:8000 / host loopback :8033)
       ├── /proxy/g2/*           -> External Pravah Science API (VANA_G2_URL)
       └── /proxy/g4/*           -> vana-auth (:8000 / host loopback :8034)
                                       │
                                       ▼
                                    vana-db (PostgreSQL 16 + PostGIS 3.4, :5432)
```

| Tier / Component | Code Path / Dockerfile | Internal Port | Host Port (`.env`) | Service Health Endpoint |
| :--- | :--- | :--- | :--- | :--- |
| **Frontend UI & Reverse Proxy** | `frontend/group5-lineage-dashboard/vana-control-center/Dockerfile` | `80` (Nginx) / `8089` (Python) | `VANA_FRONTEND_PORT` (`:8089`) | `GET /nginx-health` / `GET /health` |
| **Group 1 MasterDB Foundation** | `backend/group1-masterdb/Dockerfile` | `8000` | `VANA_G1_PORT` (`:8033`) | `GET /health` |
| **Unified Auth & Group 4 Runtime** | `backend/Dockerfile.auth` | `8000` | `VANA_AUTH_PORT` (`:8034`) | `GET /health` |
| **Spatial Database (PostGIS)** | `postgis/postgis:16-3.4` | `5432` | Internal | `pg_isready -U vana -d vana_masterdb` |
| **Lineage Dashboard (Legacy chunk)**| Same container as `vana-frontend` | `80` | `VANA_LINEAGE_PORT` (`:5185`) | `GET /nginx-health` |

---

## 2. Proper System Startup (Developer Specification)

The development team specifies the following authoritative entry points for individual service startups (mapped to the non-conflicting port allocation):

```text
1. Group 1 MasterDB (:8033)
   backend/group1-masterdb/api/main.py

2. Unified Auth + Group 4 (:8034)
   backend/unified_auth_runtime.py

3. Frontend UI + Proxy (:8089)
   frontend/.../server.py
```

### Option A: Unified Python Orchestrator (`run_vana.py` or `start_local.py`)
Run all three services concurrently in development using the single-command orchestrator:
```bash
python run_vana.py
# Or:
python start_local.py
```
This automatically:
- Reads and parses the root `.env` file
- Initializes MasterDB schemas via `init_db.py`
- Binds Group 1 MasterDB to `http://127.0.0.1:8033`
- Binds Unified Auth + Group 4 to `http://127.0.0.1:8034`
- Binds Frontend Control Center Gateway to `http://localhost:8089`

### Option B: Individual Service Startup (Manual / Debugging)
In separate terminal sessions:

```bash
# Terminal 1: Group 1 MasterDB (:8033)
cd backend/group1-masterdb
python init_db.py
uvicorn api.main:app --host 127.0.0.1 --port 8033

# Terminal 2: Unified Auth & Group 4 (:8034)
# From repository root:
uvicorn backend.unified_auth_runtime:app --host 127.0.0.1 --port 8034

# Terminal 3: Frontend UI + Reverse Proxy (:8089)
cd frontend/group5-lineage-dashboard/vana-control-center
python server.py
```

---

## 3. Environment Configuration (`.env`)

All services consume configuration from the single root `.env` file (`finalvana/.env` or `final_vana/.env`).

```ini
# Runtime Mode: 'production' enforces strict passwords and CORS
VANA_ENV=production

# --- PostgreSQL / PostGIS Spatial Database ---
POSTGRES_USER=vana
POSTGRES_PASSWORD=Pass321
POSTGRES_DB=vana_masterdb
VANA_DATABASE_URL=postgresql://vana:Pass321@vana-db:5432/vana_masterdb

# --- Exposed Host Ports (VM) ---
VANA_FRONTEND_PORT=8089
VANA_G1_PORT=8033
VANA_AUTH_PORT=8034
VANA_LINEAGE_PORT=5185

# --- Internal Upstream Targets (Docker Compose Network) ---
VANA_G1_URL=http://vana-masterdb:8000
VANA_BACKEND_URL=http://vana-auth:8000
VANA_G4_URL=http://vana-auth:8000
VANA_G2_URL=https://niyantran.blackholeinfiverse.com

# Optional Node.js Group 2/4 targets
SANSKAR_SERVICE_URL=http://vana-auth:8000
GROUP1_SERVICE_URL=http://vana-masterdb:8000
NEXT_PUBLIC_VANA_GROUP2_URL=https://niyantran.blackholeinfiverse.com/api/group2/context/resolve
NEXT_PUBLIC_VANA_GROUP4_URL=http://vana-auth:8000

# --- CORS Origins ---
VANA_CORS_ORIGINS=https://vana.example.com

# --- Predefined RBAC Accounts (Seeded automatically into PostgreSQL) ---
VANA_ADMIN_EMAIL=admin@vana.gov.in
VANA_ADMIN_PASSWORD=VanaAdmin2026

VANA_FIELD_EMAIL=field@vana.gov.in
VANA_FIELD_PASSWORD=VanaField2026

VANA_FOREST_EMAIL=forest@vana.gov.in
VANA_FOREST_PASSWORD=VanaForest2026

VANA_SESSION_TTL_SECONDS=86400
```

---

## 4. Production VM Deployment (Zero Data Loss)

### Zero Data Loss Database Volume Guarantee
When upgrading existing chunk deployments (`vana-masterdb-foundation` and `vana_lineage`) on the VM, the deployment scripts detect and mount the existing database volume:
```bash
if docker volume inspect vana-masterdb-foundation_vana_pg_data >/dev/null 2>&1; then
    TARGET_DB_VOL="vana-masterdb-foundation_vana_pg_data"
elif docker volume inspect vana_pg_data >/dev/null 2>&1; then
    TARGET_DB_VOL="vana_pg_data"
fi
```
This guarantees zero data loss of historical observations, spatial indexes, and audit logs.

### Executing VM Deployment
On the target production VM:
```bash
# 1. Enter repository
cd finalvana

# 2. Ensure .env is present with required secrets
# (Already supplied at final_vana/.env)

# 3. Execute zero-downtime deployment script
chmod +x deploy.sh
./deploy.sh latest
```

---

## 5. Docker Compose Stacks

### 1. Local / Full Build Stack (`docker-compose.yml`)
Builds all images from source Dockerfiles using local source code:
```bash
docker compose up -d --build
```

### 2. Production Container Registry Stack (`docker-compose.production.yml`)
Deploys pre-built images from Docker Hub (`bhiv/vana-masterdb`, `bhiv/vana-auth`, `bhiv/vana-frontend`):
```bash
docker compose -f docker-compose.production.yml up -d
```

---

## 6. Automated CI/CD Pipeline (GitHub Actions)

Defined in `.github/workflows/cicd.yml`:
1. **Validate**: Generates compose configuration from `docker-compose.production.template.yml` and runs `docker compose config`.
2. **Build**:
   - `bhiv/vana-masterdb` via `backend/group1-masterdb/Dockerfile`
   - `bhiv/vana-auth` & `bhiv/vana-auth-runtime` via `backend/Dockerfile.auth`
   - `bhiv/vana-frontend` & `bhiv/vana-gateway` via `frontend/.../Dockerfile`
3. **Deploy**: SSH into VM, safely handles legacy containers, attaches volume, pulls images, launches stack, and runs multi-tier health checks on ports `8033`, `8034`, `8089`, and `5185`.
4. **Rollback**: Dispatches alert notifications if health checks fail.

---

## 7. Verification Suite & Health Checks

Run these commands on the host after deployment:

```bash
# 1. Frontend & Nginx Proxy Health (Port 8089)
curl -fsS http://127.0.0.1:8089/nginx-health

# 2. Group 1 MasterDB Direct Health (Port 8033)
curl -fsS http://127.0.0.1:8033/health

# 3. Unified Auth & Group 4 Runtime Direct Health (Port 8034)
curl -fsS http://127.0.0.1:8034/health

# 4. MasterDB via Frontend Reverse Proxy (Port 8089)
curl -fsS http://127.0.0.1:8089/proxy/g1/health

# 5. Lineage Dashboard Port (Port 5185)
curl -fsS http://127.0.0.1:5185/nginx-health

# 6. Auth RBAC Login Smoke Test (using .env credentials)
curl -fsS -X POST http://127.0.0.1:8089/proxy/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@vana.gov.in","password":"VanaAdmin2026","role":"ADMIN"}'

# 7. Public Registration Security Guard (Must return HTTP 403)
curl -s -o /dev/null -w "%{http_code}\n" -X POST http://127.0.0.1:8089/proxy/auth/register
# Expected output: 403
```
