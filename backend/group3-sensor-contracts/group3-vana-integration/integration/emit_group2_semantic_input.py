# -*- coding: utf-8 -*-
"""Emit the Group 3 -> Group 2 semantic integration input.

Answers Sakshi Thakur's request (Group 2, Semantic Integration), 2026-08-14:

    "Please provide the Scientific Context input including parameter,
     source/source_id, citation, validation status, confidence, quality and
     uncertainty. Please clearly mark any GAP/UNKNOWN/NOT_VERIFIED fields.
     The acceptance requirement is that the final contextual result remains
     traceable to both the original observation_id and the scientific
     source/citation."

She asked for an artifact rather than a verbal confirmation, so this produces one.

THE OWNERSHIP SPLIT THAT MATTERS
--------------------------------
Of the seven fields requested, Group 3 owns four and Group 2 owns three:

    parameter          GROUP 3   canopy_height
    source_id          GROUP 3   the OBSERVATION source, not a literature source
    quality            GROUP 3   field QA verdict
    uncertainty        GROUP 3   expressed as NOT VERIFIED, not as a number

    citation           GROUP 2   scientific literature. Group 3 produces field
                                 observations; it has no literature citation.
    validation_status  GROUP 2   SCIENTIFIC validation - distinct from Group 3's
                                 quality_status, despite the similar name
    confidence         GROUP 2   Group 3's contract deliberately carries no
                                 confidence score

Group 2 has ALREADY produced its three: Kaushlendra's ScientificContextRecord
f47ac10b-58cc-4372-a567-0e02b2c3d479, which this file reads rather than restates.

WHY THE ACCEPTANCE CRITERION CANNOT BE MET TODAY
------------------------------------------------
"Traceable to the scientific source/citation" requires a citation that supports
the value. Group 2's own record reports validation_status GAP, confidence 0.0,
and states the cited source does not provide a canopy_height baseline. The chain
to observation_id is intact; the chain to a supporting citation does not exist yet.

Usage:
    python emit_group2_semantic_input.py
"""
import json, io, os, sys, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
DAY6 = os.path.dirname(HERE)
CANONICAL = os.path.join(HERE, "canonical_observation.json")
G2CONTEXT = os.path.join(DAY6, "handoff_bundle", "4_contextual_result_group2.json")
OUT = os.path.join(HERE, "group2_semantic_input.json")


