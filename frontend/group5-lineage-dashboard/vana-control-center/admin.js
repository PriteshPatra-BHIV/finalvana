/**
 * VANA Control Center — Admin Control Plane UI Logic
 * ===================================================
 * Depends on: config.js (window.VANA_CONFIG) and admin-auth.js (window.VANA_AUTH)
 * Must be loaded after both.
 *
 * Responsibilities:
 *  - Admin section navigation and rendering
 *  - Permission guards on every section
 *  - System Health checks via vanaFetch() (mirrors app.js, uses VANA_CONFIG)
 *  - DEV role switcher integration
 *  - Session-scoped audit log
 *
 * SAFETY INVARIANTS (never violated here):
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

// Real VANA monitoring zones (from VANA architecture — same data as app.js)
const ADMIN_ZONES = [
  { id: "TC-Z03-EXT-OPENMETEO-OBS001", name: "Thane Creek",  status: "CONFIRMED_LIVE",    lat: 19.1288, lon: 72.9421, alt_m: 4.0,   source: "Open-Meteo.com", license: "CC-BY 4.0" },
  { id: "MU-Z01-EXT-OPENMETEO-OBS001", name: "Mumbai",       status: "PENDING_UPSTREAM",  lat: 19.0760, lon: 72.8777, alt_m: null, source: "Pending",        license: "Pending" },
  { id: "NM-Z01-EXT-OPENMETEO-OBS001", name: "Navi Mumbai",  status: "PENDING_UPSTREAM",  lat: 19.0330, lon: 73.0297, alt_m: null, source: "Pending",        license: "Pending" },
  { id: "VS-Z01-EXT-OPENMETEO-OBS001", name: "Vasai",        status: "PENDING_UPSTREAM",  lat: 19.4919, lon: 72.8054, alt_m: null, source: "Pending",        license: "Pending" },
  { id: "THN-Z01-EXT-OPENMETEO-OBS001",name: "Thane",        status: "PENDING_UPSTREAM",  lat: 19.2183, lon: 72.9781, alt_m: null, source: "Pending",        license: "Pending" },
  { id: "MV-Z01-EXT-OPENMETEO-OBS001", name: "Maval",        status: "PENDING_UPSTREAM",  lat: 18.7500, lon: 73.5000, alt_m: null, source: "Pending",        license: "Pending" },
];

// ── SESSION AUDIT LOG ────────────────────────────────────────────────────
// Records admin actions for this session only. NOT persisted.
// When a real audit backend exists, replace _pushAuditEntry() to POST to it.
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
  // Keep last 100 entries in memory
  if (_sessionAuditLog.length > 100) _sessionAuditLog.length = 100;
}

// ── ADMIN FETCH HELPER ──────────────────────────────────────────────────
// Mirrors vanaFetch() from app.js. Defined here so admin.html doesn't need app.js.
async function adminFetch(url, options) {
  const timeoutMs = (window.VANA_CONFIG && window.VANA_CONFIG.REQUEST_TIMEOUT_MS) || 10000;
  const controller = new AbortController();
  const timerId = setTimeout(function () { controller.abort(); }, timeoutMs);
  options = options || {};
  try {
    const response = await fetch(url, Object.assign({}, options, { signal: controller.signal }));
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
document.addEventListener("DOMContentLoaded", function () {
  console.log("[VANA Admin] Initializing Administration Control Plane...");
  _initAuthUI();
  _renderAllSections();
  adminNav("system-health", document.getElementById("nav-system-health"));
  _pushAuditEntry("ADMIN_SESSION_START", "admin.html", "OK");
});

function _initAuthUI() {
  const auth = window.VANA_AUTH;
  const user = auth.getCurrentUser();

  // Update role badge in header
  const badge = document.getElementById("adminRoleBadge");
  const label = document.getElementById("adminUserLabel");
  if (badge && user) {
    badge.textContent = user.roleLabel || user.role;
    badge.className = "admin-role-badge " + user.role;
  }
  if (label && user) {
    label.textContent = user.isDev ? "[DEV session]" : user.name;
  }

  // Dev banner visibility
  const banner = document.getElementById("devModeBanner");
  if (banner) banner.style.display = auth.DEV_MODE ? "flex" : "none";

  // Sync dev role selector to current session role
  const sel = document.getElementById("devRoleSelect");
  if (sel && auth.DEV_MODE && user) sel.value = user.role;

  // Re-render all sections when role changes
  auth.onAuthChange(function (newUser) {
    if (badge) { badge.textContent = newUser.roleLabel || newUser.role; badge.className = "admin-role-badge " + newUser.role; }
    if (label) label.textContent = newUser.isDev ? "[DEV session]" : newUser.name;
    _renderAllSections();
  });
}

function _renderAllSections() {
  renderSystemHealth();
  renderSystemServices();
  renderSystemConfig();
  renderAccessUsers();
  renderAccessRoles();
  renderAccessPermissions();
  renderGeoZones();
  renderGeoLayers();
  renderGeoConfig();
  renderGovPolicies();
  renderGovFailClosed();
  renderGovEvidence();
  renderOpsAlerts();
  renderOpsAlertRules();
  renderOpsNotifications();
  renderAuditActivity();
}

// ── NAVIGATION ──────────────────────────────────────────────────────────
function adminNav(sectionKey, navEl) {
  // Deactivate all sections and nav items
  document.querySelectorAll(".admin-section").forEach(function (s) { s.classList.remove("active"); });
  document.querySelectorAll(".admin-nav-item").forEach(function (n) { n.classList.remove("active"); });

  const section = document.getElementById("section-" + sectionKey);
  if (section) section.classList.add("active");
  if (navEl) navEl.classList.add("active");

  _pushAuditEntry("NAVIGATE", "admin/" + sectionKey, "OK");
}

function adminSetDevRole(role) {
  window.VANA_AUTH.setDevRole(role);
  _pushAuditEntry("DEV_ROLE_CHANGE", role, "OK");
  // Re-render audit so the new entry is visible immediately if on that section
  renderAuditActivity();
}

// ── SECTION HELPER ──────────────────────────────────────────────────────
function _sectionHeader(title, desc, badge, badgeClass) {
  var badgeHtml = badge
    ? '<div class="admin-section-badge ' + (badgeClass || "") + '">' + badge + '</div>'
    : "";
  return '<div class="admin-section-header"><div class="admin-section-title-group"><div class="admin-section-title">' + title + '</div><div class="admin-section-desc">' + desc + '</div></div>' + badgeHtml + '</div>';
}

function _boundaryNotice(title, text, code) {
  var codeHtml = code ? '<div class="admin-boundary-notice-code">' + code + '</div>' : "";
  return '<div class="admin-boundary-notice"><div class="admin-boundary-notice-icon"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg></div><div class="admin-boundary-notice-body"><div class="admin-boundary-notice-title">' + title + '</div><div class="admin-boundary-notice-text">' + text + '</div>' + codeHtml + '</div></div>';
}

// =============================================================================
// SYSTEM — HEALTH
// =============================================================================
async function renderSystemHealth() {
  const el = document.getElementById("section-system-health");
  if (!el) return;

  // Requires VIEW_DASHBOARD at minimum — all roles have this
  el.innerHTML = _sectionHeader(
    "System Health",
    "Live connectivity check for Group 1, Group 2, and Group 4 backend services using the existing /proxy/* gateway.",
    "Live Check",
    "live"
  ) + '<div id="healthServiceRows">' + _buildHealthPlaceholders() + '</div><div style="margin-top:12px"><button class="admin-btn primary" onclick="runHealthCheck()" id="btnHealthCheck"><svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/></svg> Run Health Check</button></div>';

  // Run check immediately on load
  runHealthCheck();
}

function _buildHealthPlaceholders() {
  var services = [
    { key: "g1", label: "Group 1 — Canonical Observation Retrieval", proxy: window.VANA_CONFIG.G1_BASE },
    { key: "g2", label: "Group 2 — Scientific Context & Decision Resolve", proxy: window.VANA_CONFIG.G2_ENDPOINT },
    { key: "g4", label: "Group 4 — Governed Execution & Abstention Gate", proxy: window.VANA_CONFIG.G4_ENDPOINT },
  ];
  return '<div class="admin-card"><div class="admin-card-head"><span class="admin-card-title">Backend API Services</span><span class="admin-card-tag">via /proxy/* gateway</span></div>' +
    services.map(function (s) {
      return '<div class="admin-status-row" id="health-row-' + s.key + '">' +
        '<div class="admin-status-dot pending" id="health-dot-' + s.key + '"></div>' +
        '<div class="admin-status-name">' + s.label + '</div>' +
        '<div class="admin-status-detail mono" id="health-detail-' + s.key + '">Checking...</div>' +
        '<div class="admin-status-badge" id="health-badge-' + s.key + '">—</div>' +
        '</div>';
    }).join("") + '</div>';
}

async function runHealthCheck() {
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
    try {
      var res = await adminFetch(c.url, { method: "GET", headers: { "Accept": "application/json" } });
      var latency = Date.now() - t0;
      if (res.ok || res.status === 404 || res.status === 405) {
        // 404/405 means server responded — it's reachable even if /health doesn't exist
        var statusLabel = res.ok ? "ONLINE" : "REACHABLE (" + res.status + ")";
        if (dot) { dot.className = "admin-status-dot ok"; }
        if (detail) detail.innerHTML = '<span class="health-latency">' + latency + "ms</span> · HTTP " + res.status;
        if (badge) { badge.textContent = statusLabel; badge.className = "admin-status-badge ok"; }
      } else {
        allOk = false;
        if (dot) dot.className = "admin-status-dot warn";
        if (detail) detail.textContent = "HTTP " + res.status + " · " + latency + "ms";
        if (badge) { badge.textContent = "DEGRADED"; badge.className = "admin-status-badge warn"; }
      }
    } catch (err) {
      allOk = false;
      var latency2 = Date.now() - t0;
      if (dot) dot.className = "admin-status-dot error";
      if (detail) detail.textContent = err.message.substring(0, 60);
      if (badge) { badge.textContent = "UNREACHABLE"; badge.className = "admin-status-badge error"; }
    }
  }

  _pushAuditEntry("HEALTH_CHECK", "/proxy/*", allOk ? "OK" : "PARTIAL_FAILURE");
  if (btn) {
    btn.disabled = false;
    btn.innerHTML = '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/></svg> Run Health Check';
  }
}

// =============================================================================
// SYSTEM — BACKEND SERVICES
// =============================================================================
function renderSystemServices() {
  const el = document.getElementById("section-system-services");
  if (!el) return;

  el.innerHTML = _sectionHeader(
    "Backend Services",
    "Configured proxy targets. Routes are defined in config.js and vercel.json. Read-only.",
    "Read-only"
  ) + '<div class="admin-card"><div class="admin-card-head"><span class="admin-card-title">Active Proxy Routes</span><span class="admin-card-tag">config.js + vercel.json</span></div>' +
    '<table class="admin-table"><thead><tr><th>Route</th><th>Group</th><th>Purpose</th><th>Method</th></tr></thead><tbody>' +
    '<tr><td class="mono cell-primary">/proxy/g1/*</td><td>Group 1</td><td>Canonical Observation Retrieval (Observations API)</td><td class="mono">GET</td></tr>' +
    '<tr><td class="mono cell-primary">/proxy/g2/*</td><td>Group 2</td><td>Scientific Context &amp; Decision Resolve</td><td class="mono">POST</td></tr>' +
    '<tr><td class="mono cell-primary">/proxy/g4/*</td><td>Group 4</td><td>Governed Execution &amp; Abstention Gate</td><td class="mono">POST</td></tr>' +
    '</tbody></table></div>' +
    _boundaryNotice(
      "Production Proxy Configuration",
      "In production (Vercel), proxy rewrites are defined in vercel.json. Locally, the Python server.py handles the same routes. No backend IPs appear in frontend code.",
      "vercel.json → rewrites: /proxy/g1/* → G1 backend\n                          /proxy/g2/* → G2 backend\n                          /proxy/g4/* → G4 backend"
    );
}

// =============================================================================
// SYSTEM — CONFIGURATION
// =============================================================================
function renderSystemConfig() {
  const el = document.getElementById("section-system-config");
  if (!el) return;

  if (!window.VANA_AUTH.requirePermission(P.MANAGE_SYSTEM_CONFIG, null)) {
    // Still show read-only view of config for non-admins
  }

  var cfg = window.VANA_CONFIG;
  el.innerHTML = _sectionHeader(
    "Configuration",
    "Current VANA_CONFIG values loaded from config.js. Edit config.js to change these values. No restart required — reload the page.",
    window.VANA_AUTH.hasPermission(P.MANAGE_SYSTEM_CONFIG) ? "View" : "Read-only"
  ) + '<div class="admin-card"><div class="admin-card-head"><span class="admin-card-title">VANA_CONFIG (window.VANA_CONFIG)</span><span class="admin-card-tag">config.js</span></div>' +
    '<table class="admin-table"><thead><tr><th>Key</th><th>Value</th><th>Description</th></tr></thead><tbody>' +
    '<tr><td class="mono cell-primary">G1_BASE</td><td class="mono">' + cfg.G1_BASE + '</td><td>Group 1 proxy base path</td></tr>' +
    '<tr><td class="mono cell-primary">G2_ENDPOINT</td><td class="mono">' + cfg.G2_ENDPOINT + '</td><td>Group 2 context resolve endpoint</td></tr>' +
    '<tr><td class="mono cell-primary">G4_ENDPOINT</td><td class="mono">' + cfg.G4_ENDPOINT + '</td><td>Group 4 execute endpoint</td></tr>' +
    '<tr><td class="mono cell-primary">REQUEST_TIMEOUT_MS</td><td class="mono">' + cfg.REQUEST_TIMEOUT_MS + '</td><td>Fetch timeout for all API calls</td></tr>' +
    '</tbody></table></div>' +
    _boundaryNotice(
      "Configuration Management",
      "In this iteration, configuration is managed by editing config.js. Future iterations should connect this section to a backend configuration API (POST /api/admin/config) protected by the MANAGE_SYSTEM_CONFIG permission.",
      "Required backend: POST /api/admin/config → { key, value }\nRequired permission: MANAGE_SYSTEM_CONFIG\nCurrently: read-only display"
    );
}

// =============================================================================
// ACCESS CONTROL — USERS
// =============================================================================
function renderAccessUsers() {
  const el = document.getElementById("section-access-users");
  if (!el) return;

  el.innerHTML = _sectionHeader(
    "Users",
    "User account management. Requires MANAGE_USERS permission and a backend user directory.",
    "Administrator only"
  );

  if (!window.VANA_AUTH.requirePermission(P.MANAGE_USERS, null)) {
    el.innerHTML += window.VANA_AUTH._getAccessDeniedHtml
      ? window.VANA_AUTH._getAccessDeniedHtml(P.MANAGE_USERS)
      : '<div class="admin-denied-state"><div class="admin-denied-icon"><svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="12" cy="12" r="10"/><line x1="4.93" y1="4.93" x2="19.07" y2="19.07"/></svg></div><div class="admin-denied-title">Access Denied</div><div class="admin-denied-msg">Your current role does not have the <span class="mono">MANAGE_USERS</span> permission.</div></div>';
    return;
  }

  el.innerHTML += _boundaryNotice(
    "Backend Integration Required",
    "User management requires a backend user directory (e.g., /api/admin/users). No user store exists in this version. The UI below shows the integration boundary — wire it to your backend.",
    "Required: GET  /api/admin/users → [{ id, name, email, role }]\n          POST /api/admin/users → create user\n          PUT  /api/admin/users/:id → update role\n          DEL  /api/admin/users/:id → deactivate"
  ) + '<div class="admin-card"><div class="admin-card-head"><span class="admin-card-title">User Directory</span><span class="admin-card-tag">Backend pending</span></div>' +
    '<table class="admin-table"><thead><tr><th>User ID</th><th>Name</th><th>Role</th><th>Status</th></tr></thead><tbody>' +
    '<tr><td class="mono" colspan="4" style="text-align:center;color:var(--text-muted);padding:20px">No user directory connected. Implement /api/admin/users backend endpoint to populate this table.</td></tr>' +
    '</tbody></table></div>';
}

// =============================================================================
// ACCESS CONTROL — ROLES
// =============================================================================
function renderAccessRoles() {
  const el = document.getElementById("section-access-roles");
  if (!el) return;

  if (!window.VANA_AUTH.requirePermission(P.MANAGE_ROLES, el)) return;

  var auth = window.VANA_AUTH;
  var roleRows = Object.keys(auth.ROLES).map(function (k) {
    var role = auth.ROLES[k];
    var meta = auth.ROLE_META[role];
    var permCount = auth.ROLE_PERMISSIONS[role] ? auth.ROLE_PERMISSIONS[role].length : 0;
    return '<tr><td class="cell-primary">' + meta.label + '</td><td class="mono">' + role + '</td><td>' + meta.description + '</td><td><span class="admin-role-badge ' + role + '">' + permCount + ' permissions</span></td></tr>';
  }).join("");

  el.innerHTML = _sectionHeader("Roles", "The four VANA roles and their descriptions. Role assignment requires a backend user directory.", "View only") +
    '<div class="admin-card"><div class="admin-card-head"><span class="admin-card-title">Role Hierarchy</span><span class="admin-card-tag">Defined in admin-auth.js</span></div>' +
    '<table class="admin-table"><thead><tr><th>Label</th><th>Role Key</th><th>Description</th><th>Permission Set</th></tr></thead><tbody>' + roleRows + '</tbody></table></div>' +
    _boundaryNotice(
      "Role Assignment",
      "In production, role assignment is managed by the backend (PATCH /api/admin/users/:id/role). The admin-auth.js module resolves the user's role from the auth provider.",
      "Required: PATCH /api/admin/users/:id/role → { role }\nPermission: MANAGE_ROLES\nCurrently: roles are read-only display"
    );
}

// =============================================================================
// ACCESS CONTROL — PERMISSIONS
// =============================================================================
function renderAccessPermissions() {
  const el = document.getElementById("section-access-permissions");
  if (!el) return;

  if (!window.VANA_AUTH.requirePermission(P.MANAGE_ROLES, el)) return;

  var auth = window.VANA_AUTH;
  var allPerms = Object.values(auth.PERMISSIONS);
  var roles = [auth.ROLES.VIEWER, auth.ROLES.OPERATOR, auth.ROLES.ANALYST, auth.ROLES.ADMINISTRATOR];

  var headerRow = "<tr><th>Permission</th>" + roles.map(function (r) {
    return '<th>' + auth.ROLE_META[r].label + '</th>';
  }).join("") + "</tr>";

  var bodyRows = allPerms.map(function (perm) {
    var cells = roles.map(function (r) {
      var has = auth.ROLE_PERMISSIONS[r] && auth.ROLE_PERMISSIONS[r].indexOf(perm) !== -1;
      return '<td>' + (has ? '<span class="perm-check">✓</span>' : '<span class="perm-nocheck">·</span>') + '</td>';
    }).join("");
    return '<tr><td class="mono">' + perm + '</td>' + cells + '</tr>';
  }).join("");

  el.innerHTML = _sectionHeader("Permissions", "Full permission matrix showing which roles have which capabilities.", "View only") +
    '<div class="admin-card"><table class="perm-matrix"><thead>' + headerRow + '</thead><tbody>' + bodyRows + '</tbody></table></div>';
}

// =============================================================================
// GEOSPATIAL — MONITORING ZONES
// =============================================================================
function renderGeoZones() {
  const el = document.getElementById("section-geo-zones");
  if (!el) return;

  if (!window.VANA_AUTH.requirePermission(P.MANAGE_MAP_CONFIG, el)) return;

  var rows = ADMIN_ZONES.map(function (z) {
    var isLive = z.status === "CONFIRMED_LIVE";
    return '<tr>' +
      '<td class="mono cell-primary">' + z.id + '</td>' +
      '<td>' + z.name + '</td>' +
      '<td><span class="' + (isLive ? "zone-status-live" : "zone-status-pending") + '">' + z.status + '</span></td>' +
      '<td class="mono">' + z.lat.toFixed(4) + ', ' + z.lon.toFixed(4) + '</td>' +
      '<td>' + (z.alt_m !== null ? z.alt_m + " m" : "—") + '</td>' +
      '<td>' + z.source + '</td>' +
      '<td>' + z.license + '</td>' +
      '</tr>';
  }).join("");

  el.innerHTML = _sectionHeader(
    "Monitoring Zones",
    "The 6 VANA environmental surveillance zones. 1 confirmed live (Thane Creek), 5 pending upstream ingestion.",
    "6 Zones"
  ) + '<div class="admin-card"><div class="admin-card-head"><span class="admin-card-title">Zone Registry</span><span class="admin-card-tag">Real VANA data</span></div>' +
    '<div style="overflow-x:auto"><table class="admin-table"><thead><tr><th>Zone ID</th><th>Name</th><th>Status</th><th>Coordinates</th><th>Altitude</th><th>Source</th><th>License</th></tr></thead><tbody>' + rows + '</tbody></table></div></div>' +
    _boundaryNotice(
      "Zone Configuration Management",
      "Zone metadata is currently defined in admin.js and app.js (shared static data). In production, zone configuration should be managed via a backend API and loaded dynamically.",
      "Required: GET  /api/admin/zones → [zone objects]\n          PATCH /api/admin/zones/:id → update zone metadata\nPermission: MANAGE_MAP_CONFIG"
    );
}

// =============================================================================
// =============================================================================
// GEOSPATIAL — MAP LAYERS
// =============================================================================
function renderGeoLayers() {
  const el = document.getElementById("section-geo-layers");
  if (!el) return;
  if (!window.VANA_AUTH.requirePermission(P.MANAGE_MAP_CONFIG, el)) return;

  var layerDefs = [
    { name: "Base Map (Geoapify Production / OSM Development Fallback)", type: "Base Tile Layer", status: "ACTIVE", detail: "Geoapify Dark Matter / OpenStreetMap fallback" },
    { name: "Regional Reference Points", type: "Vector Points (6)", status: "ACTIVE", detail: "1 Confirmed Live (Thane Creek), 5 Regional Reference Locations" },
    { name: "Authoritative Observations", type: "Telemetry Overlay", status: "ACTIVE", detail: "Bound to Group 1 canonical record CR-b4615a27..." },
    { name: "Active Alerts Overlay", type: "Exception Badges", status: "ACTIVE", detail: "ALT-001 through ALT-004 plotted at verified coordinates" },
    { name: "Administrative Boundaries", type: "Vector Polygons", status: "DISABLED", detail: "Unavailable: No authoritative boundary shapefiles in repository" },
    { name: "Weather Satellite / Radar", type: "Raster Ingestion", status: "DISABLED", detail: "Unavailable: Future capability — no authoritative radar feed connected" },
    { name: "Rainfall Isohyets", type: "Gauge Mesh Surface", status: "DISABLED", detail: "Unavailable: Future capability — gauge mesh unpersisted" },
    { name: "Terrain Elevation Mesh", type: "DEM Vector Grid", status: "DISABLED", detail: "Unavailable: Future capability — no DEM raster connected" }
  ];

  var rows = layerDefs.map(function (l) {
    var isActive = l.status === "ACTIVE";
    return '<tr>' +
      '<td class="cell-primary">' + l.name + '</td>' +
      '<td class="mono">' + l.type + '</td>' +
      '<td><span class="' + (isActive ? 'admin-status-badge ok' : 'admin-status-badge') + '" style="' + (!isActive ? 'background:rgba(148,163,184,0.1);color:var(--text-muted)' : '') + '">' + l.status + '</span></td>' +
      '<td>' + l.detail + '</td>' +
      '</tr>';
  }).join("");

  el.innerHTML = _sectionHeader("Map Layers", "Operational layers in the VANA Geospatial Control Map. Architectural stubs remain honestly disabled.", "8 Layers") +
    '<div class="admin-card"><div class="admin-card-head"><span class="admin-card-title">Geospatial Layer Registry</span><span class="admin-card-tag">VanaGeoEngine</span></div>' +
    '<div style="overflow-x:auto"><table class="admin-table"><thead><tr><th>Layer Name</th><th>Type</th><th>Status</th><th>Description</th></tr></thead><tbody>' + rows + '</tbody></table></div></div>' +
    _boundaryNotice(
      "Layer Integrity Doctrine",
      "Per VANA zero-fabrication constitutional doctrine, future layers (boundaries, radar, isohyets) are disabled until authoritative data sources exist in the repository. Reference locations do not imply active monitoring.",
      "Controlled by: VanaGeoData GeoJSON FeatureCollections\nPermission: MANAGE_MAP_CONFIG"
    );
}

// =============================================================================
// GEOSPATIAL — GEOGRAPHIC CONFIG
// =============================================================================
function renderGeoConfig() {
  const el = document.getElementById("section-geo-config");
  if (!el) return;
  if (!window.VANA_AUTH.requirePermission(P.MANAGE_MAP_CONFIG, el)) return;

  var currentKey = (typeof sessionStorage !== "undefined" && sessionStorage.getItem("VANA_GEOAPIFY_API_KEY")) || "";
  var keyStatus = currentKey ? "Configured in DEV Session (Key Masked)" : "Not Configured (OSM Development Fallback Active)";

  el.innerHTML = _sectionHeader("Geographic Configuration", "Tile provider, coordinate system, projection, and session API key management.", "Config") +
    '<div class="admin-card"><div class="admin-card-head"><span class="admin-card-title">Geospatial Engine Parameters</span><span class="admin-card-tag">VanaGeoConfig</span></div>' +
    '<table class="admin-table"><thead><tr><th>Parameter</th><th>Value</th><th>Status</th></tr></thead><tbody>' +
    '<tr><td>Map Framework</td><td class="mono">Leaflet 1.9.4</td><td><span class="admin-status-badge ok">ACTIVE</span></td></tr>' +
    '<tr><td>Primary Tile Provider</td><td class="mono">Geoapify (OpenStreetMap-derived)</td><td><span class="admin-status-badge ok">CONFIGURED</span></td></tr>' +
    '<tr><td>Development Fallback</td><td class="mono">OpenStreetMap Direct Tiles</td><td><span class="admin-status-badge ok">READY</span></td></tr>' +
    '<tr><td>Tile Style</td><td class="mono">dark-matter-dark-grey</td><td>Default Dark Mode</td></tr>' +
    '<tr><td>Center Coordinates</td><td class="mono">19.1500° N, 73.0000° E</td><td>MMR Surveillance Center</td></tr>' +
    '<tr><td>Default Zoom</td><td class="mono">9.5 (Min: 7, Max: 18)</td><td>Fixed Bounds</td></tr>' +
    '<tr><td>Projection</td><td class="mono">EPSG:4326 (WGS 84 Web Mercator)</td><td>Standard Cartographic</td></tr>' +
    '<tr><td>Geoapify API Key</td><td class="mono">' + keyStatus + '</td><td>' + (currentKey ? '<span class="admin-status-badge ok">DEV KEY SET</span>' : '<span class="admin-status-badge">FALLBACK</span>') + '</td></tr>' +
    '</tbody></table></div>' +

    '<div class="admin-card" style="margin-top:16px"><div class="admin-card-head"><span class="admin-card-title">DEV Session Geoapify Key (Testing Only)</span><span class="admin-card-tag">DEV ONLY</span></div>' +
    '<div style="padding:14px;display:flex;flex-direction:column;gap:10px">' +
      '<div style="font-size:11.5px;color:var(--text-secondary);line-height:1.4"><strong>DEV Testing Only:</strong> You can simulate a Geoapify API key for the current browser session. It is stored in <span class="mono">sessionStorage</span> and cleared upon closing the tab. The key is never displayed, logged, or committed to git. In production, configure credentials via server-side environment variables with domain/referrer restrictions enabled on Geoapify.</div>' +
      '<div style="display:flex;gap:8px;max-width:540px">' +
        '<input type="password" id="adminGeoapifyKeyInput" class="admin-input" placeholder="Enter Geoapify API Key (DEV session only)..." autocomplete="off" style="flex:1;font-family:\'JetBrains Mono\',monospace;font-size:11px;padding:6px 10px;background:var(--bg-surface);border:1px solid var(--border-strong);border-radius:var(--radius-sm);color:var(--text-primary)">' +
        '<button class="admin-btn primary" onclick="adminSaveGeoKey()" style="padding:6px 12px;font-size:11px">Save to Session</button>' +
        '<button class="admin-btn secondary" onclick="adminClearGeoKey()" style="padding:6px 12px;font-size:11px">Clear</button>' +
      '</div>' +
      '<div id="adminGeoKeyFeedback" style="font-size:10.5px;color:var(--status-ok);display:none"></div>' +
    '</div></div>' +

    _boundaryNotice(
      "Production Tile Configuration Boundary",
      "In production, tile provider credentials and style configuration will be loaded from a secure backend or environment variable (e.g. process.env.GEOAPIFY_API_KEY). Zero secrets are committed to git.",
      "Backend Integration: GET /api/admin/geospatial/config\nPermission: MANAGE_MAP_CONFIG\nZero-Secret Doctrine Enforced"
    );
}

function adminSaveGeoKey() {
  var input = document.getElementById("adminGeoapifyKeyInput");
  var feedback = document.getElementById("adminGeoKeyFeedback");
  if (!input) return;
  var key = input.value.trim();
  if (key) {
    sessionStorage.setItem("VANA_GEOAPIFY_API_KEY", key);
    _pushAuditEntry("UPDATE_MAP_CONFIG", "sessionStorage:VANA_GEOAPIFY_API_KEY", "DEV_KEY_CONFIGURED");
    input.value = "";
    if (feedback) {
      feedback.textContent = "Key saved to sessionStorage (masked). Reload Dashboard to activate Geoapify tiles.";
      feedback.style.display = "block";
    }
  }
}

function adminClearGeoKey() {
  sessionStorage.removeItem("VANA_GEOAPIFY_API_KEY");
  var input = document.getElementById("adminGeoapifyKeyInput");
  var feedback = document.getElementById("adminGeoKeyFeedback");
  if (input) input.value = "";
  _pushAuditEntry("CLEAR_MAP_CONFIG", "sessionStorage:VANA_GEOAPIFY_API_KEY", "CLEARED");
  if (feedback) {
    feedback.textContent = "Cleared. Default OSM Development Fallback will be used.";
    feedback.style.display = "block";
  }
}

// =============================================================================
// GOVERNANCE — POLICIES
// =============================================================================
function renderGovPolicies() {
  const el = document.getElementById("section-gov-policies");
  if (!el) return;
  if (!window.VANA_AUTH.requirePermission(P.MANAGE_GOVERNANCE_POLICIES, el)) return;

  el.innerHTML = _sectionHeader(
    "Governance Policies",
    "Active VANA governance doctrine. The pipeline G3 → G1 → G2 → G4 is the authoritative execution path. Read-only — these are constitutional constraints.",
    "Read-only · Constitutional"
  ) + '<div class="admin-card"><div class="admin-card-head"><span class="admin-card-title">Active Governance Pipeline</span></div>' +
    '<div style="display:flex;align-items:center;gap:8px;padding:12px 0;font-size:13px;font-weight:700;color:var(--ink);justify-content:center">' +
    '<span class="admin-role-badge viewer">G3 — Field Observation</span>' +
    '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--text-muted)" stroke-width="2"><line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/></svg>' +
    '<span class="admin-role-badge operator">G1 — Canonical Intake</span>' +
    '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--text-muted)" stroke-width="2"><line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/></svg>' +
    '<span class="admin-role-badge analyst">G2 — Context &amp; Decision</span>' +
    '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--text-muted)" stroke-width="2"><line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/></svg>' +
    '<span class="admin-role-badge administrator">G4 — Governed Execution</span>' +
    '</div></div>' +
    '<div class="admin-card"><div class="admin-card-head"><span class="admin-card-title">Policy Invariants</span></div>' +
    '<table class="admin-table"><thead><tr><th>Policy</th><th>Value</th><th>Modifiable</th></tr></thead><tbody>' +
    '<tr><td>Pipeline mode</td><td>Strictly sequential G3→G1→G2→G4</td><td>No</td></tr>' +
    '<tr><td>Default ruling</td><td>ABSTAIN (fail-closed)</td><td>No</td></tr>' +
    '<tr><td>Observation fabrication</td><td>Prohibited — zero-fabrication invariant</td><td>No</td></tr>' +
    '<tr><td>Canonical record override</td><td>Prohibited</td><td>No</td></tr>' +
    '<tr><td>G4 execution without G1+G2</td><td>Prohibited by Fail-Closed Invariant</td><td>No</td></tr>' +
    '</tbody></table></div>';
}

// =============================================================================
// GOVERNANCE — FAIL-CLOSED RULES
// =============================================================================
function renderGovFailClosed() {
  const el = document.getElementById("section-gov-failclosed");
  if (!el) return;
  if (!window.VANA_AUTH.requirePermission(P.MANAGE_GOVERNANCE_POLICIES, el)) return;

  el.innerHTML = _sectionHeader("Fail-Closed Rules", "The three enforced fail-closed invariants that govern the VANA pipeline. These are code-level constraints, not configuration.", "Enforced in app.js") +
    '<div class="fail-closed-rule"><div class="fail-closed-rule-num">Rule 1 — G1 Gate</div><div class="fail-closed-rule-text">Group 1 failure → Group 2 must not be called</div><div class="fail-closed-rule-desc">If Group 1 (Canonical Observation Retrieval) fails for any reason (HTTP error, timeout, network failure), the pipeline halts immediately. Group 2 is skipped with status SKIPPED and fail_reason explaining the halt. Group 4 is also skipped.</div></div>' +
    '<div class="fail-closed-rule"><div class="fail-closed-rule-num">Rule 2 — G2 Gate</div><div class="fail-closed-rule-text">Group 2 failure → Group 4 must not be called</div><div class="fail-closed-rule-desc">If Group 2 (Scientific Context & Decision Resolve) fails, or if Group 1 already failed (rule 1), Group 4 is skipped. The governed execution gate is never opened without explicit G2 authorization.</div></div>' +
    '<div class="fail-closed-rule"><div class="fail-closed-rule-num">Rule 3 — Zero Fabrication</div><div class="fail-closed-rule-text">Missing authoritative data → NOT VERIFIED, never fabricated</div><div class="fail-closed-rule-desc">If canonical_record_id is null or not returned by Group 1, it is displayed as "NOT VERIFIED". No cached value, default value, or fabricated value is substituted. The canonical_record_id is only populated from authoritative Group 1 response data.</div></div>' +
    _boundaryNotice(
      "Fail-Closed Rule Management",
      "These rules are enforced in app.js (fetchLive function) and cannot be disabled through configuration. Any modification requires a code change with full audit trail and review.",
      "Location: app.js → fetchLive() → g1Success / g2Success gates\nStatus: Immutable runtime invariants\nAdmin override: NOT AVAILABLE"
    );
}

// =============================================================================
// GOVERNANCE — EVIDENCE CONFIGURATION
// =============================================================================
function renderGovEvidence() {
  const el = document.getElementById("section-gov-evidence");
  if (!el) return;
  if (!window.VANA_AUTH.requirePermission(P.MANAGE_GOVERNANCE_POLICIES, el)) return;

  el.innerHTML = _sectionHeader("Evidence Configuration", "Evidence pack schema and Group 3 source configuration.", "View only") +
    '<div class="admin-card"><div class="admin-card-head"><span class="admin-card-title">Active Evidence Pack Schema</span><span class="admin-card-tag">v2.2</span></div>' +
    '<table class="admin-table"><thead><tr><th>Field</th><th>Value</th></tr></thead><tbody>' +
    '<tr><td>Pack file</td><td class="mono">SOURCE_EVIDENCE_PACK_EMITTED_TC-Z03-EXT-OPENMETEO-OBS001.json</td></tr>' +
    '<tr><td>Schema version</td><td class="mono">v2.2</td></tr>' +
    '<tr><td>Compliance</td><td>§26 / §49.1</td></tr>' +
    '<tr><td>Observation ID</td><td class="mono">TC-Z03-EXT-OPENMETEO-OBS001</td></tr>' +
    '<tr><td>Source</td><td>Open-Meteo.com (CC-BY 4.0)</td></tr>' +
    '</tbody></table></div>';
}

// =============================================================================
// OPERATIONS — ALERTS (read-only view)
// =============================================================================
function renderOpsAlerts() {
  const el = document.getElementById("section-ops-alerts");
  if (!el) return;
  if (!window.VANA_AUTH.requirePermission(P.VIEW_ALERTS, el)) return;

  // Alert data (same as operational dashboard — read-only admin view)
  var alerts = [
    { id: "ALT-001", severity: "CRITICAL",  title: "canonical_record_id Not Returned by Group 1 Live Runtime",        category: "DATA_GAP",              ts: "Live Session" },
    { id: "ALT-002", severity: "ABSTAIN",   title: "Group 4 Abstention Gate Triggered — NOOP Enforced",               category: "GOVERNANCE_ABSTENTION", ts: "Live Session" },
    { id: "ALT-003", severity: "GAP",       title: "Missing Source Timestamp (observation_timestamp = null) in G1",    category: "DATA_GAP",              ts: "Live Session" },
    { id: "ALT-004", severity: "GAP",       title: "observation_type and measurement.unit Gap in Source Evidence",     category: "DATA_GAP",              ts: "Live Session" },
    { id: "ALT-005", severity: "INFO",      title: "5 Regional Surveillance Zones Pending Ingestion",                 category: "PENDING_REGIONAL_FEEDS",ts: "Live Session" },
    { id: "ALT-006", severity: "INFO",      title: "CORS Reverse-Proxy Gateway Active",                               category: "RUNTIME_GATEWAY",       ts: "Live Session" },
  ];

  var rows = alerts.map(function (a) {
    return '<tr><td class="mono cell-primary">' + a.id + '</td><td><span class="admin-status-badge ' + (a.severity === "CRITICAL" ? "error" : a.severity === "GAP" || a.severity === "ABSTAIN" ? "warn" : "ok") + '">' + a.severity + '</span></td><td>' + a.title + '</td><td class="mono">' + a.category + '</td><td>' + a.ts + '</td></tr>';
  }).join("");

  el.innerHTML = _sectionHeader("Alerts", "Read-only view of all operational exceptions from the dashboard. Alert management is in the Operational Dashboard.", "Read-only") +
    '<div class="admin-card"><table class="admin-table"><thead><tr><th>ID</th><th>Severity</th><th>Title</th><th>Category</th><th>Timestamp</th></tr></thead><tbody>' + rows + '</tbody></table></div>';
}

// =============================================================================
// OPERATIONS — ALERT RULES
// =============================================================================
function renderOpsAlertRules() {
  const el = document.getElementById("section-ops-alertrules");
  if (!el) return;
  if (!window.VANA_AUTH.requirePermission(P.MANAGE_ALERT_RULES, el)) return;

  el.innerHTML = _sectionHeader("Alert Rules", "Configure which conditions trigger operational alerts. Implementation pending backend alert engine.", "Future iteration") +
    _boundaryNotice(
      "Alert Rules Engine — Not Implemented",
      "Dynamic alert rule configuration requires a backend alert engine. Current alerts in the operational dashboard are statically defined in app.js.",
      "Required: GET/POST /api/admin/alert-rules\n          - condition: { field, operator, threshold }\n          - severity: CRITICAL | ABSTAIN | GAP | INFO\n          - action: { notify, log }\nPermission: MANAGE_ALERT_RULES"
    );
}

// =============================================================================
// OPERATIONS — NOTIFICATION RULES
// =============================================================================
function renderOpsNotifications() {
  const el = document.getElementById("section-ops-notifications");
  if (!el) return;
  if (!window.VANA_AUTH.requirePermission(P.MANAGE_ALERT_RULES, el)) return;

  el.innerHTML = _sectionHeader("Notification Rules", "Configure who gets notified and how when alerts are triggered. Implementation pending.", "Future iteration") +
    _boundaryNotice(
      "Notification Rules — Not Implemented",
      "Notification delivery (email, SMS, webhook) requires a backend notification service and recipient directory.",
      "Required: GET/POST /api/admin/notification-rules\n          - trigger: alert_rule_id\n          - channel: email | webhook | sms\n          - recipients: [user_id]\nPermission: MANAGE_ALERT_RULES"
    );
}

// =============================================================================
// AUDIT — ADMINISTRATIVE ACTIVITY
// =============================================================================
function renderAuditActivity() {
  const el = document.getElementById("section-audit-activity");
  if (!el) return;
  if (!window.VANA_AUTH.requirePermission(P.VIEW_AUDIT_LOG, el)) return;

  var log = _sessionAuditLog;

  var rows = log.length > 0 ? log.map(function (entry) {
    var ts = new Date(entry.ts).toLocaleTimeString("en-GB") + " " + new Date(entry.ts).toLocaleDateString("en-GB", { day: "2-digit", month: "short" });
    return '<tr>' +
      '<td class="mono audit-ts">' + ts + '</td>' +
      '<td>' + entry.userName + '</td>' +
      '<td><span class="admin-role-badge ' + entry.role + '">' + entry.role + '</span></td>' +
      '<td class="audit-action">' + entry.action + '</td>' +
      '<td class="mono" style="color:var(--text-secondary)">' + entry.resource + '</td>' +
      '<td class="audit-result ' + (entry.result === "OK" ? "ok" : "err") + '">' + entry.result + '</td>' +
      '</tr>';
  }).join("")
  : '<tr><td colspan="6" style="text-align:center;color:var(--text-muted);padding:20px">No actions recorded in this session yet.</td></tr>';

  el.innerHTML = _sectionHeader(
    "Administrative Activity",
    "Session-scoped audit log. Records all admin navigation and actions for this browser session only. Not persisted.",
    "Session only · DEV"
  ) + '<div class="admin-card" style="border-color:var(--status-warn-bg)">' +
    '<div class="admin-card-head"><span class="admin-card-title">Session Audit Log</span><span class="admin-card-tag" style="color:var(--status-warn);border-color:var(--status-warn)">DEV — Not persisted</span></div>' +
    '<table class="admin-table"><thead><tr><th>Time</th><th>User</th><th>Role</th><th>Action</th><th>Resource</th><th>Result</th></tr></thead><tbody>' + rows + '</tbody></table></div>' +
    _boundaryNotice(
      "Persistent Audit Logging",
      "Production audit logging requires a backend audit service. All administrative actions should be logged server-side with immutable records. Frontend session log is for DEV convenience only.",
      "Required: POST /api/admin/audit → { userId, role, action, resource, before, after, result }\nPersistence: Immutable append-only audit store\nCurrently: session-scoped in-memory array only"
    );
}

console.log("[VANA Admin] admin.js loaded successfully.");
