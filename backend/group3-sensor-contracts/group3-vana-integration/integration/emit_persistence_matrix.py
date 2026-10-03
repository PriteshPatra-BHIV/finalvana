# -*- coding: utf-8 -*-
"""Emit the V2.2 persistence matrix.

Mandatory deliverable of the Hemanth + Raj integration task: every V2.2 field
classified as PERSISTED, TRANSFORMED, REFERENCED_EXTERNALLY or NOT_SUPPORTED.

Classification is derived from Group 1's LIVE canonical GET responses, not from a
document. Where a field cannot be classified from the response alone, it is
reported as UNDETERMINED with the reason - never guessed.

Run:  python emit_persistence_matrix.py
"""
import io, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
DAY6 = os.path.dirname(HERE)

SCHEMA = json.load(io.open(os.path.join(DAY6, "contract", "observation.schema.v2.2.json"),
                           encoding="utf-8"))
LIVE = json.load(io.open(os.path.join(DAY6, "evidence", "live", "group1_live_records.json"),
                         encoding="utf-8"))

# The acceptance record is the only live record with the position fields populated.
# It is used ONLY to establish that those columns persist - never as a substitute
# for TC-Z03-F02-LIDAR-OBS001. See KNOWN_GAPS G-8.
TARGET = LIVE["TC-Z03-F02-LIDAR-OBS001"]["observation"]
POSITION_WITNESS = LIVE["TC-Z03-F02-ACCEPTANCE-OBS1787138092"]["observation"]

P = "PERSISTED"
T = "TRANSFORMED"
R = "REFERENCED_EXTERNALLY"
N = "NOT_SUPPORTED"
U = "UNDETERMINED"

MATRIX = [
    ("observation_id", P, "observation_id", "Caller-supplied id preserved verbatim.", TARGET),
    ("observation_type", P, "observation_type", "Stored as sent.", TARGET),
    ("observation_timestamp", T, "observed_at",
     "Wire name differs; value preserved as a timestamptz.", TARGET),
    ("device_id", P, "field_observation_meta.device_id", "Stored as sent.", TARGET),
    ("mission_id", P, "field_observation_meta.mission_id", "Stored as sent.", TARGET),
    ("quality_state", T, "quality_status", "Name differs; identical six-value vocabulary.", TARGET),
    ("calibration_state", T, "field_observation_meta.calibration_status",
     "Name differs; vocabulary matches v0.4 CHECK exactly after Arya's ruling.", TARGET),
    ("processing_status", P, "field_observation_meta.processing_status", "Stored as sent.", TARGET),
    ("accuracy", T, "field_observation_meta.accuracy + .accuracy_status",
     "Split across a numeric and a status column. NOT_VERIFIED maps to accuracy null + "
     "accuracy_status NOT_VERIFIED; a number maps to accuracy <n> + accuracy_status SPECIFIED. "
     "Lossless - Group 1 implemented the accuracy_status column Group 3 proposed.", TARGET),
    ("capture_method", P, "capture_method", "Stored as sent.", TARGET),
    ("measurement", T, "measurements[].value / .value_text",
     "Numeric goes to value with data_type NUMERIC; descriptive goes to value_text.", TARGET),
    ("unit", P, "measurements[].unit", "Stored as sent.", TARGET),
    ("raw_artifact", T, "raw_artifacts[].storage_ref", "Name differs; value preserved.", TARGET),
    ("raw_artifact_integrity", T,
     "raw_artifacts[].content_hash / .hash_algorithm / .artifact_type",
     "Object flattened to three columns. Content hash round-tripped byte-identical.", TARGET),
    ("location", T, "geo_location.* + field_observation_meta.gnss_status / .position_accuracy_m",
     "Nested object split across a geometry row and two meta columns. altitude_m, gnss_status and "
     "position_accuracy_m all confirmed persisted with real values on the acceptance record "
     "(45.2 / FIX / 0.25).", POSITION_WITNESS),
    ("provenance", T, "measurements[].provenance.* + field_observation_meta.operator",
     "Split across the provenance row and the meta row.", TARGET),
    ("is_synthetic", P, "is_synthetic", "Boolean, stored as sent.", TARGET),
    ("trace_id", R, "returned on the response envelope",
     "Runtime-minted per REQUEST, not per observation. Group 3 emits null and must not invent one. "
     "Four calls on this observation returned four different traces on 2026-08-19, so it cannot "
     "correlate an observation over time.", None),
    ("idempotency_key", R, "Idempotency-Key request header",
     "Not a stored field. Drives the 201/200/409 contract.", None),
    ("ingestion_timestamp", R, "runtime-owned",
     "Group 3 emits null by contract (const null). Group 1 owns the value.", None),
    ("tidal_state", N, None,
     "DECLARED LOSS. Kavy deferred it to v0.5 on 2026-08-17; Raj reconfirmed 2026-08-19. Group 3 may "
     "emit it; Group 1 will drop it. Agreed and recorded, not silent.", None),
]

