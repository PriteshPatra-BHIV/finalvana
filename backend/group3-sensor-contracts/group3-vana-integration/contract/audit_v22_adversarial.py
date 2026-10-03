# -*- coding: utf-8 -*-
"""V2.2 adversarial audit — schema layer + semantic layer, together.

WHY THIS FILE EXISTS
--------------------
validate_fixtures.py tests shape. validate_semantic_v22.py tests cross-field
agreement. Neither tests the two layers COMBINED, which is what a real consumer
runs — and defects have repeatedly hidden in the gap between them.

Every case here is traced to the rule it protects. The rules come from Arya
Barge's Observation Metadata Contract (FROZEN), her Decision Record, her
Controlled Observation Fixtures, and her contract rulings of 2026-08-20.

Three rounds of audit found eleven defects in V2.2. Each has a case below so it
cannot silently return:

  round 1  numeric measurement with no unit; contradictory data/quality state;
           one-directional synthetic mapping; producer-settable ingestion
           timestamp; source_timestamp after the observation
  round 2  measurement and tidal_state declared as bare union types, losing the
           inner structure V2.1 had
  round 3  accuracy and processing_status dropped from a frozen mandatory list;
           provenance requiring 2 of 4 fields; nullable artifact_type;
           non-UTC offsets accepted; timestamps compared as STRINGS

Run:  python audit_v22_adversarial.py
"""
import copy, io, json, sys

from jsonschema import Draft202012Validator, FormatChecker

SCHEMA = json.load(io.open("observation.schema.v2.2.json", encoding="utf-8"))
PKG = json.load(io.open("sample_mission_package.v2.2.json", encoding="utf-8"))

Draft202012Validator.check_schema(SCHEMA)
VALIDATOR = Draft202012Validator(SCHEMA, format_checker=FormatChecker())

# reuse the semantic layer rather than reimplementing it
_ns = {}
exec(io.open("validate_semantic_v22.py", encoding="utf-8").read().split("res = []")[0], _ns)
semantic_errors, strip = _ns["semantic_errors"], _ns["strip"]

BASE = PKG["observations"][0]
results = []


def accepted(obs):
    """True only if BOTH layers accept — what a real consumer actually sees."""
    if list(VALIDATOR.iter_errors(obs)):
        return False
    return not semantic_errors(strip(obs))


def case(label, mutate, expect_accept, rule):
    obs = copy.deepcopy(BASE)
    mutate(obs)
    got = accepted(obs)
    ok = got == expect_accept
    results.append(ok)
    print("  [%s] %-52s %-8s  %s"
          % ("PASS" if ok else "FAIL", label,
             "ACCEPTED" if got else "REJECTED", rule))
    return ok


print("V2.2 ADVERSARIAL AUDIT - schema and semantic layers combined")
print("draft 2020-12 meta-schema: VALID")
print()
print("EVERY OBSERVATION IN THE SHIPPED MISSION PACKAGE - both layers")
for _o in PKG["observations"]:
    _clean = {k: v for k, v in _o.items() if not k.startswith("_")}
    _ok = accepted(_clean)
    results.append(_ok)
    print("  [%s] %-52s %-8s  %s"
          % ("PASS" if _ok else "FAIL", _o["observation_id"],
             "ACCEPTED" if _ok else "REJECTED",
             "numeric" if isinstance(_o.get("measurement"), (int, float))
             else ("no GNSS fix" if (_o.get("location") if isinstance(_o.get("location"), dict) else {}).get("latitude") is None
                   else "descriptive")))

print()
print("MANDATORY FIELDS MAY NOT BE DROPPED  [metadata contract s4, s18]")
case("accuracy omitted", lambda o: o.pop("accuracy"), False, "s4 mandatory")
case("accuracy null", lambda o: o.__setitem__("accuracy", None), False, "s9")
case("accuracy 'NOT VERIFIED' with a space",
     lambda o: o.__setitem__("accuracy", "NOT VERIFIED"), False, "ruling 2026-08-20")
