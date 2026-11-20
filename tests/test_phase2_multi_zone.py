"""
VANA Phase 2 Multi-Zone End-to-End & Negative Cases Test Suite
=============================================================
Verifies multi-zone surveillance intake, authoritative MasterDB persistence,
SANSKAR fail-closed governance invariants, and all 8 required negative test cases:
  1. Duplicate observation submission (idempotency key deduplication)
  2. Invalid observation payload (schema rejection)
  3. Missing provenance block or required fields
  4. Unauthorized execution dispatch attempts (RBAC boundaries)
  5. Missing context resolution (fail-closed ABSTAIN)
  6. Stale or unverifiable context (fail-closed ABSTAIN)
  7. ABSTAIN creates an explicit no-op with persistent receipt
  8. Zero unauthorized physical dispatch occurs
"""

import copy
import json
import os
import random
import sys
import time
import uuid
from pathlib import Path
import pytest

FINALVANA_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = FINALVANA_DIR / "backend"
MASTERDB_DIR = BACKEND_DIR / "group1-masterdb"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
if str(MASTERDB_DIR) not in sys.path:
    sys.path.insert(0, str(MASTERDB_DIR))

import auth_service
from api import main as masterdb_api
from api import db as masterdb_db
from api.validation import validate_observation
import unified_auth_runtime


@pytest.fixture(scope="session", autouse=True)
def setup_phase2_databases():
    """Initialize SQLite tables for auth, governance audit, and MasterDB canonical records."""
    auth_service.init_users_table()
    unified_auth_runtime.init_governance_audit_table()
    masterdb_db.initialize_database()


def build_zone_observation(survey_id: str, zone_id: str, flight_id: str, sensor_id: str, lat: float, lon: float, metric: float, unit: str):
    """Construct a contract v2.2 compliant observation for any surveillance zone."""
    sample_file = MASTERDB_DIR / "sample_mission_package.v2.2.json"
    with open(sample_file, "r", encoding="utf-8") as f:
        base_sample = json.load(f)["observations"][0]

    obs = copy.deepcopy(base_sample)
    num = random.randint(100, 999)
    obs_seq = f"OBS{num}"
    obs_id = f"{survey_id}-{zone_id}-{flight_id}-{sensor_id}-{obs_seq}"
    mission_id = f"{survey_id}-{zone_id}-{flight_id}"
    ik = f"IK-{obs_id}"
    ts = "2026-08-28T14:45:00Z"

    obs["observation_id"] = obs_id
    obs["survey_id"] = survey_id
    obs["zone_id"] = zone_id
    obs["flight_id"] = flight_id
    obs["sensor_id"] = sensor_id
    obs["observation_seq"] = obs_seq
    obs["mission_id"] = mission_id
    obs["observation_timestamp"] = ts
    obs["source_timestamp"] = ts
    obs["idempotency_key"] = ik
    obs["measurement"] = metric
    obs["unit"] = unit
    obs["location"] = {
        "latitude": lat,
        "longitude": lon,
        "altitude_m": 120.0,
        "gnss_status": "NOT_VERIFIED",
        "position_accuracy_m": None
    }
    if "provenance" in obs and isinstance(obs["provenance"], dict):
        obs["provenance"]["mission_id"] = mission_id
        obs["provenance"]["captured_at"] = ts

    return obs


# =============================================================================
# MULTI-ZONE SURVEILLANCE INTAKE & PERSISTENCE
# =============================================================================

def test_zone_thane_creek_mangrove():
    """Zone 1: Thane Creek Mangrove Sanctuary (TC-Z03) intake & persistence."""
    ok, _, _, session = auth_service.authenticate_user("feild@gmail.com", "vana", "FIELD_AGENT")
    assert ok is True
    token = session["access_token"]

    obs = build_zone_observation("TC", "Z03", "F02", "LIDAR", 19.1288, 72.9421, 74.5, "%")
    errors = validate_observation(obs)
    assert len(errors) == 0, f"Schema validation failed: {errors}"

    res = masterdb_api.ingest_observation(
        observation=obs,
        idempotency_key=obs["idempotency_key"],
        authorization=f"Bearer {token}"
    )
    assert res.status_code == 201
    body = json.loads(res.body.decode("utf-8"))
    assert body["status"] == "ACCEPTED"
    assert body["observation_id"] == obs["observation_id"]
    assert body["canonical_record_id"].startswith("CR-")


