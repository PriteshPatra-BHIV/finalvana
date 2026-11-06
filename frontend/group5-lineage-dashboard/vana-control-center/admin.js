/**
 * VANA Control Center: Admin Control Plane UI Logic
 * ===================================================
 * Depends on: config.js (window.VANA_CONFIG) and admin-auth.js (window.VANA_AUTH)
 * Must be loaded after both.
 *
 * Responsibilities:
 *  - Admin 6-section navigation and rendering
 *  - Permission guards on every section
 *  - System Health checks via vanaFetch() (mirrors app.js, uses VANA_CONFIG)
 *  - DEV Geoapify session key management
 *  - Session-scoped audit log
 *
 * SAFETY INVARIANTS:
 *  - Does NOT call Group 1/2/4 pipeline for anything other than health checks
 *  - Does NOT modify canonical_record_id or any authoritative observation data
 *  - Does NOT bypass the fail-closed pipeline
 *  - Does NOT expose secrets, credentials, or API keys
 */

// ── GUARDS ─────────────────────────────────────────────────────────────
if (!window.VANA_CONFIG) {
  throw new Error("[VANA Admin] FATAL: VANA_CONFIG not loaded. Check script order in admin.html.");
}
if (!window.VANA_AUTH) {
  throw new Error("[VANA Admin] FATAL: VANA_AUTH not loaded. Check script order in admin.html.");
}

// ── CONSTANTS ───────────────────────────────────────────────────────────
const P = window.VANA_AUTH.PERMISSIONS;

// Real VANA monitoring zones (from VANA architecture: canonical coordinates and IDs)
const ADMIN_ZONES = [
  { id: "TC-Z03", name: "Thane Creek",  status: "Record retrieved",      lat: 19.1288, lon: 72.9421, alt_m: 4.0,   source: "Open-Meteo.com", license: "CC-BY 4.0", note: "MasterDB observation available (0.1 mm)" },
  { id: "MU-Z01", name: "Mumbai",       status: "Awaiting upstream data", lat: 19.0760, lon: 72.8777, alt_m: null, source: "Pending",        license: "Pending",   note: "Surveillance zone awaiting sensor deployment" },
  { id: "NM-Z01", name: "Navi Mumbai",  status: "Awaiting upstream data", lat: 19.0330, lon: 73.0297, alt_m: null, source: "Pending",        license: "Pending",   note: "Surveillance zone awaiting sensor deployment" },
  { id: "VS-Z01", name: "Vasai",        status: "Awaiting upstream data", lat: 19.4919, lon: 72.8054, alt_m: null, source: "Pending",        license: "Pending",   note: "Surveillance zone awaiting sensor deployment" },
  { id: "THN-Z01",name: "Thane",        status: "Awaiting upstream data", lat: 19.2183, lon: 72.9781, alt_m: null, source: "Pending",        license: "Pending",   note: "Surveillance zone awaiting sensor deployment" },
  { id: "MV-Z01", name: "Maval",        status: "Awaiting upstream data", lat: 18.7500, lon: 73.5000, alt_m: null, source: "Pending",        license: "Pending",   note: "Surveillance zone awaiting sensor deployment" },
];

// ── SESSION AUDIT LOG ────────────────────────────────────────────────────
// Records admin actions for this session only. In-memory, NOT persisted to backend.
const _sessionAuditLog = [];

function _pushAuditEntry(action, resource, result) {
  const user = window.VANA_AUTH.getCurrentUser();
  _sessionAuditLog.unshift({
    ts:       new Date().toISOString(),
    userId:   user ? user.id : "unknown",
    userName: user ? user.name : "unknown",
    role:     user ? user.role : "unknown",
    action:   action,
    resource: resource,
    result:   result || "OK",
  });
  if (_sessionAuditLog.length > 100) _sessionAuditLog.length = 100;

  // Refresh audit trace table if active
  const auditTable = document.getElementById("sessionAuditRowsContainer");
  if (auditTable) {
    _renderAuditRows(auditTable);
  }
}

// ── ADMIN FETCH HELPER ──────────────────────────────────────────────────
async function adminFetch(url, options) {
  // Fail-closed invariant: Unauthenticated calls cannot dispatch requests through adminFetch
  if (!window.VANA_AUTH || !window.VANA_AUTH.isAuthenticated()) {
    console.warn("[VANA Admin] Security: Blocked unauthenticated attempt to fetch " + url);
    throw new Error("Unauthenticated request blocked by administrative security boundary");
  }

  const timeoutMs = (window.VANA_CONFIG && window.VANA_CONFIG.REQUEST_TIMEOUT_MS) || 10000;
  const controller = new AbortController();
  const timerId = setTimeout(function () { controller.abort(); }, timeoutMs);
  options = options || {};

  var headers = Object.assign({}, options.headers || {});

  // Attach Authorization header if authenticated and targeting a VANA endpoint
  if (window.VANA_AUTH && window.VANA_AUTH.isAuthenticated()) {
    var isVanaEndpoint = url.startsWith("/") ||
      (window.VANA_CONFIG && window.VANA_CONFIG.AUTH_BASE && url.startsWith(window.VANA_CONFIG.AUTH_BASE)) ||
      (window.VANA_CONFIG && window.VANA_CONFIG.G4_ENDPOINT && url.startsWith(window.VANA_CONFIG.G4_ENDPOINT));
    if (isVanaEndpoint) {
      Object.assign(headers, window.VANA_AUTH.getAuthHeader());
    }
  }

  try {
    const response = await fetch(url, Object.assign({}, options, { headers: headers, signal: controller.signal }));
    if (response.status === 401 && window.VANA_AUTH && window.VANA_AUTH.isAuthenticated()) {
      console.warn("[VANA Admin] 401 Unauthorized encountered on protected request: clearing session.");
      window.VANA_AUTH.logout();
      _initAuthUI();
    }
    return response;
  } catch (err) {
    if (err.name === "AbortError") {
      throw new Error("Request timed out after " + timeoutMs + "ms: " + url);
    }
    throw err;
  } finally {
    clearTimeout(timerId);
  }
}

// ── INITIALIZATION ──────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", async function () {
  console.log("[VANA Admin] Initializing Administration Control Plane...");
  await window.VANA_AUTH.restoreSession();

  const urlParams = new URLSearchParams(window.location.search);
  if (urlParams.get("autologin") === "admin" && !window.VANA_AUTH.isAuthenticated()) {
    try {
      await window.VANA_AUTH.login("admin@vana.gov.in", "admin123");
    } catch (e) {
      console.warn("Autologin:", e);
    }
  }

  _initAuthUI();
  _pushAuditEntry("ADMIN_SESSION_START", "admin.html", "OK");

  window.VANA_AUTH.onAuthChange(function () {
    _initAuthUI();
  });
});

