# VANA Backend API Inventory and Service Catalog

**Audit Phase**: VANA Phase 2 Full System Audit  
**Repository**: `PriteshPatra-BHIV/finalvana`  
**Date**: October 2026  
**Auditor**: Antigravity Senior Systems Architect & Security Engineering  

---

## 1. Architectural Overview

The VANA backend platform is structured into decoupled subsystem boundaries adhering to a fail-closed, zero-fabrication governance architecture:

```
[ Field Sensor / Ingestion Clients / Admin UI ]
                       │
                       ▼
         [ Reverse Proxy Gateway (:8080 / Vercel) ]
                       │
       ┌───────────────┼───────────────┬────────────────┐
       ▼               ▼               ▼                ▼
 [ /proxy/auth ]  [ /proxy/g1 ]   [ /proxy/g2 ]   [ /proxy/g4 ]
  Unified Auth      MasterDB      Pravah Context    Workflow Runtime
   & RBAC API     (FastAPI/DB)      (Science)          (SANSKAR)
  (:8000/auth)    (:8013 / :8000) (niyantran)      (:8010 / :8000)
```

1. **Group 1 (MasterDB)**: Canonical database persistence, Group 3 observation validation, official forest-cover statutory benchmarks, and SHA-256 idempotency tracking. Implemented with FastAPI in `backend/group1-masterdb/api/main.py`.
2. **Group 2 (Pravah Scientific Context API)**: Contextual resolution engine evaluating physical observation evidence, temporal validity, and spatial co-location. Fail-closed decision logic implemented in `backend/group4-workflow-runtime/group2Context.js` and proxied via Next.js routes in `backend/group2-pravah-api/api_routes/group2/route.ts`.
3. **Group 3 (Sensor Contracts & Schemas)**: Frozen JSON Schema v2.2 specifications (`observation.schema.json` and `observation.schema.v2.2.json`) governing hardware telemetry, GPS accuracy, and calibration constraints.
4. **Group 4 (Workflow Runtime / SANSKAR)**: Governed execution gate evaluating rulings, enforcing noop abstentions, and issuing immutable audit records (`POST /vana/execute`).
5. **Unified Authentication & RBAC Service**: Session security, role enforcement (`PLATFORM_ADMIN`, `AUDITOR`, `GOVERNANCE_STEWARD`, `APPROVED_CONSUMER`), token verification, and permission mapping.

---

## 2. Exhaustive API Route Inventory

The platform defines **11 core backend routes** across the four subsystems and gateway:

| Route Path | Method | Owning Subsystem | Source File | Status / Verification |
| :--- | :--- | :--- | :--- | :--- |
| `GET /health` | GET | Group 1 MasterDB | `backend/group1-masterdb/api/main.py:45` | Verified (Operational) |
| `POST /observations` | POST | Group 1 MasterDB | `backend/group1-masterdb/api/main.py:80` | Verified (Operational) |
| `GET /observations/{observation_id}` | GET | Group 1 MasterDB | `backend/group1-masterdb/api/main.py:179` | Verified (Operational) |
| `POST /official/forest-cover` | POST | Group 1 MasterDB | `backend/group1-masterdb/api/main.py:54` | Verified (Operational) |
| `GET /official/forest-cover/{record_id}` | GET | Group 1 MasterDB | `backend/group1-masterdb/api/main.py:67` | Verified (Operational) |
| `GET /datasets/{dataset_id}/forest-cover` | GET | Group 1 MasterDB | `backend/group1-masterdb/api/main.py:75` | Verified (Operational) |
| `POST /api/group2/context/resolve` | POST | Group 2 Pravah Context | `backend/group4-workflow-runtime/group2Context.js:30` | Verified (Operational) |
| `POST /vana/execute` | POST | Group 4 SANSKAR Runtime | `backend/group2-pravah-api/api_routes/group4/route.ts:6` | Verified (Proxy Operational) |
| `POST /auth/login` | POST | Unified Backend Auth | External Gateway / `server.py:38` | Contract Verified |
| `GET /auth/me` | GET | Unified Backend Auth | External Gateway / `server.py:38` | Contract Verified |
| `POST /auth/register` | POST | Unified Backend Auth | External Gateway / `server.py:38` | Contract Verified |

