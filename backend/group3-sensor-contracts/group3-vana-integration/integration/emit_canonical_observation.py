# -*- coding: utf-8 -*-
"""Emit ONE canonical observation, read back out of Group 1's actual schema.

Why this exists
---------------
Group 2 (Vijay) and Group 4 (Karan) both asked for "one canonical observation"
with an ID they can carry through their own runtime. Group 3 does not own the
canonical store, so we cannot hand over a record from Group 1's instance.

What we CAN do honestly is this: apply Group 1's own VANA-schema.sql, ingest the
Group 3 fixture through it, and SELECT the row back out. What comes out is
canonical-SHAPED and canonical-SOURCED — every value below was read from the
database, not typed into a file.

    fixture -> Group 1 schema -> INSERT -> SELECT -> this file

Honesty labels carried in the output:
  is_synthetic         TRUE   - the source row says so, per Raj's request
  canonical_store      LOCAL  - Group 1's SCHEMA, not Group 1's INSTANCE
  hardware_verified    false  - no Group 3 sensor has produced a reading

Usage:
    python emit_canonical_observation.py
    python emit_canonical_observation.py --dsn postgresql://user:pw@host:5432/db
"""
import argparse, json, io, os, sys, datetime
import psycopg2
import psycopg2.extras

import ingest_roundtrip as rt   # reuse the proven reset/ingest path

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "canonical_observation.json")

TARGET = "TC-Z03-F02-LIDAR-OBS001"   # the numeric observation - it has a measurement row


