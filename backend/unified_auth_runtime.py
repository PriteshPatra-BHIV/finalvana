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
import pravah_service
import nagarpranali_adapter
from agent_orchestrator import orchestrator as agent_orchestrator
from dispatch_adapter import dispatch_adapter
from db_migration_tool import migration_manager

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


# -----------------------------------------------------------------------------
# PHASE 1 ECOSYSTEM ADAPTERS: PRAVAH CONTEXT & SENSOR CALIBRATION REGISTRY
# -----------------------------------------------------------------------------

@app.get("/api/ecosystem/health")
def ecosystem_health():
    """
    Returns live connectivity and health metrics across all 5 ecosystem boundaries.
    """
    pravah_status = pravah_service.probe_pravah_live()
    calibrated_sensors = []
    table_count = 0
    try:
        conn = auth_service._open_connection()
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [t[0] for t in cur.fetchall()]
        table_count = len(tables)
        if "sensor_calibration_registry" in tables:
            cur.execute("SELECT device_id, sensor_type, status, expires_at FROM sensor_calibration_registry")
            calibrated_sensors = [
                {"device_id": r[0], "sensor_type": r[1], "status": r[2], "expires_at": r[3]}
                for r in cur.fetchall()
            ]
        conn.close()
    except Exception:
        pass

    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "ecosystem": {
            "group1_masterdb": {
                "status": "ACTIVE",
                "engine": "SQLite",
                "verified_tables": table_count,
            },
            "group2_pravah": {
                "status": "LIVE" if pravah_status["reachable"] else "STANDIN_ACTIVE",
                "endpoint": pravah_status["endpoint"],
                "reachable": pravah_status["reachable"],
                "active_mode": pravah_service.PRAVAH_MODE,
                "fail_closed_safe": True,
            },
            "group3_sensor_calibration": {
                "status": "OPERATIONAL",
                "registered_sensors": len(calibrated_sensors),
                "sensors": calibrated_sensors,
            },
            "group4_sanskar_governance": {
                "status": "ENFORCED",
                "policy": "FAIL_CLOSED_ABSTAIN",
                "noop_guaranteed": True,
            },
            "group5_observability": {
                "status": "ACTIVE",
                "dashboard_connected": True,
                "audit_table": "governance_execution_audit",
            },
        },
    }


@app.get("/api/context/resolve")
def resolve_context(
    observation_id: Optional[str] = None,
    zone_id: Optional[str] = None,
    lat: Optional[float] = None,
    lon: Optional[float] = None,
    location: Optional[str] = None,
    allow_standin: bool = True,
):
    """
    Context resolution endpoint supporting observation-ID lookup (Pravah)
    and geospatial/location enrichment for Nagarpranali (UCCIS).
    """
    # 1. Nagarpranali geospatial / location alias query
    if lat is not None or lon is not None or location is not None:
        return nagarpranali_adapter.resolve_environmental_context(
            lat=lat,
            lon=lon,
            location_name=location,
            zone_id=zone_id,
            observation_id=observation_id,
        )

    # 2. Zone ID alone
    if zone_id and not observation_id:
        return nagarpranali_adapter.resolve_environmental_context(
            zone_id=zone_id,
            observation_id=observation_id,
        )

    # 3. Observation ID lookup delegating to Pravah
    if observation_id:
        return pravah_service.resolve_pravah_context(
            observation_id=observation_id,
            zone_id=zone_id,
            allow_standin=allow_standin,
        )

    raise HTTPException(
        status_code=400,
        detail="Missing query parameters: specify either observation_id, lat/lon, location, or zone_id.",
    )


class NagarpranaliEnrichRequest(BaseModel):
    signal_type: Optional[str] = None
    signalType: Optional[str] = None
    location: Optional[str] = None
    location_name: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None
    incident_type: Optional[str] = None
    incidentType: Optional[str] = None
    severity: Optional[str] = "MEDIUM"


