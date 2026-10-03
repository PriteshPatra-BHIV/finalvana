# -*- coding: utf-8 -*-
"""Emit the Group 3 Sensor Intake Adapter Contract.

ASSIGNED
--------
GROUP 3- VANA-28-08-2026.md, Hemanth as Primary System Integration Owner:
  - "Establish the canonical sensor/data intake interface."
  - "Define a reusable adapter/endpoint contract for additional sensor classes."
  - "Leave a reserved adapter/endpoint capability for future LiDAR hardware without
     claiming that hardware is deployed or connected."

WHAT AN ADAPTER IS, AND IS NOT
------------------------------
An adapter converts ONE source's native output into a V2.2 observation. It is a
Group 3 implementation detail. It is NOT a contract change, NOT a new canonical
field, and NOT a new identity rule - those belong to the contract owner and MDU.

Every adapter below therefore emits the SAME frozen V2.2 shape. They differ only in
how they read their source and how they fill a handful of fields.

THE HONESTY RULE THIS FILE ENFORCES
-----------------------------------
An adapter declares its own status. Only OPENMETEO is IMPLEMENTED and PROVEN. The
rest are DECLARED or RESERVED. A RESERVED adapter has no code and must never be
presented as a connected capability - the LiDAR slot in particular exists so the
architecture has somewhere to put hardware, not to imply hardware exists.

Run:  python emit_intake_adapter_contract.py
"""
import io, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
DAY6 = os.path.dirname(HERE)

SCHEMA = json.load(io.open(os.path.join(DAY6, "contract", "observation.schema.v2.2.json"),
                           encoding="utf-8"))
PROPS = SCHEMA["properties"]


def f(name):
    if name not in PROPS:
        raise SystemExit("REFUSING TO EMIT: '%s' is not in the frozen V2.2 contract." % name)
    return name


# Every adapter fills exactly these. The list is derived from the frozen contract's
# required set, so an adapter cannot forget a required field without this failing.
REQUIRED = list(SCHEMA["required"])