---

## 3. Detailed Route Specifications

### 3.1 `GET /health`
- **Subsystem**: Group 1 MasterDB (`backend/group1-masterdb/api/main.py:45`)
- **Authentication**: None (Public)
- **Request Headers**: None required
- **Response Schema** (HTTP 200 OK):
  ```json
  {
    "status": "healthy",
    "service": "VANA MasterDB Observation API",
    "version": "1.0.0"
  }
  ```

---

### 3.2 `POST /observations`
- **Subsystem**: Group 1 MasterDB (`backend/group1-masterdb/api/main.py:80-177`)
- **Authentication**: Public or API Token (Internal Service / Field Ingestion)
- **Headers**:
  - `Content-Type`: `application/json` (Required)
  - `Idempotency-Key`: `string` (Optional, maps to natural idempotency record)
- **Request Body Schema**: Group 3 V2.2 Observation Payload
  - `observation_id` (string, required): Format `^[A-Z0-9_-]{8,64}$`
  - `contract_version` (string, required): `"2.2"`
  - `observation_timestamp` (ISO 8601 string, required)
  - `observation_type` (string, required): e.g., `"precipitation"`, `"canopy_height"`
  - `measurement` (number | string | null, required)
  - `unit` (string | null): Unit of measurement (e.g., `"mm"`, `"m"`)
  - `accuracy` (number | string): Must be number or literal `"NOT_VERIFIED"`
  - `calibration_status` (string, enum: `"VERIFIED"`, `"NOT_VERIFIED"`, `"EXPIRED"`, `"FAILED"`)
  - `quality_status` (string, enum: `"CAPTURED"`, `"VALIDATED"`, `"REJECTED"`, `"PROCESSED"`)
  - `synthetic_state` (string, enum: `"PHYSICAL"`, `"CONTROLLED"`, `"SYNTHETIC"`, `"SIMULATED"`, `"UNKNOWN"`)
  - `location` (object, required):
    - `latitude` (float, -90 to 90)
    - `longitude` (float, -180 to 180)
    - `altitude_m` (float | null)
    - `gnss_status` (string)
    - `position_accuracy_m` (float | null)
  - `raw_artifact` (string | null): Relative path to artifact file
  - `raw_artifact_integrity` (object | null):
    - `checksum_sha256` (64-char hex string)
    - `hash_algorithm` (`"sha256"`)
    - `artifact_type` (string)
  - `provenance_reference` (string, required): Path or URI to provenance manifest
- **Validation Rules**:
  - Authoritative validation handled by `api.validation.validate_observation` against `observation.schema.json`.
  - Normalizes legacy v1.2/v2.1 fields before schema validation.
  - Generates SHA-256 fingerprint for request replay detection.
  - Automatically inserts foreign key parents: `source` and `dataset`.
- **Response Schemas**:
  - **HTTP 201 Created** (`ACCEPTED`):
    ```json
    {
      "trace_id": "VANA-xxxxxxxxxxxx",
      "observation_id": "TC-Z03-EXT-OPENMETEO-OBS001",
      "canonical_record_id": "CR-b4615a27-7ab1-4bde-a078-a56fa0f2414c",
      "status": "ACCEPTED",
      "message": "Observation persisted through canonical VANA persistence."
    }
    ```
  - **HTTP 200 OK** (`IDEMPOTENT_REPLAY`): Returned when identical payload is resubmitted.
  - **HTTP 409 Conflict** (`IDEMPOTENCY_CONFLICT`): Returned when an existing Idempotency-Key is reused with altered payload data.
  - **HTTP 400 Bad Request** (`REJECTED`): Returned when payload fails Group 3 schema validation with detailed list of errors.

---

### 3.3 `GET /observations/{observation_id}`
- **Subsystem**: Group 1 MasterDB (`backend/group1-masterdb/api/main.py:179-206`)
- **Authentication**: Public
- **Path Parameters**:
  - `observation_id` (string, required): Primary identifier (e.g., `TC-Z03-EXT-OPENMETEO-OBS001`)
