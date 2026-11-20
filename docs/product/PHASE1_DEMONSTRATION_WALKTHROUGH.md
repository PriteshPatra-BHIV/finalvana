# VANA + BIQOS — Stakeholder Demonstration Walkthrough & Script
**Environmental Intelligence Command Center**  
**Role:** Product, UX & Forest Department Workflow Owner (Kaushal Yadav)  
**Audience:** Maharashtra Forest Department, BIQOS Platform Leadership, Hackathon Evaluators  
**Target Duration:** 10–15 Minutes  
**Current Reference Commit:** `d456135` (HEAD of `main`)  
**Official Release Classification:** **Conditional demonstration**

---

## 1. Executive Demonstration Framing & Ground Rules

### Core Doctrine: Zero-Fabrication & Strict Fail-Closed Safety
- **No Mock Approval Simulation:** We do not fabricate green checkboxes or fake approvals. Uncalibrated observations strictly yield **`ABSTAIN`** (`noop`).
- **Telemetry Grounding Note:** The three multi-zone observation records (`TC-Z03`, `MV-Z01`, `SMR-Z01`) are **historical/test mission packages (dated 2026-08-28)** used for deterministic pipeline verification. They are clearly labeled as historical/test data and are **not** represented as live sensor feeds.
- **Credential Hygiene:** All demo credentials and bearer tokens are sanitized (`[TEST_CREDENTIALS]`, `vana_sec_...`). No plaintext production secrets or private tokens are committed or displayed.

---

## 2. 12–15 Minute Timed Demonstration Agenda

```mermaid
flowchart LR
    A["0:00-1:30<br/>Admin Dashboard"] --> B["1:30-4:00<br/>Field Agent Intake"]
    B --> C["4:00-7:00<br/>Forest Officer Review"]
    C --> D["7:00-9:30<br/>MasterDB Lineage"]
    D --> E["9:30-11:30<br/>Pravah & Governance"]
    E --> F["11:30-13:30<br/>BIQOS 5 Pillars"]
    F --> G["13:30-15:00<br/>Dependencies & Q&A"]
```

---

### Segment 1: Admin Operational Dashboard (0:00 – 1:30)
**Presenter Goal:** Demonstrate high-level situational awareness, Maharashtra GIS map, and administrative system telemetry.

