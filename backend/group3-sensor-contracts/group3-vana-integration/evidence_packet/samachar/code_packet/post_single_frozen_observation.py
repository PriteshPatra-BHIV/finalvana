# -*- coding: utf-8 -*-
"""ONE clean POST of ONE frozen observation. Nothing else.

WHY THIS EXISTS
---------------
Sanskar, 2026-08-29, after Alay confirmed the deployment is live:

    "before retrying all five, let's test Mumbai first using the exact frozen
     identity MU-Z01-EXT-OPENMETEO-OBS001 ... using the exact frozen coordinate
     19.0430, 72.8530 and no ID/coordinate substitutions. Please send me the
     actual POST response/status and observation ID."

Group 3's existing acceptance scripts CANNOT be used for this. Both
`live_acceptance_group1.py` and `group1_api_client.py` run a multi-POST
acceptance sequence whose third step deliberately sends a MUTATED payload
(`measurement` replaced with "SUBSTITUTED-EVIDENCE.JPG" / 9.9) to prove the
409 IDEMPOTENCY_CONFLICT path.

That is a legitimate negative test, but running it here would be wrong twice
over: Sanskar explicitly asked for no substitutions, and a substituted-evidence
POST landing in Group 1's log moments after that instruction would read exactly
like the thing he prohibited.

So this script does the minimum he asked for and nothing more:

    1. ASSERT the payload matches the frozen identity - abort if it does not
    2. POST it ONCE, unmodified
    3. GET it back ONCE
    4. Print the actual status, body and observation_id, verbatim
    5. Write the exchange to evidence/ so the result is citable

NO replay. NO mutation. NO conflict test. NO retry loop. One POST.

Run:
    python post_single_frozen_observation.py \\
        --base-url <group1-host> \\
        --fixture ../evidence/live/live_mission_package_MU.json \\
        --expect-id MU-Z01-EXT-OPENMETEO-OBS001 \\
        --expect-lat 19.0430 --expect-lon 72.8530
"""
import argparse
import datetime
import io
import json
import os
import sys
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
DAY6 = os.path.dirname(HERE)
TIMEOUT = 40


def call(url, method, headers, body=None):
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            raw = r.read().decode("utf-8", "replace")
            try:
                return r.status, json.loads(raw), raw
            except ValueError:
                return r.status, None, raw
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", "replace")
        try:
            return e.code, json.loads(raw), raw
        except ValueError:
            return e.code, None, raw
    except Exception as e:
        return None, None, "%s: %s" % (type(e).__name__, e)


