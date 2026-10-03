# -*- coding: utf-8 -*-
"""Emit D1-D5: Sensor -> V2.2 interface mapping, payload, metadata, gaps, readiness.

ASSIGNED
--------
Arya Barge, 2026-08-28: "Determine how the actual sensor hardware will produce data
that can be converted into a canonical VANA observation under the frozen V2.2
contract... Do not invent schema fields or change the V2.2 contract. If something is
not representable, raise it as a gap for me as the Contract Owner."

INPUT
-----
arya-27-08-2026/BOM vana.docx - Table 1 environmental sensor BOM and Table 12
recommended minimum stack. Sensor models, units and interfaces are taken FROM THAT
DOCUMENT, not chosen here.

WHAT THIS FILE WILL NOT DO
--------------------------
Invent a V2.2 field. Every target below is asserted to exist in the frozen schema at
generation time; if one does not, generation FAILS rather than emitting a mapping to
a field that is not there.

Run:  python emit_sensor_d1_d5.py
"""
import io, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
DAY6 = os.path.dirname(HERE)

SCHEMA = json.load(io.open(os.path.join(DAY6, "contract", "observation.schema.v2.2.json"),
                           encoding="utf-8"))
MATRIX = json.load(io.open(os.path.join(DAY6, "V2.2_PERSISTENCE_MATRIX.json"), encoding="utf-8"))
BYFIELD = {r["field"]: r for r in MATRIX["matrix"]}
PROPS = SCHEMA["properties"]
LOCPROPS = PROPS["location"]["properties"]


def field(name):
    """Assert a V2.2 field exists. Generation fails rather than inventing one."""
    if name not in PROPS:
        raise SystemExit("REFUSING TO EMIT: '%s' is not a field in the frozen V2.2 contract." % name)
    return name


def cls(name):
    r = BYFIELD.get(name)
    return r["classification"] if r else "NOT_CLASSIFIED"


