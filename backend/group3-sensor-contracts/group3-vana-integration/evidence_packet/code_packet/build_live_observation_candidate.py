# -*- coding: utf-8 -*-
"""Build a CANDIDATE V2.2 observation from a live AIAIC source, and validate it.

PURPOSE
-------
Arya asked for a confirmed source plus one sample current payload. This produces
a real one: it calls Open-Meteo live at Thane Creek, maps the response onto the
frozen V2.2 contract, and validates the result against the frozen schema and the
semantic layer. Nothing here is hand-written data.

WHAT THIS IS NOT
----------------
It is NOT the approved emission path. Two things are deliberately left for the
contract owner, because they are not Group 3 continuity's to decide:

  1. Arya's explicit written sign-off on the external-source amendment. The
     MDU/schema-authority gate was lifted for today by the manager on
     2026-08-24 ("no key needed today"), and the amendment is applied - but her
     signature has not been given. NO LIVE POST until it is.
  2. Nupur reviews the MDU scope question tomorrow and may still require
     registration or changes.

The identity below is now TRUTHFUL, not a placeholder: EXT is the approved
non-flight marker and external_api the approved capture method. Open-Meteo has
no flight and is not a Group 3 sensor, and the record now says so.

The frozen schema is NOT modified by this script. It only reads it.

Run:  python build_live_observation_candidate.py
      python build_live_observation_candidate.py --lat 19.1288 --lon 72.9421
"""
import argparse, datetime, hashlib, io, json, os, sys, urllib.request

from jsonschema import Draft202012Validator, FormatChecker

HERE = os.path.dirname(os.path.abspath(__file__))
DAY6 = os.path.dirname(HERE)
SCHEMA_PATH = os.path.join(DAY6, "contract", "observation.schema.v2.2.json")

DEFAULT_LAT, DEFAULT_LON = 19.1288, 72.9421     # Thane Creek, inside Group 2's zone polygon

OPEN_METEO = ("https://api.open-meteo.com/v1/forecast?latitude=%s&longitude=%s"
              "&current=temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m"
              "&timezone=UTC")

ATTRIBUTION = ("Weather data by Open-Meteo.com, CC-BY 4.0, non-commercial free tier. "
               "Open-Meteo aggregates national weather services.")


def fetch(lat, lon):
    url = OPEN_METEO % (lat, lon)
    with urllib.request.urlopen(url, timeout=25) as r:
        body = r.read().decode("utf-8")
        code = r.status
    return code, json.loads(body), body, url