def discover_ingest_path(base, override):
    """G-46: Group 3 clients use POST /observations; Rukayya documented
    POST /ingest/observations. Ask the service rather than guessing."""
    if override:
        return override, "supplied via --ingest-path"
    code, body, _ = call(base + "/openapi.json", "GET", {})
    if code == 200 and isinstance(body, dict) and isinstance(body.get("paths"), dict):
        paths = body["paths"]
        for cand in ("/ingest/observations", "/observations"):
            spec = paths.get(cand)
            if isinstance(spec, dict) and "post" in {k.lower() for k in spec}:
                return cand, "discovered from /openapi.json"
    return "/observations", "DEFAULT - route discovery unavailable, using the historic path"


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--base-url", default=os.environ.get("VANA_API_BASE_URL"))
    ap.add_argument("--fixture", required=True)
    ap.add_argument("--expect-id", required=True,
                    help="The frozen observation_id. Aborts on any mismatch.")
    ap.add_argument("--expect-lat", type=float, required=True)
    ap.add_argument("--expect-lon", type=float, required=True)
    ap.add_argument("--ingest-path", default=None,
                    help="Override the POST path. Otherwise discovered from /openapi.json.")
    args = ap.parse_args()

    if not args.base_url:
        print("No --base-url and no VANA_API_BASE_URL. Refusing to guess a host.", file=sys.stderr)
        return 2
    base = args.base_url.rstrip("/")

    fixture = args.fixture if os.path.isabs(args.fixture) else os.path.join(HERE, args.fixture)
    pkg = json.load(io.open(fixture, encoding="utf-8"))
    obs = pkg["observations"][0]

    # ---- 1. ASSERT THE FROZEN IDENTITY. Abort rather than substitute. ----
    print("=" * 78)
    print("SINGLE CLEAN POST - no replay, no mutation, no substitution")
    print("=" * 78)
    print("\n1. FROZEN IDENTITY CHECK  (abort on any mismatch)")
    problems = []
    if obs.get("observation_id") != args.expect_id:
        problems.append("observation_id is %r, expected %r"
                        % (obs.get("observation_id"), args.expect_id))
    lat = (obs.get("location") or {}).get("latitude")
    lon = (obs.get("location") or {}).get("longitude")
    if lat is None or abs(float(lat) - args.expect_lat) > 1e-9:
        problems.append("latitude is %r, expected %r" % (lat, args.expect_lat))
    if lon is None or abs(float(lon) - args.expect_lon) > 1e-9:
        problems.append("longitude is %r, expected %r" % (lon, args.expect_lon))
    print("   observation_id  %s" % obs.get("observation_id"))
    print("   latitude        %s" % lat)
    print("   longitude       %s" % lon)
    print("   idempotency_key %s" % obs.get("idempotency_key"))
    if problems:
        print("\n   ABORTED - the fixture does not match the frozen identity:")
        for p in problems:
            print("     - %s" % p)
        print("   Nothing was sent. This script does not substitute values.")
        return 1
    print("   MATCH - sending this payload byte-for-byte, unmodified.")

    # ---- 2. which path does the deployed service actually serve? ----
    path, how = discover_ingest_path(base, args.ingest_path)
    print("\n2. INGEST PATH")
    print("   using POST %s   (%s)" % (path, how))

    code, body, _ = call(base + "/health", "GET", {})
    print("   GET /health -> %s" % code)
    if code != 200:
        print("   service not healthy - stopping before the POST.")
        return 1

    # ---- 3. ONE POST ----
    ik = obs.get("idempotency_key") or ("IK-" + obs["observation_id"])
    print("\n3. POST  (one request, exactly once)")
    pcode, pbody, praw = call(base + path, "POST", {"Idempotency-Key": ik}, obs)
    print("   POST %s -> HTTP %s" % (path, pcode))
    print("   response: %s" % (praw[:600] if praw else "(empty)"))

    # ---- 4. ONE GET ----
    print("\n4. GET  (read back)")
    gcode, gbody, graw = call(base + "/observations/" + obs["observation_id"], "GET", {})
    print("   GET /observations/%s -> HTTP %s" % (obs["observation_id"], gcode))
    crid = None
    if gcode == 200 and isinstance(gbody, dict):
        rec = gbody.get("observation", gbody)
        crid = rec.get("canonical_record_id")
        for k in ("observation_id", "canonical_record_id", "contract_version",
                  "source_timestamp", "provenance_reference", "synthetic_state",
                  "is_synthetic", "hardware_verified", "data_state", "quality_state"):
            print("     %-22s %s" % (k, json.dumps(rec.get(k))))
    else:
        print("   body: %s" % (graw[:400] if graw else "(empty)"))

    # ---- 5. evidence ----
    stamp = datetime.datetime.now(datetime.timezone.utc)
    out_dir = os.path.join(DAY6, "evidence", "live")
    if not os.path.isdir(out_dir):
        os.makedirs(out_dir)
    out = os.path.join(out_dir, "SINGLE_POST_%s_%s.json"
                       % (obs["observation_id"], stamp.strftime("%Y%m%dT%H%M%SZ")))
    with io.open(out, "w", encoding="utf-8") as fh:
        json.dump({
            "_what": "One clean POST + GET, no mutation, per Sanskar's instruction 2026-08-29",
            "run_at_utc": stamp.isoformat(),
            "ingest_path_used": path,
            "ingest_path_resolution": how,
            "observation_id": obs["observation_id"],
            "latitude": lat, "longitude": lon,
            "idempotency_key": ik,
            "post_status": pcode, "post_response": pbody if pbody is not None else praw,
            "get_status": gcode, "canonical_record_id": crid,
            "get_response": gbody if gbody is not None else graw,
        }, fh, indent=2, ensure_ascii=False)
        fh.write("\n")

    print("\n5. RESULT TO SEND SANSKAR")
    print("   observation_id       %s" % obs["observation_id"])
    print("   POST status          HTTP %s" % pcode)
    print("   GET status           HTTP %s" % gcode)
    print("   canonical_record_id  %s" % (crid or "(not returned)"))
    print("   evidence             evidence/live/%s" % os.path.basename(out))
    print("\n   ONE POST WAS SENT. No replay, no mutation, no retry.")
    return 0 if pcode in (200, 201) else 1


if __name__ == "__main__":
    sys.exit(main())