# ---------------------------------------------------------------------------
# D1 - Sensor -> V2.2 interface mapping.
# Sensor / model / unit / interface are FROM Arya's BOM vana.docx Table 1 + Table 12.
# ---------------------------------------------------------------------------
SENSORS = [
    {"sensor": "pH sensor", "model": "DFRobot Gravity Analog pH / Industrial pH Kit",
     "output": "Analog voltage", "measurement": "water pH", "unit": "pH",
     "observation_type": "water_ph", "interface": "Analog (ADC)",
     "priority": "REQUIRED (BOM Table 12 #1)",
     "spec": "0-14 pH, +/-0.1 pH @ 25C, 0-60C",
     "edge_conversion": "ADC counts -> volts -> pH via calibration curve. The RAW ADC/voltage "
                        "reading is the artifact; the pH value is the measurement.",
     "calibration": "REQUIRED. A pH probe drifts and needs buffer-solution calibration. Until "
                    "calibration evidence exists, calibration_state MUST be UNCALIBRATED or "
                    "NOT_VERIFIED - never CALIBRATED by assumption."},

    {"sensor": "Dissolved oxygen sensor", "model": "Desun Uniwill DYS-1 / industrial DO",
     "output": "RS485 digital", "measurement": "dissolved oxygen", "unit": "mg/L",
     "observation_type": "dissolved_oxygen", "interface": "RS485",
     "priority": "REQUIRED (BOM Table 12 #2)",
     "spec": "0-20 mg/L",
     "edge_conversion": "RS485 frame -> mg/L. Store the raw frame as the artifact.",
     "calibration": "REQUIRED. DO membranes age; temperature compensation needed. Water "
                    "temperature should be captured in the same cycle."},

    {"sensor": "Turbidity sensor", "model": "DFRobot Gravity Analog Turbidity",
     "output": "Analog 0-4.5 V", "measurement": "turbidity", "unit": "NTU",
     "observation_type": "turbidity", "interface": "Analog (ADC)",
     "priority": "REQUIRED (BOM Table 12 #3)",
     "spec": "5 V, 40 mA max, response <500 ms",
     "edge_conversion": "Voltage -> NTU via the vendor curve. Curve identity belongs in provenance.",
     "calibration": "REQUIRED. Fouling in a mangrove creek is the dominant error source."},

    {"sensor": "Water temperature", "model": "DS18B20 waterproof probe",
     "output": "1-Wire digital", "measurement": "water temperature", "unit": "degC",
     "observation_type": "water_temperature", "interface": "1-Wire",
     "priority": "REQUIRED (BOM Table 12 #4)",
     "spec": "-55C to +125C, stainless waterproof probe",
     "edge_conversion": "Direct digital read - no conversion. Highest-trust reading in the stack.",
     "calibration": "Factory-calibrated. NOT_VERIFIED is the honest state until Group 3 checks it "
                    "against a reference."},

    {"sensor": "TDS / EC sensor", "model": "DFRobot Gravity Analog TDS",
     "output": "Analog", "measurement": "total dissolved solids", "unit": "ppm",
     "observation_type": "tds", "interface": "Analog (ADC)",
     "priority": "RECOMMENDED (BOM Table 12 #5)",
     "spec": "0-1000 ppm, +/-10% FS @ 25C",
     "edge_conversion": "Voltage -> ppm with temperature compensation from the DS18B20.",
     "calibration": "REQUIRED. NOTE for a MANGROVE site: 0-1000 ppm is a FRESHWATER range. "
                    "Brackish creek water is far higher. Raised as gap S-1."},

    {"sensor": "GNSS", "model": "Holybro M10 GPS",
     "output": "NMEA / UBX over UART", "measurement": "position", "unit": "degrees / m",
     "observation_type": "(not an observation - populates location)", "interface": "UART",
     "priority": "REQUIRED (BOM Table 12 #6)",
     "spec": "M10 GNSS receiver",
     "edge_conversion": "NMEA -> latitude, longitude, altitude_m, fix quality, HDOP/accuracy.",
     "calibration": "N/A. Fix quality is reported per reading, not calibrated."},

    {"sensor": "Air temperature / RH / pressure", "model": "BME280 / BME688-class",
     "output": "I2C digital", "measurement": "air temperature, humidity, pressure",
     "unit": "degC / %RH / hPa", "observation_type": "air_temperature",
     "interface": "I2C", "priority": "RECOMMENDED (BOM Table 12 #7)",
     "spec": "Digital environmental sensing module",
     "edge_conversion": "Direct digital read. THREE measurements - see gap S-2 on multi-parameter "
                        "readings.",
     "calibration": "Factory-calibrated; NOT_VERIFIED until checked."},

    {"sensor": "UV / solar", "model": "DFRobot GUVA-S12SD",
     "output": "Analog", "measurement": "UV irradiance", "unit": "mW/cm2",
     "observation_type": "uv_index", "interface": "Analog (ADC)",
     "priority": "OPTIONAL (BOM Table 12 #9)",
     "spec": "200-370 nm",
     "edge_conversion": "Voltage -> irradiance via vendor curve.",
     "calibration": "REQUIRED for absolute values; relative trend usable uncalibrated if declared."},

    {"sensor": "Water level / depth", "model": "Industrial pressure transducer / waterproof level sensor",
     "output": "Analog or RS485", "measurement": "water level / depth", "unit": "m",
     "observation_type": "water_level", "interface": "Analog (ADC) or RS485",
     "priority": "OPTIONAL / MISSION-DEPENDENT (BOM Table 12 #8)",
     "spec": "Select according to required deployment depth; INR 1,802",
     "edge_conversion": "Pressure -> depth. Requires the water density assumption and the local "
                        "atmospheric reference to be recorded in provenance - a raw pressure "
                        "reading is not a depth without both.",
     "calibration": "REQUIRED, and the reference matters: a gauge transducer needs atmospheric "
                    "compensation. In a TIDAL creek the value changes with the tide by design, so "
                    "a reading is only interpretable with its timestamp - which ties this sensor "
                    "to the W6-2 clock-trust question more tightly than the others.",
     "_bom_note": ("BOM Table 1 #9 marks the final model as requiring a DEPLOYMENT-DEPTH RULING. "
                   "Until that ruling exists the sensor cannot be specified, so it is mapped here "
                   "but not selectable.")},

    {"sensor": "UWB localisation", "model": "ESP32-DW3210-UWB tag + DW3210 anchor module",
     "output": "Range / time-of-flight", "measurement": "range to anchor", "unit": "m",
     "observation_type": "(not an environmental observation - localisation support)",
     "interface": "UWB radio / SPI to host",
     "priority": "SUPPORT (Arya BOM Table 9)",
     "spec": "DW3210 ultra-wideband ranging",
     "edge_conversion": "Time-of-flight -> range in metres, then a position solution against known "
                        "anchors. Included because Arya's Table 9 maps it; it is NOT an "
                        "environmental sensor and does not produce an observation of its own.",
     "calibration": "Anchor survey required. Without surveyed anchor positions a UWB solution has "
                    "no absolute reference.",
     "_note_on_v2_2": ("UWB supports location and provenance rather than measurement. If a UWB "
                       "solution supplies latitude/longitude instead of GNSS, gnss_status MUST NOT "
                       "claim FIX - no GNSS fix occurred. That is the same trap as a surveyed "
                       "coordinate and is worth an explicit ruling if UWB is used for position.")},

    {"sensor": "Camera / AI", "model": "Luxonis OAK-D Pro + Raspberry Pi AI HAT+",
     "output": "Image / depth frame", "measurement": "descriptive or derived",
     "unit": "(null for image)", "observation_type": "canopy_image",
     "interface": "USB / CSI", "priority": "MISSION-DEPENDENT (BOM Table 12 #10)",
     "spec": "Stereo depth + autofocus RGB",
     "edge_conversion": "Frame stored as the raw artifact; measurement carries the descriptive "
                        "form or a derived numeric with its own unit.",
     "calibration": "Stereo calibration required for depth-derived measurements."},
]