ADAPTERS = [
    {
        "adapter_id": "OPENMETEO",
        "sensor_class": "External live weather API",
        "status": "IMPLEMENTED AND PROVEN LIVE",
        "evidence": ("TC-Z03-EXT-OPENMETEO-OBS001 accepted by Group 1 on 2026-08-25, 13/13 "
                     "checks. Canonical record CR-b4615a27-7ab1-4bde-a078-a56fa0f2414c. "
                     "Re-verified by live GET 2026-08-28."),
        "implementation": "integration/build_live_observation_candidate.py",
        "source_read": "HTTPS GET to api.open-meteo.com/v1/forecast, JSON response body",
        "capture_method": "external_api",
        "flight_id": "EXT",
        "device_id_convention": "G3-EXT-<PROVIDER>-<NN>  e.g. G3-EXT-OPENMETEO-01",
        "synthetic_state": "CONTROLLED - real third-party data, not Group 3 hardware",
        "raw_artifact": "The HTTP JSON response body; bytes persisted at capture",
        "timestamp_source": "The source reports its own observation time",
        "location_source": "Requested point (canonical per contract 12.1); grid cell kept as source metadata",
        "gnss_status": "NOT_APPLICABLE in practice - no positioning system. Emitted NOT_VERIFIED",
        "hardware_verified": False,
    },
    {
        "adapter_id": "ANALOG_PROBE",
        "sensor_class": "Analog water-quality probe (pH, turbidity, TDS, UV)",
        "status": "DECLARED - contract defined, no implementation, no hardware present",
        "evidence": "NONE. No Group 3 analog sensor has produced a reading.",
        "implementation": None,
        "source_read": "ADC counts from the edge board",
        "capture_method": "sensor",
        "flight_id": "BLOCKED on W6-3 - a fixed ground unit has no defined third segment",
        "device_id_convention": ("A real Group 3 device identifier. MUST NOT use the G3-EXT- "
                                 "prefix, which is contractually bound to external_api"),
        "synthetic_state": "CONTROLLED until every D5 readiness condition is met, then PHYSICAL",
        "raw_artifact": "The raw ADC counts / voltage, persisted BEFORE conversion",
        "timestamp_source": "EDGE clock - the sensor has none. See W6-2",
        "location_source": "GNSS receiver, or a surveyed coordinate",
        "gnss_status": "REAL VALUE - FIX / NO_FIX / DEGRADED from the receiver",
        "hardware_verified": "true only with real hardware evidence - blocked on G-33",
    },
    {
        "adapter_id": "DIGITAL_BUS",
        "sensor_class": "Digital-bus sensor (RS485 DO, 1-Wire DS18B20, I2C BME280)",
        "status": "DECLARED - contract defined, no implementation, no hardware present",
        "evidence": "NONE.",
        "implementation": None,
        "source_read": "RS485 frame / 1-Wire value / I2C register read",
        "capture_method": "sensor",
        "flight_id": "BLOCKED on W6-3",
        "device_id_convention": "A real Group 3 device identifier",
        "synthetic_state": "CONTROLLED until D5 met",
        "raw_artifact": "The raw bus frame, persisted before decoding",
        "timestamp_source": "EDGE clock",
        "location_source": "GNSS or surveyed",
        "gnss_status": "REAL VALUE",
        "hardware_verified": "blocked on G-33",
        "_note": ("A BME280 yields THREE measurements from one read. V2.2 carries one measurement "
                  "per observation - see gap S-2. Group 3 recommends three observations sharing a "
                  "timestamp and location."),
    },
    {
        "adapter_id": "IMAGE_CAPTURE",
        "sensor_class": "Camera / stereo depth (Luxonis OAK-D Pro)",
        "status": ("DECLARED - PRESENCE CONTRADICTED as of 2026-08-29. See _presence_contradiction below. Previously recorded as PRESENT-not-VERIFIED on Suraj's register alone."),
        "evidence": ("Oak-D Pro appears in Suraj's equipment register classified PRESENT, not "
                     "VERIFIED. No frame has been captured into an observation."),

        "_presence_contradiction": {
            "_raised": "2026-08-29 (gap G-50). UNRESOLVED.",
            "suraj_equipment_register": "PRESENT, not VERIFIED",
            "manya_d7_present_column": "NOT PHYSICALLY EVIDENCED HERE",
            "reference_bom_boq": ("LISTS 'Luxonis OAK-D PRO Camera with Autofocus' - proves it "
                                  "was SPECIFIED and priced, NOT that it is in the room"),
            "_nobody_has_produced_physical_evidence_either_way": True,
            "_resolution_needed": ("One line from Suraj Surve: is the Oak-D Pro physically in "
                                   "the room today, yes or no. Until then this adapter must not "
                                   "be presented as having available hardware."),
        },
        "_capture_defect_G42": {
            "_severity": "CRITICAL - blocks a truthful first capture even if the camera IS present",
            "_defect": ("persist_raw_bytes copies the frame onto itself at the default storage "
                        "directory. open(dest,'wb') truncates before src.read() runs."),
            "_reproduced": "2304 bytes -> 0 bytes",
            "_why_it_is_dangerous": ("The sha256 of the empty file (e3b0c442...8855) is a valid "
                                     "64-char hex string, so schema AND semantic validation both "
                                     "PASS and the runner prints 'VALID - ready to hand off'."),
            "_fix": "Three lines, supplied to Dhruv Patel and regression-tested three ways.",
            "_must_land_before": "any camera is pointed at anything",
        },        "implementation": None,
        "source_read": "Image or depth frame over USB/CSI",
        "capture_method": "sensor",
        "flight_id": "F### if genuinely flown; otherwise BLOCKED on W6-3",
        "device_id_convention": "A real Group 3 device identifier",
        "synthetic_state": "CONTROLLED until D5 met",
        "raw_artifact": "The frame itself, persisted; measurement carries the descriptive or derived form",
        "timestamp_source": "EDGE clock",
        "location_source": "GNSS",
        "gnss_status": "REAL VALUE",
        "hardware_verified": "blocked on G-33",
    },
    {
        "adapter_id": "LIDAR",
        "sensor_class": "LiDAR point cloud",
        "status": "RESERVED - NO HARDWARE, NO IMPLEMENTATION, NOT CONNECTED",
        "evidence": ("NONE, and none is claimed. This slot exists so the architecture has a "
                     "defined place for LiDAR. It is NOT a capability."),
        "implementation": None,
        "source_read": "(reserved)",
        "capture_method": "sensor",
        "flight_id": "F### for an aerial survey",
        "device_id_convention": "A real Group 3 device identifier",
        "synthetic_state": "would be PHYSICAL only with real hardware evidence",
        "raw_artifact": "point cloud file, persisted",
        "timestamp_source": "EDGE clock",
        "location_source": "GNSS",
        "gnss_status": "REAL VALUE",
        "hardware_verified": "blocked on G-33",
        "_explicit_warning": ("TC-Z03-F02-LIDAR-OBS001 EXISTS in Group 1's canonical store and is "
                              "NOT evidence of LiDAR hardware. It is a legacy synthetic test "
                              "observation, and it still carries the G-1 defect - stored "
                              "is_synthetic false / synthetic_state UNKNOWN for a synthetic "
                              "record. It must not be cited as a LiDAR capability."),
    },
]