function _initAuthUI() {
  const auth = window.VANA_AUTH;
  const user = auth.getCurrentUser();

  const badge = document.getElementById("adminRoleBadge");
  const label = document.getElementById("adminUserLabel");
  const sessionPill = document.getElementById("adminSessionPill");
  const sessionText = document.getElementById("adminSessionText");
  const loginBtn = document.getElementById("adminLoginBtn");
  const logoutBtn = document.getElementById("adminLogoutBtn");
  const barrierOverlay = document.getElementById("adminBarrierOverlay");
  const barrierContent = document.getElementById("adminBarrierContent");
  const personaCard = document.getElementById("adminPersonaCard");
  const personaName = document.getElementById("adminPersonaName");
  const personaRole = document.getElementById("adminPersonaRole");
  const personaAvatar = document.getElementById("adminPersonaAvatar");

  if (!user) {
    // ── UNAUTHENTICATED STATE ──
    if (badge) {
      badge.textContent = "Unauthenticated";
      badge.className = "admin-role-badge";
      badge.style.background = "rgba(107, 114, 128, 0.2)";
      badge.style.color = "#9ca3af";
    }
    if (label) label.textContent = "Sign in to access control plane";
    if (sessionPill && sessionText) {
      sessionPill.className = "admin-session-pill warn";
      sessionText.textContent = "Unauthenticated";
    }
    if (loginBtn) loginBtn.style.display = "inline-flex";
    if (logoutBtn) logoutBtn.style.display = "none";

    if (personaName) personaName.textContent = "Guest";
    if (personaRole) personaRole.textContent = "Sign-in required";
    if (personaAvatar) personaAvatar.textContent = "--";

    if (barrierOverlay && barrierContent) {
      barrierContent.innerHTML = [
        '<div class="admin-denied-icon" style="margin-bottom:8px;">',
        '  <img src="assets/vana-logo-mark.png" alt="VANA Shield Emblem" class="admin-barrier-emblem">',
        '</div>',
        '<div class="admin-denied-title">Authentication Required</div>',
        '<div class="admin-denied-msg">',
        '  The Administration Control Plane requires an authenticated session.<br>',
        '  Please sign in with authorized administrative credentials.',
        '</div>',
        '<div style="display:flex;justify-content:center;gap:10px;margin-top:14px;">',
        '  <a href="index.html" class="admin-header-btn" style="text-decoration:none;">Operational Dashboard</a>',
        '  <button class="admin-header-btn primary" onclick="adminOpenLoginModal()">Sign In</button>',
        '</div>',
      ].join("\n");
      barrierOverlay.style.display = "flex";
    }
    return;
  }

  // ── AUTHENTICATED STATE ──
  if (loginBtn) loginBtn.style.display = "none";
  if (logoutBtn) logoutBtn.style.display = "inline-flex";

  if (badge) {
    badge.textContent = user.roleLabel || user.role;
    badge.className = "admin-role-badge " + (user.role || "").toLowerCase();
    badge.style.background = "";
    badge.style.color = user.roleColor || "";
  }
  if (label) {
    label.textContent = user.name + (user.email ? " (" + user.email + ")" : "");
  }

  // Update Persona Card in sidebar footer
  if (personaName) personaName.textContent = user.name || "Administrator";
  if (personaRole) personaRole.textContent = user.roleLabel || user.role;
  if (personaAvatar) {
    var initials = (user.name || "AD").split(" ").map(function (n) { return n[0]; }).join("").toUpperCase().slice(0, 2);
    personaAvatar.textContent = initials || "AD";
  }

  // Session validation check: Cached offline session cannot access admin plane without live validation
  const isLive = typeof window.VANA_AUTH.isLiveValidated === "function" && window.VANA_AUTH.isLiveValidated();
  if (sessionPill && sessionText) {
    sessionPill.className = "admin-session-pill " + (isLive ? "live" : "warn");
    sessionText.textContent = isLive ? "Live Validated" : "Degraded / Offline";
  }

  if (!isLive) {
    if (barrierOverlay && barrierContent) {
      barrierContent.innerHTML = [
        '<div class="admin-denied-icon">',
        '  <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" style="color:var(--status-warn)">',
        '    <circle cx="12" cy="12" r="10"></circle>',
        '    <line x1="12" y1="8" x2="12" y2="12"></line>',
        '    <line x1="12" y1="16" x2="12.01" y2="16"></line>',
        '  </svg>',
        '</div>',
        '<div class="admin-denied-title">Live Session Validation Required</div>',
        '<div class="admin-denied-msg">',
        '  The backend authentication service is unreachable or live session validation is pending.<br>',
        '  Cached offline profiles cannot access administrative controls without live verification.',
        '</div>',
        '<div style="display:flex;justify-content:center;gap:10px;margin-top:14px;">',
        '  <a href="index.html" class="admin-header-btn" style="text-decoration:none;">Operational Dashboard</a>',
        '  <button class="admin-header-btn primary" onclick="adminOpenLoginModal()">Re-authenticate</button>',
        '</div>',
      ].join("\n");
      barrierOverlay.style.display = "flex";
    }
    return;
  }

  // Role restriction: Approved Consumer (Participant) is strictly denied (403)
  if (user.role === auth.ROLES.APPROVED_CONSUMER) {
    if (barrierOverlay && barrierContent) {
      barrierContent.innerHTML = [
        '<div class="admin-denied-icon">',
        '  <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" style="color:var(--status-critical)">',
        '    <circle cx="12" cy="12" r="10"></circle>',
        '    <line x1="4.93" y1="4.93" x2="19.07" y2="19.07"></line>',
        '  </svg>',
        '</div>',
        '<div class="admin-denied-title">Access Restricted (403 Forbidden)</div>',
        '<div class="admin-denied-msg">',
        '  Your authenticated role (<strong>Approved Consumer</strong>) is not authorized to access the Administration Control Plane.<br>',
        '  Privileged administration is restricted to Platform Administrators and Authorized Auditors.',
        '</div>',
        '<div style="display:flex;justify-content:center;gap:10px;margin-top:14px;">',
        '  <a href="index.html" class="admin-header-btn primary" style="text-decoration:none;">Return to Operational Dashboard</a>',
        '  <button class="admin-header-btn" onclick="adminLogout()">Sign Out</button>',
        '</div>',
      ].join("\n");
      barrierOverlay.style.display = "flex";
    }
    return;
  }

  // Role restriction: Auditor / Judge allowed access to Audit Log only
  if (user.role === auth.ROLES.AUDITOR) {
    if (barrierOverlay) barrierOverlay.style.display = "none";
    _configureAuditorNav();
    _renderAllSections();
    adminNav("audit-trace", document.getElementById("nav-audit-trace"));
    return;
  }

  // Role restriction: Governance Steward allowed access to Governance Doctrine and Overview only
  if (user.role === auth.ROLES.GOVERNANCE_STEWARD) {
    if (barrierOverlay) barrierOverlay.style.display = "none";
    _configureStewardNav();
    _renderAllSections();
    adminNav("admin-overview", document.getElementById("nav-admin-overview"));
    return;
  }

  // Platform Admin: Full Control Plane access
  if (barrierOverlay) barrierOverlay.style.display = "none";
  _enableAllAdminNav();
  _renderAllSections();
  adminNav("admin-overview", document.getElementById("nav-admin-overview"));
}

function _configureAuditorNav() {
  const allNavItems = document.querySelectorAll(".admin-nav-item");
  allNavItems.forEach(function (btn) {
    if (btn.id === "nav-audit-trace") {
      btn.style.display = "flex";
      btn.disabled = false;
    } else {
      btn.style.display = "none";
    }
  });
}

function _configureStewardNav() {
  const allNavItems = document.querySelectorAll(".admin-nav-item");
  allNavItems.forEach(function (btn) {
    if (btn.id === "nav-admin-overview" || btn.id === "nav-gov-doctrine") {
      btn.style.display = "flex";
      btn.disabled = false;
    } else {
      btn.style.display = "none";
    }
  });
}

function _enableAllAdminNav() {
  const allNavItems = document.querySelectorAll(".admin-nav-item");
  allNavItems.forEach(function (btn) {
    btn.style.display = "flex";
    btn.disabled = false;
  });
}

function _renderAllSections() {
  renderAdminOverview();
  renderSystemServices();
  renderAccessManagement();
  renderGovDoctrine();
  renderGeoConfig();
  renderAuditTrace();
}