for s in SENSORS:
    s["v2_2_mapping"] = {
        "measurement": field("measurement"),
        "unit": field("unit"),
        "observation_type": field("observation_type"),
        "device_id": field("device_id"),
        "sensor_id": field("sensor_id"),
        "capture_method": "%s = 'sensor' (or 'ground' for a fixed installation)" % field("capture_method"),
        "location": field("location"),
        "observation_timestamp": field("observation_timestamp"),
        "source_timestamp": field("source_timestamp"),
        "raw_artifact": field("raw_artifact"),
        "raw_artifact_integrity": field("raw_artifact_integrity"),
        "provenance": field("provenance"),
        "provenance_reference": field("provenance_reference"),
        "calibration_state": field("calibration_state"),
        "quality_state": field("quality_state"),
        "data_state": field("data_state"),
        "synthetic_state": field("synthetic_state"),
        "accuracy": field("accuracy"),
        "hardware_verified": field("hardware_verified"),
    }
    s["persistence_at_group1"] = {k: cls(k) for k in
                                  ["measurement", "unit", "observation_type", "device_id",
                                   "location", "raw_artifact_integrity", "provenance",
                                   "provenance_reference", "calibration_state", "accuracy",
                                   "hardware_verified"]}


# ---------------------------------------------------------------------------
# D3 - hardware metadata requirements: can the device provide it, or must the edge?
# ---------------------------------------------------------------------------
METADATA = [
    {"item": "device_id", "device_can_provide": "PARTIAL",
     "detail": "A DS18B20 has a unique 64-bit ROM code and an RS485 sensor has an address, but "
               "neither is a VANA device identity. The EDGE assigns device_id per the Group 3 "
               "convention.",
     "edge_generated": True,
     "warning": "MUST NOT use the G3-EXT- prefix. That is contractually bound to "
                "capture_method external_api and would misrepresent a real sensor as a "
                "third-party API."},

    {"item": "observation_timestamp / source_timestamp", "device_can_provide": "NO",
     "detail": "None of the Table 1 sensors has a clock. The EDGE timestamps every reading.",
     "edge_generated": True,
     "warning": "This makes edge clock trust the single point of failure for time. See W6-2 - "
                "the contract's untrusted-clock instruction is currently unfollowable. The Holybro "
                "M10 carries UTC time in its GNSS stream, enough to set and sanity-check the edge "
                "clock. Whether the board exposes a PPS/TIMEPULSE pin for precise disciplining is "
                "UNCONFIRMED from the vendor page - an electronics question for Dhruv that decides "
                "how strong the timestamp guarantee can be."},

    {"item": "location", "device_can_provide": "YES via GNSS only",
     "detail": "Holybro M10 supplies latitude, longitude, altitude and fix quality. No other "
               "sensor knows where it is.",
     "edge_generated": False,
     "warning": "A FIXED installation may have a surveyed position more accurate than GNSS. If a "
                "surveyed coordinate is used, gnss_status must not claim FIX - that would assert "
                "a live fix that did not occur."},

    {"item": "calibration_state", "device_can_provide": "NO",
     "detail": "No sensor reports its own calibration validity. The edge must carry a calibration "
               "record and derive the state.",
     "edge_generated": True,
     "warning": "Default MUST be NOT_VERIFIED. CALIBRATED requires a real calibration event with "
                "evidence, not a config flag."},

    {"item": "quality_state", "device_can_provide": "PARTIAL",
     "detail": "Out-of-range, saturated or disconnected readings are detectable at the edge.",
     "edge_generated": True,
     "warning": "UNCERTAIN is the correct value for a no-GNSS-fix reading, and per W6-2 it is "
                "also the right marker for an untrusted clock."},

    {"item": "provenance", "device_can_provide": "NO", "edge_generated": True,
     "detail": "device_id, mission_id, captured_at and raw_artifact are all edge-assembled and "
               "must agree with the top-level values.",
     "warning": None},

    {"item": "raw_artifact", "device_can_provide": "YES - it IS the raw output",
     "edge_generated": False,
     "detail": "The ADC counts, RS485 frame, 1-Wire value or image frame. The edge must PERSIST "
               "the bytes, not just hash them.",
     "warning": "Group 3 already lost this once on 2026-08-25: a hash was computed over bytes "
                "that were never stored, making it unverifiable. Persist first, hash second."},

    {"item": "raw_artifact_integrity (sha256)", "device_can_provide": "NO",
     "edge_generated": True,
     "detail": "Computed ON THE EDGE over the captured bytes, before transmission.",
     "warning": "Hashing after upload proves what survived the network, not what the sensor "
                "produced. A placeholder checksum is prohibited by the contract."},

    {"item": "observation identity", "device_can_provide": "NO", "edge_generated": True,
     "detail": "The composite tuple is assembled at the edge from survey, zone, third segment, "
               "sensor and sequence.",
     "warning": "BLOCKED on W6-3 - a fixed ground sensor has no defined third segment. F### "
                "asserts a flight that did not happen; EXT asserts an external source it is not."},

    {"item": "idempotency / retry", "device_can_provide": "NO", "edge_generated": True,
     "detail": "IK-<observation_id> as the Idempotency-Key header. 201 -> 200 -> 409 is proven live.",
     "warning": "The edge must persist the key with the buffered reading so a retry after reboot "
                "sends the SAME key. A regenerated key on retry creates a duplicate record."},
]