def test_zone_maval_watershed():
    """Zone 2: Maval Western Ghats Catchment (MV-Z01) intake & persistence."""
    ok, _, _, session = auth_service.authenticate_user("feild@gmail.com", "vana", "FIELD_AGENT")
    assert ok is True
    token = session["access_token"]

    obs = build_zone_observation("MV", "Z01", "F01", "LIDAR", 18.7180, 73.4730, 16.2, "m")
    errors = validate_observation(obs)
    assert len(errors) == 0, f"Schema validation failed: {errors}"

    res = masterdb_api.ingest_observation(
        observation=obs,
        idempotency_key=obs["idempotency_key"],
        authorization=f"Bearer {token}"
    )
    assert res.status_code == 201
    body = json.loads(res.body.decode("utf-8"))
    assert body["status"] == "ACCEPTED"
    assert body["observation_id"] == obs["observation_id"]


def test_zone_samachar_estuary():
    """Zone 3: Samachar Coastal Estuary (SMR-Z01) intake & persistence."""
    ok, _, _, session = auth_service.authenticate_user("feild@gmail.com", "vana", "FIELD_AGENT")
    assert ok is True
    token = session["access_token"]

    obs = build_zone_observation("SMR", "Z01", "F01", "OPTICAL", 19.2220, 72.9560, 8.4, "index")
    errors = validate_observation(obs)
    assert len(errors) == 0, f"Schema validation failed: {errors}"

    res = masterdb_api.ingest_observation(
        observation=obs,
        idempotency_key=obs["idempotency_key"],
        authorization=f"Bearer {token}"
    )
    assert res.status_code == 201
    body = json.loads(res.body.decode("utf-8"))
    assert body["status"] == "ACCEPTED"
    assert body["observation_id"] == obs["observation_id"]


# =============================================================================
# EIGHT REQUIRED NEGATIVE TEST CASES
# =============================================================================

def test_negative_1_duplicate_observation():
    """Negative Case 1: Duplicate submission returns 200 IDEMPOTENT_REPLAY and inserts 0 duplicate rows."""
    ok, _, _, session = auth_service.authenticate_user("feild@gmail.com", "vana", "FIELD_AGENT")
    token = session["access_token"]

    obs = build_zone_observation("TC", "Z03", "F02", "LIDAR", 19.1288, 72.9421, 68.2, "%")
    ik = obs["idempotency_key"]
    obs_id = obs["observation_id"]

    # Initial submission
    res1 = masterdb_api.ingest_observation(observation=obs, idempotency_key=ik, authorization=f"Bearer {token}")
    assert res1.status_code == 201

    # Replay duplicate submission
    res2 = masterdb_api.ingest_observation(observation=obs, idempotency_key=ik, authorization=f"Bearer {token}")
    assert res2.status_code == 200
    body2 = json.loads(res2.body.decode("utf-8"))
    assert body2["status"] == "IDEMPOTENT_REPLAY"
    assert body2["canonical_record_id"].startswith("CR-")

    # MasterDB SQLite row count check
    conn = masterdb_db.get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM observation WHERE observation_id = ?", (obs_id,))
        count = cur.fetchone()[0]
        assert count == 1, f"Expected exactly 1 row, found {count}"
    finally:
        conn.close()


def test_negative_2_invalid_observation_payload():
    """Negative Case 2: Malformed payload violating v2.2 schema is rejected with HTTP 400 REJECTED."""
    ok, _, _, session = auth_service.authenticate_user("feild@gmail.com", "vana", "FIELD_AGENT")
    token = session["access_token"]

    malformed = {
        "contract_version": "2.2",
        "observation_id": "INVALID_PATTERN_OBS",
        "survey_id": "TC",
        "observation_timestamp": "invalid_date"
    }

    res = masterdb_api.ingest_observation(
        observation=malformed,
        idempotency_key="IK-INVALID-001",
        authorization=f"Bearer {token}"
    )
    assert res.status_code == 400
    body = json.loads(res.body.decode("utf-8"))
    assert body["status"] == "REJECTED"
    assert len(body.get("errors", [])) > 0


def test_negative_3_missing_provenance():
    """Negative Case 3: Missing provenance block fails semantic contract validation."""
    obs = build_zone_observation("TC", "Z03", "F02", "LIDAR", 19.1288, 72.9421, 55.0, "%")
    obs.pop("provenance", None)

    errors = validate_observation(obs)
    assert any("provenance" in err.lower() for err in errors), "Validation should reject missing provenance"


