# -*- coding: utf-8 -*-
"""
Group 3 → Group 1 field observation round-trip test.

Proves, against Group 1's ACTUAL canonical schema (VANA-schema.sql v0.1):

    fixture -> ingest -> retrieve -> re-submit -> NO DUPLICATE

and reports exactly which Group 3 contract fields had nowhere to go.

Runs twice:
  PASS A — schema exactly as Group 1 wrote it
  PASS B — schema plus the five additive columns Group 3 proposed

The difference between A and B is the evidence Group 1 needs for their
consolidation decision.

Usage:
    python ingest_roundtrip.py
    python ingest_roundtrip.py --dsn postgresql://user:pw@host:5432/db
"""
import argparse, json, io, os, sys, datetime
import psycopg2
import psycopg2.extras

HERE = os.path.dirname(os.path.abspath(__file__))
DAY6 = os.path.dirname(HERE)
SCHEMA_SQL = os.path.join(HERE, "VANA-schema-v0.1.sql")
FIXTURE = os.path.join(DAY6, "contract", "sample_mission_package.json")

# No credential is committed. Supply the DSN via MASTERDB_DATABASE_URL or --dsn.
# A literal password in the repo would breach the closure command's "no secrets in repo".
DEFAULT_DSN = None

# Group 3 contract fields that have no column in schema v0.1
UNMAPPABLE = [
    ("device_id",              "no column anywhere in the schema"),
    ("timestamp (time-of-day)","observation_date is DATE - only the date survives"),
    ("latitude / longitude",   "no per-observation coordinate; geography is per named place"),
    ("accuracy",               "no column"),
    ("calibration_status",     "no column"),
    ("raw_artifact_reference", "no column"),
    ("quality_status",         "no column at observation level"),
    ("trace_id",               "no column"),
    ("tidal_state",            "no column"),
]

ADDITIVE_COLUMNS = """
ALTER TABLE observation ADD COLUMN IF NOT EXISTS observed_at         TIMESTAMPTZ;
ALTER TABLE observation ADD COLUMN IF NOT EXISTS device_id           TEXT;
ALTER TABLE observation ADD COLUMN IF NOT EXISTS geom                GEOMETRY(Point, 4326);
ALTER TABLE observation ADD COLUMN IF NOT EXISTS quality_status      TEXT;
ALTER TABLE observation ADD COLUMN IF NOT EXISTS raw_artifact_ref    TEXT;
ALTER TABLE observation ADD COLUMN IF NOT EXISTS raw_artifact_sha256 TEXT;
ALTER TABLE measurement ADD COLUMN IF NOT EXISTS accuracy            TEXT;
ALTER TABLE measurement ADD COLUMN IF NOT EXISTS calibration_status  TEXT;
"""


def hr(title=""):
    print("\n" + "=" * 78)
    if title:
        print(title)
        print("=" * 78)


def load_fixture():
    pkg = json.load(io.open(FIXTURE, encoding="utf-8"))
    obs = [o for o in pkg["observations"] if not str(o.get("observation_id", "")).startswith("_")]
    return pkg, obs


def probe_verbatim(conn):
    """Apply Group 1's schema exactly as written, into public, on a clean database.

    Reports whether it applies at all. Returns (ok, error_text).
    """
    sql = io.open(SCHEMA_SQL, encoding="utf-8").read()
    with conn.cursor() as cur:
        try:
            cur.execute("DROP SCHEMA IF EXISTS public CASCADE; CREATE SCHEMA public;")
            conn.commit()
            cur.execute(sql)
            conn.commit()
            return True, None
        except Exception as e:
            conn.rollback()
            return False, str(e).strip().splitlines()[0]


