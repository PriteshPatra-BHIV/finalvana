# -*- coding: utf-8 -*-
"""Emit the Group 1 region seed - everything Group 1 needs to integrate the five regions.

WHY THIS EXISTS
---------------
Raj, 2026-08-28: "the 5 more locations are not integrated we need from group 3 and
group 2 proper schema and contract for that."

His diagnosis of the CAUSE matches Group 3's: the locations are not registered on the
Group 1 side, which is why POST returns 500 rather than 400.

But the thing he needs is NOT a schema or a contract. Verified this session:

    contract_version   const 2.2, unchanged
    required fields    24, unchanged
    cross-field rules  15, unchanged
    payload shape      identical key set, identical types vs the 13/13-passing record
                       25 of 37 fields byte-identical

No schema change is involved and no contract amendment is required. What is missing is
REFERENCE DATA: the five survey/zone identities and their coordinates, so the Group 1
persistence layer has a dataset/geography row to attach an observation to.

The evidence for that reading: TC-Z03-EXT attached to dataset DS-GROUP3-TC-Z03-F02 -
a dataset created by EARLIER F02 LiDAR work. MU-Z01 has no equivalent row.

This file emits exactly that reference data, in one place, with its authority.

Run:  python emit_group1_region_seed.py
"""
import datetime, io, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
DAY6 = os.path.dirname(HERE)

SCHEMA = json.load(io.open(os.path.join(DAY6, "contract", "observation.schema.v2.2.json"),
                           encoding="utf-8"))
REGISTER = json.load(io.open(os.path.join(DAY6, "VANA_ZONE_IDENTITY_REGISTER.json"),
                             encoding="utf-8"))

SUFFIX = {"Mumbai": "_MU", "Navi Mumbai": "_NM", "Vasai": "_VS",
          "Thane": "_THN", "Maval": "_MV"}

BASIS = {
    "Mumbai": "Mahim Nature Park / Mithi River Mouth",
    "Navi Mumbai": "Nerul / T.S. Chanakya Wetlands",
    "Vasai": "Vasai Creek Estuary",
    "Thane": "Upvan Lake Basin / Yeoor Hills boundary",
    "Maval": "Pawna Lake Catchment Area",
}


