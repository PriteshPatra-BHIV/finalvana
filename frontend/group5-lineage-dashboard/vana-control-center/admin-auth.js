/**
 * VANA Control Center — Admin Authentication & Authorization Boundary
 * ====================================================================
 *
 * This is the SINGLE module responsible for user identity and permission
 * resolution in the Admin Control Plane.
 *
 * ── DEV MODE (currently active) ───────────────────────────────────────
 * A role simulator is active. Simulated role is stored in sessionStorage
 * only (cleared when tab closes). No credentials are stored or checked.
 * No users are fabricated. The role picker is visible in the Admin UI
 * under a clearly-labelled [DEV] banner.
 *
 * ── PRODUCTION INTEGRATION ────────────────────────────────────────────
 * To connect a real authentication provider:
 *   1. Set DEV_MODE = false  (line ~50 below)
 *   2. Implement _productionGetCurrentUser() to call your auth backend:
 *      - OAuth2 token introspection endpoint
 *      - OIDC /userinfo endpoint
 *      - Government SSO / SAML assertion consumer
 *      - Custom backend: GET /api/auth/me → { id, name, role, permissions }
 *   3. No other files in the Admin UI need to change.
 *
 * ── SECURITY NOTICE ───────────────────────────────────────────────────
 * Frontend permission checks are UX gates only. They control what the
 * Admin UI renders, not what actions are possible.
 *
 * Backend API endpoints (when they exist) MUST enforce authorization
 * independently via session tokens / JWT / RBAC middleware.
 * Do NOT rely on frontend checks alone for any sensitive operation.
 * =====================================================================
 */