# Hardware-side constraints from Arya's VANA BOM & procurement list (2026-08-28),
# Table 7 and the Final Procurement Control Status. These are ELECTRONICS facts, not
# contract facts - recorded here because they gate when an adapter can be built, and
# because two of them are UNCONFIRMED and must not be assumed away.
HARDWARE_CONSTRAINTS = [
    {"item": "DYS-1 dissolved oxygen - voltage/current and connector",
     "status": "UNCONFIRMED - vendor confirmation required",
     "affects_adapter": "DIGITAL_BUS",
     "consequence": ("The DIGITAL_BUS adapter cannot be built against this sensor until its "
                     "electrical interface is known. It is the single most expensive sensor in the "
                     "BOM at INR 62,999, so this is worth confirming before purchase, not after.")},
    {"item": "External ADC", "status": "CONDITIONAL - engineering decision",
     "affects_adapter": "ANALOG_PROBE",
     "consequence": ("Whether pH/turbidity/TDS/UV read through the Teensy/ESP32 ADC or an external "
                     "ADC changes the raw artifact: the persisted bytes are ADC counts, and which "
                     "device produced them belongs in provenance.")},
    {"item": "RS485 termination and protection", "status": "REQUIRED",
     "affects_adapter": "DIGITAL_BUS", "consequence": "Hardware prerequisite before any RS485 read."},
    {"item": "DS18B20 4.7k pull-up", "status": "REQUIRED",
     "affects_adapter": "DIGITAL_BUS",
     "consequence": ("1-Wire will not read without it. A missing pull-up produces garbage rather "
                     "than an error, so the edge must range-check and set quality_state rather than "
                     "trusting the bus.")},
    {"item": "Raspberry Pi 5 power interface", "status": "UNCONFIRMED",
     "affects_adapter": "ALL - it is the edge host",
     "consequence": "Gates the edge runtime that assembles all 18 edge-supplied fields."},
    {"item": "GNSS (Holybro M10)", "status": "EXISTING - physical verification required",
     "affects_adapter": "ALL - it supplies location",
     "consequence": ("SUPERSEDED 2026-08-29 - see _availability_contradiction. Was: consistent with Suraj's PRESENT-not-VERIFIED ruling. Until verified, "
                     "gnss_status cannot honestly report FIX.")},
    {"item": "Waterproof enclosure and connectors", "status": "OPEN PROCUREMENT",
     "affects_adapter": "ALL - field deployment",
     "consequence": ("No field deployment without it. Does not block bench work or adapter "
                     "development.")},
]


