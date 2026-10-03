# -*- coding: utf-8 -*-
"""Emit the Group 3 -> Group 4 handoff in the TANTRA execution envelope.

CONFIRMED FORMAT
----------------
Karan Barda (Group 4 Lead), 2026-08-14, verbatim:

    "please use Candidate A (TANTRA Execution Envelope). Don't populate
     execution_id, trace_id, tenant_id or lineage_hash; these should come from
     the runtime. Keep the observation payload and replay idempotency_key/
     sequence as provided. I'll confirm the final trace convention after
     Mohit's confirmation."

This supersedes the earlier two-candidate emitter. Candidate B (the shared BHIV
artifact envelope read from the Sarathi adapter) is NOT the runtime handoff and
is no longer emitted here.

THE RULE THIS ENCODES
---------------------
Four fields are RUNTIME-OWNED and Group 3 leaves them null on purpose:

    execution_id   allocated by the runtime
    trace_id       injected by the runtime  <- answers the question asked 3x
    tenant_id      no tenant issued to a producer
    lineage_hash   computed over the execution chain by the runtime

Emitting null here is CORRECT, not incomplete. A producer that invented any of
these would corrupt the lineage it is supposed to be evidence for.

Two fields are PRODUCER-OWNED and Group 3 does populate them:

    replay.idempotency_key   derived from observation_id
    replay.sequence          submission sequence for this observation

Usage:
    python emit_tantra_envelope.py
"""
import json, io, os, sys, hashlib, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
CANONICAL = os.path.join(HERE, "canonical_observation.json")
OUT = os.path.join(HERE, "group3_to_group4_handoff.json")

RUNTIME_OWNED = ["execution_id", "trace_id", "tenant_id", "lineage_hash"]
PRODUCER_OWNED = ["replay.idempotency_key", "replay.sequence"]


DAY6 = os.path.dirname(HERE)
LIVE_CANDIDATE = os.path.join(DAY6, "evidence", "live", "live_observation_candidate.json")
LIVE_ACCEPTANCE = os.path.join(DAY6, "evidence", "live", "LIVE_ACCEPTANCE_PASSED_2026-08-25.json")


def _live_doc():
    """Assemble the same shape from the observation Group 1 actually accepted.

    Group 1's acceptance on 2026-08-25 is the condition the V1.2 envelope named as its
    own regeneration trigger. This path carries the V2.2 observation instead.
    """
    cand = json.load(io.open(LIVE_CANDIDATE, encoding="utf-8"))
    acc = json.load(io.open(LIVE_ACCEPTANCE, encoding="utf-8"))
    obs = cand["observation"]
    return {
        "canonical_observation": obs,
        "group4_handoff": {"idempotency_key": "IK-%s" % obs["observation_id"]},
        "_honesty": {
            "is_synthetic": obs["is_synthetic"],
            "source_type": "external_api - Open-Meteo.com, EXTERNAL LIVE API",
            "hardware_verified": obs["hardware_verified"],
            "canonical_store": (
                "Group 1's DEPLOYED PostgreSQL 16 + PostGIS 3.4 instance. Accepted "
                "%s at %s - %s." % (obs["observation_id"], acc["_emitted_at"], acc["result"])),
        },
        "_live_acceptance": acc,
    }, "2.2", (
        "V2.2 observation contract. This observation was emitted to and ACCEPTED by "
        "Group 1's deployed instance on 2026-08-25 (13/13). It supersedes the V1.2 "
        "envelope, which was built from a local v0.1 ingestion and never left this "
        "machine.")