(function () {
  "use strict";

  // ── DEPLOYMENT SWITCH ──────────────────────────────────────────────
  // Set to false and implement _productionGetCurrentUser() for production.
  const DEV_MODE = true;
  // ──────────────────────────────────────────────────────────────────

  // ── ROLE DEFINITIONS ──────────────────────────────────────────────
  const ROLES = Object.freeze({
    VIEWER:        "viewer",
    OPERATOR:      "operator",
    ANALYST:       "analyst",
    ADMINISTRATOR: "administrator",
  });

  const ROLE_META = Object.freeze({
    viewer:        { label: "Viewer",        description: "Read-only access to operational dashboard",                  color: "#6B7486" },
    operator:      { label: "Operator",      description: "Can acknowledge alerts and run replay verification",         color: "#3A8F5C" },
    analyst:       { label: "Analyst",       description: "Operator access + audit log + evidence inspection",          color: "#C9822B" },
    administrator: { label: "Administrator", description: "Full system access including user and configuration management", color: "#8B5CF6" },
  });

  // ── PERMISSION CONSTANTS ───────────────────────────────────────────
  const PERMISSIONS = Object.freeze({
    VIEW_DASHBOARD:            "VIEW_DASHBOARD",
    VIEW_MAP:                  "VIEW_MAP",
    VIEW_ALERTS:               "VIEW_ALERTS",
    VIEW_LINEAGE:              "VIEW_LINEAGE",
    VIEW_EVIDENCE:             "VIEW_EVIDENCE",
    RUN_REPLAY:                "RUN_REPLAY",
    ACKNOWLEDGE_ALERT:         "ACKNOWLEDGE_ALERT",
    VIEW_AUDIT_LOG:            "VIEW_AUDIT_LOG",
    MANAGE_USERS:              "MANAGE_USERS",
    MANAGE_ROLES:              "MANAGE_ROLES",
    MANAGE_MAP_CONFIG:         "MANAGE_MAP_CONFIG",
    MANAGE_ALERT_RULES:        "MANAGE_ALERT_RULES",
    MANAGE_GOVERNANCE_POLICIES:"MANAGE_GOVERNANCE_POLICIES",
    MANAGE_SYSTEM_CONFIG:      "MANAGE_SYSTEM_CONFIG",
  });

  // ── ROLE → PERMISSION MATRIX ───────────────────────────────────────
  const _viewerPerms = [
    PERMISSIONS.VIEW_DASHBOARD,
    PERMISSIONS.VIEW_MAP,
    PERMISSIONS.VIEW_ALERTS,
    PERMISSIONS.VIEW_LINEAGE,
  ];

  const _operatorPerms = [
    ..._viewerPerms,
    PERMISSIONS.VIEW_EVIDENCE,
    PERMISSIONS.RUN_REPLAY,
    PERMISSIONS.ACKNOWLEDGE_ALERT,
  ];

  const _analystPerms = [
    ..._operatorPerms,
    PERMISSIONS.VIEW_AUDIT_LOG,
  ];

  const _adminPerms = [
    ..._analystPerms,
    PERMISSIONS.MANAGE_USERS,
    PERMISSIONS.MANAGE_ROLES,
    PERMISSIONS.MANAGE_MAP_CONFIG,
    PERMISSIONS.MANAGE_ALERT_RULES,
    PERMISSIONS.MANAGE_GOVERNANCE_POLICIES,
    PERMISSIONS.MANAGE_SYSTEM_CONFIG,
  ];

  const ROLE_PERMISSIONS = Object.freeze({
    [ROLES.VIEWER]:        _viewerPerms,
    [ROLES.OPERATOR]:      _operatorPerms,
    [ROLES.ANALYST]:       _analystPerms,
    [ROLES.ADMINISTRATOR]: _adminPerms,
  });

  // ── DEV SIMULATOR ─────────────────────────────────────────────────
  // No credentials. Role stored in sessionStorage (tab-scoped only).
  const DEV_SESSION_KEY = "vana_dev_role";

  function _devGetCurrentUser() {
    const storedRole = sessionStorage.getItem(DEV_SESSION_KEY) || ROLES.VIEWER;
    const role = ROLE_PERMISSIONS[storedRole] ? storedRole : ROLES.VIEWER;
    const meta = ROLE_META[role];
    return {
      id:          "dev-session",
      name:        "Development Session",
      role:        role,
      roleLabel:   meta.label,
      permissions: ROLE_PERMISSIONS[role],
      isDev:       true,
    };
  }

  // ── PRODUCTION HOOK ───────────────────────────────────────────────
  // Replace this function body when connecting a real auth provider.
  // Must return: { id, name, role, roleLabel, permissions[], isDev: false }
  // or throw/return null to signal unauthenticated state.
  function _productionGetCurrentUser() {
    // Example (OAuth2 / backend session):
    //   const res = await fetch('/api/auth/me', { credentials: 'include' });
    //   if (!res.ok) return null; // unauthenticated
    //   return res.json();
    throw new Error(
      "[VANA Auth] Production auth not configured. " +
      "Set DEV_MODE=false only after implementing _productionGetCurrentUser()."
    );
  }

  // ── AUTH CHANGE LISTENERS ─────────────────────────────────────────
  const _listeners = [];

  function _notifyListeners(user) {
    _listeners.forEach(function (cb) { try { cb(user); } catch (e) {} });
  }

  // ── ACCESS DENIED RENDERER ─────────────────────────────────────────
  function _renderAccessDenied(permission) {
    return `
      <div class="admin-denied-state">
        <div class="admin-denied-icon">
          <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <circle cx="12" cy="12" r="10"></circle>
            <line x1="4.93" y1="4.93" x2="19.07" y2="19.07"></line>
          </svg>
        </div>
        <div class="admin-denied-title">Access Denied</div>
        <div class="admin-denied-msg">
          Your current role does not have the <span class="mono">${permission}</span> permission.<br>
          Contact an Administrator to request elevated access.
        </div>
        <div class="admin-denied-note">
          This is a frontend access gate. Backend authorization is enforced separately when backend endpoints are available.
        </div>
      </div>`;
  }

  // ── PUBLIC API ─────────────────────────────────────────────────────
  window.VANA_AUTH = Object.freeze({
    ROLES,
    ROLE_META,
    PERMISSIONS,
    ROLE_PERMISSIONS,
    DEV_MODE,

    /** Returns the current user object, or null if unauthenticated. */
    getCurrentUser: function () {
      try {
        return DEV_MODE ? _devGetCurrentUser() : _productionGetCurrentUser();
      } catch (e) {
        console.error("[VANA Auth] getCurrentUser failed:", e);
        return null;
      }
    },

    /** Returns true if the current user has the given permission. */
    hasPermission: function (permission) {
      const user = this.getCurrentUser();
      return !!(user && user.permissions && user.permissions.indexOf(permission) !== -1);
    },

    /**
     * Guards a container element. If the user lacks the permission,
     * injects the Access Denied state into containerEl and returns false.
     * Returns true if access is granted.
     */
    requirePermission: function (permission, containerEl) {
      if (!this.hasPermission(permission)) {
        if (containerEl) containerEl.innerHTML = _renderAccessDenied(permission);
        return false;
      }
      return true;
    },

    /**
     * DEV ONLY — Sets the simulated role. No-op in production mode.
     * Notifies all auth change listeners.
     */
    setDevRole: function (role) {
      if (!DEV_MODE) {
        console.warn("[VANA Auth] setDevRole() called in production mode — ignored.");
        return;
      }
      if (!ROLE_PERMISSIONS[role]) {
        console.warn("[VANA Auth] Unknown role:", role);
        return;
      }
      sessionStorage.setItem(DEV_SESSION_KEY, role);
      _notifyListeners(this.getCurrentUser());
    },

    /** Register a callback invoked whenever the auth state changes. */
    onAuthChange: function (callback) {
      _listeners.push(callback);
    },
  });

  console.log(
    "[VANA Auth] Initialized —",
    DEV_MODE
      ? "DEV simulator mode active (role stored in sessionStorage, not a real user)"
      : "Production auth mode"
  );
})();