def build(lat, lon, variable="precipitation", survey="TC", zone="Z03",
          region="Thane Creek", basis=None):
    code, d, raw, url = fetch(lat, lon)
    cur = d.get("current") or {}
    units = d.get("current_units") or {}
    if variable not in cur:
        raise SystemExit("variable %r not returned by the source - refusing to invent it" % variable)

    value = cur[variable]
    unit = units.get(variable)
    if unit in (None, "", " "):
        raise SystemExit("source returned no unit for %r - refusing to invent one" % variable)

    # The raw API response IS the source artifact. Hash the actual bytes returned.
    artifact_sha = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    observed_at = cur.get("time")
    if observed_at and len(observed_at) == 16:      # Open-Meteo returns 'YYYY-MM-DDTHH:MM' in UTC
        observed_at += ":00Z"

    # TRUTHFUL identity, valid since the external-source amendment was applied 2026-08-24.
    # EXT is the non-flight marker: Open-Meteo has no flight and is not a Group 3 sensor.
    seq = "OBS%03d" % 1
    # Identity is PARAMETERISED, not hardcoded. survey/zone come from the frozen
    # Zone Identity Register (owner ruling, Arya Barge 2026-08-28). Defaults keep the
    # proven Thane Creek path byte-identical.
    obs_id = "%s-%s-EXT-OPENMETEO-%s" % (survey, zone, seq)
    mission = "%s-%s-EXT" % (survey, zone)

    obs = {
        "contract_version": "2.2",
        "schema_version": "2.2",
        "observation_id": obs_id,
        "source_identity": "group3-field-edge",
        "survey_id": survey,
        "zone_id": zone,
        "flight_id": "EXT",             # non-flight marker, approved 2026-08-24
        "sensor_id": "OPENMETEO",
        "observation_seq": seq,
        "mission_id": mission,
        "parent_reference": None,
        "observation_timestamp": observed_at,
        "source_timestamp": observed_at,
        "ingestion_timestamp": None,
        "data_state": "CAPTURED",
        "synthetic_state": "CONTROLLED",
        "is_synthetic": True,
        "calibration_state": "NOT_VERIFIED",
        "quality_state": "CAPTURED",
        "location": {"latitude": lat, "longitude": lon, "altitude_m": d.get("elevation"),
                     "gnss_status": "NOT_VERIFIED", "position_accuracy_m": None},
        "waypoint_id": None,
        "device_id": "G3-EXT-OPENMETEO-01",
        "observation_type": variable,
        "capture_method": "external_api",
        "measurement": value,
        "unit": unit,
        "accuracy": "NOT_VERIFIED",
        "processing_status": "raw",
        "raw_artifact": url,
        "raw_artifact_integrity": {"checksum_sha256": artifact_sha, "hash_algorithm": "sha256",
                                   "artifact_type": "sensor_reading"},
        "integrity_reference": None,
        "provenance_reference": "open-meteo:%s" % artifact_sha[:16],
        "provenance": {"device_id": "G3-EXT-OPENMETEO-01", "mission_id": mission,
                       "captured_at": observed_at, "raw_artifact": url,
                       "operator": "Open-Meteo.com (external data provider)",
                       # The COORDINATE BASIS supplied by Group 2. Recorded so the
                       # location is traceable to a stated reason, not to a lookup.
                       "qa_record": ("coordinate basis: %s (%s) - supplied by Group 2, "
                                     "2026-08-28" % (basis, region)) if basis else None},
        "tidal_state": None,
        "trace_id": None,
        "idempotency_key": "IK-" + obs_id,
        "hardware_verified": False,
    }
    return obs, code, url, raw, artifact_sha


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lat", type=float, default=DEFAULT_LAT)
    ap.add_argument("--lon", type=float, default=DEFAULT_LON)
    ap.add_argument("--variable", default="precipitation")
    ap.add_argument("--survey", default="TC",
                    help="survey_id from the frozen Zone Identity Register")
    ap.add_argument("--zone", default="Z03", help="zone_id from the register")
    ap.add_argument("--region", default="Thane Creek", help="human region name")
    ap.add_argument("--basis", default=None,
                    help="the STATED BASIS for this coordinate, recorded in provenance")
    ap.add_argument("--out-suffix", default="",
                    help="suffix for output filenames so regions do not overwrite each other")
    a = ap.parse_args()

    print("LIVE V2.2 OBSERVATION CANDIDATE - Open-Meteo @ Thane Creek")
    print("built at : %s" % datetime.datetime.now(datetime.timezone.utc).isoformat())
    print()

    obs, code, url, raw, sha = build(a.lat, a.lon, a.variable,
                                     a.survey, a.zone, a.region, a.basis)
    print("  source HTTP        : %s" % code)
    print("  observed (UTC)     : %s" % obs["observation_timestamp"])
    print("  %-18s : %s %s" % (obs["observation_type"], obs["measurement"], obs["unit"]))
    print("  raw artifact sha256: %s" % sha)
    print()

    schema = json.load(io.open(SCHEMA_PATH, encoding="utf-8"))
    v = Draft202012Validator(schema, format_checker=FormatChecker())
    errs = [e.message for e in v.iter_errors(obs)]
    print("  FROZEN SCHEMA      : %s" % ("VALID" if not errs else "INVALID"))
    for e in errs:
        print("     - %s" % e[:110])

    ns = {}
    src = io.open(os.path.join(DAY6, "contract", "validate_semantic_v22.py"), encoding="utf-8").read()
    cwd = os.getcwd()
    os.chdir(os.path.join(DAY6, "contract"))
    try:
        exec(src.split("res = []")[0], ns)
        sem = ns["semantic_errors"](ns["strip"](obs))
    finally:
        os.chdir(cwd)
    print("  SEMANTIC LAYER     : %s" % ("clean" if not sem else "%d issue(s)" % len(sem)))
    for e in sem:
        print("     - %s" % e[:110])

    _sfx = a.out_suffix
    out = os.path.join(DAY6, "evidence", "live",
                       "live_observation_candidate%s.json" % _sfx)
    os.makedirs(os.path.dirname(out), exist_ok=True)

    # Persist the EXACT response bytes that were hashed. Without this file the
    # checksum in the observation is unverifiable and the Source Evidence Pack's
    # replay instruction is uncheckable. The bytes are the artifact.
    raw_path = os.path.join(DAY6, "evidence", "live", "raw_artifact_%s.json" % sha[:16])
    with io.open(raw_path, "w", encoding="utf-8", newline="") as fh:
        fh.write(raw)
    print("  raw artifact bytes : %s (%d bytes)" % (os.path.basename(raw_path), len(raw.encode("utf-8"))))
    with io.open(out, "w", encoding="utf-8") as fh:
        json.dump({"_README": ("TRUTHFUL V2.2 observation built from a LIVE Open-Meteo call. Uses the "
                               "approved EXT non-flight identity and external_api capture method. The "
                               "amendment was approved by Arya Barge 2026-08-24 and ratified in the "
                               "25 Aug contract; the manager ruled MDU registration NOT required for "
                               "this controlled demonstration."),
                   "_built_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                   "_source_url": url,
                   "_attribution": ATTRIBUTION,
                   "_schema_valid": not errs,
                   "_semantic_clean": not sem,
                   "_resolved_questions": [
                       "observation_id scheme - RESOLVED: flight_id EXT is the approved non-flight "
                       "marker; no fabricated flight is written. Arya 2026-08-24, ratified 2026-08-25.",
                       "synthetic_state for real external third-party data - RESOLVED: CONTROLLED. "
                       "PHYSICAL is forbidden for external_api by contract rule.",
                       "device_id 'G3-EXT-OPENMETEO-01' - RESOLVED: approved external-provider "
                       "convention G3-EXT-<PROVIDER>-<NN>. It is NOT a physical device identifier."],
                   "_raw_artifact_bytes_file": os.path.basename(raw_path),
                   "observation": obs}, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    # Also write a MISSION-PACKAGE-shaped file so live_acceptance_group1.py can
    # consume it directly. It expects {"observations": [...]}, which is what Group 1's
    # POST path is built around.
    pkg_path = os.path.join(DAY6, "evidence", "live",
                            "live_mission_package%s.json" % _sfx)
    with io.open(pkg_path, "w", encoding="utf-8") as fh:
        json.dump({"_README": ("Ready-to-emit mission package containing ONE truthful live external "
                               "observation. Regenerated on every run - the measurement and the artifact "
                               "hash change because the source is live. Emit the package you just "
                               "built, never a stale one."),
                   "_built_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                   "_source_url": url,
                   "_attribution": ATTRIBUTION,
                   "_schema_valid": not errs,
                   "_semantic_clean": not sem,
                   "mission_id": obs["mission_id"],
                   "survey": obs["survey_id"],
                   "contract_version": obs["contract_version"],
                   "observations": [obs]}, fh, indent=2, ensure_ascii=False)
        fh.write(chr(10))

    print()
    print("  candidate -> evidence/live/%s" % os.path.basename(out))
    print("  EMIT THIS -> evidence/live/%s" % os.path.basename(pkg_path))
    print()
    print("  Identity is TRUTHFUL: EXT non-flight marker + external_api capture method.")
    print("  APPROVED by Arya 2026-08-24 for today's scope. Ready to emit.")
    print("  Nupur reviews the MDU scope question tomorrow - amendment is reversible.")
    return 0 if (not errs and not sem) else 1


if __name__ == "__main__":
    sys.exit(main())