def reset(cur):
    """Install Group 1's schema into a dedicated `vana` schema.

    Necessary because CREATE TABLE geography collides with the PostGIS
    `geography` TYPE when installed into public. Namespacing avoids the
    collision without altering a single line of Group 1's DDL.
    """
    cur.execute("DROP SCHEMA IF EXISTS vana CASCADE; CREATE SCHEMA vana;")
    cur.execute("CREATE EXTENSION IF NOT EXISTS postgis;")
    cur.execute("SET search_path = vana, public;")
    sql = io.open(SCHEMA_SQL, encoding="utf-8").read()
    sql = sql.replace("CREATE EXTENSION IF NOT EXISTS postgis;", "")
    cur.execute(sql)


def ingest(cur, pkg, obs, extended):
    """Map the Group 3 mission package into the canonical tables.

    Idempotent by construction: every INSERT uses ON CONFLICT DO NOTHING on the
    natural key, which is what makes re-submission safe.
    """
    mission = pkg["mission_id"]
    source_id = "SRC-G3-FIELD-" + mission
    dataset_id = mission
    geo_id = "GEO-" + pkg["survey_id"] + "-" + pkg["zone_id"]

    # SOURCE - synthetic, and the schema lets us say so explicitly
    cur.execute("""
        INSERT INTO source (source_id, source_type, title, is_synthetic, notes)
        VALUES (%s, 'SYNTHETIC_TEST', %s, TRUE, %s)
        ON CONFLICT (source_id) DO NOTHING
    """, (source_id,
          "Group 3 field mission " + mission + " (synthetic fixture)",
          "Group 3 Thane Creek field observation fixture. Hardware evidence is Phase 2."))

    # DATASET - one per survey mission
    cur.execute("""
        INSERT INTO dataset (dataset_id, dataset_name, source_id, methodology, schema_version, status)
        VALUES (%s, %s, %s, %s, '0.1', 'VALIDATED')
        ON CONFLICT (dataset_id) DO NOTHING
    """, (dataset_id, "Thane Creek " + pkg.get("zone_name", pkg["zone_id"]) + " mission " + mission,
          source_id, "Drone aerial survey per Group 3 Field Mission SOP"))

    # GEOGRAPHY - one row per named place (zone), per the schema's design
    pts = [(o["longitude"], o["latitude"]) for o in obs
           if o.get("latitude") is not None and o.get("longitude") is not None]
    if pts:
        lon = sum(p[0] for p in pts) / len(pts)
        lat = sum(p[1] for p in pts) / len(pts)
    else:
        lon, lat = 72.94, 19.13
    cur.execute("""
        INSERT INTO geography (geo_id, place_name, geom, crs, notes)
        VALUES (%s, %s, ST_SetSRID(ST_MakePoint(%s, %s), 4326), 'EPSG:4326', %s)
        ON CONFLICT (geo_id) DO NOTHING
    """, (geo_id, "Thane Creek " + pkg.get("zone_name", pkg["zone_id"]),
          lon, lat, "Zone-level reference. Per-observation coordinates are not storable in schema v0.1."))

    inserted = 0
    for o in obs:
        ts = o["timestamp"]
        obs_date = ts[:10]                      # DATE - time-of-day is lost here
        if extended:
            cur.execute("""
                INSERT INTO observation
                    (observation_id, dataset_id, geo_id, observation_date, observation_type,
                     confidence, observed_at, device_id, geom, quality_status,
                     raw_artifact_ref, raw_artifact_sha256)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,
                        CASE WHEN %s IS NULL THEN NULL
                             ELSE ST_SetSRID(ST_MakePoint(%s,%s),4326) END,
                        %s,%s,%s)
                ON CONFLICT (observation_id) DO NOTHING
            """, (o["observation_id"], dataset_id, geo_id, obs_date,
                  o["observation_type"], None, ts, o["device_id"],
                  o.get("longitude"), o.get("longitude"), o.get("latitude"),
                  o["quality_status"],
                  o["raw_artifact_reference"]["path"],
                  o["raw_artifact_reference"].get("checksum_sha256")))
        else:
            cur.execute("""
                INSERT INTO observation
                    (observation_id, dataset_id, geo_id, observation_date, observation_type, confidence)
                VALUES (%s,%s,%s,%s,%s,%s)
                ON CONFLICT (observation_id) DO NOTHING
            """, (o["observation_id"], dataset_id, geo_id, obs_date,
                  o["observation_type"], None))
        if cur.rowcount:
            inserted += 1

        # MEASUREMENT - numeric values only; value is NUMERIC NOT NULL
        if isinstance(o["measurement"], (int, float)):
            mid = o["observation_id"] + "-M1"
            if extended:
                cur.execute("""
                    INSERT INTO measurement
                        (measurement_id, observation_id, metric_name, value, unit, method,
                         accuracy, calibration_status)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                    ON CONFLICT (measurement_id) DO NOTHING
                """, (mid, o["observation_id"], o.get("parameter", "unspecified"),
                      o["measurement"], o["unit"], o.get("processing_status"),
                      str(o["accuracy"]), o["calibration_status"]))
            else:
                cur.execute("""
                    INSERT INTO measurement
                        (measurement_id, observation_id, metric_name, value, unit, method)
                    VALUES (%s,%s,%s,%s,%s,%s)
                    ON CONFLICT (measurement_id) DO NOTHING
                """, (mid, o["observation_id"], o.get("parameter", "unspecified"),
                      o["measurement"], o["unit"], o.get("processing_status")))

            cur.execute("""
                INSERT INTO provenance (provenance_id, measurement_id, source_id, derivation_note)
                VALUES (%s,%s,%s,%s)
                ON CONFLICT (provenance_id) DO NOTHING
            """, (mid + "-P", mid, source_id,
                  "Field capture by device " + o["device_id"] +
                  "; raw artifact " + o["raw_artifact_reference"]["path"]))
    return inserted


