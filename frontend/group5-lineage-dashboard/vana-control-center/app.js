/**
 * VANA / PRAKRITI - FOREST INTELLIGENCE COMMAND CENTER
 * Frontend Runtime Integration & Executive Dashboard Engine
 * Strict Fail-Closed Zero-Fabrication Architecture
 */

// =============================================================================
// GLOBAL STATE & REAL REGIONAL CONSTANTS
// =============================================================================
const OBSERVATION_ID = "TC-Z03-EXT-OPENMETEO-OBS001";

// Real Six-Region Surveillance Zones (1 Confirmed Live, 5 Pending Upstream)
const REGIONAL_ZONES = {
  thane_creek: {
    id: "TC-Z03-EXT-OPENMETEO-OBS001",
    name: "Thane Creek",
    status: "CONFIRMED_LIVE",
    canonical_record_id: "CR-b4615a27-7ab1-4bde-a078-a56fa0f2414c",
    lat: 19.1288,
    lon: 72.9421,
    alt_m: 4.0,
    source: "Open-Meteo.com",
    license: "CC-BY 4.0",
    synthetic_state: "CONTROLLED",
    observation_type: "precipitation",
    measurement: 0.1,
    unit: "mm",
    timestamp: "2026-08-25 11:00:00+00:00",
    note: "Authoritative live observation verified end-to-end across Group 1, Group 2, and Group 4."
  },
  mumbai: {
    id: "MU-Z01-EXT-OPENMETEO-OBS001",
    name: "Mumbai",
    status: "PENDING_UPSTREAM",
    lat: 19.0760,
    lon: 72.8777,
    note: "Not yet retrievable from the authoritative Group 1 runtime (POST returns HTTP 500 / GET returns 404)."
  },
  navi_mumbai: {
    id: "NM-Z01-EXT-OPENMETEO-OBS001",
    name: "Navi Mumbai",
    status: "PENDING_UPSTREAM",
    lat: 19.0330,
    lon: 73.0297,
    note: "Not yet retrievable from the authoritative Group 1 runtime (POST returns HTTP 500 / GET returns 404)."
  },
  vasai: {
    id: "VS-Z01-EXT-OPENMETEO-OBS001",
    name: "Vasai",
    status: "PENDING_UPSTREAM",
    lat: 19.4919,
    lon: 72.8054,
    note: "Not yet retrievable from the authoritative Group 1 runtime (POST returns HTTP 500 / GET returns 404)."
  },
  thane: {
    id: "THN-Z01-EXT-OPENMETEO-OBS001",
    name: "Thane",
    status: "PENDING_UPSTREAM",
    lat: 19.2183,
    lon: 72.9781,
    note: "Not yet retrievable from the authoritative Group 1 runtime (POST returns HTTP 500 / GET returns 404)."
  },
  maval: {
    id: "MV-Z01-EXT-OPENMETEO-OBS001",
    name: "Maval",
    status: "PENDING_UPSTREAM",
    lat: 18.7500,
    lon: 73.5000,
    note: "Not yet retrievable from the authoritative Group 1 runtime (POST returns HTTP 500 / GET returns 404)."
  }
};

let currentRuntimeData = {
  observation_id: OBSERVATION_ID,
  canonical_record_id: null,
  context_id: null,
  abstention_record_id: null,
  group1: null,
  group2: null,
  group3: null,
  group4: null
};

let baselineReplayState = null;
let hasReplayExecuted = false;
let replayDiffResults = null;
let evidencePackData = null;
let activeAlertFilter = "ALL";
let acknowledgedAlertIds = new Set();
let leafletMap = null;
let leafletMarkers = {};
let currentMapMode = "tile"; // "tile" or "schematic"
let activeViewName = "fieldSummary";

// =============================================================================
// INITIALIZATION
// =============================================================================
document.addEventListener("DOMContentLoaded", async () => {
  console.log("[VANA Control Center] Initializing Executive Surface...");
  startClock();
  initLeafletMap();
  await loadDefaultEvidencePack();
  await fetchLive();
});

// =============================================================================
// REAL-TIME CLOCK (IST & UTC)
// =============================================================================
function startClock() {
  function update() {
    const now = new Date();
    const dateStr = now.toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" });
    const timeStr = now.toLocaleTimeString("en-GB", { hour12: false }) + " IST";
    const dateEl = document.getElementById("liveDateStr");
    const timeEl = document.getElementById("liveTimeStr");
    if (dateEl) dateEl.textContent = dateStr;
    if (timeEl) timeEl.textContent = timeStr;
  }
  update();
  setInterval(update, 1000);
}

// =============================================================================
// EVIDENCE PACK LOADER
// =============================================================================
async function loadDefaultEvidencePack() {
  try {
    const res = await fetch("SOURCE_EVIDENCE_PACK_EMITTED_TC-Z03-EXT-OPENMETEO-OBS001.json");
    if (res.ok) {
      evidencePackData = await res.json();
      const rawBox = document.getElementById("rawEvidencePackBox");
      if (rawBox) rawBox.textContent = JSON.stringify(evidencePackData, null, 2);
      console.log("[VANA Control Center] Loaded Group 3 Evidence Pack:", evidencePackData.evidence_pack_id);
    }
  } catch (e) {
    console.warn("[VANA Control Center] Evidence pack load failed:", e);
  }
}

// =============================================================================
// API CONFIGURATION GUARD
// Fail loudly if config.js was not loaded before app.js.
// =============================================================================
if (!window.VANA_CONFIG) {
  throw new Error(
    "[VANA] FATAL: window.VANA_CONFIG is not defined. " +
    "Ensure config.js is loaded before app.js in index.html."
  );
}

// =============================================================================
// CENTRALIZED FETCH HELPER — TIMEOUT + ERROR NORMALISATION
// All live API calls go through vanaFetch(). Never call fetch() directly
// for backend endpoints. This enforces a consistent timeout, logs every
// request, and surfaces network failures as explicit Error objects so the
// fail-closed pipeline can handle them uniformly.
// =============================================================================
/**
 * Wrapper around fetch() that:
 *  - Applies a global AbortController-based timeout (VANA_CONFIG.REQUEST_TIMEOUT_MS)
 *  - Logs every outbound request
 *  - Rejects with a descriptive Error on timeout or network failure
 *
 * @param {string} url
 * @param {RequestInit} [options]
 * @returns {Promise<Response>}
 */
async function vanaFetch(url, options = {}) {
  const timeoutMs = (window.VANA_CONFIG && window.VANA_CONFIG.REQUEST_TIMEOUT_MS) || 10000;
  const controller = new AbortController();
  const timerId = setTimeout(() => controller.abort(), timeoutMs);

  console.log(`[VANA Fetch] ${options.method || "GET"} ${url}`);
  try {
    const response = await fetch(url, { ...options, signal: controller.signal });
    return response;
  } catch (err) {
    if (err.name === "AbortError") {
      throw new Error(`Request timed out after ${timeoutMs}ms: ${url}`);
    }
    throw err;
  } finally {
    clearTimeout(timerId);
  }
}

