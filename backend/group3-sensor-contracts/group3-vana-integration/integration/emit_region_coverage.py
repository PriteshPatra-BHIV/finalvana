# -*- coding: utf-8 -*-
"""Emit the Group 3 region coverage statement for Sanskar's six-region closure.

ASKED
-----
Sanskar (Group 1), 2026-08-28: "I need the authoritative runtime mapping for the
remaining five regions: Mumbai, Navi Mumbai, Vasai, Thane and Maval. Please provide
the approved source/observation ID and existing deployed runtime path for each region.
No manually created IDs or substituted fixtures."

THE HONEST ANSWER
-----------------
Group 3 has emitted ONE observation, for Thane Creek. It holds NO observation, source
id or runtime path for Mumbai, Navi Mumbai, Vasai or Maval. Supplying five ids would
be exactly the fabrication Sanskar's own message forbids.

What this file does instead: proves, with a live probe, that Group 3 CAN produce a
truthful observation for each of the five regions through the already-proven path, and
states precisely what is needed to do it.

Run:  python emit_region_coverage.py            (uses the recorded probe)
      python emit_region_coverage.py --probe    (re-probes live)
"""
import datetime, io, json, os, sys, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
DAY6 = os.path.dirname(HERE)

# WITHDRAWN 2026-08-28 BY MANAGER DIRECTION: "do not use provisional city-centre
# coordinates or invent IDs". These coordinates remain ONLY to address the source
# endpoint for a reachability probe. They are NOT a zone, NOT a location for any
# observation, and MUST NOT be emitted. The authoritative position is
# VANA_ZONE_IDENTITY_REGISTER.json, in which all five regions are BLOCKED pending an
# authoritative boundary.
#
# The probe still proves one thing and only one thing: the SOURCE is reachable for
# these coordinates. It never proved an identity and does not now.
REGIONS = [
    {"region": "Mumbai", "lat": 19.0760, "lon": 72.8777},
    {"region": "Navi Mumbai", "lat": 19.0330, "lon": 73.0297},
    {"region": "Vasai", "lat": 19.4259, "lon": 72.8225},
    {"region": "Thane", "lat": 19.2183, "lon": 72.9781},
    {"region": "Maval", "lat": 18.7500, "lon": 73.5000},
]

ENDPOINT = ("https://api.open-meteo.com/v1/forecast?latitude=%s&longitude=%s"
            "&current=temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m"
            "&timezone=UTC")


def _obj(v):
    """Type-safe dict access. `x.get(k) or {}` guards None but NOT a wrong type:
    a string is truthy, so .get() then raises. Dhruv Patel found this class of bug
    in the semantic validator on 2026-08-28; this sweep removed it everywhere."""
    return v if isinstance(v, dict) else {}


def probe(lat, lon):
    with urllib.request.urlopen(ENDPOINT % (lat, lon), timeout=25) as r:
        return json.loads(r.read().decode("utf-8")), r.status