- **Response Schema** (HTTP 200 OK):
  ```json
  {
    "trace_id": "VANA-xxxxxxxxxxxx",
    "observation_id": "TC-Z03-EXT-OPENMETEO-OBS001",
    "status": "RETRIEVED",
    "observation": {
      "observation_id": "TC-Z03-EXT-OPENMETEO-OBS001",
      "canonical_record_id": "CR-b4615a27-7ab1-4bde-a078-a56fa0f2414c",
      "dataset_id": "DS-EXTERNAL-API-TC-Z03-F02",
      "geo_id": "GEO-...",
      "observed_at": "2026-08-25T11:00:00+00:00",
      "observation_timestamp": "2026-08-25T11:00:00+00:00",
      "source_timestamp": "2026-08-25T11:00:00+00:00",
      "capture_method": "external_api",
      "device_id": null,
      "species": null,
      "observation_type": "precipitation",
      "quality_status": "VALIDATED",
      "synthetic_state": "CONTROLLED",
      "location": {
        "latitude": 19.1288,
        "longitude": 72.9421,
        "altitude_m": 4.0,
        "gnss_status": null,
        "position_accuracy_m": null
      },
      "measurements": [
        {
          "measurement_id": "MEAS-...",
          "metric_name": "precipitation",
          "data_type": "NUMERIC",
          "value": 0.1,
          "unit": "mm",
          "provenance": { ... }
        }
      ],
      "raw_artifacts": []
    }
  }
  ```
  - **HTTP 404 Not Found**: If observation does not exist.

---

### 3.4 `POST /official/forest-cover`
- **Subsystem**: Group 1 MasterDB (`backend/group1-masterdb/api/main.py:54-65`)
- **Authentication**: Admin / Data Steward
- **Headers**:
  - `Content-Type`: `application/json`
  - `Idempotency-Key`: `string` (Optional)
- **Request Body Schema**: `OfficialForestCoverRequest` (`api/models.py:81-100`)
  ```json
  {
    "source": {
      "source_id": "SRC-FSI-ISFR-2023",
      "source_type": "GOVERNMENT_DATASET",
      "source_name": "India State of Forest Report 2023",
      "publisher": "Forest Survey of India, Ministry of Environment, Forest and Climate Change",
      "source_url": "https://fsi.nic.in/isfr-2023",
      "retrieved_at": "2026-08-20T00:00:00Z",
      "citation": "Forest Survey of India (2023). India State of Forest Report 2023."
    },
    "dataset": {
      "dataset_id": "DS-FSI-ISFR-2023-FOREST-COVER",
      "dataset_name": "India State of Forest Report 2023 Forest Cover",
      "methodology": "Multi-date satellite data (LISS-III, Resourcesat-2) interpreted using NDVI transformation"
    },
    "assessment_year": 2023,
    "geography_level": "STATE",
    "state": "Maharashtra",
    "district": null,
    "boundary_reference": "Recorded Forest Area (RFA) boundary provided by Maharashtra State Forest Department",
    "forest_cover_area": 50858.53,
    "forest_cover_percentage": 16.53,
    "very_dense_forest_area": 9538.99,
    "moderately_dense_forest_area": 15827.39,
    "open_forest_area": 10744.55,
    "mangrove_area": 315.09,
    "unit": "km2",
    "methodology": "Multi-date satellite data (LISS-III, Resourcesat-2, 23.5m resolution)",
    "quality_status": "EXTRACTED",
    "provenance_reference": "ISFR-2023/Chapter-2/Table-2.4"
  }
  ```
- **Response Schemas**:
  - **HTTP 201 Created**: `{"status": "ACCEPTED", "record_id": "FC-...", "http_status": 201}`
  - **HTTP 200 OK**: `{"status": "REPLAY", "record_id": "FC-...", "http_status": 200}`
  - **HTTP 409 Conflict**: `{"status": "CONFLICT", "record_id": "FC-...", "http_status": 409}`
  - **HTTP 400 Bad Request**: Validation failure messages.

---

### 3.5 `GET /official/forest-cover/{record_id}`
- **Subsystem**: Group 1 MasterDB (`backend/group1-masterdb/api/main.py:67-72`)
- **Authentication**: Public
- **Path Parameters**:
  - `record_id`: Canonical record identifier (format `FC-[a-f0-9]{32}`)
- **Response**: Full benchmark record object with source attribution, district breakdown, canopy density zones, and mangrove area.