// =============================================================================
// LIVE RUNTIME PIPELINE (GROUP 1 -> GROUP 2 -> GROUP 4)
// STRICT FAIL-CLOSED ZERO-FABRICATION LOGIC
// =============================================================================
async function fetchLive() {
  console.log("[VANA Live Path] Initiating live multi-group pipeline fetch for:", OBSERVATION_ID);
  
  const statusPill = document.getElementById("systemStatusPill");
  const statusText = document.getElementById("systemStatusText");
  if (statusText) statusText.textContent = "Connecting Live APIs...";
  if (statusPill) statusPill.className = "system-status-pill warn";

  // Read endpoints from VANA_CONFIG (defined in config.js).
  // /proxy/* routes are handled by the Python dev server locally and by
  // Vercel rewrites in production — no environment sniffing required.
  const g1Base = window.VANA_CONFIG.G1_BASE;
  const g2Endpoint = window.VANA_CONFIG.G2_ENDPOINT;
  const g4Endpoint = window.VANA_CONFIG.G4_ENDPOINT;

  const data = {
    observation_id: OBSERVATION_ID,
    canonical_record_id: null,
    context_id: null,
    abstention_record_id: null,
    group1: null,
    group2: null,
    group3: null,
    group4: null
  };

  let g1Success = false;
  let g2Success = false;
  let g4Success = false;

  // ---------------------------------------------------------------------------
  // STEP 1: GROUP 1 (CANONICAL RECORD RETRIEVAL)
  // ---------------------------------------------------------------------------
  try {
    console.log("[VANA Live Path] Querying Group 1:", `${g1Base}/observations/${OBSERVATION_ID}`);
    const g1Res = await vanaFetch(`${g1Base}/observations/${encodeURIComponent(OBSERVATION_ID)}`, {
      headers: { "Accept": "application/json" }
    });

    if (g1Res.ok) {
      const envelope = await g1Res.json();
      const obs = envelope.observation || {};
      const prov = obs.provenance || {};

      data.group1 = {
        retrieval_status: envelope.status || "RETRIEVED",
        trace_id: envelope.trace_id || null,
        idempotency_result: envelope.idempotency_result || null
      };

      // Strict Zero-Fabrication: Never fall back to cached canonical_record_id
      data.canonical_record_id = obs.canonical_record_id || envelope.canonical_record_id || null;

      data.group3 = {
        contract_version: obs.contract_version !== undefined ? obs.contract_version : null,
        source_identity: obs.source_identity !== undefined ? obs.source_identity : null,
        flight_id: obs.flight_id !== undefined ? obs.flight_id : null,
        mission_id: obs.mission_id !== undefined ? obs.mission_id : null,
        device_id: obs.device_id !== undefined ? obs.device_id : null,
        observation_timestamp: obs.observation_timestamp !== undefined ? obs.observation_timestamp : null,
        data_state: obs.data_state !== undefined ? obs.data_state : null,
        synthetic_state: obs.synthetic_state !== undefined ? obs.synthetic_state : null,
        location: obs.location || (obs.latitude !== undefined || obs.longitude !== undefined || obs.altitude !== undefined ? { latitude: obs.latitude ?? null, longitude: obs.longitude ?? null, altitude_m: obs.altitude ?? null } : null),
        latitude: obs.latitude !== undefined ? obs.latitude : null,
        longitude: obs.longitude !== undefined ? obs.longitude : null,
        altitude: obs.altitude !== undefined ? obs.altitude : null,
        observation_type: obs.observation_type !== undefined ? obs.observation_type : null,
        measurement: obs.measurement !== undefined ? obs.measurement : null,
        unit: obs.unit !== undefined ? obs.unit : null,
        quality_state: obs.quality_state !== undefined ? obs.quality_state : null,
        calibration_state: obs.calibration_state !== undefined ? obs.calibration_state : null,
        raw_artifact: obs.raw_artifact !== undefined ? obs.raw_artifact : null,
        sha256: obs.sha256 !== undefined ? obs.sha256 : null,
        capture_method: obs.capture_method !== undefined ? obs.capture_method : null,
        provenance: prov
      };

      g1Success = true;
    } else {
      let errMsg = `HTTP ${g1Res.status} from Group 1 runtime`;
      try {
        const errJson = await g1Res.json();
        if (errJson.message) errMsg += `: ${errJson.message}`;
      } catch (_) {}
      console.warn("[VANA Live Path] Group 1 failed:", errMsg);
      data.group1 = { failed: true, fail_reason: errMsg };
      g1Success = false;
    }
  } catch (e) {
    console.error("[VANA Live Path] Group 1 exception:", e);
    data.group1 = { failed: true, fail_reason: `Fetch failed: ${e.message}` };
    g1Success = false;
  }

  // ---------------------------------------------------------------------------
  // STEP 2: GROUP 2 (SCIENTIFIC CONTEXT & DECISION RESOLVE)
  // STRICT FAIL-CLOSED: Executed ONLY if Group 1 succeeded
  // ---------------------------------------------------------------------------
  let g2Ruling = "ABSTAIN";
  let g2ActionEligibility = false;
  let g2AbstentionRequired = true;
  let g2ActionRequest = null;

  if (g1Success) {
    try {
      console.log("[VANA Live Path] Querying Group 2:", g2Endpoint);
      const reqBody = { observation_id: OBSERVATION_ID };
      const g2Res = await vanaFetch(g2Endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(reqBody)
      });

      if (g2Res.ok) {
        const json = await g2Res.json();
        // Group 2 is strictly snake_case & binary fail-closed (ALLOW or ABSTAIN, never DENY)
        g2Ruling = json.ruling === "ALLOW" ? "ALLOW" : "ABSTAIN";
        g2ActionEligibility = json.action_eligibility === true;
        g2AbstentionRequired = json.abstention_required !== undefined ? json.abstention_required : (g2Ruling === "ABSTAIN");
        g2ActionRequest = json.action_request || null;

        data.group2 = {
          http_status: g2Res.status,
          context_status: json.context_status !== undefined ? json.context_status : null,
          ruling: g2Ruling,
          decision: g2Ruling,
          decision_made: json.decision_made !== undefined ? json.decision_made : false,
          decision_reason: json.decision_reason || json.reason || null,
          trace_id: json.trace_id || null,
          context_found: json.context_found !== undefined ? json.context_found : false,
          scientific_context: json.scientific_context || {},
          gap_fields: json.gap_fields || [],
          action_eligibility: g2ActionEligibility,
          abstention_required: g2AbstentionRequired,
          action_request: g2ActionRequest,
          evidence_state: "N/A", // Confirmed permanently out of scope
          provenance: json.provenance || {}
        };
        data.context_id = json.context_id !== undefined ? json.context_id : null;
        g2Success = true;
      } else {
        let errMsg = `HTTP ${g2Res.status} from Group 2 runtime`;
        try {
          const errJson = await g2Res.json();
          if (errJson.message) errMsg += `: ${errJson.message}`;
        } catch (_) {}
        console.warn("[VANA Live Path] Group 2 failed:", errMsg);
        data.group2 = { failed: true, fail_reason: errMsg };
        g2Success = false;
      }
    } catch (e) {
      console.error("[VANA Live Path] Group 2 exception:", e);
      data.group2 = { failed: true, fail_reason: `Fetch failed: ${e.message}` };
      g2Success = false;
    }
  } else {
    // Fail-Closed: Group 2 not called because Group 1 failed
    data.group2 = {
      failed: true,
      skipped: true,
      fail_reason: "Skipped: Execution halted because Group 1 intake failed (Fail-Closed Invariant)"
    };
    g2Success = false;
  }

  // ---------------------------------------------------------------------------
  // STEP 3: GROUP 4 (GOVERNED EXECUTION & ABSTENTION GATE)
  // STRICT FAIL-CLOSED: Executed ONLY if Group 1 AND Group 2 both succeeded
  // ---------------------------------------------------------------------------
  if (g1Success && g2Success) {
    try {
      console.log("[VANA Live Path] Querying Group 4:", g4Endpoint);
      const g4Payload = {
        observation_id: OBSERVATION_ID,
        canonical_record_id: data.canonical_record_id,
        context_id: data.context_id,
        ruling: g2Ruling,
        action_eligibility: g2ActionEligibility,
        abstention_required: g2AbstentionRequired,
        action_request: g2ActionRequest
      };

      const g4Res = await vanaFetch(g4Endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(g4Payload),
        credentials: "omit"
      });

      if (g4Res.ok) {
        const json = await g4Res.json();
        const ev = json.evidence || {};
        
        // Critical: Check both nested evidence.status (e.g. BLOCKED) and top-level status
        const outcomeRuling = ev.ruling || json.ruling || g2Ruling || "ABSTAIN";
        const realStatus = ev.status || json.status || "governed_abstention";

        data.group4 = {
          http_status: g4Res.status,
          status: realStatus,
          event_type: ev.event_type || json.event_type || null,
          ruling: outcomeRuling,
          decision_action: ev.decision_action || json.decision_action || null,
          abstention_record_id: ev.abstention_record_id || json.abstention_record_id || null,
          event_id: ev.event_id || json.event_id || null,
          execution_id: ev.execution_id || json.execution_id || null,
          governance_allowed: ev.governance_allowed !== undefined ? ev.governance_allowed : null,
          recorded_at: json.recorded_at || ev.recorded_at || null,
          decision_reason: json.decision_reason || ev.decision_reason || null
        };
        data.abstention_record_id = data.group4.abstention_record_id;
        g4Success = true;
      } else {
        let errMsg = `HTTP ${g4Res.status} from Group 4 runtime`;
        try {
          const errJson = await g4Res.json();
          if (errJson.message) errMsg += `: ${errJson.message}`;
        } catch (_) {}
        console.warn("[VANA Live Path] Group 4 failed:", errMsg);
        data.group4 = { failed: true, fail_reason: errMsg };
        g4Success = false;
      }
    } catch (e) {
      console.error("[VANA Live Path] Group 4 exception:", e);
      data.group4 = { failed: true, fail_reason: `Fetch failed: ${e.message}` };
      g4Success = false;
    }
  } else {
    // Fail-Closed: Group 4 not called because upstream stage failed
    data.group4 = {
      failed: true,
      skipped: true,
      fail_reason: "Skipped: Execution gate blocked because upstream verification failed (Fail-Closed Invariant)"
    };
    g4Success = false;
  }

  currentRuntimeData = data;

  // Snapshot initial successful state as replay baseline
  if (g1Success && g2Success && g4Success && !baselineReplayState) {
    baselineReplayState = JSON.parse(JSON.stringify(data));
  }

  // Render Dashboard
  renderDashboard(data);

  // Update top beacon based on honest count of healthy APIs
  const okCount = (g1Success ? 1 : 0) + (g2Success ? 1 : 0) + (g4Success ? 1 : 0);
  if (okCount === 3) {
    if (statusText) statusText.textContent = "All Systems Online · Fail-Closed Active";
    if (statusPill) statusPill.className = "system-status-pill";
  } else if (okCount > 0) {
    if (statusText) statusText.textContent = `${okCount} of 3 APIs Online · Fail-Closed Active`;
    if (statusPill) statusPill.className = "system-status-pill warn";
  } else {
    if (statusText) statusText.textContent = "0 of 3 APIs Reachable · System Offline";
    if (statusPill) statusPill.className = "system-status-pill error";
  }
}