FIELD_RESPONSIBILITY = {
    "_what_this_answers": "For a NEW sensor class, which fields does the adapter author have to think about?",
    "identical_for_every_adapter": {
        "fields": [f("contract_version"), f("schema_version"), f("source_identity"),
                   f("ingestion_timestamp"), f("trace_id"), f("idempotency_key"),
                   f("processing_status"), f("data_state")],
        "rule": ("Fixed by the contract or by Group 3 convention. contract_version is const 2.2; "
                 "ingestion_timestamp and trace_id are runtime-owned and emitted null; "
                 "idempotency_key is IK-<observation_id>."),
    },
    "adapter_must_supply": {
        "fields": [f("observation_type"), f("measurement"), f("unit"), f("capture_method"),
                   f("raw_artifact"), f("raw_artifact_integrity"), f("sensor_id")],
        "rule": "These are what actually differ between one sensor class and another.",
    },
    "edge_runtime_supplies": {
        "fields": [f("observation_id"), f("survey_id"), f("zone_id"), f("flight_id"),
                   f("observation_seq"), f("observation_timestamp"), f("source_timestamp"),
                   f("device_id"), f("mission_id"), f("location"), f("provenance"),
                   f("provenance_reference"), f("calibration_state"), f("quality_state"),
                   f("synthetic_state"), f("is_synthetic"), f("hardware_verified"),
                   f("accuracy")],
        "rule": ("Common edge services, not per-adapter. Writing these per-adapter is how two "
                 "sensors end up with inconsistent provenance."),
    },
}

TRANSPORT = {
    "ingest": "POST /observations",
    "retrieve": "GET /observations/{observation_id}",
    "health": "GET /health",
    "host": ("Supplied at run time via --base-url or VANA_API_BASE_URL. NEVER committed - Group "
             "1's API carries no authentication."),
    "idempotency_header": "Idempotency-Key: IK-<observation_id>",
    "expected_sequence": ("201 ACCEPTED -> 200 IDEMPOTENT_REPLAY (same key, same body) -> "
                          "409 IDEMPOTENCY_CONFLICT (same key, mutated body)"),
    "proven": "13/13 live against Group 1's deployed instance, 2026-08-25T11:04:54Z",
    "retry_rule": ("The edge MUST persist the idempotency key alongside a buffered reading. A key "
                   "regenerated after reboot creates a duplicate canonical record instead of a "
                   "safe replay."),
}


