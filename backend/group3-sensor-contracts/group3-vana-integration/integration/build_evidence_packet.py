# -*- coding: utf-8 -*-
"""Build the /evidence_packet/ required by GROUP 3 TASK-31-09-2026.md.

The task mandates a common closure structure for all four groups:

    /evidence_packet/
        review_packet.md
        screenshots/
        code_packet/        only the files necessary to review the actual change
        runtime_logs/
        api_samples/
        deployment_proof/

This assembles it from artifacts that already exist on disk. It COPIES rather
than regenerates, so what reviewers see is what was actually produced.

Nothing here fabricates a result. Where a required item does not exist - notably
screenshots, which are the operator's to capture - the packet says so plainly
rather than shipping an empty directory that implies otherwise.

Run:  python build_evidence_packet.py
"""
import datetime
import glob
import io
import json
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DAY6 = os.path.dirname(HERE)
PACKET = os.path.join(DAY6, "evidence_packet")

SUBDIRS = ["screenshots", "code_packet", "runtime_logs", "api_samples", "deployment_proof"]

# code_packet must hold ONLY what is needed to review the actual change.
CODE_PACKET = [
    ("contract/observation.schema.v2.2.json", "The frozen V2.2 contract"),
    ("contract/validate_semantic_v22.py", "Semantic / cross-field validator"),
    ("integration/build_live_observation_candidate.py", "Source acquisition + raw-byte preservation"),
    ("integration/post_single_frozen_observation.py", "One clean POST into G1, no mutation"),
    ("integration/probe_group1_six_region_state.py", "Read-only state probe"),
]

API_SAMPLES = [
    ("evidence/live/LIVE_ACCEPTANCE_PASSED_2026-08-25.json", "13/13 live acceptance against G1"),
    ("evidence/live/SOURCE_EVIDENCE_PACK_EMITTED_2026-08-25.json", "Full source provenance pack"),
    ("evidence/live/live_mission_package.json", "The Thane Creek payload as sent"),
]


def verify():
    """Re-derive the load-bearing figures. Abort rather than publish a wrong one."""
    out = {}
    sch = json.load(io.open(os.path.join(DAY6, "contract", "observation.schema.v2.2.json"),
                            encoding="utf-8"))
    out["required"] = len(sch["required"])
    out["rules"] = len(sch["allOf"])
    phys = 0
    for f in glob.glob(os.path.join(DAY6, "evidence", "**", "*.json"), recursive=True):
        if '"hardware_verified": true' in io.open(f, encoding="utf-8", errors="replace").read():
            phys += 1
    out["physical_observations"] = phys
    return out


def main():
    v = verify()
    if v["required"] != 24 or v["rules"] != 15:
        raise SystemExit("ABORT: contract shape changed (%s). Refusing to publish." % v)
    if v["physical_observations"] != 0:
        raise SystemExit("ABORT: expected 0 physical observations, found %d"
                         % v["physical_observations"])

    if os.path.isdir(PACKET):
        shutil.rmtree(PACKET)
    os.makedirs(PACKET)
    for d in SUBDIRS:
        os.makedirs(os.path.join(PACKET, d))

    copied = {"code_packet": [], "api_samples": [], "runtime_logs": [], "deployment_proof": []}

    for rel, why in CODE_PACKET:
        src = os.path.join(DAY6, rel)
        if os.path.isfile(src):
            shutil.copy2(src, os.path.join(PACKET, "code_packet", os.path.basename(rel)))
            copied["code_packet"].append((os.path.basename(rel), why))

    for rel, why in API_SAMPLES:
        src = os.path.join(DAY6, rel)
        if os.path.isfile(src):
            shutil.copy2(src, os.path.join(PACKET, "api_samples", os.path.basename(rel)))
            copied["api_samples"].append((os.path.basename(rel), why))

    # runtime logs: the captured POST/GET exchanges, successes AND failures
    for src in sorted(glob.glob(os.path.join(DAY6, "evidence", "live", "SINGLE_POST_*.json"))):
        shutil.copy2(src, os.path.join(PACKET, "runtime_logs", os.path.basename(src)))
        copied["runtime_logs"].append((os.path.basename(src), "Captured POST+GET exchange"))

    # deployment proof: the emitted contracts other groups consume
    for rel in ["GROUP3_INTAKE_ADAPTER_CONTRACT.json", "V2.2_PERSISTENCE_MATRIX.json",
                "GROUP3_ENDPOINT_INVENTORY.json"]:
        src = os.path.join(DAY6, rel)
        if os.path.isfile(src):
            shutil.copy2(src, os.path.join(PACKET, "deployment_proof", rel))
            copied["deployment_proof"].append((rel, "Consumed by downstream groups"))

    # screenshots are the operator's to capture - say so rather than imply they exist
    io.open(os.path.join(PACKET, "screenshots", "README.md"), "w", encoding="utf-8").write(
        "# screenshots/\n\n"
        "**Empty at packet build time, deliberately.**\n\n"
        "Screenshots must prove runtime behaviour and are captured by the operator against the live\n"
        "service. Group 3 does not generate them, and will not ship a placeholder image implying a\n"
        "run that did not happen.\n\n"
        "## What to capture\n\n"
        "1. `probe_group1_six_region_state.py` output - service health and six-region state\n"
        "2. A `GET /observations/TC-Z03-EXT-OPENMETEO-OBS001` response showing the canonical record\n"
        "3. The `post_single_frozen_observation.py` run, whatever it returns\n\n"
        "The runtime_logs/ directory already carries the machine-readable equivalent of (3).\n")

    stamp = datetime.datetime.now(datetime.timezone.utc)
    manifest = {
        "_packet": "Group 3 evidence packet",
        "_task": "GROUP 3 TASK-31-09-2026.md",
        "_owner": "Hemanth Reddy - VANA Integration & Data Interface",
        "_built_at": stamp.isoformat(),
        "_built_by": "integration/build_evidence_packet.py",
        "verified_at_build": v,
        "contents": {k: [n for n, _ in vv] for k, vv in copied.items()},
        "screenshots": "EMPTY - operator-captured, see screenshots/README.md",
    }
    with io.open(os.path.join(PACKET, "MANIFEST.json"), "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2, ensure_ascii=False)
        fh.write("\n")

    print("GROUP 3 EVIDENCE PACKET")
    print()
    for k in SUBDIRS:
        n = len([f for f in os.listdir(os.path.join(PACKET, k))])
        print("  %-18s %d file(s)" % (k + "/", n))
    print()
    print("  verified at build: %d required fields, %d rules, %d physical observations"
          % (v["required"], v["rules"], v["physical_observations"]))
    print()
    print("  -> evidence_packet/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
