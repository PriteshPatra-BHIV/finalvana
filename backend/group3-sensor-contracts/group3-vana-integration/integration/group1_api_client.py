# -*- coding: utf-8 -*-
"""Group 3 -> Group 1 VANA MasterDB Observation API client.

Built against Raj's handoff document (Group_1_to_Group_4_VANA_API_Handoff.docx),
target commit 92a37b337df1fb1d4b8565ada47656d182771cdf.

CONTRACT AS DOCUMENTED BY GROUP 1
---------------------------------
    POST /observations                    ingestion
    GET  /observations/{observation_id}   retrieval
    GET  /health                          health

    Header: Idempotency-Key: IK-<observation_id>   (confirmed by Raj 2026-08-24,
            Group 1 commit 1140f58; backend is format-agnostic, IK- is the
            agreed convention rather than an enforced prefix)

    201 Created            status ACCEPTED
    200 OK                 status IDEMPOTENT_REPLAY   (same key, same fingerprint)
    409 Conflict           status IDEMPOTENCY_CONFLICT (same key, DIFFERENT payload)
    409 Conflict           status DUPLICATE            (same observation_id, no key)

    Acceptance target on the real environment: 0 -> 1 -> 1

WHY THIS EXISTS
---------------
Group 1 has published the interface but NOT a base URL - their document says
"Live PostgreSQL/PostGIS VM deployment and final end-to-end validation: PENDING".
This client is therefore written and testable NOW, so that the moment a host
exists the acceptance run is one command, not a day of work.

Run without --base-url to see exactly what Group 3 will send (dry run).

Usage:
    python group1_api_client.py                                   # dry run
    python group1_api_client.py --base-url https://host:8000      # live run
"""
import argparse, json, io, os, re, sys, datetime

# Canonical trace convention, per Group 1's API handoff. Enforced in the
# observation contract as ^VANA-[0-9a-f]{12}$ and checked here on the way back.
TRACE_RE = re.compile(r"^VANA-[0-9a-f]{12}$")

HERE = os.path.dirname(os.path.abspath(__file__))
DAY6 = os.path.dirname(HERE)
DEFAULT_FIXTURE = os.path.join(DAY6, "contract", "sample_mission_package.v2.2.json")

# DYNAMIC (EOD rule, 2026-08-22): "No hardcoded observation_id ... is required for
# normal runtime execution." This is the actual Group 1 client, i.e. a RUNTIME path -
# it previously pinned TARGET = "TC-Z03-F02-LIDAR-OBS001" and a V1.2 fixture. Both are
# now resolved at call time. Found by self-audit 2026-08-22; an earlier note wrongly
# classified this file as a test tool.
TARGET = None   # resolved from the fixture, or --observation-id

# Statuses Group 1 documented. Anything else is an undocumented response.
EXPECTED = {
    "first":     (201, "ACCEPTED"),
    "replay":    (200, "IDEMPOTENT_REPLAY"),
    "conflict":  (409, "IDEMPOTENCY_CONFLICT"),
    "duplicate": (409, "DUPLICATE"),
}


def resolve(fixture_path, observation_id=None):
    """Resolve the target observation from the declared fixture. Never pinned."""
    global FIXTURE, TARGET
    FIXTURE = fixture_path
    pkg = json.load(io.open(FIXTURE, encoding="utf-8"))
    obs = pkg["observations"]
    TARGET = observation_id or obs[0]["observation_id"]
    if TARGET not in [o["observation_id"] for o in obs]:
        raise SystemExit("observation %s not in %s - refusing to guess" % (TARGET, FIXTURE))
    return TARGET


FIXTURE = DEFAULT_FIXTURE


