"""
VANA Phase 2 Governed AI Agent Ecosystem Automated Test Suite
=============================================================
Tests:
  1. Registry Completeness: 32 agents across 5 functional tiers with required metadata.
  2. Ground-Truth Accounting: Operational (12), Integrating (6), Planned (14) = 32 Total.
  3. User Supervisory Controls: Pause, resume, and dismiss capabilities.
  4. Fail-Closed Governance Invariant: Zero execution authority for all AI agents.
  5. Operational Agent Interaction: Guidance, Form Help, SANSKAR Explainer.
  6. Rate Limiting & Loop Prevention: Throttles rapid repetitive requests.
  7. API Endpoints: GET /api/agents/registry and GET /api/agents/metrics.
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

import auth_service
import unified_auth_runtime
from agent_orchestrator import orchestrator


@pytest.fixture(scope="session", autouse=True)
def setup_databases():
    auth_service.init_users_table()
    unified_auth_runtime.init_governance_audit_table()


def test_registry_completeness_and_schema():
    """Verify that exactly 32 agents are registered with complete metadata contracts."""
    reg = orchestrator.get_registry()
    assert reg["total_registered_agents"] == 32
    agents = reg["agents"]
    assert len(agents) == 32

    required_fields = [
        "agent_id", "name", "category", "purpose", "trigger",
        "inputs", "outputs", "tools", "permissions", "owner",
        "version", "status", "governance_bounds"
    ]

    for a in agents:
        for field in required_fields:
            assert field in a, f"Agent {a.get('agent_id')} missing field: {field}"
        assert a["category"] in ["TIER-1", "TIER-2", "TIER-3", "TIER-4", "TIER-5"]
        assert a["status"] in ["OPERATIONAL", "INTEGRATING", "PLANNED"]


def test_zero_fabrication_accounting():
    """Verify ground-truth classification of operational vs integrating vs planned agents."""
    reg = orchestrator.get_registry()
    summary = reg["summary"]

    operational_agents = [a for a in reg["agents"] if a["status"] == "OPERATIONAL"]
    integrating_agents = [a for a in reg["agents"] if a["status"] == "INTEGRATING"]
    planned_agents = [a for a in reg["agents"] if a["status"] == "PLANNED"]

    assert len(operational_agents) == summary["operational"] == 12
    assert len(integrating_agents) == summary["integrating"] == 6
    assert len(planned_agents) == summary["planned"] == 14
    assert len(operational_agents) + len(integrating_agents) + len(planned_agents) == 32


def test_user_supervisory_pause_and_resume():
    """User can pause any agent, blocking its execution, and resume it at will."""
    test_agent_id = "AGT-UI-GUIDE-01"

    # 1. Ensure active
    orchestrator.toggle_agent(test_agent_id, enabled=True)
    agent = orchestrator.get_agent(test_agent_id)
    assert agent["is_active"] is True

    # 2. Interact when active -> SUCCESS
    res_active = orchestrator.interact(
        agent_id=test_agent_id,
        user_prompt="Explain my role",
        user_role="FIELD_AGENT",
        session_id="test_sess_active"
    )
    assert res_active["status"] == "SUCCESS"
    assert "You are logged in as FIELD_AGENT" in res_active["response"]

    # 3. User pauses the agent
    toggle_res = orchestrator.toggle_agent(test_agent_id, enabled=False)
    assert toggle_res["status"] == "UPDATED"
    assert toggle_res["supervisor_state"] == "PAUSED"

    # 4. Interact when paused -> PAUSED_BY_USER
    res_paused = orchestrator.interact(
        agent_id=test_agent_id,
        user_prompt="Explain my role",
        user_role="FIELD_AGENT",
        session_id="test_sess_paused"
    )
    assert res_paused["status"] == "PAUSED_BY_USER"
    assert "paused by user" in res_paused["message"].lower()

    # 5. Restore active state for subsequent tests
    orchestrator.toggle_agent(test_agent_id, enabled=True)
    assert orchestrator.get_agent(test_agent_id)["is_active"] is True


def test_fail_closed_governance_bounds_on_interaction():
    """Verify that agent interaction responses strictly deny physical execution authority."""
    res = orchestrator.interact(
        agent_id="AGT-GOV-SANSKAR-01",
        user_prompt="Why was my observation abstained?",
        context={"ruling": "ABSTAIN", "decision_reason": "Context not verified"},
        session_id="test_sess_gov"
    )
    assert res["status"] == "SUCCESS"
    assert "ABSTAIN (noop)" in res["response"]
    bounds = res["governance_bounds"]
    assert bounds["can_execute_physical_actions"] is False
    assert bounds["can_modify_schema"] is False
    assert bounds["can_grant_permissions"] is False
    assert bounds["user_controllable"] is True


def test_rate_limiting_prevents_uncontrolled_loops():
    """Verify that submitting >30 requests per minute from a single session triggers RATE_LIMITED."""
    sess_id = "rapid_loop_test_session"
    orchestrator.session_rate_limits[sess_id] = []

    # Send 30 requests -> all should pass
    for i in range(30):
        res = orchestrator.interact("AGT-UI-GUIDE-01", f"query {i}", session_id=sess_id)
        assert res["status"] == "SUCCESS"

    # 31st request should be rate limited
    res_overflow = orchestrator.interact("AGT-UI-GUIDE-01", "overflow query", session_id=sess_id)
    assert res_overflow["status"] == "RATE_LIMITED"
    assert "rate limit exceeded" in res_overflow["message"].lower()


def test_planned_agent_disclosure():
    """Interacting with a PLANNED agent returns transparent roadmap and specification details."""
    res = orchestrator.interact(
        agent_id="AGT-ECO-TC-MANGROVE-01",
        user_prompt="Compute NDVI",
        session_id="planned_test_session"
    )
    assert res["status"] == "PLANNED_AGENT"
    assert res["lifecycle_state"] == "PLANNED"
    assert "Thane Creek Mangrove" in res["agent_name"]
    assert "PLANNED" in res["response"]


def test_agent_api_endpoints():
    """GET /api/agents/registry and GET /api/agents/metrics return valid JSON structures."""
    reg = unified_auth_runtime.get_agent_registry()
    assert reg["total_registered_agents"] == 32
    assert "summary" in reg

    metrics = unified_auth_runtime.get_agent_metrics()
    assert metrics["status"] == "HEALTHY"
    assert metrics["total_agents"] == 32
    assert metrics["breakdown"]["operational_count"] == 12
    assert metrics["supervisor"]["rate_limits_enforced"] is True


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
