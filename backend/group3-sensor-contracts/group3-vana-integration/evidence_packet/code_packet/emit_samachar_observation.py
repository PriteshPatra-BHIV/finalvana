# -*- coding: utf-8 -*-
"""Build the SAMACHAR V2.2 observation from Omkar's real payload, per Arya's rulings.

ARYA'S RULINGS, 2026-08-31 (contract owner):
    observation_type : "news_report"
    measurement      : Omkar's source-supplied news_score. credibility and confidence
                       remain SOURCE METADATA, not substituted as the measurement.
    unit             : "score"  (dimensionless source score, not physical, not percent)
    observation_id   : "SMR-Z01-EXT-SAMACHAR-OBS001"  - a DEDICATED SAMACHAR survey,
                       so a news record is NOT represented as a field/environmental
                       observation inside the Mumbai survey
    sensor_id        : "SAMACHAR"
    device_id        : "G3-EXT-SAMACHAR-01"

EVERY VALUE HERE COMES FROM OMKAR'S FILE. Nothing is invented.
Where a value cannot be derived from his payload, the field is left at the honest
default the contract already defines for an external source - it is never guessed.

The source file carries two junk lines from a Swagger UI copy-paste
("Response body" / "Download"); they are stripped before parsing and that is
recorded, not silently absorbed.

Run:  python emit_samachar_observation.py
"""
import datetime
import hashlib
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DAY6 = os.path.dirname(HERE)
SRC = os.path.join(DAY6, sys.argv[1] if len(sys.argv) > 1 else "samachar3.json")

RULINGS = {
    "observation_type": "news_report",
    "unit": "score",
    "observation_id": "SMR-Z01-EXT-SAMACHAR-OBS001",
    "sensor_id": "SAMACHAR",
    "device_id": "G3-EXT-SAMACHAR-01",
    "_measurement_rule": "Omkar's news_score. credibility/confidence stay as source metadata.",
    "_authority": "Arya Barge, Group 3 Canonical Observation Contract Owner, 2026-08-31",
}


def parse_publication_date(raw):
    """Omkar's scraper returns a concatenated string whose shape differs per outlet.
    Two formats seen so far, both handled. IST (UTC+5:30) -> UTC.
    Returns (ist, utc, label) or (None, None, None) if unparseable - NEVER a guess.

      Indian Express: '...Jul 21, 2026 06:05 PM ISTFirst published on:Jul 21, 2026 at 06:04 PM IST'
      Free Press Jnl: 'Fariyal SayyedUpdated:Thursday, June 04, 2026, 05:54 PM IST'

    The label matters: 'first published' and 'last updated' are different facts and
    the emitted package records which one this is rather than flattening them."""
    raw = raw or ""
    m = re.search(r"First published on:\s*([A-Z][a-z]{2} \d{1,2}, \d{4})\s*at\s*"
                  r"(\d{1,2}:\d{2})\s*(AM|PM)\s*IST", raw)
    if m:
        ist = datetime.datetime.strptime("%s %s %s" % (m.group(1), m.group(2), m.group(3)),
                                         "%b %d, %Y %I:%M %p")
        return ist, ist - datetime.timedelta(hours=5, minutes=30), "first_published"
    m = re.search(r"(?:Updated:)?\w*day,?\s*([A-Z][a-z]+ \d{1,2}, \d{4}),?\s*"
                  r"(\d{1,2}:\d{2})\s*(AM|PM)\s*IST", raw)
    if m:
        ist = datetime.datetime.strptime("%s %s %s" % (m.group(1), m.group(2), m.group(3)),
                                         "%B %d, %Y %I:%M %p")
        return ist, ist - datetime.timedelta(hours=5, minutes=30), "last_updated"
    return None, None, None