---

### 3.6 `GET /datasets/{dataset_id}/forest-cover`
- **Subsystem**: Group 1 MasterDB (`backend/group1-masterdb/api/main.py:75-77`)
- **Authentication**: Public
- **Path Parameters**:
  - `dataset_id`: Dataset identifier (e.g. `DS-FSI-ISFR-2023-FOREST-COVER`)
- **Response Schema** (HTTP 200 OK):
  ```json
  {
    "dataset_id": "DS-FSI-ISFR-2023-FOREST-COVER",
    "records": [
      {
        "record_id": "FC-9e602eff084ffc653d5bab7e0cfc6c52",
        "dataset_id": "DS-FSI-ISFR-2023-FOREST-COVER",
        "dataset_name": "India State of Forest Report 2023 Forest Cover",
        "state": "Maharashtra",
        "district": null,
        "assessment_year": 2023,
        "geography_level": "STATE",
        "forest_cover_area": 50858.53,
        "forest_cover_percentage": 16.53,
        "very_dense_forest_area": 9538.99,
        "moderately_dense_forest_area": 15827.39,
        "open_forest_area": 10744.55,
        "mangrove_area": 315.09,
        "unit": "km2",
        "quality_status": "EXTRACTED",
        "provenance_reference": "ISFR-2023/Chapter-2/Table-2.4"
      }
    ]
  }
  ```

---

### 3.7 `POST /api/group2/context/resolve`
- **Subsystem**: Group 2 Pravah Scientific Context (`backend/group4-workflow-runtime/group2Context.js:30`)
- **Proxy**: `backend/group2-pravah-api/api_routes/group2/route.ts` & `/proxy/g2/api/group2/context/resolve`
- **Authentication**: Forwarded Bearer Token
- **Request Body**:
  ```json
  {
    "observationId": "TC-Z03-EXT-OPENMETEO-OBS001",
    "location": { "latitude": 19.1288, "longitude": 72.9421 },
    "timestamp": "2026-08-25T11:00:00Z"
  }
  ```
- **Governance Behavior**:
  - Fetches canonical observation from Group 1 (`/observations/{observationId}`).
  - Validates `canonical_record_id`, `confidence`, and `timestamp`.
  - **Fail-Closed Doctrine**: If source timestamp is absent, canonical linkage is missing, or record is unverified, immediately returns `ABSTAIN` with `context_id: null`.
- **Response Schema (ABSTAIN Ruling)**:
  ```json
  {
    "observation_id": "TC-Z03-EXT-OPENMETEO-OBS001",
    "canonical_record_id": "CR-b4615a27-7ab1-4bde-a078-a56fa0f2414c",
    "context_id": null,
    "ruling": "ABSTAIN",
    "action_eligibility": false,
    "abstention_required": true,
    "action_request": null,
    "evidence": {
      "source": "Open-Meteo.com",
      "confidence": "NOT VERIFIED",
      "missing_critical_data": "TIMESTAMP",
      "provenance_reference": "...",
      "canonical_observation_location": { ... }
    },
    "provenance": {
      "group2_decision_time": "2026-10-29T14:45:00.000Z",
      "reason": "MISSING_SOURCE_TIMESTAMP",
      "message": "Authoritative evidence threshold not met (Missing source timestamp). Failing closed to ABSTAIN."
    }
  }
  ```

---

### 3.8 `POST /vana/execute`
- **Subsystem**: Group 4 Workflow Runtime / SANSKAR (`backend/group2-pravah-api/api_routes/group4/route.ts`)
- **Proxy**: `/proxy/g4/vana/execute`
- **Authentication**: Bearer Token (Roles: `PLATFORM_ADMIN`, `GOVERNANCE_STEWARD`)
- **Request Body**: Context ruling object returned by `/api/group2/context/resolve`
- **Response Schema (Abstention Gate Outcome)**:
  ```json
  {
    "success": true,
    "action": "noop",
    "status": "GOVERNED_ABSTENTION",
    "abstention_record_id": "abs_1771922718115_715",
    "event_id": "evt_1771922718115_244",
    "execution_id": "exec_1771922718115_908",
    "governance": {
      "fail_closed_enforced": true,
      "policy_evaluated": "STRICT_CANONICAL_TIMESTAMP_GATE",
      "disposition": "ABSTAIN"
    }
  }
  ```