# ---------------------------------------------------------------------------
# D4 - gap list, separated exactly as Arya required.
# ---------------------------------------------------------------------------
GAPS = {
    "already_supported_by_v2_2": [
        "Measurement, unit and observation_type for every Table 1 sensor.",
        "Nested location with gnss_status and position_accuracy_m - these stop being "
        "structurally-inapplicable the moment a real GNSS receiver is attached.",
        "Raw artifact reference plus sha256 integrity with mandatory artifact_type.",
        "Provenance object and the separate reviewer-facing provenance_reference.",
        "calibration_state, quality_state, data_state, synthetic_state, accuracy.",
        "Retry/idempotency: IK-<observation_id> with 201 -> 200 -> 409, proven live 13/13.",
    ],
    "implementation_work_required": [
        "Edge-side raw-byte persistence BEFORE hashing.",
        "Edge-side sha256 over captured bytes prior to transmission.",
        "Edge assembly of device_id, timestamps, provenance and the identity tuple.",
        "Persisting the idempotency key alongside a buffered reading so a post-reboot retry "
        "reuses it.",
        "Calibration record on the edge to derive calibration_state honestly.",
        "Per-sensor conversion curves, with the curve identity recorded in provenance.",
    ],
    "contract_owner_decision_required": [
        {"id": "W6-1", "item": "Offline / store-and-forward semantics - how a consumer should "
                               "read a large observation-to-ingestion delta."},
        {"id": "W6-2", "item": "Clock-trust instruction says data_state UNCERTAIN, which the "
                               "2026-08-22 narrowing invalidated. An honest producer is rejected. "
                               "Two-description fix, no schema change."},
        {"id": "W6-3", "item": "Third identity segment for a fixed ground sensor."},
        {"id": "S-1", "item": "TDS 0-1000 ppm is a FRESHWATER range; a mangrove creek is "
                              "brackish and will read off-scale. Sensor selection question for "
                              "Workstream 1, but it determines whether the emitted measurement "
                              "is meaningful."},
        {"id": "S-2", "item": "A BME280 produces THREE measurements from one read. V2.2 carries "
                              "ONE measurement + ONE unit per observation. Ruling needed: three "
                              "separate observations sharing a timestamp, or the object form of "
                              "measurement? Group 3 recommends three separate observations - it "
                              "keeps one measurement per canonical record and needs no change."},
    ],
    "group1_integration_issue": [
        {"id": "G-33", "item": "hardware_verified is not returned in the canonical GET, and the "
                               "contract makes synthetic_state PHYSICAL conditional on it. "
                               "BLOCKING before the first PHYSICAL emission."},
    ],
}