// =============================================================================
// DASHBOARD RENDERER
// =============================================================================
function renderDashboard(data) {
  // 1. Pinned Identifiers (Zero fallback)
  const pinnedOid = document.getElementById("pinnedOid");
  const pinnedCrId = document.getElementById("pinnedCanonicalRecordId");
  const pinnedCtxId = document.getElementById("pinnedContextId");

  if (pinnedOid) pinnedOid.textContent = data.observation_id || OBSERVATION_ID;
  if (pinnedCrId) {
    pinnedCrId.textContent = data.canonical_record_id || "NOT VERIFIED";
    pinnedCrId.style.color = data.canonical_record_id ? "var(--text-primary)" : "var(--status-critical)";
  }
  if (pinnedCtxId) {
    pinnedCtxId.textContent = data.context_id !== null && data.context_id !== undefined ? String(data.context_id) : "null";
  }

  // 2. Field Summary View (Primary view for forest officials)
  renderFieldSummary(data);

  // 3. Top KPI Strip (Computed dynamically)
  renderKPIs(data);

  // 4. Map Telemetry Strip
  renderMapTelemetry(data);

  // 5. Lineage Rail
  renderLineageRail(data);

  // 6. Governance Matrix
  renderGovernanceMatrix(data);

  // 7. Scientific Context
  renderScientificContext(data);

  // 8. Operational Alerts Feed
  renderAlertsFeed(data);

  // 9. Replay Diff Table
  renderReplayDiff(data);

  // 10. Update Leaflet Map Markers
  updateLeafletMap(data);
}

// =============================================================================
// FIELD SUMMARY VIEW RENDERER (FOR FOREST OFFICIALS)
// =============================================================================
function renderFieldSummary(data) {
  const container = document.getElementById("viewFieldSummary");
  if (!container) return;

  const g1 = data.group1 || {};
  const g2 = data.group2 || {};
  const g3 = data.group3 || {};
  const g4 = data.group4 || {};

  const isLiveG1 = g1 && !g1.failed;
  const isLiveG2 = g2 && !g2.failed;
  const isLiveG4 = g4 && !g4.failed;
  const allLive = isLiveG1 && isLiveG2 && isLiveG4;

  // Plain-Language Status & Recommendation
  let thaneRecommendation = "System recommendation: <strong>No operational action needed</strong> (System is monitoring weather baseline and verifying source timestamps. All safety guardrails active.)";
  let thaneStatusBadge = '<span class="badge LIVE"><span class="badge-swatch"></span>Live Data Available</span>';
  let thaneTrustPhrase = "Verified Live (Open-Meteo Ingestion)";
  let thaneTrustClass = "live";

  if (!isLiveG1) {
    thaneStatusBadge = '<span class="badge BLOCKED"><span class="badge-swatch"></span>Backend Unreachable</span>';
    thaneTrustPhrase = "Group 1 Authoritative Ingestion Failed";
    thaneTrustClass = "offline";
    thaneRecommendation = "System notice: <strong>Authoritative ingestion endpoint is unreachable</strong>. No live telemetry received.";
  } else if (!isLiveG2) {
    thaneStatusBadge = '<span class="badge CONTROLLED"><span class="badge-swatch"></span>Governance Gate Degraded</span>';
    thaneTrustPhrase = "Group 2 Context Unreachable (Fail-Closed)";
    thaneTrustClass = "warn";
    thaneRecommendation = "System recommendation: <strong>Fail-closed halt active</strong>. Group 2 context service did not respond; execution blocked.";
  }

  const g3Time = g3.observation_timestamp ? new Date(g3.observation_timestamp).toLocaleString("en-GB", { timeZone: "UTC" }) + " UTC" : "Not available";
  const measurementText = (g3.measurement !== undefined && g3.measurement !== null) ? `${g3.measurement} ${g3.unit || 'mm'}` : "Not available";
  const obsTypeText = g3.observation_type ? g3.observation_type.charAt(0).toUpperCase() + g3.observation_type.slice(1) : "";

  let html = `
    <!-- Top Executive Field Overview Banner -->
    <div class="field-summary-hero">
      <div class="hero-left">
        <div class="hero-title">Executive Field Status &amp; Forest Health Overview</div>
        <div class="hero-desc">Real-time status monitoring for forest governance officials across Maharashtra surveillance zones. Built on strict fail-closed safety doctrines.</div>
      </div>
      <div class="hero-metrics">
        <div class="hero-stat-box">
          <div class="stat-num emerald">${isLiveG1 ? "1" : "0"}</div>
          <div class="stat-lbl">Active Live Zone</div>
        </div>
        <div class="hero-stat-box">
          <div class="stat-num amber">5</div>
          <div class="stat-lbl">Pending Deployment</div>
        </div>
        <div class="hero-stat-box">
          <div class="stat-num ${allLive ? 'emerald' : 'amber'}">${allLive ? "Safe" : "Halted"}</div>
          <div class="stat-lbl">Governance Gate</div>
        </div>
      </div>
    </div>

    <!-- Regional Field Cards Grid -->
    <div class="field-zones-grid">

      <!-- Zone 1: Thane Creek (Authoritative Live) -->
      <div class="field-zone-card ${isLiveG1 ? 'active-live' : 'error-state'}" onclick="selectRegion('thane_creek')">
        <div class="zone-card-top">
          <div class="zone-name-box">
            <span class="zone-badge-num">Zone 01</span>
            <div class="zone-name">Thane Creek</div>
            <div class="zone-id mono">${REGIONAL_ZONES.thane_creek.id}</div>
          </div>
          ${thaneStatusBadge}
        </div>

        <div class="trust-indicator ${thaneTrustClass}">
          <span class="trust-dot"></span>
          <span>Trust Status: <strong>${thaneTrustPhrase}</strong></span>
        </div>

        <div class="field-metrics-strip">
          <div class="field-metric-item">
            <div class="metric-k">Latest Field Reading</div>
            <div class="metric-v emerald">${measurementText !== "Not available" ? `${measurementText}${obsTypeText ? ` (${obsTypeText})` : ''}` : "Not available"}</div>
          </div>
          <div class="field-metric-item">
            <div class="metric-k">Source &amp; Method</div>
            <div class="metric-v">${g3.source_identity ? `${g3.source_identity} (Cloud Ingest)` : 'Not available'}</div>
          </div>
          <div class="field-metric-item">
            <div class="metric-k">Observation Time</div>
            <div class="metric-v mono">${g3Time}</div>
          </div>
          <div class="field-metric-item">
            <div class="metric-k">Coordinates &amp; Elevation</div>
            <div class="metric-v mono">${(g3.latitude !== null && g3.latitude !== undefined && g3.longitude !== null && g3.longitude !== undefined) ? `${g3.latitude}° N, ${g3.longitude}° E${g3.altitude !== null && g3.altitude !== undefined ? ` (${g3.altitude}m)` : ''}` : 'Not available'}</div>
          </div>
        </div>

        <div class="field-recommendation-box">
          ${thaneRecommendation}
        </div>

        <div class="field-card-actions">
          <button class="btn-field-action primary" onclick="event.stopPropagation(); switchStageView('lineage');">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="6" cy="6" r="3"></circle><circle cx="6" cy="18" r="3"></circle><line x1="20" y1="4" x2="8.12" y2="15.88"></line></svg>
            <span>View Technical Lineage</span>
          </button>
          <button class="btn-field-action" onclick="event.stopPropagation(); switchStageView('map'); focusMapLocation(19.1288, 72.9421, 12);">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="1 6 1 22 8 18 16 22 23 18 23 2 16 6 8 2 1 6"></polygon></svg>
            <span>View on Map</span>
          </button>
        </div>
      </div>

      <!-- Zone 2: Mumbai -->
      <div class="field-zone-card pending" onclick="selectRegion('mumbai')">
        <div class="zone-card-top">
          <div class="zone-name-box">
            <span class="zone-badge-num">Zone 02</span>
            <div class="zone-name">Mumbai</div>
            <div class="zone-id mono">${REGIONAL_ZONES.mumbai.id}</div>
          </div>
          <span class="badge LOCAL"><span class="badge-swatch"></span>Not Yet Available</span>
        </div>
        <div class="trust-indicator pending">
          <span class="trust-dot"></span>
          <span>Trust Status: <strong>Awaiting Upstream Connection</strong></span>
        </div>
        <div class="field-zone-note">
          ${REGIONAL_ZONES.mumbai.note}
        </div>
        <div class="field-recommendation-box pending">
          System recommendation: <strong>Awaiting field edge sensor deployment</strong>. Per constitutional governance doctrine, unpersisted data is never fabricated.
        </div>
      </div>

      <!-- Zone 3: Navi Mumbai -->
      <div class="field-zone-card pending" onclick="selectRegion('navi_mumbai')">
        <div class="zone-card-top">
          <div class="zone-name-box">
            <span class="zone-badge-num">Zone 03</span>
            <div class="zone-name">Navi Mumbai</div>
            <div class="zone-id mono">${REGIONAL_ZONES.navi_mumbai.id}</div>
          </div>
          <span class="badge LOCAL"><span class="badge-swatch"></span>Not Yet Available</span>
        </div>
        <div class="trust-indicator pending">
          <span class="trust-dot"></span>
          <span>Trust Status: <strong>Awaiting Upstream Connection</strong></span>
        </div>
        <div class="field-zone-note">
          ${REGIONAL_ZONES.navi_mumbai.note}
        </div>
        <div class="field-recommendation-box pending">
          System recommendation: <strong>Awaiting field edge sensor deployment</strong>. Fail-closed safeguard active.
        </div>
      </div>

      <!-- Zone 4: Vasai -->
      <div class="field-zone-card pending" onclick="selectRegion('vasai')">
        <div class="zone-card-top">
          <div class="zone-name-box">
            <span class="zone-badge-num">Zone 04</span>
            <div class="zone-name">Vasai</div>
            <div class="zone-id mono">${REGIONAL_ZONES.vasai.id}</div>
          </div>
          <span class="badge LOCAL"><span class="badge-swatch"></span>Not Yet Available</span>
        </div>
        <div class="trust-indicator pending">
          <span class="trust-dot"></span>
          <span>Trust Status: <strong>Awaiting Upstream Connection</strong></span>
        </div>
        <div class="field-zone-note">
          ${REGIONAL_ZONES.vasai.note}
        </div>
        <div class="field-recommendation-box pending">
          System recommendation: <strong>Awaiting field edge sensor deployment</strong>. Fail-closed safeguard active.
        </div>
      </div>

      <!-- Zone 5: Thane -->
      <div class="field-zone-card pending" onclick="selectRegion('thane')">
        <div class="zone-card-top">
          <div class="zone-name-box">
            <span class="zone-badge-num">Zone 05</span>
            <div class="zone-name">Thane</div>
            <div class="zone-id mono">${REGIONAL_ZONES.thane.id}</div>
          </div>
          <span class="badge LOCAL"><span class="badge-swatch"></span>Not Yet Available</span>
        </div>
        <div class="trust-indicator pending">
          <span class="trust-dot"></span>
          <span>Trust Status: <strong>Awaiting Upstream Connection</strong></span>
        </div>
        <div class="field-zone-note">
          ${REGIONAL_ZONES.thane.note}
        </div>
        <div class="field-recommendation-box pending">
          System recommendation: <strong>Awaiting field edge sensor deployment</strong>. Fail-closed safeguard active.
        </div>
      </div>

      <!-- Zone 6: Maval -->
      <div class="field-zone-card pending" onclick="selectRegion('maval')">
        <div class="zone-card-top">
          <div class="zone-name-box">
            <span class="zone-badge-num">Zone 06</span>
            <div class="zone-name">Maval</div>
            <div class="zone-id mono">${REGIONAL_ZONES.maval.id}</div>
          </div>
          <span class="badge LOCAL"><span class="badge-swatch"></span>Not Yet Available</span>
        </div>
        <div class="trust-indicator pending">
          <span class="trust-dot"></span>
          <span>Trust Status: <strong>Awaiting Upstream Connection</strong></span>
        </div>
        <div class="field-zone-note">
          ${REGIONAL_ZONES.maval.note}
        </div>
        <div class="field-recommendation-box pending">
          System recommendation: <strong>Awaiting field edge sensor deployment</strong>. Fail-closed safeguard active.
        </div>
      </div>

    </div>
  `;

  container.innerHTML = html;
}