def build_payload():
    """The full Group 3 V1.0 observation, exactly as the frozen contract defines it.

    NOTE: Group 1's section 7 example omits accuracy, calibration_status,
    raw_artifact_reference, quality_status, processing_status and provenance.
    Group 3 sends the COMPLETE contract record - dropping six required fields to
    match an abbreviated example would discard the device, QA and raw-evidence
    linkage that the whole exercise exists to preserve. If the API rejects the
    full record, that is a contract mismatch to resolve, not a reason to send less.
    """
    pkg = json.load(io.open(FIXTURE, encoding="utf-8"))
    obs = [o for o in pkg["observations"]
           if o.get("observation_id") == TARGET][0]
    return {k: v for k, v in obs.items() if not k.startswith("_")}


def show(title, method, path, headers, body=None):
    print("\n" + "-" * 74)
    print("%s\n%s %s" % (title, method, path))
    for k, v in headers.items():
        print("  %s: %s" % (k, v))
    if body is not None:
        s = json.dumps(body, indent=2, ensure_ascii=False)
        print("  body:")
        for line in s.splitlines():
            print("    " + line)


def call(base, method, path, headers=None, body=None):
    import urllib.request, urllib.error
    url = base.rstrip("/") + path
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.status, json.loads(r.read().decode("utf-8") or "{}")
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8")
        try:
            return e.code, json.loads(raw or "{}")
        except ValueError:
            return e.code, {"_raw": raw[:400]}
    except Exception as e:
        return None, {"_error": str(e)}


