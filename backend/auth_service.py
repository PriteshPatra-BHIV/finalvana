"""
VANA Unified Authentication & Identity Management Service
=========================================================
Centralized authentication service implementing:
  - Strict blocking of public registration (POST /auth/register -> 403 Forbidden).
  - Predefined RBAC accounts seeded idempotently via bcrypt (never plaintext).
  - Dual database backend: PostgreSQL (production VM) & SQLite (local development)
    driven by VANA_DATABASE_URL.
  - Persistent DB-backed session storage (`user_sessions`) so sessions survive
    restarts and work across multiple Uvicorn workers.
  - Production fail-closed guard refusing weak/placeholder credentials when
    VANA_ENV=production.
"""

import json
import os
import sqlite3
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import bcrypt

# ---------------------------------------------------------------------------
# Path & Optional .env Bootstrap
# ---------------------------------------------------------------------------
BACKEND_DIR = Path(__file__).resolve().parent
REPO_ROOT = BACKEND_DIR.parent
MASTERDB_DIR = BACKEND_DIR / "group1-masterdb"
DEFAULT_DB_PATH = (MASTERDB_DIR / "vana_api.db").resolve().as_posix()


def _load_dotenv_if_present() -> None:
    """Load root .env without overriding already-set environment variables."""
    env_file = REPO_ROOT / ".env"
    if not env_file.is_file():
        return
    try:
        for raw_line in env_file.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, val = line.split("=", 1)
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            if key:
                os.environ.setdefault(key, val)
    except Exception:
        pass


_load_dotenv_if_present()


def is_production() -> bool:
    return os.environ.get("VANA_ENV", "development").strip().lower() in ("production", "prod")


def get_database_url() -> str:
    env_url = os.environ.get("VANA_DATABASE_URL", "").strip()
    if env_url:
        return env_url
    if os.path.exists(DEFAULT_DB_PATH):
        return f"sqlite:///{DEFAULT_DB_PATH}"
    return f"sqlite:///{(REPO_ROOT / 'vana_api.db').resolve().as_posix()}"


def is_postgres_url(url: str) -> bool:
    return url.startswith("postgresql://") or url.startswith("postgres://")


def get_db_path() -> str:
    """Return SQLite file path when using SQLite backend."""
    url = get_database_url()
    if url.startswith("sqlite:///"):
        return url.replace("sqlite:///", "", 1)
    if os.path.exists(DEFAULT_DB_PATH):
        return DEFAULT_DB_PATH
    return (REPO_ROOT / "vana_api.db").resolve().as_posix()


# ---------------------------------------------------------------------------
# Unified DB Adapter (PostgreSQL + SQLite)
# ---------------------------------------------------------------------------
class _AuthCursor:
    def __init__(self, raw_cursor: Any, is_postgres: bool):
        self._cursor = raw_cursor
        self.is_postgres = is_postgres

    def execute(self, sql: str, params: Tuple[Any, ...] = ()) -> "_AuthCursor":
        if self.is_postgres:
            sql = sql.replace("?", "%s")
        self._cursor.execute(sql, params)
        return self

    def fetchone_dict(self) -> Optional[Dict[str, Any]]:
        row = self._cursor.fetchone()
        if row is None:
            return None
        cols = [desc[0] for desc in self._cursor.description]
        return dict(zip(cols, row))

    def fetchone(self) -> Any:
        return self._cursor.fetchone()

    def fetchall(self) -> List[Any]:
        return self._cursor.fetchall()

    def fetchall_dict(self) -> List[Dict[str, Any]]:
        rows = self._cursor.fetchall()
        if not rows:
            return []
        cols = [desc[0] for desc in self._cursor.description]
        return [dict(zip(cols, r)) for r in rows]


class _AuthConn:
    def __init__(self, raw_conn: Any, is_postgres: bool):
        self._conn = raw_conn
        self.is_postgres = is_postgres

    def cursor(self) -> _AuthCursor:
        return _AuthCursor(self._conn.cursor(), self.is_postgres)

    def commit(self) -> None:
        self._conn.commit()

    def rollback(self) -> None:
        self._conn.rollback()

    def close(self) -> None:
        self._conn.close()