# ---------------------------------------------------------------------------
# D5 - physical observation readiness checklist.
# ---------------------------------------------------------------------------
READINESS = [
    {"n": 1, "condition": "The sensor physically exists and is in Group 3's possession",
     "current": "NOT MET - Table 1 water sensors are 'Proposed'. Arya's Table 10 classes them "
                "TO PROCURE / VALIDATE.", "owner": "Suraj / Arya"},
    {"n": 2, "condition": "The sensor is mounted, powered and reading",
     "current": "NOT MET - no Group 3 sensor has produced a recorded reading.", "owner": "Group 3"},
    {"n": 3, "condition": "A calibration event has occurred with retained evidence",
     "current": "NOT MET - Arya's Table 10 lists calibration equipment as OPEN REQUIREMENT.",
     "owner": "Group 3"},
    {"n": 4, "condition": "The edge device persists raw bytes and hashes them locally",
     "current": "NOT MET - implementation work.", "owner": "Hemanth / edge implementation"},
    {"n": 5, "condition": "observation_id has a legitimate third segment",
     "current": "BLOCKED on W6-3.", "owner": "Arya (contract owner)"},
    {"n": 6, "condition": "The edge clock is trusted, or the reading is honestly marked",
     "current": "BLOCKED on W6-2 - the marker the contract names is invalid.",
     "owner": "Arya (contract owner)"},
    {"n": 7, "condition": "hardware_verified survives to the canonical record",
     "current": "BLOCKED on G-33 - Group 1 does not return it.", "owner": "Raj (Group 1)"},
    {"n": 8, "condition": "synthetic_state PHYSICAL is emitted with hardware_verified true",
     "current": "NOT MET - depends on 1-7. Every observation to date is CONTROLLED or SYNTHETIC.",
     "owner": "Group 3"},
    {"n": 9, "condition": "Group 1 accepts it and returns it verbatim",
     "current": "PATH PROVEN for a non-physical observation - 13/13 on 2026-08-25. Untested for "
                "PHYSICAL.", "owner": "Group 3 + Group 1"},
]