case("processing_status omitted", lambda o: o.pop("processing_status"), False, "s4 mandatory")
case("processing_status empty", lambda o: o.__setitem__("processing_status", ""), False, "s4")
case("unknown top-level field", lambda o: o.__setitem__("bogus", 1), False, "closed contract")

print()
print("NOTHING MAY BE INVENTED  [fixtures rules 4-7, metadata contract s9, s10, s14]")
case("accuracy asserted without verified hardware",
     lambda o: o.__setitem__("accuracy", 0.85), False, "fixtures 4, 6")
case("GPS accuracy asserted without hardware",
     lambda o: o["location"].__setitem__("position_accuracy_m", 1.5), False, "fixtures 4")
case("CALIBRATED claimed without evidence",
     lambda o: o.__setitem__("calibration_state", "CALIBRATED"), False, "s10, fixtures 5, 7")
case("tidal state asserted with no source",
     lambda o: o.__setitem__("tidal_state", {"state": "HIGH", "source": None}), False, "s14")
case("tidal state with a named source",
     lambda o: o.__setitem__("tidal_state", {"state": "HIGH", "source": "INCOIS tide table"}),
     True, "s14")

print()
print("PROVENANCE MUST BE COMPLETE AND CONSISTENT  [metadata contract s13]")
case("provenance without captured_at", lambda o: o["provenance"].pop("captured_at"), False, "s13")
case("provenance without raw_artifact", lambda o: o["provenance"].pop("raw_artifact"), False, "s13")
case("provenance device disagrees",
     lambda o: o["provenance"].__setitem__("device_id", "G3-CAM-999"), False, "s13")
case("provenance mission disagrees",
     lambda o: o["provenance"].__setitem__("mission_id", "OTHER"), False, "s13")
case("provenance_reference empty",
     lambda o: o.__setitem__("provenance_reference", "   "), False, "ruling 2026-08-20")
case("raw_artifact_integrity omitted", lambda o: o.pop("raw_artifact_integrity"), False, "s11")
case("artifact_type null - artifact of unknown kind",
     lambda o: o["raw_artifact_integrity"].__setitem__("artifact_type", None), False, "s11")
case("artifact_type outside the vocabulary",
     lambda o: o["raw_artifact_integrity"].__setitem__("artifact_type", "zipfile"), False, "s11")

print()
print("TIME IS UTC, AND COMPARED AS INSTANTS  [metadata contract s6]")
case("non-UTC offset +05:30",
     lambda o: o.__setitem__("observation_timestamp", "2026-08-13T14:44:22+05:30"), False, "s6")
case("naive timestamp, no zone",
     lambda o: o.__setitem__("observation_timestamp", "2026-08-13T09:14:22"), False, "s6")
case("impossible date 2026-02-30",
     lambda o: (o.__setitem__("observation_timestamp", "2026-02-30T10:00:00Z"),
                o["provenance"].__setitem__("captured_at", "2026-02-30T10:00:00Z")), False, "s6")
case("UTC as +00:00 - a legal spelling",
     lambda o: (o.__setitem__("observation_timestamp", "2026-08-13T09:14:22+00:00"),
                o["provenance"].__setitem__("captured_at", "2026-08-13T09:14:22+00:00")), True, "s6")
case("fractional seconds - explicitly permitted",
     lambda o: (o.__setitem__("observation_timestamp", "2026-08-13T09:14:22.172677Z"),
                o["provenance"].__setitem__("captured_at", "2026-08-13T09:14:22.172677Z")), True, "s6")
case("source_timestamp after the observation",
     lambda o: o.__setitem__("source_timestamp", "2027-01-01T00:00:00Z"), False, "causality")
case("captured_at a genuinely different instant",
     lambda o: o["provenance"].__setitem__("captured_at", "2026-08-13T09:14:23Z"), False, "s13")
case("ingestion_timestamp set by the producer",
     lambda o: o.__setitem__("ingestion_timestamp", "2026-08-19T11:38:00Z"), False, "runtime-owned")

