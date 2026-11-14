"""
VANA Unified Authentication & Identity Management Service
=========================================================
Centralized authentication service implementing:
  - Phase 1: Removal / strict blocking of public registration (POST /auth/register -> 403 Forbidden).
  - Phase 2: Predefined user accounts seeded into MasterDB SQLite via bcrypt (never plaintext).
  - Phase 5: Secure bcrypt password verification, role matching enforcement, session tokens, rate limiting.
  - Phase 6: Canonical SQLite `users` schema with migrations and idempotent seeding.
"""

import os
import time
import uuid
import sqlite3
import bcrypt
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any, Tuple

# ---------------------------------------------------------------------------
# Path & Database Configuration
# ---------------------------------------------------------------------------
BACKEND_DIR = Path(__file__).resolve().parent
MASTERDB_DIR = BACKEND_DIR / "group1-masterdb"
DEFAULT_DB_PATH = (MASTERDB_DIR / "vana_api.db").resolve().as_posix()

def get_db_path() -> str:
    env_url = os.environ.get("VANA_DATABASE_URL", "")
    if env_url.startswith("sqlite:///"):
        return env_url.replace("sqlite:///", "", 1)
    if os.path.exists(DEFAULT_DB_PATH):
        return DEFAULT_DB_PATH
    # Fallback to local vana_api.db
    return "vana_api.db"

# ---------------------------------------------------------------------------
# Canonical Role & Permission Definitions
# ---------------------------------------------------------------------------
ROLE_ADMIN = "ADMIN"
ROLE_FIELD_AGENT = "FIELD_AGENT"
ROLE_FOREST_OFFICER = "FOREST_OFFICER"

VALID_ROLES = {ROLE_ADMIN, ROLE_FIELD_AGENT, ROLE_FOREST_OFFICER}

ROLE_PERMISSIONS: Dict[str, list] = {
    ROLE_ADMIN: [
        "VIEW_DASHBOARD",
        "VIEW_MAP",
        "VIEW_ALERTS",
        "VIEW_LINEAGE",
        "VIEW_EVIDENCE",
        "RUN_REPLAY",
        "ACKNOWLEDGE_ALERT",
        "DISPATCH_EXECUTION",
        "RUN_HEALTH_CHECK",
        "VIEW_SERVICES",
        "EDIT_GEO_CONFIG",
        "VIEW_AUDIT_LOG",
        "VIEW_POLICIES",
        "MANAGE_USERS",
        "MANAGE_ROLES",
        "MANAGE_MAP_CONFIG",
        "MANAGE_ALERT_RULES",
        "MANAGE_GOVERNANCE_POLICIES",
        "MANAGE_SYSTEM_CONFIG",
        "EXECUTE_WORKFLOW",
    ],
    ROLE_FIELD_AGENT: [
        "VIEW_DASHBOARD",
        "VIEW_MAP",
        "VIEW_ALERTS",
        "VIEW_LINEAGE",
        "SUBMIT_OBSERVATION",
        "INTAKE_SENSOR_DATA",
        "REGISTER_SENSOR",
        "VIEW_TELEMETRY",
    ],
    ROLE_FOREST_OFFICER: [
        "VIEW_DASHBOARD",
        "VIEW_MAP",
        "VIEW_ALERTS",
        "VIEW_LINEAGE",
        "VIEW_EVIDENCE",
        "RUN_REPLAY",
        "VIEW_FOREST_COVER",
        "VIEW_STATUTORY_BENCHMARKS",
        "VIEW_GOVERNANCE_DECISIONS",
        "VIEW_AUDIT_LOG",
    ],
}

# Predefined Accounts (Configurable via environment variables)
PREDEFINED_USERS = [
    {
        "id": "usr-admin-001",
        "email": os.environ.get("VANA_ADMIN_EMAIL", "vana@gmail.com").strip().lower(),
        "password": os.environ.get("VANA_ADMIN_PASSWORD", "vana"),
        "role": ROLE_ADMIN,
        "name": "VANA Administrator",
    },
    {
        "id": "usr-field-002",
        "email": os.environ.get("VANA_FIELD_EMAIL", "feild@gmail.com").strip().lower(),
        "password": os.environ.get("VANA_FIELD_PASSWORD", "vana"),
        "role": ROLE_FIELD_AGENT,
        "name": "Field Operations Agent",
    },
    {
        "id": "usr-forest-003",
        "email": os.environ.get("VANA_FOREST_EMAIL", "forest@gmail.com").strip().lower(),
        "password": os.environ.get("VANA_FOREST_PASSWORD", "vana"),
        "role": ROLE_FOREST_OFFICER,
        "name": "Statutory Forest Officer",
    },
]

# ---------------------------------------------------------------------------
# In-Memory Session Store & Rate Limiting Tracker
# ---------------------------------------------------------------------------
SESSIONS: Dict[str, Dict[str, Any]] = {}
SESSION_TTL_SECONDS = 86400  # 24 hours

