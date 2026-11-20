"""
VANA Phase 3 Human-in-the-Loop Statutory Actuation & Dispatch Test Suite
========================================================================
Tests:
  1. Two-Man Rule Statutory Quorum Gate: Forest Officer + Admin signatures required.
  2. Single-Signature Pending State: Single party proposal holds in PENDING_QUORUM (action: noop).
  3. RBAC Enforcement: Field Agent cannot propose or sign dispatches (HTTP 403 Forbidden).
  4. Dry-Run Flight Plan Engine: Generates deterministic 4-waypoint survey transects.
  5. Physical-Gated Fail-Closed Safety: Detached physical hardware fails closed to safe no-op.
  6. Ledger Persistence & Cryptographic SHA-256 Receipts in statutory_dispatch_ledger.
"""

import json
import random
import sys
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
import unified_auth_runtime
from dispatch_adapter import dispatch_adapter
from api import db as masterdb_db


@pytest.fixture(scope="session", autouse=True)
def setup_databases():
    auth_service.init_users_table()
    unified_auth_runtime.init_governance_audit_table()
    masterdb_db.initialize_database()


def test_two_man_rule_quorum_workflow():
    """
    Two-Man Rule Workflow:
      1. Forest Officer proposes dispatch -> PENDING_QUORUM (action: noop).
      2. Admin signs proposal -> Quorum fulfilled -> AUTHORIZED_DISPATCHED (action: dispatch_simulated).
    """
    ok, _, _, officer_sess = auth_service.authenticate_user("forest@gmail.com", "vana", "FOREST_OFFICER")
    ok2, _, _, admin_sess = auth_service.authenticate_user("vana@gmail.com", "vana", "ADMIN")
    officer_token = officer_sess["access_token"]
    admin_token = admin_sess["access_token"]

    obs_id = f"TC-Z03-F02-LIDAR-OBS{random.randint(100000, 999999)}"

    # 1. Forest Officer proposes dispatch
    prop_req = unified_auth_runtime.DispatchProposalRequest(
        observation_id=obs_id,
        proposed_action="DISPATCH_DRONE_SURVEILLANCE",
        dispatch_mode="DRY_RUN",
        target_zone="Z03"
    )
    prop_res = unified_auth_runtime.propose_dispatch(prop_req, authorization=f"Bearer {officer_token}")

    assert prop_res["status"] == "PENDING_QUORUM"
    assert prop_res["action_taken"] == "noop"
    assert prop_res["quorum_met"] is False
    assert "ADMIN" in prop_res["missing_signatories"]
    disp_id = prop_res["dispatch_id"]

    # 2. Platform Admin signs dispatch -> Quorum Met!
    sign_req = unified_auth_runtime.DispatchSignRequest(dispatch_id=disp_id)
    sign_res = unified_auth_runtime.sign_dispatch(sign_req, authorization=f"Bearer {admin_token}")

    assert sign_res["status"] == "AUTHORIZED_DISPATCHED"
    assert sign_res["action_taken"] == "dispatch_simulated"
    assert sign_res["quorum_met"] is True
    assert sign_res["signatories"]["officer_id"] is not None
    assert sign_res["signatories"]["admin_id"] is not None
    assert "flight_plan" in sign_res
    assert sign_res["flight_plan"]["waypoint_count"] == 4
    assert len(sign_res["receipt_sha256"]) == 64


def test_rbac_field_agent_cannot_propose_or_sign_dispatch():
    """Field Agents are strictly prohibited (HTTP 403) from proposing or signing statutory dispatches."""
    ok, _, _, field_sess = auth_service.authenticate_user("feild@gmail.com", "vana", "FIELD_AGENT")
    token = field_sess["access_token"]

    prop_req = unified_auth_runtime.DispatchProposalRequest(
        observation_id="TC-Z03-EXT-OPENMETEO-OBS001",
        proposed_action="DISPATCH_DRONE_SURVEILLANCE"
    )
    with pytest.raises(unified_auth_runtime.HTTPException) as exc:
        unified_auth_runtime.propose_dispatch(prop_req, authorization=f"Bearer {token}")
    assert exc.value.status_code == 403

    sign_req = unified_auth_runtime.DispatchSignRequest(dispatch_id="disp_mock_123")
    with pytest.raises(unified_auth_runtime.HTTPException) as exc2:
        unified_auth_runtime.sign_dispatch(sign_req, authorization=f"Bearer {token}")
    assert exc2.value.status_code == 403


def test_physical_gated_mode_fails_closed_when_hardware_detached():
    """When dispatch_mode is PHYSICAL_GATED and physical GCS is detached, fails closed to safe no-op."""
    ok, _, _, officer_sess = auth_service.authenticate_user("forest@gmail.com", "vana", "FOREST_OFFICER")
    ok2, _, _, admin_sess = auth_service.authenticate_user("vana@gmail.com", "vana", "ADMIN")

    officer_token = officer_sess["access_token"]
    admin_token = admin_sess["access_token"]

    prop_req = unified_auth_runtime.DispatchProposalRequest(
        observation_id=f"MV-Z01-F01-LIDAR-OBS{random.randint(100000, 999999)}",
        proposed_action="DISPATCH_DRONE_SURVEILLANCE",
        dispatch_mode="PHYSICAL_GATED",
        target_zone="Z01"
    )
    prop_res = unified_auth_runtime.propose_dispatch(prop_req, authorization=f"Bearer {officer_token}")
    disp_id = prop_res["dispatch_id"]

    sign_res = unified_auth_runtime.sign_dispatch(
        unified_auth_runtime.DispatchSignRequest(dispatch_id=disp_id),
        authorization=f"Bearer {admin_token}"
    )

    assert sign_res["status"] == "PHYSICAL_HARDWARE_DETACHED"
    assert sign_res["action_taken"] == "noop"
    assert sign_res["quorum_met"] is True
    assert "detached" in sign_res["message"].lower()


def test_statutory_dispatch_ledger_records():
    """GET /api/dispatch/ledger returns immutable audit ledger rows."""
    ok, _, _, admin_sess = auth_service.authenticate_user("vana@gmail.com", "vana", "ADMIN")
    ledger_res = unified_auth_runtime.get_dispatch_ledger(authorization=f"Bearer {admin_sess['access_token']}")

    assert "count" in ledger_res
    assert ledger_res["count"] >= 1
    assert "dispatches" in ledger_res
    first = ledger_res["dispatches"][0]
    assert "dispatch_id" in first
    assert "receipt_sha256" in first
    assert len(first["receipt_sha256"]) == 64


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
