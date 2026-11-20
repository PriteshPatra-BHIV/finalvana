# VANA Phase 1 — End-to-End Role Journeys Specification

**Document Version:** 1.0.0 (Phase 1 Production Release)  
**Classification:** Maharashtra State Forest Department · Environmental Intelligence Command Center  
**Sprint Mandate:** VANA × BIQOS 4-Hour Sprint Task Assignment (18 Nov 2026)  
**Product Owner:** Kaushal Yadav, Product, UX & Forest Department Workflow Owner  
**Last Verified:** 2026-11-20

---

## 1. Executive Summary & Core Design Tenets

VANA operates under three constitutional mandates:
1. **Zero Fabrication:** No sensor observation, statutory benchmark, or audit event may ever be simulated, synthetic without clear labeling, or populated with fabricated green statuses.
2. **Fail-Closed Security:** In the absence of verified sensor calibration, valid GNSS accuracy, or authoritative upstream context, the system must pause action (`ABSTAIN` / `noop`).
3. **Role Segregation & Least Privilege:** Execution controls are strictly restricted to authenticated Platform Administrators. Forest Officers conduct statutory reviews and compliance audits. Field Agents capture and submit ground observations.

---

## 2. The Three Primary Role Journeys

### Journey 1: Platform Administrator (ADMIN)

```
Login (vana@gmail.com) 
   │
   ▼
Operational Dashboard (index.html #overview)
   │
   ├─► System KPIs & Service Availability (MasterDB, Pravah, SANSKAR, Lineage)
   ├─► Observations Ledger & Statutory Benchmarks (FSI ISFR 2023)
   ├─► Governance Evaluation Review (SANSKAR Gate)
   └─► Administration Control Plane (admin.html)
          │
          ├─► System Configuration & Map Bounds
          ├─► Alert Thresholds & Notification Rules
          └─► Governed Execution Dispatch (POST /vana/execute)
```

#### Step-by-Step Experience
1. **Landing:** Administrator signs in via `login.html` with designated email `vana@gmail.com` and credentials.
2. **Dashboard Ingress:** Admin lands directly on the **Operational Dashboard** (`index.html #overview`).
3. **Sidebar Presentation:** The navigation sidebar prominently presents the **Administration** navigation link (`admin.html`), gated by backend RBAC (`ROLE_ADMIN`).
4. **Platform Monitoring:** Admin inspects live operational indicators:
   - Total Ingested Sensor Events.
   - MasterDB Canonical Records.
   - Fail-Closed Governance Stance (`ABSTAIN` / `noop` active).
   - Upstream Service Probes (MasterDB :8013, Pravah :8012, SANSKAR :8000).
5. **Execution Action:** When an observation satisfies statutory calibration thresholds, only the Admin can access `admin.html` and invoke `POST /vana/execute`. If the observation is uncalibrated, backend SANSKAR overrides any caller intent and returns `governed_abstention` with `action_taken: "noop"`.

---

### Journey 2: Statutory Forest Officer (FOREST_OFFICER)

```
Login (forest@gmail.com)
   │
   ▼
Statutory Workspace & Review Queue (index.html?role=FOREST_OFFICER #decisions)
   │
   ├─► Review Queue Table (Observation ID, Zone, Parameter, Timestamp, Calibration, Ruling)
   ├─► Spatial Intelligence & Geographic Extents (index.html #spatial)
   ├─► Pravah Ecological Context Resolution (Group 2 Service)
   ├─► SANSKAR Governance Clause Auditing (Contract §26 & §49.1)
   └─► Official Statutory Benchmarks (FSI ISFR 2023 Reconciled Ledger)
```

#### Step-by-Step Experience
1. **Landing:** Forest Officer signs in via `login.html` with `forest@gmail.com`.
2. **Ingress & Guidance:** Redirected to `index.html?role=FOREST_OFFICER`. The interface displays the blue **Forest Officer Statutory Workspace Banner** and directs the officer to the **Statutory Review Queue** (`#foReviewQueuePanel`).
3. **Review Queue Inspection:** The officer inspects unverified or newly ingested observations:
   - Observation ID (e.g. `TC-Z03-F02-LIDAR-OBS001`).
   - Surveillance Zone (e.g. Thane Creek Mangrove Reserve).
   - Parameter & Measured Value (e.g. Canopy Height 8.4m).
   - Calibration Status (`NOT_VERIFIED` or `CALIBRATED_LAB`).
   - SANSKAR Ruling (`ABSTAIN`).