1. **Open Application:** Navigate to `http://localhost:3000` or launch [index.html](file:///c:/Users/A/Documents/BHIV/VANA/finalvana/frontend/group5-lineage-dashboard/vana-control-center/index.html).
2. **Authenticate as Administrator:**
   - Click **Sign In** in the top right.
   - Enter Administrator credentials (`[DEMO_ADMIN_ACCOUNT]`).
   - Role badge updates to **`Platform Administrator (ROLE_ADMIN)`** with dark-green status pill.
3. **Walkthrough Key UI Elements:**
   - **Header:** Verified Government of Maharashtra branding, live UTC clock widget, and real-time MasterDB connectivity badge (**System Operational**).
   - **KPI Overview:** Point out Total Observations, Active Monitored Zones (3 Regional Zones: Thane Creek, Maval, Samachar), and Governed Events counter.
   - **Maharashtra GIS Map:** Interactive Leaflet canvas rendering surveillance zones with boundary tiles and recenter control.
   - **Admin Control Plane Access:** Open the sidebar **Administration** section; demonstrate MasterDB table health across all 17 tables and statutory benchmarks (FSI ISFR 2023).

---

### Segment 2: Field Agent Multi-Zone Intake & Offline Synchronization (1:30 – 4:00)
**Presenter Goal:** Show how field rangers capture structured environmental telemetry and demonstrate offline resilience.

1. **Switch Role to Field Agent:**
   - Sign in as Field Agent (`[DEMO_FIELD_AGENT_ACCOUNT]`).
   - Role badge updates to **`Field Operations Agent (ROLE_FIELD_AGENT)`**.
   - Note the **Field Operations Mode Banner**:
     > *"Field Operations Mode: You can capture raw environmental observations and sync offline caches."*
   - Note that the **Administration** navigation link is automatically hidden from non-admin view.
2. **Open Observation Intake Modal:**
   - Click the green **+ Submit Observation** button in the header.
   - Showcase **Dual-Mode Intake**:
     - *Guided Mode:* Form inputs for Survey ID, Zone ID, Sensor ID, Metric Value, and Coordinates.
     - *Raw JSON Mode:* Strict Group 3 Contract v2.2 schema editor with live validation pre-check.
3. **Select Monitored Regional Zone:**
   - *Option A (Mangroves):* Thane Creek Reserve (`TC-Z03`, LiDAR Canopy Density `74.5%`, 19.1288° N, 72.9421° E).
   - *Option B (Watershed):* Maval Western Ghats (`MV-Z01`, Canopy Height `16.2 m`, 18.7180° N, 73.4730° E).
   - *Option C (Estuary):* Samachar Coastal Buffer (`SMR-Z01`, Optical Index `8.4`, 19.2220° N, 72.9560° E).
4. **Demonstrate Offline Synchronization Engine:**
   - Toggle offline mode or click **Save to Offline Queue**.
   - Show offline counter indicator: *"Offline Queue: 1 pending"*.
   - Explain: Telemetry is safely buffered in browser `localStorage` (`vana_offline_observations`) during connectivity dropouts.
   - Click **Sync Queue**: Show items ingested into MasterDB with canonical record ID (`CR-...`).

---

### Segment 3: Forest Officer Review Queue & SANSKAR Fail-Closed Gate (4:00 – 7:00)
**Presenter Goal:** Show statutory compliance verification, transparent rule explanation, and tamper-proof governance safety.

1. **Switch Role to Forest Officer:**
   - Sign in as Forest Officer (`[DEMO_FOREST_OFFICER_ACCOUNT]`).
   - Role badge updates to **`Forest Review Officer (ROLE_FOREST_OFFICER)`**.
   - Note the dedicated **Forest Officer Review Queue Banner**:
     > *"Forest Officer Review Mode: Review pending environmental observations and inspect SANSKAR statutory rulings."*
2. **Inspect Historical Test Observation:**
   - Select observation `TC-Z03-F02-LIDAR-OBS889` *(Historical Benchmark Telemetry: 2026-08-28)*.
   - View telemetry parameters, sensor metadata, and location coordinates.
3. **Demonstrate SANSKAR Fail-Closed Governance:**
   - Point to the Governance Decision panel:
     - **Ruling:** **`ABSTAIN`**
     - **Action Taken:** **`noop`** (No operation; physical dispatch blocked)
     - **Abstention Record ID:** `ABS-9B9F1C4418F1`
     - **SANSKAR Event ID:** `evt_1795166521954_389`
     - **Rationale:** *"Authoritative evidence threshold not met (Context not verified). Failing closed to ABSTAIN."*
4. **Contextual AI Assistant Guidance:**
   - Click the floating **VANA Assistant** pill in the lower-right corner.
   - Review the explanation drawer: Explains deterministic calibration requirements and provides clear recovery guidance for field agents.

---

### Segment 4: MasterDB Canonical Records & Deterministic Lineage (7:00 – 9:30)
**Presenter Goal:** Prove that observations are persistently stored in SQLite MasterDB with cryptographic SHA-256 idempotency protection.

1. **Open MasterDB Lineage & Trace Subtab:**
   - Navigate to **Lineage & History** in the sidebar.
   - Show the Directed Acyclic Graph (DAG) tracing:
     `Field Ingestion` → `Schema v2.2 Validation` → `MasterDB Canonical Record` → `Context Resolution` → `SANSKAR ABSTAIN` → `Lineage Log`.
2. **Showcase SQLite MasterDB Durability:**
   - Show canonical record ID: `CR-7da754a8-a300-445e-9c41-493524ad775f`.
   - Show SHA-256 idempotency key: `IK-TC-Z03-F02-LIDAR-OBS889`.
   - Show trace ID: `VANA-c2d1d3e70d17`.
3. **Demonstrate Idempotent Duplicate Replay:**
   - Explain how re-submitting the exact same observation returns HTTP 200 `IDEMPOTENT_REPLAY` and inserts **0 duplicate rows** into MasterDB table `observation`.

---

### Segment 5: Pravah Context Resolution & Fail-Closed Boundary (9:30 – 11:30)
**Presenter Goal:** Transparently articulate the local vs external Group 2 integration boundary without exaggeration.

1. **Explain the Pravah Scientific Role:**
   - Group 2 PrAVAH associates raw sensor metrics with ecological catchment models and tidal estuarine benchmarks.
2. **Clarify the External Integration Stance:**
   - **Deterministic Local Resolver:** Active and verified in test suites.
   - **Live External Service (:8012):** Not bound in current local host environment.
   - **Fail-Closed Result:** When external port 8012 is unreachable, VANA does **not** crash or fabricate synthetic approvals. It safely and deterministically defaults to **`ABSTAIN` (`noop`)**.

---

### Segment 6: BIQOS Five-Pillar Conformance & AI Agent Inventory (11:30 – 13:30)
**Presenter Goal:** Present authoritative BIQOS alignment evidence and maintain the Zero-Fabrication doctrine on AI agents.

1. **Review BIQOS Five Pillars:**
   - **Identity & Access:** Cryptographically verified Bearer JWTs, production RBAC (Admin, Forest Officer, Field Agent).
   - **Data & Metadata:** Group 3 Contract v2.2 canonical schema stored in MasterDB SQLite tables.
   - **Workflow & Correlation:** Distributed trace propagation via `X-Trace-ID` and `X-Correlation-ID`.
   - **Governance & Execution:** SANSKAR statutory policy enforcement; fail-closed safety.
   - **Observability:** Lineage DAG, dynamic audit events queryable via `GET /api/v1/summary`.
2. **Truth in AI Inventory:**
   - Reiterate clearly: There are **not 30+ autonomous backend agents**.
   - Exactly **1 operational client-side helper** (`VANA Guidance Assistant`).
   - Exactly **1 formally specified product agent** (`vana_forest_governance_agent`).
   - Exactly **0 unmonitored autonomous actuators**.

---

### Segment 7: External Dependencies & Release Classification Q&A (13:30 – 15:00)
**Presenter Goal:** Present the dependency register, explain why the release is classified as Conditional Demonstration, and take questions.

---

## 3. Outstanding External Dependencies Slide

| Dependency | Responsible External Owner | Impact on Production Dispatch | Fallback / Security Stance |
| :--- | :--- | :--- | :--- |
| **Physical Sensor Calibration Certificates** | **Group 3 Edge Hardware Lab** | Raw field sensors lack signed calibration certificates. | **Fail-Closed Doctrine:** Observations lacking calibration certificates strictly evaluate to **ABSTAIN (`noop`)**. Spurious dispatches are impossible. |
| **Live PrAVAH External Service Binding (`:8012`)** | **Group 2 PrAVAH Core Team** | Live remote socket proxying on port 8012 requires deployment environment networking. | **Local Deterministic Fallback:** Local resolver active; network partition safely defaults to **ABSTAIN (`noop`)**. |
| **FSI ISFR 2023 Statutory Polygon Sync** | **Forest Department GIS Team** | Authoritative mangrove canopy density baseline reconciliation. | MasterDB provides fallback statutory benchmarks queryable in Admin plane. |

---

## 4. Final Demonstration Checklist for Evaluators

- [x] **Backend Authentication:** Enforced Bearer tokens; non-admin roles receive HTTP 403 on execute.
- [x] **Observation Intake:** Conforms strictly to Group 3 v2.2 schema (`TC-Z03`, `MV-Z01`, `SMR-Z01`).
- [x] **Offline Synchronization:** `localStorage` buffering with pending badge and manual queue flush.
- [x] **MasterDB Durability:** Real SQLite rows verified in tables `observation`, `idempotency_record`, and `governance_execution_audit`.
- [x] **Fail-Closed Security Invariant:** Uncalibrated sensors or missing context force ABSTAIN (noop).
- [x] **Frontend Diagnostics:** 0 HTML syntax errors, 0 duplicate IDs, 0 unclosed tags across 2,017 lines.
- [x] **Automated Regression:** 22/22 pytest tests PASS, 32/32 node tests PASS.
- [x] **Release Classification:** **Conditional demonstration** (No ungrounded production claims).
