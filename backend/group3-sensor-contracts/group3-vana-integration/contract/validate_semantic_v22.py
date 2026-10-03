# -*- coding: utf-8 -*-
"""V2.2 semantic / referential validation — the layer JSON Schema cannot provide.

WHY THIS FILE EXISTS
--------------------
The V2.2 schema tells consumers that cross-field agreement "is enforced by
contract/validate_semantic_v22.py". Until 2026-08-20 that file did not exist —
the contract described enforcement that was not implemented. An adversarial
audit found that a record whose provenance pointed at a different device, a
different mission and a different artifact validated cleanly.

This closes that. Checks 2-5 are Manya Shukla's original design, carried forward
from the V1.2 semantic layer and extended for V2.2's new fields.

WHAT JSON SCHEMA STRUCTURALLY CANNOT DO
---------------------------------------
Schema validates SHAPE. It cannot compare two fields to each other, and it
cannot check a reference against a register. An observation can be perfectly
schema-valid while claiming device G3-LIDAR-001 at the top level and
G3-CAM-001 in its provenance — internally contradictory, and its provenance
therefore worthless.

Run:  python validate_semantic_v22.py
"""
import copy, io, json, re, sys
from datetime import datetime


def ts(v):
    """Parse an ISO-8601 UTC timestamp to an instant.

    Timestamps MUST be compared as instants, never as strings. Arya's metadata
    contract section 6 permits fractional seconds, and '+00:00' and 'Z' are both
    valid UTC designators - so three spellings of the SAME instant are legal:

        2026-08-13T09:14:22Z
        2026-08-13T09:14:22+00:00
        2026-08-13T09:14:22.172677Z

    Under string comparison '09:14:22Z' > '09:14:22.172677Z' (because 'Z' sorts
    after '.'), and '...Z' != '...+00:00'. An earlier version of this file
    compared strings, so it reported a source_timestamp as being AFTER the
    observation when the two named the same second, and reported provenance
    captured_at as disagreeing with observation_timestamp when both were the
    same instant written two legal ways. Found by audit 2026-08-20.
    """
    if not v:
        return None
    try:
        return datetime.fromisoformat(str(v).replace("Z", "+00:00"))
    except ValueError:
        return None

SCHEMA = json.load(io.open("observation.schema.v2.2.json", encoding="utf-8"))
PKG = json.load(io.open("sample_mission_package.v2.2.json", encoding="utf-8"))

# The device register does not exist as a queryable service - Shivam confirmed
# Group 4's registry is file-based and holds only a placeholder for Group 3.
# Until it does, the fixture's own device set is the only register available.
# This is a STAND-IN and is labelled as one rather than presented as
# referential integrity.
KNOWN_DEVICES = {o["device_id"] for o in PKG["observations"] if "device_id" in o}

# Group 2's declared zone polygon for this mission, from the context artifact they
# supplied on 2026-08-21. Used to FLAG a coordinate that has been silently moved.
#
# WHY THIS IS NEEDED: JSON Schema can only check that a coordinate is a number in
# WGS84 range. A latitude silently changed from 19.1288 to 19.5000 is still a
# perfectly valid latitude, so both the schema and every cross-field rule accepted
# it - found by the 2026-08-21 mandatory test "coordinate mutation rejected or
# flagged", which no prior suite covered. The only way to detect a substitution to
# a VALID-but-wrong coordinate is to bind it to a declared area.
#
# This is Group 2's polygon, not a Group 3 invention. If their artifact is absent
# the check reports itself unavailable rather than silently passing.
ZONE_POLYGON = None
ZONE_SOURCE = "UNAVAILABLE - Group 2 context artifact not present; coordinate binding NOT enforced"
try:
    _ctx = json.load(io.open(
        "../reference/inbound/G2_context_TC-Z03-F02-LIDAR-OBS001_AS_RECEIVED_2026-08-21.json",
        encoding="utf-8"))
    ZONE_POLYGON = _ctx["location_polygon"]["coordinates"][0]
    ZONE_SOURCE = ("Group 2 context record for TC-Z03-F02-LIDAR-OBS001, received 2026-08-21, "
                   "location_polygon")