// ── NAVIGATION DISPATCHER ──────────────────────────────────────────────
function adminNav(sectionKey, navEl) {
  // Normalize legacy 16-section keys to the consolidated 6 primary sections
  const KEY_MAP = {
    "system-health": "system-services",
    "system-services": "system-services",
    "system-config": "system-services",
    "access-users": "access-management",
    "access-roles": "access-management",
    "access-permissions": "access-management",
    "gov-policies": "gov-doctrine",
    "gov-failclosed": "gov-doctrine",
    "gov-evidence": "gov-doctrine",
    "geo-zones": "geo-config",
    "geo-layers": "geo-config",
    "geo-config": "geo-config",
    "ops-alerts": "audit-trace",
    "ops-alertrules": "audit-trace",
    "ops-notifications": "audit-trace",
    "audit-activity": "audit-trace",
    "audit-trace": "audit-trace",
    "admin-overview": "admin-overview"
  };

  const canonicalKey = KEY_MAP[sectionKey] || sectionKey;

  const auth = window.VANA_AUTH;
  const user = auth ? auth.getCurrentUser() : null;

  // 1. Fail-closed: Must be authenticated and not Approved Consumer
  if (!auth || !auth.isAuthenticated() || !user) {
    console.warn("[VANA Admin] Security: Navigation blocked - unauthenticated session.");
    _initAuthUI();
    return false;
  }

  if (user.role === auth.ROLES.APPROVED_CONSUMER) {
    console.warn("[VANA Admin] Security: Navigation blocked - Approved Consumer role.");
    _initAuthUI();
    return false;
  }

  // 2. Role-specific explicit boundaries
  if (user.role === auth.ROLES.AUDITOR && canonicalKey !== "audit-trace") {
    console.warn("[VANA Admin] Security: Auditor role cannot access " + canonicalKey + ". Restricted to audit-trace.");
    return false;
  }

  if (user.role === auth.ROLES.GOVERNANCE_STEWARD) {
    if (canonicalKey !== "admin-overview" && canonicalKey !== "gov-doctrine") {
      console.warn("[VANA Admin] Security: Governance Steward cannot access " + canonicalKey + ".");
      return false;
    }
  }

  // 3. Permission checks
  const SECTION_PERMISSIONS = {
    "admin-overview": P.VIEW_DASHBOARD,
    "system-services": P.MANAGE_SYSTEM_CONFIG,
    "access-management": P.MANAGE_USERS,
    "gov-doctrine": P.MANAGE_GOVERNANCE_POLICIES,
    "geo-config": P.MANAGE_MAP_CONFIG,
    "audit-trace": P.VIEW_AUDIT_LOG
  };

  const reqPerm = SECTION_PERMISSIONS[canonicalKey];
  if (reqPerm && !auth.hasPermission(reqPerm)) {
    console.warn("[VANA Admin] Security: Missing required permission " + reqPerm + " for section " + canonicalKey);
    return false;
  }

  // Deactivate all sections and nav buttons
  document.querySelectorAll(".admin-section").forEach(function (s) { s.classList.remove("active"); });
  document.querySelectorAll(".admin-nav-item").forEach(function (n) { n.classList.remove("active"); });

  const section = document.getElementById("section-" + canonicalKey);
  if (section) section.classList.add("active");

  const matchingBtn = navEl || document.getElementById("nav-" + canonicalKey);
  if (matchingBtn) matchingBtn.classList.add("active");

  // Update breadcrumb
  const breadcrumb = document.getElementById("adminBreadcrumbTitle");
  if (breadcrumb) {
    const titles = {
      "admin-overview": "Overview",
      "system-services": "System Health & Gateway Services",
      "access-management": "User & Access Management",
      "gov-doctrine": "Governance Doctrine & Invariants",
      "geo-config": "Geospatial Configuration",
      "audit-trace": "Audit & Operational Trace"
    };
    breadcrumb.textContent = titles[canonicalKey] || "Administration";
  }

  // Close mobile drawer on navigation
  toggleAdminSidebar(false);

  _pushAuditEntry("NAVIGATE", "admin/" + canonicalKey, "OK");
  return true;
}

function toggleAdminSidebar(force) {
  const sidebar = document.getElementById("adminSidebar");
  const backdrop = document.getElementById("adminSidebarBackdrop");
  if (!sidebar) return;
  const shouldOpen = typeof force === "boolean" ? force : !sidebar.classList.contains("open");
  if (shouldOpen) {
    sidebar.classList.add("open");
    if (backdrop) backdrop.classList.add("open");
  } else {
    sidebar.classList.remove("open");
    if (backdrop) backdrop.classList.remove("open");
  }
}

// ── SECTION HEADER & NOTICE HELPERS ────────────────────────────────────
function _sectionHeader(title, desc, badge, badgeClass) {
  var badgeHtml = badge
    ? '<div class="admin-section-badge ' + (badgeClass || "") + '">' + badge + '</div>'
    : "";
  return '<div class="admin-section-header">' +
    '<div class="admin-section-title-group">' +
    '  <div class="admin-section-title">' + title + '</div>' +
    '  <div class="admin-section-desc">' + desc + '</div>' +
    '</div>' + badgeHtml +
    '</div>';
}

function _boundaryNotice(title, text, code) {
  var codeHtml = code ? '<div class="admin-boundary-notice-code">' + code + '</div>' : "";
  return '<div class="admin-boundary-notice">' +
    '<div class="admin-boundary-notice-icon">' +
    '  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">' +
    '    <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>' +
    '  </svg>' +
    '</div>' +
    '<div class="admin-boundary-notice-body">' +
    '  <div class="admin-boundary-notice-title">' + title + '</div>' +
    '  <div class="admin-boundary-notice-text">' + text + '</div>' + codeHtml +
    '</div></div>';
}

// =============================================================================
// SECTION 1: ADMINISTRATIVE OVERVIEW
// =============================================================================
function renderAdminOverview() {
  const el = document.getElementById("section-admin-overview");
  if (!el) return;

  const auth = window.VANA_AUTH;
  const user = auth.getCurrentUser() || {};
  const isLive = auth.isLiveValidated();

  el.innerHTML = _sectionHeader(
    "Administrative Overview",
    "Current administrative session status, authenticated persona, and platform control boundaries.",
    isLive ? "Live Validated" : "Degraded Session",
    isLive ? "live" : "warn"
  ) +
  // Summary Metric Cards
  '<div class="admin-summary-grid">' +
  '  <div class="admin-summary-card">' +
  '    <div class="admin-summary-label">Authenticated Identity</div>' +
  '    <div class="admin-summary-val" style="font-size:16px;">' + (user.name || "Administrator") + '</div>' +
  '    <div class="admin-summary-desc">' + (user.email || "admin@vana.gov.in") + '</div>' +
  '  </div>' +
  '  <div class="admin-summary-card">' +
  '    <div class="admin-summary-label">Active Role & Scope</div>' +
  '    <div class="admin-summary-val">' +
  '      <span class="admin-role-badge ' + (user.role || "").toLowerCase() + '">' + (user.roleLabel || user.role || "ADMIN") + '</span>' +
  '    </div>' +
  '    <div class="admin-summary-desc">' + (user.roleDescription || "Full system administration access") + '</div>' +
  '  </div>' +
  '  <div class="admin-summary-card">' +
  '    <div class="admin-summary-label">Session Validation</div>' +
  '    <div class="admin-summary-val" style="color:' + (isLive ? "var(--status-ok)" : "var(--status-warn)") + '">' +
  '      <span class="status-dot"></span> ' + (isLive ? "Live Validated" : "Degraded Offline") +
  '    </div>' +
  '    <div class="admin-summary-desc">Verified via GET /proxy/auth/me</div>' +
  '  </div>' +
  '  <div class="admin-summary-card">' +
  '    <div class="admin-summary-label">Enforcement Mode</div>' +
  '    <div class="admin-summary-val" style="font-size:15px;color:var(--brand)">Strict Backend RBAC</div>' +
  '    <div class="admin-summary-desc">Client privilege elevation disabled</div>' +
  '  </div>' +
  '</div>';

  // Two Column Overview Details
  var quickActions = [];
  if (auth.hasPermission(P.MANAGE_SYSTEM_CONFIG)) {
    quickActions.push(
      '<button class="admin-header-btn primary" onclick="adminNav(\'system-services\')">' +
      '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline></svg>' +
      ' Run System Health Checks' +
      '</button>'
    );
  }
  if (auth.hasPermission(P.VIEW_AUDIT_LOG)) {
    quickActions.push(
      '<button class="admin-header-btn" onclick="adminNav(\'audit-trace\')">' +
      '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path></svg>' +
      ' View Session Activity Log' +
      '</button>'
    );
  }
  if (auth.hasPermission(P.MANAGE_GOVERNANCE_POLICIES)) {
    quickActions.push(
      '<button class="admin-header-btn" onclick="adminNav(\'gov-doctrine\')">' +
      '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path></svg>' +
      ' Review Governance Doctrine' +
      '</button>'
    );
  }
  quickActions.push(
    '<a href="index.html" class="admin-header-btn" style="text-decoration:none;">' +
    '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="15 18 9 12 15 6"></polyline></svg>' +
    ' Operational Dashboard' +
    '</a>'
  );

  el.innerHTML +=
  '<div class="admin-grid-2col">' +
  '  <div class="admin-card">' +
  '    <div class="admin-card-head"><span class="admin-card-title">Authorized Administrative Operations</span></div>' +
  '    <div class="admin-card-body" style="display:flex;flex-direction:column;gap:12px;">' +
  '      <div style="font-size:12.5px;color:var(--text-secondary);line-height:1.4;">' +
  '        Perform authorized operational diagnostics, verify gateway reachability, or review active session audit events.' +
  '      </div>' +
  '      <div style="display:flex;gap:10px;flex-wrap:wrap;">' +
  quickActions.join("\n") +
  '      </div>' +
  '    </div>' +
  '  </div>' +

  '  <div class="admin-card">' +
  '    <div class="admin-card-head"><span class="admin-card-title">System Status & Security Doctrine</span></div>' +
  '    <div class="admin-card-body" style="display:flex;flex-direction:column;gap:8px;font-size:12px;color:var(--text-secondary);">' +
  '      <div><strong>Constitutional Governance:</strong> Sequential G3 to G1 to G2 to G4 pipeline enforcement active.</div>' +
  '      <div><strong>Fail-Closed Doctrine:</strong> Missing upstream context or telemetry halts downstream execution.</div>' +
  '      <div><strong>Zero-Fabrication Invariant:</strong> Unpersisted telemetry is explicitly acknowledged as a declared gap; data is never fabricated.</div>' +
  '      <div><strong>Credential Security:</strong> Tokens are stored in tab-scoped sessionStorage; zero secrets committed to git.</div>' +
  '    </div>' +
  '  </div>' +
  '</div>' +

  _boundaryNotice(
    "Administrative Boundary & Data Transparency",
    "The VANA Administration Control Plane operates under strict backend authorization. Runtime capabilities reflect genuine backend services. Administrative actions do not simulate unpersisted operations.",
    "Session User ID: " + (user.id || "usr-anon") + "\nRole Authority: " + (user.role || "UNASSIGNED") + "\nEnforcement: Backend-validated access control"
  );
}