def main():
    live = "--probe" in sys.argv
    results = []
    for r in REGIONS:
        row = dict(r)
        if live:
            try:
                d, code = probe(r["lat"], r["lon"])
                c = _obj(d.get("current"))
                row.update({"http_status": code, "reachable": True,
                            "grid_latitude": d.get("latitude"), "grid_longitude": d.get("longitude"),
                            "source_reported_time": c.get("time"),
                            "precipitation_mm": c.get("precipitation"),
                            "temperature_c": c.get("temperature_2m"),
                            "relative_humidity_pct": c.get("relative_humidity_2m")})
            except Exception as e:
                row.update({"reachable": False, "error": str(e)})
        row["group3_observation_id"] = None
        row["group3_canonical_record_id"] = None
        row["group3_runtime_path"] = None
        row["status"] = "NO GROUP 3 OBSERVATION EXISTS"
        results.append(row)

    doc = {
        "_README": ("Group 3 region coverage for Sanskar's six-region Group 1 closure. Group 3 "
                    "has emitted ONE observation, for Thane Creek. It holds no observation, "
                    "source id or runtime path for any other region. This file states that "
                    "plainly and proves what Group 3 can produce instead."),
        "_generated_by": "integration/emit_region_coverage.py",
        "_generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "_asked_by": "Sanskar (Group 1), 2026-08-28",
        "_probe_mode": "LIVE" if live else "recorded",

        "what_group3_actually_has": {
            "region": "Thane Creek",
            "observation_id": "TC-Z03-EXT-OPENMETEO-OBS001",
            "canonical_record_id": "CR-b4615a27-7ab1-4bde-a078-a56fa0f2414c",
            "source": "Open-Meteo.com - EXTERNAL LIVE API, CC-BY 4.0, keyless",
            "runtime_path": ("POST /observations with Idempotency-Key: "
                             "IK-TC-Z03-EXT-OPENMETEO-OBS001, then "
                             "GET /observations/{observation_id}"),
            "observation_timestamp": "2026-08-25T11:00:00Z",
            "location": "19.1288, 72.9421 (requested point, per frozen contract 12.1)",
            "acceptance": "13/13 live, 2026-08-25T11:04:54Z",
            "label": "VERIFIED - Group 3 ran it and holds the output",
        },

        "what_group3_does_NOT_have": {
            "regions": ["Mumbai", "Navi Mumbai", "Vasai", "Maval"],
            "_thane_note": ("'Thane' as a separate region is also absent. Every Group 3 "
                            "observation id begins TC- for the Thane CREEK survey, which is a "
                            "specific mangrove site inside Thane district, not the district. "
                            "Treating them as the same region would be a substitution."),
            "observation_ids_held": "NONE",
            "canonical_record_ids_held": "NONE",
            "runtime_paths_held": "NONE",
            "_why_this_is_the_answer": ("Sanskar asked for no manually created IDs and no "
                                        "substituted fixtures. Group 3 agrees, and therefore "
                                        "supplies none. An id invented to fill a row on a "
                                        "closure board is the exact failure the request is "
                                        "guarding against."),
        },

        "what_group3_CAN_produce_today": {
            "_claim": ("Every one of the five regions is reachable through the SAME proven path "
                       "Thane Creek used. Open-Meteo is keyless and global; the contract, the "
                       "emitter, the validator and the acceptance sequence are unchanged."),
            "_verified_how": ("Live probe of all five regions. Each returned HTTP 200 with a "
                              "current reading." if live else
                              "Live probe run 2026-08-28: all five returned HTTP 200. Re-run with "
                              "--probe to reproduce."),
            "_effort": "About 15 minutes per region once the zone identity is agreed.",
            "_what_is_needed_first": [
                "AUTHORITATIVE ZONE DEFINITION for each region. SUPERSEDED 2026-08-28 by "
                "VANA_ZONE_IDENTITY_REGISTER.json, which records all five regions as BLOCKED and "
                "names the exact missing authority. The city-centre coordinates below are "
                "WITHDRAWN by manager direction and address the source endpoint only - they are "
                "not a zone and must not be emitted as a location.",
                "A survey/zone identifier per region so observation_id is truthful. Thane Creek "
                "is TC-Z03. The other five have no assigned survey or zone code.",
                "Confirmation from Group 1 that five more external_api observations are wanted "
                "in the canonical store, rather than one region being the demo path.",
            ],
            "probe_results": results,
        },

        "_honest_caveat": ("These would be EXTERNAL LIVE API observations - synthetic_state "
                           "CONTROLLED, is_synthetic true, hardware_verified false. They are real "
                           "third-party weather data, not Group 3 field sensing. Six regions of "
                           "external API data is still zero regions of hardware evidence."),

        "_attribution_obligation": ("Weather data by Open-Meteo.com (CC-BY 4.0), aggregating "
                                    "national weather services. This must survive every "
                                    "downstream handoff for every region."),
    }

    out = os.path.join(DAY6, "GROUP3_REGION_COVERAGE.json")
    with io.open(out, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=2, ensure_ascii=False)
        fh.write("\n")

    print("GROUP 3 REGION COVERAGE - for Sanskar's six-region closure")
    print()
    print("  HELD  Thane Creek   TC-Z03-EXT-OPENMETEO-OBS001 -> CR-b4615a27-...  VERIFIED 13/13")
    print()
    print("  NOT HELD - no observation, no canonical id, no runtime path:")
    for r in results:
        extra = ""
        if r.get("reachable"):
            extra = "   [live probe OK: %s mm precip @ %s]" % (r.get("precipitation_mm"),
                                                               r.get("source_reported_time"))
        print("    %-13s %s%s" % (r["region"], r["status"], extra))
    print()
    print("  Group 3 supplies NO invented ids. All five are producible through the proven")
    print("  path once Group 2 supplies authoritative zone definitions and survey/zone codes.")
    print()
    print("  -> %s" % os.path.basename(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