def check(label, got_code, got_body, key):
    want_code, want_status = EXPECTED[key]
    got_status = (got_body or {}).get("status")
    ok = (got_code == want_code and got_status == want_status)
    print("  [%s] %-22s expected %s/%s   got %s/%s"
          % ("PASS" if ok else "FAIL", label, want_code, want_status,
             got_code, got_status))
    trace = (got_body or {}).get("trace_id")
    if trace:
        print("        trace_id returned: %s" % trace)
    return ok, trace


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default=os.environ.get("VANA_API_BASE_URL"))
    ap.add_argument("--fixture", default=DEFAULT_FIXTURE,
                    help="Declared mission package. Defaults to the current V2.2 contract fixture.")
    ap.add_argument("--observation-id", default=None,
                    help="Target observation. Defaults to the first in the fixture. Never pinned.")
    ap.add_argument("--probe-only", action="store_true",
                    help="READ ONLY. GET /health and GET /observations/{id} only - no POST, nothing "
                         "written, nothing emitted. Use this to verify connectivity, the deployed "
                         "schema version and field persistence while emission is still gated on a "
                         "contract approval.")
    args = ap.parse_args()

    resolve(args.fixture, args.observation_id)
    payload = build_payload()
    IK_KEY = 'IK-' + TARGET   # confirmed Group 1 convention, 2026-08-24
    key = payload["observation_id"]

    print("Group 3 -> Group 1 VANA MasterDB Observation API")
    print("target commit : 92a37b337df1fb1d4b8565ada47656d182771cdf")
    print("observation   : %s" % key)
    print("run at        : %s" % datetime.datetime.now(datetime.timezone.utc).isoformat())

    if not args.base_url:
        print("\nDRY RUN - no --base-url supplied.")
        print("Group 1's handoff gives paths but no host; their document states")
        print("'Live PostgreSQL/PostGIS VM deployment ... PENDING'.")
        print("\nThis is exactly what Group 3 will send the moment a host exists:")
        show("1. FIRST INGESTION  -> expect 201 ACCEPTED",
             "POST", "/observations", {"Idempotency-Key": IK_KEY}, payload)
        show("2. EXACT REPLAY     -> expect 200 IDEMPOTENT_REPLAY",
             "POST", "/observations", {"Idempotency-Key": IK_KEY}, payload)
        show("3. RETRIEVAL        -> expect the canonical record",
             "GET", "/observations/" + key, {})
        show("4. HEALTH", "GET", "/health", {})
        print("\n" + "-" * 74)
        print("Fields Group 3 sends that Group 1's section 7 example omits:")
        for f in ("accuracy", "calibration_status", "raw_artifact_reference",
                  "quality_status", "processing_status", "provenance"):
            print("    %s" % f)
        print("\nAll six are REQUIRED by the frozen contract Group 1 reports")
        print("validating 18/18 against (contract V1.0). Confirm the API accepts them.")
        print("\nWhen the host exists:")
        print("    python group1_api_client.py --base-url https://<host>")
        return 0

    base = args.base_url
    print("target host   : %s" % base)

    # --- health
    if args.probe_only:
        print("PROBE-ONLY: read-only. No POST will be issued, nothing will be emitted.")
        print()
        code, body = call(base, "GET", "/health")
        print("1. GET /health        -> %s  %s" % (code, json.dumps(body)[:200]))
        code, body = call(base, "GET", "/observations/" + TARGET)
        obs = (body or {}).get("observation") or {}
        print("2. GET /observations/%s -> %s" % (TARGET, code))
        if obs:
            print("   observation_id : %s" % obs.get("observation_id"))
            print("   is_synthetic   : %s" % obs.get("is_synthetic"))
            for k in ("synthetic_state", "data_state", "contract_version", "provenance_reference",
                      "source_identity"):
                mark = "PRESENT" if k in obs else "absent"
                print("   %-20s %s" % (k, mark))
            fom = obs.get("field_observation_meta") or {}
            print("   accuracy_status: %s | calibration: %s | processing: %s"
                  % (fom.get("accuracy_status"), fom.get("calibration_status"),
                     fom.get("processing_status")))
        print()
        print("Read-only probe complete. No write occurred.")
        return 0

    code, body = call(base, "GET", "/health")
    print("\n[0] HEALTH        %s  %s" % (code, json.dumps(body)[:120]))
    if code != 200:
        print("    service not healthy - stopping before the acceptance run")
        return 1

    print("\nACCEPTANCE RUN  (Group 1's stated target: 0 -> 1 -> 1)")
    results = []

    code, body = call(base, "POST", "/observations", {"Idempotency-Key": IK_KEY}, payload)
    ok, trace1 = check("first ingestion", code, body, "first")
    results.append(ok)

    code, body = call(base, "POST", "/observations", {"Idempotency-Key": IK_KEY}, payload)
    ok, trace2 = check("exact replay", code, body, "replay")
    results.append(ok)

    mutated = dict(payload)
    mutated["measurement"] = 9.9
    code, body = call(base, "POST", "/observations", {"Idempotency-Key": IK_KEY}, mutated)
    ok, _ = check("idempotency conflict", code, body, "conflict")
    results.append(ok)

    code, body = call(base, "POST", "/observations", {}, payload)
    ok, _ = check("duplicate, no key", code, body, "duplicate")
    results.append(ok)

    code, body = call(base, "GET", "/observations/" + key)
    retrieved = (code == 200 and (body or {}).get("observation_id") == key)
    print("  [%s] %-22s retrieved observation_id == submitted"
          % ("PASS" if retrieved else "FAIL", "retrieval"))
    results.append(retrieved)

    print("\n" + "=" * 74)
    print("RESULT: %d/%d checks passed" % (sum(1 for r in results if r), len(results)))

    if trace1:
        conforms = bool(TRACE_RE.match(trace1))
        print("""
TRACE
  returned by Group 1 : %s
  canonical format    : VANA-<12 lowercase hex>  (^VANA-[0-9a-f]{12}$)
  conforms            : %s""" % (trace1, "YES" if conforms else "NO - INVESTIGATE"))
        if not conforms:
            print("  The API returned a trace that does not match the convention")
            print("  Group 3 has adopted and enforces in the observation contract.")
        if trace1 != trace2:
            print("  NOTE: replay returned a DIFFERENT trace (%s vs %s)." % (trace1, trace2))
            print("  An idempotent replay should return the SAME trace as the")
            print("  original ingestion, or correlation is ambiguous.")

    print("""
NOT PROVEN by this run: any hardware. The payload is is_synthetic: true.
No Group 3 sensor has produced a recorded reading. Hardware is Phase 2.""")
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
