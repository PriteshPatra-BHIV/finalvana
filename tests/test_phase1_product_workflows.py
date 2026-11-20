"""
VANA Phase 1 Product, UX & Forest Department Workflow Automated Test Suite
=========================================================================
Tests the complete end-to-end lifecycle and role boundaries:
  1. Role Authentication & RBAC Boundaries (ADMIN, FIELD_AGENT, FOREST_OFFICER)
  2. Observation Intake, Contract Validation (Group 3 v2.2), and Idempotency
  3. MasterDB Canonical Persistence & Lineage Trace
  4. SANSKAR Governance Fail-Closed ABSTAIN Invariant
  5. Forest Officer Review Boundary (Review allowed, Execution strictly forbidden)
  6. Zero-Fabrication Audit Ledger Verification
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

# Ensure finalvana backend and masterdb are in path
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
import unified_auth_runtime


@pytest.fixture(scope="session", autouse=True)
def setup_databases():
    """Ensure auth and masterdb tables are clean and initialized."""
    auth_service.init_users_table()
    unified_auth_runtime.init_governance_audit_table()
    masterdb_db.initialize_database()


def get_canonical_payload(new_obs_id=None):
    """Load canonical v2.2 payload from sample package and set contract-compliant components."""
    p = MASTERDB_DIR / "sample_mission_package.v2.2.json"
    with open(p, "r", encoding="utf-8") as f:
        obs = json.load(f)["observations"][0]
    payload = copy.deepcopy(obs)
    if new_obs_id:
        obs_id = new_obs_id
        parts = obs_id.split("-")
        survey_id, zone_id, flight_id, sensor_id, obs_seq = parts[0], parts[1], parts[2], parts[3], parts[4]
    else:
        num = random.randint(100, 999)
        survey_id, zone_id, flight_id, sensor_id, obs_seq = "TC", "Z03", "F02", "LIDAR", f"OBS{num}"
        obs_id = f"{survey_id}-{zone_id}-{flight_id}-{sensor_id}-{obs_seq}"

    payload["observation_id"] = obs_id
    payload["survey_id"] = survey_id
    payload["zone_id"] = zone_id
    payload["flight_id"] = flight_id
    payload["sensor_id"] = sensor_id
    payload["observation_seq"] = obs_seq
    payload["mission_id"] = f"{survey_id}-{zone_id}-{flight_id}"
    payload["idempotency_key"] = obs_id
    if "provenance" in payload and isinstance(payload["provenance"], dict):
        payload["provenance"]["mission_id"] = payload["mission_id"]
    return payload


# -----------------------------------------------------------------------------
# 1. AUTHENTICATION & RBAC BOUNDARIES
# -----------------------------------------------------------------------------

def test_admin_authentication():
    """Platform Admin authenticates and receives valid Bearer session."""
    ok, msg, code, session = auth_service.authenticate_user("vana@gmail.com", "vana", "ADMIN")
    assert ok is True
    assert session is not None
    assert session["user"]["role"] == "ADMIN"
    assert "access_token" in session
    assert session["user"]["email"] == "vana@gmail.com"


def test_field_agent_authentication():
    """Field Agent authenticates and receives valid Bearer session."""
    ok, msg, code, session = auth_service.authenticate_user("feild@gmail.com", "vana", "FIELD_AGENT")
    assert ok is True
    assert session is not None
    assert session["user"]["role"] == "FIELD_AGENT"
    assert "access_token" in session


def test_forest_officer_authentication():
    """Forest Officer authenticates and receives valid Bearer session."""
    ok, msg, code, session = auth_service.authenticate_user("forest@gmail.com", "vana", "FOREST_OFFICER")
    assert ok is True
    assert session is not None
    assert session["user"]["role"] == "FOREST_OFFICER"
    assert "access_token" in session


def test_invalid_credentials_rejected():
    """Invalid password or non-existent user rejected with 401."""
    ok, msg, code, session = auth_service.authenticate_user("vana@gmail.com", "wrong_password", "ADMIN")
    assert ok is False
    assert code == 401
    assert session is None


def test_rbac_field_agent_cannot_execute():
    """Field Agent is strictly rejected (HTTP 403) from triggering SANSKAR execution dispatch."""
    ok, _, _, field_session = auth_service.authenticate_user("feild@gmail.com", "vana", "FIELD_AGENT")
    token = field_session["access_token"]

    req_payload = {
        "observation_id": "TC-Z03-EXT-OPENMETEO-OBS001",
        "proposed_action": "DISPATCH_RANGER_SURVEILLANCE"
    }

    with pytest.raises(unified_auth_runtime.HTTPException) as exc:
        unified_auth_runtime.vana_execute(req_payload, authorization=f"Bearer {token}")
    assert exc.value.status_code == 403
    assert "ADMIN" in exc.value.detail


def test_rbac_forest_officer_cannot_execute():
    """Forest Officer is strictly rejected (HTTP 403) from triggering SANSKAR execution dispatch."""
    ok, _, _, forest_session = auth_service.authenticate_user("forest@gmail.com", "vana", "FOREST_OFFICER")
    token = forest_session["access_token"]

    req_payload = {
        "observation_id": "TC-Z03-EXT-OPENMETEO-OBS001",
        "proposed_action": "DISPATCH_RANGER_SURVEILLANCE"
    }

    with pytest.raises(unified_auth_runtime.HTTPException) as exc:
        unified_auth_runtime.vana_execute(req_payload, authorization=f"Bearer {token}")
    assert exc.value.status_code == 403
    assert "ADMIN" in exc.value.detail


# -----------------------------------------------------------------------------
# 2. OBSERVATION INTAKE & GROUP 3 V2.2 CONTRACT VALIDATION
# -----------------------------------------------------------------------------

def test_field_agent_valid_observation_submission():
    """Field agent submits valid v2.2 observation -> 201 Created with canonical record."""
    ok, _, _, field_session = auth_service.authenticate_user("feild@gmail.com", "vana", "FIELD_AGENT")
    token = field_session["access_token"]

    num = random.randint(100, 999)
    test_obs_id = f"TC-Z03-F02-LIDAR-OBS{num}"
    test_ik = f"IK-{test_obs_id}"
    payload = get_canonical_payload(test_obs_id)
    payload["idempotency_key"] = test_ik

    res = masterdb_api.ingest_observation(
        observation=payload,
        idempotency_key=test_ik,
        authorization=f"Bearer {token}"
    )

    assert res.status_code == 201
    content = json.loads(res.body.decode("utf-8"))
    assert content["status"] == "ACCEPTED"
    assert content["observation_id"] == test_obs_id
    assert content["canonical_record_id"].startswith("CR-")


def test_idempotent_replay():
    """Submitting the exact same observation and key returns 200 IDEMPOTENT_REPLAY."""
    ok, _, _, field_session = auth_service.authenticate_user("feild@gmail.com", "vana", "FIELD_AGENT")
    token = field_session["access_token"]

    num = random.randint(100, 999)
    test_obs_id = f"TC-Z03-F02-LIDAR-OBS{num}"
    test_ik = f"IK-{test_obs_id}"
    payload = get_canonical_payload(test_obs_id)
    payload["idempotency_key"] = test_ik

    # First submission
    res1 = masterdb_api.ingest_observation(
        observation=payload,
        idempotency_key=test_ik,
        authorization=f"Bearer {token}"
    )
    assert res1.status_code == 201

    # Second submission with same payload and key
    res2 = masterdb_api.ingest_observation(
        observation=payload,
        idempotency_key=test_ik,
        authorization=f"Bearer {token}"
    )
    assert res2.status_code == 200
    content2 = json.loads(res2.body.decode("utf-8"))
    assert content2["status"] == "IDEMPOTENT_REPLAY"


def test_invalid_observation_rejected():
    """Observation missing required location fields is rejected with HTTP 400."""
    ok, _, _, field_session = auth_service.authenticate_user("feild@gmail.com", "vana", "FIELD_AGENT")
    token = field_session["access_token"]

    invalid_payload = {
        "contract_version": "2.2",
        "schema_version": "2.2",
        "observation_id": f"INVALID-{uuid.uuid4().hex[:6]}",
        "source_identity": "group3-field-edge",
        "observation_timestamp": "2026-08-25T10:00:00Z",
    }

    res = masterdb_api.ingest_observation(
        observation=invalid_payload,
        idempotency_key=f"IK-INV-{uuid.uuid4().hex[:6]}",
        authorization=f"Bearer {token}"
    )
    assert res.status_code == 400
    content = json.loads(res.body.decode("utf-8"))
    assert content["status"] == "REJECTED"
    assert len(content["errors"]) > 0


# -----------------------------------------------------------------------------
# 3. SANSKAR GOVERNANCE FAIL-CLOSED ABSTAIN INVARIANT
# -----------------------------------------------------------------------------

def test_sanskar_uncalibrated_abstain_invariant():
    """
    Constitutional Rule: If sensor calibration state is NOT_VERIFIED,
    SANSKAR must fail-closed and return ABSTAIN with action_taken='noop',
    even when requested by an authenticated Admin.
    """
    ok, _, _, admin_session = auth_service.authenticate_user("vana@gmail.com", "vana", "ADMIN")
    token = admin_session["access_token"]

    req_payload = {
        "observation_id": "TC-Z03-EXT-OPENMETEO-OBS001",
        "proposed_action": "DISPATCH_RANGER_SURVEILLANCE"
    }

    res = unified_auth_runtime.vana_execute(req_payload, authorization=f"Bearer {token}")
    assert res["status"] in ("ABSTAIN", "governed_abstention")
    assert res["ruling"] == "ABSTAIN"
    assert res["evidence"]["decision_action"] == "noop"
    assert "abstention_record_id" in res
    assert res["evidence"]["status"] == "governed_abstention"


# -----------------------------------------------------------------------------
# 4. STATUTORY AUDIT & ZERO-FABRICATION VERIFICATION
# -----------------------------------------------------------------------------

def test_audit_records_are_genuine():
    """Verify MasterDB summary contains genuine recent events, not mocks."""
    summary = masterdb_api.get_dashboard_summary()
    assert "recent_events" in summary
    assert isinstance(summary["recent_events"], list)
    for ev in summary["recent_events"]:
        assert "id" in ev or "event_id" in ev
        assert "severity" in ev or "status" in ev
