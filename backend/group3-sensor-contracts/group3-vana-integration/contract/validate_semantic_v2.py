# -*- coding: utf-8 -*-
"""V2.0 semantic / referential validation — agreement checks JSON Schema cannot express.

Carries the V1.x semantic layer forward onto the V2.0 shape, plus one new guard
that V1.x did not need.

THE NEW GUARD: is_synthetic
---------------------------
Suraj's Closure Plan section 4 states:

    "For the first software integration test is_synthetic = true.
     For the actual drone capture is_synthetic = false.
     The two must never be confused."

His example template carries FALSE. As of 2026-08-17 no Group 3 sensor has
produced a recorded reading and 0 of 8 quadruped actuators are mounted, so any
observation existing today must carry TRUE. A template that defaults to FALSE is
the exact route by which a synthetic record gets published as real, so this
layer refuses is_synthetic=false unless the record also carries hardware
evidence - a real content hash and hardware_verified=true.

That is not pedantry. It is the one failure mode that would invalidate every
other claim Group 3 has made.

Origin of checks 2-5: Manya Shukla (Group 3, Observation & Data Quality).

Run:  python validate_semantic_v2.py
"""
import copy, io, json, sys

SCHEMA = json.load(io.open("observation.schema.v2.json", encoding="utf-8"))
PKG = json.load(io.open("sample_mission_package.v2.json", encoding="utf-8"))

KNOWN_DEVICES = {o["device_id"] for o in PKG["observations"] if "device_id" in o}


# TYPE-SAFE ACCESS. `x.get("k") or {}` only guards None/falsy; a WRONG TYPE is truthy
# and then .get() raises AttributeError - a crash, not a rejection. Found by Dhruv
# Patel's negative suite 2026-08-28 (bare-string location). Same fix as V2.2.
def _obj(v):
    return v if isinstance(v, dict) else {}


def strip(o):
    return {k: v for k, v in o.items() if not k.startswith("_")}


def semantic_errors(o):
    errs = []
    prov = _obj(o.get("provenance"))
    loc = _obj(o.get("location"))
    integ = _obj(o.get("raw_artifact_integrity"))

    # 1. device must be known to the register (stand-in: the fixture's own set,
    #    because no Capability Registry exists - Shivam confirmed 2026-08-17)
    if o.get("device_id") not in KNOWN_DEVICES:
        errs.append("device_id %r not in the device register (stand-in)" % o.get("device_id"))

    # 2. provenance device must agree with the observation device   [Manya]
    if prov.get("device_id") != o.get("device_id"):
        errs.append("provenance.device_id %r disagrees with device_id %r"
                    % (prov.get("device_id"), o.get("device_id")))

    # 3. provenance mission must agree with the top-level mission   [Manya]
    if prov.get("mission_id") != o.get("mission_id"):
        errs.append("provenance.mission_id %r disagrees with mission_id %r"
                    % (prov.get("mission_id"), o.get("mission_id")))

    # 4. raw artifact must be traceable through provenance          [Manya]
    if prov.get("raw_artifact") and prov["raw_artifact"] != o.get("raw_artifact"):
        errs.append("provenance.raw_artifact %r disagrees with raw_artifact %r"
                    % (prov.get("raw_artifact"), o.get("raw_artifact")))

    # 5. capture time must agree                                    [Manya]
    if prov.get("captured_at") and prov["captured_at"] != o.get("timestamp"):
        errs.append("provenance.captured_at disagrees with timestamp")

    # 6. the artifact named in measurement must be the artifact preserved
    m = _obj(o.get("measurement"))
    if m.get("artifact") and m["artifact"] != o.get("raw_artifact"):
        errs.append("measurement.artifact %r disagrees with raw_artifact %r"
                    % (m.get("artifact"), o.get("raw_artifact")))

    # 7. a null position must be paired with UNCERTAIN
    if (loc.get("latitude") is None or loc.get("longitude") is None) \
            and o.get("quality_state") != "UNCERTAIN":
        errs.append("null coordinate without quality_state UNCERTAIN")

    # 8. no reliable tide source means the state must be UNKNOWN
    t = o.get("tidal_state")
    if isinstance(t, dict) and not t.get("source") and t.get("state") != "UNKNOWN":
        errs.append("tidal_state %r claimed with no source - must be UNKNOWN"
                    % t.get("state"))

    # 9. a numeric value requires a parameter naming what it measures
    if m.get("value") is not None and not m.get("parameter"):
        errs.append("measurement.value present without measurement.parameter")

    # 10. THE SYNTHETIC GUARD - see module docstring
    if o.get("is_synthetic") is False:
        if o.get("hardware_verified") is not True:
            errs.append("is_synthetic=false but hardware_verified is not true - "
                        "a real capture requires a verified device")
        if not integ.get("checksum_sha256"):
            errs.append("is_synthetic=false but no raw_artifact_integrity."
                        "checksum_sha256 - a real capture must hash its evidence")

    return errs


