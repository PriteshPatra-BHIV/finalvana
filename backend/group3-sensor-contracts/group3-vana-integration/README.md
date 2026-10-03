# Group 3 — VANA Sensor Intake & Integration

The Group 3 contract, validators, intake adapter definition and runtime evidence for the VANA /
Prakriti mangrove-monitoring system.

**Owner:** Hemanth Reddy · **Contract owner:** Arya Barge · **Contract:** V2.2 FROZEN

---

## What this is

Group 3 produces **canonical observations** and emits them into the VANA runtime:

```
SOURCE → GROUP 3 INTAKE → GROUP 1 CANONICAL RECORD → GROUP 2 RULING → GROUP 4 GOVERNANCE → UI
```

One observation has travelled that chain live: `TC-Z03-EXT-OPENMETEO-OBS001`, accepted by Group 1 on
2026-08-25 with 13/13 checks, canonical record `CR-b4615a27-7ab1-4bde-a078-a56fa0f2414c`.

## Layout

| Path | Contents |
|---|---|
| `contract/` | The frozen V2.2 schema, fixtures, and six validation suites |
| `integration/` | Generators that emit the interface artifacts from the contract |
| `evidence/` | Captured runtime evidence — acceptance run, source provenance, emitted payload |
| `docs/` | Runtime integration report and the open gaps register |
| `*.json` at root | Generated interface artifacts |

## Running the validation

```bash
cd contract
python validate_fixtures.py              # 30  structural
python validate_semantic.py              # 12  V1.2 semantic
python validate_semantic_v2.py           # 13  V2.1 semantic
python validate_semantic_v22.py          # 35  V2.2 semantic, cross-field
python audit_v22_adversarial.py          # 49  adversarial, both layers
python test_task_2026_08_21_mandatory.py # 28  mandatory task checks
```

**165 assertions in this repository, all green** — 30 + 12 + 13 + 35 + 49 + 26.

Two notes on the count, both deliberate:

- The full Group 3 workspace runs **226**. The extra 61 are three integration suites that need runtime
  evidence files not republished here.
- Tests `6a`/`6b` report **`UNAVAILABLE`**, not pass. They bind a coordinate against Group 2's zone
  polygon — their artifact, not ours to republish. Without it a silently-substituted *valid* coordinate
  cannot be detected by anything. The suite says so rather than counting them green.

Requires `jsonschema`.

## Regenerating the interface artifacts

```bash
cd integration
python emit_intake_adapter_contract.py   # the reusable intake contract
python emit_sensor_d1_d5.py              # D1-D5 sensor mapping
python emit_sensor_interface_map.py      # Workstream 6 boundary map
python emit_persistence_matrix.py        # all 37 fields vs Group 1 behaviour
python emit_region_coverage.py --probe   # region coverage, live probe
```

These read the frozen schema and **fail rather than emit** if they reference a field that does not
exist in it.

## The honesty rules this repository follows

Every claim carries a verification label: `VERIFIED` (ran it, hold the output) · `REPORTED` (a named
person said so, no artifact held) · `GAP` (genuinely absent, with the reason).

**What is NOT proven, stated plainly:** no Group 3 sensor has produced a recorded reading. Zero physical
observations exist. The live observation is real third-party weather data carried through the controlled
Group 3 path — `synthetic_state: CONTROLLED`, `is_synthetic: true`, `hardware_verified: false`.

`TC-Z03-F02-LIDAR-OBS001` exists in the canonical store and is **not** evidence of LiDAR hardware. It is
a legacy synthetic test record.

Open gaps are in `docs/KNOWN_GAPS.md` — 52 entries, append-only, each with a named owner.

## Attribution

Weather data by [Open-Meteo.com](https://open-meteo.com/) (CC-BY 4.0), aggregating national weather
services. This attribution is a licence obligation and must survive every downstream handoff.

## Note on runtime hosts

No service host or credential appears anywhere in this repository. The Group 1 API is supplied at run
time via `--base-url` or `VANA_API_BASE_URL`.
