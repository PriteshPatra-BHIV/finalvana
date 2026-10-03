# -*- coding: utf-8 -*-
"""ACCEPTANCE TEST — does one observation stay identifiable across all four groups?

The Day-6 acceptance criterion for the Coordination Lead is stated as:

    "One observation must be identifiable across GROUP 3 -> GROUP 1 -> GROUP 2 ->
     GROUP 4 without renaming it halfway through the pipeline."

Every other script in this repository proves ONE hop. Nothing until now compared
the identifier and provenance ACROSS all of them, which is the actual criterion.
This test reads each group's real artifact and asserts agreement.

It does not accept a hop as proven merely because a file exists - each artifact
must contain the identifier, and the values must be byte-identical.

Run:  python test_identity_survival.py
"""
import io, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
DAY6 = os.path.dirname(HERE)

EXPECT_ID = "TC-Z03-F02-LIDAR-OBS001"

ARTIFACTS = {
    "GROUP 3 fixture":
        os.path.join(DAY6, "contract", "sample_mission_package.json"),
    "GROUP 1 canonical record":
        os.path.join(HERE, "canonical_observation.json"),
    "GROUP 2 context record":
        os.path.join(DAY6, "handoff_bundle", "4_contextual_result_group2.json"),
    "GROUP 2 semantic input":
        os.path.join(DAY6, "integration", "group2_semantic_input.json"),
    "GROUP 4 TANTRA envelope":
        os.path.join(HERE, "group3_to_group4_handoff.json"),
    "UI field-observation view":
        os.path.join(DAY6, "integration", "ui_field_observation_view.json"),
}


def load(p):
    if not os.path.exists(p):
        return None
    return json.load(io.open(p, encoding="utf-8"))


def dig(obj, *keys):
    """Find the first of `keys` anywhere in a nested structure."""
    found = []

    def walk(o):
        if isinstance(o, dict):
            for k, v in o.items():
                if k in keys and not isinstance(v, (dict, list)):
                    found.append((k, v))
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
    walk(obj)
    return found


rows = []
print("IDENTITY SURVIVAL ACROSS FOUR GROUPS")
print("expected observation_id: %s" % EXPECT_ID)
print()

# ---- 1. the identifier itself must appear, unchanged, in every artifact -----
print("[1] observation_id present and unchanged in every artifact")
for label, path in ARTIFACTS.items():
    doc = load(path)
    if doc is None:
        print("  [FAIL] %-28s ARTIFACT MISSING (%s)" % (label, os.path.basename(path)))
        rows.append(False)
        continue
    hits = [v for k, v in dig(doc, "observation_id", "artifact_id", "idempotency_key")]
    match = EXPECT_ID in hits
    others = sorted({h for h in hits if h != EXPECT_ID and isinstance(h, str)})
    print("  [%s] %-28s %s" % ("PASS" if match else "FAIL", label,
                               "found" if match else "NOT FOUND"))
    if others:
        print("         also present: %s" % ", ".join(others[:3]))
    rows.append(match)

# ---- 2. no artifact may rename it ------------------------------------------
print()
print("[2] no artifact renames the observation")
g3 = load(ARTIFACTS["GROUP 3 fixture"])
g1 = load(ARTIFACTS["GROUP 1 canonical record"])
g2 = load(ARTIFACTS["GROUP 2 context record"])
g4 = load(ARTIFACTS["GROUP 4 TANTRA envelope"])
ui = load(ARTIFACTS["UI field-observation view"])

chain = [
    ("Group 3 fixture", (g3 or {}).get("observations", [{}])[0].get("observation_id")),
    ("Group 1 canonical", ((g1 or {}).get("canonical_observation") or {}).get("observation_id")),
    ("Group 2 context", (g2 or {}).get("observation_id")),
    ("Group 4 envelope", (((g4 or {}).get("envelope") or {}).get("replay") or {}).get("idempotency_key")),
    ("UI view", ((ui or {}).get("view") or {}).get("observation_id")),
]
for label, val in chain:
    ok = (val == EXPECT_ID)
    print("  [%s] %-22s %s" % ("PASS" if ok else "FAIL", label, val))
    rows.append(ok)