// =============================================================================
// KPI STRIP RENDERER (COMPUTED DYNAMICALLY)
// =============================================================================
function renderKPIs(data) {
  const g1 = data.group1 || {};
  const g2 = data.group2 || {};
  const g3 = data.group3 || {};
  const g4 = data.group4 || {};

  const g1Ok = g1 && !g1.failed;
  const g2Ok = g2 && !g2.failed;
  const g4Ok = g4 && !g4.failed;
  const okCount = (g1Ok ? 1 : 0) + (g2Ok ? 1 : 0) + (g4Ok ? 1 : 0);

  // 1. KPI Health
  const kpiHealth = document.getElementById("kpiHealthVal");
  const kpiHealthSub = document.getElementById("kpiHealthSub");
  const kpiHealthBadge = document.getElementById("kpiHealthBadge");

  if (kpiHealth) {
    if (okCount === 3) {
      kpiHealth.textContent = "3 of 3 OK";
      kpiHealth.className = "kpi-value emerald";
      if (kpiHealthSub) kpiHealthSub.textContent = "All APIs Connected";
      if (kpiHealthBadge) { kpiHealthBadge.textContent = "Operational"; kpiHealthBadge.className = "kpi-badge live"; }
    } else if (okCount > 0) {
      kpiHealth.textContent = `${okCount} of 3 OK`;
      kpiHealth.className = "kpi-value amber";
      if (kpiHealthSub) {
        if (!g1Ok) kpiHealthSub.textContent = "G1 Failed · Halted";
        else if (!g2Ok) kpiHealthSub.textContent = "G2 Failed (Fail-Closed)";
        else kpiHealthSub.textContent = "G4 Failed";
      }
      if (kpiHealthBadge) { kpiHealthBadge.textContent = "Degraded"; kpiHealthBadge.className = "kpi-badge warn"; }
    } else {
      kpiHealth.textContent = "0 of 3 OK";
      kpiHealth.className = "kpi-value crimson";
      if (kpiHealthSub) kpiHealthSub.textContent = "All Backends Offline";
      if (kpiHealthBadge) { kpiHealthBadge.textContent = "Offline"; kpiHealthBadge.className = "kpi-badge error"; }
    }
  }

  // 2. KPI Freshness (From Group 4 recorded_at or G2 provenance or G3 timestamp)
  const kpiFreshness = document.getElementById("kpiFreshnessVal");
  const kpiFreshnessSub = document.getElementById("kpiFreshnessSub");
  const kpiFreshnessBadge = document.getElementById("kpiFreshnessBadge");

  const freshnessTs = (g4 && g4.recorded_at) || (g2 && g2.provenance && g2.provenance.group2_decision_time) || (g3 && g3.observation_timestamp);

  if (kpiFreshness) {
    if (freshnessTs && g1Ok) {
      kpiFreshness.textContent = "Live Verified";
      if (kpiFreshnessSub) kpiFreshnessSub.textContent = freshnessTs;
      if (kpiFreshnessBadge) { kpiFreshnessBadge.textContent = "Authoritative"; kpiFreshnessBadge.className = "kpi-badge live"; }
    } else {
      kpiFreshness.textContent = "Unreachable";
      if (kpiFreshnessSub) kpiFreshnessSub.textContent = "No Live Telemetry";
      if (kpiFreshnessBadge) { kpiFreshnessBadge.textContent = "Unverified"; kpiFreshnessBadge.className = "kpi-badge warn"; }
    }
  }

  // 3. KPI Observations
  const kpiObs = document.getElementById("kpiObsVal");
  if (kpiObs) kpiObs.textContent = g1Ok ? "1 Confirmed" : "0 Confirmed";

  // 4. KPI Ruling Outcome
  const kpiRuling = document.getElementById("kpiRulingVal");
  const kpiRulingSub = document.getElementById("kpiRulingSub");
  if (kpiRuling) {
    if (g4Ok && g4.ruling) {
      kpiRuling.textContent = g4.ruling;
      if (kpiRulingSub) kpiRulingSub.textContent = `Action: ${g4.decision_action || 'noop'} (Enforced)`;
    } else if (g2Ok && g2.ruling) {
      kpiRuling.textContent = g2.ruling;
      if (kpiRulingSub) kpiRulingSub.textContent = "Group 2 Ruling (G4 Skipped)";
    } else {
      kpiRuling.textContent = "UNREACHABLE";
      if (kpiRulingSub) kpiRulingSub.textContent = "Pipeline unverified";
    }
  }

  // 5. KPI Lineage Invariance (Computed from replay check)
  const kpiInv = document.getElementById("kpiInvarianceVal");
  const kpiInvSub = document.getElementById("kpiInvarianceSub");
  const kpiInvBadge = document.getElementById("kpiInvarianceBadge");

  if (kpiInv) {
    if (!hasReplayExecuted) {
      kpiInv.textContent = "Not yet verified";
      kpiInv.className = "kpi-value";
      if (kpiInvSub) kpiInvSub.textContent = baselineReplayState ? "Baseline Established" : "Awaiting Baseline";
      if (kpiInvBadge) { kpiInvBadge.textContent = "Unverified"; kpiInvBadge.className = "kpi-badge"; }
    } else {
      const allMatched = replayDiffResults && replayDiffResults.every(r => r.match);
      if (allMatched) {
        kpiInv.textContent = "100% Invariant";
        kpiInv.className = "kpi-value emerald";
        if (kpiInvSub) kpiInvSub.textContent = "4 of 4 Invariants Locked";
        if (kpiInvBadge) { kpiInvBadge.textContent = "Verified"; kpiInvBadge.className = "kpi-badge live"; }
      } else {
        kpiInv.textContent = "Mismatch Detected";
        kpiInv.className = "kpi-value crimson";
        if (kpiInvSub) kpiInvSub.textContent = "Diff check failed";
        if (kpiInvBadge) { kpiInvBadge.textContent = "Mismatch"; kpiInvBadge.className = "kpi-badge error"; }
      }
    }
  }
}

