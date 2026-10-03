# -*- coding: utf-8 -*-
"""Probe the AIAIC sources that are BOTH verified_live AND keyless, at Thane Creek.

WHY THIS EXISTS
---------------
The manager's priority list for today's non-LiDAR source includes "live/current
satellite or remote-sensing data already integrated by Hemanth for AIAIC". This
script answers that question with a live call rather than a claim.

WHAT AIAIC ACTUALLY HAS
-----------------------
AIAIC's evidence registry declares 14 real sources, each with an honest wiring
status. Read carefully, only TWO are genuine keyless network calls:

    open_meteo_weather   verified_live   Open-Meteo REST API  (no key)
    nasa_power_weather   verified_live   NASA POWER REST API  (no key)

Two more are verified_live but need a data.gov.in API key (agmarknet, msp_cacp).
The remaining ten are local CSVs or PDF extractions. In AIAIC's vocabulary
"verified_live" means the source is REAL AND WIRED - it does NOT mean a live API
call. That distinction matters today, because the EOD rule requires a dynamic
runtime source, not a local file.

AIAIC DOES HOLD SATELLITE DATA - BUT NONE OF IT IS LIVE.
9 ISRO AWiFS water-body-fraction rasters (Bhuvan/NRSC), one January per year
2017-2025, plus 8 OCM2 surface-water rasters from Jan 2016. They are processed
offline by surface-water-prep/extract/extract_rasters.py into curated CSVs,
clipped to a Maharashtra bounding box, and labelled by AIAIC itself as "REGIONAL
CONTEXT, UNCALIBRATED". Annual snapshots from local files - they cannot produce a
dynamic runtime observation.

CORRECTION, recorded rather than quietly fixed: an earlier version of this
docstring asserted "there is no satellite imagery source in AIAIC". That was
wrong. The search behind it had matched only the word "sentinel" used to mean a
sentinel VALUE in water-quality data, and missed the ISRO rasters entirely.

NASA POWER is separately satellite- and model-DERIVED observational
agroclimatology with 2-3 day latency - AIAIC's own adapter says "OBSERVATIONAL
(not a forecast)". It is not imagery and must not be described as such.

Run:  python probe_aiaic_live_sources.py
      python probe_aiaic_live_sources.py --lat 19.1288 --lon 72.9421
"""
import argparse, datetime, io, json, os, sys, urllib.error, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
DAY6 = os.path.dirname(HERE)

# Thane Creek - the VANA area of interest, and inside Group 2's declared zone polygon
DEFAULT_LAT, DEFAULT_LON = 19.1288, 72.9421

ATTRIBUTION = {
    "open_meteo": "Weather data by Open-Meteo.com (CC-BY 4.0), aggregating national weather services. "
                  "Non-commercial free tier.",
    "nasa_power": "These data were obtained from the NASA Langley Research Center POWER Project "
                  "(power.larc.nasa.gov). Free and open; cite the NASA POWER Project.",
}


def get(url, timeout=25):
    t0 = datetime.datetime.now(datetime.timezone.utc)
    with urllib.request.urlopen(url, timeout=timeout) as r:
        body = r.read().decode("utf-8")
        code = r.status
    ms = (datetime.datetime.now(datetime.timezone.utc) - t0).total_seconds() * 1000.0
    return code, json.loads(body), ms, len(body)


def probe_open_meteo(lat, lon):
    url = ("https://api.open-meteo.com/v1/forecast?latitude=%s&longitude=%s"
           "&current=temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m"
           "&timezone=UTC" % (lat, lon))
    code, d, ms, n = get(url)
    cur = d.get("current") or {}
    return {"source_id": "open_meteo_weather", "status": "LIVE", "http": code,
            "latency_ms": round(ms), "bytes": n, "url": url,
            "observed_at_utc": cur.get("time"),
            "values": {k: v for k, v in cur.items() if k not in ("time", "interval")},
            "units": d.get("current_units"),
            "elevation_m": d.get("elevation"),
            "kind": "live weather API - forecast model output, updated continuously",
            "attribution": ATTRIBUTION["open_meteo"]}