except Exception:
    pass


def _inside(lat, lon, ring):
    """Ray-casting point-in-polygon. Ring is [[lon, lat], ...]."""
    x, y, inside, j = lon, lat, False, len(ring) - 1
    for i in range(len(ring)):
        xi, yi = ring[i]
        xj, yj = ring[j]
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi) + xi):
            inside = not inside
        j = i
    return inside

# Arya's compatibility table, from her V2.2 contract section 4.
SYNTHETIC_MAP = {
    "PHYSICAL":   (False,),
    "CONTROLLED": (True,),
    "SYNTHETIC":  (True,),
    "SIMULATED":  (True,),
    "UNKNOWN":    (None,),
}


def strip(o):
    return {k: v for k, v in o.items() if not k.startswith("_")}


def semantic_errors(o):
    """Return agreement/reference failures. Empty list = passes."""
    errs = []
    # TYPE-SAFE ACCESS. An earlier version used `o.get("x") or {}`, which only guards
    # against None/falsy. A WRONG TYPE is truthy: a bare-string location passed the
    # guard and then loc.get(...) raised AttributeError - an unhandled crash instead of
    # a clean rejection. Found by Dhruv Patel's negative suite, 2026-08-28 (test N3).
    #
    # This matters in a fail-closed system: a crash is not a rejection. A caller cannot
    # tell "the payload is malformed" from "the validator is broken", and the structural
    # schema layer must be the thing that reports a type error, not a stack trace.
    def _obj(v):
        return v if isinstance(v, dict) else {}

    prov = _obj(o.get("provenance"))
    loc = _obj(o.get("location"))
    integ = _obj(o.get("raw_artifact_integrity"))
    m = o.get("measurement")

    # --- 1. device must be known to the register [stand-in]
    #     EXTENDED 2026-08-24: an external provider following the approved
    #     G3-EXT-<PROVIDER>-<NN> convention is DECLARED BY THE CONTRACT ITSELF, so it is
    #     recognised without appearing in the fixture's device set. The live external
    #     observation is generated at runtime and must NOT be baked into the static
    #     fixture - that would make the fixture non-deterministic and break the
    #     reproducibility guarantee. This remains a STAND-IN: no queryable device
    #     register exists (gap G-6).
    _dev = o.get("device_id") or ""
    _external_declared = bool(re.match(r"^G3-EXT-[A-Z0-9]+-[0-9]{2}$", _dev))
    if _dev not in KNOWN_DEVICES and not _external_declared:
        errs.append("device_id %r not in the device register (stand-in: fixture device set)"
                    % o.get("device_id"))

    # --- 2. provenance device must agree with the observation device   [Manya]
    if prov.get("device_id") != o.get("device_id"):
        errs.append("provenance.device_id %r disagrees with device_id %r"
                    % (prov.get("device_id"), o.get("device_id")))

    # --- 3. provenance mission must agree with the top-level mission   [Manya]
    if prov.get("mission_id") != o.get("mission_id"):
        errs.append("provenance.mission_id %r disagrees with mission_id %r"
                    % (prov.get("mission_id"), o.get("mission_id")))

    # --- 4. raw artifact must be traceable through provenance          [Manya]
    if not prov.get("raw_artifact"):
        errs.append("provenance.raw_artifact missing - provenance links Device -> Operator -> Mission "
                    "-> Raw Artifact and the last link is absent")
    elif prov["raw_artifact"] != o.get("raw_artifact"):
        errs.append("provenance.raw_artifact %r disagrees with raw_artifact %r"
                    % (prov.get("raw_artifact"), o.get("raw_artifact")))

    # --- 5. capture time must agree                                    [Manya]
    if prov.get("captured_at") and ts(prov["captured_at"]) != ts(o.get("observation_timestamp")):
        errs.append("provenance.captured_at %r disagrees with observation_timestamp %r"
                    % (prov.get("captured_at"), o.get("observation_timestamp")))

    # --- 6. the composite ID must agree with its own component fields
    parts = (o.get("observation_id") or "").split("-")
    if len(parts) >= 5:
        for f, expected in (("survey_id", parts[0]), ("zone_id", parts[1]),
                            ("flight_id", parts[2]), ("sensor_id", parts[3]),
                            ("observation_seq", parts[4])):
            if f in o and o[f] != expected:
                errs.append("%s %r contradicts observation_id component %r"
                            % (f, o[f], expected))

    # --- 7. a source_timestamp may not post-date the observation
    st, ot = ts(o.get("source_timestamp")), ts(o.get("observation_timestamp"))
    if st and ot and st > ot:
        errs.append("source_timestamp %r is AFTER observation_timestamp %r - a source cannot "
                    "report a reading later than the observation it produced" % (st, ot))

    # --- 8. Arya's compatibility mapping, enforced in full
    ss, isyn = o.get("synthetic_state"), o.get("is_synthetic")
    if ss in SYNTHETIC_MAP and "is_synthetic" in o:
        allowed = SYNTHETIC_MAP[ss] + (None,)
        if isyn not in allowed:
            errs.append("synthetic_state %s maps to is_synthetic %r in Arya's table, got %r"
                        % (ss, SYNTHETIC_MAP[ss][0], isyn))

    # --- 9. PHYSICAL requires real hardware evidence, not just a flag
    if ss == "PHYSICAL":
        if o.get("hardware_verified") is not True:
            errs.append("synthetic_state PHYSICAL requires hardware_verified true")
        if not integ.get("checksum_sha256"):
            errs.append("synthetic_state PHYSICAL requires a real content hash - a physical "
                        "capture must hash the evidence it produced")

    # --- 10. data_state and quality_state must not contradict
    #     RULED by Arya Barge 2026-08-20: "They are two distinct required axes.
    #     data_state represents lifecycle/data state; quality_state represents QA/quality
    #     verdict. We retain both fields and reject outright contradictions. They must not
    #     be merged or treated as aliases." The owner kept the identical vocabulary for
    #     both, so only outright contradictions are detectable - that is the ruled design.
    ds, qs = o.get("data_state"), o.get("quality_state")
    # RULED by Arya Barge 2026-08-22: "For contradiction rule (3), use quality_state
    # INGESTED with data_state RAW/CAPTURED as the invalid combinations." A record
    # cannot be quality-INGESTED before it is lifecycle-INGESTED. The previous pairs
    # keyed on data_state VALIDATED/REJECTED, which are no longer legal data_state
    # values under the narrowed lifecycle vocabulary.
    if qs == "INGESTED" and ds in ("RAW", "CAPTURED"):
        errs.append("quality_state INGESTED with data_state %s - a record cannot be quality-ingested "
                    "before it is lifecycle-ingested" % ds)

    # --- 11. a null position must be paired with quality_state UNCERTAIN
    #     MOVED 2026-08-22 per Arya's ruling: UNCERTAIN is a QA verdict and is no longer
    #     a legal data_state value, so this requirement sits on quality_state alone.
    if loc.get("latitude") is None or loc.get("longitude") is None:
        if o.get("quality_state") != "UNCERTAIN":
            errs.append("null coordinate without quality_state UNCERTAIN")

    # --- 12. provenance_reference must actually point somewhere
    pr = o.get("provenance_reference")
    if not pr or not str(pr).strip():
        errs.append("provenance_reference missing or empty")

    # --- 13. accuracy must never be invented                   [metadata contract s9]
    #     "Accuracy shall contain either a verified numeric value; or NOT VERIFIED.
    #      No plausible-looking estimate shall be invented."
    #     Controlled Observation Fixtures rules 4 and 6: no GPS accuracy shall be
    #     invented; unsupported accuracy shall be recorded as NOT VERIFIED.
    acc = o.get("accuracy")
    if isinstance(acc, (int, float)) and not isinstance(acc, bool):
        if o.get("hardware_verified") is not True:
            errs.append("accuracy %r is a numeric figure but hardware_verified is not true - an "
                        "accuracy value with no verified hardware behind it is invented. Use the "
                        "literal 'NOT_VERIFIED'" % acc)

    # --- 14. the same rule for position accuracy               [fixtures rule 4]
    pa = loc.get("position_accuracy_m")
    if isinstance(pa, (int, float)) and not isinstance(pa, bool):
        if o.get("hardware_verified") is not True:
            errs.append("location.position_accuracy_m %r asserted without verified hardware - "
                        "no GPS accuracy shall be invented" % pa)

    # --- 15. calibration must not be claimed without evidence  [metadata contract s10]
    #     "No calibration record shall be claimed without evidence."
    if o.get("calibration_state") == "CALIBRATED" and o.get("hardware_verified") is not True:
        errs.append("calibration_state CALIBRATED claimed with hardware_verified %r - no calibration "
                    "record shall be claimed without evidence" % o.get("hardware_verified"))

    # --- 16. an untrusted clock must be declared               [metadata contract s6]
    #     "If the clock cannot be trusted, the system shall not invent a timestamp."
    #     A null captured_at is that admission; it must show in the data state.
    #     MOVED 2026-08-22 per Arya's ruling: the UNCERTAIN admission sits on
    #     quality_state, not data_state.
    if "captured_at" in prov and prov.get("captured_at") is None:
        if o.get("quality_state") != "UNCERTAIN":
            errs.append("provenance.captured_at is null (clock not trusted) but quality_state is %r, "
                        "not UNCERTAIN" % o.get("quality_state"))

    # --- 17. tidal state must not be invented                  [metadata contract s14]
    #     "No tidal state shall be invented." A definite reading needs a named source.
    tid = o.get("tidal_state")
    if isinstance(tid, dict) and tid.get("state") not in (None, "UNKNOWN"):
        if not (tid.get("source") or "").strip():
            errs.append("tidal_state %r asserted with no source - no tidal state shall be invented; "
                        "record UNKNOWN instead" % tid.get("state"))
    elif isinstance(tid, str) and tid != "UNKNOWN":
        errs.append("tidal_state %r given as a bare string carries no source. The object form with a "
                    "named source is required for a definite reading" % tid)

    # --- 18. the idempotency key derives from the identity     [metadata contract s16]
    #     CONVENTION CONFIRMED by Raj (Group 1) 2026-08-24 at commit 1140f58:
    #     IK-<observation_id>. The backend is FORMAT-AGNOSTIC and enforces no prefix,
    #     so this is an agreed convention Group 3 honours, not a Group 1 constraint.
    #     Enforced here rather than in the schema for exactly that reason: a schema
    #     pattern would assert a constraint Group 1 does not actually have.
    ik = o.get("idempotency_key")
    oid = o.get("observation_id")
    if ik and oid:
        if oid not in ik:
            errs.append("idempotency_key %r is not derived from observation_id %r - a repeated "
                        "submission would create a second canonical record" % (ik, oid))
        elif ik != "IK-" + oid:
            errs.append("idempotency_key %r does not follow the confirmed Group 1 convention "
                        "IK-<observation_id>, i.e. %r. Group 1's backend accepts any non-empty key, "
                        "so this would not fail on the wire - which is exactly why it has to be "
                        "caught here" % (ik, "IK-" + oid))

    # --- 19. a coordinate may not be silently moved out of the declared zone
    #     [Group 3 task 2026-08-21: "coordinate mutation rejected or flagged"]
    if ZONE_POLYGON and loc.get("latitude") is not None and loc.get("longitude") is not None:
        if not _inside(loc["latitude"], loc["longitude"], ZONE_POLYGON):
            errs.append("coordinate (%s, %s) falls OUTSIDE the declared mission zone polygon - a "
                        "coordinate that is valid but wrong is exactly what a silent substitution "
                        "looks like. Zone source: %s"
                        % (loc["latitude"], loc["longitude"], ZONE_SOURCE))

    return errs