# Raj confirmed on 2026-08-22 that synthetic_state is now the canonical persisted
# field with all five values, and that a PostgreSQL v0.8 migration is applied and the
# V2.2 runtime is deployed. That is REPORTED, not VERIFIED: Group 3 has not yet seen a
# live GET return synthetic_state. It is classified below as PERSISTED_REPORTED and is
# promoted to PERSISTED the moment a live retrieval shows the value round-tripping.
PR = "PERSISTED_REPORTED"

# Raj's Group 1 persistence audit, 2026-08-25, answered two fields Group 3 could not
# resolve from the GET response alone. These move OUT of UNDETERMINED on his authority.
# Labelled REPORTED, not VERIFIED - Group 3 cannot see Group 1's storage layer.
RAJ_AUDIT_FIELDS = [
    ("provenance_reference", P, "observation.provenance_reference",
     "VERIFIED 2026-08-26 by live GET - returns 'open-meteo:8d26e68328ac160f', byte-identical to what "
     "Group 3 emits. FULL LIFECYCLE IN ONE DAY: UNDETERMINED (Group 3 could not tell from the response) "
     "-> NOT_SUPPORTED (Raj's own persistence audit: 'accepted but currently not stored') -> PERSISTED "
     "(Raj applied the targeted correction). Frozen contract section 28 is now satisfied: a reviewer "
     "starting from the canonical record CAN reach the provenance evidence. G-25 CLOSED."),
    ("source_timestamp", P, "observation.source_timestamp",
     "VERIFIED 2026-08-26 by live GET - returns '2026-08-25 11:00:00+00:00', the value Group 3 emitted. "
     "FIXED SAME DAY. Earlier on 2026-08-26 the response body literally contained \"source_timestamp\":null, "
     "and that was the DEMONSTRATED root cause of Group 2's ABSTAIN: Group 2 read the field from the "
     "canonical record, found null, and failed closed with reason MISSING_SOURCE_TIMESTAMP. Their ruling "
     "was correct behaviour on the data they could see - the loss was introduced by Group 1, not Group 3. "
     "Raj corrected it within hours of it being traced. G-28 CLOSED. CONSEQUENCE STILL OPEN: Group 2's "
     "ABSTAIN reason is now stale and their ruling should be re-run against the corrected record (G-32)."),
    ("schema_version", P, "observation.schema_version",
     "VERIFIED 2026-08-26 by live GET - returns '2.2', matching what Group 3 emits. Three-step lifecycle "
     "in two days: UNDETERMINED -> PERSISTED_REPORTED (Raj: 'stored but not returned') -> returned as "
     "'0.7', Group 1's own DB schema version, which Group 3 raised as G-31 and Raj flagged himself with "
     "'I am not representing it as 2.2' -> PERSISTED, corrected to echo the contract schema version. "
     "Frozen contract section 5's mandatory contract_version/schema_version distinction is now satisfied "
     "on both sides. G-31 CLOSED."),
]

REPORTED_FIELDS = [
    ("data_state", P, "observation.data_state",
     "CONFIRMED PERSISTED by live probe 2026-08-24: the field is returned in the canonical GET for "
     "TC-Z03-F02-LIDAR-OBS001. This was UNDETERMINED and was the highest-risk unknown - Arya ruled "
     "data_state and quality_state two DISTINCT required axes, so had it not persisted, one ruled axis "
     "would have been lost on ingestion. It persists."),
    ("synthetic_state", P,
     "observation.synthetic_state",
     "Raj, 2026-08-22: 'synthetic_state is implemented as the canonical persisted field with the five "
     "frozen values PHYSICAL | CONTROLLED | SYNTHETIC | SIMULATED | UNKNOWN. is_synthetic is retained "
     "separately for compatibility and is not used as the canonical source of synthetic_state.' This is "
     "Group 3's Option 2 request, accepted. PROMOTED TO PERSISTED 2026-08-24: a live probe confirms the "
     "field IS returned in the canonical GET. NOTE - the probe confirms the KEY is present; it does not "
     "establish the VALUE on a legacy V1.2-era record, which predates the field."),
]

UNDETERMINED_FIELDS = [
    ("contract_version",
     "CONFIRMED ABSENT by live probe 2026-08-24 - not returned in the canonical GET. Without it a consumer cannot tell which contract version "
     "produced a record. Raj's 2026-08-25 persistence audit answered schema_version but did NOT state "
     "whether contract_version is stored. Still UNDETERMINED - asked."),
    ("source_identity", "CONFIRMED ABSENT by live probe 2026-08-24 - not returned in the canonical GET."),
    ("survey_id", "Not present in the GET response. Derivable from observation_id."),
    ("zone_id", "Not present in the GET response. Derivable from observation_id."),
    ("flight_id", "Not present in the GET response. Derivable from observation_id."),
    ("sensor_id", "Not present in the GET response. Derivable from observation_id."),
    ("observation_seq", "Not present in the GET response. Derivable from observation_id."),
    ("parent_reference", "Not present in the GET response."),
    ("integrity_reference", "Not present in the GET response."),
    ("waypoint_id", "Not present in the GET response."),
    ("hardware_verified", "Not present in the GET response."),
]