---

### 3.9 Unified Authentication Routes (`POST /auth/login`, `GET /auth/me`, `POST /auth/register`)
- **Subsystem**: Central Authentication Boundary (`http://localhost:8000/auth` / `/proxy/auth`)
- **Security Policy**: Enforced at server proxy level (`server.py:84-90`); only `/login`, `/register`, `/me` permitted.
- **Login Request**:
  ```json
  { "username": "admin", "password": "..." }
  ```
- **Login Response**:
  ```json
  {
    "access_token": "eyJhbGciOi...",
    "token_type": "bearer",
    "user": {
      "username": "admin",
      "role": "PLATFORM_ADMIN",
      "display_name": "Platform Administrator",
      "permissions": ["view_dashboard", "run_pipeline", "admin_access", "view_audit_logs"]
    }
  }
  ```
- **Token Verification (`GET /auth/me`)**:
  - Validates `Authorization: Bearer <token>`
  - Returns active user session and verified permissions.

---

## 4. Database Models, Migrations, and Schema Architecture

### MasterDB Schema (PostgreSQL / SQLite dual compatibility)
The database structure is maintained across 10 migrations (`0001_init.sql` through `0008_official_forest_cover.sql`):

1. **`schema_version`**: Migration application ledger (`version`, `applied_at`, `description`).
2. **`source`**: Data source registry (`source_id`, `source_type`, `title`, `publisher`, `url`, `citation`, `retrieved_at`, `is_synthetic`, `notes`).
3. **`dataset`**: Registered datasets (`dataset_id`, `dataset_name`, `source_id`, `methodology`, `schema_version`, `status`).
4. **`geo_location`**: Spatial coordinates and CRS (`geo_id`, `scope`, `place_name`, `lat`, `lon`, `altitude_m`, `crs`).
5. **`observation`**: Authoritative canonical records (`observation_id`, `canonical_record_id`, `dataset_id`, `geo_id`, `observed_at`, `capture_method`, `species`, `observation_type`, `quality_status`, `confidence`, `is_synthetic`, `synthetic_state`, `provenance_reference`, `contract_version`, `source_timestamp`).
6. **`field_observation_meta`**: Hardware metadata (`observation_id`, `device_id`, `operator`, `mission_id`, `accuracy`, `accuracy_status`, `calibration_status`, `gnss_status`, `position_accuracy_m`, `processing_status`).
7. **`measurement`**: Individual observations (`measurement_id`, `observation_id`, `metric_name`, `data_type`, `value`, `value_text`, `unit`, `method`).
8. **`raw_artifact`**: Evidence artifacts (`artifact_id`, `observation_id`, `artifact_type`, `storage_ref`, `content_hash`, `hash_algorithm`, `captured_at`).
9. **`processing_run`**: Ingestion runs (`run_id`, `source_id`, `dataset_id`, `pipeline_stage`, `status`, `actor`).
10. **`idempotency_record`**: Strict replay gate (`idempotency_key`, `observation_id`, `canonical_record_id`, `request_fingerprint`, `first_response_status`).
11. **`provenance`**: Lineage audit chain (`provenance_id`, `measurement_id`, `raw_artifact_id`, `source_id`, `run_id`, `derivation_note`, `recorded_at`).
12. **`official_forest_cover_record`**: Statutory benchmarks (`record_id`, `dataset_id`, `assessment_year`, `geography_level`, `state`, `district`, `forest_cover_area`, `forest_cover_percentage`, `very_dense_forest_area`, `moderately_dense_forest_area`, `open_forest_area`, `mangrove_area`, `provenance_reference`).

---

## 5. Summary of Verification Status

- **Group 1 MasterDB Pytest Suite**: 43/43 tests passed (`tests/test_api.py`: 33, `tests/test_official_forest_cover.py`: 10).
- **Group 1 Contract Validation**: 18/18 checks passed (`validate_fixtures.py`).
- **Group 1 Roundtrip & Idempotency Proof**: 100% passed (`test_roundtrip.py`, `eod_rehearsal.py`).
- **Frontend Auth & RBAC Integration**: 32/32 tests passed (`test_auth_integration.js`).