res = []


def check(label, obs, expect_pass):
    e = semantic_errors(strip(obs))
    ok = (not e) == expect_pass
    print("  [%s] %-56s expect %-6s got %s"
          % ("PASS" if ok else "FAIL", label,
             "accept" if expect_pass else "REJECT",
             "accepted" if not e else "rejected"))
    if e and expect_pass:
        for x in e[:2]:
            print("         ! %s" % x[:100])
    if not e and not expect_pass:
        print("         ! a contradictory record was accepted")
    return ok


print("V2.2 SEMANTIC / REFERENTIAL VALIDATION")
print("agreement between fields - which JSON Schema structurally cannot express")
print()
print("VALID OBSERVATIONS")
for o in PKG["observations"]:
    res.append(check(o["observation_id"], o, True))

base = strip(PKG["observations"][0])
print()
print("CONTRADICTORY RECORDS - must be rejected")
for label, mut in [
    ("device not in register",          lambda o: o.__setitem__("device_id", "DEV-UNKNOWN-999")),
    ("provenance device disagrees",     lambda o: o["provenance"].__setitem__("device_id", "G3-CAM-001")),
    ("provenance mission disagrees",    lambda o: o["provenance"].__setitem__("mission_id", "OTHER-MISSION")),
    ("provenance artifact disagrees",   lambda o: o["provenance"].__setitem__("raw_artifact", "other.las")),
    ("provenance captured_at disagrees",lambda o: o["provenance"].__setitem__("captured_at", "2026-08-13T11:00:00Z")),
    ("zone_id contradicts composite ID",lambda o: o.__setitem__("zone_id", "Z07")),
    ("sensor_id contradicts composite ID", lambda o: o.__setitem__("sensor_id", "IMX500")),
    ("source_timestamp after observation", lambda o: o.__setitem__("source_timestamp", "2027-01-01T00:00:00Z")),
    ("captured_at a different instant",  lambda o: o["provenance"].__setitem__("captured_at", "2026-08-13T09:14:23Z")),
    ("empty provenance_reference",      lambda o: o.__setitem__("provenance_reference", "   ")),
]:
    o = copy.deepcopy(base); mut(o)
    res.append(check(label, o, False))

