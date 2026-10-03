# -*- coding: utf-8 -*-
"""The 14 mandatory tests from the Group 3 task of 2026-08-21, in one place.

WHY THIS FILE EXISTS
--------------------
The task lists 14 mandatory tests by name. They were spread across five suites,
and an audit on 2026-08-21 found two of them were NOT covered anywhere:

  - "Invalid unit rejected"          -> no test existed
  - "Coordinate mutation rejected or flagged" -> only OUT-OF-RANGE coordinates
    were tested. A silent substitution to a DIFFERENT VALID coordinate - which
    is the actual attack - was not covered.

This suite proves all 14 against the exact canonical observation
TC-Z03-F02-LIDAR-OBS001, so the task's requirements can be checked in one run
rather than inferred from five.

Tests 2 and 8 (Group 1 POST acceptance and duplicate-retry idempotency against
the live service) require the deployed host and are NOT run here - they are
covered by integration/live_acceptance_group1.py, which refuses to invent a
host. They are reported below as LIVE-REQUIRED rather than silently passed.

Run:  python test_task_2026_08_21_mandatory.py
"""
import copy, io, json, sys

from jsonschema import Draft202012Validator, FormatChecker

SCHEMA = json.load(io.open("observation.schema.v2.2.json", encoding="utf-8"))
PKG = json.load(io.open("sample_mission_package.v2.2.json", encoding="utf-8"))
VALIDATOR = Draft202012Validator(SCHEMA, format_checker=FormatChecker())

_ns = {}
exec(io.open("validate_semantic_v22.py", encoding="utf-8").read().split("res = []")[0], _ns)
semantic_errors, strip = _ns["semantic_errors"], _ns["strip"]

TARGET = "TC-Z03-F02-LIDAR-OBS001"
BASE = [o for o in PKG["observations"] if o["observation_id"] == TARGET][0]
results = []


def accepted(obs):
    if list(VALIDATOR.iter_errors(obs)):
        return False
    return not semantic_errors(strip(obs))


def check(num, label, mutate, expect_accept):
    obs = copy.deepcopy(BASE)
    if mutate:
        mutate(obs)
    got = accepted(obs)
    ok = got == expect_accept
    results.append(ok)
    print("  [%s] %-2s %-54s %s"
          % ("PASS" if ok else "FAIL", num, label, "ACCEPTED" if got else "REJECTED"))


print("GROUP 3 TASK 2026-08-21 - THE 14 MANDATORY TESTS")
print("target observation: %s" % TARGET)
print()

print("MANDATED FIELD VALUES")
for k, want in [("contract_version", "2.2"), ("synthetic_state", "CONTROLLED"),
                ("is_synthetic", True), ("calibration_state", "NOT_VERIFIED"),
                ("accuracy", "NOT_VERIFIED"), ("observation_id", TARGET)]:
    ok = BASE.get(k) == want
    results.append(ok)
    print("  [%s]    %-22s = %r" % ("PASS" if ok else "FAIL", k, BASE.get(k)))
print()

check("1", "valid exact observation accepted", None, True)
check("2", "missing provenance rejected", lambda o: o.pop("provenance"), False)
check("3", "malformed measurement rejected",
      lambda o: (o.__setitem__("measurement", {"bogus": 1}), o.__setitem__("unit", None)), False)

# --- test 4: invalid unit. NOT PREVIOUSLY COVERED.
print()
print("  test 4 - invalid unit (three forms, none previously covered)")
check("4a", "numeric measurement with unit null",
      lambda o: o.__setitem__("unit", None), False)
check("4b", "numeric measurement with empty-string unit",
      lambda o: o.__setitem__("unit", ""), False)
check("4c", "numeric measurement with whitespace-only unit",
      lambda o: o.__setitem__("unit", "   "), False)
print()

check("5", "identity mutation rejected (zone contradicts composite ID)",
      lambda o: o.__setitem__("zone_id", "Z07"), False)

# --- test 6: coordinate mutation. Only OUT-OF-RANGE was covered before.
print()
print("  test 6 - coordinate mutation (silent substitution, not out-of-range)")
# 6a/6b depend on Group 2's zone polygon. Without it a silently-substituted VALID
# coordinate cannot be detected by anything - the value is in range and internally
# consistent. If that artifact is absent these are reported UNAVAILABLE, exactly like
# the LIVE-REQUIRED tests, NOT counted as passes and NOT reported as failures.
#
# Added 2026-08-28 after the repository copy of this suite silently degraded: without
# reference/inbound/ the two checks FAILED into acceptance and a consumer would have
# received a weaker validator with no warning. A check that quietly stops checking is
# the same class of defect as one that crashes instead of rejecting.
_ZONE_OK = _ns.get("ZONE_POLYGON") is not None
if _ZONE_OK:
    check("6a", "latitude silently changed to another VALID value",
          lambda o: o["location"].__setitem__("latitude", 19.5000), False)
    check("6b", "longitude silently changed to another VALID value",
          lambda o: o["location"].__setitem__("longitude", 73.5000), False)
