# VANA × BIQOS Alignment & Capability Mapping Evidence

**Document Reference:** `BHIV-VANA-PROD-BIQOS-ALIGN-2026-11`  
**Owner:** Kaushal Yadav (Product & Forest Department Workflow Owner, BHIV)  
**Target Repository:** `finalvana-main`  
**External Reference Repositories (Read-Only Inspected):**
- `BHIV-BIQOS-P0-EXECUTION-main` (Accountable Lead: Raj)
- `BHIV-Core-TANTRA-Sutradhar-main` (Accountable Lead: Raj Prajapati)

**Constitutional Rule:** VANA does **not** own or edit BIQOS or TANTRA repositories. Every pairing claim below is backed by inspected contracts, live runtime evidence where verified, and honest **`BLOCKED (Upstream)`** / **`PENDING`** status tagging where external gates remain open.

---

## 1. Authority & Semantic Boundary Matrix (VANA × BIQOS × BHIV)

Per the Group Execution Assignment and BIQOS `SYSTEM_BOUNDARIES.md`, every subsystem has exactly **one constitutional owner** — VANA never creates shadow registries, parallel governance authorities, or duplicate runtimes:

| Constitutional System | Declared Authority & Scope | Accountable Owner | VANA Interaction Surface | Boundary Compliance Status |
| :--- | :--- | :--- | :--- | :---: |
| **TMS** | Strategy, conservation targets & statutory mandates | BHIV Strategy | Defines Maharashtra Forest Dept monitoring priorities & FSI statutory compliance targets consumed by VANA | **ALIGNED** |
| **GC (Governance Council / Shakti / Sovereign)** | Sovereign governance policies & `ALLOW` / `DENY` / `ABSTAIN` authority | Aakanksha (Sovereign) / GC | VANA never fabricates `ALLOW` rulings; Group 2 fails closed to `ABSTAIN` when authoritative evidence is missing | **ALIGNED (Local Fail-Closed)** · Upstream Sovereign API attachment **PENDING** |
| **MDU (Metadata & Data Understanding)** | Canonical schemas, ontologies, semantic validation & append-only provenance event logs | Nupur / Harsha | VANA uses frozen Group 3 `observation.schema.v2.2.json` & SHA-256 provenance; ready to propose canonical environmental schema to MDU | **`BLOCKED (Upstream)`** (`GAP-01` timeout & `GAP-02` lineage model mismatch) |
| **MASTERDB (BIQOS Central)** | Dataset registration, discovery, retrieval, lifecycle state graph & BCAES catalog (`http://163.128.209.18:30308`) | Central Platform / Kavy (BCAES) / Rayyan (IAM) | 3 VANA datasets already `REGISTERED` in live MASTERDB; VANA local MasterDB (`:8013`) handles G1 canonical persistence without acting as an ecosystem-wide shadow registry | **`PARTIAL` / `BLOCKED (Upstream)`** (`GAP-03`, `GAP-04`, `GAP-08`) |
| **Bucket** | Immutable append-only truth & evidence storage (`bhiv-bucket-i1l6.onrender.com`) | Siddhesh / Ashmit Pandey | Tier-1 restricted store (`ACCESS_CONTROL_POLICY.md`); VANA attaches via BHIV Core API rather than writing directly to Tier-1 internals | **`PENDING`** (Awaiting BHIV Core `vana_agent` onboarding) |
| **TANTRA (BHIV Core / CET / Sarathi / Bridge)** | Governed runtime execution contracts & 8-step cryptographic enforcement chain | Raj Prajapati (Core), Tanvi (CET), Rajaryan (Sarathi), Ranjit (Bridge) | VANA G4 SANSKAR enforces `noop` on `ABSTAIN` locally; target pairing routes authorized `ALLOW` dispatches through BHIV Core `POST /execute` | **`PENDING`** (No `vana_agent` in `agent_configs.json`; CET only supports `TransferFunds`) |
| **NIYANTRAN / SHAKTI** | Constitutional workflow execution & orchestration (`bhiv-Shakti-GC-Infra`) | Karana / Pratik | VANA `/proxy/g2` targets `https://niyantran.blackholeinfiverse.com` (`DEF-05`); OpenAPI execution contract pending Stage B audit (`GAP-05`) | **`BLOCKED (Upstream)`** (`DEC-01`, `GAP-05`, `DEF-05`) |
| **InsightFlow / Pravah** | Federated dataset registry, observability telemetry, health & replay references | Vijay (InsightFlow), Shivam / Rayyan (Pravah) | VANA emits `VANA-<hex>` trace IDs & `/dashboard/summary`; ready to propagate `X-Trace-Id` once stable production URL replaces ephemeral `ngrok` | **`BLOCKED (Upstream)`** (Ephemeral `ngrok` URL; Pravah contract uninspected) |

---

## 2. Five-Pillar BIQOS Pairing Evidence Matrix

