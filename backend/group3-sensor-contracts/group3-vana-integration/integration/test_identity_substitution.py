# -*- coding: utf-8 -*-
"""IDENTITY SUBSTITUTION TEST — required by today's task, section HEMANTH / Critical Test.

    "Create an identity-substitution test:
         Group 3 observation -> attempted ID or coordinate replacement
                             -> detection -> REJECT / FLAG"

WHY THIS IS DIFFERENT FROM THE OTHER SUITES
-------------------------------------------
validate_fixtures.py     proves a MALFORMED record is rejected.
validate_semantic.py     proves an INTERNALLY CONTRADICTORY record is rejected.
test_identity_survival.py proves the identity SURVIVES the honest path.

None of them prove the adversarial case: a record that is perfectly well-formed
AND internally consistent, but is NOT THE OBSERVATION IT CLAIMS TO BE. That is
the substitution attack, and it is what this file tests.

Threat model, taken from today's task "Out of scope" list:
    identity replacement - coordinate modification - silent schema migration
    provenance loss - synthetic substitution disguised as live observation

Run:  python test_identity_substitution.py
"""
import copy, io, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
DAY6 = os.path.dirname(HERE)
CONTRACT = os.path.join(DAY6, "contract")
sys.path.insert(0, CONTRACT)
from jsonschema import Draft202012Validator, FormatChecker  # noqa: E402

SCHEMA = json.load(io.open(os.path.join(CONTRACT, "observation.schema.json"), encoding="utf-8"))
PKG = json.load(io.open(os.path.join(CONTRACT, "sample_mission_package.json"), encoding="utf-8"))
V = Draft202012Validator(SCHEMA, format_checker=FormatChecker())

CANONICAL_ID = "TC-Z03-F02-LIDAR-OBS001"


def strip(o):
    return {k: v for k, v in o.items() if not k.startswith("_")}


BASE = strip([o for o in PKG["observations"]
              if o.get("observation_id") == CANONICAL_ID][0])

# The attested baseline. In production this is the value Group 1 already holds.
ATTESTED = {
    "observation_id": BASE["observation_id"],
    "device_id": BASE["device_id"],
    "timestamp": BASE["timestamp"],
    "latitude": BASE["latitude"],
    "longitude": BASE["longitude"],
    "measurement": BASE["measurement"],
    "unit": BASE.get("unit"),
    "raw_artifact": BASE["raw_artifact_reference"]["path"],
    "raw_sha256": BASE["raw_artifact_reference"].get("checksum_sha256"),
    "provenance_device": BASE["provenance"]["device_id"],
    "provenance_artifact": BASE["provenance"]["raw_artifact"],
}


def detect_substitution(c, a=ATTESTED):
    """Compare a candidate against the attested baseline for the SAME id."""
    d = []
    if c.get("observation_id") != a["observation_id"]:
        d.append("IDENTITY REPLACED: %r is not %r"
                 % (c.get("observation_id"), a["observation_id"]))
        return d

    for f in ("device_id", "timestamp", "latitude", "longitude", "measurement", "unit"):
        if c.get(f) != a[f]:
            d.append("%s MUTATED: %r -> %r" % (f.upper(), a[f], c.get(f)))

    raw = c.get("raw_artifact_reference") or {}
    if raw.get("path") != a["raw_artifact"]:
        d.append("RAW ARTIFACT SWAPPED: %r -> %r" % (a["raw_artifact"], raw.get("path")))
    if a["raw_sha256"] and raw.get("checksum_sha256") != a["raw_sha256"]:
        d.append("CONTENT HASH CHANGED - the evidence file is not the same file")

    prov = c.get("provenance") or {}
    if prov.get("device_id") != a["provenance_device"]:
        d.append("PROVENANCE DEVICE REWRITTEN: %r -> %r"
                 % (a["provenance_device"], prov.get("device_id")))
    if prov.get("raw_artifact") != a["provenance_artifact"]:
        d.append("PROVENANCE ARTIFACT REWRITTEN")
    return d


res = []


