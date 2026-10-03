# -*- coding: utf-8 -*-
"""LIVE Group 3 -> Group 1 acceptance run against the deployed VANA MasterDB API.

Group 1 published a live host on 2026-08-19 (Raj Prajapati):

    Service:  VANA MasterDB Observation API
    Base URL: NOT RECORDED HERE - see the note below
    Runtime:  PostgreSQL 16 + PostGIS 3.4
    Status:   LIVE / VERIFIED

The base URL is deliberately NOT written into this file. Group 1's API has no
authentication, and this repository is destined to be public. Supply the host
at run time via --base-url or the VANA_API_BASE_URL environment variable; this
script refuses to guess one.

This is the first LIVE evidence Group 3 has been able to produce. Every prior
Group 1 proof was CONTROLLED/LOCAL - our own container running their schema.

SAFETY NOTE
-----------
This writes to Group 1's live database. It is the action the task requires
("Group 1 ingestion: prove acceptance or capture the exact runtime blocker")
and the endpoint was published to Group 3 for exactly this purpose. The
observation carries is_synthetic=true and a Group-3-namespaced id, and the
idempotency contract makes a repeat run safe by design.

The base URL is NOT hardcoded into any file pushed to a public repository -
it is read from the environment or passed in. See --base-url.

Usage:
    python live_acceptance_group1.py --base-url http://HOST:PORT
"""
import argparse, io, json, os, sys, datetime, urllib.request, urllib.error

HERE = os.path.dirname(os.path.abspath(__file__))
DAY6 = os.path.dirname(HERE)
DEFAULT_FIXTURE = os.path.join(DAY6, "contract", "sample_mission_package.v2.2.json")

EXPECTED = {
    "first":     (201, "ACCEPTED"),
    "replay":    (200, "IDEMPOTENT_REPLAY"),
    "conflict":  (409, "IDEMPOTENCY_CONFLICT"),
}


def call(base, method, path, headers=None, body=None):
    url = base.rstrip("/") + path
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=40) as r:
            return r.status, json.loads(r.read().decode("utf-8") or "{}")
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8")
        try:
            return e.code, json.loads(raw or "{}")
        except ValueError:
            return e.code, {"_raw": raw[:600]}
    except Exception as e:
        return None, {"_error": str(e)}


res = []


