# -*- coding: utf-8 -*-
"""Verify the five regional payloads against the exact field list Group 1 asked for.

Sanskar, 2026-08-31, requested the five real source observations and named the
fields G1 needs. He also said: "Do not create fixtures, dummy measurements,
fabricated observation IDs, or substitute coordinates."

This proves, before anything is sent, that:
  1. every field on HIS list is present and non-null where it must be
  2. each payload validates structurally AND semantically against frozen V2.2
  3. the raw source bytes are on disk and the recorded sha256 matches them
  4. no coordinate has been substituted - each matches the authorised register

It writes nothing and sends nothing. Read-only.

Run:  python verify_five_region_payloads.py
"""
import glob
import hashlib
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DAY6 = os.path.dirname(HERE)

REGIONS = [("Mumbai", "MU"), ("Navi Mumbai", "NM"), ("Vasai", "VS"),
           ("Thane", "THN"), ("Maval", "MV")]

# Sanskar's list, verbatim.
REQUIRED = ["observation_id", "source_identity", "mission_id", "observation_timestamp",
            "source_timestamp", "location", "device_id", "observation_type",
            "capture_method", "measurement", "unit", "quality_state", "synthetic_state",
            "is_synthetic", "calibration_state", "processing_status", "accuracy",
            "raw_artifact", "raw_artifact_integrity", "provenance_reference", "provenance"]


def main():
    schema = json.load(io.open(os.path.join(DAY6, "contract", "observation.schema.v2.2.json"),
                               encoding="utf-8"))
    seed = json.load(io.open(os.path.join(DAY6, "GROUP1_REGION_SEED.json"), encoding="utf-8"))
    authorised = {r["survey_id"]: (r["location"]["latitude"], r["location"]["longitude"])
                  for r in seed["regions"]}

    import jsonschema
    ns = {}
    vpath = os.path.join(DAY6, "contract", "validate_semantic_v22.py")
    cwd = os.getcwd()
    os.chdir(os.path.dirname(vpath))
    exec(io.open(vpath, encoding="utf-8").read().split("res = []")[0], ns)
    os.chdir(cwd)

    print("VERIFYING THE FIVE REGIONAL PAYLOADS AGAINST GROUP 1'S FIELD LIST")
    print()
    all_ok = True
    for region, code in REGIONS:
        p = os.path.join(DAY6, "evidence", "live", "live_mission_package_%s.json" % code)
        if not os.path.isfile(p):
            print("  %-13s *** PAYLOAD MISSING ***" % region); all_ok = False; continue
        obs = json.load(io.open(p, encoding="utf-8"))["observations"][0]

        missing = [f for f in REQUIRED if f not in obs or obs[f] is None]
        loc = obs.get("location") or {}
        if loc.get("latitude") is None or loc.get("longitude") is None:
            missing.append("location.lat/lon")

        struct = sorted(jsonschema.Draft202012Validator(schema).iter_errors(obs),
                        key=lambda e: list(e.path))
        sem = list(ns["semantic_errors"](ns["strip"](obs)))

        # raw bytes on disk, hash matches
        h = (obs.get("raw_artifact_integrity") or {}).get("checksum_sha256", "")
        cand = glob.glob(os.path.join(DAY6, "evidence", "live", "raw_artifact_%s*.json" % h[:16]))
        bytes_ok = bool(cand) and hashlib.sha256(io.open(cand[0], "rb").read()).hexdigest() == h

        # coordinate not substituted
        auth = authorised.get(obs.get("survey_id"))
        coord_ok = auth is not None and abs(loc.get("latitude", 0) - auth[0]) < 1e-9 \
            and abs(loc.get("longitude", 0) - auth[1]) < 1e-9

        ok = not missing and not struct and not sem and bytes_ok and coord_ok
        all_ok = all_ok and ok
        print("  %-13s %s" % (region, "READY" if ok else "*** NOT READY ***"))
        print("     observation_id   %s" % obs.get("observation_id"))
        print("     fields (%d/%d)    %s" % (len(REQUIRED) - len(missing), len(REQUIRED),
                                             "all present" if not missing else "MISSING: %s" % missing))
        print("     structural       %s" % ("PASS" if not struct else "FAIL %d" % len(struct)))
        print("     semantic         %s" % ("PASS" if not sem else "FAIL: %s" % sem))
        print("     raw bytes+sha256 %s" % ("verified on disk" if bytes_ok else "*** NOT VERIFIED ***"))
        print("     coordinate       %.4f, %.4f  %s"
              % (loc.get("latitude", 0), loc.get("longitude", 0),
                 "matches authorised register" if coord_ok else "*** DOES NOT MATCH REGISTER ***"))
        print()

    print("  %s" % ("ALL FIVE READY TO SEND - no fixtures, no substituted coordinates"
                    if all_ok else "*** NOT ALL READY - do not send ***"))
    print()
    print("  Files to attach:")
    for _, c in REGIONS:
        print("    evidence/live/live_mission_package_%s.json" % c)
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