def case(label, mutate, expect_detect, note=""):
    o = copy.deepcopy(BASE)
    mutate(o)
    schema_ok = not list(V.iter_errors(o))
    div = detect_substitution(o)
    detected = bool(div)
    ok = (detected == expect_detect)
    print("  [%s] %-44s %s" % ("PASS" if ok else "FAIL", label,
                               "FLAGGED" if detected else "passed silently"))
    print("         schema alone: %s%s"
          % ("ACCEPTS it" if schema_ok else "rejects it",
             ("   <- " + note) if note else ""))
    for x in div[:2]:
        print("         ! %s" % x[:100])
    res.append(ok)


print("IDENTITY SUBSTITUTION TEST")
print("canonical observation: %s" % CANONICAL_ID)
print()
print("Every case below is a WELL-FORMED record. The question is not")
print("'is it valid' but 'is it the observation it claims to be'.")
print()

print("[A] CONTROL")
case("unmodified genuine observation", lambda o: None, False)

print()
print("[B] IDENTITY REPLACEMENT")
case("observation_id swapped for another real one",
     lambda o: o.__setitem__("observation_id", "TC-Z03-F02-IMX500-OBS002"), True,
     "both IDs are contract-valid")
case("observation_id swapped for the V2.0 flat form",
     lambda o: o.__setitem__("observation_id", "OBS-THANE-0001"), True,
     "schema rejects this format too")

print()
print("[C] COORDINATE MODIFICATION")
case("latitude nudged 0.0001 deg (about 11 m)",
     lambda o: o.__setitem__("latitude", 19.1289), True, "in range, schema-valid")
case("coordinates moved to a different zone",
     lambda o: (o.__setitem__("latitude", 19.0330),
                o.__setitem__("longitude", 72.9200)), True, "in range, schema-valid")

print()
print("[D] MEASUREMENT SUBSTITUTION")
case("canopy height 4.7 -> 9.9 m",
     lambda o: o.__setitem__("measurement", 9.9), True,
     "schema-valid; this IS the ecological claim")
case("unit m -> ft, value unchanged",
     lambda o: o.__setitem__("unit", "ft"), True,
     "schema-valid; silently changes the meaning")

print()
print("[E] EVIDENCE SWAP")
case("raw artifact path repointed",
     lambda o: o["raw_artifact_reference"].__setitem__(
         "path", "TC-Z03-F02/drone/pointcloud_F02_999.las"), True)
case("same path, different content hash",
     lambda o: o["raw_artifact_reference"].__setitem__(
         "checksum_sha256", "b" * 64), True,
     "the file behind the observation was replaced")

print()
print("[F] PROVENANCE REWRITE")
case("provenance device reattributed",
     lambda o: o["provenance"].__setitem__("device_id", "G3-CAM-001"), True)
case("provenance artifact repointed",
     lambda o: o["provenance"].__setitem__("raw_artifact", "other.las"), True)

print()
print("[G] TIMESTAMP DRIFT")
case("captured 1 hour later",
     lambda o: o.__setitem__("timestamp", "2026-08-13T10:14:22Z"), True,
     "schema-valid ISO-8601")

print()
print("[H] SYNTHETIC SUBSTITUTION - the one that matters most")
flag = PKG.get("is_synthetic")
ok = (flag is True)
print("  [%s] %-44s is_synthetic=%s"
      % ("PASS" if ok else "FAIL", "fixture is marked synthetic at source", flag))
print("         A record identical in every field but claiming is_synthetic=false")
print("         is a DIFFERENT CLAIM ABOUT THE PHYSICAL WORLD, not a different")
print("         value. No Group 3 sensor has produced a recorded reading.")
res.append(ok)

print()
print("=" * 74)
print("RESULT: %d/%d checks passed" % (sum(1 for r in res if r), len(res)))
print()
print("WHAT THIS PROVES: an attempted identity, coordinate, measurement, evidence")
print("or provenance substitution is DETECTED and can be REJECTED or FLAGGED,")
print("even when the substituted record is perfectly schema-valid.")
print()
print("HOW: comparison against an ATTESTED BASELINE for the same observation_id.")
print("Schema validation alone cannot do this - a mutated record is still a valid")
print("record. Detection requires knowing what the observation was BEFORE.")
print()
print("LIMITATION, stated: the baseline here comes from the frozen fixture. In")
print("production it must come from Group 1's canonical record, which requires")
print("their deployed instance. Not available today (no host issued), so this is")
print("a CONTROLLED proof of the mechanism, not a live tamper-detection service.")
sys.exit(0 if all(res) else 1)