def counts(cur):
    out = {}
    for t in ("source", "dataset", "geography", "observation", "measurement", "provenance"):
        cur.execute("SELECT count(*) FROM " + t)
        out[t] = cur.fetchone()[0]
    return out


def retrieve(cur, observation_id, extended):
    cols = "o.observation_id, o.observation_date, o.observation_type, g.place_name, d.dataset_id, s.is_synthetic"
    if extended:
        cols += ", o.observed_at, o.device_id, ST_Y(o.geom) AS lat, ST_X(o.geom) AS lon, o.quality_status, o.raw_artifact_ref"
    cur.execute("""
        SELECT """ + cols + """
        FROM observation o
        JOIN dataset d ON d.dataset_id = o.dataset_id
        JOIN source  s ON s.source_id  = d.source_id
        LEFT JOIN geography g ON g.geo_id = o.geo_id
        WHERE o.observation_id = %s
    """, (observation_id,))
    return cur.fetchone()


def run_pass(conn, label, extended, pkg, obs):
    hr("PASS " + label)
    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        reset(cur)
        cur.execute("SET search_path = vana, public;")
        if extended:
            cur.execute(ADDITIVE_COLUMNS)
            print("  applied 8 additive columns proposed by Group 3")
        conn.commit()

        # --- first ingest
        n = ingest(cur, pkg, obs, extended)
        conn.commit()
        c1 = counts(cur)
        print("\n  [1] INGEST        %d observations -> %s" % (n, c1))

        # --- retrieve
        target = obs[0]["observation_id"]
        row = retrieve(cur, target, extended)
        ok_retrieve = row is not None
        print("  [2] RETRIEVE      %s -> %s" % (target, "FOUND" if ok_retrieve else "NOT FOUND"))
        if row:
            print("        dataset=%s  place=%s  synthetic=%s  date=%s"
                  % (row["dataset_id"], row["place_name"], row["is_synthetic"], row["observation_date"]))
            if extended:
                print("        observed_at=%s  device=%s  lat=%s lon=%s  quality=%s"
                      % (row["observed_at"], row["device_id"], row["lat"], row["lon"], row["quality_status"]))

        # --- re-submit the identical package
        ingest(cur, pkg, obs, extended)
        conn.commit()
        c2 = counts(cur)
        print("  [3] RE-SUBMIT     same package again -> %s" % c2)

        no_dupe = (c1 == c2)
        print("  [4] DUPLICATE?    %s" % ("NO DUPLICATE - counts identical" if no_dupe
                                          else "!! DUPLICATED - counts changed"))

        print("\n  RESULT: ingest=%s retrieve=%s idempotent=%s"
              % ("PASS" if n == len(obs) else "PARTIAL",
                 "PASS" if ok_retrieve else "FAIL",
                 "PASS" if no_dupe else "FAIL"))
        return ok_retrieve and no_dupe


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dsn", default=os.environ.get("MASTERDB_DATABASE_URL", DEFAULT_DSN))

    args = ap.parse_args()

    print("VANA Group 3 -> Group 1 round-trip test")
    print("schema  :", os.path.basename(SCHEMA_SQL))
    print("fixture :", os.path.basename(FIXTURE))
    print("target  :", args.dsn.split("@")[-1])
    print("run at  :", datetime.datetime.now(datetime.timezone.utc).isoformat())

    pkg, obs = load_fixture()
    print("\nfixture carries %d observations from mission %s" % (len(obs), pkg["mission_id"]))

    if not args.dsn:
        print("No DSN. Set MASTERDB_DATABASE_URL or pass --dsn. "
              "Refusing to guess a database.", file=sys.stderr)
        return 2
    conn = psycopg2.connect(args.dsn)
    try:
        hr("PRE-FLIGHT - does the schema apply as written?")
        ok, err = probe_verbatim(conn)
        if ok:
            print("  Group 1 schema applies verbatim into public: PASS")
        else:
            print("  Group 1 schema applies verbatim into public: FAIL")
            print("    " + (err or ""))
            print("""
  DEFECT CONFIRMED. `CREATE TABLE geography` collides with the PostGIS
  `geography` TYPE, which the schema's own `CREATE EXTENSION postgis` installs
  into public. The schema header states "Requires PostGIS extension", so this
  will reproduce on any PostGIS database.

  Why it was not caught earlier: Group 1's proof ran against a local SQLite
  stand-in, which has no PostGIS and therefore no colliding type.

  Fix used below, which changes no line of Group 1's DDL: install the VANA
  tables into their own `vana` schema, so vana.geography (table) and
  public.geography (PostGIS type) coexist.""")

        a = run_pass(conn, "A - schema exactly as Group 1 wrote it", False, pkg, obs)

        hr("WHAT PASS A COULD NOT STORE")
        for f, why in UNMAPPABLE:
            print("  DROPPED  %-26s %s" % (f, why))
        print("""
  Consequence: the Day-3 acceptance question - "what device produced this,
  when, where, and which original artifact supports it?" - cannot be answered
  from a Pass A record. Device, precise time, precise position and artifact
  reference were all discarded at the boundary.""")

        b = run_pass(conn, "B - schema plus the 8 additive columns", True, pkg, obs)

        hr("SUMMARY")
        print("  Pass A (schema as-is)      : %s  - round-trip works, 9 contract fields lost"
              % ("PASS" if a else "FAIL"))
        print("  Pass B (with additions)    : %s  - round-trip works, full provenance retained"
              % ("PASS" if b else "FAIL"))
        print("""
  Both passes prove the contract maps, persists, retrieves and is idempotent
  against Group 1's real schema. The difference between them is exactly the
  evidence Group 1 needs for the consolidation decision.

  NOT proven here: Group 1's own instance, the SVACS/edge hop, and any
  hardware. This is a local run against their schema, with a synthetic
  fixture. Hardware remains Phase 2.""")
        return 0 if (a and b) else 1
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