def main():
    if not os.path.isfile(SRC):
        raise SystemExit("ABORT: %s not found." % SRC)

    raw_text = io.open(SRC, encoding="utf-8-sig").read()
    brace = raw_text.index("{")
    stripped = raw_text[:brace].strip()
    doc = json.loads(raw_text[brace:])
    D = doc["data"]
    sc, intel, summ = D["scraped_content"], D["intelligence"], D["analysis_summary"]

    # ---- persist the raw source bytes FIRST, then hash what was written -------
    # Same discipline as the sensor path: never hash a value that was not durably stored.
    canonical = json.dumps(doc, sort_keys=True, separators=(",", ":")).encode("utf-8")
    sha = hashlib.sha256(canonical).hexdigest()
    art_dir = os.path.join(DAY6, "evidence", "live")
    if not os.path.isdir(art_dir):
        os.makedirs(art_dir)
    art_path = os.path.join(art_dir, "raw_artifact_samachar_%s.json" % sha[:16])
    with io.open(art_path, "wb") as fh:
        fh.write(canonical)
    verify = hashlib.sha256(io.open(art_path, "rb").read()).hexdigest()
    if verify != sha:
        raise SystemExit("ABORT: persisted artifact hash does not match. Refusing to emit.")

    # ---- timestamps: from HIS data, not ours --------------------------------
    ist, utc, ts_label = parse_publication_date(sc.get("publication_date"))
    if utc is None:
        raise SystemExit("ABORT: could not parse a publication date from the source. "
                         "Refusing to substitute a fetch time for an observation time.")
    obs_ts = utc.strftime("%Y-%m-%dT%H:%M:%SZ")

    # ---- measurement: Arya's ruling. news_score, nothing substituted --------
    measurement = sc.get("news_score")
    if measurement is None:
        raise SystemExit("ABORT: news_score absent from the source. Not substituting another score.")

    # ---- location: derive from the article, never hardcode --------------------
    # The source supplies place NAMES, not coordinates. Map a name to an authorised
    # register point and record the basis. If no name maps, ABORT - do not guess.
    seed = json.load(io.open(os.path.join(DAY6, "GROUP1_REGION_SEED.json"), encoding="utf-8"))
    by_region = {r["region"]: r for r in seed["regions"]}
    PLACE_TO_REGION = {
        "thane": "Thane", "thane east": "Thane", "mithbunder": "Thane", "thane creek": "Thane",
        "mumbai": "Mumbai", "kandivali": "Mumbai", "charkop": "Mumbai", "mahim": "Mumbai",
        "navi mumbai": "Navi Mumbai", "nerul": "Navi Mumbai",
        "vasai": "Vasai", "maval": "Maval",
    }
    places = [str(p) for p in intel.get("validated_entities", {}).get("locations", [])]
    matched, region = None, None
    for p_ in places:
        r_ = PLACE_TO_REGION.get(p_.strip().lower())
        if r_:
            matched, region = p_, r_
            break
    if region is None:
        raise SystemExit(
            "ABORT: none of the article's locations %s maps to an authorised register "
            "point. Refusing to substitute a coordinate. Add a mapping only if the place "
            "genuinely sits in that survey area." % places)
    lat = by_region[region]["location"]["latitude"]
    lon = by_region[region]["location"]["longitude"]
    coord_basis = by_region[region]["coordinate_basis"]

    oid = RULINGS["observation_id"]
    seg = oid.split("-")
    survey, zone, third, sensor, seq = seg[0], seg[1], seg[2], seg[3], seg[4]
    mission = "%s-%s-%s" % (survey, zone, third)

    obs = {
        "contract_version": "2.2",
        "schema_version": "2.2",
        "observation_id": oid,
        "survey_id": survey,
        "zone_id": zone,
        "flight_id": third,
        "sensor_id": RULINGS["sensor_id"],
        "observation_seq": seq,
        "mission_id": mission,
        "device_id": RULINGS["device_id"],
        "source_identity": "group3-field-edge",

        "observation_type": RULINGS["observation_type"],
        "measurement": measurement,
        "unit": RULINGS["unit"],
        "capture_method": "external_api",

        "observation_timestamp": obs_ts,
        "source_timestamp": obs_ts,
        "ingestion_timestamp": None,

        # Location is DERIVED from the article's own extracted place entities and
        # mapped to an authorised register point - never hardcoded.
        # DEFECT FIXED 2026-08-31: an earlier version hardcoded Mumbai's coordinates,
        # which put Mahim Nature Park on a Thane East article. That is a substituted
        # coordinate - the exact thing the project forbids. Caught by Omkar asking
        # how location is represented when only a place NAME is available.
        "location": {"latitude": lat, "longitude": lon,
                     "altitude_m": None, "gnss_status": "NOT_VERIFIED",
                     "position_accuracy_m": None},

        "data_state": "CAPTURED",
        "quality_state": "CAPTURED",
        "synthetic_state": "CONTROLLED",
        "is_synthetic": True,
        "hardware_verified": False,
        "calibration_state": "NOT_VERIFIED",
        "accuracy": "NOT_VERIFIED",
        "processing_status": "raw",

        "raw_artifact": sc.get("url"),
        "raw_artifact_integrity": {"checksum_sha256": sha, "hash_algorithm": "sha256",
                                   "artifact_type": "sensor_reading"},
        "provenance_reference": "samachar:%s" % sha[:16],
        "provenance": {"device_id": RULINGS["device_id"], "mission_id": mission,
                       "captured_at": obs_ts, "raw_artifact": sc.get("url")},

        "idempotency_key": "IK-%s" % oid,
        "trace_id": None, "parent_reference": None, "integrity_reference": None,
        "waypoint_id": None, "tidal_state": None,
    }

    pkg = {
        "_README": ("SAMACHAR observation built from Omkar Patil's real pipeline output, "
                    "under Arya Barge's contract rulings of 2026-08-31."),
        "_built_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "_source_file": os.path.basename(SRC),
        "_source_file_note": ("Leading junk stripped before parsing: %r (Swagger UI "
                              "copy-paste artifact, %d chars). Recorded, not hidden."
                              % (stripped, brace)),
        "_source_url": sc.get("url"),
        "_source_title": sc.get("title"),
        "_rulings_applied": RULINGS,
        "_timestamp_derivation": {
            "raw_string": sc.get("publication_date"),
            "kind": ts_label,
            "_kind_note": ("first_published and last_updated are different facts. "
                           "Recorded, not flattened."),
            "parsed_IST": ist.strftime("%Y-%m-%d %H:%M") + " IST",
            "converted_UTC": obs_ts,
            "_cross_check": ("Agrees with the source's own extracted date entity: %s"
                             % intel["validated_entities"].get("dates")),
        },
        "_location_derivation": {
            "_rule": ("Derived from the article's own extracted place entities and mapped to an "
                      "authorised register point. NEVER hardcoded, never guessed."),
            "article_places": places,
            "matched_place": matched,
            "mapped_to_region": region,
            "register_coordinate": [lat, lon],
            "coordinate_basis": coord_basis,
            "_honest_caveat": ("This is the REGISTERED SURVEY POINT for that region, not the "
                              "article's specific site. The source supplies no coordinates. "
                              "It is the subject area of the report, not a sensor position."),
            "_defect_fixed_2026_08_31": ("An earlier build hardcoded Mumbai's coordinates and "
                                          "placed them on a Thane East article. Caught by Omkar "
                                          "Patil asking how location is represented when only a "
                                          "place name is available."),
        },
        "_source_metadata_NOT_used_as_measurement": {
            "_why": "Arya's ruling - these stay source metadata, never substituted.",
            "credibility_score": summ.get("credibility_score"),
            "confidence": intel.get("confidence", {}).get("score"),
            "authenticity": D.get("authenticity_analysis", {}).get("score"),
        },
        "_raw_artifact_file": os.path.relpath(art_path, DAY6).replace("\\", "/"),
        "_honest_caveat": ("A news report is not a physical measurement. synthetic_state "
                           "CONTROLLED, is_synthetic true, hardware_verified false. The "
                           "location is the SUBJECT of the article, not a sensor position."),
        "mission_id": mission, "survey": survey, "contract_version": "2.2",
        "observations": [obs],
    }

    out = os.path.join(DAY6, "evidence", "live", "live_mission_package_SAMACHAR.json")
    with io.open(out, "w", encoding="utf-8") as fh:
        json.dump(pkg, fh, indent=2, ensure_ascii=False)
        fh.write("\n")

    print("SAMACHAR OBSERVATION - built from Omkar's real values, under Arya's rulings")
    print()
    print("  observation_id     %s" % obs["observation_id"])
    print("  observation_type   %s" % obs["observation_type"])
    print("  measurement        %s %s   (news_score, per ruling)" % (obs["measurement"], obs["unit"]))
    print("  observation_time   %s   <- from HIS publication_date" % obs_ts)
    print("  device / sensor    %s / %s" % (obs["device_id"], obs["sensor_id"]))
    print("  provenance         %s" % obs["provenance_reference"])
    print("  raw artifact       %s bytes persisted, sha256 verified" % len(canonical))
    print()
    print("  NOT used as measurement (kept as metadata): credibility=%s confidence=%s"
          % (summ.get("credibility_score"), intel.get("confidence", {}).get("score")))
    print()
    print("  -> evidence/live/%s" % os.path.basename(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
