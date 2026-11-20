"""
Authentication & Authorization Dependency for VANA MasterDB API
===============================================================
Enforces Bearer token verification against user_sessions in MasterDB.
Fail-closed doctrine: Reject unauthenticated (401) and unauthorized (403) requests.
"""

import os
import sys
import time
from typing import Optional, Set
from fastapi import Header, HTTPException
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[2]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import auth_service


def get_current_user(authorization: Optional[str] = Header(None)) -> dict:
    """
    Validates Bearer token from the Authorization header against DB-persisted sessions.
    Rejects missing or invalid tokens with HTTP 401.
    Rejects expired sessions with HTTP 401.
    """
    if not authorization:
        raise HTTPException(
            status_code=401,
            detail="Authentication required. Provide a valid Bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = auth_service.get_session_user(authorization)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired session token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


def require_roles(allowed_roles: Set[str]):
    """
    Returns a dependency enforcing that the authenticated user possesses one of the allowed_roles.
    ADMIN possesses superuser override for operational endpoints.
    Rejects unauthorized roles with HTTP 403.
    """
    def _role_checker(authorization: Optional[str] = Header(None)) -> dict:
        user = get_current_user(authorization)
        role = user.get("role", "").upper()
        
        # Admin is always permitted if ADMIN is in allowed_roles, or as administrative override
        if role == "ADMIN" or role in allowed_roles:
            return user

        allowed_str = ", ".join(sorted(allowed_roles))
        raise HTTPException(
            status_code=403,
            detail=f"Operation forbidden. User role '{role}' is not authorized. Required: {allowed_str}.",
        )

    return _role_checker


# Canonical endpoint authorizers
require_field_agent_or_admin = require_roles({"FIELD_AGENT", "ADMIN"})
require_forest_officer_or_admin = require_roles({"FOREST_OFFICER", "ADMIN"})
require_admin_only = require_roles({"ADMIN"})