def main():
    rows = []
    for e in REGISTER["register"]:
        region = e["region"]
        pkg = json.load(io.open(os.path.join(DAY6, "evidence", "live",
                                             "live_mission_package%s.json" % SUFFIX[region]),
                                encoding="utf-8"))
        o = pkg["observations"][0]
        rows.append({
            "region": region,
            "survey_id": o["survey_id"],
            "zone_id": o["zone_id"],
            "mission_id": o["mission_id"],
            "observation_id": o["observation_id"],
            "idempotency_key": o["idempotency_key"],
            "location": {"latitude": o["location"]["latitude"],
                         "longitude": o["location"]["longitude"],
                         "altitude_m": o["location"]["altitude_m"],
                         "crs": "EPSG:4326"},
            "coordinate_basis": BASIS[region],
            "coordinate_source": "Group 2 (Sakshi), supplied 2026-08-28 with stated basis",
            "identity_authority": ("Owner ruling, Arya Barge, Group 3 Canonical Observation "
                                   "Contract & Provenance Owner, 2026-08-28"),
            "capture_method": o["capture_method"],
            "flight_id": o["flight_id"],
            "sensor_id": o["sensor_id"],
            "device_id": o["device_id"],
            "source_identity": o["source_identity"],
            "synthetic_state": o["synthetic_state"],
            "is_synthetic": o["is_synthetic"],
            "hardware_verified": o["hardware_verified"],
            "payload_file": "evidence/live/live_mission_package%s.json" % SUFFIX[region],
        })

    doc = {
        "_README": ("Group 1 region seed. Everything Group 1 needs to integrate the five new "
                    "regions. This is REFERENCE DATA, not a schema and not a contract change."),
        "_generated_by": "integration/emit_group1_region_seed.py",
        "_generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "_for": "Raj / Sanskar / Kavy - Group 1",

        "THE_IMPORTANT_CLARIFICATION": {
            "_asked_for": ("Raj, 2026-08-28: 'we need from group 3 and group 2 proper schema and "
                           "contract for that'."),
            "_the_correction": ("No schema change and no contract amendment is involved. Verified "
                                "this session and stated so that Group 1 does not plan work that "
                                "is not needed."),
            "evidence": {
                "contract_version": "const 2.2 - unchanged since the freeze",
                "required_fields": len(SCHEMA["required"]),
                "cross_field_rules": len(SCHEMA["allOf"]),
                "payload_shape_vs_the_13_of_13_record": ("identical key set, identical types, "
                                                         "25 of 37 fields byte-identical"),
                "differing_fields": ("12, and every one is a value that SHOULD differ for a new "
                                     "region: survey_id, zone_id, observation_id, mission_id, "
                                     "idempotency_key, coordinates, timestamps, hash, "
                                     "provenance_reference, raw_artifact"),
            },
            "_what_is_actually_missing": ("REFERENCE DATA. The Group 1 persistence layer has no "
                                          "dataset/geography row for these survey/zone pairs. "
                                          "Evidence: TC-Z03-EXT attached to dataset "
                                          "DS-GROUP3-TC-Z03-F02, created by EARLIER F02 LiDAR "
                                          "work. Every Group 3 observation Group 1 holds begins "
                                          "TC-. These five are the first for a previously-unseen "
                                          "survey/zone."),
            "_why_the_distinction_matters": ("A schema change would need a contract amendment, an "
                                             "owner ruling, and a re-freeze - days. Seeding "
                                             "reference rows needs none of that. Calling this a "
                                             "schema problem would send Group 1 after the wrong "
                                             "work."),
        },

        "authority": {
            "identity": ("Owner ruling, Arya Barge, 2026-08-28. survey_id and zone_id APPROVED for "
                         "all five. All five observation_ids validate against the frozen V2.2 "
                         "pattern."),
            "coordinates": ("Group 2 (Sakshi), 2026-08-28, each with a stated environmental basis. "
                            "Group 3 did not choose or modify them."),
            "contract": "V2.2 FROZEN. Unchanged. No V2.3, no new field, no re-freeze.",
        },

        "regions": rows,

        "what_group1_needs_to_do": [
            "1. Register a dataset/geography row for each of the five survey/zone pairs below, the "
            "same way DS-GROUP3-TC-Z03-F02 exists for TC/Z03.",
            "2. OR guard the lookup so a first-observation-for-a-new-survey creates the row instead "
            "of raising. Either resolves the 500.",
            "3. Confirm, and Group 3 re-runs the acceptance sequence for all five - about 15 "
            "minutes total.",
        ],

        "current_failure": {
            "symptom": "POST /observations -> HTTP 500 Internal Server Error",
            "observed": ["MU-Z01-EXT-OPENMETEO-OBS001 at 2026-08-28T14:58:24Z",
                         "NM-Z01-EXT-OPENMETEO-OBS001 at 2026-08-28T15:01:39Z"],
            "service_health": "GET /health returns 200 healthy - not an outage",
            "persistence": "None. All five observation_ids return 404 - the 500 aborts before write",
            "existing_records": "Undamaged. TC-Z03-EXT-OPENMETEO-OBS001 intact, CR-b4615a27- unchanged",
            "_why_500_not_400": ("Group 1 returns 400 for a validation failure - demonstrated "
                                 "2026-08-24. A 500 is an unhandled exception."),
            "_server_log_pointer": "The exception at 14:58:24Z or 15:01:39Z will name the cause.",
        },

        "_group3_will_not_work_around_it": (
            "Emitting these five under TC/Z03 would be accepted by Group 1 and would be WRONG - "
            "they are five different regions whose identities the contract owner ruled today. "
            "Group 3 has not done this and will not."),

        "_honest_caveat": ("All five are EXTERNAL LIVE API observations - synthetic_state "
                           "CONTROLLED, hardware_verified false. Real third-party weather data "
                           "through the controlled Group 3 path, NOT field sensing. 1/6 to 6/6 is a "
                           "runtime-identity milestone and still zero regions of hardware evidence."),
    }

    out = os.path.join(DAY6, "GROUP1_REGION_SEED.json")
    with io.open(out, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=2, ensure_ascii=False)
        fh.write("\n")

    print("GROUP 1 REGION SEED - what Group 1 needs to integrate the five regions")
    print()
    print("  %-13s %-5s %-5s %-30s %s" % ("REGION", "SURV", "ZONE", "OBSERVATION_ID", "COORDINATE"))
    for r in rows:
        print("  %-13s %-5s %-5s %-30s %.4f, %.4f"
              % (r["region"], r["survey_id"], r["zone_id"], r["observation_id"],
                 r["location"]["latitude"], r["location"]["longitude"]))
    print()
    print("  NO schema change. NO contract change. contract_version const 2.2,")
    print("  %d required fields, %d cross-field rules - all unchanged."
          % (len(SCHEMA["required"]), len(SCHEMA["allOf"])))
    print("  What is missing is a dataset/geography row per survey/zone.")
    print()
    print("  -> %s" % os.path.basename(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
