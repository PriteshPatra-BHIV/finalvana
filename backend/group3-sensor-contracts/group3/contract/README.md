# Group 3 — Field Observation Contract V1.0

**Owner:** Group 3 — Field & Edge Systems · **Frozen:** 2026-08-13

**This is what Group 3 emits.** It is not a description of the canonical store — Group 1 owns that.

---

## Files

| File | Purpose |
|---|---|
| `observation.schema.json` | The 13-field contract as JSON Schema (draft 2020-12) |
| `sample_mission_package.json` | A synthetic mission — one numeric measurement, one image, one with no GNSS fix |
| `validate_fixtures.py` | Runs the samples plus 15 malformed cases. **18/18 passing** |

```bash
pip install jsonschema
python validate_fixtures.py
```

---

## The four rules the schema enforces

1. **Location and time are mandatory.** If no GNSS fix is obtained, `latitude`/`longitude` are `null`
   **and `quality_status` must be `UNCERTAIN`** — the schema enforces that pairing. **A coordinate is never
   invented.**
2. **`accuracy` and `calibration_status` reject `null` and free text.** The literal `NOT VERIFIED` is the
   honest value. As of freezing, no Group 3 sensor has a stated accuracy figure and no device holds a
   calibration record, so **every observation currently carries `NOT VERIFIED`**.
3. **A numeric measurement requires a unit.**
4. **Unknown fields are rejected** — `additionalProperties: false`.

**Acceptance criterion:** a malformed or incomplete field observation cannot silently become a valid
canonical record.

---

## Identity

Per the Group 3 Lead's Thane Creek mission plan:

```
Survey ID + Zone ID + Flight ID + Sensor ID + Observation ID + GPS coordinates + timestamp
example: TC-Z03-F02-IMX500-OBS001
```

**Identity is the whole tuple, including timestamp and coordinates.** Do not treat the `OBS###` fragment as
unique on its own — it repeats every flight.

---

## Alignment status

**Group 1 — canonical schema v0.1**

| Maps cleanly | No column in v0.1 | Partial |
|---|---|---|
| `observation_id` · numeric `measurement` · `unit` · mission grouping via `dataset` | `device_id` · `raw_artifact_reference` · `quality_status` · `accuracy` · `calibration_status` | `timestamp` (`observation_date` is `DATE`, so time-of-day is lost) · `latitude`/`longitude` (no per-observation coordinate) · `observation_type` (name collision — theirs means *what* was measured, ours *how* it was captured) |

**Group 1 consolidation pending.** A round-trip test against their real schema is in `../integration/` —
ingest, retrieve, re-submit, no duplicate, run both with and without the additive columns.

**Group 4 — conventions**

| Item | Status |
|---|---|
| `trace_id` | **PROVISIONAL** — `trace-vana-<16 hex>`, adopted from a live governed execution. No regex enforced until Group 4 confirms in writing. **Known limitation:** the trace is present in the API response and Bucket evidence but null in runtime/OTel logs, so end-to-end correlation is unproven |
| `idempotency_key` | Derived from `observation_id`; uses `replay.idempotency_key` from the TANTRA execution envelope |
| Device registration | Intended for the existing Capability Registry under `capability_type: "edge_robotics"` |

---

## What this contract does not claim

- **No Group 3 sensor has produced a recorded reading.** The sample package is a **synthetic fixture**.
- **No device holds a calibration record.**
- **Hardware deployment and real Thane Creek measurements are Phase 2.**

---

*Group 3 · VANA / Prakriti*
