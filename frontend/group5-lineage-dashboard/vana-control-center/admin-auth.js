/**
 * VANA Control Center — Unified Authentication & RBAC Engine
 * ==========================================================
 *
 * Single shared authentication module for both:
 *  - Operational Dashboard (index.html / app.js)
 *  - Administration Control Plane (admin.html / admin.js)
 *
 * Real Backend Authentication & Confirmed RBAC Contract:
 *  - Endpoints: POST /auth/login, POST /auth/register, GET /auth/me
 *  - Bearer Token: Authorization: Bearer <access_token>
 *  - Confirmed Role Mappings:
 *      admin        → PLATFORM_ADMIN
 *      participant  → APPROVED_CONSUMER
 *      judge        → AUDITOR
 *      auditor      → AUDITOR
 *      steward      → GOVERNANCE_STEWARD
 *
 * Safety Invariants:
 *  - DEV_MODE simulator is disabled; no client-side privilege escalation.
 *  - Access token persisted tab-scoped in sessionStorage only. No password storage.
 *  - Cached user data is NEVER treated as authoritative authorization;
 *    session is validated on initialization via GET /auth/me.
 *  - Fail-closed permission checking supports both array and object permissions.
 */
(function (root, factory) {
  if (typeof module !== "undefined" && module.exports) {
    module.exports = factory();
  } else {
    root.VANA_AUTH = factory();
  }
})(typeof window !== "undefined" ? window : globalThis, function () {
  "use strict";

  // Production deployment switch — simulator permanently disabled
  var DEV_MODE = false;

  // Storage keys (tab-scoped)
  var TOKEN_STORAGE_KEY = "vana_access_token";
  var USER_STORAGE_KEY = "vana_user_profile";
  var VANA_AUTH_STORAGE_KEYS = [
    "vana_access_token",
    "vana_user_profile",
    "vana_user",
    "vana_role",
    "vana_dev_role"
  ];

  // ── CONFIRMED ROLE CONSTANTS ───────────────────────────────────────────
  var ROLES = Object.freeze({
    // Canonical backend mapped roles
    PLATFORM_ADMIN:     "PLATFORM_ADMIN",
    APPROVED_CONSUMER:  "APPROVED_CONSUMER",
    AUDITOR:            "AUDITOR",
    GOVERNANCE_STEWARD: "GOVERNANCE_STEWARD",

    // Backward-compatibility aliases
    ADMIN:              "PLATFORM_ADMIN",
    ADMINISTRATOR:      "PLATFORM_ADMIN",
    PARTICIPANT:        "APPROVED_CONSUMER",
    OPERATOR:           "APPROVED_CONSUMER",
    VIEWER:             "APPROVED_CONSUMER",
    JUDGE:              "AUDITOR",
    ANALYST:            "AUDITOR",
    STEWARD:            "GOVERNANCE_STEWARD",
  });

  // ── ROLE PRESENTATION METADATA ─────────────────────────────────────────
  var ROLE_META = Object.freeze({
    PLATFORM_ADMIN: {
      label: "Platform Admin",
      description: "Full system administration and governed execution access",
      color: "#8B5CF6",
    },
    APPROVED_CONSUMER: {
      label: "Approved Consumer",
      description: "Operational observation and telemetry monitoring (Read-only execution)",
      color: "#3A8F5C",
    },
    AUDITOR: {
      label: "Auditor / Judge",
      description: "Audit-log review, deterministic lineage verification, and evidence inspection",
      color: "#C9822B",
    },
    GOVERNANCE_STEWARD: {
      label: "Governance Steward",
      description: "Governance policy and contextual verification oversight",
      color: "#0284C7",
    },
  });

  // ── PERMISSION CONSTANTS ───────────────────────────────────────────────
  var PERMISSIONS = Object.freeze({
    VIEW_DASHBOARD:             "VIEW_DASHBOARD",
    VIEW_MAP:                   "VIEW_MAP",
    VIEW_ALERTS:                "VIEW_ALERTS",
    VIEW_LINEAGE:               "VIEW_LINEAGE",
    VIEW_EVIDENCE:              "VIEW_EVIDENCE",
    RUN_REPLAY:                 "RUN_REPLAY",
    ACKNOWLEDGE_ALERT:          "ACKNOWLEDGE_ALERT",
    VIEW_AUDIT_LOG:             "VIEW_AUDIT_LOG",
    MANAGE_USERS:               "MANAGE_USERS",
    MANAGE_ROLES:               "MANAGE_ROLES",
    MANAGE_MAP_CONFIG:          "MANAGE_MAP_CONFIG",
    MANAGE_ALERT_RULES:         "MANAGE_ALERT_RULES",
    MANAGE_GOVERNANCE_POLICIES: "MANAGE_GOVERNANCE_POLICIES",
    MANAGE_SYSTEM_CONFIG:       "MANAGE_SYSTEM_CONFIG",
    EXECUTE_WORKFLOW:           "EXECUTE_WORKFLOW",
  });

  // ── ROLE NORMALIZATION ─────────────────────────────────────────────────
  function normalizeRole(rawRole) {
    if (!rawRole || typeof rawRole !== "string") return null;
    var clean = rawRole.trim().toLowerCase();
    switch (clean) {
      case "admin":
      case "administrator":
      case "platform_admin":
        return ROLES.PLATFORM_ADMIN;
      case "participant":
      case "consumer":
      case "approved_consumer":
      case "viewer":
      case "operator":
        return ROLES.APPROVED_CONSUMER;
      case "judge":
      case "auditor":
      case "analyst":
        return ROLES.AUDITOR;
      case "steward":
      case "governance_steward":
        return ROLES.GOVERNANCE_STEWARD;
      default:
        return rawRole.toUpperCase();
    }
  }

  // ── PERMISSION NORMALIZATION (ARRAY OR OBJECT SUPPORT) ─────────────────
  function normalizePermissions(rawPerms) {
    var granted = new Set();
    var rawObj = {};

    if (Array.isArray(rawPerms)) {
      rawPerms.forEach(function (p) {
        if (typeof p === "string") {
          var clean = p.trim();
          granted.add(clean.toUpperCase());
          granted.add(clean);
          rawObj[clean] = true;
        }
      });
    } else if (rawPerms && typeof rawPerms === "object") {
      Object.assign(rawObj, rawPerms);
      for (var key in rawPerms) {
        if (Object.prototype.hasOwnProperty.call(rawPerms, key)) {
          var val = rawPerms[key];
          var upKey = key.trim().toUpperCase();
          if (val === true || val === 1 || val === "true") {
            granted.add(upKey);
            granted.add(key);
          } else if (val && typeof val === "object") {
            // Nested permission representation e.g. { audit: { read: true } }
            for (var subKey in val) {
              if (Object.prototype.hasOwnProperty.call(val, subKey)) {
                var subVal = val[subKey];
                if (subVal === true || subVal === 1 || subVal === "true") {
                  granted.add(upKey + "_" + subKey.trim().toUpperCase());
                  granted.add(key + "_" + subKey);
                }
              }
            }
          }
        }
      }
    }

    return {
      has: function (permission) {
        if (!permission || typeof permission !== "string") return false;
        var clean = permission.trim();
        var up = clean.toUpperCase();
        if (granted.has(up) || granted.has(clean)) return true;
        if (rawObj[clean] === true || rawObj[clean.toLowerCase()] === true || rawObj[up] === true) {
          return true;
        }
        return false;
      },
      list: Array.from(granted),
      raw: rawObj,
    };
  }

  // ── USER PROFILE NORMALIZATION ─────────────────────────────────────────
  function normalizeUserProfile(resp) {
    if (!resp || typeof resp !== "object") return null;

    var candidate = null;
    if (resp.user && typeof resp.user === "object") {
      candidate = resp.user;
    } else if (resp.data && typeof resp.data === "object") {
      if (resp.data.user && typeof resp.data.user === "object") {
        candidate = resp.data.user;
      } else {
        candidate = resp.data;
      }
    } else if (resp.id || resp._id || resp.email) {
      candidate = resp;
    }

    if (!candidate) return null;

    var id = candidate.id || candidate._id || candidate.userId || resp.id || resp._id || "usr-anon";
    var email = candidate.email || resp.email || "";
    var name = candidate.name || candidate.fullName || candidate.username || email || "Authenticated User";
    var rawRole = candidate.role || resp.role || "";
    var role = normalizeRole(rawRole);
    var rawPerms = candidate.permissions || candidate.perms || resp.permissions || [];
    var permsHelper = normalizePermissions(rawPerms);

    var meta = (role && ROLE_META[role]) || {
      label: role || "Authenticated User",
      description: "Authenticated VANA Session",
      color: "#6B7486",
    };

    return {
      id: String(id),
      email: String(email),
      name: String(name),
      role: role,
      rawRole: rawRole,
      roleLabel: meta.label,
      roleDescription: meta.description,
      roleColor: meta.color,
      permissions: permsHelper.list,
      _permsHelper: permsHelper,
      isDev: false,
    };
  }

  // ── SAFE STORAGE ACCESS ────────────────────────────────────────────────
  function _getStorage() {
    try {
      if (typeof window !== "undefined" && window.sessionStorage) {
        return window.sessionStorage;
      }
    } catch (_) {}
    return null;
  }

  function _clearVanaStorage() {
    var storage = _getStorage();
    if (storage) {
      VANA_AUTH_STORAGE_KEYS.forEach(function (k) {
        try { storage.removeItem(k); } catch (_) {}
      });
    }
  }

  // ── IN-MEMORY AUTH STATE ───────────────────────────────────────────────
  var _currentUser = null;
  var _isSessionLiveValidated = false;
  var _listeners = [];
  var _restorationPromise = null;

  function _notifyListeners(user) {
    _listeners.forEach(function (cb) {
      try { cb(user); } catch (e) { console.error("[VANA Auth] Listener error:", e); }
    });
  }

  function _getAuthEndpoint(key, fallback) {
    if (typeof window !== "undefined" && window.VANA_CONFIG && window.VANA_CONFIG[key]) {
      return window.VANA_CONFIG[key];
    }
    return fallback;
  }

  // ── ACCESS DENIED RENDERER ─────────────────────────────────────────────
  function _renderAccessDenied(permission) {
    return [
      '<div class="admin-denied-state">',
      '  <div class="admin-denied-icon">',
      '    <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">',
      '      <circle cx="12" cy="12" r="10"></circle>',
      '      <line x1="4.93" y1="4.93" x2="19.07" y2="19.07"></line>',
      '    </svg>',
      '  </div>',
      '  <div class="admin-denied-title">Access Denied</div>',
      '  <div class="admin-denied-msg">',
      '    Your current role does not have the <span class="mono">' + (permission || "PRIVILEGED_ACTION") + '</span> permission.<br>',
      '    Backend authorization is enforced. Contact an Administrator to request elevated access.',
      '  </div>',
      '  <div class="admin-denied-note">',
      '    VANA Environmental Governance System · Strict Fail-Closed Zero-Fabrication Architecture',
      '  </div>',
      '</div>',
    ].join("\n");
  }

  // ── CORE PUBLIC API ────────────────────────────────────────────────────
  var vanaAuth = {
    ROLES: ROLES,
    ROLE_META: ROLE_META,
    PERMISSIONS: PERMISSIONS,
    DEV_MODE: DEV_MODE,

    // Export helpers for testability and normalization
    normalizeRole: normalizeRole,
    normalizePermissions: normalizePermissions,
    normalizeUserProfile: normalizeUserProfile,

    /**
     * Returns the current authenticated user object or null if unauthenticated.
     */
    getCurrentUser: function () {
      return _currentUser;
    },

    /**
     * Returns true if user has an active authenticated session.
     */
    isAuthenticated: function () {
      return !!(_currentUser && this.getAccessToken());
    },

    /**
     * Returns true only if session has been actively validated by a successful
     * live backend /me check or login (not a degraded offline cached session).
     */
    isLiveValidated: function () {
      return !!(_currentUser && this.getAccessToken() && _isSessionLiveValidated);
    },

    /**
     * Returns the current access token string from sessionStorage.
     */
    getAccessToken: function () {
      var storage = _getStorage();
      return storage ? storage.getItem(TOKEN_STORAGE_KEY) : null;
    },

    /**
     * Returns Authorization headers object for authenticated API calls.
     */
    getAuthHeader: function () {
      var token = this.getAccessToken();
      return token ? { "Authorization": "Bearer " + token } : {};
    },

    /**
     * Checks if current user has a specific permission.
     * Evaluates backend permissions primary; falls back to canonical role matrix.
     * Fails closed if user is unauthenticated, unvalidated offline, or unauthorized.
     */
    hasPermission: function (permission) {
      if (!_currentUser) return false;
      if (!permission || typeof permission !== "string") return false;

      // Fail-Closed Invariant: A cached user after network error cannot perform
      // privileged actions or bypass live backend session validation.
      var privilegedPermissions = [
        PERMISSIONS.EXECUTE_WORKFLOW,
        PERMISSIONS.MANAGE_USERS,
        PERMISSIONS.MANAGE_ROLES,
        PERMISSIONS.MANAGE_SYSTEM_CONFIG,
        PERMISSIONS.VIEW_AUDIT_LOG,
        PERMISSIONS.MANAGE_GOVERNANCE_POLICIES,
      ];
      if (!_isSessionLiveValidated && privilegedPermissions.indexOf(permission) !== -1) {
        return false;
      }

      var role = _currentUser.role;

      // Fail-Closed Safeguard: Approved Consumer can NEVER execute workflows or manage users
      if (role === ROLES.APPROVED_CONSUMER && privilegedPermissions.indexOf(permission) !== -1) {
        return false;
      }

      // 1. Backend-provided permissions object check (primary authority)
      if (_currentUser._permsHelper && _currentUser._permsHelper.list.length > 0) {
        // Backend provided an explicit permissions list/object — fail closed if omitted
        return _currentUser._permsHelper.has(permission);
      }

      // 2. Canonical role capability fallback (only if backend perms omitted in contract)
      if (role === ROLES.PLATFORM_ADMIN) {
        return true;
      }

      if (role === ROLES.AUDITOR) {
        var auditorPerms = [
          PERMISSIONS.VIEW_DASHBOARD,
          PERMISSIONS.VIEW_MAP,
          PERMISSIONS.VIEW_ALERTS,
          PERMISSIONS.VIEW_LINEAGE,
          PERMISSIONS.VIEW_EVIDENCE,
          PERMISSIONS.RUN_REPLAY,
          PERMISSIONS.ACKNOWLEDGE_ALERT,
          PERMISSIONS.VIEW_AUDIT_LOG,
        ];
        return auditorPerms.indexOf(permission) !== -1;
      }

      if (role === ROLES.APPROVED_CONSUMER) {
        var participantPerms = [
          PERMISSIONS.VIEW_DASHBOARD,
          PERMISSIONS.VIEW_MAP,
          PERMISSIONS.VIEW_ALERTS,
          PERMISSIONS.VIEW_LINEAGE,
        ];
        return participantPerms.indexOf(permission) !== -1;
      }

      if (role === ROLES.GOVERNANCE_STEWARD) {
        var stewardPerms = [
          PERMISSIONS.VIEW_DASHBOARD,
          PERMISSIONS.VIEW_MAP,
          PERMISSIONS.VIEW_ALERTS,
          PERMISSIONS.VIEW_LINEAGE,
          PERMISSIONS.VIEW_EVIDENCE,
          PERMISSIONS.MANAGE_GOVERNANCE_POLICIES,
        ];
        return stewardPerms.indexOf(permission) !== -1;
      }

      // Fail-closed for all unknown, tampered, or unassigned roles
      return false;
    },

    /**
     * Guards a container element. If the user lacks the permission,
     * injects the Access Denied state into containerEl and returns false.
     */
    requirePermission: function (permission, containerEl) {
      if (!this.hasPermission(permission)) {
        if (containerEl) {
          containerEl.innerHTML = _renderAccessDenied(permission);
        }
        return false;
      }
      return true;
    },

    /**
     * Authenticates user against backend POST /auth/login.
     * Never stores passwords. Stores access_token in sessionStorage.
     */
    login: async function (email, password) {
      if (!email || !password || typeof email !== "string" || typeof password !== "string") {
        return { success: false, error: "Email and password are required." };
      }

      var loginUrl = _getAuthEndpoint("AUTH_LOGIN", "/proxy/auth/login");
      try {
        var res = await fetch(loginUrl, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "Accept": "application/json",
          },
          body: JSON.stringify({ email: email.trim(), password: password }),
        });

        var data = null;
        try {
          data = await res.json();
        } catch (_) {
          data = null;
        }

        if (!res.ok) {
          var errMsg = "Authentication failed (HTTP " + res.status + ")";
          if (data && (data.detail || data.message || data.error)) {
            errMsg = data.detail || data.message || data.error;
          } else if (res.status === 401) {
            errMsg = "Invalid email or password.";
          }
          return { success: false, error: errMsg, status: res.status };
        }

        if (!data || (!data.access_token && !data.token)) {
          return { success: false, error: "Malformed login response from authentication server." };
        }

        var token = data.access_token || data.token;
        var normalizedUser = normalizeUserProfile(data);
        if (!normalizedUser) {
          // If profile missing in login envelope, fetch via GET /auth/me
          var meRes = await this._fetchMeProfile(token);
          if (meRes.success) {
            normalizedUser = meRes.user;
          } else {
            return { success: false, error: "Failed to load authenticated user profile." };
          }
        }

        // Persist session tab-scoped
        var storage = _getStorage();
        if (storage) {
          storage.setItem(TOKEN_STORAGE_KEY, token);
          storage.setItem(USER_STORAGE_KEY, JSON.stringify(normalizedUser));
        }

        _currentUser = normalizedUser;
        _isSessionLiveValidated = true;
        _notifyListeners(_currentUser);

        return { success: true, user: _currentUser, token: token };
      } catch (err) {
        return { success: false, error: "Connection error reaching authentication service: " + err.message };
      }
    },

    /**
     * Helper to retrieve profile from GET /auth/me using Bearer token.
     */
    _fetchMeProfile: async function (token) {
      var meUrl = _getAuthEndpoint("AUTH_ME", "/proxy/auth/me");
      try {
        var res = await fetch(meUrl, {
          method: "GET",
          headers: {
            "Accept": "application/json",
            "Authorization": "Bearer " + token,
          },
        });

        if (!res.ok) {
          return { success: false, status: res.status };
        }

        var data = await res.json();
        var user = normalizeUserProfile(data);
        if (!user) {
          return { success: false, status: 500, error: "Could not parse user profile from /me" };
        }

        return { success: true, user: user };
      } catch (err) {
        return { success: false, error: err.message, isNetworkError: true };
      }
    },

    /**
     * Restores session on page reload using GET /auth/me verification.
     * Prevents duplicate simultaneous validation calls.
     */
    restoreSession: function () {
      if (_restorationPromise) {
        return _restorationPromise;
      }

      var self = this;
      _restorationPromise = (async function () {
        var token = self.getAccessToken();
        if (!token) {
          _currentUser = null;
          _isSessionLiveValidated = false;
          return null;
        }

        // Validate token against backend /me
        var meRes = await self._fetchMeProfile(token);
        if (meRes.success) {
          _currentUser = meRes.user;
          _isSessionLiveValidated = true;
          var storage = _getStorage();
          if (storage) {
            storage.setItem(USER_STORAGE_KEY, JSON.stringify(_currentUser));
          }
          _notifyListeners(_currentUser);
          return _currentUser;
        }

        // If backend explicitly rejected token (401 Unauthorized), purge session
        if (meRes.status === 401) {
          console.warn("[VANA Auth] Stored token rejected with 401 Unauthorized — clearing session.");
          _isSessionLiveValidated = false;
          self.clearSession();
          return null;
        }

        // On network error or server 5xx: preserve token and use cached profile in degraded state
        if (meRes.isNetworkError || (meRes.status && meRes.status >= 500)) {
          console.warn("[VANA Auth] Backend /me unavailable (" + (meRes.status || "network error") + "). Retaining cached session in degraded state.");
          _isSessionLiveValidated = false;
          var storage2 = _getStorage();
          if (storage2) {
            try {
              var cached = JSON.parse(storage2.getItem(USER_STORAGE_KEY) || "null");
              if (cached) {
                cached._permsHelper = normalizePermissions(cached.permissions);
                cached.isLiveValidated = false;
                cached.isOffline = true;
                _currentUser = cached;
                _notifyListeners(_currentUser);
                return _currentUser;
              }
            } catch (_) {}
          }
        }

        return _currentUser;
      })().finally(function () {
        _restorationPromise = null;
      });

      return _restorationPromise;
    },

    /**
     * Clears all VANA authentication session storage keys and resets session state.
     */
    clearSession: function () {
      _clearVanaStorage();
      _currentUser = null;
      _isSessionLiveValidated = false;
      _notifyListeners(null);
    },

    /**
     * Logs out the user by clearing client-side VANA storage and notifying listeners.
     */
    logout: function () {
      this.clearSession();
    },

    /**
     * Subscribes a listener callback to auth state changes.
     */
    onAuthChange: function (callback) {
      if (typeof callback === "function") {
        _listeners.push(callback);
      }
    },

    /**
     * Simulated role elevation permanently disabled in production.
     */
    setDevRole: function (role) {
      console.warn("[VANA Auth] setDevRole() is disabled. Production RBAC is enforced by backend.");
    },
  };

  console.log("[VANA Auth] Initialized — Production RBAC boundary active (Backend enforced)");
  return Object.freeze(vanaAuth);
});
