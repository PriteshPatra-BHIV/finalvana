# -*- coding: utf-8 -*-
"""Emit the Sensor -> VANA Data Interface Map (Workstream 6).

ASSIGNED
--------
Arya Barge, 2026-08-27: "define and validate the Sensor -> Edge -> VANA/Group 1
integration boundary, including timestamp, device identity, location, observation
identity inputs, raw artifact, integrity/hash, provenance, retry and offline
behaviour... make sure the hardware output remains compatible with the frozen V2.2
observation contract and doesn't introduce new canonical/provenance semantics outside
the agreed authority boundary."

Matches Workstream 6 in GROUP 3-VANA-27-08-2026.md.

AUTHORITY BOUNDARY THIS FILE OBEYS
----------------------------------
"Group 3 may design implementation mappings, but may not silently create canonical
schema or provenance rules. Nupur's MDU boundary remains relevant here."

So: every row below MAPS a hardware concern onto a field the frozen V2.2 contract
already defines. Where the contract has NO field for a real hardware concern, this
file records it as an OPEN GAP addressed to the contract owner - it does not invent
a field, and it does not propose a schema change as though it were already agreed.

Classification is read from the live persistence matrix and the frozen schema, not
hand-written, so the map cannot drift from what Group 1 actually does.

Run:  python emit_sensor_interface_map.py
"""
import io, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
DAY6 = os.path.dirname(HERE)

SCHEMA = json.load(io.open(os.path.join(DAY6, "contract", "observation.schema.v2.2.json"),
                           encoding="utf-8"))
MATRIX = json.load(io.open(os.path.join(DAY6, "V2.2_PERSISTENCE_MATRIX.json"), encoding="utf-8"))
BYFIELD = {r["field"]: r for r in MATRIX["matrix"]}


def cls(field):
    r = BYFIELD.get(field)
    return r["classification"] if r else "NOT_IN_MATRIX"