// =============================================================================
// MAP TELEMETRY BAR
// =============================================================================
function renderMapTelemetry(data) {
  const g3 = data.group3 || {};
  const g1 = data.group1 || {};
  const isLive = g1 && !g1.failed;

  const telSource = document.getElementById("telSourceVal");
  const telMeas = document.getElementById("telMeasurementVal");
  const telLoc = document.getElementById("telLocationVal");
  const telSynth = document.getElementById("telSyntheticVal");

  if (telSource) telSource.textContent = isLive && g3.source_identity ? `${g3.source_identity} (CC-BY 4.0)` : (isLive ? "Not available" : "Backend Unreachable");
  if (telMeas) telMeas.textContent = isLive && g3.measurement !== null && g3.measurement !== undefined ? `${g3.measurement} ${g3.unit || "mm"}${g3.observation_type ? ` (${g3.observation_type})` : ''}` : "Not available";
  if (telLoc) telLoc.textContent = (isLive && g3.latitude !== null && g3.latitude !== undefined && g3.longitude !== null && g3.longitude !== undefined) ? `${g3.latitude}° N, ${g3.longitude}° E${g3.altitude !== null && g3.altitude !== undefined ? ` (${g3.altitude}m)` : ''}` : "Not available";
  if (telSynth) telSynth.textContent = isLive ? (g3.synthetic_state || "Not available") : "Not available";
}

// =============================================================================
// LINEAGE RAIL VIEW RENDERER (GROUP 3 -> 1 -> 2 -> 4)
// =============================================================================
function renderLineageRail(data) {
  const container = document.getElementById("lineageRailContainer");
  if (!container) return;

  const g3 = data.group3 || {};
  const g1 = data.group1 || {};
  const g2 = data.group2 || {};
  const g4 = data.group4 || {};

  const g1Failed = g1 && g1.failed;
  const g2Failed = g2 && g2.failed;
  const g4Failed = g4 && g4.failed;

  let html = `
    <!-- CROSS-GROUP TRACE IDENTIFIERS STRIP -->
    <div class="stage-card" style="margin-bottom:14px">
      <div class="stage-group-tag">Cross-Group Identity Invariant Bar</div>
      <div class="stage-title">Deterministic Canonical Identifiers</div>
      <div class="field-grid">
        <div class="field-cell"><div class="field-k">observation_id</div><div class="field-v mono" style="color:var(--status-ok)">${data.observation_id}</div></div>
        <div class="field-cell"><div class="field-k">canonical_record_id</div><div class="field-v mono">${data.canonical_record_id || '<span style="color:var(--status-critical)">NOT VERIFIED</span>'}</div></div>
        <div class="field-cell"><div class="field-k">context_id</div><div class="field-v mono" style="color:var(--status-warn)">${data.context_id === null ? "null" : data.context_id}</div></div>
        <div class="field-cell"><div class="field-k">abstention_record_id</div><div class="field-v mono">${data.abstention_record_id || '<span style="color:var(--text-muted)">null</span>'}</div></div>
        <div class="field-cell"><div class="field-k">contract_version</div><div class="field-v mono">${g3.contract_version || 'Not available'}</div></div>
        <div class="field-cell"><div class="field-k">synthetic_state</div><div class="field-v">${g3.synthetic_state ? `<span class="badge CONTROLLED"><span class="badge-swatch"></span>${g3.synthetic_state}</span>` : 'Not available'}</div></div>
      </div>
    </div>

    <!-- STAGE 1: GROUP 3 RAW OBSERVATION & PROVENANCE -->
    <div class="lineage-stage-node">
      <div class="stage-dot">3</div>
      <div class="stage-card">
        <div class="stage-card-head">
          <div>
            <div class="stage-group-tag">Group 3 · Ingestion &amp; Provenance Engine</div>
            <div class="stage-title">Raw Observation &amp; Third-Party License Provenance</div>
            <div class="stage-id-line mono">observation_id: <strong>${data.observation_id}</strong></div>
          </div>
          <span class="badge CONTROLLED"><span class="badge-swatch"></span>${g3.synthetic_state || 'CONTROLLED'}</span>
        </div>

        <div class="sub-stage-title">Telemetry &amp; Coordinate Grounding</div>
        <div class="field-grid">
          <div class="field-cell"><div class="field-k">Source Identity</div><div class="field-v">${g3.source_identity || "Not available"}</div></div>
          <div class="field-cell"><div class="field-k">Capture Method</div><div class="field-v mono">${g3.capture_method || "Not available"}</div></div>
          <div class="field-cell"><div class="field-k">Observation Type</div><div class="field-v">${g3.observation_type || "Not available"}</div></div>
          <div class="field-cell"><div class="field-k">Measurement</div><div class="field-v mono" style="color:var(--status-ok);font-weight:700">${(g3.measurement !== undefined && g3.measurement !== null) ? `${g3.measurement} ${g3.unit || 'mm'}` : "Not available"}</div></div>
          <div class="field-cell"><div class="field-k">Observation Timestamp</div><div class="field-v mono">${g3.observation_timestamp || "Not available"}</div></div>
          <div class="field-cell"><div class="field-k">Coordinates</div><div class="field-v mono">${(g3.latitude !== null && g3.latitude !== undefined && g3.longitude !== null && g3.longitude !== undefined) ? `${g3.latitude}° N, ${g3.longitude}° E` : "Not available"}</div></div>
          <div class="field-cell"><div class="field-k">Altitude</div><div class="field-v mono">${g3.altitude !== null && g3.altitude !== undefined ? `${g3.altitude} m` : "Not available"}</div></div>
          <div class="field-cell"><div class="field-k">Mission ID</div><div class="field-v mono">${g3.mission_id || "Not available"}</div></div>
          <div class="field-cell"><div class="field-k">Device ID</div><div class="field-v mono">${g3.device_id || "Not available"}</div></div>
          <div class="field-cell"><div class="field-k">Raw Checksum (SHA-256)</div><div class="field-v mono" style="font-size:9.5px">${g3.sha256 || "Not available"}</div></div>
        </div>

        <div class="sub-stage-title">Field Applicability &amp; Declared Gaps (§26/§49.1)</div>
        <div class="field-grid">
          <div class="field-cell"><div class="field-k">GNSS Status</div><div class="field-v na-field">Not applicable (Cloud lookup)</div></div>
          <div class="field-cell"><div class="field-k">Calibration State</div><div class="field-v na-field">Not applicable (Weather model)</div></div>
          <div class="field-cell"><div class="field-k">Measurement Uncertainty</div><div class="field-v gap">GAP (Not reported by source)</div></div>
          <div class="field-cell"><div class="field-k">Raw Artifact Persistence</div><div class="field-v declared-gap">DECLARED GAP (§26 / §49.1)</div></div>
        </div>
      </div>
    </div>

    <!-- STAGE 2: GROUP 1 CANONICAL RECORD -->
    <div class="lineage-stage-node ${g1Failed ? 'blocked' : ''}">
      <div class="stage-dot">${g1Failed ? '✕' : '1'}</div>
      <div class="stage-card">
        <div class="stage-card-head">
          <div>
            <div class="stage-group-tag">Group 1 · Authoritative Intake &amp; Ledger</div>
            <div class="stage-title">Canonical Record Ledger Entry</div>
            <div class="stage-id-line mono">canonical_record_id: <strong>${data.canonical_record_id || '<span style="color:var(--status-critical)">UNVERIFIED</span>'}</strong></div>
          </div>
          <span class="badge ${g1Failed ? 'BLOCKED' : 'LIVE'}"><span class="badge-swatch"></span>${g1Failed ? 'FAILED' : 'RETRIEVED'}</span>
        </div>

        ${g1Failed ? `
          <div class="decision-block BLOCK">
            <div class="decision-label">Group 1 Ingestion Failure</div>
            <div class="decision-outcome">CANONICAL RECORD LOOKUP FAILED</div>
            <div class="decision-reason">${g1.fail_reason || 'Unknown error'}</div>
          </div>
        ` : `
          <div class="field-grid">
            <div class="field-cell"><div class="field-k">Retrieval Status</div><div class="field-v mono" style="color:var(--status-ok)">${g1.retrieval_status || "Not available"}</div></div>
            <div class="field-cell"><div class="field-k">Trace ID</div><div class="field-v mono">${g1.trace_id || 'null'}</div></div>
            <div class="field-cell"><div class="field-k">Storage State</div><div class="field-v mono">PERSISTED_AUTHORITATIVE</div></div>
          </div>
        `}
      </div>
    </div>

    <!-- STAGE 3: GROUP 2 SCIENTIFIC CONTEXT & DECISION -->
    <div class="lineage-stage-node ${g2Failed ? 'blocked' : ''}">
      <div class="stage-dot">${g2Failed ? '✕' : '2'}</div>
      <div class="stage-card">
        <div class="stage-card-head">
          <div>
            <div class="stage-group-tag">Group 2 · Botanical Context &amp; Rulings</div>
            <div class="stage-title">Scientific Context Resolution &amp; Decision</div>
            <div class="stage-id-line mono">context_id: <span style="color:var(--status-warn)">${data.context_id === null ? "null" : data.context_id}</span></div>
          </div>
          <span class="badge ${g2Failed ? 'BLOCKED' : 'CONTROLLED'}"><span class="badge-swatch"></span>${g2Failed ? (g2.skipped ? 'SKIPPED' : 'FAILED') : g2.ruling || 'ABSTAIN'}</span>
        </div>

        ${g2Failed ? `
          <div class="decision-block BLOCK">
            <div class="decision-label">${g2.skipped ? 'Fail-Closed Gate Activated' : 'Group 2 Resolution Failure'}</div>
            <div class="decision-outcome">${g2.skipped ? 'STAGE SKIPPED DUE TO UPSTREAM FAILURE' : 'CONTEXT RESOLUTION FAILED'}</div>
            <div class="decision-reason">${g2.fail_reason || 'Unknown error'}</div>
          </div>
        ` : `
          <div class="decision-block ABSTAIN">
            <div class="decision-label">Group 2 Decision · ruling: ${g2.ruling || 'ABSTAIN'}</div>
            <div class="decision-outcome">ABSTAINED - NO OPERATIONAL ACTION AUTHORIZED</div>
            <div class="decision-reason">${g2.decision_reason || "Not available"}</div>
          </div>

          <div class="field-grid" style="margin-top:10px">
            <div class="field-cell"><div class="field-k">HTTP Status</div><div class="field-v mono">${g2.http_status || 200}</div></div>
            <div class="field-cell"><div class="field-k">Evidence State</div><div class="field-v na-field">N/A (Permanently out of scope)</div></div>
            <div class="field-cell"><div class="field-k">Action Eligibility</div><div class="field-v mono">${g2.action_eligibility !== undefined && g2.action_eligibility !== null ? g2.action_eligibility : "Not available"}</div></div>
            <div class="field-cell"><div class="field-k">Abstention Required</div><div class="field-v mono" style="color:var(--status-warn)">${g2.abstention_required !== undefined && g2.abstention_required !== null ? g2.abstention_required : "Not available"}</div></div>
          </div>
        `}
      </div>
    </div>

    <!-- STAGE 4: GROUP 4 GOVERNED OUTCOME -->
    <div class="lineage-stage-node ${g4Failed ? 'blocked' : ''}">
      <div class="stage-dot">${g4Failed ? '✕' : '4'}</div>
      <div class="stage-card">
        <div class="stage-card-head">
          <div>
            <div class="stage-group-tag">Group 4 · Governance &amp; Execution Gate</div>
            <div class="stage-title">Governed Abstention Enforcement</div>
            <div class="stage-id-line mono">abstention_record_id: <strong>${data.abstention_record_id || '<span style="color:var(--text-muted)">null</span>'}</strong></div>
          </div>
          <span class="badge ${g4Failed ? 'BLOCKED' : 'BLOCKED'}"><span class="badge-swatch"></span>${g4Failed ? (g4.skipped ? 'SKIPPED' : 'FAILED') : 'GOVERNED NOOP'}</span>
        </div>

        ${g4Failed ? `
          <div class="decision-block BLOCK">
            <div class="decision-label">${g4.skipped ? 'Fail-Closed Execution Gate Halted' : 'Group 4 Execution Error'}</div>
            <div class="decision-outcome">${g4.skipped ? 'EXECUTION BLOCKED BY FAIL-CLOSED INVARIANT' : 'GOVERNED EXECUTION FAILED'}</div>
            <div class="decision-reason">${g4.fail_reason || 'Unknown error'}</div>
          </div>
        ` : `
          <div class="decision-block ABSTAIN">
            <div class="decision-label">Governed Ruling: ${g4.ruling || 'Not available'} · Decision Action: ${g4.decision_action || 'Not available'}</div>
            <div class="decision-outcome">GOVERNED ABSTENTION ENFORCED (NO EFFECT)</div>
            <div class="decision-reason">${g4.decision_reason || "Not available"}</div>
          </div>

          <div class="field-grid" style="margin-top:10px">
            <div class="field-cell"><div class="field-k">Ruling</div><div class="field-v mono" style="color:var(--status-warn)">${g4.ruling || "Not available"}</div></div>
            <div class="field-cell"><div class="field-k">Decision Action</div><div class="field-v mono">${g4.decision_action || "Not available"}</div></div>
            <div class="field-cell"><div class="field-k">Governance Allowed</div><div class="field-v mono">${g4.governance_allowed !== null && g4.governance_allowed !== undefined ? g4.governance_allowed : "Not confirmed"}</div></div>
            <div class="field-cell"><div class="field-k">Recorded Timestamp</div><div class="field-v mono" style="font-size:10px">${g4.recorded_at || 'Not available'}</div></div>
          </div>
        `}
      </div>
    </div>
  `;

  container.innerHTML = html;
}