print()
print("TIMESTAMPS COMPARED AS INSTANTS, NOT STRINGS - three legal spellings of one instant")
for label, mut, exp in [
    ("captured_at '+00:00' vs observation 'Z' (same instant)",
     lambda o: o["provenance"].__setitem__("captured_at", "2026-08-13T09:14:22+00:00"), True),
    ("source '...22Z' vs observation '...22.172677Z' (same second)",
     lambda o: (o.__setitem__("observation_timestamp", "2026-08-13T09:14:22.172677Z"),
                o["provenance"].__setitem__("captured_at", "2026-08-13T09:14:22.172677Z")), True),
    ("source genuinely one second later - still rejected",
     lambda o: o.__setitem__("source_timestamp", "2026-08-13T09:14:23Z"), False),
]:
    obs = copy.deepcopy(base); mut(obs)
    res.append(check(label, obs, exp))

print()
print("ARYA'S FROZEN METADATA CONTRACT - RULES THAT FORBID INVENTION")
for label, mut, exp in [
    ("accuracy numeric without verified hardware",
     lambda o: o.__setitem__("accuracy", 0.85), False),
    ("accuracy NOT_VERIFIED (the honest form)",
     lambda o: o.__setitem__("accuracy", "NOT_VERIFIED"), True),
    ("position_accuracy_m asserted without hardware",
     lambda o: o["location"].__setitem__("position_accuracy_m", 1.5), False),
    ("calibration CALIBRATED without evidence",
     lambda o: o.__setitem__("calibration_state", "CALIBRATED"), False),
    ("null captured_at without quality_state UNCERTAIN",
     lambda o: o["provenance"].__setitem__("captured_at", None), False),
    ("provenance.raw_artifact missing",
     lambda o: o["provenance"].__setitem__("raw_artifact", None), False),
    ("tidal_state HIGH with no source",
     lambda o: o.__setitem__("tidal_state", {"state": "HIGH", "source": None}), False),
    ("tidal_state HIGH with a named source",
     lambda o: o.__setitem__("tidal_state", {"state": "HIGH", "source": "INCOIS tide table"}), True),
    ("idempotency_key not derived from the identity",
     lambda o: o.__setitem__("idempotency_key", "some-random-uuid"), False),
    ("idempotency_key without the confirmed IK- prefix",
     lambda o: o.__setitem__("idempotency_key", o["observation_id"]), False),
]:
    obs = copy.deepcopy(base); mut(obs)
    res.append(check(label, obs, exp))