# Workstream 6's ten named concerns, each mapped to the contract field that already
# carries it. "carried_by" names a REAL field; nothing here is invented.
INTERFACE = [
    {"concern": "Sensor payload model",
     "carried_by": ["measurement", "unit", "observation_type"],
     "hardware_note": (
         "A numeric reading goes in measurement with a real unit; the numeric-requires-unit rule "
         "is enforced in both the bare and object forms. An image or point cloud goes in "
         "raw_artifact with measurement carrying the descriptive form."),
     "blocked_on": "Workstream 1 - the actual measurements the first unit must sense."},

    {"concern": "Timestamp source and semantics",
     "carried_by": ["observation_timestamp", "source_timestamp", "ingestion_timestamp"],
     "hardware_note": (
         "Three distinct roles already exist. For a field sensor: observation_timestamp is when the "
         "sensor took the reading and MUST NOT change if the send is delayed; source_timestamp is "
         "the device's own reported instant; ingestion_timestamp is Group 1's and Group 3 emits "
         "null. A large observation->ingestion delta is therefore already the expressible signal of "
         "a delayed send - no new field needed."),
     "blocked_on": None},

    {"concern": "Device identity",
     "carried_by": ["device_id", "source_identity", "sensor_id"],
     "hardware_note": (
         "device_id is the physical device for real hardware. The G3-EXT-<PROVIDER>-<NN> convention "
         "is for EXTERNAL providers only and must NOT be used for a Group 3 sensor - a G3-EXT- "
         "prefix is contractually bound to capture_method external_api. A field unit uses a real "
         "device identifier and capture_method sensor or ground."),
     "blocked_on": None},

    {"concern": "Location identity",
     "carried_by": ["location"],
     "hardware_note": (
         "Nested location with latitude/longitude/altitude_m/gnss_status/position_accuracy_m, "
         "WGS84/EPSG:4326. gnss_status and position_accuracy_m are STRUCTURALLY INAPPLICABLE for "
         "external_api but become live fields with real values for hardware - an earlier acceptance "
         "record already proved FIX / 0.25 m / 45.2 m persist. If there is no fix, latitude and "
         "longitude may be null ONLY with quality_state UNCERTAIN."),
     "blocked_on": None},

    {"concern": "Observation identity inputs",
     "carried_by": ["observation_id", "survey_id", "zone_id", "flight_id", "observation_seq"],
     "hardware_note": (
         "The composite tuple. A ground sensor is NOT a flight: flight_id EXT is reserved for "
         "external sources, so a fixed ground unit needs a ruling on what occupies the third "
         "segment. See OPEN GAP W6-3."),
     "blocked_on": "Contract owner ruling - see W6-3."},

    {"concern": "Raw artifact capture",
     "carried_by": ["raw_artifact"],
     "hardware_note": (
         "A reference to the preserved original evidence. For a sensor this is the stored reading "
         "or image on the edge device, then its uploaded location. The bytes MUST be persisted at "
         "capture time - Group 3 already learned this the hard way on 2026-08-25 when an "
         "Open-Meteo response was hashed but not stored, leaving the hash unverifiable."),
     "blocked_on": None},

    {"concern": "Hash / integrity approach",
     "carried_by": ["raw_artifact_integrity", "provenance_reference"],
     "hardware_note": (
         "sha256 over the actual captured bytes, computed ON THE EDGE DEVICE before transmission so "
         "the hash covers what the sensor produced rather than what survived the network. "
         "artifact_type is mandatory; checksum may be null ONLY where hashing is genuinely "
         "unsupported, and a placeholder checksum is prohibited."),
     "blocked_on": None},

    {"concern": "Provenance fields",
     "carried_by": ["provenance", "provenance_reference"],
     "hardware_note": (
         "provenance requires device_id, mission_id, captured_at and raw_artifact, each agreeing "
         "with the top-level value. provenance_reference is the separate reviewer-facing pointer. "
         "Both now persist and are returned by Group 1 - verified 2026-08-26."),
     "blocked_on": None},

    {"concern": "Transmission / retry behaviour",
     "carried_by": ["idempotency_key"],
     "hardware_note": (
         "ALREADY SOLVED AND PROVEN LIVE. IK-<observation_id> with the 201 ACCEPTED -> 200 "
         "IDEMPOTENT_REPLAY -> 409 IDEMPOTENCY_CONFLICT sequence is the retry model. A field unit "
         "that retries after a dropped connection sends the same key and gets 200, not a duplicate. "
         "A unit that retries with MUTATED content gets 409 and cannot corrupt the canonical record. "
         "This needs no design work - it needs implementing on the edge device."),
     "blocked_on": None},

    {"concern": "Offline behaviour",
     "carried_by": [],
     "hardware_note": (
         "NOT COVERED BY THE CONTRACT. See OPEN GAP W6-1. The idempotency key makes the eventual "
         "replay safe, but the SEMANTICS of a late arrival are undefined."),
     "blocked_on": "Contract owner ruling - see W6-1."},
]


