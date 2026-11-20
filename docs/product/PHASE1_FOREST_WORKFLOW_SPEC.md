# VANA Phase 1 — Forest Department Workflow Specification

**Document Version:** 1.0.0 (Phase 1 Production Release)  
**Standard:** Maharashtra State Forest Department Surveillance & Compliance Protocol  
**Sprint Mandate:** VANA × BIQOS 4-Hour Sprint Task Assignment (18 Nov 2026)  
**Product Owner:** Kaushal Yadav, Product, UX & Forest Department Workflow Owner  
**Last Verified:** 2026-11-20

---

## 1. End-to-End Observation Lifecycle

The complete observation lifecycle follows a deterministic, 6-stage pipeline:

```
[1. CAPTURE] ──► [2. VALIDATE] ──► [3. MASTERDB LEDGER] ──► [4. CONTEXT / PRAVAH] ──► [5. SANSKAR GATE] ──► [6. EVIDENCE & REPLAY]
   Ground /          Group 3           Canonical Record        Ecological Baseline       Fail-Closed Rule         Immutable Audit
  Edge Telemetry      v2.2 Check         CR-... (SHA-256)        Resolution (G2)           ABSTAIN / noop          Lineage Trail
```

### Detailed Stage Breakdown

#### Stage 1: Field Capture
- **Actor:** Field Agent or Automated Edge Telemetry Station.
- **Payload:** Conforms to Group 3 Ingestion Contract v2.2.
- **Fields Collected:**
  - `observation_id`: Strictly formatted as `^[A-Z0-9]+-Z[0-9]{1,2}-(F[0-9]{1,3}|EXT)-[A-Z0-9]+-OBS[0-9]{3,}$` (e.g. `TC-Z03-F01-SENSOR-OBS101`).
  - `survey_id`, `zone_id`, `flight_id`, `sensor_id`, `observation_seq`: Component identifiers strictly matching the `observation_id`.
  - `location`: Latitude (°N), Longitude (°E), Altitude (m), GNSS acquisition status (`NOT_VERIFIED` or `VERIFIED`).
  - `measurement` & `unit`: Quantitative observation (e.g. `8.4 m` canopy height, `12.5 mm` precipitation).
  - `raw_artifact` & `raw_artifact_integrity`: Checksum SHA-256 of the raw telemetry file or photograph.
  - `calibration_state`: `NOT_VERIFIED` (default field state) or `CALIBRATED_LAB`.
- **Offline Handling:** If agent is disconnected in remote forest reserves, observations are cached in browser `localStorage` (`vana_offline_queue`) and batched upon reconnection.

#### Stage 2: Contract Validation
- **Authority:** Group 1 MasterDB Ingestion Service (`POST /observations`).
- **Validation Engine:** `validate_semantic_v22.py` checking 22 constitutional contract clauses:
  - Required top-level and nested keys.
  - Pattern compliance of observation identifiers.
  - Internal component consistency (`survey_id`, `flight_id`, `mission_id` alignment).
  - Idempotency key derivation check (idempotency key must derive from `observation_id` to prevent duplicate record generation).
  - Numeric ranges: Latitude [-90, 90], Longitude [-180, 180], Measurement >= 0.
- **Outcomes:**
  - Valid: Proceeds to Stage 3.
  - Invalid: Immediate rejection with `HTTP 400 Bad Request` and structured error array.

#### Stage 3: MasterDB Canonical Persistence
- **Authority:** MasterDB Ledger (`vana_api.db` / PostgreSQL).
- **Persistence Actions:**
  - Assigns unique Canonical Record ID (`CR-...`).
  - Computes SHA-256 payload hash for tamper protection.
  - Evaluates `Idempotency-Key`:
    - First submission: Persists canonical record, writes audit event, returns `HTTP 201 Created`.
    - Repeated submission with matching key: Returns `HTTP 200 OK` with status `IDEMPOTENT_REPLAY` and the original `canonical_record_id`.
    - Key collision with different payload: Returns `HTTP 409 Conflict`.
- **Database Durability:** Survives service restarts and maintains foreign key constraints.

#### Stage 4: Context & Scientific Resolution (Pravah)
- **Authority:** Group 2 Pravah Environmental Service (Port 8012).
- **Function:** Reconciles raw observation with authoritative ecological baselines:
  - Historical weather records (Open-Meteo API).
  - Tidal states for coastal mangrove zones (Thane Creek).
  - Seasonal precipitation averages and canopy density indices.
- **Fail-Closed Rule:** If Group 2 is unreachable or context is unresolved, context is declared `UNRESOLVED` (not fabricated).

#### Stage 5: SANSKAR Governance & Statutory Gate
- **Authority:** Group 4 SANSKAR Policy Runtime (Port 8000).
- **Constitutional Decision Rule:**
  ```python
  if observation.calibration_state != "CALIBRATED_LAB" or gnss_status != "VERIFIED":
      effective_ruling = "ABSTAIN"
      action_taken = "noop"
      evidence_status = "governed_abstention"
  ```
- **Outcomes:**
  - `ABSTAIN`: Action paused. Generates immutable `abstention_record_id` (e.g. `ABS-5F10E61651E1`). No physical dispatch or hardware actuation is triggered.
  - `ALLOW`: Permitted **only** when sensor calibration is verified and statutory thresholds are met. Generates action request for administrative authorization.

#### Stage 6: Lineage, Audit & Executive Dashboard
- **Authority:** Group 5 Lineage Dashboard (Port 8080).
- **Function:**
  - Displays genuine audit events from MasterDB (`recent_events`).
  - Provides deterministic replay engine to verify mathematical identity across all 5 stages.
  - Exposes official FSI ISFR statutory forest cover benchmarks for executive reporting.

---

## 2. Statutory Review vs Operational Execution Boundary

| Operation | Forest Officer (`FOREST_OFFICER`) | Platform Admin (`ADMIN`) | Legal / Constitutional Authority |
|---|:---:|:---:|---|
| **Inspect Incoming Observations** | Allowed | Allowed | Forest Department Surveillance Mandate |
| **Audit Sensor Calibration & GNSS** | Allowed | Allowed | National Environmental Standards |
| **Verify Pravah Ecological Context** | Allowed | Allowed | State Biodiversity Board Protocol |
| **Query FSI ISFR Forest Cover** | Allowed | Allowed | Forest (Conservation) Act, 1980 |
| **Authorise Physical Field Dispatch** | **FORBIDDEN (403)** | **AUTHORIZED** | SANSKAR Statutory Governance Framework |
| **Modify Alert Thresholds / Policies** | Read-Only | **AUTHORIZED** | IT Security & Administration Mandate |

---

## 3. Incident Recovery & Field Guidance

1. **Rejected Submission (HTTP 400):** Check the returned `errors` list. Verify that `flight_id` matches the flight component in `observation_id` and that `idempotency_key` contains the `observation_id`.
2. **Offline Data Preservation:** When network connectivity is absent, field agents must keep the observation modal open or click "Submit to MasterDB" to trigger automatic local storage queueing. Never clear browser cache while offline observations are pending.
3. **Governed Abstention (ABSTAIN):** Forest Officers inspecting an `ABSTAIN` outcome must verify whether the sensor has undergone certified laboratory calibration. Calibrated hardware will yield `ALLOW` upon subsequent verification.