# ---- 3. the measurement must not be mutated -------------------------------
print()
print("[3] the primary measurement is not mutated downstream")
m_g1 = (((g1 or {}).get("canonical_observation") or {}).get("measurement") or {}).get("value")
m_ui = (((ui or {}).get("view") or {}).get("measurement") or {}).get("value")
g2_val = ((g2 or {}).get("parameter_value") or {}).get("value")
print("  Group 1 canonical value : %s" % m_g1)
print("  UI view value           : %s" % m_ui)
print("  Group 2 context value   : %s  (null is CORRECT - Group 2 declared a GAP)" % g2_val)
ok = (m_g1 == 4.7 and m_ui == 4.7)
print("  [%s] Group 3's 4.7 m survives unmodified" % ("PASS" if ok else "FAIL"))
rows.append(ok)
ok2 = (g2_val is None)
print("  [%s] Group 2 did NOT overwrite the primary observation"
      % ("PASS" if ok2 else "FAIL"))
rows.append(ok2)

# ---- 4. provenance must survive ------------------------------------------
print()
print("[4] provenance survives to the canonical record")
prov = ((g1 or {}).get("canonical_observation") or {}).get("provenance") or {}
raw = ((g1 or {}).get("canonical_observation") or {}).get("raw_artifact") or {}
dev = ((g1 or {}).get("canonical_observation") or {}).get("device_id")
for label, val, want in (("provenance_id", prov.get("provenance_id"), True),
                         ("device_id", dev, "G3-LIDAR-001"),
                         ("raw artifact ref", raw.get("reference"), True),
                         ("raw artifact sha256", raw.get("sha256"), True)):
    ok = (val == want) if isinstance(want, str) else bool(val)
    print("  [%s] %-20s %s" % ("PASS" if ok else "FAIL", label, val))
    rows.append(ok)

# ---- 5. the synthetic marking must never be stripped ----------------------
print()
print("[5] synthetic marking survives every hop - the rule most costly to lose")
marks = [
    ("Group 3 fixture", (g3 or {}).get("is_synthetic")),
    ("Group 1 canonical", ((g1 or {}).get("_honesty") or {}).get("is_synthetic")),
    ("Group 4 envelope", ((g4 or {}).get("_honesty") or {}).get("is_synthetic")),
    ("UI banner", (((ui or {}).get("view") or {}).get("origin_banner") or {}).get("is_synthetic")),
]
for label, val in marks:
    ok = (val is True)
    print("  [%s] %-22s is_synthetic=%s" % ("PASS" if ok else "FAIL", label, val))
    rows.append(ok)

# Group 2 carries it as source_type on the observation side
g2_src = None
for k, v in dig(g2 or {}, "source_type"):
    g2_src = v
print("  [%s] %-22s Group 2 record carries no is_synthetic flag of its own"
      % ("INFO", "Group 2 context"))
print("         (their record describes CONTEXT, not the observation - the")
print("          synthetic marking travels on the observation, which is correct)")

# ---- 6. trace must be null and never invented ----------------------------
print()
print("[6] trace_id is null everywhere Group 3 touches - never invented")
traces = [
    ("Group 3 fixture", (g3 or {}).get("observations", [{}])[0].get("trace_id")),
    ("Group 4 envelope", ((g4 or {}).get("envelope") or {}).get("trace_id")),
]
for label, val in traces:
    ok = (val is None)
    print("  [%s] %-22s trace_id=%s" % ("PASS" if ok else "FAIL", label, val))
    rows.append(ok)

print()
print("=" * 74)
print("RESULT: %d/%d checks passed" % (sum(1 for r in rows if r), len(rows)))
print()
print("WHAT THIS PROVES: one observation is identifiable, unmutated and")
print("provenance-linked across the Group 3, Group 1, Group 2 and Group 4")
print("artifacts, with its synthetic marking intact at every hop.")
print()
print("WHAT IT DOES NOT PROVE:")
print("  - Group 1's DEPLOYED instance   (API specified, no host issued)")
print("  - the SVACS / edge transport    (not a transport service - see SVACS_ANALYSIS)")
print("  - Group 2's LIVE service        (their own sheet says LOCAL / NOT LIVE)")
print("  - Group 4 governed execution    (awaiting their run)")
print("  - any hardware                  (no sensor has produced a reading)")
print()
print("This is artifact-level identity survival, not a live end-to-end run.")
sys.exit(0 if all(rows) else 1)