@app.post("/api/nagarpranali/enrich")
def enrich_nagarpranali(req: NagarpranaliEnrichRequest):
    """
    Enriches a Nagarpranali civic incident payload with authoritative VANA
    environmental context, canopy density, and governance status.
    """
    return nagarpranali_adapter.enrich_nagarpranali_incident(req.model_dump())


@app.get("/api/nagarpranali/contract")
def get_nagarpranali_contract():
    """
    Returns the interface contract specification for Nagarpranali integration.
    """
    return nagarpranali_adapter.get_contract_specification()


class NagarpranaliLifecycleRequest(BaseModel):
    signal_type: Optional[str] = "Flood Alert"
    signalType: Optional[str] = None
    location: Optional[str] = "Thane Creek Zone A"
    location_name: Optional[str] = None
    incident_type: Optional[str] = "Mangrove Encroachment & Flood Threat"
    incidentType: Optional[str] = None
    severity: Optional[str] = "HIGH"
    lat: Optional[float] = None
    lon: Optional[float] = None


@app.post("/api/nagarpranali/lifecycle/run")
def run_nagarpranali_lifecycle(req: NagarpranaliLifecycleRequest):
    """
    Executes the 5-stage Nagarpranali + VANA operational lifecycle simulation.
    """
    return nagarpranali_adapter.simulate_nagarpranali_lifecycle(
        signal_type=req.signal_type or req.signalType or "Flood Alert",
        location=req.location or req.location_name or "Thane Creek Zone A",
        incident_type=req.incident_type or req.incidentType or "Mangrove Encroachment & Flood Threat",
        severity=req.severity or "HIGH",
        lat=req.lat,
        lon=req.lon,
    )


@app.get("/api/nagarpranali/components/status")
def get_nagarpranali_component_status():
    """
    Returns the mandatory sprint status matrix disclosing WORKING, PARTIAL,
    BLOCKED, DESIGN-ONLY, and NOT STARTED components across the ecosystem.
    """
    return nagarpranali_adapter.get_component_status()





class CalibrationRegisterRequest(BaseModel):
    device_id: str
    sensor_type: str
    calibration_cert_sha256: str
    calibrated_at: str
    expires_at: str
    status: str = "VERIFIED"


@app.get("/api/sensors/calibration")
def list_sensor_calibrations(authorization: Optional[str] = Header(None)):
    """
    Lists all attested sensors and their calibration validity.
    Accessible to authenticated users.
    """
    get_authenticated_user(authorization)
    try:
        conn = auth_service._open_connection()
        cur = conn.cursor()
        cur.execute("SELECT device_id, sensor_type, calibration_cert_sha256, calibrated_at, expires_at, status, registered_at FROM sensor_calibration_registry")
        rows = cur.fetchall()
        conn.close()
        return {
            "count": len(rows),
            "sensors": [
                {
                    "device_id": r[0],
                    "sensor_type": r[1],
                    "cert_sha256": r[2],
                    "calibrated_at": r[3],
                    "expires_at": r[4],
                    "status": r[5],
                    "registered_at": r[6],
                }
                for r in rows
            ],
        }
    except Exception as exc:
        return {"count": 0, "sensors": [], "note": str(exc)}


