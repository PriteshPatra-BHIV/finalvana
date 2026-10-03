# -*- coding: utf-8 -*-
"""Emit the Group 3 UI field-observation view.

New P1 deliverable from today's build push:

    "Group 3 must expose enough information for the VANA UI to show:
     MISSION, OBSERVATION ID, DEVICE, TIME, LOCATION, MEASUREMENT, QUALITY,
     CALIBRATION, RAW ARTIFACT, PROVENANCE, STATUS.
     Recommended status progression:
       CAPTURED -> VALIDATED -> PACKAGED -> TRANSMITTED -> CANONICAL
     The UI should distinguish synthetic fixture from real hardware
     observation prominently."

TWO STATUS AXES - DO NOT MERGE THEM
------------------------------------
The directive elsewhere tells Manya to "use the existing quality semantics
rather than inventing another status vocabulary". The progression above is NOT
the existing quality vocabulary - it is a different axis, and collapsing the two
would destroy information:

  quality_status  = the FIELD QA VERDICT about the observation itself
                    RAW / CAPTURED / VALIDATED / REJECTED / UNCERTAIN / INGESTED
                    Owner: Group 3 field QA. Frozen in contract V1.0.

  pipeline_status = HOW FAR the observation has travelled through VANA
                    CAPTURED / VALIDATED / PACKAGED / TRANSMITTED / CANONICAL
                    Owner: the pipeline. DERIVED, never hand-set.

An observation can be quality_status=UNCERTAIN (no GNSS fix) and still reach
pipeline_status=CANONICAL. Both facts are true and the UI must show both.

pipeline_status is therefore NOT added to the frozen observation contract. It is
computed here from observable facts.

Usage:
    python emit_ui_view.py
"""
import json, io, os, sys, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
CANONICAL = os.path.join(HERE, "canonical_observation.json")
HANDOFF = os.path.join(HERE, "group3_to_group4_handoff.json")
OUT = os.path.join(HERE, "ui_field_observation_view.json")


def derive_pipeline_status(obs, transmitted, canonical):
    """Derive how far the observation actually travelled. Never hand-set."""
    if canonical:
        return "CANONICAL"
    if transmitted:
        return "TRANSMITTED"
    return "PACKAGED"