def rec(label, ok, detail=""):
    print("  [%s] %-40s %s" % ("PASS" if ok else "FAIL", label, detail))
    res.append(ok)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default=os.environ.get("VANA_API_BASE_URL"))
    ap.add_argument("--fixture", default=DEFAULT_FIXTURE,
                    help="Mission package to submit. Defaults to the CURRENT V2.2 contract fixture. "
                         "Pass ../contract/sample_mission_package.v2.json for the legacy V2.1 path, "
                         "which is what Group 1's live validator accepted before V2.2 alignment.")
    a = ap.parse_args()
    if not a.base_url:
        print("No --base-url and VANA_API_BASE_URL unset. Refusing to guess a host.")
        return 2
    base = a.base_url

    obs = json.load(io.open(a.fixture, encoding="utf-8"))["observations"][0]
    obs = {k: v for k, v in obs.items() if not k.startswith("_")}
    oid = obs["observation_id"]
    IK_KEY = 'IK-' + oid   # confirmed Group 1 convention, 2026-08-24

    print("GROUP 3 -> GROUP 1  LIVE ACCEPTANCE RUN")
    print("host        : %s" % base)
    print("observation : %s" % oid)
    print("fixture     : %s" % os.path.basename(a.fixture))
    print("schema      : V%s" % obs.get("schema_version"))
    print("is_synthetic: %s" % obs.get("is_synthetic"))
    print("run at      : %s" % datetime.datetime.now(datetime.timezone.utc).isoformat())
    print()

    code, body = call(base, "GET", "/health")
    rec("health", code == 200, "%s %s" % (code, (body or {}).get("service", "")))
    if code != 200:
        print("\n  service unreachable - stopping"); return 1

    print()
    print("ACCEPTANCE SEQUENCE (Group 1's stated target: 0 -> 1 -> 1)")

    code, body = call(base, "POST", "/observations", {"Idempotency-Key": IK_KEY}, obs)
    want = EXPECTED["first"]
    st = (body or {}).get("status")
    ok = (code, st) == want
    trace1 = (body or {}).get("trace_id")
    rec("1. first ingestion", ok, "expected %s/%s got %s/%s" % (want[0], want[1], code, st))
    if not ok:
        print("      response: %s" % json.dumps(body)[:500])
    if trace1:
        print("      trace_id returned: %s" % trace1)

    code, body = call(base, "POST", "/observations", {"Idempotency-Key": IK_KEY}, obs)
    want = EXPECTED["replay"]
    st = (body or {}).get("status")
    ok = (code, st) == want
    trace2 = (body or {}).get("trace_id")
    rec("2. exact replay", ok, "expected %s/%s got %s/%s" % (want[0], want[1], code, st))

    mutated = json.loads(json.dumps(obs))
    mutated["measurement"] = {"artifact": "SUBSTITUTED-EVIDENCE.JPG"}
    code, body = call(base, "POST", "/observations", {"Idempotency-Key": IK_KEY}, mutated)
    want = EXPECTED["conflict"]
    st = (body or {}).get("status")
    ok = (code, st) == want
    rec("3. same key, mutated payload", ok,
        "expected %s/%s got %s/%s" % (want[0], want[1], code, st))

    code, body = call(base, "GET", "/observations/" + oid)
    got = (body or {}).get("observation") or {}
    rec("4. retrieval", code == 200 and got.get("observation_id") == oid,
        "observation_id preserved verbatim")

    print()
    print("CANONICAL RECORD REMAINS UNCHANGED AFTER CONFLICT")
    meas = got.get("measurements") or [{}]
    arts = got.get("raw_artifacts") or [{}]
    substituted = any("SUBSTITUTED" in str(m.get("value_text") or "") for m in meas) or \
                  any("SUBSTITUTED" in str(x.get("storage_ref") or "") for x in arts)
    rec("5. mutation did NOT overwrite the record", not substituted,
        "conflict rejected without corrupting canonical state")

    print()
    print("FIELD PERSISTENCE - what actually survived")
    geo = got.get("geo_location") or {}
    fom = got.get("field_observation_meta") or {}
    checks = [
        ("is_synthetic", got.get("is_synthetic"), True),
        ("capture_method", got.get("capture_method"), obs.get("capture_method")),
        ("quality_status", got.get("quality_status"), obs.get("quality_state")),
        ("location.altitude_m", geo.get("altitude_m"), (obs.get("location") or {}).get("altitude_m")),
        ("gnss_status", fom.get("gnss_status"), (obs.get("location") or {}).get("gnss_status")),
        ("position_accuracy_m", fom.get("position_accuracy_m"),
         (obs.get("location") or {}).get("position_accuracy_m")),
        ("calibration_status", fom.get("calibration_status"), obs.get("calibration_state")),
        ("device_id", fom.get("device_id"), obs.get("device_id")),
    ]
    for label, got_v, sent_v in checks:
        ok = (got_v == sent_v) or (sent_v is None and got_v is None)
        print("    [%s] %-22s sent=%-22r got=%r"
              % ("PASS" if ok else "----", label, sent_v, got_v))
        if sent_v is not None:
            res.append(ok)

    print()
    print("    tidal_state sent=%r  -> deferred to v0.5, NOT expected to persist"
          % (obs.get("tidal_state") or {}).get("state"))

    print()
    print("=" * 74)
    print("RESULT: %d/%d checks passed" % (sum(1 for r in res if r), len(res)))
    if trace1:
        print()
        print("TRACE: %s" % trace1)
        import re
        print("  matches Group 1 convention ^VANA-[0-9a-f]{12}$ : %s"
              % bool(re.match(r"^VANA-[0-9a-f]{12}$", trace1)))
        if trace1 != trace2:
            print("  NOTE: replay returned a different trace (%s)" % trace2)
    print()
    print("CLASSIFICATION: LIVE. This ran against Group 1's deployed")
    print("PostgreSQL 16 + PostGIS 3.4 instance, not a local container.")
    print()
    print("STILL NOT PROVEN: any hardware. The observation is is_synthetic=true.")
    print("No Group 3 sensor has produced a recorded reading.")
    return 0 if all(res) else 1


if __name__ == "__main__":
    sys.exit(main())
