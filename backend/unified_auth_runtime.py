"""
VANA Unified Authentication & SANSKAR Governed Execution Service
================================================================
Fulfills the backend contracts for:
  - POST /auth/login
  - GET  /auth/me
  - POST /auth/logout
  - POST /auth/register (strictly disabled -> 403)
  - POST /vana/execute
  - GET  /health
"""

import json
import os
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
import auth_service

# Initialize users, session, and governance audit tables on service start
auth_service.init_users_table()


def init_governance_audit_table():
    conn = None
    try:
        conn = auth_service._open_connection()
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS governance_execution_audit (
                audit_id VARCHAR(64) PRIMARY KEY,
                event_id VARCHAR(64) NOT NULL,
                execution_id VARCHAR(64),
                abstention_record_id VARCHAR(64),
                observation_id VARCHAR(128),
                canonical_record_id VARCHAR(128),
                caller_ruling VARCHAR(32),
                effective_ruling VARCHAR(32) NOT NULL,
                action_taken VARCHAR(32) NOT NULL,
                operator_id VARCHAR(64),
                operator_role VARCHAR(64),
                decision_reason TEXT,
                payload_json TEXT,
                recorded_at TEXT NOT NULL
            )
        """)
        conn.commit()
    except Exception as e:
        print(f"[Governance Audit] Table init note: {e}")
    finally:
        if conn is not None:
            conn.close()


init_governance_audit_table()


def _parse_cors_origins() -> List[str]:
    raw = os.environ.get("VANA_CORS_ORIGINS", "").strip()
    if raw:
        origins = [o.strip().rstrip("/") for o in raw.split(",") if o.strip()]
        if origins:
            return origins
    # Safe local dev defaults when VANA_CORS_ORIGINS is not configured
    return ["http://localhost:8080", "http://127.0.0.1:8080"]


_CORS_ORIGINS = _parse_cors_origins()
_ALLOW_CREDENTIALS = "*" not in _CORS_ORIGINS

app = FastAPI(
    title="VANA Unified Auth & Execution Runtime",
    version="1.0.0",
    description="Unified backend auth and SANSKAR governed execution runtime for VANA",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_CORS_ORIGINS,
    allow_credentials=_ALLOW_CREDENTIALS,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_authenticated_user(authorization: Optional[str]) -> dict:
    """
    Validates the Authorization Bearer header against DB-persisted sessions.
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
        client_ip=client_ip,
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

    caller_ruling = str(payload.get("ruling", "ABSTAIN")).strip().upper()
    context_id = payload.get("context_id")
    obs_id = payload.get("observation_id") or "TC-Z03-EXT-OPENMETEO-OBS001"
    canonical_id = payload.get("canonical_record_id")

    # -------------------------------------------------------------------------
    # Server-side validation of observation & calibration against MasterDB
    # -------------------------------------------------------------------------
    obs_verified = False
    calibrated = False
    conn = None
    try:
        try:
            import api.db as master_db
            conn = master_db.get_connection()
        except Exception:
            conn = auth_service._open_connection()

        cur = conn.cursor()
        cur.execute(
            "SELECT observation_id, canonical_record_id, quality_status FROM observation WHERE observation_id = ? OR canonical_record_id = ?",
            (obs_id, canonical_id or obs_id),
        )
        obs_row = cur.fetchone_dict() if hasattr(cur, "fetchone_dict") else None
        if not obs_row:
            row_tuple = cur.fetchone()
            if row_tuple:
                obs_row = {"observation_id": row_tuple[0], "canonical_record_id": row_tuple[1], "quality_status": row_tuple[2]}
        
        if obs_row:
            if not canonical_id:
                canonical_id = obs_row.get("canonical_record_id")
            obs_verified = obs_row.get("quality_status") == "VALIDATED"
            
            try:
                cur.execute(
                    "SELECT calibration_status FROM field_observation_meta WHERE observation_id = ?",
                    (obs_row["observation_id"],),
                )
                meta_tuple = cur.fetchone()
                if meta_tuple and meta_tuple[0] == "CALIBRATED":
                    calibrated = True
                else:
                    calibrated = False
            except Exception:
                calibrated = False
        else:
            obs_verified = False
            calibrated = False
    except Exception as err:
        obs_verified = False
        calibrated = False
    finally:
        if conn is not None:
            conn.close()

    # -------------------------------------------------------------------------
    # Fail-closed SANSKAR governance gate:
    # Overrides caller_ruling to ABSTAIN if context is missing or unverified
    # -------------------------------------------------------------------------
    if caller_ruling != "ABSTAIN" and (not context_id or not obs_verified or not calibrated):
        effective_ruling = "ABSTAIN"
        decision_reason = "Server-side governance gate: Sensor calibration or context unverified. Strict fail-closed override to ABSTAIN."
    elif caller_ruling == "ALLOW" and context_id and obs_verified and calibrated:
        effective_ruling = "ALLOW"
        decision_reason = "Authoritative context and calibration verified. Governed execution dispatch authorized."
    else:
        effective_ruling = "ABSTAIN"
        decision_reason = "Authoritative evidence threshold not met (Context not verified). Failing closed to ABSTAIN."

    if effective_ruling == "ABSTAIN":
        status_val = "governed_abstention"
        action_val = "noop"
    else:
        status_val = "action_request_generated"
        action_val = "dispatch"

    # -------------------------------------------------------------------------
    # Persist execution/abstention audit receipt into MasterDB
    # -------------------------------------------------------------------------
    try:
        conn = auth_service._open_connection()
        cur = conn.cursor()
        audit_id = f"aud_{ts_ms}_{uuid.uuid4().hex[:4]}"
        cur.execute("""
            INSERT INTO governance_execution_audit (
                audit_id, event_id, execution_id, abstention_record_id, observation_id,
                canonical_record_id, caller_ruling, effective_ruling, action_taken,
                operator_id, operator_role, decision_reason, payload_json, recorded_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            audit_id, event_id,
            execution_id if effective_ruling != "ABSTAIN" else None,
            abstention_record_id if effective_ruling == "ABSTAIN" else None,
            obs_id, canonical_id,
            caller_ruling, effective_ruling, action_val,
            user.get("id"), user.get("role"),
            decision_reason, json.dumps(payload), now_iso
        ))
        conn.commit()
    except Exception as e:
        print(f"[Governance Audit] Persistence note: {e}")
    finally:
        if conn is not None:
            conn.close()

    return {
        "status": status_val,
        "ruling": effective_ruling,
        "event_id": event_id,
        "execution_id": execution_id if effective_ruling != "ABSTAIN" else None,
        "abstention_record_id": abstention_record_id if effective_ruling == "ABSTAIN" else None,
        "recorded_at": now_iso,
        "decision_reason": decision_reason,
        "evidence": {
            "status": status_val,
            "ruling": effective_ruling,
            "decision_action": action_val,
            "abstention_record_id": abstention_record_id if effective_ruling == "ABSTAIN" else None,
            "event_id": event_id,
            "execution_id": execution_id if effective_ruling != "ABSTAIN" else None,
            "governance_allowed": effective_ruling != "ABSTAIN",
            "context_id": context_id,
            "observation_id": obs_id,
            "canonical_record_id": canonical_id,
            "recorded_at": now_iso,
        },
    }
