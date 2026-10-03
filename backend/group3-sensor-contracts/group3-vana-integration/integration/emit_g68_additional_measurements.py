# -*- coding: utf-8 -*-
"""Emit the G-68 additional measurement records under Arya's ruling of 2026-09-02.

ARYA'S RULING (approved), verbatim constraints:
  - observation types approved as proposed
  - units approved as source-declared and UNCONVERTED
  - shape approved: OBS001 precipitation, then OBS002/003/004 at the same
    timestamp/provenance
  - "Apply the same semantic mapping to MU, NM, VS and THN, giving 15 additional
    records total"
  - "Keep all source values unchanged, preserve the existing provenance/
     timestamp/state semantics, RE-VERIFY THE RAW-ARTIFACT HASH BEFORE EMISSION,
     and do not create any new capture or derived/converted measurement"

WHAT THIS SCRIPT REFUSES TO DO
  - it will not emit if the raw artifact's sha256 does not match the hash on the
    existing canonical record for that region
  - it will not emit if a source field is absent from the capture
  - it will not convert a unit or round a value
  - it makes NO network call and NO new capture

Thane Creek (TC) is deliberately absent: its raw source bytes were never
persisted, so its extra variables cannot be recovered without a new capture.
5 regions x 3 measurements = 15.

Run:  python emit_g68_additional_measurements.py
"""
import copy
import datetime
import glob
import hashlib
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DAY6 = os.path.dirname(HERE)
LIVE = os.path.join(DAY6, "evidence", "live")

REGIONS = ["MU", "NM", "VS", "THN", "MV"]

# Arya's approved mapping: sequence -> (source field, observation_type)
MAPPING = [
    ("OBS002", "temperature_2m",       "air_temperature"),
    ("OBS003", "relative_humidity_2m", "relative_humidity"),
    ("OBS004", "wind_speed_10m",       "wind_speed"),
]


def sha256_of(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def artifacts_by_hash():
    out = {}
    for p in glob.glob(os.path.join(LIVE, "raw_artifact_*.json")):
        if "samachar" in os.path.basename(p):
            continue
        out[sha256_of(p)] = p
    return out


def main():
    print("G-68 EMISSION - additional measurements from already-captured data")
    print("Under Arya's semantic ruling of 2026-09-02.")
    print("No new capture. No conversion. No rounding. No network call.")
    print()

    by_hash = artifacts_by_hash()
    emitted, packages = [], []

    for code in REGIONS:
        base_path = os.path.join(LIVE, "live_mission_package_%s.json" % code)
        pkg = json.load(io.open(base_path, encoding="utf-8"))
        base = pkg["observations"][0]
        want_hash = base["raw_artifact_integrity"]["checksum_sha256"]

        # --- HARD GATE 1: the artifact must exist and re-hash correctly -------
        art = by_hash.get(want_hash)
        if art is None:
            raise SystemExit(
                "ABORT %s: no raw artifact on disk hashes to %s. Refusing to emit a "
                "measurement whose source cannot be re-verified." % (code, want_hash[:16]))
        actual = sha256_of(art)
        if actual != want_hash:
            raise SystemExit("ABORT %s: artifact hash %s != record hash %s"
                             % (code, actual[:16], want_hash[:16]))

        cap = json.load(io.open(art, encoding="utf-8"))
        cur, units = cap.get("current") or {}, cap.get("current_units") or {}

        print("  %-4s artifact %s  sha re-verified" % (code, os.path.basename(art)[:34]))

        for seq, field, otype in MAPPING:
            # --- HARD GATE 2: the source field must be present ---------------
            if field not in cur:
                raise SystemExit("ABORT %s/%s: '%s' absent from the capture. Refusing "
                                 "to substitute a value." % (code, seq, field))
            if field not in units:
                raise SystemExit("ABORT %s/%s: no source-declared unit for '%s'. "
                                 "Refusing to invent one." % (code, seq, field))

            obs = copy.deepcopy(base)
            oid = "%s-%s-%s-%s-%s" % (base["survey_id"], base["zone_id"],
                                      base["flight_id"], base["sensor_id"], seq)

            # ONLY these five fields change. Everything else is inherited
            # verbatim from the live record - same place, same instant, same
            # provenance, same state semantics.
            obs["observation_id"] = oid
            obs["observation_seq"] = seq
            obs["observation_type"] = otype
            obs["measurement"] = cur[field]      # unchanged, unconverted, unrounded
            obs["unit"] = units[field]           # source-declared
            obs["idempotency_key"] = "IK-" + oid

            # --- HARD GATE 3: value identity ---------------------------------
            if obs["measurement"] != cur[field]:
                raise SystemExit("ABORT: measurement mutated during assembly")

            emitted.append({
                "region": code, "observation_id": oid, "observation_type": otype,
                "source_field": field, "measurement": obs["measurement"],
                "unit": obs["unit"],
                "observation_timestamp": obs["observation_timestamp"],
                "provenance_reference": obs["provenance_reference"],
                "raw_artifact_sha256": want_hash,
                "raw_artifact_file": os.path.basename(art),
            })

            out_pkg = copy.deepcopy(pkg)
            out_pkg["observations"] = [obs]
            out_pkg["_g68"] = {
                "emitted_under": "Arya Barge semantic ruling, 2026-09-02",
                "source_field": field,
                "unit_authority": "Open-Meteo current_units, source-declared, unconverted",
                "derived_from_capture": os.path.basename(art),
                "raw_artifact_sha256_reverified": want_hash,
                "no_new_capture": True, "no_conversion": True, "no_rounding": True,
                "sibling_of": base["observation_id"],
            }
            out_path = os.path.join(LIVE, "live_mission_package_%s_%s.json" % (code, seq))
            with io.open(out_path, "w", encoding="utf-8") as fh:
                json.dump(out_pkg, fh, indent=2, ensure_ascii=False)
                fh.write("\n")
            packages.append(out_path)
            print("       %-30s %-18s %s %s" % (oid, otype, obs["measurement"], obs["unit"]))

    stamp = datetime.datetime.now(datetime.timezone.utc)
    manifest = os.path.join(LIVE, "G68_EMISSION_%s.json" % stamp.strftime("%Y%m%dT%H%M%SZ"))
    with io.open(manifest, "w", encoding="utf-8") as fh:
        json.dump({
            "_README": ("G-68 additional measurement records, emitted from already-captured "
                        "and hash-verified Open-Meteo data. No new capture, no conversion."),
            "_ruling": "Arya Barge, Group 3 Canonical Observation Contract owner, 2026-09-02",
            "_emitted_at": stamp.isoformat(),
            "_regions": REGIONS,
            "_excluded": {"TC": "raw source bytes never persisted; not recoverable "
                                "without a new capture"},
            "_not_yet_ingested": ("These are BUILT and VALIDATED only. Nothing has been sent "
                                  "to Group 1."),
            "count": len(emitted),
            "records": emitted,
        }, fh, indent=2, ensure_ascii=False)
        fh.write("\n")

    print()
    print("  %d records emitted across %d regions" % (len(emitted), len(REGIONS)))
    print("  -> evidence/live/%s" % os.path.basename(manifest))
    print()
    print("  NOT INGESTED. Nothing sent to Group 1.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
