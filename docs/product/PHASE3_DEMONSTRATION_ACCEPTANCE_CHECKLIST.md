# Phase 3 Stakeholder Demonstration Acceptance Checklist
**VANA Environmental Intelligence Command Center**  
**Role:** Product, UX & Forest Department Workflow Owner (Kaushal Yadav)  
**Verification Date:** 2026-11-20  
**Current Reference Commit:** `28ace20`  
**Official Release Classification:** **Conditional demonstration**

---

## 1. Role Journeys Acceptance Criteria & Evidence

### A. Field Operations Agent Journey
| Acceptance Criteria | Expected Behavior | Actual Verified Result | Status |
| :--- | :--- | :--- | :--- |
| **Authentication & Profile** | Login with Field Agent credentials maps to `ROLE_FIELD_AGENT` | Authenticated session with Bearer JWT returned | **PASS** |
| **Workspace Banner** | Header displays Field Operations Mode banner | `#fieldOpsWorkspaceBanner` displayed | **PASS** |
| **Navigation Restrictions** | Admin Control Plane is hidden from navigation | `#navItemAdminPlane` hidden in sidebar | **PASS** |
| **Dual-Mode Intake** | Intake modal supports both Guided Form and Raw JSON v2.2 | Modal switches between Form and JSON view with live validation | **PASS** |
| **Multi-Zone Intake** | Accepts observations for Thane Creek, Maval, and Samachar | Tested across all 3 zones with valid v2.2 schema | **PASS** |
| **Offline Buffering** | Unsent observations buffer to `localStorage` when offline | `vana_offline_observations` holds pending items; counter updates | **PASS** |
| **Offline Sync Flush** | Clicking Sync Ingests buffered observations to MasterDB | Items ingested with HTTP 201 Created and canonical IDs | **PASS** |
| **Execution Blocked** | Field Agent cannot trigger `POST /vana/execute` | Backend rejects with HTTP 403 Forbidden | **PASS** |

---

### B. Forest Review Officer Journey
| Acceptance Criteria | Expected Behavior | Actual Verified Result | Status |
| :--- | :--- | :--- | :--- |
| **Authentication & Profile** | Login with Forest Officer credentials maps to `ROLE_FOREST_OFFICER` | Authenticated session with Bearer JWT returned | **PASS** |
| **Workspace Banner** | Header displays Forest Officer Review Mode banner | `#foReviewQueuePanel` displayed | **PASS** |
| **Navigation Restrictions** | Admin Control Plane is hidden from navigation | `#navItemAdminPlane` hidden in sidebar | **PASS** |
| **Observation Review** | Can inspect observation parameters, telemetry, and coordinates | Details modal displays canonical metadata and sensor readings | **PASS** |
| **Governance Ruling View** | SANSKAR assessment displays ruling and statutory rationale | ABSTAIN / noop badge and rationale displayed | **PASS** |
| **VANA Guidance Assistant** | Floating assistant explains deterministic rules & recovery steps | `#assistantDrawer` opens with contextual guidance | **PASS** |
| **Execution Blocked** | Forest Officer cannot trigger `POST /vana/execute` | Backend rejects with HTTP 403 Forbidden | **PASS** |

---

### C. Platform Administrator Journey
| Acceptance Criteria | Expected Behavior | Actual Verified Result | Status |
| :--- | :--- | :--- | :--- |
| **Authentication & Profile** | Login with Admin credentials maps to `ROLE_ADMIN` | Authenticated session with Bearer JWT returned | **PASS** |
| **Operational Dashboard** | Direct landing on operational dashboard with full KPIs | KPIs, Leaflet GIS map, and status pill rendered | **PASS** |
| **Admin Control Plane** | Administration accessible in sidebar navigation | Full access to `#adminPlaneView` | **PASS** |
| **Table Health Inspection** | Can view table health across all 17 MasterDB SQLite tables | Tables listed with active status and durability confirmation | **PASS** |
| **Statutory Benchmarks** | Can query FSI ISFR 2023 forest cover baselines | Reconciles state-level baseline from MasterDB ledger | **PASS** |
| **Execution Authority** | Admin is authorized to invoke `POST /vana/execute` | Authorized execution endpoint accepts Admin token | **PASS** |
| **Governance Gate** | Uncalibrated observations still evaluate to ABSTAIN (noop) | SANSKAR strictly overrides caller ruling to ABSTAIN | **PASS** |

---

## 2. Governance, Security & Lineage Acceptance

| Acceptance Item | Specification | Verification Result | Status |
| :--- | :--- | :--- | :--- |
| **Fail-Closed Security** | SANSKAR overrides to ABSTAIN on missing/uncalibrated data | Verified in `unified_auth_runtime.py` and test suites | **PASS** |
| **Idempotency Protection** | SHA-256 idempotency key deduplication (Rule 18) | Duplicate submission returns HTTP 200 `IDEMPOTENT_REPLAY` | **PASS** |
| **MasterDB Durability** | Records survive server restarts in SQLite database | Persisted rows verified in `observation` and `idempotency_record` | **PASS** |
| **No-Op Persistence** | ABSTAIN generates immutable receipt in audit table | Verified row in `governance_execution_audit` table | **PASS** |
| **Zero Side-Effects** | ABSTAIN guarantees zero physical actuator dispatch | `execution_id: None`, `governance_allowed: False` | **PASS** |
| **Zero UI Diagnostics** | VS Code HTML/JS diagnostics panel reports 0 issues | Clean scan: 0 errors, 0 duplicate IDs, 0 unclosed tags | **PASS** |
| **Automated Regressions** | 100% pass across all unit and integration test suites | 22/22 pytest pass (5.23s), 32/32 node tests pass (21.22ms) | **PASS** |
