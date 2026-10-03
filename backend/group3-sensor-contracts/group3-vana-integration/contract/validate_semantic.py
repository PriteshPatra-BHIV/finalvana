# -*- coding: utf-8 -*-
"""Semantic / referential validation — the layer JSON Schema cannot provide.

ORIGIN
------
Manya Shukla (Group 3, Observation & Data Quality) identified on 2026-08-17 that
"semantic/referential failures a basic JSON Schema check may not catch" were
untested, then implemented four of them in `validate_manya.py`. Those four
checks are reproduced and extended here so they run as part of the contract's
own test suite rather than only in her working folder.

Credit: checks 2-5 below are Manya's design.

WHY A SEPARATE FILE
-------------------
JSON Schema validates SHAPE. It cannot validate AGREEMENT between fields, and it
cannot validate references against a registry. An observation can be perfectly
schema-valid while claiming device G3-LIDAR-001 in one field and G3-CAM-001 in
another - the record is then internally contradictory and its provenance is
worthless. That class of bug is invisible to `validate_fixtures.py`.

The frozen schema is deliberately NOT modified to accommodate these - Manya's
own decision, and the right one. Shape and agreement are different concerns.

Run:  python validate_semantic.py
"""
import copy, io, json, sys

SCHEMA = json.load(io.open("observation.schema.json", encoding="utf-8"))
PKG = json.load(io.open("sample_mission_package.json", encoding="utf-8"))


# TYPE-SAFE ACCESS. `x.get("k") or {}` only guards None/falsy; a WRONG TYPE is truthy
# and then .get() raises AttributeError - a crash, not a rejection. Found by Dhruv
# Patel's negative suite 2026-08-28 (bare-string location). Same fix as V2.2.
def _obj(v):
    return v if isinstance(v, dict) else {}


def strip(o):
    return {k: v for k, v in o.items() if not k.startswith("_")}


# The device register does not exist yet (Shivam confirmed there is no Capability
# Registry API and no device-registration payload). Until it does, the fixture's
# own device set is the only registry available. This is a STAND-IN, and it is
# labelled as one rather than presented as referential integrity.
KNOWN_DEVICES = {o["device_id"] for o in PKG["observations"] if "device_id" in o}


def semantic_errors(obs):
    """Return a list of agreement/reference failures. Empty list = passes."""
    errs = []
    prov = _obj(obs.get("provenance"))
    raw = _obj(obs.get("raw_artifact_reference"))

    # 1. mission identity must be present, and present through provenance
    if not isinstance(prov.get("mission_id"), str) or not prov.get("mission_id", "").strip():
        errs.append("provenance.mission_id missing or empty")

    # 2. device must be known to the register  [Manya]
    if obs.get("device_id") not in KNOWN_DEVICES:
        errs.append("device_id %r not in the device register (stand-in: fixture device set)"
                    % obs.get("device_id"))

    # 3. provenance device must agree with the observation device  [Manya]
    if prov.get("device_id") != obs.get("device_id"):
        errs.append("provenance.device_id %r disagrees with device_id %r"
                    % (prov.get("device_id"), obs.get("device_id")))

    # 4. raw artifact must be traceable through provenance  [Manya]
    if raw.get("path") != prov.get("raw_artifact"):
        errs.append("raw_artifact_reference.path %r disagrees with provenance.raw_artifact %r"
                    % (raw.get("path"), prov.get("raw_artifact")))

    # 5. capture time must agree between the observation and its provenance
    if prov.get("captured_at") and obs.get("timestamp") \
            and prov["captured_at"] != obs["timestamp"]:
        errs.append("provenance.captured_at %r disagrees with timestamp %r"
                    % (prov.get("captured_at"), obs.get("timestamp")))

    # 6. the composite ID must agree with its own component fields.
    #    Group 3 submits survey/zone/flight/sensor/seq separately (Raj's API
    #    accepts them), so the two representations must not contradict.
    oid = obs.get("observation_id") or ""
    parts = oid.split("-")
    if len(parts) >= 5:
        want = {"survey_id": parts[0], "zone_id": parts[1],
                "flight_id": parts[2], "sensor_id": parts[3],
                "observation_seq": parts[4]}
        for f, expected in want.items():
            if f in obs and obs[f] != expected:
                errs.append("%s %r contradicts observation_id component %r"
                            % (f, obs[f], expected))

    # 7. a null position must be paired with UNCERTAIN. The schema enforces this
    #    too; repeated here because it is the rule most costly to lose.
    if (obs.get("latitude") is None or obs.get("longitude") is None) \
            and obs.get("quality_status") != "UNCERTAIN":
        errs.append("null coordinate without quality_status UNCERTAIN")

    return errs


def check(label, obs, expect_pass):
    errs = semantic_errors(strip(obs))
    ok = (not errs) == expect_pass
    print("  [%s] %-52s expect %-6s got %s"
          % ("PASS" if ok else "FAIL", label,
             "accept" if expect_pass else "REJECT",
             "accepted" if not errs else "rejected"))
    if errs and expect_pass:
        for e in errs[:2]:
            print("         ! %s" % e[:100])
    if not errs and not expect_pass:
        print("         ! a contradictory record was accepted")
    return ok


print("SEMANTIC / REFERENTIAL VALIDATION")
print("checks the AGREEMENT between fields, which JSON Schema cannot")
print()
print("VALID OBSERVATIONS FROM THE MISSION PACKAGE")
res = []
for o in PKG["observations"]:
    res.append(check(o["observation_id"], o, True))

print()
print("CONTRADICTORY RECORDS - must be rejected")
base = strip(PKG["observations"][0])

o = copy.deepcopy(base); o["device_id"] = "DEV-UNKNOWN-999"
res.append(check("device not in register", o, False))

o = copy.deepcopy(base); o["provenance"]["device_id"] = "G3-CAM-001"
res.append(check("provenance device disagrees with device_id", o, False))

o = copy.deepcopy(base); o["provenance"]["raw_artifact"] = "TC-Z03-F02/drone/other.las"
res.append(check("provenance artifact disagrees with reference", o, False))

o = copy.deepcopy(base); o["provenance"]["captured_at"] = "2026-08-13T11:00:00Z"
res.append(check("provenance captured_at disagrees with timestamp", o, False))

o = copy.deepcopy(base); o["provenance"]["mission_id"] = ""
res.append(check("empty provenance mission_id", o, False))

o = copy.deepcopy(base); del o["provenance"]["mission_id"]
res.append(check("missing provenance mission_id", o, False))

o = copy.deepcopy(base); o["zone_id"] = "Z07"
res.append(check("zone_id contradicts the composite ID", o, False))

o = copy.deepcopy(base); o["sensor_id"] = "IMX500"
res.append(check("sensor_id contradicts the composite ID", o, False))

o = copy.deepcopy(base); o["latitude"] = None
res.append(check("null latitude without UNCERTAIN", o, False))

print()
print("%d/%d semantic checks passed" % (sum(1 for r in res if r), len(res)))
print()
print("An observation can be schema-valid and still internally contradictory.")
print("This layer is what stops a record whose provenance points somewhere else.")
print()
print("KNOWN LIMITATION: the device register does not exist yet - Shivam confirmed")
print("there is no Capability Registry API and no device-registration payload. The")
print("fixture's own device set is a STAND-IN. Real referential integrity needs")
print("Ashmit's register, and is tracked as a dependency rather than assumed.")
sys.exit(0 if all(res) else 1)