print()
print("ARYA'S COMPATIBILITY TABLE - enforced in both directions")
for label, mut, exp in [
    ("SYNTHETIC + is_synthetic false",
     lambda o: o.__setitem__("is_synthetic", False), False),
    ("PHYSICAL + is_synthetic true",
     lambda o: (o.__setitem__("synthetic_state", "PHYSICAL"), o.__setitem__("is_synthetic", True)), False),
    ("CONTROLLED + is_synthetic true (correct)",
     lambda o: o.__setitem__("synthetic_state", "CONTROLLED"), True),
    ("UNKNOWN + is_synthetic null (correct)",
     lambda o: (o.__setitem__("synthetic_state", "UNKNOWN"), o.__setitem__("is_synthetic", None)), True),
]:
    o = copy.deepcopy(base); mut(o)
    res.append(check(label, o, exp))

print()
print("PHYSICAL REQUIRES EVIDENCE, NOT A FLAG")
o = copy.deepcopy(base)
o["synthetic_state"] = "PHYSICAL"; o["is_synthetic"] = False
res.append(check("PHYSICAL without hardware_verified", o, False))
o["hardware_verified"] = True
o["raw_artifact_integrity"] = {"checksum_sha256": None, "hash_algorithm": None, "artifact_type": "point_cloud"}
res.append(check("PHYSICAL, verified, but no content hash", o, False))
o["raw_artifact_integrity"]["checksum_sha256"] = "a" * 63 + "f"
o["raw_artifact_integrity"]["hash_algorithm"] = "sha256"
res.append(check("PHYSICAL, verified, hashed (a real capture)", o, True))

