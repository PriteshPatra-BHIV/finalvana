"""
Test Suite: Phase 1 Nagarpranali+ Alignment & Environmental Enrichment
======================================================================
Verifies that VANA's environmental context resolution and Nagarpranali
enrichment endpoints satisfy the Nagarpranali+ convergence contract with
strict zero-fabrication and fail-closed safety.
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


def test_nagarpranali_thane_creek_coordinate_resolution():
    """Verifies that Thane Creek mangrove coordinates return verified eco-zone context."""
    data = unified_auth_runtime.resolve_context(lat=19.12, lon=72.99)
    assert data["status"] == "success"
    assert data["zone_id"] == "TC-Z03-F02"
    assert data["zone_name"] == "Thane Creek Mangrove Reserve"
    assert data["protection_class"] == "Eco-Sensitive Coastal Zone 1"
    assert data["tree_canopy_density"] >= 0.60
    assert data["governance_status"] == "governed_verified"
    assert data["statutory_action"] == "ALLOW"
    assert data["canonical_record_id"].startswith("CR-")
    assert data["trace_id"].startswith("VANA-NP-")


def test_nagarpranali_location_string_resolution():
    """Verifies that textual location 'Thane Creek Zone A' matches the mangrove reserve."""
    data = unified_auth_runtime.resolve_context(location="Thane Creek Zone A")
    assert data["status"] == "success"
    assert data["zone_id"] == "TC-Z03-F02"
    assert "Mangrove" in data["zone_name"]
    assert "CR-e95e9174" in data["canonical_record_id"]


def test_nagarpranali_maval_watershed_resolution():
    """Verifies that Western Ghats catchment coordinates return watershed intelligence."""
    data = unified_auth_runtime.resolve_context(lat=18.75, lon=73.42)
    assert data["status"] == "success"
    assert data["zone_id"] == "MV-Z01-F01"
    assert "Western Ghats" in data["protection_class"]
    assert data["tree_canopy_density"] >= 0.70


def test_nagarpranali_fail_closed_unmapped_coordinates():
    """Verifies that unmapped coordinates strictly fail closed to ABSTAIN (noop)."""
    data = unified_auth_runtime.resolve_context(lat=0.0, lon=0.0)
    assert data["status"] == "abstain"
    assert data["governance_status"] == "governed_abstention"
    assert data["statutory_action"] == "noop"
    assert data["abstention_id"].startswith("ABS-")
    assert "outside verified" in data["reason"].lower()


def test_nagarpranali_incident_enrich_endpoint():
    """Verifies that a civic incident payload is enriched with environmental intelligence."""
    req = unified_auth_runtime.NagarpranaliEnrichRequest(
        signal_type="Flood Alert",
        location="Thane Creek Zone A",
        incident_type="Flood Incident",
        severity="HIGH",
    )
    data = unified_auth_runtime.enrich_nagarpranali(req)
    assert data["signal_type"] == "Flood Alert"
    assert data["is_environmentally_sensitive"] is True
    assert "Joint Municipal Ward & Forest Department" in data["recommended_escalation"]
    assert "Thane Creek Mangrove Reserve" in data["plain_language_action"]
    env_intel = data["environmental_intelligence"]
    assert env_intel["status"] == "success"
    assert env_intel["canonical_record_id"].startswith("CR-")


def test_nagarpranali_contract_specification():
    """Verifies the contract endpoint exposes the interface specification."""
    contract = unified_auth_runtime.get_nagarpranali_contract()
    assert contract["contract_name"] == "VANA_NAGARPRANALI_INTEGRATION_CONTRACT"
    assert "GET /api/context/resolve" in contract["endpoints"]
    assert "POST /api/nagarpranali/enrich" in contract["endpoints"]
    assert "TC-Z03-F02" in contract["supported_zones"]


def test_backward_compatibility_pravah_observation_id():
    """Verifies that original Pravah observation_id context resolution is unbroken."""
    data = unified_auth_runtime.resolve_context(observation_id="OBS-TC-TEST-001")
    assert data["status"] == "VERIFIED"
    assert "environmental_factors" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