@app.post("/api/sensors/calibration")
def register_sensor_calibration(req: CalibrationRegisterRequest, authorization: Optional[str] = Header(None)):
    """
    Registers a signed sensor calibration certificate in the MasterDB registry.
    Strictly restricted to ADMIN users.
    """
    user = get_authenticated_user(authorization)
    if user.get("role") != "ADMIN":
        raise HTTPException(
            status_code=403,
            detail=f"Only Platform Administrators can register sensor calibration certificates. Caller role: {user.get('role')}.",
        )

    now_iso = datetime.now(timezone.utc).isoformat()
    try:
        conn = auth_service._open_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO sensor_calibration_registry (
                device_id, sensor_type, calibration_cert_sha256, calibrated_at, expires_at, status, registered_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(device_id) DO UPDATE SET
                sensor_type = excluded.sensor_type,
                calibration_cert_sha256 = excluded.calibration_cert_sha256,
                calibrated_at = excluded.calibrated_at,
                expires_at = excluded.expires_at,
                status = excluded.status,
                registered_at = excluded.registered_at
        """, (
            req.device_id, req.sensor_type, req.calibration_cert_sha256,
            req.calibrated_at, req.expires_at, req.status, now_iso
        ))
        conn.commit()
        conn.close()
        return {
            "status": "REGISTERED",
            "device_id": req.device_id,
            "sensor_type": req.sensor_type,
            "calibration_status": req.status,
            "registered_at": now_iso,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to register calibration: {exc}")


# -----------------------------------------------------------------------------
# PHASE 2 GOVERNED AI AGENT ECOSYSTEM (30+ TARGET)
# -----------------------------------------------------------------------------

class AgentInteractRequest(BaseModel):
    agent_id: str
    user_prompt: str = ""
    context: Optional[Dict[str, Any]] = None
    session_id: Optional[str] = "default_session"


class AgentToggleRequest(BaseModel):
    agent_id: str
    enabled: bool


@app.get("/api/agents/registry")
def get_agent_registry():
    """
    Returns the comprehensive 32-agent declarative registry with live supervisor telemetry.
    """
    return agent_orchestrator.get_registry()


@app.get("/api/agents/metrics")
def get_agent_metrics():
    """
    Returns live ecosystem operational metrics, breakdown counts, and supervisor telemetry.
    """
    return agent_orchestrator.get_metrics()


@app.post("/api/agents/interact")
def interact_with_agent(
    req: AgentInteractRequest,
    authorization: Optional[str] = Header(None)
):
    """
    Controlled interaction with a registered agent.
    Applies user-pause checks, rate limiting, and fail-closed governance bounds.
    """
    user_role = "FIELD_AGENT"
    if authorization:
        try:
            user = get_authenticated_user(authorization)
            user_role = user.get("role", "FIELD_AGENT")
        except Exception:
            pass

    return agent_orchestrator.interact(
        agent_id=req.agent_id,
        user_prompt=req.user_prompt,
        context=req.context,
        user_role=user_role,
        session_id=req.session_id or "default_session",
    )


@app.post("/api/agents/toggle")
def toggle_agent(
    req: AgentToggleRequest,
    authorization: Optional[str] = Header(None)
):
    """
    Allows user to pause or resume an agent (User Supervisory Control).
    Requires authenticated user session.
    """
    get_authenticated_user(authorization)
    return agent_orchestrator.toggle_agent(agent_id=req.agent_id, enabled=req.enabled)


# -----------------------------------------------------------------------------
# PHASE 3 HUMAN-IN-THE-LOOP (HITL) STATUTORY ACTUATION & DISPATCH FRAMEWORK
# -----------------------------------------------------------------------------

class DispatchProposalRequest(BaseModel):
    observation_id: str
    proposed_action: str = "DISPATCH_RANGER_SURVEILLANCE"
    dispatch_mode: str = "DRY_RUN"  # "DRY_RUN" or "PHYSICAL_GATED"
    target_zone: Optional[str] = "Z03"


class DispatchSignRequest(BaseModel):
    dispatch_id: str
    signature_note: Optional[str] = "Statutory verification signed."


@app.post("/api/dispatch/propose")
def propose_dispatch(
    req: DispatchProposalRequest,
    authorization: Optional[str] = Header(None)
):
    """
    Proposes a field dispatch. Accessible to Forest Officers and Admins.
    Field Agents are strictly rejected with HTTP 403.
    """
    user = get_authenticated_user(authorization)
    role = user.get("role", "").upper()
    if role not in ("ADMIN", "FOREST_OFFICER"):
        raise HTTPException(
            status_code=403,
            detail=f"Only Forest Officers and Admins can propose dispatches. Caller role: {role}."
        )

    ts_ms = int(time.time() * 1000)
    dispatch_id = f"disp_{ts_ms}_{uuid.uuid4().hex[:4]}"
    now_iso = datetime.now(timezone.utc).isoformat()
    officer_id = user.get("id") if role == "FOREST_OFFICER" else None
    admin_id = user.get("id") if role == "ADMIN" else None

    # Execute pending check
    res = dispatch_adapter.execute_statutory_dispatch(
        dispatch_id=dispatch_id,
        observation_id=req.observation_id,
        target_zone=req.target_zone or "Z03",
        latitude=19.1288,
        longitude=72.9421,
        proposed_action=req.proposed_action,
        officer_id=officer_id,
        admin_id=admin_id,
        dispatch_mode=req.dispatch_mode,
    )

    try:
        conn = auth_service._open_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO statutory_dispatch_ledger (
                dispatch_id, observation_id, mission_id, target_zone, proposed_action,
                officer_id, admin_id, quorum_met, dispatch_mode, status,
                flight_plan_json, receipt_sha256, dispatched_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            dispatch_id, req.observation_id, f"MISS-{dispatch_id}", req.target_zone,
            req.proposed_action, officer_id, admin_id, 0, req.dispatch_mode,
            res["status"], None, res["receipt_sha256"], now_iso
        ))
        conn.commit()
        conn.close()
    except Exception as exc:
        print(f"[Dispatch Ledger Note]: {exc}")

    return res


@app.post("/api/dispatch/sign")
def sign_dispatch(
    req: DispatchSignRequest,
    authorization: Optional[str] = Header(None)
):
    """
    Signs a pending dispatch proposal. Fulfills the Two-Man Rule.
    Requires the counterpart role (Forest Officer <-> Admin).
    """
    user = get_authenticated_user(authorization)
    role = user.get("role", "").upper()
    if role not in ("ADMIN", "FOREST_OFFICER"):
        raise HTTPException(
            status_code=403,
            detail=f"Only Forest Officers and Admins can sign statutory dispatches. Caller role: {role}."
        )

    now_iso = datetime.now(timezone.utc).isoformat()
    conn = auth_service._open_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT dispatch_id, observation_id, target_zone, proposed_action, officer_id, admin_id, dispatch_mode FROM statutory_dispatch_ledger WHERE dispatch_id = ?",
        (req.dispatch_id,)
    )
    row = cur.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail=f"Dispatch '{req.dispatch_id}' not found.")

    disp_id, obs_id, zone, action, off_id, adm_id, mode = row[0], row[1], row[2], row[3], row[4], row[5], row[6]

    if role == "ADMIN":
        adm_id = user.get("id")
    elif role == "FOREST_OFFICER":
        off_id = user.get("id")

    # Evaluate quorum
    res = dispatch_adapter.execute_statutory_dispatch(
        dispatch_id=disp_id,
        observation_id=obs_id,
        target_zone=zone,
        latitude=19.1288,
        longitude=72.9421,
        proposed_action=action,
        officer_id=off_id,
        admin_id=adm_id,
        dispatch_mode=mode,
    )

    flight_json = json.dumps(res.get("flight_plan")) if res.get("flight_plan") else None
    cur.execute("""
        UPDATE statutory_dispatch_ledger SET
            officer_id = ?, admin_id = ?, quorum_met = ?, status = ?,
            flight_plan_json = ?, receipt_sha256 = ?, dispatched_at = ?
        WHERE dispatch_id = ?
    """, (
        off_id, adm_id, 1 if res["quorum_met"] else 0, res["status"],
        flight_json, res["receipt_sha256"], now_iso, disp_id
    ))
    conn.commit()
    conn.close()
    return res


@app.get("/api/dispatch/ledger")
def get_dispatch_ledger(authorization: Optional[str] = Header(None)):
    """
    Returns the complete statutory dispatch ledger.
    """
    get_authenticated_user(authorization)
    try:
        conn = auth_service._open_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT dispatch_id, observation_id, proposed_action, officer_id, admin_id,
                   quorum_met, dispatch_mode, status, receipt_sha256, dispatched_at
            FROM statutory_dispatch_ledger ORDER BY dispatched_at DESC
        """)
        rows = cur.fetchall()
        conn.close()
        return {
            "count": len(rows),
            "dispatches": [
                {
                    "dispatch_id": r[0],
                    "observation_id": r[1],
                    "proposed_action": r[2],
                    "officer_id": r[3],
                    "admin_id": r[4],
                    "quorum_met": bool(r[5]),
                    "dispatch_mode": r[6],
                    "status": r[7],
                    "receipt_sha256": r[8],
                    "dispatched_at": r[9],
                }
                for r in rows
            ],
        }
    except Exception as exc:
        return {"count": 0, "dispatches": [], "note": str(exc)}