else:
    for _n in ("6a", "6b"):
        print("  [UNAVAILABLE] %-2s coordinate substitution - Group 2 zone polygon not present" % _n)
    print("       reference/inbound/G2_context_*.json is required to bind a coordinate.")
    print("       NOT counted as a pass. Restore the artifact to enable these two checks.")
check("6c", "coordinate out of WGS84 range",
      lambda o: o["location"].__setitem__("latitude", 91), False)
print()

check("7", "provenance mutation rejected (device disagrees)",
      lambda o: o["provenance"].__setitem__("device_id", "G3-CAM-999"), False)
check("9", "PHYSICAL without verified hardware rejected",
      lambda o: (o.__setitem__("synthetic_state", "PHYSICAL"),
                 o.__setitem__("is_synthetic", False)), False)
check("10", "PHYSICAL without real content hash rejected",
      lambda o: (o.__setitem__("synthetic_state", "PHYSICAL"),
                 o.__setitem__("is_synthetic", False),
                 o.__setitem__("hardware_verified", True),
                 o["raw_artifact_integrity"].__setitem__("checksum_sha256", None)), False)
check("11", "CALIBRATED without evidence rejected",
      lambda o: o.__setitem__("calibration_state", "CALIBRATED"), False)
check("12", "numeric accuracy without verified hardware rejected",
      lambda o: o.__setitem__("accuracy", 0.85), False)

# --- test 13: legacy identity may not silently replace the canonical one
print()
print("  test 13 - OBS-THANE-0001 cannot silently replace the canonical observation")
check("13a", "legacy id substituted wholesale",
      lambda o: o.__setitem__("observation_id", "OBS-THANE-0001"), False)
check("13b", "legacy id with components left pointing at the real observation",
      lambda o: (o.__setitem__("observation_id", "OBS-THANE-0001"),
                 o.__setitem__("idempotency_key", "OBS-THANE-0001")), False)

# --- test 14: V1.2 / V2.0 identity ambiguity must be DETECTED AND CLASSIFIED
print()
print("  test 14 - V1.2 / V2.0 identity ambiguity detected and formally classified")


def classify(obs):
    """Return the contract generation an observation claims, or AMBIGUOUS."""
    has_v22 = all(k in obs for k in ("synthetic_state", "data_state", "source_identity"))
    has_v12 = any(k in obs for k in ("timestamp", "quality_status", "calibration_status",
                                     "raw_artifact_reference"))
    declared = obs.get("contract_version")
    if has_v12 and has_v22:
        return "AMBIGUOUS"
    if has_v12:
        return "V1.2"
    if has_v22:
        return "V2.2" if declared == "2.2" else "AMBIGUOUS"
    return "UNKNOWN"


for label, mut, want in [
    ("clean V2.2 observation classifies as V2.2", None, "V2.2"),
    ("V1.2 field smuggled into a V2.2 payload -> AMBIGUOUS",
     lambda o: o.__setitem__("quality_status", "VALIDATED"), "AMBIGUOUS"),
    ("V2.2 shape declaring contract_version 2.0 -> AMBIGUOUS",
     lambda o: o.__setitem__("contract_version", "2.0"), "AMBIGUOUS"),
]:
    obs = copy.deepcopy(BASE)
    if mut:
        mut(obs)
    got = classify(obs)
    ok = got == want
    results.append(ok)
    print("  [%s] 14 %-54s %s" % ("PASS" if ok else "FAIL", label, got))
    # an ambiguous payload must ALSO be rejected outright, not merely labelled
    if want == "AMBIGUOUS":
        rej = not accepted(obs)
        results.append(rej)
        print("  [%s] 14 %-54s %s"
              % ("PASS" if rej else "FAIL", "   ...and rejected, not merely labelled",
                 "REJECTED" if rej else "ACCEPTED"))

print()
print("REQUIRES THE LIVE GROUP 1 SERVICE - not run here, not silently passed")
print("  [LIVE-REQUIRED]  2  Group 1 POST acceptance for the exact observation")
print("  [LIVE-REQUIRED]  8  duplicate retry is idempotent")
print("     both covered by integration/live_acceptance_group1.py, which refuses to")
print("     invent a host. Run it with --base-url once Group 1 has deployed V2.2.")

print()
print("=" * 78)
passed = sum(1 for r in results if r)
print("%d/%d offline mandatory checks passed" % (passed, len(results)))
print("2 of the 14 mandatory tests are LIVE-REQUIRED and are reported, not assumed.")
sys.exit(0 if passed == len(results) else 1)