# Real hardware concerns with NO field in the frozen contract. Recorded as gaps for the
# contract owner. Group 3 does not invent fields and does not presume the ruling.
OPEN_GAPS = [
    {"id": "W6-1", "title": "Offline / store-and-forward semantics are undefined",
     "evidence": ("A full-text search of the frozen schema finds no occurrence of offline, "
                  "store-and-forward, buffer, backfill, late arrival or retry."),
     "why_it_matters": (
         "A field unit will lose connectivity. When it reconnects it may flush hours of buffered "
         "readings. Each carries its own observation_id so they are distinct records, and the "
         "idempotency key makes replay safe - the MECHANICS are fine. What is undefined is whether "
         "a consumer should treat a reading whose ingestion_timestamp is six hours after its "
         "observation_timestamp differently from a fresh one."),
     "who_it_actually_affects": (
         "Group 2. Their temporal-applicability ruling already turns on time windows - it ruled GAP "
         "on the LiDAR observation for being outside 2020-2023. A delayed field reading could be "
         "ruled differently purely because of transport delay rather than anything about the "
         "measurement."),
     "group3_position": (
         "The delta between observation_timestamp and ingestion_timestamp is ALREADY expressible "
         "and needs no new field. What is needed is a RULING on how a consumer should read it. That "
         "is a contract-owner and Group 2 question, not a Group 3 one."),
     "owner": "Arya Barge (contract) + Group 2 (temporal semantics)"},

    {"id": "W6-2", "title": "The clock-trust instruction in the contract is STALE and unfollowable",
     "evidence": (
         "CORRECTED FINDING. Group 3's first pass claimed clock trust was not expressible at all. "
         "That was wrong and the audit caught it: observation_timestamp's own description already "
         "says 'If the clock cannot be trusted the observation carries data_state UNCERTAIN; a time "
         "is never invented', and source_timestamp says it may be null only where the clock could "
         "not be trusted. The mechanism EXISTS. The defect is that it is now unfollowable - "
         "data_state was narrowed to RAW/CAPTURED/INGESTED by the contract owner's 2026-08-22 "
         "ruling, and UNCERTAIN moved to quality_state. The DESCRIPTION was not updated with the "
         "enum. A producer that follows the description emits a value the schema rejects."),
     "why_it_matters": (
         "This is precisely the field-hardware case. For an external_api observation the SOURCE "
         "reports the time. For a field sensor the DEVICE reports it, and a unit whose RTC reset on "
         "power loss is the single most likely bad timestamp VANA will ever see. The contract "
         "anticipated it - and then the instruction for handling it was invalidated by an unrelated "
         "amendment. The first hardware producer to hit an untrusted clock will follow the "
         "description and be rejected."),
     "concrete_failure": (
         "A field unit loses power, its clock resets, and the edge software correctly detects it "
         "cannot trust the time. Following observation_timestamp's description it sets data_state "
         "UNCERTAIN - and the payload is REJECTED, because data_state now only accepts "
         "RAW/CAPTURED/INGESTED. The honest producer is punished and the dishonest one, which emits "
         "a plausible wrong timestamp with data_state CAPTURED, sails through."),
     "group3_position": (
         "No new field is needed and none is proposed. The fix is a DESCRIPTION correction the "
         "contract owner already effectively made in 2026-08-22: the untrusted-clock marker is "
         "quality_state UNCERTAIN, not data_state UNCERTAIN. Correcting the two descriptions makes "
         "the existing mechanism followable again with zero schema change and zero wire change. A "
         "secondary question the owner may want to consider separately: the mechanism is binary "
         "(trusted / not trusted) and cannot distinguish a GNSS-disciplined clock from a "
         "free-running-but-plausible one. That is a lesser gap and not blocking."),
     "owner": "Arya Barge (contract owner) - description correction, not a semantic change"},

    {"id": "W6-3", "title": "A fixed ground sensor has no defined third identity segment",
     "evidence": ("observation_id pattern is ^[A-Z0-9]+-Z[0-9]{1,2}-(F[0-9]{1,3}|EXT)-[A-Z0-9]+-"
                  "OBS[0-9]{3,}$. The third segment accepts F### (a flight) or EXT (an external "
                  "non-flight source). A fixed ground sensor is neither."),
     "why_it_matters": (
         "Using F### would assert a flight that did not happen - exactly the fabrication the EXT "
         "amendment was created to prevent on 2026-08-22. Using EXT would assert an external "
         "third-party source, which a Group 3 sensor is not."),
     "group3_position": (
         "This is the same shape of problem the EXT amendment solved, and it should be solved the "
         "same way: an additive marker under contract-owner ruling. Group 3 does not create it "
         "unilaterally."),
     "owner": "Arya Barge (contract owner)"},

    {"id": "W6-4", "title": "hardware_verified is not returned by Group 1 - blocks the PHYSICAL gate",
     "evidence": ("Live GET 2026-08-27: hardware_verified is absent from the canonical response. "
                  "Persistence matrix classification: UNDETERMINED."),
     "why_it_matters": (
         "The frozen contract makes synthetic_state PHYSICAL conditional on hardware_verified true. "
         "synthetic_state IS persisted. So a sensor can emit PHYSICAL, Group 1 will store PHYSICAL, "
         "and a downstream consumer will see a physical-evidence claim with no way to verify the "
         "flag that justified it."),
     "why_it_has_not_bitten": (
         "No Group 3 observation has ever been PHYSICAL. Every one to date is CONTROLLED or "
         "SYNTHETIC, so the gate has never been exercised. It goes live on the first real sensor "
         "reading."),
     "group3_position": "Group 1 stores and returns hardware_verified before the first PHYSICAL emission.",
     "owner": "Raj / Group 1 (tracked as G-33)"},
]


