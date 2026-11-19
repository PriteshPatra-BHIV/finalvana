# VANA | AI Backend & Deployment Owner EOD Handover Report

**Document Reference:** `BHIV-VANA-BACKEND-DEPLOY-EOD-2026-11`  
**Owner:** Pritesh Patra (AI Backend and Deployment Owner, BHQ)  
**Date:** 19 November 2026  
**Repository:** [https://github.com/PriteshPatra-BHIV/finalvana.git](https://github.com/PriteshPatra-BHIV/finalvana.git)  
**Branch:** `main`  
**Base Commit Hash:** `8f1cab7`  
**Release Tag:** `v1.0.0-rc1`  
**Deployment Target:** `https://vana.blackholeinfiverse.com`  
**Individual Workstream Status:** **`DONE`** *(Consolidation, 5-group pipeline integration, database/governance stabilization, auth hardening, and deployment runbooks complete)*

---

## 1. Executive Summary & Responsibility Scope

As designated in **Section 1 (Scope, Owners and Accountability)** of the VANA Group Execution Assignment:
* **Primary Responsibility:** AI Backend and deployment owner: consolidate approved VANA repository, integrate five-group pipeline, stabilise database/governance contracts, harden authentication/security and deploy agreed release to VM/domain.
* **Assigned Deliverables / Proof:**
  1. Versioned build and deployment on VM/domain (`https://vana.blackholeinfiverse.com`).
  2. Health and readiness verification across all microservice tiers.
  3. Verified G1 → G5 pipeline integration contracts.
  4. Secure configuration (hardened RBAC, closed public registration, parameterized secrets, and CORS boundaries).
  5. Migration and rollback runbook with zero-data-loss database preservation.
  6. Empirical runtime logs and passing test evidence.

All required backend and deployment artifacts are finalized, committed to `finalvana`, and ready for collective team demonstration.

---

## 2. System Architecture & Topology

The deployed production architecture unifies all five functional groups into an isolated, fail-closed containerized network fronted by an Nginx reverse proxy gateway. Internal backend services and the PostGIS database remain inaccessible to the public internet.

```
Public / Browser Client (HTTPS :443)
       │
       ▼  [DNS: vana.blackholeinfiverse.com]
┌─────────────────────────────────────────────────────────────────────────────┐
│ PRODUCTION HOST / VM                                                        │
│                                                                             │
│  Nginx Host TLS Termination (:443 / :80)                                    │
│       │                                                                     │
│       ▼ Reverse Proxy to 127.0.0.1:8089                                     │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │ Container: vana_frontend (Nginx Proxy & Control Center UI, :8089)     │  │
│  │   ├── /                         -> Static Web Assets                  │  │
│  │   ├── /login, /admin            -> Clean URL Rewrites                 │  │
│  │   ├── /proxy/auth/register      -> 403 Forbidden (Blocked)            │  │
│  │   ├── /proxy/auth/*             -> vana_auth (:8000 / host :8034)     │  │
│  │   ├── /proxy/g1/*               -> vana_masterdb (:8000 / host :8033) │  │
│  │   ├── /proxy/g2/*               -> Pravah Science API (niyantran)     │  │
│  │   └── /proxy/g4/*               -> vana_auth / SANSKAR Runtime        │  │
│  └───────┬─────────────────────────────┬─────────────────────────────────┘  │
│          │ (vana_network)              │                                    │
│          ▼                             ▼                                    │
│  ┌─────────────────────────┐   ┌─────────────────────────────────────────┐  │
│  │ Container: vana_masterdb│   │ Container: vana_auth (Unified Runtime)  │  │
│  │ Group 1 FastAPI (:8033) │   │ FastAPI + SANSKAR Gate (:8034)          │  │
│  └───────┬─────────────────┘   └───────┬─────────────────────────────────┘  │
│          │                             │                                    │
│          └──────────────┬──────────────┘                                    │
│                         ▼ (Internal :5432)                                  │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │ Container: vana_db (PostgreSQL 16 + PostGIS 3.4)                      │  │
│  │ Volume: vana-masterdb-foundation_vana_pg_data (Preserved Data)        │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
       │                                 │
       ▼ (/proxy/g2/*)                   ▼ (/proxy/g4/* upstream sync)
┌─────────────────────────────┐   ┌─────────────────────────────────────────┐
│ Group 2 Pravah Science API  │   │ Group 4 BHL Workflow Runtime            │
│ (niyantran.blackhole...com) │   │ (163.128.209.18:8010)                   │
└─────────────────────────────┘   └─────────────────────────────────────────┘
```

### Dedicated Non-Conflicting Port Allocation
To guarantee that the unified deployment never collides with legacy developer chunks (`8010`, `8013`, `8080`, `5178`), the production configuration allocates dedicated non-conflicting host ports:

| Service Container | Technology | Internal Port | Host Port (`.env`) | Service Health Endpoint |
| :--- | :--- | :--- | :--- | :--- |
| `vana_frontend` | Nginx 1.27 Alpine | `80` | `:8089` | `GET /nginx-health` (`200 OK`) |
| `vana_masterdb` | FastAPI + Python 3.11 | `8000` | `:8033` | `GET /health` (`200 OK`) |
| `vana_auth` | FastAPI + Uvicorn | `8000` | `:8034` | `GET /health` (`200 OK`) |
| `vana_db` | PostGIS 16-3.4 | `5432` | None (Internal) | `pg_isready -U vana -d vana_masterdb` |
| `vana_lineage` | Nginx Static Mirror | `80` | `:5185` | `GET /nginx-health` (`200 OK`) |

---

## 3. Verified Five-Group Pipeline Integration Contracts

Every microservice boundary has been aligned to strict, verifiable JSON contracts:

```
[Field Sensor] ──> [Group 3 Intake] ──> [Group 1 MasterDB] ──> [Group 2 Context] ──> [Group 4 SANSKAR] ──> [Group 5 UI]
  Telemetry          v2.2 Schema          Canonical CR-*       Fail-Closed Ruling     Governed Execution     Lineage Rail
```

### 3.1 Contract Register

| Group | Subsystem / Service | Endpoint Path | Method | Key Request/Response Contract Attributes | Status |
| :---: | :--- | :--- | :---: | :--- | :---: |
| **G1** | Canonical MasterDB Ingestion | `/observations` | `POST` | **Headers:** `Idempotency-Key` (SHA-256).<br>**Response (201):** `observation_id`, `canonical_record_id: "CR-<uuid>"`, `status: "ACCEPTED"`.<br>**Response (200):** `status: "IDEMPOTENT_REPLAY"`.<br>**Response (409):** `status: "IDEMPOTENCY_CONFLICT"`. | **LIVE PASS** |
| **G1** | Canonical Retrieval | `/observations/{id}` | `GET` | **Response (200):** Full canonical observation, `geo_location`, `measurements`, `field_meta`, `raw_artifacts` (with SHA-256 hash).<br>**Response (404):** Fail-closed not-found error. | **LIVE PASS** |
| **G1** | Statutory Benchmark | `/official/forest-cover/{id}` | `GET` | **Dataset:** `DS-FSI-ISFR-2023-FOREST-COVER`.<br>**Response (200):** Total Forest Cover `50,858.53 km²`, Mangrove `315.09 km²`. Zero hardcoded values. | **LIVE PASS** |
| **G2** | Pravah Context Decision Brain | `/api/group2/context/resolve` | `POST` | **Input:** Observation payload from G1.<br>**Behavior:** Evaluates temporal & spatial validity.<br>**Output (ABSTAIN):** `ruling: "ABSTAIN"`, `action_eligibility: false`, `abstention_required: true`, `context_id: null`. | **LIVE PASS** |
| **G3** | Sensor Schema Validation | `validate_manya.py` | CLI/Lib | **Contract:** Frozen JSON Schema v2.2.<br>**Checks:** Mandatory timestamp, valid device ID, geographic bounds, raw artifact SHA-256 linkage. Rejects uncalibrated/tampered data. | **LIVE PASS** (13/13) |
| **G4** | SANSKAR Governed Execution | `/vana/execute` | `POST` | **Auth:** `Authorization: Bearer <token>` (ADMIN only).<br>**ABSTAIN Ruling:** Generates `status: "governed_abstention"`, `action: "noop"`, immutable audit metadata: `abstention_record_id: "ABS-<id>"`, `event_id`, `execution_id`. | **LIVE PASS** |
| **G5** | Control Center & Lineage Map | `/index.html`, `/admin.html` | `GET` | **UI Integration:** Consumes `/proxy/*` routes exclusively. Displays 4-tier lineage rail, real Leaflet geospatial map, role views (`ADMIN`, `FOREST_OFFICER`, `FIELD_AGENT`), and deterministic replay verification. | **LIVE PASS** |

---

## 4. Security Hardening & RBAC Configuration

### 4.1 Strict Closed-Registration Boundary
Public self-registration is permanently disabled across both the API gateway and the backend code.
* In `frontend/.../nginx.conf.template`:
  ```nginx
  location = /proxy/auth/register {
      default_type application/json;
      return 403 '{"error":"Registration Disabled","message":"Public registration is disabled. VANA operates under a strict predefined role-based access control policy.","status_code":403}';
  }
  ```
* In `backend/unified_auth_runtime.py:132-142`:
  ```python
  @app.post("/auth/register", status_code=403)
  def register():
      raise HTTPException(
          status_code=403,
          detail="Public registration is disabled. VANA operates under a strict predefined role-based access control policy."
      )
  ```

### 4.2 Pre-Seeded RBAC Directory & Password Hashing
All pre-seeded accounts utilize cryptographically secure `bcrypt` hashing (cost factor 12) with unique salts. No plaintext passwords or placeholder tokens are committed to source control:

| Account Role | Username / Email | Default Identifier | Permitted Workflows | Auth Restriction |
| :--- | :--- | :--- | :--- | :--- |
| **`PLATFORM_ADMIN`** | `admin@vana.gov.in` | `admin` | Full control: system overview, health checks, replay verification, workflow execution dispatch (`/vana/execute`). | Full Access |
| **`FOREST_OFFICER`** | `officer@vana.gov.in` | `officer` | Operational review: statutory benchmarks, observation analysis, lineage audit, exception triage. | Read/Review (No Dispatch) |
| **`FIELD_AGENT`** | `field@vana.gov.in` | `field` | Field operations: mobile drone/LIDAR upload, inspection submission, telemetry validation. | Intake Only |

### 4.3 Database-Backed Persistent Sessions
Sessions are persisted in PostgreSQL table `user_sessions`. If any container is restarted or updated, active tokens remain valid until expiration, eliminating session loss across Uvicorn workers.

---

## 5. Deployment Runbook & Operational Verification

### 5.1 Automated VM Deployment Script (`deploy.sh`)
The repository includes a battle-tested deployment orchestrator (`deploy.sh`) designed for execution on the production VM:

```bash
# 1. Clone repository on the production VM
sudo mkdir -p /var/www/vana && sudo chown -R $USER:$USER /var/www/vana
git clone https://github.com/PriteshPatra-BHIV/finalvana.git /var/www/vana
cd /var/www/vana

# 2. Configure production environment
cp .env.example .env
nano .env  # Configure secure POSTGRES_PASSWORD and domain

# 3. Execute zero-downtime deployment
chmod +x deploy.sh
./deploy.sh latest
```

### 5.2 Zero-Data-Loss Database Volume Migration
`deploy.sh` automatically probes the host Docker daemon for existing legacy volumes before startup:
1. Detects `vana-masterdb-foundation_vana_pg_data` or `vana_pg_data`.
2. Attaches the identified volume into `docker-compose.production.yml`.
3. Ensures that all canonical records, FSI statutory datasets, and audit logs are preserved with **zero data loss**.

### 5.3 Rollback Procedure
If a regression or deployment issue occurs, rollback is executed in seconds:

```bash
# Method A: Roll back to previous Git commit
cd /var/www/vana
git checkout HEAD~1
./deploy.sh previous_tag

# Method B: Direct Docker Compose Rollback
docker compose -f docker-compose.production.yml down
# Edit docker-compose.production.yml to reference the previous stable image tag
docker compose -f docker-compose.production.yml up -d
```

---

## 6. Empirical Test Evidence & Runtime Logs

### Test Suite 1: Group 3 Schema Validation (`validate_manya.py`)
```text
[PASS] T01 Valid observation: expected ACCEPTED
[PASS] T02 Missing timestamp: expected REJECTED
[PASS] T03 Missing location: expected REJECTED
[PASS] T04 Unknown device: expected REJECTED by semantic device check
[PASS] T05 Invalid observation ID: expected REJECTED
[PASS] T06 Malformed measurement: expected REJECTED
[PASS] T07 NOT VERIFIED calibration: expected ACCEPTED
[PASS] T08 Missing artifact reference: expected REJECTED
[PASS] T09 Duplicate submission: same key + same payload => IDEMPOTENT_REPLAY; no second record
[PASS] T10 Blank trace_id: expected ACCEPTED; runtime supplies response trace_id
[PASS] Extra: invalid quality state: expected REJECTED
[PASS] Extra: invalid calibration state: expected REJECTED
[PASS] RAW-01 Raw artifact linkage: observation -> device -> raw artifact -> provenance

13/13 validation checks passed (100% PASS)
```

### Test Suite 2: MasterDB Canonical Persistence & Idempotency (`test_roundtrip.py`)
```text
[seed] Seed observation OBS-THANECREEK-AGB-2023-01: created (CR-705ceac0-64e1-49f2-bdb6-a4abd0524e9d)
[1] Seed record retrieval: SUCCESS (Full GeoLocation & Dual Allometry Measurements verified)
[2/3] Idempotency proof — row count across 3 submissions:
    attempt 1: created=True,  canonical_id=CR-1442d167-65e0-4a58-bb15-ccd4cb78be74, row count=1
    attempt 2: created=False, canonical_id=CR-1442d167-65e0-4a58-bb15-ccd4cb78be74, row count=1
    attempt 3: created=False, canonical_id=CR-1442d167-65e0-4a58-bb15-ccd4cb78be74, row count=1
    RESULT: 0 -> 1 -> 1 -> 1. Idempotency confirmed at schema v0.2.
[2b] Text-based measurement (CANOPY_IMAGE) stored and retrieved correctly: PASS
[4] Invalid record rejection test (missing dataset_id): REJECTED as expected
[5] Artifact-only observation (DRONE_OBS003): Provenance verified
[DONE] All v0.6 evidence checks passed.
```

---

## 7. BIQOS & Upstream Integration Alignment

| Upstream Subsystem | Authority Boundary | In-Scope Interaction | Verification Status |
| :--- | :--- | :--- | :--- |
| **BIQOS MASTERDB** (`:30308`) | Dataset Registration & Catalog | VANA datasets `DS-FSI-ISFR-2023-FOREST-COVER`, `DS-VANA-SPATIAL-LAYERS`, and `DS-VANA-THANE-CREEK-BLUE-CARBON` verified as `REGISTERED`. | **LIVE VERIFIED** |
| **Pravah / Niyantran** | Decision Governance Authority | Cryptographic evaluation of temporal/spatial telemetry; fail-closed `ABSTAIN` issuance. | **LIVE PASS** |
| **BCAES Engine** | Carbon Accounting Baseline | Statutory biomass density baseline integration for Thane Creek Mangrove Sanctuary. | In Alignment (Outreach Prepared) |
| **SANSKAR Runtime** | Governed Execution Gate | Fail-closed `noop` enforcement on `ABSTAIN` ruling; immutable `ABS-*` audit event logging. | **LIVE PASS** |

---

## 8. Defect Register & Known Limitations

| Defect / Limitation ID | Severity | Description | Current Workaround / Mitigation | Owner & Target Fix |
| :--- | :---: | :--- | :--- | :--- |
| **DEC-VANA-02** | Medium | `GET /dashboard/summary` telemetry contains placeholder distribution counts for unmonitored zones. | The 5 unmonitored zones are explicitly rendered as `PENDING_UPSTREAM` on the UI map. | Pritesh / Next release |
| **DEC-VANA-04** | Low | MasterDB internal write port (`:8033`) requires firewall lockdown. | Port `:8033` is bound to host loopback (`127.0.0.1`) only; public ingress blocked by Nginx. | Pritesh / Completed |
| **DEF-CORS-01** | Low | Wildcard CORS allowed during local development. | Parameterized in `.env` via `VANA_CORS_ORIGINS`; strictly restricted in production mode. | Pritesh / Completed |

---

## 9. Readiness Verdict

> [!IMPORTANT]
> **BACKEND & DEPLOYMENT VERDICT: `READY FOR DEMONSTRATION`**  
> **PRODUCTION HARDENING VERDICT: `CANDIDATE FOR 48-HOUR PRODUCTION HARDENING`**
>
> **Justification:**
> 1. All 5-tier microservice integration contracts (`G1 → G2 → G3 → G4 → G5`) are functional, fail-closed, and empirically verified.
> 2. The unified deployment architecture (`docker-compose.production.yml`, `deploy.sh`) successfully eliminates port collisions and guarantees zero data loss via volume preservation.
> 3. Core authentication security (bcrypt password hashing, closed public registration `403`, RBAC token validation) is active and enforced.
> 4. All unit, schema, and idempotency tests (13/13 `validate_manya.py`, `test_roundtrip.py`) pass with 100% success.
> 5. Known gaps (`DEC-VANA-02`, upstream BIQOS capability manifests) are transparently documented without simulation or fabrication.

---

## 10. Handover Sign-Off

* **Backend & Deployment Owner:** Pritesh Patra (BHQ)  
* **Signature Date:** 19 November 2026  
* **Handover Repository:** `https://github.com/PriteshPatra-BHIV/finalvana.git` (`main` / `8f1cab7`)  
* **Next Action:** Co-host live EOD demonstration with Kaushal, Pratik, and Rhugved.
