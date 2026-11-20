"""
VANA Governed AI Agent Orchestrator & Supervisor
================================================
Implements Section 4 of the VANA + BIQOS Sprint Task Assignment:
  - Declarative Agent Registry (32 agents across 5 functional tiers).
  - Strict user-in-the-loop supervisor controls: Identifiable, dismissible, pausable, disableable.
  - Rate limiting, session isolation, and loop prevention.
  - Strict governance boundaries: Agents may guide, explain, and validate;
    they CANNOT grant permissions, alter MasterDB schemas, or trigger physical dispatches.
  - Ground-truth reporting: Separates operational, integrating, and planned agents.
"""

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

BACKEND_DIR = Path(__file__).resolve().parent
REGISTRY_PATH = BACKEND_DIR / "agent_registry.json"


class AgentSupervisor:
    """
    Supervises, rate-limits, and isolates the 30+ agent ecosystem.
    Enforces that AI agents never bypass governance or trigger autonomous execution.
    """

    def __init__(self, registry_file: Path = REGISTRY_PATH):
        self.registry_file = registry_file
        self.paused_agents: set[str] = set()
        self.invocation_counts: dict[str, int] = {}
        self.session_rate_limits: dict[str, list[float]] = {}
        self.max_requests_per_minute = 30
        self._load_registry()

    def _load_registry(self) -> None:
        if self.registry_file.is_file():
            with open(self.registry_file, "r", encoding="utf-8") as f:
                self.registry_data = json.load(f)
        else:
            self.registry_data = {
                "ecosystem": "VANA Forest Intelligence",
                "version": "2.0.0",
                "total_registered_agents": 0,
                "summary": {"operational": 0, "integrating": 0, "planned": 0, "total": 0},
                "tiers": [],
                "agents": [],
            }
        self.agents_map = {a["agent_id"]: a for a in self.registry_data.get("agents", [])}

    def get_registry(self) -> Dict[str, Any]:
        """Returns the full declarative registry with live supervisor states."""
        reg = dict(self.registry_data)
        # Augment agents with live supervisor state
        augmented_agents = []
        for a in reg.get("agents", []):
            agent_copy = dict(a)
            agent_copy["is_active"] = a["agent_id"] not in self.paused_agents
            agent_copy["total_invocations"] = self.invocation_counts.get(a["agent_id"], 0)
            augmented_agents.append(agent_copy)
        reg["agents"] = augmented_agents
        return reg

    def get_agent(self, agent_id: str) -> Optional[Dict[str, Any]]:
        a = self.agents_map.get(agent_id)
        if not a:
            return None
        res = dict(a)
        res["is_active"] = agent_id not in self.paused_agents
        res["total_invocations"] = self.invocation_counts.get(agent_id, 0)
        return res

    def list_agents(
        self, category: Optional[str] = None, status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        agents = []
        for a in self.registry_data.get("agents", []):
            if category and a.get("category") != category:
                continue
            if status and a.get("status") != status.upper():
                continue
            item = dict(a)
            item["is_active"] = a["agent_id"] not in self.paused_agents
            item["total_invocations"] = self.invocation_counts.get(a["agent_id"], 0)
            agents.append(item)
        return agents

    def toggle_agent(self, agent_id: str, enabled: bool) -> Dict[str, Any]:
        """User supervisory control: allows pausing or resuming an agent."""
        if agent_id not in self.agents_map:
            return {"status": "ERROR", "message": f"Agent '{agent_id}' not found."}

        if enabled:
            self.paused_agents.discard(agent_id)
            state = "ACTIVE"
        else:
            self.paused_agents.add(agent_id)
            state = "PAUSED"

        return {
            "status": "UPDATED",
            "agent_id": agent_id,
            "supervisor_state": state,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def _check_rate_limit(self, session_key: str) -> bool:
        """Rate limiting & loop prevention: max 30 requests per minute per session."""
        now = time.time()
        timestamps = self.session_rate_limits.get(session_key, [])
        # Keep timestamps from the last 60 seconds
        recent = [t for t in timestamps if now - t < 60.0]
        if len(recent) >= self.max_requests_per_minute:
            return False
        recent.append(now)
        self.session_rate_limits[session_key] = recent
        return True

    def interact(
        self,
        agent_id: str,
        user_prompt: str,
        context: Optional[Dict[str, Any]] = None,
        user_role: str = "FIELD_AGENT",
        session_id: str = "default_session",
    ) -> Dict[str, Any]:
        """
        Executes a controlled, governed agent interaction.
        Strictly enforces:
          - Rejection if paused by user.
          - Rate limits & loop prevention.
          - Zero autonomous dispatch permissions.
        """
        agent = self.get_agent(agent_id)
        if not agent:
            return {
                "status": "NOT_FOUND",
                "message": f"Agent '{agent_id}' is not registered in the ecosystem.",
                "governance_allowed": False,
            }

        # 1. User Supervisory Pause Check
        if not agent.get("is_active"):
            return {
                "status": "PAUSED_BY_USER",
                "agent_id": agent_id,
                "message": f"Agent '{agent['name']}' ({agent_id}) is currently paused by user. Enable it in the AI Agent Center to resume assistance.",
                "governance_allowed": False,
            }

        # 2. Rate Limiting & Loop Prevention
        if not self._check_rate_limit(session_id):
            return {
                "status": "RATE_LIMITED",
                "agent_id": agent_id,
                "message": "Interaction rate limit exceeded (maximum 30 requests per minute). Throttling to prevent agent loops.",
                "governance_allowed": False,
            }

        # Track invocation
        self.invocation_counts[agent_id] = self.invocation_counts.get(agent_id, 0) + 1
        now_iso = datetime.now(timezone.utc).isoformat()
        clean_prompt = (user_prompt or "").strip().lower()

        # 3. Grounded Deterministic Responses for Operational Agents
        if agent["status"] == "OPERATIONAL":
            if agent_id == "AGT-UI-GUIDE-01":
                response_text = self._handle_general_guide(clean_prompt, user_role)
            elif agent_id == "AGT-UI-ONBOARD-02":
                response_text = self._handle_onboarding_guide(user_role)
            elif agent_id == "AGT-UI-FORM-03":
                response_text = self._handle_form_guide(clean_prompt, context)
            elif agent_id == "AGT-UI-RECOVER-04":
                response_text = "Offline queue active. Stored observations will auto-sync when network connectivity returns."
            elif agent_id == "AGT-GOV-SANSKAR-01":
                response_text = self._handle_sanskar_explainer(context)
            elif agent_id == "AGT-GOV-FAILCLOSED-02":
                response_text = "Fail-closed watchdog active: uncalibrated hardware or missing context strictly evaluates to ABSTAIN (noop)."
            else:
                response_text = f"Agent {agent['name']} ({agent_id}) operational. Analyzing task telemetry with read-only permissions."

            return {
                "status": "SUCCESS",
                "agent_id": agent_id,
                "agent_name": agent["name"],
                "category": agent["category"],
                "response": response_text,
                "governance_bounds": {
                    "can_execute_physical_actions": False,
                    "can_modify_schema": False,
                    "can_grant_permissions": False,
                    "user_controllable": True,
                },
                "timestamp": now_iso,
            }

        # 4. Roadmap Disclosures for Integrating & Planned Agents
        return {
            "status": "PLANNED_AGENT",
            "agent_id": agent_id,
            "agent_name": agent["name"],
            "category": agent["category"],
            "lifecycle_state": agent["status"],
            "response": (
                f"Agent '{agent['name']}' ({agent_id}) is in the {agent['status']} lifecycle phase. "
                f"Purpose: {agent['purpose']}. Planned runtime: {agent.get('runtime', 'Worker container')}."
            ),
            "governance_bounds": {
                "can_execute_physical_actions": False,
                "can_modify_schema": False,
                "can_grant_permissions": False,
                "user_controllable": True,
            },
            "timestamp": now_iso,
        }

    def _handle_general_guide(self, prompt: str, role: str) -> str:
        if "role" in prompt or "who" in prompt:
            return f"You are logged in as {role}. Platform Admins govern dispatches, Forest Officers review telemetry, and Field Agents submit observations."
        if "calibration" in prompt or "sensor" in prompt:
            return "Sensor calibration requires signed SHA-256 certificates registered in MasterDB. Uncalibrated hardware strictly triggers ABSTAIN (noop)."
        if "pravah" in prompt or "context" in prompt:
            return "Pravah (Group 2) supplies catchment and environmental context. If unreachable, VANA uses deterministic local stand-in or safely fails closed."
        return "VANA Guidance Assistant: Available to explain forest zones (Thane Creek, Maval, Samachar), observation intake, and SANSKAR governance."

    def _handle_onboarding_guide(self, role: str) -> str:
        if role == "ADMIN":
            return "Welcome, Administrator. Your primary dashboard displays live surveillance zones, MasterDB records, ecosystem health, and SANSKAR governance controls."
        elif role == "FOREST_OFFICER":
            return "Welcome, Forest Officer. Use the Observation Review Queue to inspect incoming field telemetry, verify calibration certificates, and review evidence."
        return "Welcome, Field Agent. Use the New Observation intake form to submit field data. If working in remote areas, data is saved offline and synced when connected."

    def _handle_form_guide(self, prompt: str, context: Optional[Dict[str, Any]]) -> str:
        return "Observation Form Guide: Ensure coordinates fall within Maharashtra forest divisions. Natural key format: {SURVEY}-{ZONE}-{FLIGHT}-{SENSOR}-OBS{SEQ}."

    def _handle_sanskar_explainer(self, context: Optional[Dict[str, Any]]) -> str:
        ctx = context or {}
        ruling = ctx.get("ruling", "ABSTAIN")
        reason = ctx.get("decision_reason", "Authoritative evidence threshold not met.")
        if ruling == "ABSTAIN":
            return f"SANSKAR Rationale: The evaluation resulted in ABSTAIN (noop) because: {reason}. Statutory rules prohibit automated dispatch without complete proof."
        return f"SANSKAR Rationale: Evaluated as ALLOW because authoritative context and verified sensor calibration were confirmed by an authorized Administrator."

    def get_metrics(self) -> Dict[str, Any]:
        """Returns live ecosystem operational metrics and supervisor telemetry."""
        reg_summary = self.registry_data.get("summary", {})
        return {
            "status": "HEALTHY",
            "total_agents": self.registry_data.get("total_registered_agents", 0),
            "breakdown": {
                "operational_count": reg_summary.get("operational", 0),
                "integrating_count": reg_summary.get("integrating", 0),
                "planned_count": reg_summary.get("planned", 0),
            },
            "supervisor": {
                "paused_agents_count": len(self.paused_agents),
                "paused_agents": sorted(list(self.paused_agents)),
                "active_agents_count": len(self.agents_map) - len(self.paused_agents),
                "total_invocations": sum(self.invocation_counts.values()),
                "rate_limits_enforced": True,
                "max_requests_per_minute": self.max_requests_per_minute,
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


# Global Singleton Orchestrator Instance
orchestrator = AgentSupervisor()