print()
print("MEASUREMENT AND LOCATION STRUCTURE  [metadata contract s7, s8]")
case("bare numeric measurement, no unit",
     lambda o: (o.__setitem__("measurement", 4.7), o.__setitem__("unit", None)), False, "s8")
case("object measurement, numeric value, no unit",
     lambda o: (o.__setitem__("measurement", {"value": 4.7}), o.__setitem__("unit", None)),
     False, "s8")
case("empty descriptive measurement",
     lambda o: (o.__setitem__("measurement", ""), o.__setitem__("unit", None)), False, "s8")
case("latitude 91 - outside WGS84", lambda o: o["location"].__setitem__("latitude", 91), False, "s7")
case("longitude -181 - outside WGS84",
     lambda o: o["location"].__setitem__("longitude", -181), False, "s7")

print()
print("SYNTHETIC STATE MAY NOT BE LAUNDERED  [canonical observation contract s4]")
case("SYNTHETIC relabelled is_synthetic false",
     lambda o: o.__setitem__("is_synthetic", False), False, "compatibility table")
case("PHYSICAL claimed with is_synthetic true",
     lambda o: (o.__setitem__("synthetic_state", "PHYSICAL"),
                o.__setitem__("hardware_verified", True),
                o.__setitem__("is_synthetic", True)), False, "compatibility table")
case("PHYSICAL claimed without verified hardware",
     lambda o: (o.__setitem__("synthetic_state", "PHYSICAL"),
                o.__setitem__("is_synthetic", False)), False, "physical boundary")
case("quality_state INGESTED with data_state CAPTURED",
     lambda o: o.__setitem__("quality_state", "INGESTED"), False, "ruling 2026-08-22")
case("data_state VALIDATED - no longer a legal lifecycle value",
     lambda o: o.__setitem__("data_state", "VALIDATED"), False, "ruling 2026-08-22")
case("data_state UNCERTAIN - no longer a legal lifecycle value",
     lambda o: o.__setitem__("data_state", "UNCERTAIN"), False, "ruling 2026-08-22")
case("identity contradicts its own components",
     lambda o: o.__setitem__("zone_id", "Z07"), False, "metadata contract s3")
case("idempotency key not derived from identity",
     lambda o: o.__setitem__("idempotency_key", "some-random-uuid"), False, "s16")

print()
# ---------------------------------------------------------------------------
# REGRESSION, added 2026-08-28. Dhruv Patel's negative suite found that a
# malformed nested field CRASHED the semantic validator instead of rejecting the
# payload: `o.get("location") or {}` guards None but not a WRONG TYPE, and a
# bare-string location is truthy, so .get() raised AttributeError.
#
# In a fail-closed system a crash is NOT a rejection. A caller cannot tell
# "malformed payload" from "validator broken", and a stack trace is not an
# acceptance decision. These cases assert that a wrong-typed nested field is
# REJECTED CLEANLY by the structural layer, never raised.
# ---------------------------------------------------------------------------
print()
print("MALFORMED NESTED FIELDS MUST REJECT, NOT CRASH  [regression, Dhruv 2026-08-28]")
for _fld, _bad, _label in [
        ("location", "19.1288,72.9421", "location as a bare string"),
        ("location", 19.1288, "location as a number"),
        ("location", ["19.1288", "72.9421"], "location as a list"),
        ("provenance", "device G3-X", "provenance as a bare string"),
        ("raw_artifact_integrity", "sha256:abc", "integrity as a bare string"),
        ("measurement", ["0.1"], "measurement as a list")]:
    def _mut(o, _f=_fld, _b=_bad):
        o[_f] = _b
    case(_label, _mut, False, "wrong type must reject cleanly, never raise")

print("=" * 78)
passed = sum(1 for r in results if r)
print("%d/%d adversarial cases passed" % (passed, len(results)))
sys.exit(0 if passed == len(results) else 1)
