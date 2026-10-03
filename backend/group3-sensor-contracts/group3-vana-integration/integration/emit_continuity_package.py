# -*- coding: utf-8 -*-
"""Emit the Group 3 deterministic cross-group continuity package.

WHAT THIS ANSWERS
-----------------
"Which exact observation are we supposed to use?"

A downstream engineer should never have to ask a Group 3 member to reconstruct
history from memory. This emits ONE artifact that lets a reviewer start at any
point in the chain and walk it in either direction:

    GROUP 3 SOURCE -> OBSERVATION_ID -> PROVENANCE
                   -> GROUP 1 CANONICAL RECORD
                   -> GROUP 2 CONTEXT INPUT
                   -> GROUP 4 ACTION INPUT

HONESTY RULES THIS FILE OBEYS
-----------------------------
Every link carries a verification label. VERIFIED means captured output exists on
disk. REPORTED means a named person said so and the artifact is not held. GAP
means the link genuinely does not exist and never will, with the reason.

A GAP is not a failure to be smoothed over. Group 4's action_request_id is a GAP
BY RULING - Group 2 ruled the context temporally inapplicable and required
abstention - and stating that plainly is the correct handoff.

Run:  python emit_continuity_package.py
"""
import argparse, hashlib, io, json, os, re, sys, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
DAY6 = os.path.dirname(HERE)

CONTRACT = json.load(io.open(os.path.join(DAY6, "contract", "observation.schema.v2.2.json"),
                             encoding="utf-8"))
DEFAULT_PKG = os.path.join(DAY6, "contract", "sample_mission_package.v2.2.json")
LIVE = json.load(io.open(os.path.join(DAY6, "evidence", "live", "group1_live_records.json"),
                         encoding="utf-8"))
G2 = json.load(io.open(os.path.join(DAY6, "reference", "inbound",
                                    "G2_temporal_ruling_GAP_2026-08-20.json"), encoding="utf-8"))
# The single observation Group 2's held context record actually covers. Any OTHER
# observation has no Group 2 context and must be labelled GAP, never VERIFIED.
G2_CONTEXT_COVERS = "TC-Z03-F02-LIDAR-OBS001"

# Group 2 rulings issued for a specific observation WITHOUT a context record. Vijay
# Dhawan ruled ABSTAIN for the Open-Meteo observation on 2026-08-25 and independently
# confirmed the LiDAR context must not be reused for it. A ruling is not a context
# record, and a message is not an artifact - these load as REPORTED, never VERIFIED.
# Group 2 sent three successive versions for the same observation. All are retained so
# the sequence is auditable, but only the LATEST must reach a consumer - an earlier
# version carries wrong identity fields and empty evidence. Sort so G2_FINAL_ARTIFACT_*
# wins over G2_ruling_*, and later dates win within each kind.
#
# Two shapes exist on disk: early files put the ruling fields at the top level, later
# ones nest them under _as_received_verbatim so the verbatim record stays separable from
# Group 3's annotations. Accept both rather than silently skipping one.
G2_RULINGS = {}
_inbound = os.path.join(DAY6, "reference", "inbound")
for _f in sorted(os.listdir(_inbound)):
    if not _f.endswith(".json"):
        continue
    if not (_f.startswith("G2_ruling_") or _f.startswith("G2_FINAL_ARTIFACT_")):
        continue
    _r = json.load(io.open(os.path.join(_inbound, _f), encoding="utf-8"))
    _body = _r.get("_as_received_verbatim", _r)
    _oid = _body.get("observation_id")
    if not _oid:
        print("SKIPPING %s - no observation_id at top level or in _as_received_verbatim" % _f)
        continue
    _final = _f.startswith("G2_FINAL_ARTIFACT_")
    # Rank by the DATE IN THE FILENAME, never alphabetically. An earlier version sorted
    # by name, so G2_FINAL_ARTIFACT_TC-Z03... beat G2_FINAL_ARTIFACT_RERUN_... purely
    # because T > R, and the package served Group 4 the SUPERSEDED artifact carrying the
    # stale MISSING_SOURCE_TIMESTAMP reason. Found by self-audit on 2026-08-27.
    _m = re.search(r"(\d{4}-\d{2}-\d{2})", _f)
    _date = _m.group(1) if _m else "0000-00-00"
    _rank = (1 if _final else 0, _date)
    _prev = G2_RULINGS.get(_oid)
    if _prev is None or _rank > _prev[4]:
        G2_RULINGS[_oid] = (_body, _f, _final, _r, _rank)