def main():
    doc = {
        "_README": ("D1-D5 for the Sensor -> VANA Data Interface workstream. Sensor models, units "
                    "and interfaces are taken from Arya Barge's BOM vana.docx (Table 1 and Table "
                    "12). Every V2.2 target is asserted to exist in the frozen schema at "
                    "generation time - this file fails rather than emitting a mapping to a field "
                    "that does not exist."),
        "_generated_by": "integration/emit_sensor_d1_d5.py",
        "_owner": "Hemanth Reddy - VANA Integration & Data Interface, Group 3",
        "_assigned_by": "Arya Barge, 2026-08-28",
        "_input_document": ("arya-27-08-2026/BOM vana.docx. NEWER SOURCES REVIEWED 2026-08-29: arya-29-08-2026/VANA BOM & procurement list .docx and refrence part BOM BOQ(1).pdf - see _availability_contradiction."),
        "_contract": "observation.schema.v2.2.json (FROZEN)",
        "_authority_boundary": ("No schema field invented, no contract change proposed as agreed. "
                                "Everything not representable is raised as a gap for the contract "
                                "owner in D4."),

        "_availability_contradiction": {
            "_raised": "2026-08-29 (gaps G-50, G-51, G-52). UNRESOLVED.",
            "_what_this_document_does_and_does_not_claim": (
                "This maps sensor INTERFACES to V2.2. It does NOT assert that any sensor is "
                "physically present. Three owners' documents disagree with the availability "
                "claim; the disagreement is recorded here rather than silently resolved."),
            "water_sensors_pH_turbidity_TDS_DO_DS18B20_BME280": {
                "dhruv_own_bom_analysis": "REQUIRED / TO PROCURE and RECOMMENDED / TO PROCURE",
                "manya_d3_hardware_status": "NO HARDWARE VERIFIED (DYS-1: VERIFY)",
                "reference_bom_boq_2026_08_29": ("NO PART NUMBER for any of them, verified across "
                                                 "every line item of the 2-page reference BOM/BOQ"),
                "_conclusion": ("Aspirational at the PARTS level, not merely unmounted. These "
                                "rows must not be presented as near-term."),
            },
            "oak_d_pro": {
                "suraj_equipment_register": "PRESENT, not VERIFIED",
                "manya_d7_present_column": "NOT PHYSICALLY EVIDENCED HERE",
                "reference_bom_boq": ("LISTED - proves it was SPECIFIED and priced, not that it "
                                      "is in the room"),
                "_conclusion": "CONTRADICTED. One line from Suraj Surve resolves it.",
                "_further_blocker": ("Even if present, gap G-42 destroys the first captured frame "
                                     "and reports VALID. Fix supplied to Dhruv; must land first."),
            },
            "mechanical_readiness_manya_d7": {
                "subsystems_listed": 20, "mounted": 0, "assembled": 0, "deployment_ready": 0,
            },
            "_recommended_column_split": ("SPECIFIED (has a part number) vs PHYSICALLY VERIFIED "
                                          "(someone has confirmed it is in the room). Today's "
                                          "honest answer: several SPECIFIED, ZERO PHYSICALLY "
                                          "VERIFIED."),
        },

        "D1_sensor_to_v2_2_mapping": SENSORS,
        "D2_edge_payload_definition": {
            "_what_this_is": ("What the edge device must produce for ONE sensor reading before "
                              "transmission. Field names are V2.2 field names; values show the "
                              "SOURCE of each, not example data."),
            "_ordering": "Persist raw bytes -> hash -> assemble -> validate -> POST with Idempotency-Key.",
            "payload_shape": {
                "contract_version": "const '2.2'",
                "schema_version": "'2.2'",
                "observation_id": "EDGE-assembled tuple - BLOCKED on W6-3 for a fixed ground unit",
                "source_identity": "EDGE - the Group 3 producing software identity",
                "survey_id / zone_id / sensor_id / observation_seq": "EDGE",
                "flight_id": "BLOCKED on W6-3",
                "observation_timestamp": "EDGE clock at capture - see W6-2",
                "source_timestamp": "EDGE clock; equals observation_timestamp for a direct sensor read",
                "ingestion_timestamp": "null - runtime-owned by Group 1",
                "device_id": "EDGE - NEVER a G3-EXT- prefix",
                "mission_id": "EDGE",
                "location": "GNSS receiver, or a surveyed coordinate with gnss_status NOT claiming FIX",
                "observation_type": "per-sensor, from D1",
                "capture_method": "'sensor' or 'ground'",
                "measurement": "converted value from the raw reading",
                "unit": "per-sensor, from D1 - REQUIRED for a numeric measurement",
                "data_state": "'RAW' at capture, 'CAPTURED' once written to edge storage",
                "quality_state": "EDGE-derived; UNCERTAIN when GNSS or clock cannot be trusted",
                "synthetic_state": "'PHYSICAL' only when every D5 condition is met, else CONTROLLED",
                "is_synthetic": "false only when synthetic_state is PHYSICAL",
                "hardware_verified": "true only with real hardware evidence - see G-33",
                "calibration_state": "from the edge calibration record; NOT_VERIFIED by default",
                "accuracy": "a verified number, or the string NOT_VERIFIED. Never estimated",
                "processing_status": "'raw' at the edge",
                "raw_artifact": "path/reference to the PERSISTED raw bytes",
                "raw_artifact_integrity": "{checksum_sha256 over persisted bytes, sha256, artifact_type}",
                "provenance": "{device_id, mission_id, captured_at, raw_artifact, operator}",
                "provenance_reference": "reviewer-facing pointer, e.g. derived from the hash",
                "idempotency_key": "IK-<observation_id>, PERSISTED with the buffered reading",
                "trace_id": "null - runtime-owned",
            },
        },
        "D3_hardware_metadata_requirements": METADATA,
        "D3b_hardware_constraints_from_bom": {
            "_source": ("Arya Barge, VANA BOM & procurement list, 2026-08-28 - Table 7 Sensor "
                        "Interface Summary and the Final Procurement Control Status."),
            "_interface_cross_check": ("All 9 sensor interfaces in her Table 7 were compared against "
                                       "D1. 9 of 9 AGREE - independently derived, zero "
                                       "disagreements."),
            "_two_are_UNCONFIRMED": ("DYS-1 electrical details and the Pi 5 power interface. Neither "
                                     "may be assumed. The DYS-1 is the most expensive item in the "
                                     "BOM at INR 62,999."),
            "constraints": HARDWARE_CONSTRAINTS,
        },
        "D4_interface_gap_list": GAPS,
        "D5_physical_observation_readiness_checklist": READINESS,

        "_the_question_arya_asked": {
            "q": "If we connect this actual sensor tomorrow, exactly how does its reading become "
                 "a truthful VANA canonical observation?",
            "a": ("Sensor produces raw output -> edge PERSISTS the raw bytes -> edge computes "
                  "sha256 over those bytes -> edge converts to a measurement with a real unit -> "
                  "edge assembles the V2.2 observation with GNSS location, its own timestamps, "
                  "device identity, provenance and honest calibration/quality states -> edge "
                  "validates against the frozen schema -> POST to Group 1 with "
                  "Idempotency-Key: IK-<observation_id> -> Group 1 generates canonical_record_id "
                  "-> Group 2 contextualises -> Group 4 governs. "
                  "EVERY STEP EXCEPT THREE IS ALREADY DEFINED AND PROVEN. The three that are not: "
                  "the identity third segment (W6-3), the clock-trust marker (W6-2), and "
                  "hardware_verified persistence (G-33). Until those close, the reading is "
                  "truthfully emittable as CONTROLLED but NOT as PHYSICAL."),
        },
        "_distinction_arya_required": {
            "hardware_capability": "The BOM says a sensor CAN measure this. Table 1.",
            "hardware_present": "Group 3 physically holds it. Only GNSS, Pi 5, OAK-D, ESP32 and "
                                "power - per Arya's Table 10. NO water sensor is present.",
            "hardware_verified": "It has been mounted, powered and shown to read correctly. "
                                 "NOTHING in Group 3 meets this - Suraj's own boundary ruling.",
            "observation_generated": "A reading has become a canonical record. ZERO physical "
                                     "observations exist. Every one to date is CONTROLLED or SYNTHETIC.",
        },
    }

    out = os.path.join(DAY6, "SENSOR_D1_D5_INTERFACE_PACKAGE.json")
    with io.open(out, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=2, ensure_ascii=False)
        fh.write("\n")

    print("D1-D5 SENSOR -> VANA INTERFACE PACKAGE")
    print()
    print("  D1  sensors mapped to V2.2      : %d" % len(SENSORS))
    print("  D2  edge payload fields defined : %d" % len(doc["D2_edge_payload_definition"]["payload_shape"]))
    print("  D3  metadata requirements       : %d" % len(METADATA))
    print("  D3b hardware constraints (BOM)  : %d  (%d UNCONFIRMED)"
          % (len(HARDWARE_CONSTRAINTS),
             sum(1 for h in HARDWARE_CONSTRAINTS if h["status"].startswith("UNCONFIRMED"))))
    print("      edge-generated              : %d of %d"
          % (sum(1 for m in METADATA if m["edge_generated"]), len(METADATA)))
    print("  D4  already supported by V2.2   : %d" % len(GAPS["already_supported_by_v2_2"]))
    print("      implementation required     : %d" % len(GAPS["implementation_work_required"]))
    print("      contract-owner decisions    : %d  (%s)"
          % (len(GAPS["contract_owner_decision_required"]),
             ", ".join(g["id"] for g in GAPS["contract_owner_decision_required"])))
    print("      Group 1 integration issues  : %d  (%s)"
          % (len(GAPS["group1_integration_issue"]),
             ", ".join(g["id"] for g in GAPS["group1_integration_issue"])))
    print("  D5  readiness conditions        : %d" % len(READINESS))
    met = sum(1 for r in READINESS if r["current"].startswith("MET"))
    print("      currently met               : %d of %d" % (met, len(READINESS)))
    print()
    print("  NEW gaps raised for the contract owner: S-1 (TDS range vs brackish water),")
    print("                                         S-2 (multi-parameter sensor, one measurement)")
    print()
    print("  -> %s" % os.path.basename(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
