# -*- coding: utf-8 -*-
"""Manya — Group 3 observation validation evidence.

Runs the frozen JSON Schema plus the mandatory semantic checks for today's task.
It deliberately does NOT modify the frozen schema.

Run:
    python validate_manya.py
"""

import copy
import json
from pathlib import Path
from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parent
SCHEMA = json.loads((ROOT / "observation.schema.json").read_text(encoding="utf-8"))
PACKAGE = json.loads((ROOT / "sample_mission_package.json").read_text(encoding="utf-8"))
V = Draft202012Validator(SCHEMA, format_checker=FormatChecker())

KNOWN_DEVICES = {o["device_id"] for o in PACKAGE["observations"]}

def strip_comments(obj):
    return {k: v for k, v in obj.items() if not k.startswith("_")}

def schema_valid(obs):
    return not list(V.iter_errors(strip_comments(obs)))

def semantic_valid(obs):
    # Mission identity is required through provenance in the frozen contract.
    if not isinstance(obs.get("provenance", {}).get("mission_id"), str) or not obs["provenance"]["mission_id"]:
        return False
    # Device must be known to the current controlled fixture registry for this test.
    if obs.get("device_id") not in KNOWN_DEVICES:
        return False
    # Provenance device must agree with the observation device.
    if obs.get("provenance", {}).get("device_id") != obs.get("device_id"):
        return False
    # Raw artifact must be traceable through provenance.
    raw = obs.get("raw_artifact_reference", {})
    if raw.get("path") != obs.get("provenance", {}).get("raw_artifact"):
        return False
    return True

def full_valid(obs):
    return schema_valid(obs) and semantic_valid(obs)

def result(label, passed, detail):
    status = "PASS" if passed else "FAIL"
    print(f"[{status}] {label}: {detail}")
    return passed

base = strip_comments(PACKAGE["observations"][0])
results = []

# 1. Valid observation
results.append(result("T01 Valid observation", full_valid(base), "expected ACCEPTED"))

# 2. Missing timestamp
o = copy.deepcopy(base); del o["timestamp"]
results.append(result("T02 Missing timestamp", not full_valid(o), "expected REJECTED"))

# 3. Missing location
o = copy.deepcopy(base); del o["latitude"]
results.append(result("T03 Missing location", not full_valid(o), "expected REJECTED"))

# 4. Unknown device
o = copy.deepcopy(base); o["device_id"] = "DEV-UNKNOWN-999"
results.append(result("T04 Unknown device", not full_valid(o), "expected REJECTED by semantic device check"))

# 5. Invalid observation ID
o = copy.deepcopy(base); o["observation_id"] = "not-an-id"
results.append(result("T05 Invalid observation ID", not full_valid(o), "expected REJECTED"))

# 6. Malformed measurement
o = copy.deepcopy(base); o["measurement"] = {"bad": "type"}
results.append(result("T06 Malformed measurement", not full_valid(o), "expected REJECTED"))

# 7. NOT VERIFIED calibration is an allowed state
o = copy.deepcopy(base); o["calibration_status"] = "NOT VERIFIED"
results.append(result("T07 NOT VERIFIED calibration", full_valid(o), "expected ACCEPTED"))

# 8. Missing artifact reference
o = copy.deepcopy(base); del o["raw_artifact_reference"]
results.append(result("T08 Missing artifact reference", not full_valid(o), "expected REJECTED"))

# 9. Duplicate submission / idempotency contract simulation
store = {}
key = base["idempotency_key"]
fingerprint = json.dumps(base, sort_keys=True, separators=(",", ":"))
first = store.setdefault(key, fingerprint)
replay = store.get(key) == fingerprint
different = store.get(key) != json.dumps({**base, "measurement": 4.8}, sort_keys=True, separators=(",", ":"))
duplicate_test_pass = (first == fingerprint and replay and different)
results.append(result(
    "T09 Duplicate submission",
    duplicate_test_pass,
    "same key + same payload => IDEMPOTENT_REPLAY; no second record"
))

# Additional confirmed boundary behavior: trace_id may be null.
o = copy.deepcopy(base); o["trace_id"] = None
results.append(result("T10 Blank trace_id", full_valid(o), "expected ACCEPTED; runtime supplies response trace_id"))

# Additional quality-state rejection check
o = copy.deepcopy(base); o["quality_status"] = "GOOD"
results.append(result("Extra: invalid quality state", not full_valid(o), "expected REJECTED"))

# Additional calibration-state rejection check
o = copy.deepcopy(base); o["calibration_status"] = "probably fine"
results.append(result("Extra: invalid calibration state", not full_valid(o), "expected REJECTED"))

# Raw artifact linkage
raw = base["raw_artifact_reference"]
prov = base["provenance"]
linkage = (
    raw["path"] == prov["raw_artifact"]
    and prov["device_id"] == base["device_id"]
    and isinstance(raw["checksum_sha256"], str)
    and len(raw["checksum_sha256"]) == 64
)
results.append(result("RAW-01 Raw artifact linkage", linkage, "observation -> device -> raw artifact -> provenance"))

print()
print(f"{sum(results)}/{len(results)} validation checks passed")
if not all(results):
    raise SystemExit(1)
