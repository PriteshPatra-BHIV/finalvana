# Phase 1 & 2 Product Acceptance Checklist
**VANA Environmental Intelligence Command Center**  
**Role:** Product, UX & Forest Department Workflow Owner (Kaushal Yadav)  
**Verification Date:** 2026-11-20  
**Current Reference Commit:** `d456135` (HEAD of `main`)  
**Release Classification:** **Conditional demonstration**

---

## 1. Role Journeys & Permissions

- [x] **Platform Admin Journey:**
  - [x] Lands directly on Operational Dashboard.
  - [x] Administration is accessible in the sidebar.
  - [x] Can view system health, users, audit logs, and trigger administrative workflows.
  - [x] Authenticated via Bearer token (`ROLE_ADMIN`).
- [x] **Forest Officer Journey:**
  - [x] Dedicated Review Queue banner displayed upon login (`ROLE_FOREST_OFFICER`).
  - [x] Can inspect pending observations, context resolution, and statutory rulings across all 3 zones.
  - [x] Execution attempts fail closed if uncalibrated.
  - [x] Cannot access administrative control plane (Enforced HTTP 403 on backend).
- [x] **Field Agent Journey:**
  - [x] Dedicated Field Intake banner displayed upon login (`ROLE_FIELD_AGENT`).
  - [x] Dual-mode Observation Intake Modal (Guided Form + Raw JSON conforming to v2.2).
  - [x] Client-side offline cache (`localStorage`) with pending count indicator and sync button.
  - [x] Cannot trigger governance execution (Enforced HTTP 403 on backend).

---

## 2. Multi-Zone Surveillance & Data Integrity

> [!NOTE]
> **Data Grounding Note:** Verified observations (`TC-Z03`, `MV-Z01`, `SMR-Z01`) represent historical / test mission packages dated `2026-08-28T14:45:00Z` used for deterministic pipeline validation. They are not represented as live real-time sensor streams.

- [x] **Thane Creek Mangrove Reserve (`TC-Z03`):** Verified intake, LiDAR canopy metrics, and MasterDB persistence.
- [x] **Maval Western Ghats Catchment (`MV-Z01`):** Verified intake, canopy profiler metrics, and MasterDB persistence.
- [x] **Samachar Coastal Estuary (`SMR-Z01`):** Verified intake, spectral imager metrics, and MasterDB persistence.
- [x] **Idempotency Protection:** SHA-256 idempotency key prevents duplicate row creation in MasterDB.
- [x] **MasterDB Persistence:** Rows written to `observation` table survive server restarts.
- [x] **Zero Fabrication:** Zero invented telemetry; all IDs are cryptographically generated and database-verified.

---

## 3. Governance & SANSKAR Security

- [x] **Fail-Closed Gate:** Uncalibrated sensors or missing context yield `ABSTAIN` / `noop`.
- [x] **Genuine Audit Log:** ABSTAIN creates persistent abstention record (`ABS-...`).
- [x] **Hardened Fail-Closed Check:** Unregistered or missing observations strictly fail closed (`obs_verified = False`, `calibrated = False`).
- [x] **VANA Guidance Assistant:** Client-side assistant accurately explains why dispatches are held without hallucinating approvals.

---

## 4. Eight Negative Test Cases Conformance

- [x] **Case 1: Duplicate observation submission:** Handled via idempotent replay (HTTP 200/201, zero duplicate rows).
- [x] **Case 2: Invalid observation payload:** Malformed payload rejected with HTTP 400 REJECTED.
- [x] **Case 3: Missing provenance block:** Semantic validator rejects missing provenance.
- [x] **Case 4: Unauthorized execution:** Non-admin roles strictly rejected with HTTP 403 Forbidden.
- [x] **Case 5: Missing context (`context_id: None`):** SANSKAR overrides to ABSTAIN (noop).
- [x] **Case 6: Stale or unverifiable context:** SANSKAR overrides to ABSTAIN (noop).
- [x] **Case 7: ABSTAIN creates explicit no-op:** Persistent receipt saved in `governance_execution_audit`.
- [x] **Case 8: Zero unauthorized physical dispatch:** Execution ID is None, dispatch queue empty.

---

## 5. UI/UX Quality & Frontend Diagnostics

- [x] **HTML Syntax Validity:** 0 syntax errors, 0 duplicate IDs, 0 unclosed tags across 2,017 lines of `index.html`.
- [x] **JavaScript Conformance:** Node syntax check clean across `app.js`, `admin-auth.js`, and `config.js`.
- [x] **Responsive Mobile Layout:** Flex/grid layout, off-canvas navigation drawer with backdrop, touch-friendly tap targets.
- [x] **Official Maharashtra Branding:** Official emblem and department typography rendered with proper entity escaping.
- [x] **Sanitized Credentials:** Zero secrets, bearer tokens, or sensitive passwords exposed in documents or logs.