print()
print("STATE CONTRADICTION")
for label, ds, qs in [("quality_state INGESTED vs data_state RAW", "RAW", "INGESTED"),
                      ("quality_state INGESTED vs data_state CAPTURED", "CAPTURED", "INGESTED")]:
    o = copy.deepcopy(base); o["data_state"] = ds; o["quality_state"] = qs
    res.append(check(label, o, False))

print()
print("=" * 78)
print("%d/%d semantic checks passed" % (sum(1 for r in res if r), len(res)))
print()
print("KNOWN LIMITATIONS, stated rather than hidden:")
print("  - KNOWN_DEVICES is a STAND-IN. No device register service exists; Group 4's")
print("    (external providers matching G3-EXT-<PROVIDER>-<NN> are accepted as declared by")
print("     the contract convention, since live external observations are generated at")
print("     runtime and must not be baked into the deterministic fixture)")
print("    capability registry is file-based and holds only a placeholder for Group 3.")
print("  - data_state and quality_state are now DISTINCT vocabularies, ruled by the contract")
print("    owner on 2026-08-22: data_state RAW/CAPTURED/INGESTED (lifecycle) and quality_state")
print("    RAW/CAPTURED/VALIDATED/REJECTED/UNCERTAIN/INGESTED (QA verdict). This closed the")
print("    2026-08-20 ambiguity where a producer could not tell which field to set.")
print("  - coordinate binding: %s" % ZONE_SOURCE)
print("  - synthetic_state PHYSICAL is currently unreachable for real Group 3 data: no")
print("    sensor has produced a recorded reading and 0 of 8 actuators are mounted.")
sys.exit(0 if all(res) else 1)