def fetch(cur, observation_id):
    """Pull the observation back out, joined across the canonical tables."""
    cur.execute("""
        SELECT
            o.observation_id,
            o.observation_date,
            o.observation_type,
            o.observed_at,
            o.device_id,
            ST_Y(o.geom)        AS latitude,
            ST_X(o.geom)        AS longitude,
            o.quality_status,
            o.raw_artifact_ref,
            o.raw_artifact_sha256,
            g.geo_id,
            g.place_name,
            g.crs,
            d.dataset_id,
            d.dataset_name,
            d.methodology,
            d.schema_version,
            s.source_id,
            s.source_type,
            s.is_synthetic,
            m.measurement_id,
            m.metric_name,
            m.value,
            m.unit,
            m.method,
            m.accuracy,
            m.calibration_status,
            p.provenance_id,
            p.derivation_note
        FROM observation o
        JOIN dataset  d ON d.dataset_id = o.dataset_id
        JOIN source   s ON s.source_id  = d.source_id
        LEFT JOIN geography  g ON g.geo_id = o.geo_id
        LEFT JOIN measurement m ON m.observation_id = o.observation_id
        LEFT JOIN provenance  p ON p.measurement_id = m.measurement_id
        WHERE o.observation_id = %s
    """, (observation_id,))
    return cur.fetchone()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dsn", default=os.environ.get("MASTERDB_DATABASE_URL", rt.DEFAULT_DSN))
    args = ap.parse_args()

    pkg, obs = rt.load_fixture()
    src = [o for o in obs if o["observation_id"] == TARGET][0]

    conn = psycopg2.connect(args.dsn)
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            rt.reset(cur)
            cur.execute("SET search_path = vana, public;")
            cur.execute(rt.ADDITIVE_COLUMNS)
            conn.commit()

            n = rt.ingest(cur, pkg, obs, True)
            conn.commit()

            row = fetch(cur, TARGET)
            if row is None:
                print("FAIL: %s not found after ingest" % TARGET)
                return 1

            # re-submit, then re-read: the ID and the values must be unchanged
            rt.ingest(cur, pkg, obs, True)
            conn.commit()
            row2 = fetch(cur, TARGET)
            cur.execute("SELECT count(*) FROM observation")
            obs_count = cur.fetchone()[0]

        stable = (row["observation_id"] == row2["observation_id"]
                  and row["observed_at"] == row2["observed_at"]
                  and row["value"] == row2["value"])

        ts = row["observed_at"].astimezone(datetime.timezone.utc).isoformat().replace("+00:00", "Z")

        doc = {
            "_README": (
                "ONE canonical observation, SELECTed out of Group 1's VANA-schema.sql "
                "after ingesting the Group 3 field fixture through it. Every value in "
                "'canonical_observation' was read from the database. This is Group 1's "
                "SCHEMA, not Group 1's INSTANCE - see _honesty."
            ),
            "_honesty": {
                "is_synthetic": bool(row["is_synthetic"]),
                "source_type": row["source_type"],
                "hardware_verified": False,
                "canonical_store": "LOCAL - Group 1 schema v0.1 applied to PostgreSQL 16 / PostGIS",
                "not_proven": [
                    "Group 1's own database instance",
                    "the SVACS / edge transport hop",
                    "any physical sensor reading"
                ],
                "note": (
                    "No Group 3 sensor has produced a recorded reading. Values are "
                    "illustrative and exist to prove the system path, not hardware "
                    "readiness. Do not treat this as real field data."
                )
            },
            "_generated": {
                "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "by": "integration/emit_canonical_observation.py",
                "schema_applied": os.path.basename(rt.SCHEMA_SQL),
                "fixture": os.path.basename(rt.FIXTURE),
                "observations_ingested": n,
                "observation_rows_after_resubmit": obs_count,
                "idempotent_reread_stable": stable
            },

            # --- exactly the shape Group 2 asked for -------------------------
            "group2_minimal_view": {
                "observation_id": row["observation_id"],
                "location": {
                    "latitude": float(row["latitude"]),
                    "longitude": float(row["longitude"])
                },
                "timestamp": ts,
                "measurement": {
                    "value": float(row["value"]),
                    "unit": row["unit"]
                }
            },

            # --- the full canonical record -----------------------------------
            "canonical_observation": {
                "observation_id": row["observation_id"],
                "observation_type": row["observation_type"],
                "observation_date": row["observation_date"].isoformat(),
                "observed_at": ts,
                "device_id": row["device_id"],
                "location": {
                    "latitude": float(row["latitude"]),
                    "longitude": float(row["longitude"]),
                    "crs": row["crs"],
                    "geo_id": row["geo_id"],
                    "place_name": row["place_name"]
                },
                "measurement": {
                    "measurement_id": row["measurement_id"],
                    "parameter": row["metric_name"],
                    "value": float(row["value"]),
                    "unit": row["unit"],
                    "method": row["method"],
                    "accuracy": row["accuracy"],
                    "calibration_status": row["calibration_status"]
                },
                "quality_status": row["quality_status"],
                "source": {
                    "source_id": row["source_id"],
                    "source_type": row["source_type"],
                    "is_synthetic": bool(row["is_synthetic"])
                },
                "dataset": {
                    "dataset_id": row["dataset_id"],
                    "dataset_name": row["dataset_name"],
                    "methodology": row["methodology"],
                    "schema_version": row["schema_version"]
                },
                "raw_artifact": {
                    "reference": row["raw_artifact_ref"],
                    "sha256": row["raw_artifact_sha256"]
                },
                "provenance": {
                    "provenance_id": row["provenance_id"],
                    "derivation_note": row["derivation_note"]
                }
            },

            # --- what Group 4 needs to carry through governed execution -------
            "group4_handoff": {
                "observation_id": row["observation_id"],
                "idempotency_key": src["idempotency_key"],
                "trace_id": src["trace_id"],
                "trace_id_status": (
                    "NULL on this record, and correctly so. CANONICAL FORMAT is "
                    "'VANA-<12 lowercase hex>' (e.g. VANA-3a9fd87b337d), per the "
                    "Group 1 VANA MasterDB Observation API v1.0.0 handoff, which "
                    "returns trace_id in every ingestion, replay, conflict and "
                    "duplicate response. Group 3 does NOT mint traces - it emits "
                    "null and receives one back on ingestion. The trace becomes "
                    "non-null only after this observation has been submitted."
                ),
                "identity_rule": (
                    "Identity is the whole tuple: Survey + Zone + Flight + Sensor + "
                    "Observation seq, PLUS coordinates and timestamp. The OBS### "
                    "fragment is NOT unique on its own - it repeats every flight."
                ),
                "device_registration": {
                    "device_id": row["device_id"],
                    "intended_capability_type": "edge_robotics",
                    "status": "NOT REGISTERED - route POST /api/v1/registry/capabilities unconfirmed by Group 4"
                },
                "idempotency": (
                    "Re-submitting the identical package left observation count at %d. "
                    "Enforced by ON CONFLICT DO NOTHING on the natural key." % obs_count
                )
            }
        }

        io.open(OUT, "w", encoding="utf-8").write(
            json.dumps(doc, indent=2, ensure_ascii=False) + "\n")

        print("canonical observation emitted -> %s" % os.path.basename(OUT))
        print()
        print("  observation_id  : %s" % row["observation_id"])
        print("  observed_at     : %s" % ts)
        print("  location        : %.4f, %.4f  (%s)" % (row["latitude"], row["longitude"], row["crs"]))
        print("  measurement     : %s %s  (%s)" % (row["value"], row["unit"], row["metric_name"]))
        print("  device_id       : %s" % row["device_id"])
        print("  quality_status  : %s" % row["quality_status"])
        print("  source_type     : %s   is_synthetic=%s" % (row["source_type"], row["is_synthetic"]))
        print("  raw artifact    : %s" % row["raw_artifact_ref"])
        print("  provenance_id   : %s" % row["provenance_id"])
        print()
        print("  re-submitted, re-read: %s   observation rows: %d"
              % ("IDENTICAL" if stable else "CHANGED - INVESTIGATE", obs_count))
        print()
        print("  NOT PROVEN: Group 1's instance, the SVACS/edge hop, any hardware.")
        return 0 if stable else 1
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