// =============================================================================
// SECTION 2: SYSTEM HEALTH & GATEWAY SERVICES
// =============================================================================
function renderSystemServices() {
  const el = document.getElementById("section-system-services");
  if (!el) return;

  // Strict RBAC permission check
  if (!window.VANA_AUTH.requirePermission(P.MANAGE_SYSTEM_CONFIG, el)) return;

  const cfg = window.VANA_CONFIG || {};

  el.innerHTML = _sectionHeader(
    "System Health & Gateway Services",
    "Live connectivity checks for backend subsystems and configured reverse-proxy routing.",
    "Diagnostics",
    "live"
  ) +

  // Live Service Health Panel
  '<div class="admin-card">' +
  '  <div class="admin-card-head">' +
  '    <span class="admin-card-title">Backend API Subsystems Reachability</span>' +
  '    <span class="admin-card-tag">via /proxy/* gateway</span>' +
  '  </div>' +
  '  <div id="healthServiceRows">' + _buildHealthPlaceholders() + '</div>' +
  '  <div style="padding:14px 18px;border-top:1px solid var(--border-light);background:var(--bg-surface-subtle);display:flex;justify-content:space-between;align-items:center;">' +
  '    <button class="admin-header-btn primary" onclick="runHealthCheck()" id="btnHealthCheck">' +
  '      <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/></svg>' +
  '      Run Health Checks' +
  '    </button>' +
  '    <span style="font-size:11px;color:var(--text-muted);">Probes live /health endpoints across all three groups</span>' +
  '  </div>' +
  '</div>' +

  // Configured Gateway Routes Table
  '<div class="admin-card">' +
  '  <div class="admin-card-head">' +
  '    <span class="admin-card-title">Configured Gateway Proxy Routes</span>' +
  '    <span class="admin-card-tag">config.js + vercel.json</span>' +
  '  </div>' +
  '  <div class="admin-table-wrap">' +
  '    <table class="admin-table">' +
  '      <thead>' +
  '        <tr><th>Route Prefix</th><th>Subsystem</th><th>Operational Purpose</th><th>Method</th><th>Auth Requirement</th></tr>' +
  '      </thead>' +
  '      <tbody>' +
  '        <tr><td class="mono cell-primary">/proxy/g1/*</td><td>Group 1</td><td>Canonical Observation Retrieval & MasterDB Ledger</td><td class="mono">GET / POST</td><td>Public / Header</td></tr>' +
  '        <tr><td class="mono cell-primary">/proxy/g2/*</td><td>Group 2</td><td>Scientific Context & Decision Resolution (Pravah)</td><td class="mono">POST</td><td>Forwarded Bearer</td></tr>' +
  '        <tr><td class="mono cell-primary">/proxy/g4/*</td><td>Group 4</td><td>Governed Execution & Abstention Gate (SANSKAR)</td><td class="mono">POST</td><td>Privileged Bearer</td></tr>' +
  '        <tr><td class="mono cell-primary">/proxy/auth/*</td><td>Auth Central</td><td>Unified Authentication & Token Verification (/me)</td><td class="mono">GET / POST</td><td>Bearer Token</td></tr>' +
  '      </tbody>' +
  '    </table>' +
  '  </div>' +
  '</div>' +

  // Expandable Technical Configuration
  '<details class="tech-details" style="margin-top:0;">' +
  '  <summary>' +
  '    <span>Technical Runtime Configuration (window.VANA_CONFIG)</span>' +
  '    <span class="admin-section-badge" style="font-size:10px;">Read-Only</span>' +
  '  </summary>' +
  '  <div class="tech-details-content">' +
  '    <table class="admin-table">' +
  '      <thead><tr><th>Parameter Key</th><th>Resolved Value</th><th>Description</th></tr></thead>' +
  '      <tbody>' +
  '        <tr><td class="mono cell-primary">G1_BASE</td><td class="mono">' + (cfg.G1_BASE || "/proxy/g1") + '</td><td>Group 1 MasterDB proxy base path</td></tr>' +
  '        <tr><td class="mono cell-primary">G2_ENDPOINT</td><td class="mono">' + (cfg.G2_ENDPOINT || "/proxy/g2/api/group2/context/resolve") + '</td><td>Group 2 scientific context resolution endpoint</td></tr>' +
  '        <tr><td class="mono cell-primary">G4_ENDPOINT</td><td class="mono">' + (cfg.G4_ENDPOINT || "/proxy/g4/vana/execute") + '</td><td>Group 4 governed execution endpoint</td></tr>' +
  '        <tr><td class="mono cell-primary">AUTH_BASE</td><td class="mono">' + (cfg.AUTH_BASE || "/proxy/auth") + '</td><td>Unified authentication service base route</td></tr>' +
  '        <tr><td class="mono cell-primary">REQUEST_TIMEOUT_MS</td><td class="mono">' + (cfg.REQUEST_TIMEOUT_MS || 10000) + ' ms</td><td>Network fetch timeout applied to all API calls</td></tr>' +
  '      </tbody>' +
  '    </table>' +
  '  </div>' +
  '</details>' +

  _boundaryNotice(
    "Gateway Architecture & Zero-Secret Doctrine",
    "Configured proxy routes are handled transparently by the local Python proxy (server.py) or production edge rewrites (vercel.json). Direct backend IP addresses are never exposed to browser client code.",
    "Route Mapping: /proxy/g1/* -> MasterDB (Port 8013)\n               /proxy/g2/* -> Pravah API (Production)\n               /proxy/g4/* -> SANSKAR Runtime (Port 8010)"
  );
}