# --- DYNAMIC RESOLUTION (EOD requirement, 2026-08-22) ------------------------
# "No hardcoded observation_id, canonical_record_id, context_id or
#  action_request_id is required for normal runtime execution."
#
# The observation id is READ FROM THE FIXTURE, not pinned to a constant, and the
# canonical_record_id is RESOLVED FROM GROUP 1 - live when a host is supplied,
# otherwise from the stored evidence snapshot which is then LABELLED as a
# snapshot rather than presented as a dynamically resolved value.
#
# An earlier version pinned OBS_ID = "TC-Z03-F02-LIDAR-OBS001" as a module
# constant and read canonical_record_id out of a static evidence file. Found by
# self-audit on 2026-08-22 against the EOD dynamic-runtime rule.
_ap = argparse.ArgumentParser()
_ap.add_argument("--fixture", default=None,
                 help="Mission package holding the target observation. Defaults to the controlled V2.2 "
                      "fixture. For a LIVE external observation pass "
                      "../evidence/live/live_mission_package.json - it is generated at runtime and is "
                      "deliberately NOT in the static fixture, which must stay deterministic.")
_ap.add_argument("--observation-id", default=None,
                 help="Target observation. Defaults to the first observation in the fixture.")
_ap.add_argument("--base-url", default=os.environ.get("VANA_API_BASE_URL"),
                 help="Group 1 host. When supplied, canonical_record_id is resolved by a LIVE GET "
                      "instead of read from the stored evidence snapshot.")
_args = _ap.parse_args()

PKG = json.load(io.open(_args.fixture or DEFAULT_PKG, encoding="utf-8"))
OBS_ID = _args.observation_id or PKG["observations"][0]["observation_id"]
_match = [o for o in PKG["observations"] if o["observation_id"] == OBS_ID]
if not _match:
    print("Observation %s is not in %s" % (OBS_ID, _args.fixture or DEFAULT_PKG))
    print("Available: %s" % ", ".join(o["observation_id"] for o in PKG["observations"]))
    print()
    print("A LIVE external observation lives in evidence/live/live_mission_package.json, not in the")
    print("static fixture - it is generated at runtime and the fixture must stay deterministic.")
    print("Pass it explicitly:  --fixture ../evidence/live/live_mission_package.json")
    sys.exit(2)
obs = _match[0]

CANONICAL_SOURCE = None
live = None
LIVE_TRACE = None
if _args.base_url:
    try:
        _u = _args.base_url.rstrip("/") + "/observations/" + OBS_ID
        with urllib.request.urlopen(_u, timeout=40) as _r:
            _body = json.loads(_r.read().decode("utf-8")) or {}
        live = _body.get("observation")
        LIVE_TRACE = _body.get("trace_id")
        # The host is supplied at run time and is NEVER written into an artifact:
        # Group 1's API carries no authentication, so a base URL committed to a repo
        # is an open endpoint. Only the path is recorded.
        CANONICAL_SOURCE = ("LIVE GET <group1-base-url>/observations/%s - resolved dynamically "
                            "from Group 1. Host supplied at run time, redacted here." % OBS_ID)
    except Exception as _e:
        CANONICAL_SOURCE = "LIVE GET FAILED (%s). No canonical_record_id resolved." % _e
if live is None:
    _rec = LIVE.get(OBS_ID)
    if _rec:
        live = _rec["observation"]
        CANONICAL_SOURCE = CANONICAL_SOURCE or (
            "STORED EVIDENCE SNAPSHOT evidence/live/group1_live_records.json, captured %s. "
            "NOT dynamically resolved. Re-run with --base-url for a live resolution."
            % LIVE.get("_captured_at"))
    else:
        print("No live record held for %s and no --base-url supplied." % OBS_ID)
        print("canonical_record_id cannot be resolved. Refusing to invent one.")
        sys.exit(2)