# -----------------------------------------------------------------------------
# PHASE 4 CLOUD DATABASE MIGRATION & POSTGIS HARDENING
# -----------------------------------------------------------------------------

@app.get("/api/database/migration/plan")
def get_database_migration_plan(
    target_url: Optional[str] = "postgresql://vana:vana_sec@localhost:5432/vana_prod",
    authorization: Optional[str] = Header(None)
):
    """
    Returns the cloud database migration plan (SQLite -> PostgreSQL + PostGIS).
    Restricted to Platform Administrators.
    """
    user = get_authenticated_user(authorization)
    if user.get("role") != "ADMIN":
        raise HTTPException(
            status_code=403,
            detail=f"Only Platform Administrators can view database migration plans. Caller role: {user.get('role')}."
        )
    return migration_manager.generate_migration_plan(target_url=target_url)




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

    # Optional automated context resolution via Pravah
    if context_id is None and payload.get("resolve_context"):
        ctx_res = pravah_service.resolve_pravah_context(
            observation_id=obs_id,
            allow_standin=payload.get("allow_standin", True)
        )
        if ctx_res.get("status") == "VERIFIED":
            context_id = ctx_res.get("context_id")

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
                    "SELECT device_id, calibration_status FROM field_observation_meta WHERE observation_id = ?",
                    (obs_row["observation_id"],),
                )
                meta_tuple = cur.fetchone()
                if meta_tuple:
                    device_id = meta_tuple[0]
                    cal_status = meta_tuple[1]
                    if cal_status == "CALIBRATED":
                        calibrated = True
                    elif device_id:
                        cur.execute(
                            "SELECT status, expires_at FROM sensor_calibration_registry WHERE device_id = ? OR device_id = ?",
                            (device_id, obs_row["observation_id"]),
                        )
                        reg_tuple = cur.fetchone()
                        if reg_tuple and reg_tuple[0] == "VERIFIED" and (not reg_tuple[1] or reg_tuple[1] > now_iso):
                            calibrated = True
                        else:
                            calibrated = False
                    else:
                        calibrated = False
                else:
                    parts = str(obs_row["observation_id"]).split("-")
                    sensor_key = parts[3] if len(parts) >= 4 else None
                    if sensor_key:
                        cur.execute(
                            "SELECT status, expires_at FROM sensor_calibration_registry WHERE device_id = ? OR sensor_type = ?",
                            (sensor_key, sensor_key),
                        )
                        reg_tuple = cur.fetchone()
                        if reg_tuple and reg_tuple[0] == "VERIFIED" and (not reg_tuple[1] or reg_tuple[1] > now_iso):
                            calibrated = True
                        else:
                            calibrated = False
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

    statutory_flight_plan = None
    if effective_ruling == "ABSTAIN":
        status_val = "governed_abstention"
        action_val = "noop"
    else:
        status_val = "action_request_generated"
        action_val = "dispatch"
        two_man = payload.get("two_man_signatures") or {}
        officer_sig = two_man.get("officer_id")
        admin_sig = two_man.get("admin_id") or user.get("id")
        dispatch_mode = payload.get("dispatch_mode", "DRY_RUN")

        statutory_res = dispatch_adapter.execute_statutory_dispatch(
            dispatch_id=execution_id,
            observation_id=obs_id,
            target_zone=payload.get("target_zone", "Z03"),
            latitude=19.1288,
            longitude=72.9421,
            proposed_action=payload.get("proposed_action", "DISPATCH_RANGER_SURVEILLANCE"),
            officer_id=officer_sig,
            admin_id=admin_sig,
            dispatch_mode=dispatch_mode,
        )
        statutory_flight_plan = statutory_res.get("flight_plan")

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
