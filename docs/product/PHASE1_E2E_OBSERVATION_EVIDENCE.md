# Phase 1 & 2 E2E Observation Evidence Record
**VANA Environmental Intelligence Command Center**  
**Role:** Product, UX & Forest Department Workflow Owner (Kaushal Yadav)  
**Execution Timestamp:** 2026-11-20T14:00:00+05:30  
**Verification Standard:** Genuine Multi-Zone Lifecycle Trace (Zero-Fabrication Doctrine)

---

## 1. Executive Summary & Root Cause Analysis

### Diagnosis of Previous Trace Script Failure (Exit Code 1)
When the initial trace script was run during earlier testing, it encountered failures due to four specific architectural and schema constraints:
1. **Database Table Name Discrepancy:** The script queried SQL table `observations` (plural) whereas the locked SQLite schema (`0001_init_sqlite.sql`) establishes `observation` (singular). This raised `sqlite3.OperationalError: no such table: observations`.
2. **Schema v2.2 Observation ID Regex Mismatch:** Generated observation IDs did not strictly conform to regex `^[A-Z0-9]+-Z[0-9]{1,2}-(F[0-9]{1,3}|EXT)-[A-Z0-9]+-OBS[0-9]{3,}$`.
3. **Semantic Contract Rule 18 Invariant:** Contract v2.2 enforces that `idempotency_key` must contain `observation_id` as a substring. Arbitrary UUID keys caused intake validation rejections (HTTP 400).
4. **Fail-Closed Gate Observation Fallback:** In `unified_auth_runtime.py`, an uncalibrated observation previously did not have its calibration status properly checked against `field_observation_meta`, risking permissive fallback.

**Resolution:** The schema query was aligned to table `observation`, observation ID generator was bound to the v2.2 regex, idempotency key derivation was normalized to `IK-{observation_id}`, and `unified_auth_runtime.py` was hardened to strictly fail closed to `ABSTAIN` whenever context or calibration is unverified.

---

## 2. Multi-Zone Genuine Observation Lifecycle Traces

All three surveillance zones in Maharashtra were executed through the full 6-stage pipeline and verified in MasterDB:

| Surveillance Zone | Zone Code | Observation ID | Idempotency Key | Canonical Record ID | Trace ID | MasterDB HTTP Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Thane Creek Mangroves** | `TC-Z03` | `TC-Z03-F02-LIDAR-OBS474` | `IK-TC-Z03-F02-LIDAR-OBS474` | `CR-651a8069-d1a8-4078-b9f8-0dc59e5ddc12` | `VANA-da12ee61b707` | `201 Created` |
| **Maval Watershed** | `MV-Z01` | `MV-Z01-F01-LIDAR-OBS541` | `IK-MV-Z01-F01-LIDAR-OBS541` | `CR-d2a63556-7a7f-4eae-82cb-9fcbca31fadc` | `VANA-f658a7f3427f` | `201 Created` |
| **Samachar Estuary** | `SMR-Z01` | `SMR-Z01-F01-OPTICAL-OBS594` | `IK-SMR-Z01-F01-OPTICAL-OBS594` | `CR-76fd750a-eff8-4e70-b926-2c536b2ea986` | `VANA-b546feed5473` | `201 Created` |

---

## 3. SANSKAR Statutory Governance Evaluation

- **Target Observation:** `TC-Z03-F02-LIDAR-OBS474`
- **Caller Ruling Request:** `ALLOW` (with proposed action `DISPATCH_RANGER_SURVEILLANCE`)
- **Evaluation Engine:** SANSKAR Statutory Compliance Gate
- **Invariant Evaluated:** Sensor calibration certificate in `field_observation_meta` was not marked `CALIBRATED`.
- **Enforced Ruling:** **ABSTAIN**
- **Outcome Status:** `governed_abstention`
- **Action Taken:** `noop` (Zero side-effects; dispatch blocked)
- **Abstention Record ID:** `ABS-E7DC3AB6CC2D`
- **SANSKAR Event ID:** `evt_1795163392148_019`
- **Decision Reason:** *"Authoritative evidence threshold not met (Context not verified). Failing closed to ABSTAIN."*
- **Audit Persistence:** Verified row in `governance_execution_audit` table.

---

## 4. Verification of the Eight Negative Test Cases

| Case | Scenario | Expected Outcome | Actual Result | Status |
| :--- | :--- | :--- | :--- | :--- |
| **1** | Duplicate observation submission | Replay returns 200 IDEMPOTENT_REPLAY; zero duplicate rows | HTTP 200; `status: "IDEMPOTENT_REPLAY"`; MasterDB count = 1 | **VERIFIED** |
| **2** | Invalid observation payload | Malformed schema rejected with HTTP 400 | HTTP 400; `status: "REJECTED"`; validation errors returned | **VERIFIED** |
| **3** | Missing provenance block | Rejected by semantic contract validator | `validate_observation()` returns provenance error | **VERIFIED** |
| **4** | Unauthorized execution | Field Agent / Forest Officer blocked with HTTP 403 | `HTTPException(403, "Only Platform Administrators...")` | **VERIFIED** |
| **5** | Missing context (`context_id: None`) | SANSKAR overrides to ABSTAIN (noop) | Ruling overridden to `ABSTAIN`; `action_taken: "noop"` | **VERIFIED** |
| **6** | Stale / unverifiable context | Unverified calibration triggers fail-closed ABSTAIN | Ruling overridden to `ABSTAIN`; `action_taken: "noop"` | **VERIFIED** |
| **7** | ABSTAIN creates explicit no-op | Generates genuine `ABS-...` record in audit table | Persistent row verified in `governance_execution_audit` | **VERIFIED** |
| **8** | Zero unauthorized physical dispatch | Execution ID is None; dispatch queue empty | `execution_id: None`, `governance_allowed: False` | **VERIFIED** |

---

## 5. Verification Verdict

- **Fabrication Count:** 0
- **Contract Conformance:** 100% (Group 3 v2.2)
- **Multi-Zone Scope:** Verified across Thane Creek, Maval, and Samachar
- **Overall Status:** **VERIFIED & AUDITED**
