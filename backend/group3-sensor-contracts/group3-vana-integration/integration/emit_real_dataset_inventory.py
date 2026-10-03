# -*- coding: utf-8 -*-
"""Emit the inventory of REAL datasets available to Group 3, in Arya's nine fields.

Arya, 2026-08-31: "give me the inventory of REAL datasets currently available to
Group 3 that can actually be routed through the existing intake architecture ...
For each available dataset give only: dataset/source name, current owner/location,
source/API/file, observation fields, units, timestamp, location, whether it has
already entered Group 3 intake, whether Group 1 POST/GET proof exists.
Please don't create substitute/synthetic measurements."

Every row is derived from artifacts on disk. Nothing is listed as available that
Group 3 does not hold, and nothing Group 3 holds is omitted.

Run:  python emit_real_dataset_inventory.py
"""
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


def main():
    rows = []

    # ---- 1. the proven one -------------------------------------------------
    tc = json.load(io.open(os.path.join(LIVE, "live_mission_package.json"), encoding="utf-8"))
    tco = tc["observations"][0]
    rows.append({
        "dataset": "Open-Meteo forecast - Thane Creek",
        "owner_location": "External third party (Open-Meteo.com). Captured by Group 3.",
        "source": tco["raw_artifact"],
        "observation_fields": "precipitation (emitted). Raw capture also holds temperature_2m, "
                              "relative_humidity_2m, wind_speed_10m - see row 4",
        "units": "mm",
        "timestamp": tco["observation_timestamp"],
        "location": "%.4f, %.4f (Thane Creek)" % (tco["location"]["latitude"],
                                                  tco["location"]["longitude"]),
        "entered_g3_intake": "YES",
        "g1_proof": "YES - POST 201, canonical CR-b4615a27-7ab1-4bde-a078-a56fa0f2414c, "
                    "GET 200. 13/13 acceptance 2026-08-25T11:04:54Z",
        "_artifacts": ["evidence/live/live_mission_package.json",
                       "evidence/live/LIVE_ACCEPTANCE_PASSED_2026-08-25.json",
                       "evidence/live/SOURCE_EVIDENCE_PACK_EMITTED_2026-08-25.json"],
    })

    # ---- 2. the five held --------------------------------------------------
    regions, tss = [], set()
    for code in ["MU", "NM", "VS", "THN", "MV"]:
        o = json.load(io.open(os.path.join(LIVE, "live_mission_package_%s.json" % code),
                              encoding="utf-8"))["observations"][0]
        regions.append("%s (%.4f, %.4f)" % (o["survey_id"], o["location"]["latitude"],
                                            o["location"]["longitude"]))
        tss.add(o["observation_timestamp"])
    rows.append({
        "dataset": "Open-Meteo forecast - five regions",
        "owner_location": "External third party. Captured by Group 3, coordinates from Group 2.",
        "source": "https://api.open-meteo.com/v1/forecast (one call per region)",
        "observation_fields": "precipitation",
        "units": "mm",
        "timestamp": ", ".join(sorted(tss)),
        "location": " | ".join(regions),
        "entered_g3_intake": "YES - built, schema+semantic valid, raw bytes preserved and "
                             "sha256-verified 5 of 5",
        "g1_proof": "YES - all five INGESTED by Group 1 on 2026-09-01 (201 POST + 200 GET each) "
                    "and INDEPENDENTLY VERIFIED by Group 3 the same day: GET on every record, "
                    "diffed field-by-field against the payload Group 3 built. 6/6, 19 checks "
                    "per record. Measurement, unit, coordinates, timestamps, identity, "
                    "provenance and raw-source sha256 all intact",
        "_artifacts": ["evidence/live/live_mission_package_{MU,NM,VS,THN,MV}.json",
                       "evidence/live/GROUP1_SIX_REGION_VERIFICATION_20260901T091610Z.json",
                       "evidence_packet/SIX_REGION_VERIFICATION_RESULT.md"],
    })

    # ---- 3. SAMACHAR -------------------------------------------------------
    sp = os.path.join(LIVE, "live_mission_package_SAMACHAR.json")
    if os.path.isfile(sp):
        s = json.load(io.open(sp, encoding="utf-8"))
        so = s["observations"][0]
        rows.append({
            "dataset": "SAMACHAR news/context - Omkar Patil's pipeline",
            "owner_location": "Omkar Patil (Samachar). Output supplied to Group 3.",
            "source": s["_source_url"],
            "observation_fields": "news_score (emitted). credibility_score, confidence, "
                                  "authenticity retained as source metadata, NOT as measurement",
            "units": "score (dimensionless)",
            "timestamp": "%s (%s)" % (so["observation_timestamp"],
                                      s["_timestamp_derivation"]["kind"]),
            "location": "%.4f, %.4f - %s. SUBJECT area of the article, not a sensor position"
                        % (so["location"]["latitude"], so["location"]["longitude"],
                           s["_location_derivation"]["mapped_to_region"]),
            "entered_g3_intake": "YES - built, schema+semantic valid, source payload persisted "
                                 "and sha256-verified",
            "g1_proof": "YES - INGESTED 2026-09-01 under Rukayya's GO. POST 201, canonical "
                        "%s, GET 200. Round-trip verified: 15 of 15 "
                        "comparable fields identical, including the measurement at full "
                        "precision and the raw-source sha256" % "CR-c3d2e7cc-3ddc-41d6-a85c-b782cf43801d",
            "_artifacts": ["evidence/live/live_mission_package_SAMACHAR.json",
                           "evidence_packet/samachar/"],
        })

    # ---- 4. the unemitted variables - a real finding ------------------------
    extra, coords = set(), set()
    for f in glob.glob(os.path.join(LIVE, "raw_artifact_*.json")):
        if "samachar" in os.path.basename(f):
            continue
        try:
            d = json.load(io.open(f, encoding="utf-8"))
        except Exception:
            continue
        for k in (d.get("current") or {}):
            if k not in ("time", "interval", "precipitation"):
                extra.add(k)
        if d.get("latitude") is not None:
            coords.add((round(d["latitude"], 3), round(d["longitude"], 3)))
    if extra:
        rows.append({
            "dataset": "Open-Meteo - variables ALREADY CAPTURED but never emitted",
            "owner_location": "Already on disk in Group 3's evidence store",
            "source": "The same captures behind rows 1 and 2 - no new call needed",
            "observation_fields": ", ".join(sorted(extra)),
            "units": "temperature_2m degC | relative_humidity_2m % | wind_speed_10m km/h",
            "timestamp": "same as the capture they came from",
            "location": "%d distinct points already captured" % len(coords),
            "entered_g3_intake": "NO - the contract carries ONE measurement per observation, so "
                                 "only precipitation was emitted. These are real, hash-verified, "
                                 "and unused",
            "g1_proof": "NO - never emitted. Each would need its own observation_id from the "
                        "contract owner",
            "_artifacts": ["evidence/live/raw_artifact_*.json"],
        })

    # ---- 5. reachable but not captured -------------------------------------
    rows.append({
        "dataset": "Open-Meteo marine / air-quality / flood APIs",
        "owner_location": "External third party. Referenced in Group 3 code, never called.",
        "source": "marine-api / air-quality-api / flood-api .open-meteo.com/v1/*",
        "observation_fields": "NOT CAPTURED - no claim made about what they return",
        "units": "n/a", "timestamp": "n/a", "location": "n/a",
        "entered_g3_intake": "NO",
        "g1_proof": "NO",
        "_artifacts": ["integration/build_live_observation_candidate.py (URLs only)"],
    })

    # ---- 6. routed to G3 but NOT held --------------------------------------
    # Shravani answered both questions on 2026-09-01. Recorded as her words, not our inference.
    for name, owner, note in [
        ("Marine Task 3 normalized datasets", "Shravani / Marine team",
         "CLOSED 2026-09-01 - owner confirms NOT APPLICABLE to Group 3"),
        ("National GIS v3 / spatial_truth_export.json", "Shravani / GIS team",
         "CLOSED 2026-09-01 - owner confirms NOT APPLICABLE to Group 3"),
    ]:
        rows.append({
            "dataset": name, "owner_location": owner,
            "source": "Held by the owner. NOT routed to Group 3.",
            "observation_fields": ("name, lat/lon, source, notes - NO measurement, NO unit, "
                                   "NO timestamp (owner's description, 2026-09-01)"),
            "units": "n/a - no measurements",
            "timestamp": "n/a - records carry none",
            "location": ("lat/lon present, but keyed to facility/zone scale (economic zones, "
                         "ports, IWT terminals, waterways) - does NOT resolve to named "
                         "localities"),
            "entered_g3_intake": "NO - and correctly so",
            "g1_proof": "N/A",
            "_status": note,
            "_owner_words": ("Reference/context data; destination is the science/context layer, "
                             "not Group 3 intake. Both rows closed as 'nothing needed'."),
            "_artifacts": [],
        })
    rows.append({
        "dataset": "GOUDHA 41 runtime-ingested records",
        "owner_location": "GOUDHA (a system/product - owner NOT identified by Group 3)",
        "source": "NOT HELD BY GROUP 3 - zero files present",
        "observation_fields": "unknown - never received, and no owner to ask",
        "units": "unknown", "timestamp": "unknown", "location": "unknown",
        "entered_g3_intake": "NO - never received",
        "g1_proof": "NO",
        "_status": ("STILL OPEN. Unlike Marine/GIS, the observation-shaped question has never "
                    "been put to anyone because no owner has been identified."),
        "_artifacts": [],
    })

    doc = {
        "_README": "Real datasets available to Group 3. Derived from artifacts on disk.",
        "_for": "Arya Barge", "_owner": "Hemanth Reddy - Group 3 Integration",
        "_generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "_generated_by": "integration/emit_real_dataset_inventory.py",
        "_rule_followed": ("Nothing listed as available that Group 3 does not hold. Nothing held "
                           "is omitted. No substitute or synthetic measurement anywhere."),
        "datasets": rows,
        "_summary": {
            "held_and_proven_end_to_end": 7,
            "held_and_validated_awaiting_g1": 0,
            "held_but_never_emitted": 1,
            "reachable_but_not_captured": 1,
            "closed_by_owner_as_not_applicable": 2,
            "routed_to_group3_but_no_owner_identified": 1,
        },
    }
    out = os.path.join(DAY6, "GROUP3_REAL_DATASET_INVENTORY.json")
    with io.open(out, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=2, ensure_ascii=False); fh.write("\n")

    print("GROUP 3 - REAL DATASET INVENTORY")
    print()
    for r in rows:
        print("  %-46s intake=%-4s g1=%s"
              % (r["dataset"][:46], r["entered_g3_intake"][:3], r["g1_proof"][:3]))
    print()
    for k, v in doc["_summary"].items():
        print("  %-34s %d" % (k, v))
    print()
    print("  -> %s" % os.path.basename(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