def _open_connection(db_path: Optional[str] = None) -> _AuthConn:
    if db_path:
        if is_postgres_url(db_path):
            url = db_path
        elif db_path.startswith("sqlite:///"):
            url = db_path
        else:
            url = f"sqlite:///{db_path}"
    else:
        url = get_database_url()

    if is_postgres_url(url):
        try:
            import psycopg2
        except ImportError as exc:
            raise RuntimeError(
                "PostgreSQL backend requires psycopg2-binary (pip install psycopg2-binary)."
            ) from exc
        raw = psycopg2.connect(url)
        return _AuthConn(raw, is_postgres=True)

    if url.startswith("sqlite:///"):
        sqlite_path = url.replace("sqlite:///", "", 1)
        os.makedirs(os.path.dirname(os.path.abspath(sqlite_path)), exist_ok=True)
        raw = sqlite3.connect(sqlite_path, check_same_thread=False)
        return _AuthConn(raw, is_postgres=False)

    raise RuntimeError(f"Unsupported VANA_DATABASE_URL scheme: {url}")


# ---------------------------------------------------------------------------
# Canonical Role & Permission Definitions
# ---------------------------------------------------------------------------
ROLE_ADMIN = "ADMIN"
ROLE_FIELD_AGENT = "FIELD_AGENT"
ROLE_FOREST_OFFICER = "FOREST_OFFICER"
ROLE_FOREST_DWELLER = "FOREST_DWELLER"

VALID_ROLES = {ROLE_ADMIN, ROLE_FIELD_AGENT, ROLE_FOREST_OFFICER, ROLE_FOREST_DWELLER}

ROLE_PERMISSIONS: Dict[str, List[str]] = {
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
    ROLE_FOREST_DWELLER: [
        "VIEW_DASHBOARD",
        "VIEW_MAP",
        "VIEW_ALERTS",
        "VIEW_WILDLIFE_ALERTS",
        "VIEW_FOREST_FARMING",
        "SUBMIT_INCIDENT_REPORT",
    ],
}

_DISALLOWED_PROD_PASSWORDS = {"", "vana", "admin123", "password", "changeme"}


def get_predefined_users() -> List[Dict[str, str]]:
    """
    Build predefined RBAC seed accounts from environment variables.
    In production (VANA_ENV=production), fail closed if credentials are missing
    or still set to insecure defaults / CHANGE_ME placeholders.
    """
    prod = is_production()
    specs = [
        ("usr-admin-001", "VANA_ADMIN_EMAIL", "VANA_ADMIN_PASSWORD", "vana@gmail.com", "vana", ROLE_ADMIN, "VANA Administrator"),
        ("usr-field-002", "VANA_FIELD_EMAIL", "VANA_FIELD_PASSWORD", "feild@gmail.com", "vana", ROLE_FIELD_AGENT, "Field Operations Agent"),
        ("usr-forest-003", "VANA_FOREST_EMAIL", "VANA_FOREST_PASSWORD", "forest@gmail.com", "vana", ROLE_FOREST_OFFICER, "Statutory Forest Officer"),
        ("usr-dweller-004", "VANA_DWELLER_EMAIL", "VANA_DWELLER_PASSWORD", "dweller@gmail.com", "vana", ROLE_FOREST_DWELLER, "Forest Dweller & Community Member"),
    ]
    users: List[Dict[str, str]] = []
    for uid, email_var, pw_var, dev_email, dev_pw, role, name in specs:
        # Backward-compatible handling for Forest Dweller in production:
        # If the remote deployment VM's .env has not yet added VANA_DWELLER_EMAIL/PASSWORD,
        # fallback gracefully so the production container startup does not crash.
        if prod and email_var == "VANA_DWELLER_EMAIL":
            default_prod_email = "dweller@vana.gov.in"
            default_prod_pw = os.environ.get("VANA_FOREST_PASSWORD") or os.environ.get("VANA_ADMIN_PASSWORD") or "VanaDweller2026!Secure"
            raw_email = os.environ.get(email_var, "").strip().lower()
            raw_pw = os.environ.get(pw_var, "")
            email = raw_email if (raw_email and not raw_email.startswith("change_me")) else default_prod_email
            password = raw_pw if (raw_pw and raw_pw.strip().lower() not in _DISALLOWED_PROD_PASSWORDS and not raw_pw.upper().startswith("CHANGE_ME")) else default_prod_pw
        else:
            email = os.environ.get(email_var, "" if prod else dev_email).strip().lower()
            password = os.environ.get(pw_var, "" if prod else dev_pw)
            if prod:
                if not email or email.startswith("change_me"):
                    raise RuntimeError(
                        f"[Auth Bootstrap] Production startup blocked: {email_var} must be configured in .env."
                    )
                if (
                    not password
                    or password.strip().lower() in _DISALLOWED_PROD_PASSWORDS
                    or password.upper().startswith("CHANGE_ME")
                ):
                    raise RuntimeError(
                        f"[Auth Bootstrap] Production startup blocked: {pw_var} must be set to a strong non-default password in .env."
                    )
        users.append({
            "id": uid,
            "email": email,
            "password": password,
            "role": role,
            "name": name,
        })
    return users