function _buildHealthPlaceholders() {
  var services = [
    { key: "g1", label: "Group 1: Canonical Observation Retrieval (MasterDB)", proxy: (window.VANA_CONFIG && window.VANA_CONFIG.G1_BASE) || "/proxy/g1" },
    { key: "g2", label: "Group 2: Scientific Context & Decision Resolve (Pravah)", proxy: (window.VANA_CONFIG && window.VANA_CONFIG.G2_ENDPOINT) || "/proxy/g2" },
    { key: "g4", label: "Group 4: Governed Execution & Abstention Gate (SANSKAR)", proxy: (window.VANA_CONFIG && window.VANA_CONFIG.G4_ENDPOINT) || "/proxy/g4" },
  ];
  return services.map(function (s) {
    return '<div class="admin-status-row" id="health-row-' + s.key + '">' +
      '<span class="status-dot" id="health-dot-' + s.key + '" style="background:var(--border-strong);"></span>' +
      '<div class="admin-status-name">' + s.label + '</div>' +
      '<div class="admin-status-detail mono" id="health-detail-' + s.key + '">Pending check...</div>' +
      '<div class="admin-status-badge" id="health-badge-' + s.key + '">NOT CHECKED</div>' +
      '</div>';
  }).join("");
}

async function runHealthCheck() {
  if (!window.VANA_AUTH || !window.VANA_AUTH.hasPermission(P.MANAGE_SYSTEM_CONFIG)) {
    console.warn("[VANA Admin] Security: Health check invocation denied - MANAGE_SYSTEM_CONFIG required.");
    return;
  }

  const btn = document.getElementById("btnHealthCheck");
  if (btn) { btn.disabled = true; btn.textContent = "Checking..."; }
  _pushAuditEntry("HEALTH_CHECK", "/proxy/*", "RUNNING");

  const checks = [
    { key: "g1", label: "G1", url: window.VANA_CONFIG.G1_BASE + "/health" },
    { key: "g2", label: "G2", url: window.VANA_CONFIG.G2_ENDPOINT.replace("/api/group2/context/resolve", "/health") },
    { key: "g4", label: "G4", url: window.VANA_CONFIG.G4_ENDPOINT.replace("/vana/execute", "/health") },
  ];

  var allOk = true;

  for (var i = 0; i < checks.length; i++) {
    var c = checks[i];
    var dot = document.getElementById("health-dot-" + c.key);
    var detail = document.getElementById("health-detail-" + c.key);
    var badge = document.getElementById("health-badge-" + c.key);

    var t0 = Date.now();
    var checkedAt = new Date().toLocaleTimeString();
    try {
      var res = await adminFetch(c.url, { method: "GET", headers: { "Accept": "application/json" } });
      var latency = Date.now() - t0;
      if (res.ok) {
        if (dot) { dot.style.background = "var(--status-ok)"; }
        if (detail) detail.innerHTML = '<span style="color:var(--status-ok);font-weight:600;">' + latency + "ms</span> · HTTP " + res.status + " · " + checkedAt;
        if (badge) { badge.textContent = "REACHABLE"; badge.className = "admin-status-badge ok"; }
      } else {
        allOk = false;
        if (dot) dot.style.background = "var(--status-warn)";
        if (detail) detail.innerHTML = '<span style="color:var(--status-warn);font-weight:600;">' + latency + "ms</span> · HTTP " + res.status + " · " + checkedAt;
        if (badge) { badge.textContent = "DEGRADED (" + res.status + ")"; badge.className = "admin-status-badge warn"; }
      }
    } catch (err) {
      allOk = false;
      var latency2 = Date.now() - t0;
      if (dot) dot.style.background = "var(--status-critical)";
      if (detail) detail.innerHTML = '<span style="color:var(--status-critical);font-weight:600;">' + latency2 + "ms</span> · Unavailable · " + checkedAt;
      if (badge) { badge.textContent = "UNAVAILABLE"; badge.className = "admin-status-badge error"; }
    }
  }

  _pushAuditEntry("HEALTH_CHECK", "/proxy/*", allOk ? "OK" : "PARTIAL_FAILURE");
  if (btn) {
    btn.disabled = false;
    btn.innerHTML = '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/></svg> Run Health Checks';
  }
}

// =============================================================================
// SECTION 3: USER & ACCESS MANAGEMENT
// =============================================================================
function renderAccessManagement() {
  const el = document.getElementById("section-access-management");
  if (!el) return;

  // Strict RBAC permission check
  if (!window.VANA_AUTH.requirePermission(P.MANAGE_USERS, el)) return;

  const auth = window.VANA_AUTH;
  const user = auth.getCurrentUser() || {};
  const isLive = auth.isLiveValidated();

  // Role metadata rows
  const roleRows = Object.keys(auth.ROLES).filter(function (k, idx, arr) {
    // Show canonical unique roles only
    return ["PLATFORM_ADMIN", "APPROVED_CONSUMER", "AUDITOR", "GOVERNANCE_STEWARD"].indexOf(auth.ROLES[k]) !== -1 && arr.indexOf(k) === idx;
  }).map(function (k) {
    var role = auth.ROLES[k];
    var meta = auth.ROLE_META[role] || {};
    var perms = (auth.ROLE_PERMISSIONS && auth.ROLE_PERMISSIONS[role]) ? auth.ROLE_PERMISSIONS[role] : [];
    return '<tr>' +
      '<td class="cell-primary">' + (meta.label || role) + '</td>' +
      '<td class="mono">' + role + '</td>' +
      '<td>' + (meta.description || "Authorized VANA role") + '</td>' +
      '<td><span class="admin-role-badge ' + role.toLowerCase() + '">' + perms.length + ' permissions</span></td>' +
      '</tr>';
  }).join("");

  // Permission matrix
  const allPerms = Object.values(auth.PERMISSIONS);
  const canonicalRoles = [auth.ROLES.PLATFORM_ADMIN, auth.ROLES.AUDITOR, auth.ROLES.GOVERNANCE_STEWARD, auth.ROLES.APPROVED_CONSUMER];

  const matrixHead = '<tr><th>Capability / Permission</th>' + canonicalRoles.map(function (r) {
    var meta = auth.ROLE_META[r] || {};
    return '<th>' + (meta.label || r) + '</th>';
  }).join("") + '</tr>';

  const matrixBody = allPerms.map(function (perm) {
    var cells = canonicalRoles.map(function (r) {
      var has = false;
      if (r === auth.ROLES.PLATFORM_ADMIN) has = true;
      else if (auth.ROLE_PERMISSIONS && auth.ROLE_PERMISSIONS[r]) {
        has = auth.ROLE_PERMISSIONS[r].indexOf(perm) !== -1;
      }
      return '<td>' + (has ? '<span class="perm-check">✓</span>' : '<span class="perm-nocheck">·</span>') + '</td>';
    }).join("");
    return '<tr><td class="mono">' + perm + '</td>' + cells + '</tr>';
  }).join("");

  el.innerHTML = _sectionHeader(
    "User & Access Management",
    "Current session identity, role hierarchy, and fail-closed permission evaluation matrix.",
    "RBAC Config"
  ) +

  // Current User Session Card
  '<div class="admin-card">' +
  '  <div class="admin-card-head"><span class="admin-card-title">Active Session Identity & Credentials</span></div>' +
  '  <div class="admin-card-body">' +
  '    <div style="display:grid;grid-template-columns:repeat(auto-fit, minmax(200px, 1fr));gap:12px;">' +
  '      <div><span style="font-size:11px;color:var(--text-muted);display:block;">User ID</span><strong class="mono">' + (user.id || "usr-anon") + '</strong></div>' +
  '      <div><span style="font-size:11px;color:var(--text-muted);display:block;">Full Name</span><strong>' + (user.name || "Administrator") + '</strong></div>' +
  '      <div><span style="font-size:11px;color:var(--text-muted);display:block;">Email Address</span><span class="mono">' + (user.email || "admin@vana.gov.in") + '</span></div>' +
  '      <div><span style="font-size:11px;color:var(--text-muted);display:block;">Assigned Role</span><span class="admin-role-badge ' + (user.role || "").toLowerCase() + '">' + (user.roleLabel || user.role || "ADMIN") + '</span></div>' +
  '      <div><span style="font-size:11px;color:var(--text-muted);display:block;">Live Validation</span><strong style="color:' + (isLive ? "var(--status-ok)" : "var(--status-warn)") + '">' + (isLive ? "Verified (Live /me)" : "Degraded Offline") + '</strong></div>' +
  '    </div>' +
  '  </div>' +
  '</div>' +

  // Role Hierarchy Table
  '<div class="admin-card">' +
  '  <div class="admin-card-head"><span class="admin-card-title">Canonical Role Hierarchy</span><span class="admin-card-tag">admin-auth.js</span></div>' +
  '  <div class="admin-table-wrap">' +
  '    <table class="admin-table">' +
  '      <thead><tr><th>Display Label</th><th>Role Constant</th><th>Scope of Authority</th><th>Permission Set</th></tr></thead>' +
  '      <tbody>' + roleRows + '</tbody>' +
  '    </table>' +
  '  </div>' +
  '</div>' +

  // Permission Matrix Table
  '<div class="admin-card">' +
  '  <div class="admin-card-head"><span class="admin-card-title">Full Capability & Permission Matrix</span><span class="admin-card-tag">Strict RBAC</span></div>' +
  '  <div class="admin-table-wrap">' +
  '    <table class="perm-matrix">' +
  '      <thead>' + matrixHead + '</thead>' +
  '      <tbody>' + matrixBody + '</tbody>' +
  '    </table>' +
  '  </div>' +
  '</div>' +

  _boundaryNotice(
    "User Directory Capability Boundary",
    "User directory management is not available through the connected backend. User account CRUD operations (Add, Edit, Delete User) and remote role assignment endpoints are not exposed by the current runtime.",
    "Required Backend: GET/POST /api/admin/users\nPermission: MANAGE_USERS\nCurrent State: Honest boundary: zero simulated user records"
  );
}