def probe_nasa_power(lat, lon):
    today = datetime.date.today()
    start = today - datetime.timedelta(days=10)
    end = today - datetime.timedelta(days=3)          # POWER runs 2-3 days behind
    url = ("https://power.larc.nasa.gov/api/temporal/daily/point?parameters=T2M,PRECTOTCORR,RH2M"
           "&community=AG&longitude=%s&latitude=%s&start=%s&end=%s&format=JSON"
           % (lon, lat, start.strftime("%Y%m%d"), end.strftime("%Y%m%d")))
    code, d, ms, n = get(url)
    params = (d.get("properties") or {}).get("parameter") or {}
    latest = {}
    for k, series in params.items():
        real = {day: v for day, v in series.items() if v not in (-999, -999.0)}
        if real:
            day = sorted(real)[-1]
            latest[k] = {"date": day, "value": real[day], "days_returned": len(real)}
    return {"source_id": "nasa_power_weather", "status": "LIVE", "http": code,
            "latency_ms": round(ms), "bytes": n, "url": url,
            "latest": latest,
            "kind": "satellite- and model-DERIVED observational agroclimatology, 2-3 day latency. "
                    "NOT satellite imagery and NOT a forecast.",
            "attribution": ATTRIBUTION["nasa_power"]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lat", type=float, default=DEFAULT_LAT)
    ap.add_argument("--lon", type=float, default=DEFAULT_LON)
    a = ap.parse_args()

    print("AIAIC LIVE SOURCE PROBE - keyless, verified_live sources only")
    print("location : %s, %s  (Thane Creek - VANA area of interest)" % (a.lat, a.lon))
    print("run at   : %s" % datetime.datetime.now(datetime.timezone.utc).isoformat())
    print()

    results, failures = [], 0
    for name, fn in (("Open-Meteo", probe_open_meteo), ("NASA POWER", probe_nasa_power)):
        try:
            r = fn(a.lat, a.lon)
            results.append(r)
            print("  [LIVE] %-12s HTTP %s  %s ms  %s bytes"
                  % (name, r["http"], r["latency_ms"], r["bytes"]))
        except Exception as e:
            failures += 1
            results.append({"source_id": name, "status": "UNAVAILABLE", "error": str(e)[:200]})
            print("  [FAIL] %-12s %s" % (name, str(e)[:70]))

    print()
    for r in results:
        if r.get("status") != "LIVE":
            continue
        if r["source_id"] == "open_meteo_weather":
            print("  Open-Meteo observed %s UTC  ->  %s" % (r["observed_at_utc"], r["values"]))
            print("             elevation %s m (coastal/creek - consistent with Thane Creek)"
                  % r["elevation_m"])
        else:
            for k, v in r["latest"].items():
                print("  NASA POWER %-12s %s = %s   (%d days returned)"
                      % (k, v["date"], v["value"], v["days_returned"]))

    out = os.path.join(DAY6, "evidence", "live", "aiaic_source_probe.json")
    doc = {"_README": ("Live probe of the only two AIAIC sources that are BOTH verified_live AND "
                       "keyless network calls. Captured to answer whether they are genuinely "
                       "accessible at runtime, rather than asserting it."),
           "_probed_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
           "_location": {"latitude": a.lat, "longitude": a.lon, "name": "Thane Creek"},
           "_classification": "LIVE - real external third-party APIs, no key, no Group 3 hardware",
           "_honesty": ("Neither source is Group 3 hardware evidence. Neither is satellite imagery. "
                        "AIAIC does hold ISRO AWiFS/OCM2 rasters, but they are annual offline snapshots, not a "
                        "live feed. Any observation "
                        "built from these must carry the external source identity and attribution, and "
                        "must NOT be classified PHYSICAL."),
           "sources": results}
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with io.open(out, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=2, ensure_ascii=False)
        fh.write("\n")

    print()
    print("evidence -> evidence/live/aiaic_source_probe.json")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    sys.exit(main())