def test_negative_4_unauthorized_execution():
    """Negative Case 4: Non-admin roles (Field Agent, Forest Officer) receive HTTP 403 when invoking execute."""
    # Field Agent attempt
    ok, _, _, field_session = auth_service.authenticate_user("feild@gmail.com", "vana", "FIELD_AGENT")
    with pytest.raises(unified_auth_runtime.HTTPException) as exc1:
        unified_auth_runtime.vana_execute({"observation_id": "TC-Z03-F02-LIDAR-OBS001"}, authorization=f"Bearer {field_session['access_token']}")
    assert exc1.value.status_code == 403

    # Forest Officer attempt
    ok, _, _, fo_session = auth_service.authenticate_user("forest@gmail.com", "vana", "FOREST_OFFICER")
    with pytest.raises(unified_auth_runtime.HTTPException) as exc2:
        unified_auth_runtime.vana_execute({"observation_id": "TC-Z03-F02-LIDAR-OBS001"}, authorization=f"Bearer {fo_session['access_token']}")
    assert exc2.value.status_code == 403


def test_negative_5_missing_context():
    """Negative Case 5: When context_id is None, SANSKAR overrides caller ruling to ABSTAIN (Fail-Closed)."""
    ok, _, _, admin_session = auth_service.authenticate_user("vana@gmail.com", "vana", "ADMIN")
    admin_token = admin_session["access_token"]

    req = {
        "observation_id": "TC-Z03-EXT-OPENMETEO-OBS001",
        "ruling": "ALLOW",
        "context_id": None,  # Context missing
        "proposed_action": "DISPATCH_PATROL"
    }

    res = unified_auth_runtime.vana_execute(req, authorization=f"Bearer {admin_token}")
    assert res["ruling"] == "ABSTAIN"
    assert res["evidence"]["decision_action"] == "noop"
    assert "Sensor calibration or context unverified" in res["decision_reason"] or "evidence threshold not met" in res["decision_reason"]


def test_negative_6_stale_or_unverifiable_context():
    """Negative Case 6: Unverified observation calibration state triggers fail-closed ABSTAIN."""
    ok, _, _, admin_session = auth_service.authenticate_user("vana@gmail.com", "vana", "ADMIN")
    admin_token = admin_session["access_token"]

    req = {
        "observation_id": "NON-EXISTENT-UNVERIFIED-OBS",
        "ruling": "ALLOW",
        "context_id": "ctx_stale_999",
        "proposed_action": "DISPATCH_DRONE"
    }

    res = unified_auth_runtime.vana_execute(req, authorization=f"Bearer {admin_token}")
    assert res["ruling"] == "ABSTAIN"
    assert res["evidence"]["decision_action"] == "noop"


def test_negative_7_abstain_creates_explicit_noop_and_receipt():
    """Negative Case 7: Governed abstention creates explicit noop action and persistent receipt in MasterDB."""
    ok, _, _, admin_session = auth_service.authenticate_user("vana@gmail.com", "vana", "ADMIN")
    admin_token = admin_session["access_token"]

    req = {
        "observation_id": "TC-Z03-EXT-OPENMETEO-OBS001",
        "ruling": "ABSTAIN",
        "proposed_action": "DISPATCH_PATROL"
    }

    res = unified_auth_runtime.vana_execute(req, authorization=f"Bearer {admin_token}")
    assert res["status"] == "governed_abstention"
    assert res["ruling"] == "ABSTAIN"
    assert res["evidence"]["decision_action"] == "noop"
    assert res["execution_id"] is None
    assert res["abstention_record_id"].startswith("ABS-")

    # Verify audit receipt in governance_execution_audit table
    conn = auth_service._open_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT effective_ruling, action_taken, abstention_record_id FROM governance_execution_audit WHERE abstention_record_id = ?", (res["abstention_record_id"],))
        row = cur.fetchone()
        assert row is not None, "Abstention record must be persistently saved in governance audit table"
        assert row[0] == "ABSTAIN"
        assert row[1] == "noop"
    finally:
        conn.close()


def test_negative_8_no_unauthorized_physical_dispatch():
    """Negative Case 8: Governed ABSTAIN guarantees execution_id is None and zero dispatch is triggered."""
    ok, _, _, admin_session = auth_service.authenticate_user("vana@gmail.com", "vana", "ADMIN")
    admin_token = admin_session["access_token"]

    req = {
        "observation_id": "TC-Z03-EXT-OPENMETEO-OBS001",
        "ruling": "ALLOW",
        "context_id": None
    }

    res = unified_auth_runtime.vana_execute(req, authorization=f"Bearer {admin_token}")
    assert res["evidence"]["governance_allowed"] is False
    assert res["evidence"]["execution_id"] is None
    assert res["evidence"]["decision_action"] == "noop"