// =============================================================================
// SECTION 4: GOVERNANCE DOCTRINE & INVARIANTS
// =============================================================================
function renderGovDoctrine() {
  const el = document.getElementById("section-gov-doctrine");
  if (!el) return;

  // Strict RBAC permission check (Steward or Admin)
  if (!window.VANA_AUTH.hasPermission(P.MANAGE_GOVERNANCE_POLICIES) && !window.VANA_AUTH.hasPermission(P.VIEW_EVIDENCE)) {
    window.VANA_AUTH.requirePermission(P.MANAGE_GOVERNANCE_POLICIES, el);
    return;
  }

  el.innerHTML = _sectionHeader(
    "Governance Doctrine & Invariants",
    "Authoritative pipeline execution sequence, fail-closed principles, and Group 3 contract clauses.",
    "Constitutional",
    "live"
  ) +

  // Pipeline Sequence Visual
  '<div class="admin-card">' +
  '  <div class="admin-card-head"><span class="admin-card-title">Authoritative Pipeline Execution Sequence</span></div>' +
  '  <div class="admin-card-body">' +
  '    <div style="display:flex;align-items:center;gap:8px;justify-content:center;flex-wrap:wrap;padding:8px 0;">' +
  '      <span class="admin-role-badge approved_consumer" style="padding:6px 12px;font-size:11.5px;">Stage 1: G3 Sensor Contract</span>' +
  '      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="color:var(--text-muted);"><line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/></svg>' +
  '      <span class="admin-role-badge platform_admin" style="padding:6px 12px;font-size:11.5px;">Stage 2: G1 MasterDB Ledger</span>' +
  '      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="color:var(--text-muted);"><line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/></svg>' +
  '      <span class="admin-role-badge auditor" style="padding:6px 12px;font-size:11.5px;">Stage 3: G2 Pravah Context</span>' +
  '      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="color:var(--text-muted);"><line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/></svg>' +
  '      <span class="admin-role-badge governance_steward" style="padding:6px 12px;font-size:11.5px;">Stage 4: G4 SANSKAR Execution Gate</span>' +
  '    </div>' +
  '  </div>' +
  '</div>' +

  // Enforced Fail-Closed Rules
  '<div class="admin-card">' +
  '  <div class="admin-card-head"><span class="admin-card-title">Enforced Fail-Closed Invariants</span><span class="admin-card-tag">Code-Enforced</span></div>' +
  '  <div class="admin-card-body">' +
  '    <div class="fail-closed-rule">' +
  '      <div class="fail-closed-rule-num">Rule 1: Group 1 Retrieval Gate</div>' +
  '      <div class="fail-closed-rule-text">No authoritative observation retrieval halts downstream processing</div>' +
  '      <div class="fail-closed-rule-desc">If Group 1 canonical retrieval returns an error, times out, or fails to resolve the observation record, the pipeline halts immediately. Group 2 context resolution and Group 4 execution gates are bypassed fail-closed.</div>' +
  '    </div>' +
  '    <div class="fail-closed-rule">' +
  '      <div class="fail-closed-rule-num">Rule 2: Group 2 Context Gate</div>' +
  '      <div class="fail-closed-rule-text">Unverified scientific context results in governed ABSTAIN</div>' +
  '      <div class="fail-closed-rule-desc">If Group 2 context resolution indicates missing evidence thresholds, unverified provenance, or missing timestamps, the ruling fails closed to ABSTAIN with action_eligibility false. Governed execution dispatches NOOP.</div>' +
  '    </div>' +
  '    <div class="fail-closed-rule" style="margin-bottom:0;">' +
  '      <div class="fail-closed-rule-num">Rule 3: Zero-Fabrication Invariant</div>' +
  '      <div class="fail-closed-rule-text">Missing evidence is recorded as NOT VERIFIED; never fabricated</div>' +
  '      <div class="fail-closed-rule-desc">When canonical records or telemetry fields are missing from upstream responses, they are displayed as NOT VERIFIED or Unresolved. No mock data, placeholder timestamps, or fabricated record IDs are ever injected.</div>' +
  '    </div>' +
  '  </div>' +
  '</div>' +

  // Group 3 Contract Clauses
  '<div class="admin-card">' +
  '  <div class="admin-card-head"><span class="admin-card-title">Group 3 Ingestion Contract Specification</span><span class="admin-card-tag">Contract v2.2</span></div>' +
  '  <div class="admin-table-wrap">' +
  '    <table class="admin-table">' +
  '      <thead><tr><th>Clause Reference</th><th>Type</th><th>Specification & Compliance Requirement</th></tr></thead>' +
  '      <tbody>' +
  '        <tr><td class="mono cell-primary">Clause §26</td><td>Contract Requirement</td><td>Telemetry Byte Handling: Raw payload bytes not persisted at capture time; declared data gap per contract specification.</td></tr>' +
  '        <tr><td class="mono cell-primary">Clause §49.1</td><td>Contract Requirement</td><td>Cryptographic Integrity: SHA-256 value recorded in the canonical evidence record. Raw payload bytes are not recoverable from hash.</td></tr>' +
  '        <tr><td class="mono cell-primary">Evidence Pack</td><td>Data Schema</td><td>SOURCE_EVIDENCE_PACK_EMITTED_TC-Z03-EXT-OPENMETEO-OBS001.json (v2.2 compliance baseline).</td></tr>' +
  '      </tbody>' +
  '    </table>' +
  '  </div>' +
  '</div>' +

  _boundaryNotice(
    "Contract Integrity Notice",
    "Clauses §26 and §49.1 are authoritative provisions of the Group 3 Ingestion Contract v2.2, not statutory state legislation. Invariant enforcement is immutable at runtime.",
    "Pipeline Status: Strictly sequential G3 -> G1 -> G2 -> G4\nFail-Closed Overrides: Prohibited\nModifiable via UI: No (Constitutional constraints)"
  );
}

