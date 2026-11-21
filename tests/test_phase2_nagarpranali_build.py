"""
Test Suite: Phase 2 Nagarpranali+ Capability Build & Lifecycle Verification
==========================================================================
Verifies that VANA's 5-stage operational lifecycle simulation, Nagarpranali
integration adapter, AI guidance assistance, and fail-closed governance
operate with 100% compliance and zero data fabrication.
"""

import sys
from pathlib import Path
import pytest

FINALVANA_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = FINALVANA_DIR / "backend"
MASTERDB_DIR = BACKEND_DIR / "group1-masterdb"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
if str(MASTERDB_DIR) not in sys.path:
    sys.path.insert(0, str(MASTERDB_DIR))

import unified_auth_runtime
import nagarpranali_adapter


def test_nagarpranali_lifecycle_thane_creek_happy_path():
    """Verifies complete 5-stage operational chain for Thane Creek Mangrove alert."""
    result = nagarpranali_adapter.simulate_nagarpranali_lifecycle(
        signal_type="Flood Alert",
        location="Thane Creek Zone A",
        incident_type="Mangrove Encroachment Threat",
        severity="HIGH",
    )
    assert result["success"] is True
    assert result["governance_ruling"] == "ALLOW"
    assert result["signalId"].startswith("SIG-NP-")
    assert result["telemetryId"].startswith("TEL-NP-")
    assert result["incidentId"].startswith("INC-NP-")
    assert result["escalationId"].startswith("ESC-NP-")
    assert result["decisionId"].startswith("DEC-NP-")
    assert result["replayId"].startswith("REP-NP-")
    assert result["runtimeLogId"].startswith("LOG-NP-")

    env = result["environmental_intelligence"]
    assert env["zone_id"] == "TC-Z03-F02"
    assert env["tree_canopy_density"] >= 0.60
    assert "Joint Municipal Ward & Forest Department Dispatch" in result["decision_text"]

    # Replay timeline must contain all 5 sequential stages
    timeline = result["replay_timeline"]
    assert len(timeline) == 5
    assert "Stage 1 [Signal]" in timeline[0]
    assert "Stage 2 [Telemetry]" in timeline[1]
    assert "Stage 3 [Incident]" in timeline[2]
    assert "Stage 4 [Governance]" in timeline[3]
    assert "Stage 5 [Lineage & Replay]" in timeline[4]


def test_nagarpranali_lifecycle_maval_happy_path():
    """Verifies complete 5-stage operational chain for Maval Western Ghats watershed."""
    result = nagarpranali_adapter.simulate_nagarpranali_lifecycle(
        signal_type="Runoff Alert",
        location="Maval Watershed",
        incident_type="Siltation Hazard",
        lat=18.75,
        lon=73.42,
    )
    assert result["success"] is True
    assert result["governance_ruling"] == "ALLOW"
    env = result["environmental_intelligence"]
    assert env["zone_id"] == "MV-Z01-F01"
    assert env["tree_canopy_density"] >= 0.70
    assert "Western Ghats" in env["protection_class"]


def test_nagarpranali_lifecycle_fail_closed_unmapped():
    """Verifies that an unmapped location strictly fails closed to ABSTAIN (noop)."""
    result = nagarpranali_adapter.simulate_nagarpranali_lifecycle(
        signal_type="Noise Complaint",
        location="Unknown Industrial Lot 99",
        lat=0.0,
        lon=0.0,
    )
    assert result["success"] is False
    assert result["governance_ruling"] == "ABSTAIN"
    assert "noop" in result["decision_text"].lower()
    assert result["environmental_intelligence"]["status"] == "abstain"
    assert result["environmental_intelligence"]["abstention_id"].startswith("ABS-")


def test_nagarpranali_lifecycle_endpoint_via_runtime():
    """Verifies the /api/nagarpranali/lifecycle/run endpoint handler."""
    req = unified_auth_runtime.NagarpranaliLifecycleRequest(
        signal_type="Flood Alert",
        location="Thane Creek Zone A",
        incident_type="Mangrove Encroachment",
        severity="HIGH",
    )
    data = unified_auth_runtime.run_nagarpranali_lifecycle(req)
    assert data["success"] is True
    assert data["message"] == "Operational Chain Completed (VANA Governed)"
    assert "VANA Guidance Assistant" in data["ai_guidance"]


def test_nagarpranali_ai_guidance_field_present():
    """Verifies plain-language AI guidance is generated for the incident response."""
    result = nagarpranali_adapter.simulate_nagarpranali_lifecycle(
        signal_type="Flood Alert",
        location="Thane Creek Zone A",
    )
    assert "ai_guidance" in result
    assert "VANA Guidance Assistant" in result["ai_guidance"]
    assert "Thane Creek Mangrove Reserve" in result["ai_guidance"]


def test_zero_fabrication_canonical_record_link():
    """Verifies that the canonical record link references real MasterDB record."""
    result = nagarpranali_adapter.simulate_nagarpranali_lifecycle(
        location="Thane Creek Zone A",
    )
    canonical_id = result["environmental_intelligence"]["canonical_record_id"]
    assert canonical_id == "CR-e95e9174-969b-46ff-9ba3-cbff085150b4"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