4. **Audit & Lineage Inspection:** Clicking **"Inspect & Audit"** highlights that observation, presents its Group 2 scientific context, displays statutory policy clauses, and confirms the fail-closed rationale.
5. **Security Isolation:** Forest Officers **never** see execution trigger controls. Any direct API attempt by a Forest Officer to call `POST /vana/execute` is rejected by the backend with `HTTP 403 Forbidden` (`Execution dispatch requires ADMIN privileges`).

---

### Journey 3: Field Agent (FIELD_AGENT)

```
Login (feild@gmail.com)
   │
   ▼
Field Operations Workspace (index.html?role=FIELD_AGENT #monitoring)
   │
   ├─► Field Observation Intake Banner (+ Start Field Observation)
   ├─► Dual-Mode Observation Modal
   │      ├─► Structured Field Capture Form (Default)
   │      │      ├─► Surveillance Zone Dropdown (Maharashtra Centroids)
   │      │      ├─► Parameter & Unit Selection
   │      │      ├─► Device GNSS Coordinate Acquisition (navigator.geolocation)
   │      │      ├─► UTC Timestamp Autofill ("Set Now")
   │      │      └─► Photo / Evidence Attachment Preview
   │      └─► Advanced JSON Contract Editor (Group 3 v2.2)
   ├─► Offline Queue Engine (localStorage)
   │      ├─► Offline state detection (navigator.onLine)
   │      ├─► Automatic local caching when offline
   │      └─► One-click batch synchronization when reconnected
   └─► Submission Result & Trace Feedback
```

#### Step-by-Step Experience
1. **Landing:** Field Agent signs in via `login.html` with `feild@gmail.com`.
2. **Ingress & Guidance:** Redirected to `index.html?role=FIELD_AGENT`. The interface presents the green **Field Agent Operational Workspace Banner** with a prominent **+ Start Field Observation** call-to-action.
3. **Observation Capture:** Clicking the start button launches the **Dual-Mode Observation Modal**:
   - The **Field Capture Form** allows the agent to select the surveillance zone (e.g. Thane Creek, Tadoba, Koyna), enter the reading, and click **"Use Device GPS"** to record high-accuracy GNSS coordinates.
   - The agent attaches a ground photograph or artifact, with an instant visual thumbnail preview.
   - The agent clicks **"Set Now"** to record the authoritative observation timestamp.
4. **Offline Resilience:** If network connectivity is lost (`navigator.onLine === false` or network failure):
   - The modal automatically caches the observation into browser `localStorage` (`vana_offline_queue`).
   - The UI displays an amber status pill: `● N Queued Offline`.
   - The agent receives clear reassurance: "Saved to Local Offline Queue. Submissions will synchronize automatically when connection returns."
5. **Submission & Ingestion:** When online, clicking **"Submit to MasterDB"** sends `POST /observations` with the agent's Bearer token and SHA-256 idempotency key:
   - Valid payload: Returns `HTTP 201 Created` with `observation_id`, `canonical_record_id`, and `trace_id`.
   - Duplicate submission: Returns `HTTP 200 IDEMPOTENT_REPLAY` without creating duplicate records.
   - Invalid schema: Returns `HTTP 400 REJECTED` with explicit plain-language error guidance.

---

## 3. Role Journey Verification Summary

| Role | Target Landing Screen | Primary Actions | Execution Access | Offline Capability |
|---|---|---|---|---|
| **Platform Admin** | `index.html #overview` | System monitoring, policy audits, administrative controls (`admin.html`), governed dispatch | **AUTHORIZED** (`POST /vana/execute`) | Full dashboard access |
| **Forest Officer** | `index.html?role=FOREST_OFFICER` (Reviews & Decisions) | Review observation queue, inspect Pravah context, audit FSI statutory benchmarks | **FORBIDDEN** (`HTTP 403`) | Online review mode |
| **Field Agent** | `index.html?role=FIELD_AGENT` (Monitoring & Intake) | Capture observations, GNSS coordinates, photo preview, sync edge telemetry | **FORBIDDEN** (`HTTP 403`) | **ACTIVE** (`localStorage` offline queue) |
