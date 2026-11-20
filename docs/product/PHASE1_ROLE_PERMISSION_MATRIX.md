# VANA Phase 1 — Role-Based Access Control (RBAC) & Permission Matrix

**Document Version:** 1.0.0 (Phase 1 Production Release)  
**Security Standard:** Fail-Closed Backend Enforcement & Least-Privilege Authorization  
**Sprint Mandate:** VANA × BIQOS 4-Hour Sprint Task Assignment (18 Nov 2026)  
**Product Owner:** Kaushal Yadav, Product, UX & Forest Department Workflow Owner  
**Last Verified:** 2026-11-20

---

## 1. Security Architecture & Boundary Model

VANA enforces a strict multi-tier security boundary:
1. **Frontend Role Presentation:** Gating is used strictly for UX ergonomics (hiding irrelevant administrative controls from field staff).
2. **Backend Authoritative Enforcement:** Security is **never** enforced solely on the client. Every API endpoint verifies Bearer token validity, session expiration, and role claims against the MasterDB session store (`user_sessions`).
3. **Fail-Closed Default:** Unrecognized roles, expired sessions, or forged tokens result in `HTTP 401 Unauthorized` or `HTTP 403 Forbidden`.

---

## 2. Canonical Role Definitions

| Role Identifier | Role Label | Primary Responsibility | Authentication Identity |
|---|---|---|---|
| `ADMIN` | Platform Admin | Full infrastructure administration, policy tuning, and governed execution dispatch. | `vana@gmail.com` |
| `FOREST_OFFICER` | Forest Officer | Statutory forest cover monitoring, observation review, and evidence audits. | `forest@gmail.com` |
| `FIELD_AGENT` | Field Agent | Field sensor data collection, ground observation intake, and offline telemetry sync. | `feild@gmail.com` |

---

## 3. End-to-End API Authorization Matrix

| Endpoint | Method | Permitted Roles | Unauthenticated Behavior | Unauthorized Role Behavior | Idempotency Protection |
|---|---|---|---|---|---|
| `/auth/login` | POST | Public | Returns `access_token` and user profile on valid credentials | Returns `HTTP 401` on invalid password or bad role | N/A |
| `/auth/me` | GET | Authenticated (Any) | Returns `HTTP 401 Unauthorized` | Allowed for all authenticated sessions | N/A |
| `/auth/logout` | POST | Authenticated (Any) | Purges token from session database | Allowed | N/A |
| `/health` | GET | Public | Returns `status: "healthy"` | Allowed | N/A |
| `/dashboard/summary` | GET | Public / All | Returns canonical MasterDB summary | Allowed | N/A |
| `/observations` | GET | Public / All | Returns retrieved observation records | Allowed | N/A |
| `/observations` | POST | `FIELD_AGENT`, `ADMIN` | Returns `HTTP 401 Unauthorized` | Returns `HTTP 403 Forbidden` for `FOREST_OFFICER` | **Mandatory** (`Idempotency-Key` header with SHA-256) |
| `/official/forest-cover` | GET | Public / All | Returns FSI ISFR statutory benchmarks | Allowed | N/A |
| `/official/forest-cover` | POST | `ADMIN` | Returns `HTTP 401 Unauthorized` | Returns `HTTP 403 Forbidden` for `FIELD_AGENT`, `FOREST_OFFICER` | Database primary key constraint |
| `/vana/execute` | POST | `ADMIN` | Returns `HTTP 401 Unauthorized` | Returns `HTTP 403 Forbidden` for `FIELD_AGENT`, `FOREST_OFFICER` | Governance Audit Ledger `audit_id` |

---

## 4. UI Capabilities & View Access Matrix

| UI Section / Feature | Admin (`ADMIN`) | Forest Officer (`FOREST_OFFICER`) | Field Agent (`FIELD_AGENT`) | Anonymous / Unauthenticated |
|---|:---:|:---:|:---:|:---:|
| **Operational Dashboard (`#overview`)** | Full Access | Full Access | Full Access | Read-Only |
| **Role Workspace Banner** | Admin Mode | Forest Officer Mode | Field Agent Mode | Hidden |
| **Spatial Intelligence Map (`#spatial`)** | Interactive | Interactive | Interactive | View Extents |
| **Sensor Intake & Monitoring (`#monitoring`)** | Full View | Full View | Full View | View Records |
| **Observation Submission Modal** | Dual-Mode Form/JSON | View Only | **Active Intake Form** | Login Modal Prompt |
| **Offline Queue & Local Storage Sync** | Available | N/A | **Active Local Sync** | Disabled |
| **Statutory Review Queue (`#decisions`)** | View & Audit | **Primary Queue** | View Only | Read-Only |
| **Pravah Ecological Context Details** | Inspect | **Inspect & Audit** | Inspect | View Summary |
| **SANSKAR Governance Ruling Display** | Inspect | **Statutory Audit** | View Status | View Status |
| **History & Lineage Replay (`#masterdb`)** | Full Lineage | Full Lineage | View Lineage | View Summary |
| **Statutory Benchmarks (FSI ISFR)** | Query & Audit | **Inspect Baseline** | View Summary | View Summary |
| **Administration Plane (`admin.html`)** | **Authorized** | **Hidden & Blocked (403)** | **Hidden & Blocked (403)** | **Hidden & Blocked (401)** |
| **Execution Dispatch Controls** | **Authorized** | **STRICTLY BLOCKED** | **STRICTLY BLOCKED** | **BLOCKED** |

---

## 5. Security Invariant Validations

1. **Tamper Resistance:** Modifying `sessionStorage.getItem("vana_user")` in the browser devtools does **not** grant execution privileges; the backend validates the Bearer token cryptographic session row on each request.
2. **Token Forwarding Isolation:** VANA authentication tokens are restricted to the origin API gateway and are never forwarded to external third-party hosts.
3. **Expired Token Purge:** Sessions automatically expire after 86,400 seconds (24 hours). Expired tokens return `HTTP 401` and prompt immediate session re-authentication.