| # | BIQOS Pairing Pillar | Contract Requirement (PDF Page 3) | Verified VANA Implementation & Local Proof | Live External BIQOS Pairing Proof / Blocker | Honest EOD Status |
| :-: | :--- | :--- | :--- | :--- | :---: |
| **1** | **Identity & Access** | Agreed user/role mapping, auth, authorization, least-privilege access | `ADMIN`, `FOREST_OFFICER`, `FIELD_AGENT` enforced via `bcrypt` + Bearer sessions in `backend/auth_service.py`; `/auth/register` blocked (`403`); non-Admin G4 execution blocked (`403`). 32/32 frontend RBAC tests passing. | BIQOS has no ecosystem-wide human SSO (`GAP-06`); `GET /capabilities` returns `401` (`GAP-03`). G1 write routes (`POST /observations`, `POST /official/forest-cover`) still need Bearer RBAC (`BLK-VANA-03`). | **`PARTIAL`** *(Local G4 verified; G1 auth + BIQOS SSO pending)* |
| **2** | **Data & Metadata** | Documented observation, decision, outcome & provenance contracts; schema compatibility & source ownership | Frozen Group 3 `observation.schema.v2.2.json` (`CR-<uuid>`), FSI ISFR 2023 statutory dataset (`50,858.53 km²`), SHA-256 raw artifact checksums & idempotency (`201`/`200`/`409`/`400`) verified (43/43 MasterDB tests + 10/10 scenarios). | **Live BIQOS Proof:** 3 VANA datasets already `REGISTERED` in live MASTERDB (`163.128.209.18:30308`): `DS-FSI-ISFR-2023-FOREST-COVER` (`pkg-04d17aaca527`), `DS-VANA-SPATIAL-LAYERS` (`pkg-b28e736588f8`), `DS-VANA-THANE-CREEK-BLUE-CARBON` (`pkg-ba021794347b`). **Blocked** at `NOT_RETRIEVABLE` due to MDU `GAP-01`/`GAP-02` & unseeded BCAES `GAP-04`. | **`PARTIAL / BLOCKED (Upstream)`** |
| **3** | **Workflow** | Event/API hand-off, correlation/trace IDs, retry/idempotency, explicit failure responses | End-to-end correlation IDs (`VANA-...`, `CR-...`, `evt_...`, `exec_...`, `ABS-...`), `Idempotency-Key` deduplication/conflict (`200`/`409`), and fail-closed `400`/`401`/`403` verified across G1–G5. | Not yet attached to BHIV Core `POST /execute` (`agent_configs.json` lacks `vana_agent`); CET only supports `TransferFunds`; NIYANTRAN contract uninspected (`GAP-05`). G4 local DB persistence pending (`BLK-VANA-02`). | **`PARTIAL / BLOCKED (Upstream)`** |
| **4** | **Governance** | Policy decisions remain with authorized owner; neither system assumes another's authority | MasterDB persists records without inventing rulings; Group 2 fails closed to `ABSTAIN` (`context_id: null`); Group 4 enforces `decision_action: "noop"` on `ABSTAIN` even for `ADMIN` tokens. | Respects BIQOS `ACCESS_CONTROL_POLICY.md` Tier-1 isolation (zero unauthorized access to Sovereign/Sarathi/Bucket internals). Needs server-side G2 ruling verification in G4 (`BLK-VANA-02`). | **`VERIFIED LOCALLY`** · Upstream TANTRA chain **PENDING** |
| **5** | **Observability** | Shared trace IDs, service health, exceptions, audit events & replay references visible | `/health` probes active on G1 (`:8013`) and G4 (`:8000`); deterministic 4-invariant lineage replay verified byte-for-byte on SHA-256 checksums. | `GET /dashboard/summary` currently has hardcoded `audit_events` & `"ABSTAIN 100%"` (`BLK-VANA-01`); InsightFlow registry uses ephemeral `ngrok` URL; Pravah OpenAPI contract not yet published. | **`PARTIAL / BLOCKED (Upstream)`** |

---

## 3. Capability Lifecycle Mapping (BIQOS 6-Stage State Graph)

Mapped strictly against `BHIV-BIQOS-P0-EXECUTION-main/docs/architecture/CAPABILITY_LIFECYCLE.md` (preserving the **Non-Interchangeability Rule**: Discovery ≠ Registration ≠ Certification ≠ Availability ≠ Execution):

