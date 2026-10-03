# -*- coding: utf-8 -*-
"""Assemble the SAMACHAR evidence bundle Arya requested for the final REVIEW_PACKET.

Arya, 2026-08-31: "please provide the final SAMACHAR V2.2 payload using approved
rulings, structural/semantic validation evidence, actual G1 POST request/response,
canonical_record_id + GET response if successful, or complete G-40 500 evidence if
blocked, along with runtime logs, screenshots and the focused code packet."

Every item is produced from artifacts on disk. The one item that cannot be
produced - the live POST - is marked HELD with the reason and who asked for the
hold, rather than silently omitted or filled with the Mumbai 500 as though it
were SAMACHAR's.

Run:  python build_samachar_evidence_bundle.py
"""
import datetime
import glob
import hashlib
import io
import json
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DAY6 = os.path.dirname(HERE)
OUT = os.path.join(DAY6, "evidence_packet", "samachar")

CODE = [
    ("integration/emit_samachar_observation.py", "Builds the payload from the source under Arya's rulings"),
    ("contract/observation.schema.v2.2.json", "The frozen contract validated against"),
    ("contract/validate_semantic_v22.py", "Semantic / cross-field validator"),
    ("integration/post_single_frozen_observation.py", "One clean POST - the emission path, unused so far"),
]


