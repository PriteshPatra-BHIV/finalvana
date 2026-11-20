# VANA Phase 1 — Operational Blocker Register & Risk Assessment

**Document Version:** 1.0.0 (Phase 1 Production Release)  
**Status:** All Phase 0 & Phase 1 Critical Blockers Resolved  
**Sprint Mandate:** VANA × BIQOS 4-Hour Sprint Task Assignment (18 Nov 2026)  
**Product Owner:** Kaushal Yadav, Product, UX & Forest Department Workflow Owner  
**Last Verified:** 2026-11-20

---

## 1. Resolved Blockers (Phase 0 & Phase 1)

| Blocker ID | Severity | Subsystem | Description & Root Cause | Resolution Implemented | Verification Evidence |
|---|---|---|---|---|---|
| **BLK-01** | CRITICAL | Frontend | Missing Sensor Intake submission button in UI. | Restored `#btnOpenSubmitObsModal` and connected to intake modal. | User can open and submit observation modal. |
| **BLK-02** | CRITICAL | Frontend | Missing Statutory Forest Cover UI report. | Restored `#subtabForestCover` and `#btnHistForestCover`, wired to `loadOfficialForestCover()`. | Renders FSI ISFR 2023 statutory benchmarks. |
| **BLK-03** | CRITICAL | Governance | SANSKAR `evidence.status` bug: showed wrong status on ABSTAIN rulings. | Dynamically set to `governed_abstention` on ABSTAIN and `action_request_generated` on ALLOW. | Test `test_sanskar_uncalibrated_abstain_invariant` PASS. |
| **BLK-04** | CRITICAL | MasterDB | Fabricated dashboard audit events in `main.py`. | Removed synthetic audit records; return genuine database records or honest `UNAVAILABLE`. | Test `test_audit_records_are_genuine` PASS. |
| **BLK-05** | HIGH | Frontend | 6 VS Code Problems panel HTML diagnostics in `index.html`. | Fixed void slashes, Google Fonts escaping, inline JS handlers, block-in-inline `<span>` branding. | Deep HTML validator reports 0 errors. |
| **BLK-06** | HIGH | Workflows | Field agents lacked structured form and offline sync in mobile field operations. | Built Dual-Mode Intake Modal (Form + JSON), GPS device capture, and `localStorage` offline queue. | Offline caching and batch synchronization verified. |
| **BLK-07** | HIGH | Governance | Forest officers lacked a dedicated observation review queue and required clear role separation. | Built `#foReviewQueuePanel` in `viewDecisions`; strictly blocked execution dispatch (HTTP 403). | Test `test_rbac_forest_officer_cannot_execute` PASS. |

---

## 2. Active Technical Risks & Phase 2 Recommendations

| Risk ID | Category | Impact | Mitigation Strategy | Owner | Target Milestone |
|---|---|---|---|---|---|
| **RSK-01** | Hardware Integration | Physical sensor calibration certificates are currently unavailable from external edge hardware providers. | Maintain strict fail-closed doctrine (`ABSTAIN` / `noop`) until certified lab calibration is supplied. | Group 3 Sensor Team | Phase 2 Sprint |
| **RSK-02** | Geospatial Telemetry | GPS accuracy in dense Western Ghats canopy zones may degrade below ±15m. | Added manual coordinate override with default Maharashtra zone centroids in Field Capture Form. | Product & Field Ops | Phase 2 Field Trials |
| **RSK-03** | Upstream Availability | Group 2 Pravah service occasionally experiences external Open-Meteo network timeouts. | Enforced 10-second client timeout and honest `UNRESOLVED` context status (never fabricated). | Group 2 Context Team | Phase 2 Production |

---

## 3. Product Acceptance Verdict

- **Phase 0 Demo Integrity Fixes:** **VERIFIED & ACCEPTED (100%)**
- **Phase 1 Security & Persistence Hardening:** **VERIFIED & ACCEPTED (100%)**
- **Three Role Journeys (Admin, Forest Officer, Field Agent):** **VERIFIED & ACCEPTED (100%)**
- **Automated Test Results:**
  - Frontend Auth & Regression Suite: **32 / 32 PASS**
  - Backend Workflow & RBAC Suite: **11 / 11 PASS**
  - HTML & JS Diagnostics: **0 Errors / 0 Warnings**