FAILED_LOGIN_ATTEMPTS: Dict[str, list] = {}
RATE_LIMIT_MAX_ATTEMPTS = 5
RATE_LIMIT_WINDOW_SECONDS = 300  # 5 minutes
LOCKOUT_DURATION_SECONDS = 60    # 1 minute lockout after limit reached


def normalize_role(role_str: Optional[str]) -> Optional[str]:
    if not role_str or not isinstance(role_str, str):
        return None
    cleaned = role_str.strip().upper().replace(" ", "_")
    if cleaned in ("ADMIN", "PLATFORM_ADMIN", "ADMINISTRATOR"):
        return ROLE_ADMIN
    if cleaned in ("FIELD_AGENT", "FIELD", "FEILD", "AGENT", "PARTICIPANT", "OPERATOR"):
        return ROLE_FIELD_AGENT
    if cleaned in ("FOREST_OFFICER", "FOREST", "OFFICER", "AUDITOR", "JUDGE", "STEWARD", "GOVERNANCE_STEWARD"):
        return ROLE_FOREST_OFFICER
    return cleaned


# ---------------------------------------------------------------------------
# Database Initialization & Seeding (Idempotent)
# ---------------------------------------------------------------------------
def init_users_table(db_path: Optional[str] = None) -> None:
    """
    Creates the canonical users table if it does not exist and seeds the three
    predefined user accounts with bcrypt password hashes.
    Ensures idempotency: does not overwrite existing records or passwords on server restarts.
    """
    targets = []
    if db_path:
        targets.append(db_path)
    else:
        configured_path = get_db_path()
        targets.append(configured_path)
        # Also ensure MasterDB directory and root db are synchronized if they exist
        if DEFAULT_DB_PATH not in targets:
            targets.append(DEFAULT_DB_PATH)
        root_db = (BACKEND_DIR.parent.parent / "vana_api.db").resolve().as_posix()
        if os.path.exists(root_db) and root_db not in targets:
            targets.append(root_db)

    for target in targets:
        try:
            os.makedirs(os.path.dirname(os.path.abspath(target)), exist_ok=True)
            conn = sqlite3.connect(target, check_same_thread=False)
            cur = conn.cursor()

            # Create users table with all required fields
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL,
                    name TEXT NOT NULL,
                    is_active INTEGER DEFAULT 1,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    last_login_at TEXT
                );
            """)
            cur.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);")
            conn.commit()

            # Seed predefined accounts idempotently
            now_iso = datetime.now(timezone.utc).isoformat()
            for u in PREDEFINED_USERS:
                email = u["email"].lower()
                cur.execute("SELECT id, password_hash, role FROM users WHERE email = ?", (email,))
                existing = cur.fetchone()
                if not existing:
                    pw_hash = bcrypt.hashpw(u["password"].encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
                    cur.execute("""
                        INSERT INTO users (id, email, password_hash, role, name, is_active, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, 1, ?, ?)
                    """, (u["id"], email, pw_hash, u["role"], u["name"], now_iso, now_iso))
                    conn.commit()
                    print(f"[*] [Auth Bootstrap] Seeded predefined account '{email}' with role '{u['role']}' in {target}", flush=True)

            conn.close()
        except Exception as e:
            print(f"[!] [Auth Bootstrap] Error initializing database at {target}: {e}", flush=True)


# ---------------------------------------------------------------------------
# Rate Limiting Logic
# ---------------------------------------------------------------------------
def check_rate_limit(key: str) -> Tuple[bool, Optional[int]]:
    """
    Checks whether key (IP or email) is currently rate-limited.
    Returns (is_limited, retry_after_seconds).
    """
    now = time.time()
    attempts = FAILED_LOGIN_ATTEMPTS.get(key, [])
    # Filter attempts within the window
    valid_attempts = [ts for ts in attempts if now - ts < RATE_LIMIT_WINDOW_SECONDS]
    FAILED_LOGIN_ATTEMPTS[key] = valid_attempts

    if len(valid_attempts) >= RATE_LIMIT_MAX_ATTEMPTS:
        latest = max(valid_attempts)
        elapsed_since_last = now - latest
        if elapsed_since_last < LOCKOUT_DURATION_SECONDS:
            retry_after = int(LOCKOUT_DURATION_SECONDS - elapsed_since_last) + 1
            return True, retry_after

    return False, None


def record_failed_attempt(key: str) -> None:
    now = time.time()
    if key not in FAILED_LOGIN_ATTEMPTS:
        FAILED_LOGIN_ATTEMPTS[key] = []
    FAILED_LOGIN_ATTEMPTS[key].append(now)


def clear_failed_attempts(key: str) -> None:
    FAILED_LOGIN_ATTEMPTS.pop(key, None)


# ---------------------------------------------------------------------------
# Authentication & Verification Core
# ---------------------------------------------------------------------------
def authenticate_user(
    email: str,
    password: str,
    selected_role: Optional[str] = None,
    client_ip: Optional[str] = None,
    db_path: Optional[str] = None
) -> Tuple[bool, str, int, Optional[Dict[str, Any]]]:
    """
    Verifies user credentials against SQLite users table.
    Enforces:
      - Rate limiting against brute-force attacks.
      - Password verification using bcrypt.
      - Account active status.
      - Strict Role Match: Rejects mismatch if selected_role doesn't match database role.
      - Session creation with 24h validity.

    Returns: (success: bool, message: str, status_code: int, session_data: Optional[dict])
    """
    rate_key = (client_ip or email or "unknown").strip().lower()
    is_limited, retry_after = check_rate_limit(rate_key)
    if is_limited:
        return (
            False,
            f"Too many failed login attempts. Please wait {retry_after} seconds before trying again.",
            429,
            None
        )

    if not email or not password:
        return False, "Email and password are required.", 400, None

    clean_email = email.strip().lower()
    active_db = db_path or get_db_path()

    try:
        conn = sqlite3.connect(active_db, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("""
            SELECT id, email, password_hash, role, name, is_active, created_at
            FROM users WHERE email = ?
        """, (clean_email,))
        row = cur.fetchone()

        if not row:
            record_failed_attempt(rate_key)
            conn.close()
            return False, "Invalid email or password.", 401, None

        user = dict(row)

        if not user.get("is_active", 1):
            conn.close()
            return False, "Account is disabled. Contact system administrator.", 403, None

        # Verify password using bcrypt
        password_bytes = password.encode("utf-8")
        hash_bytes = user["password_hash"].encode("utf-8")
        try:
            pw_match = bcrypt.checkpw(password_bytes, hash_bytes)
        except Exception:
            pw_match = False

        if not pw_match:
            record_failed_attempt(rate_key)
            conn.close()
            return False, "Invalid email or password.", 401, None

        # Enforce Role Matching Gate
        user_role = normalize_role(user["role"])
        if selected_role:
            norm_selected = normalize_role(selected_role)
            if norm_selected and norm_selected != user_role:
                record_failed_attempt(rate_key)
                conn.close()
                return (
                    False,
                    f"Role mismatch: User '{clean_email}' is registered as {user_role}, but {norm_selected} was selected.",
                    403,
                    None
                )

        # Login successful — reset failed attempts
        clear_failed_attempts(rate_key)

        now_iso = datetime.now(timezone.utc).isoformat()
        cur.execute("UPDATE users SET last_login_at = ? WHERE id = ?", (now_iso, user["id"]))
        conn.commit()
        conn.close()

        # Build user profile with permissions
        permissions = ROLE_PERMISSIONS.get(user_role, [
            "VIEW_DASHBOARD", "VIEW_MAP", "VIEW_ALERTS", "VIEW_LINEAGE"
        ])

        user_profile = {
            "id": user["id"],
            "email": user["email"],
            "name": user["name"],
            "role": user_role,
            "permissions": permissions,
            "last_login_at": now_iso,
        }

        # Issue secure bearer token & register session
        token = f"vana_sec_{uuid.uuid4().hex}"
        now_ts = time.time()
        expires_at = now_ts + SESSION_TTL_SECONDS

        SESSIONS[token] = {
            "token": token,
            "user": user_profile,
            "created_at": now_ts,
            "expires_at": expires_at,
        }

        session_payload = {
            "access_token": token,
            "token_type": "bearer",
            "expires_in": SESSION_TTL_SECONDS,
            "user": user_profile,
        }

        return True, "Login successful.", 200, session_payload

    except Exception as e:
        return False, f"Internal authentication error: {str(e)}", 500, None


def get_session_user(auth_header: Optional[str]) -> Tuple[bool, str, int, Optional[Dict[str, Any]]]:
    """
    Validates the Authorization Bearer header against server-managed sessions.
    Strict fail-closed: rejects missing, malformed, expired, or revoked tokens.
    """
    if not auth_header:
        return False, "Missing Authorization header. Authentication required.", 401, None

    if not auth_header.startswith("Bearer "):
        return False, "Invalid Authorization header format. Expected 'Bearer <token>'.", 401, None

    token = auth_header.split("Bearer ", 1)[1].strip()
    if not token:
        return False, "Empty bearer token. Authentication required.", 401, None

    session = SESSIONS.get(token)
    if not session:
        return False, "Session invalid or expired. Sign in again.", 401, None

    if time.time() > session.get("expires_at", 0):
        SESSIONS.pop(token, None)
        return False, "Session has expired. Sign in again.", 401, None

    user = session.get("user")
    if not user or not isinstance(user, dict):
        return False, "Session corrupted or invalid. Sign in again.", 401, None

    return True, "Authenticated", 200, user


def revoke_token(auth_header: Optional[str]) -> Tuple[bool, str, int]:
    """
    Invalidates session associated with the bearer token.
    """
    if not auth_header or not auth_header.startswith("Bearer "):
        return False, "Invalid Authorization header.", 400

    token = auth_header.split("Bearer ", 1)[1].strip()
    if token in SESSIONS:
        SESSIONS.pop(token, None)
        return True, "Session successfully revoked.", 200
    return True, "Session already inactive or revoked.", 200

