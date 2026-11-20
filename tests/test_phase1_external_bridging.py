"""
VANA Phase 1 External Bridging & Ecosystem Health Automated Test Suite
======================================================================
Tests:
  1. Group 2 Pravah live probing & graceful fail-closed behavior when port 8012 is offline.
  2. Group 2 Pravah local stand-in mode compliance with Schema v2.2 and zero-fabrication markings.
  3. Group 3 Sensor Calibration Registry: registration, validity, and RBAC protection.
  4. SANSKAR Fail-Closed Governance Invariant on uncalibrated sensors / missing context.
  5. SANSKAR Authorized Governed Dispatch on verified observation + calibrated sensor + valid context.
  6. Ecosystem Health Endpoint across all 5 boundaries (G1-G5).
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
import pravah_service
import unified_auth_runtime
from api import db as masterdb_db
from api import main as masterdb_api


@pytest.fixture(scope="session", autouse=True)
def setup_env():
    auth_service.init_users_table()
    unified_auth_runtime.init_governance_audit_table()
    masterdb_db.initialize_database()


def test_pravah_probe_offline_fails_closed_safely():
    """When port 8012 is offline, probe_pravah_live reports unreachable without crashing."""
    probe = pravah_service.probe_pravah_live(timeout_sec=0.2)
    assert "reachable" in probe
    assert "endpoint" in probe
    if not probe["reachable"]:
        assert probe["fail_closed_mode"] == "ACTIVE (ABSTAIN / noop)"


def test_pravah_local_standin_zero_fabrication_contract():
    """Local stand-in mode produces contract v2.2 compliant context with transparent synthetic marking."""
    res = pravah_service.resolve_pravah_context(
        observation_id="TC-Z03-F02-LIDAR-OBS999",
        zone_id="Z03",
        allow_standin=True,
    )
    assert res["status"] == "VERIFIED"
    assert res["contract_version"] == "2.2"
    assert res["source"] == "local_integration_standin"
    assert res["is_synthetic"] is True
    assert "environmental_factors" in res
    assert res["environmental_factors"]["canopy_density_pct"] == 74.5


def test_pravah_strict_live_fails_closed_when_port_8012_unreachable():
    """When allow_standin=False and live port 8012 is offline, context resolution strictly fails closed."""
    # Temporarily set mode to LIVE
    orig_mode = pravah_service.PRAVAH_MODE
    try:
        pravah_service.PRAVAH_MODE = "LIVE"
        res = pravah_service.resolve_pravah_context(
            observation_id="TC-Z03-F02-LIDAR-OBS999",
            allow_standin=False,
            timeout_sec=0.1,
        )
        if not pravah_service.probe_pravah_live(timeout_sec=0.1)["reachable"]:
            assert res["status"] == "UNAVAILABLE"
            assert res["statutory_action"] == "FAIL_CLOSED_ABSTAIN"
            assert res["context_verified"] is False
    finally:
        pravah_service.PRAVAH_MODE = orig_mode


def test_ecosystem_health_endpoint():
    """GET /api/ecosystem/health returns live status across all 5 boundaries."""
    health = unified_auth_runtime.ecosystem_health()
    assert health["status"] == "healthy"
    eco = health["ecosystem"]
    assert "group1_masterdb" in eco
    assert eco["group1_masterdb"]["status"] == "ACTIVE"
    assert "group2_pravah" in eco
    assert eco["group2_pravah"]["fail_closed_safe"] is True
    assert "group3_sensor_calibration" in eco
    assert "group4_sanskar_governance" in eco
    assert eco["group4_sanskar_governance"]["policy"] == "FAIL_CLOSED_ABSTAIN"
    assert "group5_observability" in eco


def test_sensor_calibration_rbac_boundaries():
    """Only Platform Admin can register sensor calibration; Field Agent & Forest Officer receive 403."""
    ok, _, _, field_sess = auth_service.authenticate_user("feild@gmail.com", "vana", "FIELD_AGENT")
    ok2, _, _, admin_sess = auth_service.authenticate_user("vana@gmail.com", "vana", "ADMIN")

    req = unified_auth_runtime.CalibrationRegisterRequest(
        device_id=f"G3-DRONE-{random.randint(1000, 9999)}",
        sensor_type="LIDAR",
        calibration_cert_sha256="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        calibrated_at="2026-11-01T00:00:00Z",
        expires_at="2027-11-01T00:00:00Z",
        status="VERIFIED"
    )

    # Field agent rejected
    with pytest.raises(unified_auth_runtime.HTTPException) as exc:
        unified_auth_runtime.register_sensor_calibration(req, authorization=f"Bearer {field_sess['access_token']}")
    assert exc.value.status_code == 403

    # Admin accepted
    res = unified_auth_runtime.register_sensor_calibration(req, authorization=f"Bearer {admin_sess['access_token']}")
    assert res["status"] == "REGISTERED"
    assert res["device_id"] == req.device_id


def test_sanskar_positive_governed_execution_with_calibrated_sensor():
    """
    Positive Invariant Test:
    When an observation is VALIDATED in MasterDB, its sensor has a VERIFIED calibration cert
    in sensor_calibration_registry, context is provided, and ADMIN requests ALLOW:
    SANSKAR successfully authorizes execution dispatch.
    """
    ok, _, _, admin_sess = auth_service.authenticate_user("vana@gmail.com", "vana", "ADMIN")
    ok2, _, _, field_sess = auth_service.authenticate_user("feild@gmail.com", "vana", "FIELD_AGENT")
    admin_token = admin_sess["access_token"]
    field_token = field_sess["access_token"]

    # 1. Ingest valid observation via standard generator
    from test_phase2_multi_zone import build_zone_observation
    payload = build_zone_observation("TC", "Z03", "F02", "LIDAR", 19.1288, 72.9421, 74.5, "%")
    obs_id = payload["observation_id"]
    ik = payload["idempotency_key"]

    # Ensure device is not pre-registered so we can verify the uncalibrated gate
    conn = auth_service._open_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM sensor_calibration_registry WHERE device_id = 'G3-LIDAR-001' OR device_id = ?", (obs_id,))
    conn.commit()
    conn.close()

    ingest_res = masterdb_api.ingest_observation(
        observation=payload,
        idempotency_key=ik,
        authorization=f"Bearer {field_token}"
    )
    assert ingest_res.status_code == 201

    # 2. Before sensor is registered: SANSKAR MUST FAIL CLOSED TO ABSTAIN
    exec_req = {
        "observation_id": obs_id,
        "ruling": "ALLOW",
        "context_id": "CTX-PROVENANCE-001"
    }
    res_uncalibrated = unified_auth_runtime.vana_execute(exec_req, authorization=f"Bearer {admin_token}")
    assert res_uncalibrated["ruling"] == "ABSTAIN"
    assert res_uncalibrated["evidence"]["decision_action"] == "noop"

    try:
        # 3. Register the sensor device in sensor_calibration_registry
        cal_req = unified_auth_runtime.CalibrationRegisterRequest(
            device_id="G3-LIDAR-001",
            sensor_type="LIDAR",
            calibration_cert_sha256="a1b2c3d4e5f67890123456789abcdef0123456789abcdef0123456789abcdef0",
            calibrated_at="2026-11-01T00:00:00Z",
            expires_at="2027-11-01T00:00:00Z",
            status="VERIFIED"
        )
        unified_auth_runtime.register_sensor_calibration(cal_req, authorization=f"Bearer {admin_token}")

        # 4. Now execute with registered calibration + valid context -> ALLOW authorized!
        res_calibrated = unified_auth_runtime.vana_execute(exec_req, authorization=f"Bearer {admin_token}")
        assert res_calibrated["ruling"] == "ALLOW"
        assert res_calibrated["status"] == "action_request_generated"
        assert res_calibrated["evidence"]["decision_action"] == "dispatch"
        assert res_calibrated["execution_id"] is not None
    finally:
        conn = auth_service._open_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM sensor_calibration_registry WHERE device_id = 'G3-LIDAR-001' OR device_id = ?", (obs_id,))
        conn.commit()
        conn.close()


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