def main():
    rows = []
    for item in INTERFACE:
        rows.append({
            "workstream6_concern": item["concern"],
            "carried_by_contract_fields": item["carried_by"],
            "persistence_at_group1": {f: cls(f) for f in item["carried_by"]},
            "hardware_mapping_note": item["hardware_note"],
            "blocked_on": item["blocked_on"],
            "requires_new_canonical_semantics": not item["carried_by"],
        })

    covered = [r for r in rows if r["carried_by_contract_fields"]]
    doc = {
        "_README": (
            "Sensor -> VANA Data Interface Map. Workstream 6 deliverable, assigned by Arya Barge "
            "2026-08-27. Maps each hardware output concern onto the field the FROZEN V2.2 contract "
            "already defines. Where the contract has no field for a real hardware concern it is "
            "recorded as an open gap for the contract owner - never invented here."),
        "_generated_by": "integration/emit_sensor_interface_map.py",
        "_owner": "Hemanth Reddy - VANA Integration & Data Interface, Group 3",
        "_contract": "observation.schema.v2.2.json (FROZEN, Arya Barge)",
        "_authority_boundary": (
            "Group 3 may design implementation mappings but may not silently create canonical schema "
            "or provenance rules. TMS strategy / GC governance / MDU schemas, provenance and identity "
            "/ Group 3 hardware implementation. Every gap below is addressed to its owner, not "
            "resolved unilaterally."),
        "_headline": (
            "%d of %d Workstream 6 concerns are ALREADY carried by the frozen V2.2 contract and need "
            "mapping, not new semantics. %d require a contract-owner ruling before field hardware "
            "emits." % (len(covered), len(rows), len(OPEN_GAPS))),
        "_retry_model_status": (
            "SOLVED AND PROVEN LIVE. IK-<observation_id> with 201 -> 200 -> 409 was demonstrated "
            "end to end against Group 1's deployed instance on 2026-08-25, 13/13 checks. The edge "
            "device implements it; no design work remains."),
        "interface_map": rows,
        "open_gaps_for_contract_owner": OPEN_GAPS,
        "compatibility_evidence": {
            "source": "V2.2_PERSISTENCE_MATRIX.json",
            "summary": MATRIX["summary"],
            "total_fields_classified": len(MATRIX["matrix"]),
            "_note": ("Every classification derived from Group 1's LIVE canonical GET, not from a "
                      "document. This is the Runtime Integration/Compatibility Evidence half of the "
                      "deliverable for the Group 1 boundary."),
        },
        "what_is_NOT_proven": (
            "No Group 3 sensor has produced a recorded reading. 0 of 8 quadruped actuators are "
            "mounted. Oak-D Pro and T-Motor 4-in-1 are classified PRESENT, not VERIFIED, per Suraj's "
            "hardware boundary ruling. This map describes the boundary a field unit MUST meet; it "
            "does not claim any field unit exists."),
    }

    out = os.path.join(DAY6, "SENSOR_TO_VANA_INTERFACE_MAP.json")
    with io.open(out, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=2, ensure_ascii=False)
        fh.write("\n")

    print("SENSOR -> VANA DATA INTERFACE MAP  (Workstream 6)")
    print()
    for r in rows:
        mark = "OK  " if r["carried_by_contract_fields"] else "GAP "
        print("  [%s] %-34s %s" % (mark, r["workstream6_concern"],
                                   ", ".join(r["carried_by_contract_fields"]) or "no contract field"))
        if r["blocked_on"]:
            print("        blocked on: %s" % r["blocked_on"])
    print()
    print("  OPEN GAPS FOR THE CONTRACT OWNER")
    for g in OPEN_GAPS:
        print("    %-6s %s" % (g["id"], g["title"]))
        print("           owner: %s" % g["owner"])
    print()
    print("  %d of %d concerns already carried by frozen V2.2." % (len(covered), len(rows)))
    print("  Compatibility evidence: %d fields classified, %s"
          % (len(MATRIX["matrix"]), MATRIX["summary"]))
    print()
    print("  -> %s" % os.path.basename(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