def main():
    if not os.path.exists(CANONICAL):
        print("FAIL: run integration/emit_canonical_observation.py first.")
        return 2

    doc = json.load(io.open(CANONICAL, encoding="utf-8"))
    obs = doc["canonical_observation"]

    g2 = None
    if os.path.exists(G2CONTEXT):
        g2 = json.load(io.open(G2CONTEXT, encoding="utf-8"))

    requested = {
        "parameter": {
            "owner": "GROUP 3",
            "value": obs["measurement"]["parameter"],
            "measurement_value": obs["measurement"]["value"],
            "unit": obs["measurement"]["unit"],
            "status": "PROVIDED"
        },
        "source_id": {
            "owner": "GROUP 3",
            "value": obs["source"]["source_id"],
            "source_type": obs["source"]["source_type"],
            "is_synthetic": obs["source"]["is_synthetic"],
            "status": "PROVIDED",
            "important": (
                "This is the OBSERVATION source - which device/mission produced "
                "the reading. It is NOT a scientific literature source. Do not "
                "use it to satisfy the citation half of the acceptance criterion."
            )
        },
        "citation": {
            "owner": "GROUP 2",
            "value": (g2 or {}).get("source_citation"),
            "source_doi": (g2 or {}).get("source_doi"),
            "source_url": (g2 or {}).get("source_url"),
            "status": "GROUP 2 FIELD - see data-quality flags below",
            "group3_position": (
                "Group 3 produces field observations and holds NO scientific "
                "literature citation. Supplying one would be fabrication."
            )
        },
        "validation_status": {
            "owner": "GROUP 2 (scientific) / GROUP 3 (field QA)",
            "group2_scientific_validation": (g2 or {}).get("validation_status"),
            "group3_field_qa": obs["quality_status"],
            "status": "BOTH PROVIDED",
            "important": (
                "TWO DIFFERENT FIELDS WITH SIMILAR NAMES. Group 3's "
                "quality_status=VALIDATED means the field QA passed. Group 2's "
                "validation_status=GAP means no scientific baseline exists. "
                "Both are true simultaneously. Do not collapse them."
            )
        },
        "confidence": {
            "owner": "GROUP 2",
            "value": (g2 or {}).get("confidence_score"),
            "status": "GROUP 2 FIELD",
            "group3_position": (
                "Group 3's contract carries NO confidence score by design. A "
                "confidence number for an uncalibrated sensor would be invented."
            )
        },
        "quality": {
            "owner": "GROUP 3",
            "value": obs["quality_status"],
            "vocabulary": ["RAW", "CAPTURED", "VALIDATED", "REJECTED",
                           "UNCERTAIN", "INGESTED"],
            "status": "PROVIDED",
            "meaning": "Field QA verdict on the observation itself."
        },
        "uncertainty": {
            "owner": "GROUP 3",
            "accuracy": obs["measurement"]["accuracy"],
            "calibration_status": obs["measurement"]["calibration_status"],
            "numeric_uncertainty": None,
            "status": "NOT_VERIFIED",
            "important": (
                "There is NO numeric uncertainty figure. No Group 3 sensor has a "
                "stated accuracy specification and no device holds a calibration "
                "record, so 'NOT VERIFIED' is the honest literal. It is not a "
                "placeholder and must not be substituted with a plausible number. "
                "Group 3 also encodes uncertainty structurally: an observation with "
                "no GNSS fix carries quality_status=UNCERTAIN rather than a "
                "defaulted coordinate."
            )
        }
    }

    gaps = {
        "GAP": [
            "citation - no scientific source supports a canopy_height baseline "
            "at this location (Group 2's own finding)",
            "confidence - 0.0, because no baseline exists to compare against",
            "scientific validation_status - GAP"
        ],
        "NOT_VERIFIED": [
            "accuracy - no sensor accuracy specification exists",
            "calibration_status - no device holds a calibration record",
            "all physical hardware - 0 of 8 actuators mounted, no sensor has "
            "produced a recorded reading"
        ],
        "UNKNOWN": [
            "spatial applicability (location_polygon) - empty in Group 2's record",
            "temporal applicability (valid_from / valid_to) - null in Group 2's record"
        ],
        "SYNTHETIC": [
            "the observation itself - is_synthetic: true, source_type "
            "SYNTHETIC_TEST. The value 4.7 m is illustrative and exists to prove "
            "the system path, not hardware readiness."
        ]
    }

    traceability = {
        "requirement": (
            "final contextual result remains traceable to BOTH the original "
            "observation_id AND the scientific source/citation"
        ),
        "leg_1_observation_id": {
            "chain": [
                "fixture: TC-Z03-F02-LIDAR-OBS001",
                "Group 1 canonical record: observation.observation_id = "
                "TC-Z03-F02-LIDAR-OBS001 (primary key, preserved verbatim)",
                "Group 2 context record: observation_id = TC-Z03-F02-LIDAR-OBS001",
                "Group 4 envelope: replay.idempotency_key = TC-Z03-F02-LIDAR-OBS001"
            ],
            "status": "SATISFIED - the identifier is unchanged at every hop",
            "note": (
                "Identity is the whole tuple - Survey+Zone+Flight+Sensor+Sequence "
                "PLUS coordinates and timestamp. OBS001 alone repeats every flight."
            )
        },
        "leg_2_scientific_citation": {
            "status": "NOT SATISFIABLE TODAY",
            "why": (
                "Traceability to a citation requires a citation that supports the "
                "value. Group 2's record reports validation_status GAP, confidence "
                "0.0, and states that canopy_height is unsupported by the current "
                "science model with no verified baseline for this bounding box. "
                "There is no supporting citation to trace to."
            ),
            "this_is_not_a_missing_artifact": (
                "Every artifact exists. The science does not. Marking this "
                "dependency CLOSED would record a traceability chain that does "
                "not hold."
            ),
            "recommended_disposition": (
                "Record leg 1 SATISFIED and leg 2 GAP, with Group 2's own "
                "validation_evidence as the reason. That is an honest closure."
            )
        }
    }

    citation_flags = []
    if g2:
        doi = g2.get("source_doi")
        cit = g2.get("source_citation")
        if doi and not str(doi).startswith("10."):
            citation_flags.append(
                "source_doi = %r is not a DOI. A DOI has the form 10.xxxx/yyyy. "
                "This appears to be a title in a DOI field." % doi)
        if cit and g2.get("source_url") in (None, ""):
            citation_flags.append(
                "source_citation = %r names a platform and publisher but has no "
                "author, title or retrievable identifier, and source_url is null. "
                "Nobody can retrieve it." % cit)
        if g2.get("validation_status") == "GAP" and cit:
            citation_flags.append(
                "A citation is populated on a record whose value is null and whose "
                "validation_status is GAP. Group 2's own explanation states the "
                "source does not provide a canopy_height baseline. A citation that "
                "supports nothing implies support that does not exist - null would "
                "be the honest value.")

    out = {
        "_README": (
            "Group 3 -> Group 2 semantic integration input for "
            "TC-Z03-F02-LIDAR-OBS001. Answers the seven requested fields, marks "
            "ownership per field, and states explicitly which half of the "
            "acceptance criterion can be satisfied today."
        ),
        "observation_id": obs["observation_id"],
        "context_id": (g2 or {}).get("context_id"),
        "_ownership_note": (
            "Of the seven fields requested from Group 3, three are Group 2's own "
            "outputs - citation, confidence and scientific validation_status. "
            "Group 2 has already produced them in ScientificContextRecord %s "
            "(Kaushlendra). They are echoed here for completeness, not authored "
            "by Group 3." % ((g2 or {}).get("context_id") or "<not found>")
        ),
        "requested_fields": requested,
        "explicit_gap_marking": gaps,
        "traceability": traceability,
        "citation_data_quality_flags": citation_flags or [
            "Group 2 context record not found alongside this script - flags not computed."],
        "group3_observation_summary": {
            "observation_id": obs["observation_id"],
            "device_id": obs["device_id"],
            "timestamp": obs["observed_at"],
            "latitude": obs["location"]["latitude"],
            "longitude": obs["location"]["longitude"],
            "crs": obs["location"]["crs"],
            "parameter": obs["measurement"]["parameter"],
            "value": obs["measurement"]["value"],
            "unit": obs["measurement"]["unit"],
            "quality_status": obs["quality_status"],
            "accuracy": obs["measurement"]["accuracy"],
            "calibration_status": obs["measurement"]["calibration_status"],
            "source_id": obs["source"]["source_id"],
            "is_synthetic": obs["source"]["is_synthetic"],
            "raw_artifact": obs["raw_artifact"]["reference"],
            "raw_artifact_sha256": obs["raw_artifact"]["sha256"],
            "provenance_id": obs["provenance"]["provenance_id"]
        },
        "_generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
    }

    io.open(OUT, "w", encoding="utf-8").write(
        json.dumps(out, indent=2, ensure_ascii=False) + "\n")

    print("Group 3 -> Group 2 semantic input emitted -> %s" % os.path.basename(OUT))
    print()
    print("SEVEN REQUESTED FIELDS")
    for k, v in requested.items():
        print("  %-18s owner=%-34s %s" % (k, v["owner"], v["status"]))
    print()
    print("TRACEABILITY")
    print("  leg 1  observation_id      %s" % traceability["leg_1_observation_id"]["status"])
    print("  leg 2  scientific citation %s" % traceability["leg_2_scientific_citation"]["status"])
    print()
    if citation_flags:
        print("CITATION DATA-QUALITY FLAGS (Group 2's record)")
        for f in citation_flags:
            print("  - %s" % f[:150])
        print()
    print("Every artifact exists. The science does not. Closing this dependency")
    print("as SATISFIED would record a traceability chain that does not hold.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