| VANA Asset / Capability | BIQOS Identifier / Source | Current Honest Lifecycle Stage | Evidence & Blocking Gate to Next Stage |
| :--- | :--- | :---: | :--- |
| **VANA Lineage Dashboard Repo** | Slice 1 Repo #19 (`bhiv-Vana_lineage_dashboard`) | **`DISCOVERED`** (`UNREGISTERED_IN_MASTERDB`) | Reconciled in BIQOS Slice 1 census; blocked from `REGISTERED` until Data Steward / Kavy seeds `cap-vana-forest-intelligence` into BCAES (`GAP-04` / `DEC-04`). |
| **FSI ISFR 2023 Forest Cover Dataset** | `DS-FSI-ISFR-2023-FOREST-COVER` (`pkg-04d17aaca527`) | **`REGISTERED`** (`NOT_RETRIEVABLE`) | Verified in live MASTERDB Oct 28 reseed; blocked from `CERTIFIED` → `AVAILABLE` by `PACKAGE_CERTIFIED: false` and MDU `LINEAGE_REGISTERED` failure (`GAP-01`/`GAP-02`). |
| **VANA Spatial Layers Dataset** | `DS-VANA-SPATIAL-LAYERS` (`pkg-b28e736588f8`) | **`REGISTERED`** (`NOT_RETRIEVABLE`) | Same upstream MASTERDB certification & MDU provenance blockers (`GAP-01`/`GAP-02`). |
| **Thane Creek Blue Carbon Dataset** | `DS-VANA-THANE-CREEK-BLUE-CARBON` (`pkg-ba021794347b`) | **`REGISTERED`** (`NOT_RETRIEVABLE`) | Same upstream MASTERDB certification & MDU provenance blockers (`GAP-01`/`GAP-02`). |
| **VANA Governed Execution Gate (SANSKAR)** | Local `POST /vana/execute` (Target: `vana_agent` on BHIV Core) | **`DISCOVERED` (Local Operational / External Unattached)** | Operational locally on `:8000`; awaits BHIV Core `agent_configs.json` onboarding (Raj) & CET environmental intent registration (Tanvi). |

---

## 4. Ready-to-Submit Onboarding Payloads (For BIQOS / TANTRA Owners)

> **Note:** These payloads are prepared **inside VANA docs only** for submission to BIQOS / TANTRA owners. Zero changes have been made to BIQOS or TANTRA repositories.

### 4.1 Proposed BCAES Capability Manifest (For Submission to Raj & Kavy — `GAP-04` / `DEC-04`)
```json
{
  "id": "cap-vana-forest-intelligence",
  "name": "VANA Environmental Governance Monitoring System",
  "version": "1.0.0",
  "owner": "VANA Team (Kaushal Yadav, Pritesh Patra, Rhugved Chavan, Pratik Bhuvad)",
  "classification": "capability",
  "domain": "geospatial_environmental_governance",
  "repository": "finalvana-main",
  "slice1_inventory_ref": "bhiv-Vana_lineage_dashboard",
  "schema_version": "2.2",
  "canonical_datasets": [
    "DS-FSI-ISFR-2023-FOREST-COVER",
    "DS-VANA-SPATIAL-LAYERS",
    "DS-VANA-THANE-CREEK-BLUE-CARBON"
  ],
  "roles": ["ADMIN", "FOREST_OFFICER", "FIELD_AGENT"],
  "governance_mode": "fail_closed_abstain_noop",
  "health_endpoints": {
    "masterdb": "/proxy/g1/health",
    "runtime": "/proxy/g4/health"
  },
  "status": "PROPOSED_FOR_REGISTRATION"
}
```

### 4.2 Proposed BHIV Core Product Attachment Spec (For Submission to Raj Prajapati — `Product_Attachment_Framework.md`)
```json
{
  "agent_name": "vana_forest_governance_agent",
  "agent_type": "product",
  "description": "VANA Forest Department observation-to-governed-outcome agent (G1-G5 fail-closed ABSTAIN/ALLOW gate)",
  "capabilities": [
    "environmental_observation_validation",
    "statutory_forest_benchmark_lookup",
    "governed_abstention_noop",
    "lineage_replay_verification"
  ],
  "connection_type": "http_api",
  "endpoint": "https://vana.blackholeinfiverse.com/proxy/g4/vana/execute",
  "health_check": "https://vana.blackholeinfiverse.com/proxy/g4/health",
  "trace_propagation": {
    "header": "X-Trace-Id",
    "canonical_id_field": "canonical_record_id"
  },
  "failure_mode": "fail-closed",
  "max_concurrent": 5,
  "timeout_seconds": 30
}
```

### 4.3 Proposed MDU Canonical Environmental Observation Schema Submission (For Nupur / Harsha)
- **Source Contract:** `finalvana-main/backend/group3-sensor-contracts/` (`observation.schema.v2.2.json`)
- **Key Mandatory Fields:** `observation_id` (`^[A-Z0-9_-]{8,64}$`), `contract_version: "2.2"`, `observation_timestamp` (ISO-8601, zero fallback), `observation_type`, `measurement`, `calibration_status` (`VERIFIED|NOT_VERIFIED|EXPIRED|FAILED`), `quality_status`, `synthetic_state`, `location` (`latitude`, `longitude`), `raw_artifact_integrity.checksum_sha256`, `provenance_reference`.
- **Provenance Compatibility:** Aligns with MDU's append-only provenance event model (`ORIGIN` → `INGESTION` → `VALIDATION`) once `DEC-03` reconciles MASTERDB's `MDUContractAdapter`.