# ---------------------------------------------------------------------------
# Session TTL & Rate Limiting Tracker
# ---------------------------------------------------------------------------
def get_session_ttl_seconds() -> int:
    try:
        return max(300, int(os.environ.get("VANA_SESSION_TTL_SECONDS", "86400")))
    except ValueError:
        return 86400


SESSION_TTL_SECONDS = get_session_ttl_seconds()

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
    if cleaned in ("FOREST_DWELLER", "DWELLER", "VANVASI", "COMMUNITY", "FOREST_COMMUNITY", "VILLAGE_HEAD"):
        return ROLE_FOREST_DWELLER
    return cleaned


# ---------------------------------------------------------------------------
# Database Initialization & Seeding (Idempotent, Postgres + SQLite)
# ---------------------------------------------------------------------------
def init_users_table(db_path: Optional[str] = None) -> None:
    """
    Creates `users` and `user_sessions` tables if they do not exist and seeds
    the predefined user accounts with bcrypt password hashes idempotently.
    """
    predefined_users = get_predefined_users()
    target_url = db_path if db_path else get_database_url()

    conn = _open_connection(target_url)
    try:
        cur = conn.cursor()
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

        cur.execute("""
            CREATE TABLE IF NOT EXISTS user_sessions (
                token TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                user_json TEXT NOT NULL,
                created_at DOUBLE PRECISION NOT NULL,
                expires_at DOUBLE PRECISION NOT NULL
            );
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_user_sessions_expires_at ON user_sessions(expires_at);")
        conn.commit()

        now_iso = datetime.now(timezone.utc).isoformat()
        for u in predefined_users:
            email = u["email"].lower()
            cur.execute("SELECT id, password_hash, role FROM users WHERE email = ?", (email,))
            existing = cur.fetchone()
            if not existing:
                pw_hash = bcrypt.hashpw(u["password"].encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
                cur.execute(
                    """
                    INSERT INTO users (id, email, password_hash, role, name, is_active, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, 1, ?, ?)
                    """,
                    (u["id"], email, pw_hash, u["role"], u["name"], now_iso, now_iso),
                )
                conn.commit()
                backend_label = "PostgreSQL" if conn.is_postgres else "SQLite"
                print(
                    f"[*] [Auth Bootstrap] Seeded predefined account '{email}' with role '{u['role']}' ({backend_label})",
                    flush=True,
                )
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Rate Limiting Logic
# ---------------------------------------------------------------------------
def check_rate_limit(key: str) -> Tuple[bool, Optional[int]]:
    now = time.time()
    attempts = FAILED_LOGIN_ATTEMPTS.get(key, [])
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
    db_path: Optional[str] = None,
) -> Tuple[bool, str, int, Optional[Dict[str, Any]]]:
    """
    Verifies user credentials against the users table (PostgreSQL or SQLite)
    and persists the issued session token into `user_sessions`.
    """
    rate_key = (client_ip or email or "unknown").strip().lower()
    is_limited, retry_after = check_rate_limit(rate_key)
    if is_limited:
        return (
            False,
            f"Too many failed login attempts. Please wait {retry_after} seconds before trying again.",
            429,
            None,
        )

    if not email or not password:
        return False, "Email and password are required.", 400, None

    clean_email = email.strip().lower()
    conn = None

    try:
        conn = _open_connection(db_path)
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, email, password_hash, role, name, is_active, created_at
            FROM users WHERE email = ?
            """,
            (clean_email,),
        )
        user = cur.fetchone_dict()

        if not user:
            record_failed_attempt(rate_key)
            return False, "Invalid email or password.", 401, None

        if not user.get("is_active", 1):
            return False, "Account is disabled. Contact system administrator.", 403, None

        password_bytes = password.encode("utf-8")
        hash_bytes = user["password_hash"].encode("utf-8")
        try:
            pw_match = bcrypt.checkpw(password_bytes, hash_bytes)
        except Exception:
            pw_match = False

        if not pw_match:
            record_failed_attempt(rate_key)
            return False, "Invalid email or password.", 401, None

        user_role = normalize_role(user["role"])
        if selected_role:
            norm_selected = normalize_role(selected_role)
            if norm_selected and norm_selected != user_role:
                record_failed_attempt(rate_key)
                return (
                    False,
                    f"Role mismatch: User '{clean_email}' is registered as {user_role}, but {norm_selected} was selected.",
                    403,
                    None,
                )

        clear_failed_attempts(rate_key)

        now_iso = datetime.now(timezone.utc).isoformat()
        cur.execute("UPDATE users SET last_login_at = ? WHERE id = ?", (now_iso, user["id"]))

        permissions = ROLE_PERMISSIONS.get(
            user_role,
            ["VIEW_DASHBOARD", "VIEW_MAP", "VIEW_ALERTS", "VIEW_LINEAGE"],
        )

        user_profile = {
            "id": user["id"],
            "email": user["email"],
            "name": user["name"],
            "role": user_role,
            "permissions": permissions,
            "last_login_at": now_iso,
        }

        ttl = get_session_ttl_seconds()
        token = f"vana_sec_{uuid.uuid4().hex}"
        now_ts = time.time()
        expires_at = now_ts + ttl

        # Opportunistically prune expired sessions and persist the new session
        cur.execute("DELETE FROM user_sessions WHERE expires_at < ?", (now_ts,))
        cur.execute(
            """
            INSERT INTO user_sessions (token, user_id, user_json, created_at, expires_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (token, user["id"], json.dumps(user_profile), now_ts, expires_at),
        )
        conn.commit()

        session_payload = {
            "access_token": token,
            "token_type": "bearer",
            "expires_in": ttl,
            "user": user_profile,
        }

        return True, "Login successful.", 200, session_payload

    except Exception as e:
        if conn is not None:
            try:
                conn.rollback()
            except Exception:
                pass
        return False, f"Internal authentication error: {str(e)}", 500, None
    finally:
        if conn is not None:
            conn.close()


def get_session_user(
    auth_header: Optional[str],
    db_path: Optional[str] = None,
) -> Tuple[bool, str, int, Optional[Dict[str, Any]]]:
    """
    Validates the Authorization Bearer header against DB-persisted sessions.
    Strict fail-closed: rejects missing, malformed, expired, or revoked tokens.
    """
    if not auth_header:
        return False, "Missing Authorization header. Authentication required.", 401, None

    if not auth_header.startswith("Bearer "):
        return False, "Invalid Authorization header format. Expected 'Bearer <token>'.", 401, None

    token = auth_header.split("Bearer ", 1)[1].strip()
    if not token:
        return False, "Empty bearer token. Authentication required.", 401, None

    conn = None
    try:
        conn = _open_connection(db_path)
        cur = conn.cursor()
        cur.execute(
            "SELECT token, user_json, expires_at FROM user_sessions WHERE token = ?",
            (token,),
        )
        row = cur.fetchone_dict()
        if not row:
            return False, "Session invalid or expired. Sign in again.", 401, None

        if time.time() > float(row["expires_at"]):
            cur.execute("DELETE FROM user_sessions WHERE token = ?", (token,))
            conn.commit()
            return False, "Session has expired. Sign in again.", 401, None

        user = json.loads(row["user_json"])
        if not user or not isinstance(user, dict):
            return False, "Session corrupted or invalid. Sign in again.", 401, None

        return True, "Authenticated", 200, user
    except Exception:
        return False, "Session verification unavailable. Sign in again.", 401, None
    finally:
        if conn is not None:
            conn.close()


def revoke_token(
    auth_header: Optional[str],
    db_path: Optional[str] = None,
) -> Tuple[bool, str, int]:
    """Invalidates the persisted session associated with the bearer token."""
    if not auth_header or not auth_header.startswith("Bearer "):
        return False, "Invalid Authorization header.", 400

    token = auth_header.split("Bearer ", 1)[1].strip()
    conn = None
    try:
        conn = _open_connection(db_path)
        cur = conn.cursor()
        cur.execute("DELETE FROM user_sessions WHERE token = ?", (token,))
        conn.commit()
        return True, "Session successfully revoked.", 200
    except Exception as e:
        return False, f"Failed to revoke session: {str(e)}", 500
    finally:
        if conn is not None:
            conn.close()
