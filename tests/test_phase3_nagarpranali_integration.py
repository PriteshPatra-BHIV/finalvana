"""
Test Suite: Phase 3 Nagarpranali+ Integration & Negative Case Hardening
======================================================================
Verifies:
  1. Component status disclosure matrix (WORKING, PARTIAL, BLOCKED, DESIGN-ONLY, NOT STARTED).
  2. End-to-end integration schema alignment with Nagarpranali React & Node frontend.
  3. Negative case hardening: empty location, extreme coordinates, and unmapped entities.
  4. Immutable trace propagation and replay sequence.
  5. Citizen-facing plain-language usability guarantees.
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


def test_nagarpranali_component_status_matrix():
    """Verifies that every ecosystem component is labeled per Section 1 Sprint Rules."""
    data = unified_auth_runtime.get_nagarpranali_component_status()
    assert data["ecosystem"] == "NAGARPRANALI+ & VANA Convergence"
    components = data["components"]
    assert len(components) >= 8

    status_map = {c["name"]: c["status"] for c in components}
    valid_statuses = {"WORKING", "PARTIAL", "BLOCKED", "DESIGN-ONLY", "NOT STARTED"}

    for name, status in status_map.items():
        assert status in valid_statuses, f"Component {name} has invalid status {status}"

    # Verify key boundaries
    assert status_map["MasterDB Canonical Persistence"] == "WORKING"
    assert status_map["SANSKAR Fail-Closed Governance Engine"] == "WORKING"
    assert status_map["Nagarpranali Environmental Adapter"] == "WORKING"
    assert status_map["32-Agent Governed AI Ecosystem"] == "WORKING"
    assert status_map["Live Port 8012 PrAVAH Socket Proxy"] == "BLOCKED"
    assert status_map["Physical Drone Actuator Dispatch"] == "PARTIAL"
    assert status_map["NICAI Marine Intelligence Interface"] == "DESIGN-ONLY"
    assert status_map["Bharat Mala / NW-53 Corridor Gateway"] == "NOT STARTED"


def test_nagarpranali_e2e_replay_format_matches_frontend():
    """Verifies output schema aligns with Nagarpranali React ReplaySessions.jsx."""
    req = unified_auth_runtime.NagarpranaliLifecycleRequest(
        signal_type="Flood Alert",
        location="Thane Creek Zone A",
        incident_type="Mangrove Siltation & Flooding",
        severity="HIGH",
    )
    result = unified_auth_runtime.run_nagarpranali_lifecycle(req)
    assert result["success"] is True

    # Check keys required by Nagarpranali dashboard and replay viewer
    assert "signalId" in result
    assert "telemetryId" in result
    assert "incidentId" in result
    assert "decisionId" in result
    assert "replayId" in result
    assert "replay_timeline" in result
    assert isinstance(result["replay_timeline"], list)
    assert len(result["replay_timeline"]) == 5


def test_negative_case_empty_location_fails_closed():
    """Empty or whitespace location gracefully fails closed without 500 error."""
    req = unified_auth_runtime.NagarpranaliLifecycleRequest(
        signal_type="Civic Hazard",
        location="   ",
    )
    result = unified_auth_runtime.run_nagarpranali_lifecycle(req)
    assert result["success"] is False
    assert result["governance_ruling"] == "ABSTAIN"
    assert result["environmental_intelligence"]["status"] == "abstain"
    assert "noop" in result["decision_text"].lower()


def test_negative_case_extreme_coordinates_fails_closed():
    """Out-of-range coordinates fail closed safely to ABSTAIN (noop)."""
    data = unified_auth_runtime.resolve_context(lat=999.0, lon=999.0)
    assert data["status"] == "abstain"
    assert data["governance_status"] == "governed_abstention"
    assert data["statutory_action"] == "noop"
    assert "abstention_id" in data


def test_immutable_trace_propagation():
    """Verifies that distinct invocations generate unique trace IDs starting with VANA-NP-."""
    req1 = unified_auth_runtime.NagarpranaliLifecycleRequest(location="Thane Creek Zone A")
    req2 = unified_auth_runtime.NagarpranaliLifecycleRequest(location="Thane Creek Zone A")
    res1 = unified_auth_runtime.run_nagarpranali_lifecycle(req1)
    res2 = unified_auth_runtime.run_nagarpranali_lifecycle(req2)

    trace1 = res1["environmental_intelligence"]["trace_id"]
    trace2 = res2["environmental_intelligence"]["trace_id"]

    assert trace1.startswith("VANA-NP-")
    assert trace2.startswith("VANA-NP-")
    assert trace1 != trace2, "Trace IDs must be unique per invocation"


def test_plain_language_guidance_for_citizens():
    """Verifies that citizen guidance avoids cryptic database internals."""
    req = unified_auth_runtime.NagarpranaliLifecycleRequest(location="Thane Creek Zone A")
    result = unified_auth_runtime.run_nagarpranali_lifecycle(req)

    guidance = result["ai_guidance"]
    # Guidance must be readable English
    assert "VANA Guidance Assistant" in guidance
    assert "Thane Creek Mangrove Reserve" in guidance
    # Must NOT expose raw database syntax to citizens
    assert "SELECT " not in guidance
    assert "SRID=" not in guidance


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
