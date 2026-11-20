# Phase 1 & 2 Demonstration Walkthrough Script
**VANA Environmental Intelligence Command Center**  
**Role:** Product, UX & Forest Department Workflow Owner (Kaushal Yadav)  
**Audience:** Maharashtra Forest Department, BIQOS Platform Team, Hackathon Judges

---

## 1. Demonstration Setup & Pre-Flight Check

1. **Verify Backend Status:**
   - MasterDB running on port 8000 (`python backend/group1-masterdb/api/main.py`)
   - SQLite DB initialized: `backend/group1-masterdb/vana_api.db`
2. **Open Frontend:**
   - Navigate to `http://localhost:3000` or open `frontend/group5-lineage-dashboard/vana-control-center/index.html`.
   - Confirm Header displays: "VANA Logo", "Government of Maharashtra emblem", "System Operational" green pill.

---

## 2. Step-by-Step Role Walkthrough

### Part 1: Field Agent Multi-Zone Capture (Mobile & Desktop)
1. **Login:**
   - Click **Sign In** in the top-right header.
   - Enter credentials: `feild@gmail.com` / `vana`.
   - Observe Role Badge changes to **Field Agent (ROLE_FIELD_AGENT)** with green badge.
   - Note the **Field Agent Workspace Banner** displaying:
     > *"Field Operations Mode: You can capture raw environmental observations and sync offline caches."*
2. **Submit Field Observation (Multi-Zone Selection):**
   - Click the green **+ Submit Observation** button in the header.
   - Select or configure surveillance zone:
     - **Thane Creek Mangroves (`TC-Z03`):** LiDAR Canopy Density `74.5%` (19.1288° N, 72.9421° E)
     - **Maval Western Ghats (`MV-Z01`):** Canopy Height Profiler `16.2 m` (18.7180° N, 73.4730° E)
     - **Samachar Estuary (`SMR-Z01`):** Spectral Health Index `8.4` (19.2220° N, 72.9560° E)
   - Click **Validate & Ingest into MasterDB**.
   - Show success notification: Observation accepted with canonical record ID (`CR-...`).
3. **Offline Resilience Demo:**
   - Toggle network offline (or click **Save to Offline Queue**).
   - Show badge counter: "Offline Queue: 1 pending".
   - Toggle back online and click **Sync Queue**: Show items ingested into MasterDB.

---

### Part 2: Forest Officer Verification & Statutory Review
1. **Switch Role:**
   - Sign in as `forest@gmail.com` / `vana`.
   - Role Badge updates to **Forest Officer (ROLE_FOREST_OFFICER)**.
   - Note the dedicated **Forest Officer Review Queue** banner.
2. **Review Observation:**
   - Select observation `TC-Z03-F02-LIDAR-OBS474`.
   - View telemetry, ground coordinates, and canopy density.
   - Observe SANSKAR governance assessment panel:
     - Policy: Statutory Mangrove Conservation (FSI Baseline).
     - Rationale: Calibration certificate unverified.
     - Governance Ruling: **ABSTAIN (noop)**.
3. **Inspect Assistant Guidance:**
   - Click the floating **VANA Assistant** pill in the bottom right.
   - Review explanation: Shows clear reason why execution was held (Fail-Closed Security Doctrine).

---

### Part 3: Platform Administrator Control Plane
1. **Switch Role:**
   - Sign in as `vana@gmail.com` / `vana`.
   - Role Badge updates to **Administrator (ROLE_ADMIN)**.
2. **Access Admin Control Plane:**
   - Click **Administration** in the sidebar.
   - Review:
     - MasterDB health & table row counts across all 17 tables.
     - SANSKAR governance execution audit ledger (`governance_execution_audit`).
     - Statutory Benchmarks (FSI ISFR 2023) sub-tab.
     - Replay & Diff engine for forensic verification.

---

## 3. Negative Cases Demonstration for Evaluators

1. **Duplicate Submission:** Demonstrate re-submitting an existing observation. The system returns `status: "IDEMPOTENT_REPLAY"` and inserts 0 duplicate rows into MasterDB.
2. **Unauthorized Dispatch:** Demonstrate Field Agent or Forest Officer attempting to invoke execution. The backend rejects with `HTTP 403 Forbidden`.
3. **Fail-Closed Gate:** Demonstrate execution with missing or uncalibrated context. SANSKAR automatically overrides to `ABSTAIN` with action `noop` and stores an immutable receipt.
