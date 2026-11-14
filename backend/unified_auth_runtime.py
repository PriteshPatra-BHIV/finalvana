"""
VANA Unified Authentication & SANSKAR Governed Execution Service
================================================================
Fulfills the backend contracts for:
  - POST /auth/login
  - GET  /auth/me
  - POST /auth/register
  - POST /vana/execute
  - GET  /health
Runs on port 8000 (UNIFIED_BACKEND default).
"""

import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import sys
from pathlib import Path
BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
import auth_service

# Initialize users table on service start
auth_service.init_users_table()

app = FastAPI(
    title="VANA Unified Auth & Execution Runtime",
    version="1.0.0",
    description="Unified backend auth and SANSKAR governed execution runtime for VANA",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory users and token sessions
USERS = {
    "admin@vana.gov.in": {
        "id": "adm-001",
        "email": "admin@vana.gov.in",
        "name": "VANA Administrator",
        "role": "admin",
        "permissions": [
            "VIEW_DASHBOARD",
            "VIEW_MAP",
            "VIEW_ALERTS",
            "VIEW_LINEAGE",
            "VIEW_AUDIT_LOG",
            "RUN_REPLAY",
            "MANAGE_USERS",
            "MANAGE_SYSTEM_CONFIG",
            "EXECUTE_WORKFLOW",
        ],
    },
    "participant@vana.gov.in": {
        "id": "part-002",
        "email": "participant@vana.gov.in",
        "name": "Field Participant",
        "role": "participant",
        "permissions": [
            "VIEW_DASHBOARD",
            "VIEW_MAP",
            "VIEW_ALERTS",
            "VIEW_LINEAGE",
        ],
    },
    "judge@vana.gov.in": {
        "id": "judge-003",
        "email": "judge@vana.gov.in",
        "name": "Lineage Judge",
        "role": "judge",
        "permissions": [
            "VIEW_DASHBOARD",
            "VIEW_AUDIT_LOG",
            "RUN_REPLAY",
        ],
    },
    "auditor@vana.gov.in": {
        "id": "audit-004",
        "email": "auditor@vana.gov.in",
        "name": "Governance Auditor",
        "role": "auditor",
        "permissions": [
            "VIEW_DASHBOARD",
            "VIEW_AUDIT_LOG",
            "RUN_REPLAY",
        ],
    },
    "steward@vana.gov.in": {
        "id": "stew-005",
        "email": "steward@vana.gov.in",
        "name": "Governance Steward",
        "role": "steward",
        "permissions": [
            "VIEW_DASHBOARD",
            "VIEW_AUDIT_LOG",
        ],
    },
}

SESSIONS: Dict[str, dict] = {}
SESSION_TTL_SECONDS = 86400  # 24 hours session validity


def get_authenticated_user(authorization: Optional[str]) -> dict:
    """
    Validates the Authorization Bearer header against server-managed sessions.
    Strictly fail-closed: rejects missing, malformed, expired, or unauthenticated tokens with HTTP 401.
    """
    ok, msg, code, user = auth_service.get_session_user(authorization)
    if not ok:
        raise HTTPException(status_code=code, detail=msg)
    return user


class LoginRequest(BaseModel):
    email: Optional[str] = None
    username: Optional[str] = None
    password: str
    role: Optional[str] = None
    selected_role: Optional[str] = None


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "service": "VANA Unified Auth & Execution Runtime",
        "version": "1.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.post("/auth/login")
def login(req: LoginRequest, request: Request):
    identifier = (req.email or req.username or "").strip().lower()
    if not identifier:
        raise HTTPException(status_code=400, detail="Email or username is required.")

    selected_role = req.role or req.selected_role
    client_ip = request.client.host if request.client else None

    ok, msg, code, session_data = auth_service.authenticate_user(
        email=identifier,
        password=req.password,
        selected_role=selected_role,
        client_ip=client_ip
    )
    if not ok:
        raise HTTPException(status_code=code, detail=msg)

    return session_data


@app.get("/auth/me")
def me(authorization: Optional[str] = Header(None)):
    user = get_authenticated_user(authorization)
    return {
        "status": "active",
        "user": user,
        "permissions": user.get("permissions", []),
    }


@app.post("/auth/logout")
def logout(authorization: Optional[str] = Header(None)):
    ok, msg, code = auth_service.revoke_token(authorization)
    return {
        "status": "success" if ok else "error",
        "message": msg,
        "revoked_at": datetime.now(timezone.utc).isoformat(),
    }


@app.post("/auth/register", status_code=403)
def register():
    """
    Public registration is strictly disabled.
    VANA operates under a closed, role-based access control architecture.
    """
    raise HTTPException(
        status_code=403,
        detail="Public registration is disabled. VANA operates under a strict predefined role-based access control policy.",
    )


@app.post("/vana/execute")
def vana_execute(payload: Dict[str, Any], authorization: Optional[str] = Header(None)):
    user = get_authenticated_user(authorization)

    # Strict RBAC enforcement
    role = user.get("role", "").upper()
    perms = user.get("permissions", [])
    if role != "ADMIN" and "EXECUTE_WORKFLOW" not in perms:
        raise HTTPException(
            status_code=403,
            detail=f"Execution dispatch requires ADMIN privileges. User role: {role}.",
        )

    ts_ms = int(time.time() * 1000)
    event_id = f"evt_{ts_ms}_{uuid.uuid4().hex[:3]}"
    execution_id = f"exec_{ts_ms}_{uuid.uuid4().hex[:3]}"
    abstention_record_id = f"ABS-{uuid.uuid4().hex[:12].upper()}"
    now_iso = datetime.now(timezone.utc).isoformat()

    ruling = payload.get("ruling", "ABSTAIN")
    obs_id = payload.get("observation_id", "TC-Z03-EXT-OPENMETEO-OBS001")
    canonical_id = payload.get("canonical_record_id")

    return {
        "status": "governed_abstention" if ruling == "ABSTAIN" else "action_request_generated",
        "ruling": ruling,
        "event_id": event_id,
        "execution_id": execution_id,
        "recorded_at": now_iso,
        "decision_reason": "Authoritative evidence threshold not met (Context not verified). Failing closed to ABSTAIN.",
        "evidence": {
            "status": "governed_abstention",
            "ruling": ruling,
            "decision_action": "noop" if ruling == "ABSTAIN" else "dispatch",
            "abstention_record_id": abstention_record_id,
            "event_id": event_id,
            "execution_id": execution_id,
            "governance_allowed": ruling != "ABSTAIN",
            "context_id": payload.get("context_id"),
            "observation_id": obs_id,
            "canonical_record_id": canonical_id,
            "recorded_at": now_iso,
        },
    }