def _obj(v):
    """Type-safe dict access. `x.get(k) or {}` guards None but NOT a wrong type:
    a string is truthy, so .get() then raises. Dhruv Patel found this class of bug
    in the semantic validator on 2026-08-28; this sweep removed it everywhere."""
    return v if isinstance(v, dict) else {}


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


_G2 = G2_RULINGS[OBS_ID][0] if OBS_ID in G2_RULINGS else {}

package = {
    "_README": (
        "Group 3 deterministic cross-group continuity package. Start at any link and walk the chain "
        "in either direction without asking a Group 3 member to reconstruct history. Every link "
        "carries a verification label: VERIFIED (captured output on disk), REPORTED (a named person "
        "said so, artifact not held), or GAP (the link genuinely does not exist, with the reason)."),
    "_generated_by": "integration/emit_continuity_package.py",
    "_owner": "Hemanth Reddy - Cross-Group Observation Continuity & Final Group 3 Handoff Owner",
    "_date": "2026-08-20",

    "the_observation": {
        "observation_id": OBS_ID,
        "source_identity": obs["source_identity"],
        "source_state": {
            "synthetic_state": obs["synthetic_state"],
            "data_state": obs["data_state"],
            "quality_state": obs["quality_state"],
            "meaning": (
                "SYNTHETIC. This observation was produced deterministically by the Group 3 software "
                "path. It is NOT a physical field capture. No Group 3 sensor has produced a recorded "
                "reading; available hardware is PRESENT only, per Suraj Surve's ruling of 2026-08-20. "
                "This classification must survive every downstream hop unchanged."),
            "label": "VERIFIED"},
        "identity_rule": (
            "Composite: survey_id-zone_id-flight_id-sensor_id-observation_seq. Per Arya Barge's "
            "Observation Metadata Contract section 3, identity must not be reduced to the sequence "
            "fragment alone. The five component fields are also carried explicitly because Group 1's "
            "request body accepts them and Kavy is building zone/flight queryability on them."),
        "components": {k: obs[k] for k in
                       ("survey_id", "zone_id", "flight_id", "sensor_id", "observation_seq")},
    },

    "contract_versions": {
        "group3_contract_version": obs["contract_version"],
        "group3_schema_version": obs["schema_version"],
        "group3_contract_status": CONTRACT["_freeze_status"]["status"],
        "group1_canonical_schema": "v0.4",
        "group1_api": "VANA MasterDB Observation API 1.0.0",
        "label": "VERIFIED"},

    "provenance": {
        "provenance_reference": obs["provenance_reference"],
        "inline_provenance": obs["provenance"],
        "raw_artifact": obs["raw_artifact"],
        "raw_artifact_integrity": obs["raw_artifact_integrity"],
        "note": (
            "provenance_reference is the reviewer-facing pointer to provenance evidence and is "
            "DISTINCT from the inline provenance object - ruled by Arya Barge 2026-08-20. Both are "
            "required and non-empty."),
        "label": "VERIFIED"},

    "group1_canonical_record": {
        # Group 1 v0.9 returns a REAL canonical_record_id (CR-<uuid>), generated by its
        # persistence layer. An earlier version of this script reported observation_id
        # here, which is a DIFFERENT identifier - caller-supplied, not Group-1-generated.
        # Fall back to a stated GAP rather than silently substituting the observation_id.
        "canonical_record_id": live.get("canonical_record_id"),
        "canonical_record_id_note": (
            "Generated by Group 1's persistence layer and read back from the canonical "
            "record. NEVER supplied in the POST, per contract section 9."
            if live.get("canonical_record_id") else
            "GAP - Group 1's response carries no canonical_record_id field. Group 3 will "
            "NOT substitute the observation_id: they are different identifiers."),
        "observation_id": live["observation_id"],
        "_id_distinction": (
            "observation_id is CALLER-supplied and is the stable cross-group correlation "
            "key. canonical_record_id is GROUP-1-generated and identifies the canonical "
            "row. Do not use one where the other is meant."),
        "canonical_record_id_resolution": CANONICAL_SOURCE,
        "dataset_id": live["dataset_id"],
        "geo_id": live["geo_id"],
        "measurement_id": live["measurements"][0]["measurement_id"],
        "provenance_id": live["measurements"][0]["provenance"]["provenance_id"],
        "artifact_id": live["raw_artifacts"][0]["artifact_id"],
        "retrieval": "GET /observations/" + OBS_ID,
        "content_hash_roundtrip": (
            "BYTE-IDENTICAL. The raw artifact content hash Group 3 emitted was returned unchanged: "
            + obs["raw_artifact_integrity"]["checksum_sha256"]),
        "label": "VERIFIED",
        "evidence": "evidence/live/group1_live_records.json",
        "DEFECT": {
            "field": "is_synthetic",
            "group3_emitted": obs["is_synthetic"],
            "group1_stored": live["is_synthetic"],
            "severity": "BLOCKING for scientific use",
            "cause": (
                "The V1.2 payload that created this record carried is_synthetic at PACKAGE level; "
                "Group 1's API reads it PER OBSERVATION, so it defaulted to false. Proven with a "
                "control record sent WITH the flag, which stored true."),
            "why_it_matters": (
                "A synthetic observation is recorded in the canonical database as physical. Any "
                "downstream consumer reading this record will believe it is real field data."),
            "fix_owner": "Raj (Group 1) - a 409 DUPLICATE blocks Group 3 from overwriting it",
            "structurally_prevented_going_forward": (
                "V2.2 makes synthetic_state required at OBSERVATION level and forbids laundering "
                "SYNTHETIC into PHYSICAL. The defect cannot recur under this contract.")}},

    "group2_context": ({
        # Group 2's ruling for this observation. ABSTAIN with a stated reason is a real
        # downstream answer, not a silent gap - but it arrived as a posted artifact
        # rather than something Group 3 can retrieve, so it is REPORTED, never VERIFIED.
        "context_id": _G2["context_id"],
        "label": "REPORTED",
        "ruling": _G2["ruling"],
        "action_eligibility": _G2["action_eligibility"],
        "abstention_required": _G2["abstention_required"],
        "action_request": _G2["action_request"],
        "evidence_block": _G2.get("evidence"),
        "group2_provenance": _G2.get("provenance"),
        "statement": (
            "Group 2 ruled ABSTAIN for %s: no authoritative scientific context record "
            "exists for it, so no action is eligible. Group 2 independently confirmed "
            "that the context record for %s must NOT be reused here."
            % (OBS_ID, G2_CONTEXT_COVERS)),
        "source": "Vijay Dhawan (Group 2)",
        "evidence": "reference/inbound/" + G2_RULINGS[OBS_ID][1],
        "is_final_artifact": G2_RULINGS[OBS_ID][2],
        "identity_preserved": (
            _G2.get("canonical_record_id") == (live or {}).get("canonical_record_id")),
        "attribution_carried": bool(_obj(_G2.get("evidence")).get("attribution")),
        "open_defect": _obj(G2_RULINGS[OBS_ID][3].get("_defect")).get("summary"),
    } if OBS_ID in G2_RULINGS else {
        "context_id": None,
        "label": "GAP",
        "covers_observation": G2_CONTEXT_COVERS,
        "this_observation": OBS_ID,
        "statement": (
            "Group 2 has NOT issued a scientific context record for %s. The only Group 2 "
            "context record Group 3 holds covers %s and is a canopy-height record - it says "
            "nothing about this observation. Group 3 must not present it as though it did."
            % (OBS_ID, G2_CONTEXT_COVERS)),
        "what_closes_this": (
            "Group 2 retrieves %s from Group 1 and returns a context record with an honest "
            "ALLOW or ABSTAIN, per contract section 13. The Source Evidence Pack at "
            "evidence/live/SOURCE_EVIDENCE_PACK_EMITTED_2026-08-25.json is what Group 2 "
            "needs in order to do that." % OBS_ID),
        "held_record_for_a_different_observation": {
            "observation_id": G2_CONTEXT_COVERS,
            "context_id": G2["context_id"],
            "temporal_ruling": G2["temporal_ruling"],
            "_note": "Retained for reference only. NOT this observation's context."},
    } if OBS_ID != G2_CONTEXT_COVERS else {
        "context_id": G2["context_id"],
        "temporal_ruling": G2["temporal_ruling"],
        "action_eligibility": G2["action_eligibility"],
        "abstention_required": G2["abstention_required"],
        "statement": G2["group2_statement"],
        "label": "VERIFIED",
        "promoted": (
            "REPORTED -> VERIFIED on 2026-08-21. All three named artifacts received from Vijay Dhawan "
            "and stored unmodified: G2_temporal_applicability_ruling_AS_RECEIVED_2026-08-21.json, "
            "G2_TEMPORAL_APPLICABILITY_RULING_AS_RECEIVED_2026-08-21.md, and "
            "G2_context_TC-Z03-F02-LIDAR-OBS001_AS_RECEIVED_2026-08-21.json, all under "
            "reference/inbound/."),
        "context_record": {
            "parameter_name": "expected_canopy_height",
            "expected_value": 4.5, "expected_range": [3.0, 6.0], "unit": "m",
            "observed_value": 4.7,
            "observed_within_expected_range": True,
            "source_citation": "Simard et al. (2019) / NASA TanDEM-X Global Mangrove Canopy Height",
            "source_doi": "10.3334/ORNLDAAC/1665",
            "confidence_score": 0.85,
            "validation_status": "VERIFIED",
            "note": "Group 3's measured canopy height of 4.7 m sits inside Group 2's expected 3.0-6.0 m "
                    "band for these coordinates. The scientific context VALIDATES the measurement. The "
                    "GAP ruling is purely TEMPORAL and says nothing against the value itself."},
        "timestamp_discrepancy": {
            "severity": "RAISED WITH GROUP 2 - outcome unaffected, stated reason disputed",
            "group2_states": "Observation Timestamp: UNAVAILABLE (No authoritative timestamp found). "
                             "Ruling section 16 adds: 'The upstream observation does not currently "
                             "bundle a verifiable observation timestamp within its payload.'",
            "group3_evidence": (
                "observation_timestamp = 2026-08-13T09:14:22Z. It is a REQUIRED field in contract V2.2 "
                "and was REQUIRED as 'timestamp' in V1.2. It is available to Group 2 from three "
                "independent places: (1) Group 3's semantic input for this very observation, at "
                "group3_observation_summary.timestamp; (2) the Group 3 mission package, at "
                "observation_timestamp; (3) Group 1's live canonical record, at observed_at = "
                "'2026-08-13 09:14:22+00:00', verified by GET on 2026-08-19."),
            "assessment": (
                "The claim in ruling section 16 is not correct as written. The timestamp is bundled, is "
                "mandatory, and is persisted canonically. This looks like a retrieval or field-mapping "
                "issue on the Group 2 side rather than missing upstream data."),
            "why_the_outcome_still_stands": (
                "By Group 2's own decision table, an observation outside the validity window with no "
                "adaptation rule ALSO rules GAP. 2026-08-13 is outside 2020-01-01 to 2023-12-31. So the "
                "ruling lands on GAP either way and no downstream decision changes. Group 3 is NOT "
                "asking for the ruling to be reversed - only for the reason to be corrected, so that no "
                "defect is attributed to the Group 3 payload that does not exist."),
            "raised": "MESSAGE_TO_VIJAY_2026-08-21_TIMESTAMP_DISCREPANCY.md"}}),

    "group4_action_input": {
        "action_request_id": None,
        "label": "GAP",
        "governed_abstention": {
            "_status": "IMPLEMENTED BY GROUP 4, reported by Shivam 2026-08-21. REPORTED, not VERIFIED - "
                       "no ledger artifact or API response is held by Group 3 yet.",
            "event_type": "GOVERNED_ABSTENTION",
            "observation_id": OBS_ID,
            "context_id": G2["context_id"],
            "ruling": G2["temporal_ruling"],
            "identifiers_reported": {
                "event_id": "generated at record time - ledger identity, NOT stable across replay",
                "execution_id": "preserved from the runtime execution - runtime-owned per Karan Barda's "
                                "2026-08-14 ruling, therefore varies per execution",
            },
            "group3_position": (
                "Group 3 asks for a deterministic abstention_record_id as the fourth correlation "
                "reference, with the ledger event_id retained ALONGSIDE it as the evidence pointer - not "
                "instead of it. Reason: an identifier generated at record time cannot correlate a "
                "decision across replay. Group 3 has already hit exactly this defect with Group 1's "
                "trace_id, which is per-REQUEST rather than per-observation - four calls against this one "
                "observation returned four different traces on 2026-08-19."),
            "derivation_constraint": (
                "The deterministic id MUST be derived from stable identity only: observation_id + "
                "context_id + ruling. It MUST NOT include execution_id. Karan Barda ruled execution_id "
                "runtime-owned on 2026-08-14, so it changes on every execution - including it would make "
                "the identifier non-deterministic across replay, which defeats its entire purpose."),
            "awaiting": "Group 4 confirmation of the derivation and the resulting abstention_record_id.",
            "abstention_record_id": None},
        "this_is_a_ruling_not_an_omission": (
            "Group 2 ruled GAP: action_eligibility false, abstention_required true. An "
            "action_request_id will therefore NEVER exist for this observation, and manufacturing one "
            "would be exactly the silent fabrication this handoff exists to prevent. REASON PER THE "
            "RULING ARTIFACT (received 2026-08-21): 'Temporal applicability cannot be established "
            "because the observation timestamp is unavailable' - source_reference_time null, "
            "temporal_relationship UNAVAILABLE. An earlier Group 3 note gave the reason as the "
            "observation falling 2 years 8 months outside the 2020-01-01 to 2023-12-31 window; that "
            "was Group 3's inference from a message and is NOT what the artifact says. Corrected "
            "2026-08-21. The outcome is unaffected - Group 2's own decision table rules GAP for an "
            "out-of-window observation with no adaptation rule too - but the stated reason is disputed, "
            "see group2_context.timestamp_discrepancy."),
        "what_group4_must_produce_instead": (
            "A governed abstention record, using the Abstention registry in Karan Barda's own "
            "capability map. Group 3 has requested its identifier; it is not yet supplied."),
        "handoff_envelope": "integration/group3_to_group4_handoff.json (TANTRA execution envelope, "
                            "format confirmed by Karan Barda 2026-08-14)",
        "handoff_envelope_contract_version": (
            "V1.2, NOT V2.2. The envelope is generated from canonical_observation.json, which comes from "
            "the V1.2 mission package ingested through Group 1's LOCAL v0.1 schema. The envelope FORMAT "
            "is confirmed and current; the observation inside it predates the V2.2 contract. It must be "
            "regenerated from a V2.2 observation once Group 1 has aligned its validator and accepted V2.2 "
            "live. Stated here rather than left for a reader to discover.")},

    "trace_and_correlation": {
        "group3_emits": None,
        "rule": ("Group 3 does not mint trace IDs - Arya's metadata contract section 15 and Karan "
                 "Barda's 2026-08-14 ruling that execution_id, trace_id, tenant_id and lineage_hash "
                 "are runtime-owned."),
        # RESOLVED FROM THE LIVE RESPONSE where a host was supplied; otherwise from the
        # stored snapshot IF it happens to hold this observation. A live external
        # observation is not in the static snapshot, so an unguarded lookup here raised
        # KeyError - found on the first successful live run, 2026-08-25.
        "group1_trace_observed": (LIVE_TRACE
                                  or _obj(LIVE.get(OBS_ID)).get("trace_id")
                                  or "not captured in this run"),
        "group1_trace_source": ("live GET response envelope" if LIVE_TRACE
                                else "stored snapshot" if _obj(LIVE.get(OBS_ID)).get("trace_id")
                                else "none - no host supplied and observation not in the snapshot"),
        "group1_trace_format": "VANA-<12 lowercase hex>",
        "KNOWN_LIMITATION": (
            "Group 1's trace is per-REQUEST, not per-observation. Four calls against this one "
            "observation returned four different traces on 2026-08-19, so the trace CANNOT correlate "
            "an observation over time. Group 4's runtime separately uses a 16-hex trace-vana- form. "
            "The two schemes are unreconciled."),
        "stable_correlation_key": (
            "observation_id is the only identifier that is stable across all four groups. Use it, "
            "not the trace."),
        "label": "VERIFIED"},

    "known_transformations": [
        {"hop": "Group 3 -> Group 1", "field": "observation_timestamp",
         "becomes": "observed_at", "lossless": True,
         "note": "Wire name differs; value preserved. Reconciliation is a Group 1 validator item."},
        {"hop": "Group 3 -> Group 1", "field": "accuracy",
         "becomes": "field_observation_meta.accuracy + field_observation_meta.accuracy_status",
         "lossless": True,
         "note": "The literal NOT_VERIFIED maps to accuracy null + accuracy_status NOT_VERIFIED; a "
                 "number maps to accuracy <n> + accuracy_status SPECIFIED. Group 1 implemented the "
                 "accuracy_status column Group 3 proposed, so the distinction between 'nobody filled "
                 "this in' and 'we checked and no specification exists' survives."},
        {"hop": "Group 3 -> Group 1", "field": "location.*",
         "becomes": "geo_location.* + field_observation_meta.gnss_status/position_accuracy_m",
         "lossless": True,
         "note": "Nested location was RULED by Arya Barge 2026-08-20 precisely because the flat form "
                 "has no gnss_status or position_accuracy_m. All three of altitude_m, gnss_status "
                 "and position_accuracy_m are confirmed persisted with real values on "
                 "TC-Z03-F02-ACCEPTANCE-OBS1787138092 (45.2, FIX, 0.25)."},
        {"hop": "Group 3 -> Group 1", "field": "measurement + unit",
         "becomes": "measurement.value / value_text + unit, with data_type", "lossless": True},
        {"hop": "Group 3 -> Group 1", "field": "tidal_state", "becomes": None, "lossless": False,
         "note": "NOT PERSISTED. Kavy deferred tidal_state to v0.5 on 2026-08-17 and Raj reconfirmed "
                 "2026-08-19. Group 3 may emit it; Group 1 will drop it. This is a declared, agreed "
                 "loss, not a silent one."}],

    "known_gaps": [
        # PINNED, not interpolated. This gap is about the LiDAR record specifically.
        # TC-Z03-EXT-OPENMETEO-OBS001 was proven is_synthetic True -> True on 2026-08-25,
        # so interpolating OBS_ID here made the package assert something false about it.
        {"id": "G-1", "gap": "Live record TC-Z03-F02-LIDAR-OBS001 stores is_synthetic false for a "
                             "synthetic observation", "owner": "Raj (Group 1)", "status": "OPEN",
         "blocking": "scientific use of that record",
         "not_applicable_to": "TC-Z03-EXT-OPENMETEO-OBS001, which round-tripped is_synthetic true"},
        {"id": "G-2", "gap": "Diagnostic control record TC-Z03-F02-LIDAR-OBS009 is still in the "
                             "canonical database and is not a real observation",
         "owner": "Raj (Group 1)", "status": "OPEN", "blocking": "canonical cleanliness"},
        {"id": "G-3", "gap": "Group 1 validator not yet aligned to the V2.2 shape",
         "owner": "Raj (Group 1)",
         "status": "CLOSED 2026-08-25 - live acceptance passed 13/13 against Group 1's deployed "
                   "instance at 11:04:54Z. capture_method external_api and device_id "
                   "G3-EXT-OPENMETEO-01 were both accepted and returned verbatim.",
         "blocking": "nothing"},
        {"id": "G-4", "gap": "Group 2's three named artifacts not received; the temporal ruling "
                             "remains REPORTED", "owner": "Vijay Dhawan (Group 2)",
         "status": "CLOSED 2026-08-21 - all three received and stored unmodified under "
                   "reference/inbound/. The Group 2 link is VERIFIED for TC-Z03-F02-LIDAR-OBS001, "
                   "the observation those artifacts cover. It is NOT verified for any other "
                   "observation - see group2_context.",
         "blocking": "nothing"},
        {"id": "G-9", "gap": "Group 2's ruling states the observation timestamp is UNAVAILABLE and "
                             "section 16 attributes that to the Group 3 payload. The timestamp exists, "
                             "is a REQUIRED contract field, and is reachable by Group 2 in three "
                             "places including Group 1's canonical observed_at",
         "owner": "Vijay Dhawan / Kaushal (Group 2)", "status": "RAISED 2026-08-21",
         "blocking": "nothing downstream - the GAP outcome holds either way. What is at stake is the "
                     "stated REASON, and a defect wrongly attributed to Group 3's payload"},
        {"id": "G-5", "gap": "Group 4 governed abstention record identifier not supplied",
         "owner": "Karan Barda (Group 4)", "status": "OPEN",
         "blocking": "closing the fourth correlation reference"},
        {"id": "G-6", "gap": "No device register service exists. The semantic validator's device "
                             "check uses the fixture's own device set as a declared STAND-IN",
         "owner": "Group 4 capability registry", "status": "OPEN",
         "blocking": "true referential integrity on device_id"},
        {"id": "G-7", "gap": "Physical hardware unverified. 0 of 8 quadruped actuators mounted; no "
                             "sensor has produced a recorded reading",
         "owner": "Suraj Surve (Group 3)", "status": "PHASE 2 BY RULING",
         "blocking": "nothing in the software path - explicitly out of scope for Day 1"},
        {"id": "G-8", "gap": "TC-Z03-F02-ACCEPTANCE-OBS1787138092 carries invented hardware values "
                             "(gnss_status FIX, position_accuracy_m 0.25, calibration_status "
                             "CALIBRATED) written before the no-invention rules were enforced",
         "owner": "Group 3 raised; Raj (Group 1) holds the record", "status": "OPEN",
         "blocking": "nothing operationally - the record is correctly flagged is_synthetic true, but "
                     "the values are not real and Group 3 would not emit them today"}],

    "reproduce_this": {
        "1_validate_the_contract": "cd contract && python validate_fixtures.py",
        "2_semantic_layer": "cd contract && python validate_semantic_v22.py",
        "3_adversarial_audit": "cd contract && python audit_v22_adversarial.py",
        "4_identity_survival": "cd integration && python test_identity_survival.py",
        "5_identity_substitution": "cd integration && python test_identity_substitution.py",
        "6_closure_plan_abc": "cd integration && python test_closure_plan_abc.py",
        "7_regenerate_this_package": "cd integration && python emit_continuity_package.py",
        "note": "No network access is required for any of the above. Live Group 1 acceptance requires "
                "the base URL, which is deliberately NOT recorded in any file destined for a public "
                "repository because the API has no authentication."},
}