def main():
    impl = [a for a in ADAPTERS if a["status"].startswith("IMPLEMENTED")]
    doc = {
        "_README": ("Group 3 Sensor Intake Adapter Contract. One reusable shape for every sensor "
                    "class feeding VANA. An adapter converts a source's native output into a "
                    "frozen V2.2 observation; it never adds a canonical field or identity rule."),
        "_generated_by": "integration/emit_intake_adapter_contract.py",
        "_owner": "Hemanth Reddy - Primary System Integration Owner, Group 3",
        "_contract": "observation.schema.v2.2.json (FROZEN, Arya Barge)",
        "_authority_boundary": ("Adapters are Group 3 implementation. Canonical schema, provenance "
                                "and identity rules remain with the contract owner and MDU. This "
                                "file adds no field and proposes no contract change."),
        "_status_summary": {
            "IMPLEMENTED_AND_PROVEN": [a["adapter_id"] for a in ADAPTERS
                                       if a["status"].startswith("IMPLEMENTED")],
            "DECLARED_no_implementation": [a["adapter_id"] for a in ADAPTERS
                                           if a["status"].startswith("DECLARED")],
            "RESERVED_no_hardware": [a["adapter_id"] for a in ADAPTERS
                                     if a["status"].startswith("RESERVED")],
            "_honesty": ("%d of %d adapters is implemented and proven. The rest are contract "
                         "definitions with no code and, in most cases, no hardware. A DECLARED or "
                         "RESERVED adapter must never be shown as a connected capability."
                         % (len(impl), len(ADAPTERS))),
        },
        "required_fields_every_adapter_must_fill": REQUIRED,
        "field_responsibility_split": FIELD_RESPONSIBILITY,
        "transport_contract": TRANSPORT,
        "adapters": ADAPTERS,
        "how_to_add_a_new_sensor_class": [
            "1. Confirm the measurement, unit and observation_type - Suraj's sensor capability matrix.",
            "2. Choose the adapter family: ANALOG_PROBE, DIGITAL_BUS or IMAGE_CAPTURE.",
            "3. Implement ONLY the source read and the seven adapter-supplied fields.",
            "4. Persist raw bytes, then hash them. Never hash without persisting.",
            "5. Validate against the frozen schema before transmission.",
            "6. POST with IK-<observation_id>; confirm 201, then replay for 200.",
            "7. Do NOT add a canonical field. If something is not representable, raise it as a gap.",
        ],
        "_open_blockers_for_any_hardware_adapter": {
            "W6-3": "Fixed ground sensor has no defined observation_id third segment.",
            "W6-2": "Clock-trust instruction names data_state UNCERTAIN, which is now invalid.",
            "G-33": "hardware_verified is not returned by Group 1 - the PHYSICAL gate cannot be verified.",
            "_effect": ("All three block PHYSICAL classification, not intake. A hardware adapter "
                        "can emit truthfully as CONTROLLED today."),
        },
    }

    out = os.path.join(DAY6, "GROUP3_INTAKE_ADAPTER_CONTRACT.json")
    with io.open(out, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=2, ensure_ascii=False)
        fh.write("\n")

    print("GROUP 3 SENSOR INTAKE ADAPTER CONTRACT")
    print()
    for a in ADAPTERS:
        mark = ("PROVEN  " if a["status"].startswith("IMPLEMENTED")
                else "declared" if a["status"].startswith("DECLARED") else "RESERVED")
        print("  [%s] %-14s %s" % (mark, a["adapter_id"], a["sensor_class"]))
    print()
    print("  required fields every adapter fills : %d" % len(REQUIRED))
    print("  identical for every adapter         : %d"
          % len(FIELD_RESPONSIBILITY["identical_for_every_adapter"]["fields"]))
    print("  adapter-specific                    : %d"
          % len(FIELD_RESPONSIBILITY["adapter_must_supply"]["fields"]))
    print("  edge-runtime supplied               : %d"
          % len(FIELD_RESPONSIBILITY["edge_runtime_supplies"]["fields"]))
    print()
    print("  %d of %d adapters implemented and proven. LiDAR is RESERVED - no hardware, none claimed."
          % (len(impl), len(ADAPTERS)))
    print()
    print("  -> %s" % os.path.basename(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