def main():
    from_live = "--from-live" in sys.argv

    if from_live:
        if not os.path.exists(LIVE_CANDIDATE):
            print("FAIL: %s not found. Run build_live_observation_candidate.py first."
                  % os.path.basename(LIVE_CANDIDATE))
            return 2
        doc, contract_version, contract_note = _live_doc()
    else:
        if not os.path.exists(CANONICAL):
            print("FAIL: run integration/emit_canonical_observation.py first.")
            return 2
        doc = json.load(io.open(CANONICAL, encoding="utf-8"))
        contract_version = "1.2"
        contract_note = (
            "V1.2 observation contract, ingested through Group 1 local schema v0.1. "
            "SUPERSEDED - Group 1 accepted V2.2 live on 2026-08-25. Re-run with "
            "--from-live for the current envelope.")

    obs = doc["canonical_observation"]
    handoff = doc["group4_handoff"]

    payload = {
        "observation": obs,
        "emitted_by": "group3-field-edge",
        # Derived, not asserted. This envelope is built from canonical_observation.json,
        # which comes from the V1.2 mission package ingested through Group 1's LOCAL v0.1
        # schema. It therefore describes the V1.2 observation contract - NOT the V2.2
        # contract Arya Barge ruled freeze-ready on 2026-08-20. Regenerate this envelope
        # from a V2.2 observation once Group 1 has aligned its validator and accepted V2.2
        # live. An earlier version hardcoded "1.0" with no note, which read as current.
        "contract_version": contract_version,
        "contract_version_note": contract_note,
        "is_synthetic": doc["_honesty"]["is_synthetic"],
        "hardware_verified": doc["_honesty"]["hardware_verified"]
    }
    payload_sha = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()

    envelope = {
        "execution_id": None,      # runtime-owned
        "trace_id": None,          # runtime-owned - Group 3 must NOT invent this
        "tenant_id": None,         # runtime-owned
        "lineage_hash": None,      # runtime-owned
        "replay": {
            "idempotency_key": handoff["idempotency_key"],
            "sequence": 1
        },
        "payload": payload
    }

    out = {
        "_README": (
            "Group 3 -> Group 4 handoff, TANTRA execution envelope. Format confirmed "
            "by Karan Barda (Group 4 Lead) on 2026-08-14. The four null fields are "
            "runtime-owned by his instruction and are null BY DESIGN, not by omission."
        ),
        "_format_ruling": {
            "confirmed_by": "Karan Barda, Group 4 Lead",
            "date": "2026-08-14",
            "envelope": "TANTRA Execution Envelope (Candidate A)",
            "runtime_owned_fields": RUNTIME_OWNED,
            "producer_owned_fields": PRODUCER_OWNED,
            "supersedes": "the two-candidate emitter; Candidate B is not the runtime handoff"
        },
        "_honesty": {
            "is_synthetic": doc["_honesty"]["is_synthetic"],
            "source_type": doc["_honesty"]["source_type"],
            "hardware_verified": False,
            "canonical_store": doc["_honesty"]["canonical_store"],
            "note": (
                ("No Group 3 sensor has produced a recorded reading. This is real "
                 "third-party data from an EXTERNAL LIVE API carried through the "
                 "controlled Group 3 path, accepted by Group 1's DEPLOYED instance. "
                 "It is NOT Group 3 hardware evidence and must not be presented as one.")
                if from_live else
                ("No Group 3 sensor has produced a recorded reading. This observation "
                 "was ingested through Group 1's schema on a LOCAL database and read "
                 "back. Do not treat it as real field data or as a Group 1 instance record.")
            )
        },
        "_trace_convention": {
            "canonical_format": "VANA-<12 lowercase hex>",
            "example": "VANA-3a9fd87b337d",
            "regex": "^VANA-[0-9a-f]{12}$",
            "source": (
                "Group 1 VANA MasterDB Observation API v1.0.0 handoff, Raj "
                "Prajapati 2026-08-14, target commit "
                "92a37b337df1fb1d4b8565ada47656d182771cdf. The API returns "
                "trace_id in every ingestion, replay, conflict and duplicate "
                "response."
            ),
            "supersedes": (
                "the provisional 'trace-vana-<16 hex>' form observed in a Group 4 "
                "governed execution on 2026-08-13"
            ),
            "group3_position": (
                "Group 3 emits null and never mints a trace. Karan's 2026-08-14 "
                "ruling on OWNERSHIP stands - the producer does not mint traces. "
                "This fixes only the FORMAT."
            ),
            "correlation_resolved": (
                "Because Group 1's API returns trace_id on ingestion, Group 3 CAN "
                "now correlate its submission to the resulting trace. This closes "
                "the open question of whether the trace is returned to the producer."
            )
        },
        "_still_open_with_group4": [
            {
                "item": "Does Group 4's runtime accept Group 1's VANA-<12 hex> trace, or mint its own?",
                "status": "OPEN - must be settled between Groups 1 and 4",
                "impact_on_group3": (
                    "If both mint a trace, one observation carries two identifiers "
                    "and correlation breaks at the boundary. Group 3 has adopted the "
                    "Group 1 format and will carry whichever the two groups agree on."
                ),
                "owner": "Raj / Karan"
            },
            {
                "item": "Trace null in runtime/OTel logs",
                "status": "OPEN - disclosed by Karan himself",
                "impact_on_group3": (
                    "Correlation unproven at Group 4's layer. Not Group 3's to fix, "
                    "but it means the injected trace is not yet observable end to end."
                ),
                "owner": "Mohit, Group 4"
            }
        ],
        "_payload_sha256": payload_sha,
        "_generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "envelope": envelope
    }

    out_path = (os.path.join(HERE, "group3_to_group4_handoff.v2.2.json")
                if from_live else OUT)
    io.open(out_path, "w", encoding="utf-8").write(
        json.dumps(out, indent=2, ensure_ascii=False) + "\n")

    print("Group 3 -> Group 4 handoff emitted -> %s" % os.path.basename(out_path))
    print("  contract_version : %s" % contract_version)
    print()
    print("TANTRA execution envelope - format CONFIRMED by Karan Barda, 2026-08-14")
    print()
    print("  RUNTIME-OWNED (null by his instruction, NOT by omission):")
    for f in RUNTIME_OWNED:
        print("    [runtime] %-14s null" % f)
    print()
    print("  PRODUCER-OWNED (Group 3 populates):")
    print("    [group3 ] %-14s %s" % ("replay.idempotency_key", envelope["replay"]["idempotency_key"]))
    print("    [group3 ] %-14s %s" % ("replay.sequence", envelope["replay"]["sequence"]))
    print("    [group3 ] %-14s observation %s" % ("payload", obs["observation_id"]))
    print()
    print("  payload_sha256 : %s" % payload_sha)
    print("  is_synthetic   : %s" % doc["_honesty"]["is_synthetic"])
    print()
    print("  RESULT: handoff format CLOSED. Group 3 emits this shape from here on.")
    print()
    print("  STILL OPEN: does the runtime RETURN the trace_id to the producer?")
    print("  Without it Group 3 cannot correlate its submission to the governed")
    print("  execution, and end-to-end identity survival stays unproven from our side.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