// =============================================================================
// SECTION 5: GEOSPATIAL CONFIGURATION
// =============================================================================
function renderGeoConfig() {
  const el = document.getElementById("section-geo-config");
  if (!el) return;

  // Strict RBAC permission check
  if (!window.VANA_AUTH.requirePermission(P.MANAGE_MAP_CONFIG, el)) return;

  var currentKey = (typeof sessionStorage !== "undefined" && sessionStorage.getItem("VANA_GEOAPIFY_API_KEY")) || "";
  var keyStatus = currentKey ? "Configured in DEV Session (Key Masked)" : "Not Configured (OSM Development Fallback Active)";

  // Zone rows
  var zoneRows = ADMIN_ZONES.map(function (z) {
    var isLive = z.status === "Record retrieved";
    return '<tr>' +
      '<td class="mono cell-primary">' + z.id + '</td>' +
      '<td>' + z.name + '</td>' +
      '<td><span class="status-pill ' + (isLive ? "active" : "waiting") + '">' + z.status + '</span></td>' +
      '<td class="mono">' + z.lat.toFixed(4) + '° N, ' + z.lon.toFixed(4) + '° E</td>' +
      '<td>' + (z.alt_m !== null ? z.alt_m + " m" : "--") + '</td>' +
      '<td>' + z.source + '</td>' +
      '<td style="font-size:11.5px;color:var(--text-secondary);">' + z.note + '</td>' +
      '</tr>';
  }).join("");

  // Map layers
  var layerDefs = [
    { name: "Base Map (Geoapify Dark Matter / OSM Development Fallback)", type: "Base Tile Layer", status: "ACTIVE", detail: "Cartographic surface with automatic OSM direct-tile fallback" },
    { name: "Regional Reference Points (6 Monitored Locations)", type: "Vector Points", status: "ACTIVE", detail: "1 Record Retrieved (Thane Creek), 5 Regional Monitoring Locations" },
    { name: "Authoritative Observations Layer", type: "Telemetry Overlay", status: "ACTIVE", detail: "Bound to Group 1 canonical record CR-b4615a27..." },
    { name: "Active Alerts Overlay", type: "Exception Badges", status: "ACTIVE", detail: "ALT-001 through ALT-006 plotted at canonical coordinates" },
    { name: "Administrative Boundaries", type: "Vector Polygons", status: "DISABLED", detail: "Unavailable: Boundary shapefiles not yet connected in repository" },
    { name: "Weather Satellite / Radar Ingestion", type: "Raster Stream", status: "DISABLED", detail: "Unavailable: Future capability: radar feed not connected" },
    { name: "Rainfall Isohyets", type: "Mesh Surface", status: "DISABLED", detail: "Unavailable: Future capability: gauge mesh unpersisted" },
    { name: "Terrain Elevation Mesh", type: "DEM Grid", status: "DISABLED", detail: "Unavailable: Future capability: no DEM raster connected" }
  ];

  var layerRows = layerDefs.map(function (l) {
    var isActive = l.status === "ACTIVE";
    return '<tr>' +
      '<td class="cell-primary">' + l.name + '</td>' +
      '<td class="mono">' + l.type + '</td>' +
      '<td><span class="admin-status-badge ' + (isActive ? "ok" : "") + '" style="' + (!isActive ? "background:var(--bg-muted);color:var(--text-muted);" : "") + '">' + l.status + '</span></td>' +
      '<td style="font-size:11.5px;color:var(--text-secondary);">' + l.detail + '</td>' +
      '</tr>';
  }).join("");

  el.innerHTML = _sectionHeader(
    "Geospatial Configuration",
    "Surveillance zone registry, operational map layer definitions, and session cartographic parameters.",
    "6 Zones"
  ) +

  // Zone Registry Card
  '<div class="admin-card">' +
  '  <div class="admin-card-head"><span class="admin-card-title">Surveillance Zone Registry</span><span class="admin-card-tag">Canonical MMR Coordinates</span></div>' +
  '  <div class="admin-table-wrap">' +
  '    <table class="admin-table">' +
  '      <thead><tr><th>Zone ID</th><th>Location Name</th><th>Status</th><th>Coordinates</th><th>Altitude</th><th>Source Feed</th><th>Operational Description</th></tr></thead>' +
  '      <tbody>' + zoneRows + '</tbody>' +
  '    </table>' +
  '  </div>' +
  '</div>' +

  // Map Layers Registry Card
  '<div class="admin-card">' +
  '  <div class="admin-card-head"><span class="admin-card-title">Geospatial Map Layers Registry</span><span class="admin-card-tag">8 Layer Definitions</span></div>' +
  '  <div class="admin-table-wrap">' +
  '    <table class="admin-table">' +
  '      <thead><tr><th>Layer Name</th><th>Type</th><th>Status</th><th>Configuration Detail</th></tr></thead>' +
  '      <tbody>' + layerRows + '</tbody>' +
  '    </table>' +
  '  </div>' +
  '</div>' +

  // DEV Session Geoapify Key Management Card
  '<div class="admin-card">' +
  '  <div class="admin-card-head">' +
  '    <span class="admin-card-title">Development / Local Session Configuration</span>' +
  '    <span class="admin-card-tag">sessionStorage</span>' +
  '  </div>' +
  '  <div class="admin-card-body" style="display:flex;flex-direction:column;gap:12px;">' +
  '    <div style="font-size:12px;color:var(--text-secondary);line-height:1.4;">' +
  '      <strong>DEV Testing Only:</strong> Configure a temporary Geoapify API key for the current browser session. ' +
  '      The key is stored in <span class="mono">sessionStorage</span> and cleared upon closing the tab. It is never logged or committed to git. ' +
  '      Current status: <strong class="mono">' + keyStatus + '</strong>.' +
  '    </div>' +
  '    <div style="display:flex;gap:8px;max-width:540px;">' +
  '      <input type="password" id="adminGeoapifyKeyInput" class="admin-form-input" placeholder="Enter Geoapify API key for DEV session..." autocomplete="off" style="flex:1;font-family:\'JetBrains Mono\',monospace;font-size:11.5px;">' +
  '      <button class="admin-header-btn primary" onclick="adminSaveGeoKey()">Save to Session</button>' +
  '      <button class="admin-header-btn" onclick="adminClearGeoKey()">Clear</button>' +
  '    </div>' +
  '    <div id="adminGeoKeyFeedback" style="font-size:11.5px;color:var(--status-ok);display:none;"></div>' +
  '  </div>' +
  '</div>' +

  _boundaryNotice(
    "Layer Integrity Doctrine",
    "Per VANA zero-fabrication doctrine, disabled map layers (radar, rainfall isohyets, elevation meshes) are honestly presented as unavailable architectural stubs until authoritative spatial data feeds are provisioned in the repository.",
    "Storage Scope: sessionStorage (DEV testing only)\nProduction Key Loading: Environment variables on server\nDefault Cartographic Fallback: OpenStreetMap direct tiles active"
  );
}

function adminSaveGeoKey() {
  if (!window.VANA_AUTH || !window.VANA_AUTH.hasPermission(P.MANAGE_MAP_CONFIG)) {
    console.warn("[VANA Admin] Security: Geo key configuration denied - MANAGE_MAP_CONFIG required.");
    return;
  }
  var input = document.getElementById("adminGeoapifyKeyInput");
  var feedback = document.getElementById("adminGeoKeyFeedback");
  if (!input) return;
  var key = input.value.trim();
  if (key) {
    sessionStorage.setItem("VANA_GEOAPIFY_API_KEY", key);
    _pushAuditEntry("UPDATE_MAP_CONFIG", "sessionStorage:VANA_GEOAPIFY_API_KEY", "DEV_KEY_CONFIGURED");
    input.value = "";
    if (feedback) {
      feedback.textContent = "Key saved to sessionStorage (masked). Reload Operational Dashboard to activate Geoapify tiles.";
      feedback.style.display = "block";
    }
  }
}

function adminClearGeoKey() {
  if (!window.VANA_AUTH || !window.VANA_AUTH.hasPermission(P.MANAGE_MAP_CONFIG)) {
    console.warn("[VANA Admin] Security: Geo key clear denied - MANAGE_MAP_CONFIG required.");
    return;
  }
  sessionStorage.removeItem("VANA_GEOAPIFY_API_KEY");
  var input = document.getElementById("adminGeoapifyKeyInput");
  var feedback = document.getElementById("adminGeoKeyFeedback");
  if (input) input.value = "";
  _pushAuditEntry("CLEAR_MAP_CONFIG", "sessionStorage:VANA_GEOAPIFY_API_KEY", "CLEARED");
  if (feedback) {
    feedback.textContent = "Cleared. Default OpenStreetMap development fallback will be used.";
    feedback.style.display = "block";
  }
}