def main():
    pkg_path = os.path.join(DAY6, "evidence", "live", "live_mission_package_SAMACHAR.json")
    if not os.path.isfile(pkg_path):
        raise SystemExit("ABORT: SAMACHAR payload not built. Run emit_samachar_observation.py first.")
    pkg = json.load(io.open(pkg_path, encoding="utf-8"))
    obs = pkg["observations"][0]

    # --- re-run BOTH validations now, capture the real output --------------
    import jsonschema
    schema = json.load(io.open(os.path.join(DAY6, "contract", "observation.schema.v2.2.json"),
                               encoding="utf-8"))
    struct = sorted(jsonschema.Draft202012Validator(schema).iter_errors(obs),
                    key=lambda e: list(e.path))
    ns, cwd = {}, os.getcwd()
    os.chdir(os.path.join(DAY6, "contract"))
    exec(io.open("validate_semantic_v22.py", encoding="utf-8").read().split("res = []")[0], ns)
    os.chdir(cwd)
    sem = list(ns["semantic_errors"](ns["strip"](obs)))

    if struct or sem:
        raise SystemExit("ABORT: payload no longer validates (%d structural, %d semantic). "
                         "Refusing to publish an evidence bundle for an invalid payload."
                         % (len(struct), len(sem)))

    # --- raw source artifact, re-verified ----------------------------------
    h = obs["raw_artifact_integrity"]["checksum_sha256"]
    art = glob.glob(os.path.join(DAY6, "evidence", "live", "raw_artifact_samachar_%s*.json" % h[:16]))
    art_ok = bool(art) and hashlib.sha256(io.open(art[0], "rb").read()).hexdigest() == h
    if not art_ok:
        raise SystemExit("ABORT: raw source artifact missing or hash mismatch.")

    if os.path.isdir(OUT):
        shutil.rmtree(OUT)
    for d in ["", "code_packet", "runtime_logs", "api_samples", "screenshots"]:
        os.makedirs(os.path.join(OUT, d))

    shutil.copy2(pkg_path, os.path.join(OUT, "api_samples", "SAMACHAR_payload_as_built.json"))
    shutil.copy2(art[0], os.path.join(OUT, "api_samples", os.path.basename(art[0])))
    src = os.path.join(DAY6, pkg["_source_file"])
    if os.path.isfile(src):
        shutil.copy2(src, os.path.join(OUT, "api_samples", "SOURCE_" + pkg["_source_file"]))
    for rel, _ in CODE:
        p = os.path.join(DAY6, rel)
        if os.path.isfile(p):
            shutil.copy2(p, os.path.join(OUT, "code_packet", os.path.basename(rel)))

    # --- validation evidence, captured not asserted ------------------------
    ts = datetime.datetime.now(datetime.timezone.utc)
    log = os.path.join(OUT, "runtime_logs", "validation_run.txt")
    with io.open(log, "w", encoding="utf-8") as fh:
        fh.write("SAMACHAR V2.2 VALIDATION - run %s\n" % ts.isoformat())
        fh.write("=" * 72 + "\n\n")
        fh.write("observation_id   : %s\n" % obs["observation_id"])
        fh.write("observation_type : %s\n" % obs["observation_type"])
        fh.write("measurement      : %s %s\n" % (obs["measurement"], obs["unit"]))
        fh.write("observation_time : %s\n" % obs["observation_timestamp"])
        fh.write("device / sensor  : %s / %s\n" % (obs["device_id"], obs["sensor_id"]))
        fh.write("provenance_ref   : %s\n\n" % obs["provenance_reference"])
        fh.write("STRUCTURAL (jsonschema Draft202012) : PASS - 0 errors\n")
        fh.write("SEMANTIC   (validate_semantic_v22)  : PASS - 0 errors\n\n")
        fh.write("raw source artifact : %s\n" % os.path.basename(art[0]))
        fh.write("  bytes             : %d\n" % os.path.getsize(art[0]))
        fh.write("  sha256 recorded   : %s\n" % h)
        fh.write("  sha256 re-read    : %s\n" % hashlib.sha256(io.open(art[0],"rb").read()).hexdigest())
        fh.write("  match             : YES\n")

    # --- the POST: HELD, and said so plainly -------------------------------
    held = {
        "_status": "NOT ATTEMPTED - HELD",
        "_this_is_not_a_failure": ("The POST has not been attempted. This is not a G3 defect, not a "
                                   "validation failure, and not a 500 on this observation."),
        "_who_asked": "Sanskar, Group 1, 2026-08-31",
        "_their_words": ("'Please continue holding the five regional payloads and don't retry them "
                         "yet ... we are treating this as a new-survey/external-source ingestion-path "
                         "issue, not only a five-region issue. We will verify the fix against the "
                         "new-survey path before asking you to retry.'"),
        "_why_it_covers_SAMACHAR": ("SMR-Z01-EXT-SAMACHAR-OBS001 is a first observation for a "
                                    "previously-unseen survey (SMR) - exactly the path Group 1 asked "
                                    "to hold."),
        "_what_G40_evidence_exists": ("Three captured POST/GET exchanges on the SAME new-survey path, "
                                      "using Mumbai. Held in evidence_packet/runtime_logs/. They "
                                      "document the blocker but are NOT SAMACHAR's own POST and must "
                                      "not be presented as such."),
        "_what_would_complete_this": ("One command, once Group 1 gives the GO. Everything else in "
                                      "this bundle is finished."),
        "_command": ("python post_single_frozen_observation.py "
                     "--fixture ../evidence/live/live_mission_package_SAMACHAR.json "
                     "--expect-id %s --expect-lat %s --expect-lon %s"
                     % (obs["observation_id"], obs["location"]["latitude"],
                        obs["location"]["longitude"])),
    }
    with io.open(os.path.join(OUT, "runtime_logs", "POST_STATUS_HELD.json"), "w",
                 encoding="utf-8") as fh:
        json.dump(held, fh, indent=2, ensure_ascii=False); fh.write("\n")

    io.open(os.path.join(OUT, "screenshots", "README.md"), "w", encoding="utf-8").write(
        "# screenshots/\n\nEmpty deliberately.\n\n"
        "There is no live POST to screenshot yet - the emission is held at Group 1's request "
        "(see `runtime_logs/POST_STATUS_HELD.json`). Group 3 will not ship a placeholder image "
        "implying a run that did not happen.\n\n"
        "The validation run IS captured, machine-readable, in `runtime_logs/validation_run.txt`.\n")

    manifest = {
        "_bundle": "SAMACHAR evidence - for Arya's final REVIEW_PACKET",
        "_built_at": ts.isoformat(),
        "_built_by": "integration/build_samachar_evidence_bundle.py",
        "requested_items": {
            "final V2.2 payload under approved rulings": "api_samples/SAMACHAR_payload_as_built.json",
            "structural validation evidence": "runtime_logs/validation_run.txt - PASS, 0 errors",
            "semantic validation evidence": "runtime_logs/validation_run.txt - PASS, 0 errors",
            "actual G1 POST request/response": "NOT AVAILABLE - runtime_logs/POST_STATUS_HELD.json",
            "canonical_record_id + GET": "NOT AVAILABLE - depends on the POST",
            "G-40 500 evidence": ("evidence_packet/runtime_logs/ - three exchanges on the same "
                                  "new-survey path, using Mumbai. NOT SAMACHAR's own POST"),
            "runtime logs": "runtime_logs/",
            "screenshots": "screenshots/README.md - none, and why",
            "focused code packet": "code_packet/ - %d files" % len(CODE),
        },
        "rulings_applied": pkg["_rulings_applied"],
        "timestamp_derivation": pkg["_timestamp_derivation"],
        "source": {"file": pkg["_source_file"], "url": pkg["_source_url"],
                   "title": pkg["_source_title"]},
        "honest_caveat": pkg["_honest_caveat"],
    }
    with io.open(os.path.join(OUT, "MANIFEST.json"), "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2, ensure_ascii=False); fh.write("\n")

    print("SAMACHAR EVIDENCE BUNDLE")
    print()
    print("  observation_id  %s" % obs["observation_id"])
    print("  STRUCTURAL      PASS - 0 errors")
    print("  SEMANTIC        PASS - 0 errors")
    print("  raw artifact    %d bytes, sha256 re-verified" % os.path.getsize(art[0]))
    print()
    for d in ["code_packet", "runtime_logs", "api_samples", "screenshots"]:
        print("  %-14s %d file(s)" % (d + "/", len(os.listdir(os.path.join(OUT, d)))))
    print()
    print("  POST            NOT ATTEMPTED - HELD at Group 1's request, stated in the bundle")
    print()
    print("  -> evidence_packet/samachar/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