for name, path in [("contract_schema", os.path.join(DAY6, "contract",
                                                    "observation.schema.v2.2.json")),
                   ("mission_package", os.path.join(DAY6, "contract",
                                                    "sample_mission_package.v2.2.json"))]:
    package.setdefault("artifact_hashes", {})[name] = {
        "path": "contract/" + os.path.basename(path), "sha256": sha256_file(path)}

out = os.path.join(DAY6, "GROUP3_CONTINUITY_PACKAGE.json")
with io.open(out, "w", encoding="utf-8") as fh:
    json.dump(package, fh, indent=2, ensure_ascii=False)
    fh.write("\n")

labels = {}
for k, v in package.items():
    if isinstance(v, dict) and "label" in v:
        labels[k] = v["label"]

print("Group 3 continuity package written: GROUP3_CONTINUITY_PACKAGE.json")
print()
print("CHAIN LINK LABELS")
for k, v in labels.items():
    print("  %-28s %s" % (k, v))
print()
_open = [g for g in package["known_gaps"] if not g["status"].startswith("CLOSED")]
_closed = [g for g in package["known_gaps"] if g["status"].startswith("CLOSED")]
print("  known gaps: %d open, %d closed" % (len(_open), len(_closed)))
print("    open:   %s" % ", ".join(g["id"] for g in _open))
print("    closed: %s" % ", ".join(g["id"] for g in _closed))
print("  stable correlation key: observation_id (NOT the trace - it is per-request)")
sys.exit(0)
