# -*- coding: utf-8 -*-
"""READ-ONLY probe of Group 1 state after Rukayya's closing-day verification.

WHY THIS EXISTS
---------------
Rukayya reported (2026-08-29) six-region closure:
    POST /ingest/observations -> 201
    GET  /observations/{observation_id} -> 200
    Replay/idempotency -> 200
for Mumbai, Navi Mumbai, Vasai, Thane, Maval and ALIBAUG.

Three things must be established BEFORE Group 3 posts anything:

  1. THE INGEST PATH CHANGED. Every Group 3 client posts to `POST /observations`.
     Rukayya documents `POST /ingest/observations`. If that is now the real path,
     our emitters are pointed at the wrong route.

  2. WHOSE RECORDS ARE THEY? If Group 1 ingested its own placeholder records for
     these regions, Group 3's five real Open-Meteo payloads are still not in, and
     those identities are already occupied. Posting ours could 409 or duplicate.
     A Group 3 record is identifiable: provenance_reference starts "open-meteo:".

  3. ALIBAUG IS NOT IN OUR REGISTER. Arya ruled survey/zone identity for exactly
     five regions - MU, NM, VS, THN, MV. Alibaug was never ruled and has no
     survey_id. And Group 3's sixth region is Thane CREEK (TC/Z03), which is not
     obviously the "Thane" in Rukayya's list.

THIS SCRIPT WRITES NOTHING. GET only. No POST, no PUT, no DELETE.
It exists so the question is answered by evidence rather than assumption.

Run:  python probe_group1_six_region_state.py --base-url <group1-host>
"""
import argparse
import io
import json
import os
import sys
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
DAY6 = os.path.dirname(HERE)

# Group 3's five ruled identities, plus the pre-existing Thane Creek baseline.
OURS = [
    ("Mumbai",       "MU-Z01-EXT-OPENMETEO-OBS001"),
    ("Navi Mumbai",  "NM-Z01-EXT-OPENMETEO-OBS001"),
    ("Vasai",        "VS-Z01-EXT-OPENMETEO-OBS001"),
    ("Thane (city)", "THN-Z01-EXT-OPENMETEO-OBS001"),
    ("Maval",        "MV-Z01-EXT-OPENMETEO-OBS001"),
    ("Thane Creek",  "TC-Z03-EXT-OPENMETEO-OBS001"),
]

TIMEOUT = 25


def get(url):
    """GET only. Returns (status, parsed_body_or_text)."""
    req = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            raw = r.read().decode("utf-8", "replace")
            try:
                return r.status, json.loads(raw)
            except ValueError:
                return r.status, raw
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", "replace")
        try:
            return e.code, json.loads(raw)
        except ValueError:
            return e.code, raw
    except Exception as e:
        return None, "%s: %s" % (type(e).__name__, e)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--base-url", default=os.environ.get("VANA_API_BASE_URL"),
                    help="Group 1 host. Never committed - pass it or set VANA_API_BASE_URL.")
    args = ap.parse_args()
    if not args.base_url:
        print("No --base-url and no VANA_API_BASE_URL. This script refuses to guess a host.",
              file=sys.stderr)
        return 2
    base = args.base_url.rstrip("/")

    print("=" * 78)
    print("READ-ONLY PROBE OF GROUP 1 STATE  (GET only - nothing is written)")
    print("=" * 78)

    # --- 1. service up? -------------------------------------------------
    code, body = get(base + "/health")
    print("\n1. SERVICE")
    print("   GET /health -> %s   %s" % (code, json.dumps(body)[:90] if code else body))

    # --- 2. what routes actually exist? ---------------------------------
    print("\n2. ROUTE DISCOVERY  (does /ingest/observations exist?)")
    code, body = get(base + "/openapi.json")
    if code == 200 and isinstance(body, dict) and "paths" in body:
        paths = sorted(body["paths"].keys())
        for p in paths:
            methods = ",".join(sorted(m.upper() for m in body["paths"][p]))
            mark = ""
            if p.rstrip("/") == "/observations":
                mark = "   <- what every Group 3 client currently posts to"
            if "ingest" in p:
                mark = "   <- what Rukayya documented"
            print("     %-42s %s%s" % (p, methods, mark))
    else:
        print("     /openapi.json -> %s (route list unavailable; not a failure)" % code)

    # --- 3. six-region state, and WHOSE record it is --------------------
    print("\n3. SIX-REGION STATE  (and whose record occupies each identity)")
    print("   %-13s %-30s %-5s %s" % ("REGION", "OBSERVATION_ID", "HTTP", "OCCUPANT"))
    summary = {"ours": [], "theirs": [], "absent": [], "error": []}
    for region, oid in OURS:
        code, body = get(base + "/observations/" + oid)
        occupant = ""
        if code == 200:
            obs = body.get("observation", body) if isinstance(body, dict) else {}
            prov = obs.get("provenance_reference") or ""
            crid = obs.get("canonical_record_id") or "?"
            if str(prov).startswith("open-meteo:"):
                occupant = "GROUP 3 record  %s  %s" % (prov[:26], crid[:14])
                summary["ours"].append(region)
            else:
                occupant = "NOT ours - provenance=%r  %s" % (prov, crid[:14])
                summary["theirs"].append(region)
        elif code == 404:
            occupant = "absent - identity still free"
            summary["absent"].append(region)
        else:
            occupant = str(body)[:46]
            summary["error"].append(region)
        print("   %-13s %-30s %-5s %s" % (region, oid, code, occupant))

    # --- 4. what this means ---------------------------------------------
    print("\n4. READING")
    if summary["ours"]:
        print("   Group 3 records present : %s" % ", ".join(summary["ours"]))
    if summary["theirs"]:
        print("   OCCUPIED BY NON-GROUP-3 RECORDS: %s" % ", ".join(summary["theirs"]))
        print("     -> Group 1 ingested something else under our ruled identities.")
        print("        Do NOT post over these. Ask what they contain first.")
    if summary["absent"]:
        print("   Still absent (safe to post): %s" % ", ".join(summary["absent"]))
    if summary["error"]:
        print("   Errored: %s" % ", ".join(summary["error"]))

    print("\n   ALIBAUG: not probed. It has no Group 3 identity - Arya ruled five")
    print("   regions and Alibaug was not among them. If Group 1 holds an Alibaug")
    print("   record, its survey_id was assigned outside the contract owner's ruling")
    print("   and Arya should confirm it before it is treated as canonical.")

    print("\n   NOTHING WAS WRITTEN BY THIS SCRIPT.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