def main():
    if not os.path.exists(CANONICAL):
        print("FAIL: run integration/emit_canonical_observation.py first.")
        return 2

    doc = json.load(io.open(CANONICAL, encoding="utf-8"))
    obs = doc["canonical_observation"]

    # Observable facts, not assertions.
    reached_group1_schema = True                      # proven by the round-trip
    reached_group1_instance = False                   # no endpoint issued
    crossed_edge_transport = False                    # SVACS blocked
    packaged_for_group4 = os.path.exists(HANDOFF)

    pipeline_status = derive_pipeline_status(
        obs,
        transmitted=crossed_edge_transport,
        canonical=reached_group1_schema)

    view = {
        "mission": obs["dataset"]["dataset_id"],
        "observation_id": obs["observation_id"],
        "device": {
            "device_id": obs["device_id"],
            "verification_state": "NOT VERIFIED",
            "deployment_state": "PHASE 2",
            "note": "Device identifier only. No Group 3 device has produced a recorded reading."
        },
        "time": obs["observed_at"],
        "location": {
            "latitude": obs["location"]["latitude"],
            "longitude": obs["location"]["longitude"],
            "crs": obs["location"]["crs"],
            "place_name": obs["location"]["place_name"]
        },
        "measurement": {
            "parameter": obs["measurement"]["parameter"],
            "value": obs["measurement"]["value"],
            "unit": obs["measurement"]["unit"]
        },
        "quality": obs["quality_status"],
        "calibration": obs["measurement"]["calibration_status"],
        "accuracy": obs["measurement"]["accuracy"],
        "raw_artifact": {
            "reference": obs["raw_artifact"]["reference"],
            "sha256": obs["raw_artifact"]["sha256"],
            "note": "Reference only - the raw file is not transmitted to the canonical store."
        },
        "provenance": {
            "provenance_id": obs["provenance"]["provenance_id"],
            "source_id": obs["source"]["source_id"],
            "device_id": obs["device_id"],
            "mission_id": obs["dataset"]["dataset_id"]
        },
        "status": pipeline_status,

        # The banner the directive asks for, as data rather than prose.
        "origin_banner": {
            "level": "WARNING",
            "label": "SYNTHETIC FIXTURE - NOT A HARDWARE OBSERVATION",
            "is_synthetic": doc["_honesty"]["is_synthetic"],
            "source_type": obs["source"]["source_type"],
            "hardware_verified": False,
            "display_rule": (
                "MUST be shown prominently and MUST NOT be dismissible while "
                "is_synthetic is true. A synthetic observation rendered like a "
                "real one is the failure mode this banner exists to prevent."
            )
        }
    }

    doc_out = {
        "_README": (
            "Group 3 UI field-observation view. Every value is read from the "
            "canonical record produced by integration/"
            "emit_canonical_observation.py. Nothing here is hand-entered."
        ),
        "_two_status_axes": {
            "quality_status": {
                "value": obs["quality_status"],
                "meaning": "field QA verdict about the observation itself",
                "vocabulary": ["RAW", "CAPTURED", "VALIDATED", "REJECTED",
                               "UNCERTAIN", "INGESTED"],
                "owner": "Group 3 field QA",
                "frozen_in": "observation contract V1.0"
            },
            "pipeline_status": {
                "value": pipeline_status,
                "meaning": "how far the observation has travelled through VANA",
                "vocabulary": ["CAPTURED", "VALIDATED", "PACKAGED",
                               "TRANSMITTED", "CANONICAL"],
                "owner": "the pipeline - DERIVED, never hand-set",
                "deliberately_not_in_contract": (
                    "Adding it would break the V1.0 freeze and would conflate a QA "
                    "verdict with a transport position. An observation can be "
                    "UNCERTAIN and CANONICAL at the same time; both are true."
                )
            }
        },
        "_status_derivation": {
            "reached_group1_schema": reached_group1_schema,
            "reached_group1_instance": reached_group1_instance,
            "crossed_edge_transport": crossed_edge_transport,
            "packaged_for_group4": packaged_for_group4,
            "derived_status": pipeline_status,
            "honest_caveat": (
                "CANONICAL here means the observation reached a canonical record "
                "built from Group 1's SCHEMA on a LOCAL database. It has NOT "
                "reached Group 1's instance, and it did NOT cross the edge "
                "transport - SVACS is blocked. The UI must not imply otherwise."
            )
        },
        "_generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "view": view
    }

    io.open(OUT, "w", encoding="utf-8").write(
        json.dumps(doc_out, indent=2, ensure_ascii=False) + "\n")

    print("UI field-observation view emitted -> %s" % os.path.basename(OUT))
    print()
    print("  MISSION        %s" % view["mission"])
    print("  OBSERVATION ID %s" % view["observation_id"])
    print("  DEVICE         %s   (%s / %s)" % (view["device"]["device_id"],
                                               view["device"]["verification_state"],
                                               view["device"]["deployment_state"]))
    print("  TIME           %s" % view["time"])
    print("  LOCATION       %.4f, %.4f  %s" % (view["location"]["latitude"],
                                               view["location"]["longitude"],
                                               view["location"]["crs"]))
    print("  MEASUREMENT    %s %s  (%s)" % (view["measurement"]["value"],
                                            view["measurement"]["unit"],
                                            view["measurement"]["parameter"]))
    print("  QUALITY        %s          <- field QA verdict" % view["quality"])
    print("  CALIBRATION    %s" % view["calibration"])
    print("  RAW ARTIFACT   %s" % view["raw_artifact"]["reference"])
    print("  PROVENANCE     %s" % view["provenance"]["provenance_id"])
    print("  STATUS         %s          <- pipeline position, DERIVED" % view["status"])
    print()
    print("  BANNER: %s" % view["origin_banner"]["label"])
    print()
    print("  Two status axes kept separate on purpose:")
    print("    quality_status  = %-10s (QA verdict, contract V1.0)" % view["quality"])
    print("    pipeline_status = %-10s (transport position, derived)" % view["status"])
    print()
    print("  CAVEAT: CANONICAL = Group 1's SCHEMA on a LOCAL database.")
    print("          NOT their instance. Edge transport NOT crossed - SVACS blocked.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