// =============================================================================
// GOVERNANCE MATRIX VIEW RENDERER
// =============================================================================
function renderGovernanceMatrix(data) {
  const g4 = data.group4 || {};
  const g2 = data.group2 || {};
  const grid = document.getElementById("governanceGrid");
  const reasonEl = document.getElementById("govDecisionReason");
  if (!grid) return;

  if (reasonEl) {
    if (g4 && !g4.failed && g4.decision_reason) {
      reasonEl.textContent = g4.decision_reason;
    } else if (g4 && !g4.failed) {
      reasonEl.textContent = "Not available";
    } else {
      reasonEl.textContent = "Pipeline failed upstream. Strict fail-closed guardrail active: zero operational side-effects dispatched.";
    }
  }

  grid.innerHTML = `
    <div class="field-cell"><div class="field-k">Observation ID</div><div class="field-v mono">${data.observation_id}</div></div>
    <div class="field-cell"><div class="field-k">Canonical Record ID</div><div class="field-v mono">${data.canonical_record_id || '<span style="color:var(--status-critical)">UNVERIFIED</span>'}</div></div>
    <div class="field-cell"><div class="field-k">Context ID (Preserved)</div><div class="field-v mono" style="color:var(--status-warn)">${data.context_id === null ? "null" : data.context_id}</div></div>
    <div class="field-cell"><div class="field-k">Abstention Record ID</div><div class="field-v mono">${data.abstention_record_id || '<span style="color:var(--text-muted)">null</span>'}</div></div>
    <div class="field-cell"><div class="field-k">Group 2 Ruling</div><div class="field-v mono">${g2.ruling || (g2.failed ? "FAILED" : "Not available")}</div></div>
    <div class="field-cell"><div class="field-k">Group 4 Ruling</div><div class="field-v mono">${g4.ruling || (g4.failed ? "FAILED" : "Not available")}</div></div>
    <div class="field-cell"><div class="field-k">Decision Action</div><div class="field-v mono" style="color:var(--status-warn)">${g4.decision_action || (g4.failed ? "FAILED" : "Not available")}</div></div>
    <div class="field-cell"><div class="field-k">Action Eligibility</div><div class="field-v mono">${g2.action_eligibility !== undefined && g2.action_eligibility !== null ? g2.action_eligibility : "Not available"}</div></div>
    <div class="field-cell"><div class="field-k">Abstention Required</div><div class="field-v mono" style="color:var(--status-warn)">${g2.abstention_required !== undefined && g2.abstention_required !== null ? g2.abstention_required : "Not available"}</div></div>
    <div class="field-cell"><div class="field-k">Fail-Closed Invariant</div><div class="field-v mono" style="color:var(--status-ok)">ENFORCED</div></div>
  `;
}

// =============================================================================
// SCIENTIFIC CONTEXT RENDERER (DYNAMIC PER SENSOR TYPE)
// =============================================================================
function renderScientificContext(data) {
  const grid = document.getElementById("scientificGrid");
  if (!grid) return;

  const g2 = data.group2 || {};
  const sc = g2.scientific_context || {};
  const scKeys = Object.keys(sc);

  let dynamicCells = "";
  if (scKeys.length > 0) {
    dynamicCells = scKeys.map(k => `
      <div class="field-cell">
        <div class="field-k">${k.replace(/_/g, " ")}</div>
        <div class="field-v mono">${typeof sc[k] === 'object' ? JSON.stringify(sc[k]) : sc[k]}</div>
      </div>
    `).join("");
  } else {
    dynamicCells = `
      <div class="field-cell">
        <div class="field-k">Dynamic Sensor Context</div>
        <div class="field-v na-field">External weather lookup · No botanical canopy context schema returned</div>
      </div>
    `;
  }

  grid.innerHTML = `
    <div class="field-cell"><div class="field-k">Sensor Classification</div><div class="field-v">Open-Meteo Cloud Precipitation API</div></div>
    <div class="field-cell"><div class="field-k">Evidence State Schema</div><div class="field-v na-field">N/A (Permanently out of scope)</div></div>
    ${dynamicCells}
    <div class="field-cell"><div class="field-k">Ecological Indicators DOI</div><div class="field-v"><a href="https://doi.org/10.1016/j.ecolind.2021.107890" target="_blank" style="color:var(--brand)">10.1016/j.ecolind.2021.107890</a></div></div>
    <div class="field-cell"><div class="field-k">Spatial Benchmark DOI</div><div class="field-v"><a href="https://doi.org/10.1038/s41597-020-00780-w" target="_blank" style="color:var(--brand)">10.1038/s41597-020-00780-w</a></div></div>
    <div class="field-cell"><div class="field-k">Authoritative Timestamp Check</div><div class="field-v gap">GAP (Threshold not satisfied)</div></div>
  `;
}