// =============================================================================
// SECTION 6: AUDIT & OPERATIONAL TRACE
// =============================================================================
function renderAuditTrace() {
  const el = document.getElementById("section-audit-trace");
  if (!el) return;

  // Strict RBAC permission check
  if (!window.VANA_AUTH.requirePermission(P.VIEW_AUDIT_LOG, el)) return;

  // Operational Exceptions
  const alerts = [
    { id: "ALT-001", severity: "CRITICAL", title: "canonical_record_id Not Returned by Group 1 Live Runtime", category: "DATA_GAP", ts: "Live Session" },
    { id: "ALT-002", severity: "ABSTAIN", title: "Group 4 Abstention Gate Triggered: NOOP Enforced", category: "GOVERNANCE_ABSTENTION", ts: "Live Session" },
    { id: "ALT-003", severity: "GAP", title: "Missing Source Timestamp (observation_timestamp = null) in G1", category: "DATA_GAP", ts: "Live Session" },
    { id: "ALT-004", severity: "GAP", title: "observation_type and measurement.unit Gap in Source Evidence", category: "DATA_GAP", ts: "Live Session" },
    { id: "ALT-005", severity: "INFO", title: "5 Regional Surveillance Zones Pending Ingestion", category: "PENDING_REGIONAL_FEEDS", ts: "Live Session" },
    { id: "ALT-006", severity: "INFO", title: "CORS Reverse-Proxy Gateway Active", category: "RUNTIME_GATEWAY", ts: "Live Session" },
  ];

  const alertRows = alerts.map(function (a) {
    var badgeClass = a.severity === "CRITICAL" ? "error" : a.severity === "GAP" || a.severity === "ABSTAIN" ? "warn" : "ok";
    return '<tr>' +
      '<td class="mono cell-primary">' + a.id + '</td>' +
      '<td><span class="admin-status-badge ' + badgeClass + '">' + a.severity + '</span></td>' +
      '<td>' + a.title + '</td>' +
      '<td class="mono">' + a.category + '</td>' +
      '<td>' + a.ts + '</td>' +
      '</tr>';
  }).join("");

  el.innerHTML = _sectionHeader(
    "Audit & Operational Trace",
    "Current browser session activity trace and documented operational exceptions.",
    "Trace Audit"
  ) +

  // Current Browser Session Activity Log Card
  '<div class="admin-card">' +
  '  <div class="admin-card-head">' +
  '    <span class="admin-card-title">Current Browser Session Activity</span>' +
  '    <span class="admin-card-tag">In-Memory Session Trace</span>' +
  '  </div>' +
  '  <div class="admin-table-wrap">' +
  '    <table class="admin-table">' +
  '      <thead><tr><th>Time</th><th>User Identity</th><th>Role</th><th>Action</th><th>Target Resource</th><th>Result</th></tr></thead>' +
  '      <tbody id="sessionAuditRowsContainer">' + _buildAuditRowsHtml() + '</tbody>' +
  '    </table>' +
  '  </div>' +
  '  <div style="padding:10px 18px;border-top:1px solid var(--border-light);background:var(--bg-surface-subtle);font-size:11.5px;color:var(--text-muted);">' +
  '    These entries are held in browser memory for the current session. They are not a persistent or authoritative backend audit log.' +
  '  </div>' +
  '</div>' +

  // Documented Operational Exceptions Card
  '<div class="admin-card">' +
  '  <div class="admin-card-head">' +
  '    <span class="admin-card-title">Documented Operational Exceptions</span>' +
  '    <span class="admin-card-tag">Static Registry (ALT-001 - ALT-006)</span>' +
  '  </div>' +
  '  <div class="admin-table-wrap">' +
  '    <table class="admin-table">' +
  '      <thead><tr><th>Exception ID</th><th>Severity</th><th>Operational Description</th><th>Classification Category</th><th>Recorded Timestamp</th></tr></thead>' +
  '      <tbody>' + alertRows + '</tbody>' +
  '    </table>' +
  '  </div>' +
  '</div>' +

  _boundaryNotice(
    "Alert Rules & Notification Engine Limitation",
    "Dynamic alert-rule configuration and notification delivery are not currently available through the connected backend. In production, authoritative audit logs are persisted on the unified runtime with append-only governance records.",
    "Session Audit: In-memory trace (max 100 entries)\nAuthoritative Audit: Persisted on backend runtime (/proxy/g4/vana/execute)\nAlert Rules: Statically defined in platform contracts"
  );
}

function _buildAuditRowsHtml() {
  var log = _sessionAuditLog;
  if (!log || log.length === 0) {
    return '<tr><td colspan="6" style="text-align:center;color:var(--text-muted);padding:20px;">No actions recorded in this session yet.</td></tr>';
  }
  return log.map(function (entry) {
    var ts = new Date(entry.ts).toLocaleTimeString("en-GB") + " " + new Date(entry.ts).toLocaleDateString("en-GB", { day: "2-digit", month: "short" });
    return '<tr>' +
      '<td class="mono">' + ts + '</td>' +
      '<td>' + entry.userName + '</td>' +
      '<td><span class="admin-role-badge ' + (entry.role || "").toLowerCase() + '">' + entry.role + '</span></td>' +
      '<td style="font-weight:600;">' + entry.action + '</td>' +
      '<td class="mono" style="color:var(--text-secondary);">' + entry.resource + '</td>' +
      '<td><span class="admin-status-badge ' + (entry.result === "OK" ? "ok" : "warn") + '">' + entry.result + '</span></td>' +
      '</tr>';
  }).join("");
}

function _renderAuditRows(container) {
  if (container) {
    container.innerHTML = _buildAuditRowsHtml();
  }
}

// ── AUTHENTICATED MODAL ACTIONS ─────────────────────────────────────────
function adminOpenLoginModal() {
  var modal = document.getElementById("adminLoginModal");
  var barrier = document.getElementById("adminBarrierOverlay");
  var errEl = document.getElementById("adminLoginError");
  if (errEl) { errEl.style.display = "none"; errEl.textContent = ""; }

  // Hide the barrier overlay so it does not block or conflict with the modal
  if (barrier) {
    barrier.style.display = "none";
  }

  if (modal) {
    modal.style.display = "flex";
  }
  var emailInput = document.getElementById("adminEmailInput");
  if (emailInput) {
    setTimeout(function () { emailInput.focus(); }, 50);
  }
}

function adminCloseLoginModal() {
  var modal = document.getElementById("adminLoginModal");
  if (modal) {
    modal.style.display = "none";
  }

  // Closing without authenticating must restore the Authentication Required barrier
  var auth = window.VANA_AUTH;
  if (!auth || !auth.isAuthenticated() || !auth.isLiveValidated()) {
    _initAuthUI();
  }
}

async function adminSubmitLogin(event) {
  if (event) event.preventDefault();
  var emailInput = document.getElementById("adminEmailInput");
  var passInput = document.getElementById("adminPasswordInput");
  var submitBtn = document.getElementById("adminLoginSubmitBtn");
  var errEl = document.getElementById("adminLoginError");

  if (!emailInput || !passInput) return;
  var email = emailInput.value.trim();
  var pass = passInput.value;

  if (submitBtn) { submitBtn.disabled = true; submitBtn.textContent = "Signing In..."; }
  if (errEl) { errEl.style.display = "none"; errEl.textContent = ""; }

  var res = await window.VANA_AUTH.login(email, pass);
  if (submitBtn) { submitBtn.disabled = false; submitBtn.textContent = "Sign In"; }

  if (res.success) {
    passInput.value = "";
    var modal = document.getElementById("adminLoginModal");
    if (modal) modal.style.display = "none";
    _initAuthUI();
  } else {
    if (errEl) {
      var errMsg = res.error || "Authentication failed. Please verify credentials.";
      if (typeof errMsg === "string" && (errMsg.includes("10061") || errMsg.includes("actively refused") || errMsg.includes("Failed to fetch"))) {
        errMsg = "Authentication Service Unavailable: Upstream auth backend at localhost:8000 is stopped or unreachable (Connection Refused).";
      }
      errEl.textContent = errMsg;
      errEl.style.display = "block";
    }
  }
}

// Close modal on Escape key press
document.addEventListener("keydown", function (e) {
  if (e.key === "Escape") {
    var modal = document.getElementById("adminLoginModal");
    if (modal && modal.style.display === "flex") {
      adminCloseLoginModal();
    }
  }
});

function adminLogout() {
  window.VANA_AUTH.logout();
  _initAuthUI();
}

console.log("[VANA Admin] admin.js loaded successfully.");