def check(label, obs, expect_pass):
    e = semantic_errors(strip(obs))
    ok = (not e) == expect_pass
    print("  [%s] %-54s expect %-6s got %s"
          % ("PASS" if ok else "FAIL", label,
             "accept" if expect_pass else "REJECT",
             "accepted" if not e else "rejected"))
    if e and expect_pass:
        for x in e[:2]:
            print("         ! %s" % x[:100])
    if not e and not expect_pass:
        print("         ! a contradictory record was accepted")
    return ok


print("V2.0 SEMANTIC / REFERENTIAL VALIDATION")
print()
res = []
print("VALID OBSERVATIONS")
for o in PKG["observations"]:
    res.append(check(o["observation_id"], o, True))

base = strip(PKG["observations"][0])
print()
print("CONTRADICTORY RECORDS - must be rejected")

o = copy.deepcopy(base); o["device_id"] = "DRONE-UNKNOWN-999"
res.append(check("device not in register", o, False))

o = copy.deepcopy(base); o["provenance"]["device_id"] = "DRONE-RGB-002"
res.append(check("provenance device disagrees", o, False))

o = copy.deepcopy(base); o["provenance"]["mission_id"] = "MNG-OTHER-20260817-001"
res.append(check("provenance mission disagrees", o, False))

o = copy.deepcopy(base); o["provenance"]["raw_artifact"] = "OTHER.JPG"
res.append(check("provenance artifact disagrees", o, False))

o = copy.deepcopy(base); o["provenance"]["captured_at"] = "2026-08-17T11:00:00Z"
res.append(check("provenance captured_at disagrees with timestamp", o, False))

o = copy.deepcopy(base); o["measurement"]["artifact"] = "SOMETHING-ELSE.JPG"
res.append(check("measurement.artifact disagrees with raw_artifact", o, False))

o = copy.deepcopy(base); o["location"]["latitude"] = None
res.append(check("null latitude without UNCERTAIN", o, False))

o = copy.deepcopy(base); o["tidal_state"] = {"state": "HIGH", "source": None, "timestamp": None}
res.append(check("tidal HIGH claimed with no source", o, False))

o = copy.deepcopy(base); o["measurement"]["value"] = 4.7
res.append(check("numeric value with no parameter", o, False))

print()
print("THE SYNTHETIC GUARD - Closure Plan section 4")
o = copy.deepcopy(base); o["is_synthetic"] = False
res.append(check("is_synthetic=false on today's fixture", o, False))

o = copy.deepcopy(base); o["is_synthetic"] = False; o["hardware_verified"] = True
res.append(check("is_synthetic=false, verified, but no content hash", o, False))

o = copy.deepcopy(base)
o["is_synthetic"] = False; o["hardware_verified"] = True
o["raw_artifact_integrity"] = {"checksum_sha256": "a"*63+"f",
                               "hash_algorithm": "sha256", "artifact_type": "IMAGE"}
res.append(check("is_synthetic=false, verified, hashed (a real capture)", o, True))

print()
print("%d/%d semantic checks passed" % (sum(1 for r in res if r), len(res)))
print()
print("KNOWN LIMITATIONS, stated rather than hidden:")
print("  - the device register does not exist (no Capability Registry API,")
print("    confirmed by Shivam 2026-08-17). KNOWN_DEVICES is a STAND-IN.")
print("  - tidal_state has no canonical home. Group 1 has not accepted it;")
print("    Kavy has it on the v0.5 list.")
print("  - is_synthetic=false is currently unreachable for real Group 3 data:")
print("    no sensor has produced a reading, 0 of 8 actuators mounted.")
sys.exit(0 if all(res) else 1)
