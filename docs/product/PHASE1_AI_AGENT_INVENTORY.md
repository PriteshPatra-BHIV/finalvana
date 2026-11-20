# Governed AI Agent Ecosystem & Declarative Inventory
**VANA Environmental Intelligence & BIQOS Integration**  
**Role:** Product, UX & Forest Department Workflow Owner (Kaushal Yadav)  
**Sprint Reference:** Section 4 & 4-Hour Sprint Mandate (`VANA_BIQOS_4_Hour_Sprint_Task_Assignment_18_Nov_2026.pdf`)  
**Audit Standard:** Zero-Fabrication & Strict Ground Truth  
**Target Capability:** 30+ Specialized Domain Agents  
**Registry File:** [`backend/agent_registry.json`](file:///c:/Users/A/Documents/BHIV/VANA/finalvana/backend/agent_registry.json)  
**Supervisor Runtime:** [`backend/agent_orchestrator.py`](file:///c:/Users/A/Documents/BHIV/VANA/finalvana/backend/agent_orchestrator.py)

---

## 1. Compliance with the "30+ Agent Rule"

The sprint assignment establishes a strict audit standard:
> *"30+ is the target capability, not a claim. Report separately how many agents are implemented, integrated, tested and merely planned. A placeholder or one agent wearing multiple labels does not count as 30 operational agents."* (Page 1 & Section 4)

### Ground-Truth Breakdown (32 Total Agents Cataloged):

| Status | Count | Definition | Architectural Proof |
| :--- | :---: | :--- | :--- |
| **OPERATIONAL** | **12** | Active runtime code; tested & interactive | `backend/agent_orchestrator.py`, `frontend/app.js`, SANSKAR kernel |
| **INTEGRATING** | **6** | Interfaces built; undergoing boundary wiring | Cryptographic hash attestor, GPS sanity, Replay verifier |
| **PLANNED** | **14** | Formally architected; detailed roadmap specifications | Mangrove NDVI, Western Ghats runoff, Fire fuel index, etc. |
| **TOTAL** | **32** | **Full 30+ Target Capability Cataloged** | Verified in `tests/test_phase2_agent_ecosystem.py` |

---

## 2. Five Functional Tiers Overview

```
                      32 GOVERNED AGENTS ACROSS 5 TIERS
                      
  ┌────────────────────────────────────────────────────────────────────────┐
  │ TIER 1: UX, Onboarding & User Guidance (4 Agents)                      │
  │ • General Guidance  • Role Onboarding  • Form Assistant  • Recovery    │
  ├────────────────────────────────────────────────────────────────────────┤
  │ TIER 2: Edge Intake, Validation & Data Quality (6 Agents)              │
  │ • Schema v2.2       • SHA-256 Idempotency • Hash Attestor • Calib Insp │
  ├────────────────────────────────────────────────────────────────────────┤
  │ TIER 3: Specialized Ecological & Forest Analytics (12 Agents)          │
  │ • Thane Creek Mangrove • Western Ghats Hydrology • Fire Risk • Biomass │
  ├────────────────────────────────────────────────────────────────────────┤
  │ TIER 4: Statutory Governance, Policy & Audit (6 Agents)                │
  │ • SANSKAR Explainer • Fail-Closed Watchdog • Chain-of-Custody • FCA    │
  ├────────────────────────────────────────────────────────────────────────┤
  │ TIER 5: Observability, Lineage & Replay (4 Agents)                     │
  │ • Lineage Graph Nav • Deterministic Replay • Ingest Telemetry • BIQOS  │
  └────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Complete Agent Catalog (32 Agents)

### Tier 1: UX, Onboarding & User Guidance (4 Agents)
1. **`AGT-UI-GUIDE-01` — VANA General Guidance Assistant** (`OPERATIONAL`): Explains workflows, roles, and forest telemetry in plain language. Read-only.
2. **`AGT-UI-ONBOARD-02` — Role-Based Onboarding Guide** (`OPERATIONAL`): Greets and guides first-time Admins, Forest Officers, and Field Agents.
3. **`AGT-UI-FORM-03` — Field Observation Form Assistant** (`OPERATIONAL`): Provides real-time field validation, coordinate hints, and format checks.
4. **`AGT-UI-RECOVER-04` — Offline Queue & Recovery Assistant** (`OPERATIONAL`): Monitors network connectivity and manages offline synchronization.

### Tier 2: Edge Intake, Validation & Data Quality (6 Agents)
5. **`AGT-INTAKE-VAL-01` — Group 3 Schema v2.2 Contract Validator** (`OPERATIONAL`): Validates incoming payloads against contract v2.2 schemas.
6. **`AGT-INTAKE-IDEMP-02` — SHA-256 Idempotency & Conflict Guard** (`OPERATIONAL`): Fingerprints payloads to guarantee exact-once ingestion.
7. **`AGT-INTAKE-HASH-03` — Raw Artifact Cryptographic Hash Attestor** (`INTEGRATING`): Verifies SHA-256 hashes of raw point clouds (.las) and TIFF images.
8. **`AGT-INTAKE-GEO-04` — Geospatial Boundary & Altitude Sanity Evaluator** (`INTEGRATING`): Verifies drone altitude limits and forest reserve boundaries.
9. **`AGT-INTAKE-PROV-05` — Cross-Field Provenance Agreement Checker** (`INTEGRATING`): Ensures observation natural keys match provenance blocks.
10. **`AGT-INTAKE-CALIB-06` — Hardware Calibration Attestation Inspector** (`OPERATIONAL`): Checks `sensor_calibration_registry` for signed certificates.

### Tier 3: Specialized Ecological & Forest Analytics (12 Agents)
11. **`AGT-ECO-TC-MANGROVE-01` — Thane Creek Mangrove Salinity & Canopy Density Assessor** (`PLANNED`): Analyzes canopy height models and NDVI trends.
12. **`AGT-ECO-MV-HYDRO-02` — Maval Western Ghats Catchment & Runoff Model** (`PLANNED`): Simulates monsoon runoff and slope stability.
13. **`AGT-ECO-SMR-ESTUARY-03` — Samachar Coastal Turbidity & Erosion Monitor** (`PLANNED`): Tracks estuarine sedimentation and tidal drift.
14. **`AGT-ECO-BIOMASS-04` — Forest Above-Ground Biomass Estimator** (`PLANNED`): Allometric equations for dry biomass tonnes/ha.
15. **`AGT-ECO-FIRE-05` — Fire Weather Risk & Fuel Moisture Analyzer** (`PLANNED`): Computes KBDI drought index and combustible fuel load.
16. **`AGT-ECO-ENCROACH-06` — Multi-Temporal Forest Encroachment Detector** (`PLANNED`): Compares satellite orthomosaics against legal cadastral borders.
17. **`AGT-ECO-CORRIDOR-07` — Wildlife Corridor Boundary & Fragmentation Tracker** (`PLANNED`): Evaluates structural connectivity for carnivore corridors.
18. **`AGT-ECO-SPECIES-08` — Botanical & Mangrove Species Identification Assistant** (`PLANNED`): Mobile edge vision classifier for mangrove flora.
19. **`AGT-ECO-CANOPY-09` — LIDAR Point-Cloud Stratification Classifier** (`PLANNED`): Separates understory, mid-canopy, and dominant emergent layers.
20. **`AGT-ECO-CARBON-10` — Carbon Stock Sequestration Rate Calculator** (`PLANNED`): Computes metric tonnes of CO2e sequestered biennially.
21. **`AGT-ECO-DROUGHT-11` — Soil Moisture & Evapotranspiration Deficit Evaluator** (`PLANNED`): Integrates Pravah weather data for drought stress modeling.
22. **`AGT-ECO-POACH-12` — Acoustic & Motion Anomaly Surveillance Correlator** (`PLANNED`): Correlates gunshot frequencies and nocturnal thermal detections.

### Tier 4: Statutory Governance, Policy & Audit (6 Agents)
23. **`AGT-GOV-SANSKAR-01` — SANSKAR Statutory Rule & Policy Explainer** (`OPERATIONAL`): Explains SANSKAR rulings and statutory rationales.
24. **`AGT-GOV-FAILCLOSED-02` — Fail-Closed ABSTAIN Invariant Watchdog** (`OPERATIONAL`): Guarantees missing context/calibration forces ABSTAIN (noop).
25. **`AGT-GOV-CUSTODY-03` — Chain-of-Custody Cryptographic Ledger Verifier** (`INTEGRATING`): Audits unbroken cryptographic links from sensor to UI.
26. **`AGT-GOV-FSI-04` — Forest Survey of India (ISFR) Benchmark Cross-Referencer** (`PLANNED`): Compares state cover against national ISFR baselines.
27. **`AGT-GOV-STATUTE-05` — Forest Conservation Act (FCA) Clearances Checker** (`PLANNED`): Evaluates diversion proposals against FCA Section 2.
28. **`AGT-GOV-DISPATCH-06` — Multi-Officer Human-in-the-Loop Dispatch Gate** (`INTEGRATING`): Two-man rule verification for physical sorties.

### Tier 5: Observability, Lineage & Replay (4 Agents)
29. **`AGT-OBS-LINEAGE-01` — Observation Graph Lineage Navigator** (`OPERATIONAL`): Builds 6-stage DAG lineage rail across observation lifecycle.
30. **`AGT-OBS-REPLAY-02` — Deterministic Observation State Replay Verifier** (`INTEGRATING`): Replays historical observations to verify state immutability.
31. **`AGT-OBS-TELEMETRY-03` — Multi-Zone Ingestion Rate & Latency Monitor** (`OPERATIONAL`): Aggregates ingestion rates and latency metrics.
32. **`AGT-OBS-INTEGRATION-04` — BIQOS 5-Pillar Contract Boundary Health Monitor** (`OPERATIONAL`): Heartbeat monitor for Identity, Data, Workflow, Governance, Observability.

---

## 4. Governance & Autonomy Guardrails

1. **User Supervisory Invariants (Pausable & Dismissible)**:
   - Every agent can be paused or resumed in real time via `POST /api/agents/toggle`.
   - Pausing an agent immediately blocks all interactions and returns status `PAUSED_BY_USER`.
2. **Zero Autonomous Dispatch Authority**:
   - No agent has permission to execute physical actions, modify MasterDB schemas, or elevate user credentials.
   - All dispatches require SANSKAR evaluation and human officer sign-off.
3. **Loop Prevention & Rate Limiting**:
   - The supervisor strictly enforces a maximum rate limit of 30 requests per minute per session, preventing uncontrolled agent loops.
4. **Audit Trail**:
   - All agent interactions and supervisor state changes are logged with ISO timestamps and operator identities.