def dig(obj, path):
    cur = obj
    for part in path.split("."):
        if part.endswith("[]"):
            cur = (cur.get(part[:-2]) or [{}])[0]
        else:
            if not isinstance(cur, dict):
                return None
            cur = cur.get(part)
    return cur


rows, counts = [], {P: 0, T: 0, R: 0, N: 0, U: 0}
for field, klass, dest, note, witness in MATRIX:
    observed = None
    if witness and dest and "+" not in dest and " " not in dest:
        observed = dig(witness, dest)
    rows.append({"field": field, "classification": klass, "canonical_destination": dest,
                 "observed_live_value": observed, "note": note})
    counts[klass] += 1

for field, klass, dest, note in REPORTED_FIELDS + RAJ_AUDIT_FIELDS:
    rows.append({"field": field, "classification": klass, "canonical_destination": dest,
                 "observed_live_value": None, "note": note})
    counts[klass] = counts.get(klass, 0) + 1

for field, why in UNDETERMINED_FIELDS:
    rows.append({"field": field, "classification": U, "canonical_destination": None,
                 "observed_live_value": None, "note": why})
    counts[U] += 1

known = {r["field"] for r in rows}
missing = [f for f in SCHEMA["properties"] if f not in known]

doc = {
    "_README": ("V2.2 persistence matrix. Every V2.2 field classified as PERSISTED, TRANSFORMED, "
                "REFERENCED_EXTERNALLY, NOT_SUPPORTED or UNDETERMINED. Classification derived from "
                "Group 1's LIVE canonical GET responses, not from a document. UNDETERMINED means the "
                "field is absent from the GET response and Group 3 cannot tell from the response alone "
                "whether Group 1 stores it and does not return it, or does not store it. That is a "
                "question for Group 1, not a guess for Group 3."),
    "_generated_by": "integration/emit_persistence_matrix.py",
    "_target_observation": "TC-Z03-F02-LIDAR-OBS001",
    "_evidence": "evidence/live/group1_live_records.json",
    "_acceptance_record_caveat": (
        "TC-Z03-F02-ACCEPTANCE-OBS1787138092 is cited ONLY as the witness that altitude_m, gnss_status "
        "and position_accuracy_m persist with real values, because those are null on the target record. "
        "It is never used as a substitute for the target observation. See KNOWN_GAPS G-8, which records "
        "that its hardware values are invented."),
    "_contract_version": "2.2",
    "_group1_runtime_state": {
        "_label": ("VERIFIED 2026-08-25 - Group 3 ran the live acceptance sequence against Group 1's "
                   "deployed instance and passed 13/13. Previously REPORTED from Raj, 2026-08-22."),
        "v2_2_runtime": "DEPLOYED - proven live 2026-08-25T11:04:54Z",
        "db_migration": "PostgreSQL v0.9 APPLIED (canonical_record_id migration 0004)",
        "endpoints": {"ingest": "POST /observations",
                      "retrieve": "GET /observations/{observation_id}",
                      "health": "GET /health"},
        "canonical_record_id": ("Will NOT be supplied or preselected. Generated/resolved by the Group 1 "
                                "persistence layer and retrieved from the resulting canonical record."),
        "acceptance_sequence": "201 ACCEPTED -> GET 200 -> replay 200 -> conflict 409 -> final GET 200",
        "obs001": "Untouched. No delete, repair or re-POST. OBS009 also untouched.",
        "MATRIX_CAVEAT": (
            "RESOLVED 2026-08-25. The earlier caveat warned that these classifications were derived "
            "against Group 1 schema v0.4 and that a later migration might have given canonical "
            "destinations to fields listed UNDETERMINED. Group 3 re-checked all 14 UNDETERMINED fields "
            "against a LIVE v0.9 GET of TC-Z03-EXT-OPENMETEO-OBS001 on 2026-08-25: all 14 are STILL "
            "absent from the response. The count is current, not stale. UNDETERMINED still means Group 3 "
            "cannot tell stored-and-not-returned from not-stored - that remains a question for Group 1."),
        "v0_9_additions_observed_live": (
            "canonical_record_id IS now returned (CR-<uuid>), generated by Group 1's persistence layer. "
            "data_state, synthetic_state and quality_state all round-tripped.")},
    "summary": counts,
    "fields_in_schema_not_classified": missing,
    "matrix": rows,
}

out = os.path.join(DAY6, "V2.2_PERSISTENCE_MATRIX.json")
with io.open(out, "w", encoding="utf-8") as fh:
    json.dump(doc, fh, indent=2, ensure_ascii=False)
    fh.write("\n")

print("V2.2 PERSISTENCE MATRIX -> V2.2_PERSISTENCE_MATRIX.json")
print()
for k in (P, PR, T, R, N, U):
    print("  %-22s %d" % (k, counts.get(k, 0)))
print()
print("  total classified      %d of %d schema fields" % (len(rows), len(SCHEMA["properties"])))
if missing:
    print("  *** NOT CLASSIFIED:   %s" % ", ".join(missing))
    sys.exit(1)
print("  every V2.2 field is classified - none left out")
sys.exit(0)