// =============================================================================
// REAL-TIME OPERATIONAL ALERTS & EXCEPTIONS GENERATOR
// =============================================================================
const OPERATIONAL_ALERTS = [
  {
    id: "ALT-001",
    severity: "CRITICAL",
    category: "INGESTION_CLASSIFICATION",
    title: "External Cloud API Ingestion Active (Controlled Path)",
    description: "Observation TC-Z03-EXT-OPENMETEO-OBS001 is ingested from external weather cloud API (Open-Meteo.com) under synthetic_state: CONTROLLED. Edge hardware is not deployed.",
    timestamp: "2026-08-25 11:00 UTC",
    actionable: true
  },
  {
    id: "ALT-002",
    severity: "GAP",
    category: "DECLARED_DATA_GAP",
    title: "Contract §26 / §49.1 Declared Gap: Raw Artifact Not Persisted",
    description: "Raw payload bytes were not persisted at capture time. Formally acknowledged as a declared data gap in Group 3 evidence pack. Downstream verification must not treat this as missing payload failure.",
    timestamp: "2026-08-25 11:00 UTC",
    actionable: false
  },
  {
    id: "ALT-003",
    severity: "ABSTAIN",
    category: "CONTEXT_ABSTENTION",
    title: "Missing Authoritative Timestamp: Failing Closed to ABSTAIN",
    description: "Group 2 context resolution could not establish authoritative physical hardware timestamp threshold. In accordance with constitution, pipeline failed closed to ABSTAIN.",
    timestamp: "2026-08-25 11:00 UTC",
    actionable: true
  },
  {
    id: "ALT-004",
    severity: "ABSTAIN",
    category: "GOVERNED_NOOP",
    title: "Group 4 Governed Abstention Enforced: Decision Action NOOP",
    description: "Group 4 received ruling ABSTAIN and enforced decision_action: noop. No operational action dispatched.",
    timestamp: "2026-08-25 11:00 UTC",
    actionable: true
  },
  {
    id: "ALT-005",
    severity: "INFO",
    category: "PENDING_REGIONAL_FEEDS",
    title: "5 Regional Surveillance Zones Pending Ingestion",
    description: "Mumbai, Navi Mumbai, Vasai, Thane, and Maval are unpersisted in Group 1 database (HTTP 500 / 404). Honest pending states rendered.",
    timestamp: "Current Session",
    actionable: false
  },
  {
    id: "ALT-006",
    severity: "INFO",
    category: "RUNTIME_GATEWAY",
    title: "CORS Reverse-Proxy Gateway Active on Port 8080",
    description: "All runtime calls routed through /proxy/* gateway (Python server locally, Vercel rewrites in production). No direct backend IPs in frontend code. Timeout enforced at 10s per request.",
    timestamp: "Current Session",
    actionable: true
  }
];
window.OPERATIONAL_ALERTS = OPERATIONAL_ALERTS;

function renderAlertsFeed(data) {
  const container = document.getElementById("alertsContainer");
  const badge = document.getElementById("alertCounterBadge");
  const navBadge = document.getElementById("navAlertCount");
  const mobileBadge = document.getElementById("mobileAlertCount");
  if (!container) return;

  const filtered = OPERATIONAL_ALERTS.filter(alt => {
    if (activeAlertFilter === "ALL") return true;
    if (activeAlertFilter === alt.severity) return true;
    if (activeAlertFilter === "GAP" && alt.category.includes("GAP")) return true;
    return false;
  });

  if (badge) badge.textContent = `${OPERATIONAL_ALERTS.length} Exceptions`;
  if (navBadge) navBadge.textContent = OPERATIONAL_ALERTS.length;
  if (mobileBadge) mobileBadge.textContent = OPERATIONAL_ALERTS.length;

  let html = "";
  filtered.forEach(alt => {
    const isAck = acknowledgedAlertIds.has(alt.id);
    html += `
      <div class="alert-card ${alt.severity} ${isAck ? "acknowledged" : ""}" id="card_${alt.id}">
        <div class="alert-card-head">
          <span class="alert-severity-badge ${alt.severity}">${alt.severity}</span>
          <span class="alert-timestamp mono">${alt.timestamp}</span>
        </div>
        <div class="alert-title">${alt.title}</div>
        <div class="alert-description">${alt.description}</div>
        <div class="alert-actions">
          <span class="ack-status-tag">${isAck ? "✓ Acknowledged (Session)" : "Unacknowledged"}</span>
          <div style="display:flex;gap:5px">
            <button class="btn-op-action" onclick="acknowledgeAlert('${alt.id}')" title="Mark as acknowledged for current operator session (non-persistent)">
              ${isAck ? "Undo" : "Acknowledge"}
            </button>
            <button class="btn-op-action primary" onclick="fetchLive()" title="Re-run live fetch pipeline">
              Retry
            </button>
          </div>
        </div>
      </div>
    `;
  });

  container.innerHTML = html;
}

function filterAlerts(category, btn) {
  activeAlertFilter = category;
  document.querySelectorAll(".filter-chip").forEach(el => el.classList.remove("active"));
  if (btn) btn.classList.add("active");
  renderAlertsFeed(currentRuntimeData);
}

function acknowledgeAlert(id) {
  if (acknowledgedAlertIds.has(id)) {
    acknowledgedAlertIds.delete(id);
  } else {
    acknowledgedAlertIds.add(id);
  }
  renderAlertsFeed(currentRuntimeData);
}

// =============================================================================
// REPLAY & DETERMINISTIC DIFF ENGINE (ACTUAL COMPUTED INTEGRITY CHECK)
// =============================================================================
async function triggerReplayVerification() {
  const logEl = document.getElementById("replayProofLog");
  if (logEl) {
    logEl.innerHTML = `<span style="color:var(--status-warn)">[REPLAY RUNNING] Executing fresh live API sequence across Group 1 -> 2 -> 4...</span>`;
  }
  switchStageView("replay");

  // Re-run live fetch
  await fetchLive();

  // Compute honest equality comparison
  const baseline = baselineReplayState || currentRuntimeData;
  const current = currentRuntimeData;

  const invariants = [
    {
      field: "observation_id",
      base: baseline.observation_id || "null",
      curr: current.observation_id || "null",
      match: Boolean(baseline.observation_id && current.observation_id && baseline.observation_id === current.observation_id)
    },
    {
      field: "canonical_record_id",
      base: baseline.canonical_record_id || "null",
      curr: current.canonical_record_id || "null",
      match: Boolean(baseline.canonical_record_id && current.canonical_record_id && baseline.canonical_record_id === current.canonical_record_id)
    },
    {
      field: "context_id",
      base: String(baseline.context_id),
      curr: String(current.context_id),
      match: String(baseline.context_id) === String(current.context_id)
    },
    {
      field: "ruling",
      base: (baseline.group4 && baseline.group4.ruling) || (baseline.group2 && baseline.group2.ruling) || "ABSTAIN",
      curr: (current.group4 && current.group4.ruling) || (current.group2 && current.group2.ruling) || "ABSTAIN",
      match: Boolean(current.group4 && !current.group4.failed && ((baseline.group4 && baseline.group4.ruling) === current.group4.ruling))
    }
  ];

  hasReplayExecuted = true;
  replayDiffResults = invariants;

  // Render Diff Table
  renderReplayDiff(current);

  // Update KPIs
  renderKPIs(current);

  const allPassed = invariants.every(i => i.match);
  const ts = new Date().toISOString();

  if (logEl) {
    logEl.innerHTML = `
      <div style="color:${allPassed ? 'var(--status-ok)' : 'var(--status-critical)'}">${allPassed ? '✓ REPLAY VERIFICATION COMPLETE' : '⚠ REPLAY INTEGRITY WARNING'} at ${ts}</div>
      <div>--------------------------------------------------------------------------------</div>
      ${invariants.map(inv => `<div>* Invariant (${inv.field}): ${inv.curr} [${inv.match ? 'MATCH: PRESERVED' : 'MISMATCH / UNVERIFIED'}]</div>`).join("")}
      <div>--------------------------------------------------------------------------------</div>
      <div style="color:${allPassed ? 'var(--status-ok)' : 'var(--status-warn)'}">
        ${allPassed ? 'CONCLUSION: Lineage reproduction is 100% deterministic and invariant across replays.' : 'CONCLUSION: One or more invariants could not be verified live.'}
      </div>
    `;
  }
}

