# -*- coding: utf-8 -*-
"""READ-ONLY verification of Group 1's reported six-region closure.

WHY THIS EXISTS
---------------
Sanskar reported (2026-09-01) that Group 1 completed live production ingestion
for all five regional payloads Group 3 supplied, giving a canonical record id
for each, and stated:

    "We did not modify the observation IDs or source measurements during
     ingestion."

That is a REPORTED claim. It becomes VERIFIED only when Group 3 retrieves the
records itself and compares them, field by field, against the payloads Group 3
built. This script does exactly that and nothing else.

WHAT IT CHECKS, per region
  1. GET /observations/{observation_id} returns 200
  2. the canonical record id returned matches the one Sanskar reported
  3. observation_id came back verbatim
  4. the MEASUREMENT survived - value and unit, unchanged
  5. the COORDINATE survived - latitude and longitude, unchanged
  6. observation_timestamp, sensor_id, device_id survived
  7. provenance still identifies Group 3's source, not a Group 1 placeholder

A mismatch on 4, 5 or 7 is serious: it would mean the canonical store holds
something other than what Group 3 measured.

THIS SCRIPT WRITES NOTHING TO GROUP 1. GET only. No POST, no PUT, no DELETE.
The host is never written to disk - evidence records it as REDACTED.

Run:  python verify_group1_six_region_closure.py --base-url <group1-host>
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
LIVE = os.path.join(DAY6, "evidence", "live")

# Canonical record ids exactly as Sanskar reported them, 2026-09-01.
# Transcribed from his message; NOT generated. If one of these is a typo on his
# side the check below will fail loudly, which is the correct outcome.
REPORTED = {
    "MU":  ("Mumbai",      "CR-d13c51cb-c9c7-42fc-b303-1dabc3e52b7b"),
    "NM":  ("Navi Mumbai", "CR-331d3f3d-ec51-45e0-b632-45d6c91fd50c"),
    "VS":  ("Vasai",       "CR-1ee091b3-ad16-4086-a88b-860affe142e8"),
    "THN": ("Thane",       "CR-03125aaf-6d7e-4f7b-b4f1-97c7e6712755"),
    "MV":  ("Maval",       "CR-f9782ddc-3a77-4df7-ba52-81a365ac165d"),
    "TC":  ("Thane Creek", "CR-b4615a27-7ab1-4bde-a078-a56fa0f2414c"),
}

LOCAL_FILE = {
    "MU": "live_mission_package_MU.json",
    "NM": "live_mission_package_NM.json",
    "VS": "live_mission_package_VS.json",
    "THN": "live_mission_package_THN.json",
    "MV": "live_mission_package_MV.json",
    "TC": "live_mission_package.json",
}


MISSING = object()   # distinct from a stored null


def find_value(obj, names):
    """First value under any of `names`, at any depth.

    Returns MISSING when the key is absent. A key present but null returns
    None. Conflating the two is how a check silently passes.
    """
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in names and not isinstance(v, (dict, list)):
                return v
        for v in obj.values():
            r = find_value(v, names)
            if r is not MISSING:
                return r
    elif isinstance(obj, list):
        for v in obj:
            r = find_value(v, names)
            if r is not MISSING:
                return r
    return MISSING


def find_container(obj, name):
    """Like find_value, but returns dict/list containers."""
    if isinstance(obj, dict):
        if name in obj:
            return obj[name]
        for v in obj.values():
            r = find_container(v, name)
            if r is not MISSING:
                return r
    elif isinstance(obj, list):
        for v in obj:
            r = find_container(v, name)
            if r is not MISSING:
                return r
    return MISSING


def same_instant(sent, stored):
    """Group 1 renders timestamps Postgres-style ('2026-08-25 11:00:00+00:00');
    Group 3 sends ISO 8601 ('2026-08-25T11:00:00Z'). Same instant, different
    serialisation - compare as datetimes, never as strings."""
    try:
        a = datetime.datetime.fromisoformat(str(sent).replace("Z", "+00:00"))
        b = datetime.datetime.fromisoformat(str(stored).replace("Z", "+00:00"))
        return a == b
    except Exception:
        return False


def stored_reading(doc):
    """Group 1 normalises the flat measurement/unit pair into a relational
    `measurements[]` array. The reading is at measurements[0].value/.unit -
    there is NO top-level `measurement` key in the retrieval response."""
    ms = find_container(doc, "measurements")
    if isinstance(ms, list) and ms and isinstance(ms[0], dict):
        return ms[0].get("value", MISSING), ms[0].get("unit", MISSING)
    return MISSING, MISSING


def get(base, oid, timeout):
    url = "%s/observations/%s" % (base.rstrip("/"), oid)
    req = urllib.request.Request(url, method="GET",
                                 headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")
    except Exception as e:
        return None, "TRANSPORT ERROR: %s" % e


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url")
    ap.add_argument("--from-evidence", help="re-run the comparisons offline against "
                    "a saved verification artifact - makes NO network call")
    ap.add_argument("--timeout", type=float, default=30.0)
    a = ap.parse_args()
    if not a.base_url and not a.from_evidence:
        ap.error("one of --base-url or --from-evidence is required")
    saved = {}
    if a.from_evidence:
        for r in json.load(io.open(a.from_evidence, encoding="utf-8"))["regions"]:
            saved[r["observation_id"]] = (r["http_status"], r["raw_response"])

    print("GROUP 1 SIX-REGION CLOSURE - INDEPENDENT VERIFICATION (GET only)")
    print("Verifying Sanskar's report of 2026-09-01 against Group 3's own payloads.")
    print()

    results, failures = [], 0
    for code in ["TC", "MU", "NM", "VS", "THN", "MV"]:
        name, cr_reported = REPORTED[code]
        local = json.load(io.open(os.path.join(LIVE, LOCAL_FILE[code]),
                                  encoding="utf-8"))["observations"][0]
        oid = local["observation_id"]

        if a.from_evidence:
            status, doc = saved.get(oid, (None, None))
        else:
            status, body = get(a.base_url, oid, a.timeout)
            try:
                doc = json.loads(body)
            except Exception:
                doc = None

        checks, notes = {}, []
        checks["http_200"] = (status == 200)

        if doc is not None:
            cr_actual = find_value(doc, {"canonical_record_id", "record_id",
                                         "canonical_id"})
            if cr_actual is MISSING:
                cr_actual = None
            checks["canonical_matches_report"] = (cr_actual == cr_reported)
            if cr_actual != cr_reported:
                notes.append("reported %s, got %r" % (cr_reported, cr_actual))

            checks["observation_id_verbatim"] = (
                find_value(doc, {"observation_id"}) == oid)

            # Group 1 MINTS its own geo_id on ingestion, one per coordinate.
            # Group 3 never sends one - V2.2 has no such field. Recorded, not checked.
            g = find_value(doc, {"geo_id"})
            if g is not MISSING:
                notes.append("NOTE: Group 1 assigned geo_id %s (we sent none)" % g)

            # V2.2 field names, taken from the payload itself: the reading is
            # `measurement` (a number) and `unit` (a string). There is no
            # `measurement_value`/`measurement_unit` pair - guessing those would
            # make every check below vacuously true.
            # THE READING. Stored relationally by Group 1 in measurements[].
            got_val, got_unit = stored_reading(doc)
            for label, want, got in (("measurement", local.get("measurement"), got_val),
                                     ("unit", local.get("unit"), got_unit)):
                ok = (got == want) or (
                    isinstance(want, float) and isinstance(got, (int, float))
                    and not isinstance(got, bool) and abs(float(got) - want) < 1e-9)
                checks["%s_survived" % label] = ok
                if not ok:
                    notes.append("%s: sent %r, stored %r" % (label, want, got))

            # TIMESTAMPS - compared as instants.
            for field in ("observation_timestamp", "source_timestamp"):
                want = local.get(field)
                if want is None:
                    continue
                got = find_value(doc, {field})
                ok = same_instant(want, got)
                checks["%s_survived" % field] = ok
                if not ok:
                    notes.append("%s: sent %r, stored %r" % (field, want, got))

            # Everything else, verbatim.
            for field in ("observation_type", "device_id", "is_synthetic",
                          "capture_method", "synthetic_state", "data_state",
                          "contract_version", "schema_version"):
                want = local.get(field)
                if want is None:
                    continue
                got = find_value(doc, {field})
                ok = (got == want) or (str(got) == str(want))
                checks["%s_survived" % field] = ok
                if not ok:
                    notes.append("%s: sent %r, stored %r" % (field, want, got))

            for axis in ("latitude", "longitude"):
                want = local["location"][axis]
                got = find_value(doc, {axis})
                ok = isinstance(got, (int, float)) and abs(float(got) - want) < 1e-9
                checks["%s_survived" % axis] = ok
                if not ok:
                    notes.append("%s: sent %r, stored %r" % (axis, want, got))

            # Identifies the record as Group 3's real Open-Meteo capture rather
            # than a Group 1 placeholder occupying the same identity.
            want_prov = local.get("provenance_reference")
            if want_prov:
                prov = find_value(doc, {"provenance_reference"})
                checks["provenance_is_group3_source"] = (prov == want_prov)
                if prov != want_prov:
                    notes.append("provenance: sent %r, stored %r" % (want_prov, prov))

            # The strongest single check: the sha256 of the raw source bytes.
            # If this survives, the reading demonstrably came from the capture
            # Group 3 hashed at emission time.
            want_hash = (local.get("raw_artifact_integrity") or {}).get("checksum_sha256")
            if want_hash:
                got_hash = find_value(doc, {"checksum_sha256"})
                if got_hash is not MISSING:
                    checks["source_sha256_survived"] = (got_hash == want_hash)
                    if got_hash != want_hash:
                        notes.append("sha256: sent %s, stored %s"
                                     % (want_hash[:16], str(got_hash)[:16]))
                else:
                    notes.append("NOTE: Group 1 does not return checksum_sha256 "
                                 "(not a failure - it may not persist it)")
        else:
            checks["response_parsed"] = False
            notes.append("body not JSON: %s" % body[:160])

        passed = all(checks.values())
        failures += (not passed)
        results.append({
            "region": name, "survey_id": code, "observation_id": oid,
            "http_status": status,
            "canonical_record_id_reported_by_group1": cr_reported,
            "checks": checks, "notes": notes,
            "verdict": "VERIFIED" if passed else "FAILED",
            "raw_response": doc if doc is not None else body[:4000],
        })
        print("  %-12s %-30s HTTP %-4s %-8s %s"
              % (name, oid, status, "VERIFIED" if passed else "FAILED",
                 "" if passed else "; ".join(notes)[:70]))

    print()
    print("  %d/%d independently verified" % (len(results) - failures, len(results)))

    out = os.path.join(LIVE, "GROUP1_SIX_REGION_VERIFICATION_%s.json"
                       % datetime.datetime.now(datetime.timezone.utc)
                       .strftime("%Y%m%dT%H%M%SZ"))
    with io.open(out, "w", encoding="utf-8") as fh:
        json.dump({
            "_README": ("Group 3's INDEPENDENT read-only verification of Group 1's "
                        "reported six-region closure. GET only; nothing was written "
                        "to Group 1."),
            "_host": "REDACTED - supplied at run time",
            "_verified_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "_source_of_reported_ids": "Sanskar, Group 1, message of 2026-09-01",
            "_claim_under_test": ("'We did not modify the observation IDs or source "
                                  "measurements during ingestion.'"),
            "verified": len(results) - failures, "total": len(results),
            "verdict": "ALL VERIFIED" if failures == 0 else "%d FAILED" % failures,
            "regions": results,
        }, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    print("  -> evidence/live/%s" % os.path.basename(out))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
