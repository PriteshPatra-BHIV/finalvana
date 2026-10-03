# -*- coding: utf-8 -*-
"""Test Group 2 /resolve across all 7 Group 3 canonical records, after Pritesh's
timestamp-format fix.

WHY THIS EXISTS
---------------
Group 3 raised G-82 on 2026-09-01: Group 2 abstained citing
`MISSING_SOURCE_TIMESTAMP` on a record that carried a source timestamp in four
fields. The suspected cause was a format mismatch - Group 1 renders Postgres
style (`2026-08-25 11:00:00+00:00`), most parsers expect ISO-8601
(`2026-08-25T11:00:00Z`).

Pritesh confirmed that diagnosis on 2026-09-02 and deployed a fix:

    "My API was rejecting the timestamp because it was looking for the T and Z
     formatting ... I just updated the code to seamlessly accept the Postgres
     format ... without generating any fake fallback timestamps ... The code is
     already pushed and live, so it's completely ready to test."

Pratik's bundle (generated 05:18Z the same day) already showed the reason as
`CONTEXT_NOT_VERIFIED` rather than `MISSING_SOURCE_TIMESTAMP`, with
`missing_critical_data: NONE_BUT_UNVERIFIED`. Whether that run predates or
postdates Pritesh's push is NOT established, and this script does not guess.

WHAT IT ANSWERS
  1. Is `MISSING_SOURCE_TIMESTAMP` gone on all 7 records, not just the 3 tested?
  2. Does any record now resolve a non-null `context_id`?
  3. Is any ruling other than ABSTAIN reachable?

Question 3 matters: every governed outcome so far is `noop` / NOT EXECUTED, so
the ALLOW and DENY branches are unproven end to end (G-86).

SCOPE. `/resolve` is a QUERY - it asks Group 2 to evaluate an existing record.
It creates no observation and mutates nothing in Group 1. Nothing is sent to
Group 4. Run at Pritesh's explicit invitation to test.

Run:  python verify_group2_resolve_after_fix.py --g2-url <group2-resolve-endpoint>
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

RECORDS = [
    ("Thane Creek", "live_mission_package.json"),
    ("Mumbai", "live_mission_package_MU.json"),
    ("Navi Mumbai", "live_mission_package_NM.json"),
    ("Vasai", "live_mission_package_VS.json"),
    ("Thane", "live_mission_package_THN.json"),
    ("Maval", "live_mission_package_MV.json"),
    ("SAMACHAR", "live_mission_package_SAMACHAR.json"),
]


def resolve(url, oid, timeout):
    body = json.dumps({"observation_id": oid}).encode("utf-8")
    req = urllib.request.Request(
        url, data=body, method="POST",
        headers={"Content-Type": "application/json", "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")
    except Exception as e:
        return None, "TRANSPORT ERROR: %s" % e


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--g2-url", required=True,
                    help="Group 2 context resolve endpoint")
    ap.add_argument("--timeout", type=float, default=45.0)
    a = ap.parse_args()

    print("GROUP 2 /resolve - ALL 7 GROUP 3 CANONICAL RECORDS")
    print("Testing Pritesh's timestamp-format fix, at his invitation.")
    print("Query only: no observation created, nothing written to Group 1, "
          "nothing sent to Group 4.")
    print()

    rows, stale, resolved, rulings = [], 0, 0, {}
    for name, fn in RECORDS:
        local = json.load(io.open(os.path.join(LIVE, fn), encoding="utf-8"))["observations"][0]
        oid = local["observation_id"]
        status, raw = resolve(a.g2_url, oid, a.timeout)
        try:
            doc = json.loads(raw)
        except Exception:
            doc = None

        ruling = ctx = reason = missing = None
        if isinstance(doc, dict):
            ruling = doc.get("ruling")
            ctx = doc.get("context_id")
            prov = doc.get("provenance") or {}
            reason = prov.get("reason")
            ev = doc.get("evidence") or {}
            missing = ev.get("missing_critical_data")
            # did OUR timestamp reach it intact?
            ts_seen = ev.get("observation_timestamp")
        else:
            ts_seen = None

        is_stale = (reason == "MISSING_SOURCE_TIMESTAMP")
        stale += is_stale
        resolved += (ctx is not None)
        rulings[ruling] = rulings.get(ruling, 0) + 1

        rows.append({
            "region": name, "observation_id": oid, "http_status": status,
            "ruling": ruling, "context_id": ctx, "reason": reason,
            "missing_critical_data": missing,
            "observation_timestamp_seen_by_g2": ts_seen,
            "sent_observation_timestamp": local.get("observation_timestamp"),
            "STALE_TIMESTAMP_REASON": is_stale,
            "response": doc if doc is not None else raw[:2000],
        })
        print("  %-12s %-30s HTTP %-4s %-8s ctx=%-6s %s"
              % (name, oid, status, ruling or "-",
                 "SET" if ctx else "null", reason or ""))

    print()
    print("  MISSING_SOURCE_TIMESTAMP still returned : %d of %d  %s"
          % (stale, len(rows), "<- G-82 NOT fixed" if stale else "<- G-82 FIXED"))
    print("  records resolving a context_id          : %d of %d" % (resolved, len(rows)))
    print("  rulings seen                            : %s"
          % ", ".join("%s=%d" % kv for kv in sorted(rulings.items(), key=lambda x: str(x[0]))))
    if resolved == 0:
        print()
        print("  NOTE: no record resolves a context. Every outcome is an abstention, so the")
        print("        ALLOW and DENY branches remain unproven end to end (G-86). That is a")
        print("        Group 2 context/geography question, not a Group 3 data question.")

    stamp = datetime.datetime.now(datetime.timezone.utc)
    out = os.path.join(LIVE, "GROUP2_RESOLVE_AFTER_FIX_%s.json"
                       % stamp.strftime("%Y%m%dT%H%M%SZ"))
    with io.open(out, "w", encoding="utf-8") as fh:
        json.dump({
            "_README": ("Group 3's test of Group 2 /resolve across all 7 canonical "
                        "records, after Pritesh's timestamp-format fix. Query only."),
            "_endpoint": "REDACTED - supplied at run time",
            "_run_at": stamp.isoformat(),
            "_context": ("Pritesh, 2026-09-02: fix deployed for Postgres-style "
                         "timestamps, all four timestamp fields detected, no fake "
                         "fallback timestamps generated."),
            "missing_source_timestamp_count": stale,
            "records_with_context": resolved,
            "rulings": {str(k): v for k, v in rulings.items()},
            "records": rows,
        }, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    print()
    print("  -> evidence/live/%s" % os.path.basename(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