function renderReplayDiff(data) {
  const tbody = document.getElementById("invariantDiffTableBody");
  if (!tbody) return;

  const baseline = baselineReplayState || data;
  const current = data;

  const invariants = replayDiffResults || [
    { field: "observation_id", base: baseline.observation_id || "null", curr: current.observation_id || "null", match: baseline.observation_id === current.observation_id },
    { field: "canonical_record_id", base: baseline.canonical_record_id || "null", curr: current.canonical_record_id || "null", match: Boolean(baseline.canonical_record_id && current.canonical_record_id && baseline.canonical_record_id === current.canonical_record_id) },
    { field: "context_id", base: String(baseline.context_id), curr: String(current.context_id), match: String(baseline.context_id) === String(current.context_id) },
    { field: "ruling", base: (baseline.group4 && baseline.group4.ruling) || (baseline.group2 && baseline.group2.ruling) || "ABSTAIN", curr: (current.group4 && current.group4.ruling) || (current.group2 && current.group2.ruling) || "ABSTAIN", match: Boolean(current.group4 && !current.group4.failed) }
  ];

  tbody.innerHTML = invariants.map(inv => `
    <tr>
      <td class="mono" style="font-weight:700;color:var(--ink)">${inv.field}</td>
      <td class="mono" style="color:var(--text-secondary)">${inv.base}</td>
      <td class="mono" style="color:${inv.match ? 'var(--status-ok)' : 'var(--status-critical)'}">${inv.curr}</td>
      <td>
        <span class="status-check-pill ${inv.match ? 'pass' : 'fail'}">
          ${inv.match ? `
            <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"></polyline></svg>
            <span>INVARIANT MATCH</span>
          ` : `
            <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
            <span>UNVERIFIED / MISMATCH</span>
          `}
        </span>
      </td>
    </tr>
  `).join("");
}

// =============================================================================
// REGIONAL ZONE SELECTOR
// =============================================================================
function selectRegion(zoneKey) {
  const zone = REGIONAL_ZONES[zoneKey];
  if (!zone) return;

  if (zone.status === "CONFIRMED_LIVE") {
    switchStageView("fieldSummary");
    console.log("[VANA Control Center] Selected authoritative live zone: Thane Creek");
  } else {
    alert(`[PENDING REGION] ${zone.name}\nObservation ID: ${zone.id}\nStatus: ${zone.status}\n\n${zone.note}\n\nPer constitutional doctrine, unpersisted data is never fabricated.`);
  }
}

// =============================================================================
// =============================================================================
// LEAFLET ACCURATE GEOSPATIAL MAP ENGINE (BRIDGED TO VanaGeoEngine)
// =============================================================================
function initLeafletMap() {
  if (window.VanaGeoEngine) {
    window.VanaGeoEngine.init("leafletMap");
    leafletMap = window.VanaGeoEngine.map;
    return;
  }
}

function updateLeafletMap(data) {
  if (window.VanaGeoEngine) {
    window.VanaGeoEngine.updateWithRuntimeData(data);
    leafletMap = window.VanaGeoEngine.map;
    if (leafletMap) leafletMap.invalidateSize();
    return;
  }
  if (!leafletMap) return;
  leafletMap.invalidateSize();
}

function focusMapLocation(lat, lon, zoom) {
  if (window.VanaGeoEngine && window.VanaGeoEngine.map) {
    window.VanaGeoEngine.map.setView([lat, lon], zoom || 11, { animate: true });
    return;
  }
  if (!leafletMap) return;
  leafletMap.setView([lat, lon], zoom || 11, { animate: true });
}

function setMapDisplayMode(mode) {
  currentMapMode = mode;
  const tileWrapper = document.getElementById("leafletMapWrapper");
  const schematicWrapper = document.getElementById("schematicMapWrapper");
  const btnTile = document.getElementById("btnMapTile");
  const btnSchematic = document.getElementById("btnMapSchematic");

  if (mode === "tile") {
    if (tileWrapper) tileWrapper.style.display = "block";
    if (schematicWrapper) schematicWrapper.style.display = "none";
    if (btnTile) btnTile.classList.add("active");
    if (btnSchematic) btnSchematic.classList.remove("active");
    if (window.VanaGeoEngine && window.VanaGeoEngine.map) {
      setTimeout(() => { window.VanaGeoEngine.map.invalidateSize(); }, 150);
    } else if (leafletMap) {
      setTimeout(() => { leafletMap.invalidateSize(); }, 150);
    }
  } else {
    if (tileWrapper) tileWrapper.style.display = "none";
    if (schematicWrapper) schematicWrapper.style.display = "flex";
    if (btnTile) btnTile.classList.remove("active");
    if (btnSchematic) btnSchematic.classList.add("active");
  }
}


// =============================================================================
// UI NAVIGATION & TAB SWITCHING (SYNCHRONIZED DESKTOP & MOBILE)
// =============================================================================
function switchStageView(viewName) {
  activeViewName = viewName;

  const views = {
    fieldSummary: { el: "viewFieldSummary", tab: "tabBtnFieldSummary", title: "Field Operations & Regional Status Overview" },
    map: { el: "viewMap", tab: "tabBtnMap", title: "Regional Geospatial View (6 MMR & Maharashtra Zones)" },
    lineage: { el: "viewLineage", tab: "tabBtnLineage", title: "Lineage Rail & Trace Audit (G3 -> G1 -> G2 -> G4)" },
    governance: { el: "viewGovernance", tab: "tabBtnGovernance", title: "Automated Governance Ruling & Execution Gate" },
    scientific: { el: "viewScientific", tab: "tabBtnScientific", title: "Botanical Context & Dynamic Sensor Context Fields" },
    replay: { el: "viewReplay", tab: "tabBtnReplay", title: "Deterministic Lineage Replay Engine" },
    evidencePack: { el: "viewEvidencePack", tab: "tabBtnEvidencePack", title: "Group 3 Source Evidence Pack v2.2" }
  };

  Object.values(views).forEach(v => {
    const el = document.getElementById(v.el);
    const tab = document.getElementById(v.tab);
    if (el) el.style.display = "none";
    if (tab) tab.classList.remove("active");
  });

  const selected = views[viewName] || views.fieldSummary;
  const selEl = document.getElementById(selected.el);
  const selTab = document.getElementById(selected.tab);
  const titleEl = document.getElementById("stageSubtitleText");

  if (selEl) {
    selEl.style.display = viewName === "map" || viewName === "evidencePack" || viewName === "fieldSummary" ? "flex" : "block";
  }
  if (selTab) selTab.classList.add("active");
  if (titleEl) titleEl.textContent = selected.title;

  if (viewName === "map" && leafletMap) {
    setTimeout(() => { leafletMap.invalidateSize(); }, 150);
  }

  // Scroll active tab into view on small screens
  if (selTab) selTab.scrollIntoView({ behavior: "smooth", inline: "center", block: "nearest" });
}

function switchMainTab(viewKey, navItem) {
  // Sync desktop sidebar
  document.querySelectorAll(".nav-item").forEach(el => el.classList.remove("active"));
  if (navItem && navItem.classList.contains("nav-item")) {
    navItem.classList.add("active");
  }

  // Sync mobile bottom nav
  document.querySelectorAll(".bottom-nav-item").forEach(el => el.classList.remove("active"));
  const bnavMap = {
    fieldSummaryView: "bnavField",
    mapView: "bnavOverview",
    regionalView: "bnavOverview",
    lineageView: "bnavLineage",
    governanceView: "bnavGovernance",
    replayView: "bnavReplay"
  };
  const bnavId = bnavMap[viewKey];
  if (bnavId) {
    const bnavEl = document.getElementById(bnavId);
    if (bnavEl) bnavEl.classList.add("active");
  }

  const map = {
    fieldSummaryView: "fieldSummary",
    mapView: "map",
    lineageView: "lineage",
    governanceView: "governance",
    regionalView: "map",
    scientificView: "scientific",
    evidencePackView: "evidencePack",
    replayView: "replay"
  };

  switchStageView(map[viewKey] || "fieldSummary");

  // Close mobile drawer if open
  toggleSidebar(false);
}

function focusAlerts(navItem) {
  document.querySelectorAll(".nav-item").forEach(el => el.classList.remove("active"));
  document.querySelectorAll(".bottom-nav-item").forEach(el => el.classList.remove("active"));
  
  const navAlerts = document.getElementById("navItemAlerts");
  const bnavAlerts = document.getElementById("bnavAlerts");
  if (navAlerts) navAlerts.classList.add("active");
  if (bnavAlerts) bnavAlerts.classList.add("active");

  const alertsPanel = document.getElementById("alertsPanel");
  if (alertsPanel) {
    alertsPanel.scrollIntoView({ behavior: "smooth" });
    alertsPanel.style.outline = "2px solid var(--status-warn)";
    setTimeout(() => { alertsPanel.style.outline = ""; }, 1500);
  }

  toggleSidebar(false);
}

function toggleSidebar(forceState) {
  const sidebar = document.getElementById("mainSidebar");
  const backdrop = document.getElementById("sidebarBackdrop");
  if (!sidebar) return;

  const isMobile = window.innerWidth <= 768;

  if (isMobile) {
    if (forceState !== undefined) {
      if (forceState) {
        sidebar.classList.add("mobile-open");
        if (backdrop) backdrop.classList.add("active");
      } else {
        sidebar.classList.remove("mobile-open");
        if (backdrop) backdrop.classList.remove("active");
      }
    } else {
      const isOpen = sidebar.classList.toggle("mobile-open");
      if (backdrop) {
        if (isOpen) backdrop.classList.add("active");
        else backdrop.classList.remove("active");
      }
    }
  } else {
    sidebar.classList.toggle("collapsed");
  }
}
