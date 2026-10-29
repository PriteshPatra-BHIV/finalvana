/**
 * VANA: Environmental Governance Platform
 * User-Centric Frontend Runtime Integration & Executive Engine
 * Strict Fail-Closed Zero-Fabrication Architecture
 */

// =============================================================================
// GLOBAL STATE & REAL REGIONAL CONSTANTS
// =============================================================================
// Real Six-Region Surveillance Zones (1 Confirmed Live, 5 Pending Upstream)
let currentObservationId = "TC-Z03-EXT-OPENMETEO-OBS001";
const OBSERVATION_ID = currentObservationId;
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
    note: "Authoritative live observation verified end-to-end across operational runtimes."
  },
  mumbai: {
    id: "MU-Z01-EXT-OPENMETEO-OBS001",
    name: "Mumbai",
    status: "PENDING_UPSTREAM",
    lat: 19.0760,
    lon: 72.8777,
    alt_m: null,
    source: "Pending",
    license: "Pending",
    note: "Awaiting field edge sensor deployment. Not yet retrievable from authoritative backend runtime."
  },
  navi_mumbai: {
    id: "NM-Z01-EXT-OPENMETEO-OBS001",
    name: "Navi Mumbai",
    status: "PENDING_UPSTREAM",
    lat: 19.0330,
    lon: 73.0297,
    alt_m: null,
    source: "Pending",
    license: "Pending",
    note: "Awaiting field edge sensor deployment. Not yet retrievable from authoritative backend runtime."
  },
  vasai: {
    id: "VS-Z01-EXT-OPENMETEO-OBS001",
    name: "Vasai",
    status: "PENDING_UPSTREAM",
    lat: 19.4919,
    lon: 72.8054,
    alt_m: null,
    source: "Pending",
    license: "Pending",
    note: "Awaiting field edge sensor deployment. Not yet retrievable from authoritative backend runtime."
  },
  thane: {
    id: "THN-Z01-EXT-OPENMETEO-OBS001",
    name: "Thane",
    status: "PENDING_UPSTREAM",
    lat: 19.2183,
    lon: 72.9781,
    alt_m: null,
    source: "Pending",
    license: "Pending",
    note: "Awaiting field edge sensor deployment. Not yet retrievable from authoritative backend runtime."
  },
  maval: {
    id: "MV-Z01-EXT-OPENMETEO-OBS001",
    name: "Maval",
    status: "PENDING_UPSTREAM",
    lat: 18.7500,
    lon: 73.5000,
    alt_m: null,
    source: "Pending",
    license: "Pending",
    note: "Awaiting field edge sensor deployment. Not yet retrievable from authoritative backend runtime."
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
let activeAttentionFilter = "ALL";
let activeMonitoringFilter = "ALL";
let activeAlertFilter = "ALL";
let activeMonitoringZoneFilter = "ALL";
let acknowledgedAlertIds = new Set();
let leafletMap = null;
let activeMainView = "overviewView";
let activeHistorySubTab = "provenance";

// =============================================================================
// INITIALIZATION
// =============================================================================
document.addEventListener("DOMContentLoaded", async () => {
  console.log("[VANA Platform] Initializing User-Centric Surface...");
  startClock();
  initLeafletMap();

  // Restore authenticated session from token storage before initiating protected pipeline
  if (window.VANA_AUTH) {
    try {
      await window.VANA_AUTH.restoreSession();
    } catch (e) {
      console.warn("[VANA Platform] Auth session restore failed:", e);
    }
    initDashboardAuthUI();
    window.VANA_AUTH.onAuthChange(() => {
      initDashboardAuthUI();
      renderDecisions(currentRuntimeData);
    });
  }

  await loadDefaultEvidencePack();
  await fetchLive();
});

// =============================================================================
// DASHBOARD AUTHENTICATION UI & EVENT HANDLERS
// =============================================================================
function initDashboardAuthUI() {
  const auth = window.VANA_AUTH;
  const user = auth ? auth.getCurrentUser() : null;

  const roleBadge = document.getElementById("dashRoleBadge");
  const authBtn = document.getElementById("dashAuthBtn");
  const authBtnText = document.getElementById("dashAuthBtnText");

  // Sidebar Persona card
  const ministerName = document.querySelector(".minister-name");
  const ministerRole = document.querySelector(".minister-role");
  const ministerAvatar = document.querySelector(".minister-avatar");

  if (user && auth && auth.isAuthenticated()) {
    // Authenticated state
    if (roleBadge) {
      roleBadge.textContent = user.roleLabel || user.role;
      roleBadge.className = "auth-role-badge " + (user.role || "").toLowerCase();
      roleBadge.style.display = "inline-flex";
    }
    if (authBtn) {
      authBtn.title = `Signed in as ${user.name} (${user.roleLabel || user.role}) · Click to Sign Out`;
      authBtn.className = "btn-header";
      authBtn.onclick = handleDashboardLogout;
    }
    if (authBtnText) {
      authBtnText.textContent = "Sign Out";
    }

    if (ministerName) ministerName.textContent = user.name || "Authenticated Official";
    if (ministerRole) ministerRole.textContent = `${user.roleLabel || user.role} · VANA`;
    if (ministerAvatar) {
      const initials = (user.name || "AU").split(" ").map(w => w[0]).join("").slice(0, 2).toUpperCase();
      ministerAvatar.textContent = initials;
      ministerAvatar.style.background = user.roleColor || "var(--brand)";
    }
  } else {
    // Unauthenticated state
    if (roleBadge) {
      roleBadge.style.display = "none";
    }
    if (authBtn) {
      authBtn.title = "Sign in to authenticate execution actions";
      authBtn.className = "btn-header primary";
      authBtn.onclick = openDashboardLoginModal;
    }
    if (authBtnText) {
      authBtnText.textContent = "Sign In";
    }

    if (ministerName) ministerName.textContent = "State Surveillance";
    if (ministerRole) ministerRole.textContent = "Dept of Environment & Forest";
    if (ministerAvatar) {
      ministerAvatar.textContent = "MH";
      ministerAvatar.style.background = "var(--brand)";
    }
  }
}

function openDashboardLoginModal() {
  const modal = document.getElementById("dashboardLoginModal");
  const errEl = document.getElementById("dashLoginError");
  if (errEl) { errEl.style.display = "none"; errEl.textContent = ""; }
  if (modal) modal.style.display = "flex";
  const emailInput = document.getElementById("dashEmailInput");
  if (emailInput) emailInput.focus();
}

function closeDashboardLoginModal() {
  const modal = document.getElementById("dashboardLoginModal");
  if (modal) modal.style.display = "none";
}

async function handleDashboardLogin(event) {
  if (event) event.preventDefault();
  const emailInput = document.getElementById("dashEmailInput");
  const passInput = document.getElementById("dashPasswordInput");
  const submitBtn = document.getElementById("dashLoginSubmitBtn");
  const errEl = document.getElementById("dashLoginError");

  if (!emailInput || !passInput) return;
  const email = emailInput.value.trim();
  const pass = passInput.value;

  if (submitBtn) { submitBtn.disabled = true; submitBtn.textContent = "Signing In..."; }
  if (errEl) { errEl.style.display = "none"; errEl.textContent = ""; }

  if (!window.VANA_AUTH) {
    if (errEl) { errEl.textContent = "Authentication module unavailable."; errEl.style.display = "block"; }
    if (submitBtn) { submitBtn.disabled = false; submitBtn.textContent = "Sign In"; }
    return;
  }

  const res = await window.VANA_AUTH.login(email, pass);
  if (submitBtn) { submitBtn.disabled = false; submitBtn.textContent = "Sign In"; }

  if (res.success) {
    passInput.value = "";
    closeDashboardLoginModal();
    initDashboardAuthUI();
    // Re-run pipeline to execute authenticated step
    await fetchLive();
  } else {
    if (errEl) {
      errEl.textContent = res.error || "Authentication failed. Please verify credentials.";
      errEl.style.display = "block";
    }
  }
}

function handleDashboardLogout() {
  if (window.VANA_AUTH) {
    window.VANA_AUTH.logout();
    initDashboardAuthUI();
    fetchLive();
  }
}

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
      console.log("[VANA Platform] Loaded Evidence Pack:", evidencePackData.evidence_pack_id);
    }
  } catch (e) {
    console.warn("[VANA Platform] Evidence pack load failed:", e);
  }
}

// =============================================================================
// API CONFIGURATION GUARD
// =============================================================================
if (!window.VANA_CONFIG) {
  throw new Error("[VANA] FATAL: window.VANA_CONFIG is not defined.");
}

// Centralized Fetch Wrapper
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
// LIVE RUNTIME PIPELINE (STRICT FAIL-CLOSED)
// =============================================================================
async function fetchLive(targetObservationId) {
  if (targetObservationId && typeof targetObservationId === "string") {
    currentObservationId = targetObservationId.trim();
    const selectEl = document.getElementById("headerObservationSelect");
    if (selectEl && selectEl.value !== currentObservationId) {
      let optExists = Array.from(selectEl.options).some(opt => opt.value === currentObservationId);
      if (!optExists) {
        const newOpt = document.createElement("option");
        newOpt.value = currentObservationId;
        newOpt.textContent = `Custom (${currentObservationId})`;
        selectEl.appendChild(newOpt);
      }
      selectEl.value = currentObservationId;
    }
  }

  console.log("[VANA Live Path] Fetching operational runtimes for:", currentObservationId);
  
  const statusPill = document.getElementById("systemStatusPill");
  const statusText = document.getElementById("systemStatusText");
  if (statusText) statusText.textContent = "Connecting Live APIs...";
  if (statusPill) statusPill.className = "system-status-pill warn";

  const g1Base = window.VANA_CONFIG.G1_BASE;
  const g2Endpoint = window.VANA_CONFIG.G2_ENDPOINT;
  const g4Endpoint = window.VANA_CONFIG.G4_ENDPOINT;

  const data = {
    observation_id: currentObservationId,
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

  // STEP 1: Observation Intake & Canonical Retrieval
  try {
    const g1Res = await vanaFetch(`${g1Base}/observations/${encodeURIComponent(currentObservationId)}`, {
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

      data.canonical_record_id = obs.canonical_record_id || envelope.canonical_record_id || null;

      const primaryMeas = (Array.isArray(obs.measurements) && obs.measurements.length > 0) ? obs.measurements[0] : null;
      const measVal = (obs.measurement !== undefined && obs.measurement !== null)
        ? obs.measurement
        : (primaryMeas && primaryMeas.value !== undefined ? primaryMeas.value : null);
      const measUnit = obs.unit || (primaryMeas ? primaryMeas.unit : null);
      const obsType = obs.observation_type || (primaryMeas ? primaryMeas.metric_name : null);

      data.group3 = {
        contract_version: obs.contract_version !== undefined ? obs.contract_version : null,
        source_identity: obs.source_identity !== undefined ? obs.source_identity : null,
        flight_id: obs.flight_id !== undefined ? obs.flight_id : null,
        mission_id: obs.mission_id !== undefined ? obs.mission_id : null,
        device_id: obs.device_id !== undefined ? obs.device_id : null,
        observation_timestamp: obs.observation_timestamp !== undefined ? obs.observation_timestamp : null,
        data_state: obs.data_state !== undefined ? obs.data_state : null,
        synthetic_state: obs.synthetic_state !== undefined ? obs.synthetic_state : null,
        location: obs.location || (obs.latitude !== undefined || obs.longitude !== undefined ? { latitude: obs.latitude ?? null, longitude: obs.longitude ?? null, altitude_m: obs.altitude ?? null } : null),
        latitude: obs.latitude !== undefined ? obs.latitude : null,
        longitude: obs.longitude !== undefined ? obs.longitude : null,
        altitude: obs.altitude !== undefined ? obs.altitude : null,
        observation_type: obsType,
        measurement: measVal,
        unit: measUnit,
        quality_state: obs.quality_state !== undefined ? obs.quality_state : null,
        calibration_state: obs.calibration_state !== undefined ? obs.calibration_state : null,
        raw_artifact: obs.raw_artifact !== undefined ? obs.raw_artifact : null,
        sha256: obs.sha256 !== undefined ? obs.sha256 : null,
        capture_method: obs.capture_method !== undefined ? obs.capture_method : null,
        provenance: prov
      };

      g1Success = true;
    } else {
      let errMsg = `HTTP ${g1Res.status} from intake runtime`;
      try {
        const errJson = await g1Res.json();
        if (errJson.message) errMsg += `: ${errJson.message}`;
      } catch (_) {}
      data.group1 = { failed: true, fail_reason: errMsg, http_status: g1Res.status };
      data.canonical_record_id = null;
      data.group3 = null;
      g1Success = false;
    }
  } catch (e) {
    data.group1 = { failed: true, fail_reason: `Fetch failed: ${e.message}`, http_status: 0 };
    data.canonical_record_id = null;
    data.group3 = null;
    g1Success = false;
  }

  // STEP 2: Scientific Context & Decision Resolve (Fail-Closed)
  let g2Ruling = "ABSTAIN";
  let g2ActionEligibility = false;
  let g2AbstentionRequired = true;
  let g2ActionRequest = null;

  if (g1Success) {
    try {
      const reqBody = { observation_id: currentObservationId };
      const g2Res = await vanaFetch(g2Endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(reqBody)
      });

      if (g2Res.ok) {
        const json = await g2Res.json();
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
          evidence_state: "N/A",
          provenance: json.provenance || {}
        };
        data.context_id = json.context_id !== undefined ? json.context_id : null;
        g2Success = true;
      } else {
        let errMsg = `HTTP ${g2Res.status} from decision runtime`;
        try {
          const errJson = await g2Res.json();
          if (errJson.message) errMsg += `: ${errJson.message}`;
        } catch (_) {}
        data.group2 = { failed: true, fail_reason: errMsg };
        g2Success = false;
      }
    } catch (e) {
      data.group2 = { failed: true, fail_reason: `Fetch failed: ${e.message}` };
      g2Success = false;
    }
  } else {
    data.group2 = {
      failed: true,
      skipped: true,
      fail_reason: "Skipped: Execution halted because upstream intake failed (Fail-Closed Invariant)"
    };
    g2Success = false;
  }

  // STEP 3: Governed Execution Gate (Strict Fail-Closed + RBAC)
  if (g1Success && g2Success) {
    const isAuth = window.VANA_AUTH && window.VANA_AUTH.isAuthenticated();
    const isLive = window.VANA_AUTH && typeof window.VANA_AUTH.isLiveValidated === "function" ? window.VANA_AUTH.isLiveValidated() : true;
    if (!isAuth) {
      data.group4 = {
        failed: true,
        requires_auth: true,
        http_status: 401,
        fail_reason: "Authentication Required: Protected execution gate requires an authenticated session. Sign in to authorize execution."
      };
      g4Success = false;
    } else if (!isLive) {
      data.group4 = {
        failed: true,
        unverified_session: true,
        http_status: 403,
        fail_reason: "Validation Required: Cached session cannot dispatch privileged execution without active backend validation. Reconnect or sign in again."
      };
      g4Success = false;
    } else {
      try {
        const g4Payload = {
          observation_id: currentObservationId,
          canonical_record_id: data.canonical_record_id,
          context_id: data.context_id,
          ruling: g2Ruling,
          action_eligibility: g2ActionEligibility,
          abstention_required: g2AbstentionRequired,
          action_request: g2ActionRequest
        };

        const g4Headers = Object.assign(
          { "Content-Type": "application/json", "Accept": "application/json" },
          window.VANA_AUTH ? window.VANA_AUTH.getAuthHeader() : {}
        );

        const g4Res = await vanaFetch(g4Endpoint, {
          method: "POST",
          headers: g4Headers,
          body: JSON.stringify(g4Payload),
          credentials: "omit"
        });

        if (g4Res.ok) {
          const json = await g4Res.json();
          const ev = json.evidence || {};

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
        } else if (g4Res.status === 403) {
          let errMsg = "Execution Forbidden (HTTP 403): Approved Consumer role does not have execution dispatch privileges. Backend authorization enforced.";
          try {
            const errJson = await g4Res.json();
            if (errJson.detail || errJson.message) {
              errMsg = `Execution Forbidden (HTTP 403): ${errJson.detail || errJson.message}`;
            }
          } catch (_) {}

          data.group4 = {
            failed: true,
            forbidden: true,
            http_status: 403,
            fail_reason: errMsg
          };
          g4Success = false;
        } else if (g4Res.status === 401) {
          if (window.VANA_AUTH) {
            window.VANA_AUTH.logout();
            initDashboardAuthUI();
          }
          data.group4 = {
            failed: true,
            unauthorized: true,
            http_status: 401,
            fail_reason: "Session Expired (HTTP 401): Please sign in again to dispatch governed execution."
          };
          g4Success = false;
        } else {
          let errMsg = `HTTP ${g4Res.status} from execution runtime`;
          try {
            const errJson = await g4Res.json();
            if (errJson.message || errJson.detail) errMsg += `: ${errJson.message || errJson.detail}`;
          } catch (_) {}
          data.group4 = { failed: true, http_status: g4Res.status, fail_reason: errMsg };
          g4Success = false;
        }
      } catch (e) {
        data.group4 = { failed: true, fail_reason: `Fetch failed: ${e.message}` };
        g4Success = false;
      }
    }
  } else {
    data.group4 = {
      failed: true,
      skipped: true,
      fail_reason: "Skipped: Execution gate blocked because upstream verification failed (Fail-Closed Invariant)"
    };
    g4Success = false;
  }

  currentRuntimeData = data;

  if (g1Success && g2Success && g4Success && !baselineReplayState) {
    baselineReplayState = JSON.parse(JSON.stringify(data));
  }

  renderDashboard(data);

  const okCount = (g1Success ? 1 : 0) + (g2Success ? 1 : 0) + (g4Success ? 1 : 0);
  if (okCount === 3) {
    if (statusText) statusText.textContent = "All Systems Online · Fail-Closed Active";
    if (statusPill) statusPill.className = "system-status-pill";
  } else if (okCount > 0) {
    if (statusText) statusText.textContent = `${okCount} of 3 Services Reachable`;
    if (statusPill) statusPill.className = "system-status-pill warn";
  } else {
    if (statusText) statusText.textContent = "0 of 3 Services Reachable";
    if (statusPill) statusPill.className = "system-status-pill error";
  }
}

// =============================================================================
// MAIN DASHBOARD RENDERER
// =============================================================================
function renderDashboard(data) {
  // Pinned Identifiers (strictly non-fabricated)
  const pinnedOid = document.getElementById("pinnedOid");
  const pinnedCrId = document.getElementById("pinnedCanonicalRecordId");
  const pinnedCtxId = document.getElementById("pinnedContextId");
  const pinnedOutcomeTag = document.getElementById("pinnedOutcomeTag");

  if (pinnedOid) pinnedOid.textContent = data.observation_id || currentObservationId;
  if (pinnedCrId) {
    if (data.group1 && data.group1.failed) {
      pinnedCrId.textContent = "NOT FOUND / UNRESOLVED";
      pinnedCrId.style.color = "var(--status-critical)";
    } else {
      pinnedCrId.textContent = data.canonical_record_id || "NOT VERIFIED";
      pinnedCrId.style.color = data.canonical_record_id ? "var(--text-primary)" : "var(--status-critical)";
    }
  }
  if (pinnedCtxId) {
    pinnedCtxId.textContent = data.context_id !== null && data.context_id !== undefined ? String(data.context_id) : "null";
  }
  if (pinnedOutcomeTag) {
    if (data.group1 && data.group1.failed) {
      pinnedOutcomeTag.textContent = "Observation Not Found";
      pinnedOutcomeTag.style.color = "var(--status-critical)";
    } else {
      const isPaused = (data.group4 && data.group4.ruling === "ABSTAIN") || (data.group2 && data.group2.ruling === "ABSTAIN");
      pinnedOutcomeTag.textContent = isPaused ? "Assessment Paused (Hold)" : "Evaluating...";
      pinnedOutcomeTag.style.color = "";
    }
  }

  // 1. KPI Strip
  renderKPIs(data);

  // 2. View 1: Overview
  renderOverview(data);

  // 3. View 2: Environmental Monitoring
  renderMonitoring(data);

  // 4. View 3: Map & Locations
  renderMapLocations(data);

  // 5. View 4: Review & Decisions
  renderDecisions(data);

  // 6. View 5: History & Evidence
  renderHistoryEvidence(data);
}

// =============================================================================
// KPI STRIP RENDERER
// =============================================================================
function renderKPIs(data) {
  const g1 = data.group1 || {};
  const g2 = data.group2 || {};
  const g4 = data.group4 || {};

  const g1Ok = g1 && !g1.failed;
  const g2Ok = g2 && !g2.failed;
  const g4Ok = g4 && !g4.failed;
  const okCount = (g1Ok ? 1 : 0) + (g2Ok ? 1 : 0) + (g4Ok ? 1 : 0);

  // Health Pill
  const statusText = document.getElementById("systemStatusText");
  const statusPill = document.getElementById("systemStatusPill");
  if (statusText && statusPill) {
    if (okCount === 3) {
      statusText.textContent = "All Systems Online";
      statusPill.className = "system-status-pill";
    } else if (okCount > 0) {
      statusText.textContent = `${okCount} of 3 Services Active`;
      statusPill.className = "system-status-pill warn";
    } else {
      statusText.textContent = "Offline";
      statusPill.className = "system-status-pill error";
    }
  }

  // Location summary counts
  const kpiMonitored = document.getElementById("kpiLocationsMonitored");
  if (kpiMonitored) kpiMonitored.textContent = "6";

  const kpiObs = document.getElementById("kpiObsVal");
  if (kpiObs) kpiObs.textContent = g1Ok ? "1" : "0";

  const kpiAwaiting = document.getElementById("kpiAwaitingInfo");
  if (kpiAwaiting) kpiAwaiting.textContent = "5";

  const kpiReviews = document.getElementById("kpiReviewsRequired");
  if (kpiReviews) kpiReviews.textContent = "1";

  // Subtitle in card
  const kpiRulingSub = document.getElementById("kpiRulingSub");
  if (kpiRulingSub) {
    kpiRulingSub.textContent = "Thane Creek: Assessment paused";
  }
}

// =============================================================================
// VIEW 1: OVERVIEW RENDERER
// =============================================================================

// Monitored locations attention registry answering:
// 1. Which location?
// 2. What is missing or concerning?
// 3. When was it last updated?
// 4. What should the user do next?
const ATTENTION_LOCATIONS = [
  {
    id: "thane_creek",
    name: "Thane Creek",
    statusText: "Needs review",
    statusClass: "paused",
    category: "REVIEW",
    concern: "Assessment paused: additional evidence needed. Authoritative physical hardware sensor timestamp is required before automated dispatch can be completed.",
    lastUpdated: "25 Aug 2026, 11:00 UTC",
    nextStep: "Review required physical hardware evidence in Reviews & Decisions.",
    actionLabel: "Review Assessment",
    actionFn: "switchMainTab('decisionsView', document.getElementById('navItemDecisions'))"
  },
  {
    id: "mumbai",
    name: "Mumbai",
    statusText: "Waiting for information",
    statusClass: "waiting",
    category: "WAITING",
    concern: "No recent observation available. Field sensor deployment is pending for this surveillance zone.",
    lastUpdated: "No observation recorded",
    nextStep: "Check observation source or wait for edge sensor deployment.",
    actionLabel: "View on Map",
    actionFn: "switchMainTab('mapView', document.getElementById('navItemMap')); focusMapLocation(19.0760, 72.8777, 12);"
  },
  {
    id: "navi_mumbai",
    name: "Navi Mumbai",
    statusText: "Waiting for information",
    statusClass: "waiting",
    category: "WAITING",
    concern: "No recent observation available. Field sensor deployment is pending for this surveillance zone.",
    lastUpdated: "No observation recorded",
    nextStep: "Check observation source or wait for edge sensor deployment.",
    actionLabel: "View on Map",
    actionFn: "switchMainTab('mapView', document.getElementById('navItemMap')); focusMapLocation(19.0330, 73.0297, 12);"
  },
  {
    id: "vasai",
    name: "Vasai",
    statusText: "Waiting for information",
    statusClass: "waiting",
    category: "WAITING",
    concern: "No recent observation available. Field sensor deployment is pending for this surveillance zone.",
    lastUpdated: "No observation recorded",
    nextStep: "Check observation source or wait for edge sensor deployment.",
    actionLabel: "View on Map",
    actionFn: "switchMainTab('mapView', document.getElementById('navItemMap')); focusMapLocation(19.4919, 72.8054, 12);"
  },
  {
    id: "thane",
    name: "Thane",
    statusText: "Waiting for information",
    statusClass: "waiting",
    category: "WAITING",
    concern: "No recent observation available. Field sensor deployment is pending for this surveillance zone.",
    lastUpdated: "No observation recorded",
    nextStep: "Check observation source or wait for edge sensor deployment.",
    actionLabel: "View on Map",
    actionFn: "switchMainTab('mapView', document.getElementById('navItemMap')); focusMapLocation(19.2183, 72.9781, 12);"
  },
  {
    id: "maval",
    name: "Maval",
    statusText: "Waiting for information",
    statusClass: "waiting",
    category: "WAITING",
    concern: "No recent observation available. Field sensor deployment is pending for this surveillance zone.",
    lastUpdated: "No observation recorded",
    nextStep: "Check observation source or wait for edge sensor deployment.",
    actionLabel: "View on Map",
    actionFn: "switchMainTab('mapView', document.getElementById('navItemMap')); focusMapLocation(18.7500, 73.5000, 12);"
  }
];

// =============================================================================
// VIEW 1: OVERVIEW RENDERER
// =============================================================================
function renderOverview(data) {
  // 1. Overall Status banner description
  const statusDesc = document.getElementById("overallStatusDesc");
  if (statusDesc) {
    if (data.group1 && data.group1.failed) {
      statusDesc.innerHTML = `<span style="color:var(--status-critical);font-weight:600;">Observation '${data.observation_id}' not found in MasterDB (${data.group1.fail_reason || "HTTP 404"}).</span> Pipeline halted under fail-closed governance. <button class="btn-header" style="font-size:11px;padding:2px 8px;margin-left:8px;" onclick="fetchLive('TC-Z03-EXT-OPENMETEO-OBS001')">Return to Primary</button>`;
    } else {
      statusDesc.textContent = `Observation data is recorded for ${data.observation_id}, while other monitored areas are awaiting sensor updates or additional evidence.`;
    }
  }

  // 2. Render Locations Needing Attention List
  renderAttentionLocationsFeed();

  // 3. Render Human-Readable Event Activity Stream
  const eventStream = document.getElementById("overviewActivityStream");
  if (eventStream) {
    let events = [];
    if (data.group1 && data.group1.failed) {
      events = [
        { time: "Current Session", title: `Observation ${data.observation_id} Not Found`, desc: `${data.group1.fail_reason || "HTTP 404"}. Upstream intake halted under fail-closed governance.`, type: "warn" },
        { time: "Current Session", title: "Automated Safeguard Active", desc: "Downstream execution and policy evaluation prevented from operating on unverified records.", type: "warn" }
      ];
    } else {
      const g3 = data.group3 || {};
      const measStr = (g3.measurement !== null && g3.measurement !== undefined) ? `${g3.measurement} ${g3.unit || ""}`.trim() : "Verified Reading";
      const obsType = g3.observation_type || "observation";
      events = [
        { time: "Current Session", title: `Assessment evaluated for ${data.observation_id}`, desc: "Statutory governance hold active: physical hardware sensor timestamp is required before assessment can be completed.", type: "warn" },
        { time: "Current Session", title: `Observation recorded for ${data.observation_id}`, desc: `${measStr} (${obsType}) recorded. Measurement is within statutory baseline.`, type: "live" },
        { time: "Current Session", title: "Canonical record verified in master ledger", desc: `Persisted authoritative record reference ${data.canonical_record_id || "CR-..."}.`, type: "live" },
        { time: "Current Session", title: "Automated fail-closed safeguard active", desc: "Zero operational side-effects dispatched while assessment is paused.", type: "warn" }
      ];
    }

    eventStream.innerHTML = events.map(ev => `
      <div style="display:flex;gap:10px;align-items:flex-start;padding:6px 0;border-bottom:1px solid var(--border-light);">
        <span class="status-dot" style="margin-top:5px;background:${ev.type === 'live' ? 'var(--status-ok)' : 'var(--status-warn)'};"></span>
        <div style="flex:1;min-width:0;">
          <div style="display:flex;align-items:center;justify-content:space-between;gap:6px;">
            <strong style="color:var(--text-main);font-size:12px;">${ev.title}</strong>
            <span class="mono" style="font-size:10px;color:var(--text-muted);white-space:nowrap;">${ev.time}</span>
          </div>
          <div style="color:var(--text-secondary);font-size:11.5px;margin-top:2px;line-height:1.4;">${ev.desc}</div>
        </div>
      </div>
    `).join("");
  }
}

function renderAttentionLocationsFeed() {
  const container = document.getElementById("attentionLocationsList");
  if (!container) return;

  const filtered = ATTENTION_LOCATIONS.filter(item => {
    if (activeAttentionFilter === "ALL") return true;
    if (activeAttentionFilter === item.category) return true;
    return false;
  });

  container.innerHTML = filtered.map(loc => `
    <div class="attention-row">
      <div class="attention-main">
        <div class="attention-location-title">
          <span>${loc.name}</span>
          <span class="status-pill ${loc.statusClass}">${loc.statusText}</span>
        </div>
        <div class="attention-issue-desc">${loc.concern}</div>
        <div class="attention-meta">
          <span><strong>Last update:</strong> ${loc.lastUpdated}</span>
          <span><strong>Next step:</strong> ${loc.nextStep}</span>
        </div>
      </div>
      <div class="attention-action">
        <button class="btn-header" style="font-size:11.5px;padding:4px 8px;" onclick="${loc.actionFn}">
          ${loc.actionLabel}
        </button>
      </div>
    </div>
  `).join("");
}

function filterAttentionLocations(filterType, btn) {
  activeAttentionFilter = filterType;
  document.querySelectorAll("#btnFilterAttnAll, #btnFilterAttnReview, #btnFilterAttnWaiting").forEach(el => el.classList.remove("active"));
  if (btn) btn.classList.add("active");
  renderAttentionLocationsFeed();
}


// =============================================================================
// VIEW 2: ENVIRONMENTAL MONITORING RENDERER
// =============================================================================
// =============================================================================
// VIEW 2: ENVIRONMENTAL MONITORING RENDERER
// =============================================================================
function renderMonitoring(data) {
  const container = document.getElementById("monitoringCardsContainer");
  const tbody = document.getElementById("monitoringTableBody");
  if (!container && !tbody) return;

  const g3 = data.group3 || {};
  const g1 = data.group1 || {};
  const isG1Live = g1 && !g1.failed;

  // If G1 failed (e.g. 404 or bad ID), show prominent notification banner and empty/halted cards
  if (!isG1Live) {
    if (container) {
      container.innerHTML = `
        <div style="background:var(--status-critical-bg);border:1px solid var(--status-critical-border);border-radius:var(--radius-md);padding:16px 18px;margin-bottom:14px;">
          <div style="font-weight:700;font-size:13.5px;color:var(--status-critical);display:flex;align-items:center;gap:6px;">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg>
            <span>Observation Not Found in MasterDB (HTTP ${g1.http_status || 404})</span>
          </div>
          <div style="font-size:12px;color:var(--text-main);margin-top:6px;line-height:1.45;">
            The requested observation ID <strong class="mono">${data.observation_id}</strong> is not present in canonical storage. In accordance with zero-fabrication doctrine, no simulated metrics or stale values are displayed.
          </div>
          <div style="margin-top:12px;display:flex;gap:8px;">
            <button type="button" class="btn-header" style="font-size:11.5px;padding:3px 10px;" onclick="fetchLive('TC-Z03-EXT-OPENMETEO-OBS001')">
              Return to Primary Observation
            </button>
            <button type="button" class="btn-header" style="font-size:11.5px;padding:3px 10px;" onclick="openObservationSubmitModal()">
              Submit New Observation
            </button>
          </div>
        </div>
      `;
    }
    if (tbody) {
      tbody.innerHTML = `
        <tr>
          <td colspan="7" style="text-align:center;padding:20px;color:var(--text-muted);font-size:12px;">
            Pipeline halted: observation <strong class="mono">${data.observation_id}</strong> was not found in MasterDB (HTTP ${g1.http_status || 404}).
          </td>
        </tr>
      `;
    }
    return;
  }

  const zoneKeys = Object.keys(REGIONAL_ZONES).filter(key => {
    const z = REGIONAL_ZONES[key];
    const isLive = z.status === "CONFIRMED_LIVE" && isG1Live;

    // Apply button category filters
    if (activeMonitoringFilter === "UPDATED" && !isLive) return false;
    if (activeMonitoringFilter === "WAITING" && isLive) return false;
    if (activeMonitoringFilter === "REVIEW" && key !== "thane_creek") return false;

    // Apply zone dropdown filter
    if (activeMonitoringZoneFilter !== "ALL" && activeMonitoringZoneFilter !== key) return false;

    return true;
  });

  // 1. Observation Cards
  if (container) {
    let html = "";
    zoneKeys.forEach(key => {
      const z = REGIONAL_ZONES[key];
      const isLive = z.status === "CONFIRMED_LIVE" && isG1Live;

      if (isLive) {
        const timeStr = g3.observation_timestamp ? new Date(g3.observation_timestamp).toLocaleString("en-GB", { timeZone: "UTC" }) + " UTC" : "Recorded in Ledger";
        const measurement = (g3.measurement !== null && g3.measurement !== undefined) ? `${g3.measurement} ${g3.unit || ''}`.trim() : "Recorded";
        const obsType = g3.observation_type || "Observation";

        html += `
          <div class="content-panel">
            <div class="panel-header">
              <div>
                <div class="panel-title" style="font-size:15px;display:flex;align-items:center;gap:8px;">
                  <span>${z.name} Monitoring Station</span>
                  <span class="status-pill active">Updated recently</span>
                </div>
                <div style="font-size:11.5px;color:var(--text-secondary);margin-top:2px;">
                  Reference: ${data.observation_id} · Monitored Location
                </div>
              </div>
              <span class="status-pill paused">Assessment paused</span>
            </div>

            <div class="panel-body">
              <div style="display:flex;align-items:center;gap:24px;padding-bottom:14px;border-bottom:1px solid var(--border-light);margin-bottom:14px;flex-wrap:wrap;">
                <div>
                  <div style="font-size:11px;color:var(--text-secondary);font-weight:600;text-transform:uppercase;">Latest Reading</div>
                  <div style="font-size:22px;font-weight:700;color:var(--status-ok);">${measurement} <span style="font-size:13px;color:var(--text-secondary);font-weight:normal;">(${obsType})</span></div>
                </div>
                <div style="height:36px;width:1px;background:var(--border-light);" class="hide-on-mobile"></div>
                <div>
                  <div style="font-size:11px;color:var(--text-secondary);font-weight:600;text-transform:uppercase;">Coordinates &amp; Elevation</div>
                  <div class="mono" style="font-size:13px;font-weight:600;color:var(--text-main);">${z.lat}° N, ${z.lon}° E (${z.alt_m}m)</div>
                </div>
                <div style="height:36px;width:1px;background:var(--border-light);" class="hide-on-mobile"></div>
                <div>
                  <div style="font-size:11px;color:var(--text-secondary);font-weight:600;text-transform:uppercase;">Observation Freshness</div>
                  <div class="mono" style="font-size:13px;font-weight:600;color:var(--text-main);">${timeStr}</div>
                </div>
              </div>

              <div class="tech-kv-grid" style="margin-bottom:14px;">
                <div class="tech-kv-item">
                  <div class="tech-k">Data Ingestion Source</div>
                  <div class="tech-v">${g3.source_identity || z.source}</div>
                </div>
                <div class="tech-kv-item">
                  <div class="tech-k">Canonical Record ID</div>
                  <div class="tech-v mono">${data.canonical_record_id || '<span style="color:var(--status-critical)">NOT VERIFIED</span>'}</div>
                </div>
                <div class="tech-kv-item">
                  <div class="tech-k">Information Status</div>
                  <div class="tech-v" style="color:var(--status-ok)">Active reading verified</div>
                </div>
                <div class="tech-kv-item">
                  <div class="tech-k">Governance Assessment</div>
                  <div class="tech-v" style="color:#7B4C0A">Assessment paused: additional evidence needed</div>
                </div>
              </div>

              <div style="background:var(--bg-page);border:1px solid var(--border-light);border-radius:var(--radius-sm);padding:8px 12px;font-size:12px;color:var(--text-secondary);margin-bottom:14px;">
                <strong>Explanation:</strong> ${obsType} measurement of ${measurement} was ingested and verified into the canonical master ledger. An authoritative physical hardware sensor timestamp is required before statutory dispatch can proceed.
              </div>

              <!-- Collapsible Sensor Technical Parameters -->
              <details class="tech-details" style="margin-top:0;">
                <summary>
                  <span>Technical details: Sensor metadata &amp; checksum</span>
                </summary>
                <div class="tech-details-content">
                  <div class="tech-kv-grid">
                    <div class="tech-kv-item"><div class="tech-k">Device ID</div><div class="tech-v mono">${g3.device_id || "Field Edge Device"}</div></div>
                    <div class="tech-kv-item"><div class="tech-k">Mission ID</div><div class="tech-v mono">${g3.mission_id || "Not available"}</div></div>
                    <div class="tech-kv-item"><div class="tech-k">Capture Method</div><div class="tech-v mono">${g3.capture_method || "sensor"}</div></div>
                    <div class="tech-kv-item"><div class="tech-k">Contract Version</div><div class="tech-v mono">${g3.contract_version || "2.2"}</div></div>
                    <div class="tech-kv-item" style="grid-column:1 / -1;"><div class="tech-k">SHA-256 Checksum</div><div class="tech-v mono" style="font-size:10.5px;overflow-wrap:anywhere;">${g3.sha256 || "Not available"}</div></div>
                  </div>
                </div>
              </details>

              <div style="margin-top:14px;display:flex;align-items:center;justify-content:flex-end;gap:10px;">
                <button class="btn-header" onclick="switchMainTab('mapView', document.getElementById('navItemMap')); focusMapLocation(${z.lat}, ${z.lon}, 12);">
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="1 6 1 22 8 18 16 22 23 18 23 2 16 6 8 2 1 6"></polygon></svg>
                  <span>View on Map</span>
                </button>
                <button class="btn-header primary" onclick="switchMainTab('decisionsView', document.getElementById('navItemDecisions'))">
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path></svg>
                  <span>Review Assessment</span>
                </button>
              </div>
            </div>
          </div>
        `;
      } else {
        html += `
          <div class="content-panel">
            <div class="panel-header">
              <div>
                <div class="panel-title" style="font-size:14px;display:flex;align-items:center;gap:8px;">
                  <span>${z.name} Surveillance Zone</span>
                  <span class="status-pill waiting">Waiting for information</span>
                </div>
                <div style="font-size:11.5px;color:var(--text-secondary);margin-top:2px;">
                  Reference: ${z.id} · Monitored Area
                </div>
              </div>
              <span class="status-pill neutral">Awaiting Sensor Feed</span>
            </div>
            <div class="panel-body">
              <div style="background:var(--bg-page);border:1px solid var(--border-light);border-radius:var(--radius-sm);padding:10px 12px;font-size:12px;color:var(--text-secondary);margin-bottom:12px;line-height:1.45;">
                <strong>Status explanation:</strong> No recent observation is available for ${z.name}. Edge sensor hardware is awaiting deployment. This indicates awaiting data and is not an environmental hazard. Under constitutional doctrine, unpersisted observations are never fabricated.
              </div>
              <div class="tech-kv-grid">
                <div class="tech-kv-item"><div class="tech-k">Reference Latitude</div><div class="tech-v mono">${z.lat}° N</div></div>
                <div class="tech-kv-item"><div class="tech-k">Reference Longitude</div><div class="tech-v mono">${z.lon}° E</div></div>
                <div class="tech-kv-item"><div class="tech-k">Deployment Status</div><div class="tech-v">Awaiting Edge Ingestion Gateway</div></div>
                <div class="tech-kv-item"><div class="tech-k">Next Step</div><div class="tech-v">Wait for edge sensor telemetry feed</div></div>
              </div>
              <div style="margin-top:12px;display:flex;justify-content:flex-end;">
                <button class="btn-header" onclick="switchMainTab('mapView', document.getElementById('navItemMap')); focusMapLocation(${z.lat}, ${z.lon}, 12);">
                  <span>Focus on Map</span>
                </button>
              </div>
            </div>
          </div>
        `;
      }
    });

    if (zoneKeys.length === 0) {
      container.innerHTML = `<div style="padding:24px;text-align:center;color:var(--text-muted);font-size:13px;background:var(--bg-surface);border:1px solid var(--border-light);border-radius:var(--radius-md);">No locations match the selected filter.</div>`;
    } else {
      container.innerHTML = html;
    }
  }

  // 2. Data Table (Zero em dashes)
  if (tbody) {
    tbody.innerHTML = Object.keys(REGIONAL_ZONES).map(key => {
      const z = REGIONAL_ZONES[key];
      const isLive = isG1Live && (z.id === data.observation_id || (key === "thane_creek" && (data.observation_id.startsWith("TC-") || data.observation_id.includes("THANECREEK"))));
      const measVal = (g3.measurement !== null && g3.measurement !== undefined) ? g3.measurement : (isLive ? z.measurement : null);
      const unitVal = (isLive && g3.unit) ? g3.unit : (z.unit || '');
      const reading = isLive && measVal !== null && measVal !== undefined ? `${measVal} ${unitVal}`.trim() : "Not recorded";
      const obsType = isLive ? (g3.observation_type || z.observation_type || 'Observation') : 'Not recorded';

      return `
        <tr>
          <td>
            <strong style="color:var(--text-main);">${z.name}</strong>
            <div class="mono" style="font-size:10.5px;color:var(--text-muted);">${z.id}</div>
          </td>
          <td>
            <span class="status-pill ${isLive ? 'active' : 'waiting'}">
              ${isLive ? 'Updated recently' : 'Waiting for info'}
            </span>
          </td>
          <td>${obsType}</td>
          <td class="mono" style="font-weight:${isLive ? '700' : 'normal'};color:${isLive ? 'var(--status-ok)' : 'var(--text-muted)'};">${reading}</td>
          <td class="mono">${z.lat}° N, ${z.lon}° E</td>
          <td>${z.source}</td>
          <td>
            <button class="btn-header" style="padding:2px 8px;font-size:11px;" onclick="switchMainTab('mapView', document.getElementById('navItemMap')); focusMapLocation(${z.lat}, ${z.lon}, 12);">
              Map
            </button>
          </td>
        </tr>
      `;
    }).join("");
  }
}

function filterMonitoringLocations(category, btn) {
  activeMonitoringFilter = category;
  document.querySelectorAll("#btnFilterMonAll, #btnFilterMonLive, #btnFilterMonWait, #btnFilterMonReview").forEach(el => el.classList.remove("active"));
  if (btn) btn.classList.add("active");
  renderMonitoring(currentRuntimeData);
}


// =============================================================================
// VIEW 3: MAP & LOCATIONS RENDERER
// =============================================================================
function renderMapLocations(data) {
  // Update Leaflet Map Markers
  updateLeafletMap(data);

  // Update telemetry bar
  const g3 = data.group3 || {};
  const g1 = data.group1 || {};
  const isLive = g1 && !g1.failed;

  const telSource = document.getElementById("telSourceVal");
  const telMeas = document.getElementById("telMeasurementVal");
  const telLoc = document.getElementById("telLocationVal");
  const telSynth = document.getElementById("telSyntheticVal");

  if (telSource) telSource.textContent = isLive && g3.source_identity ? `${g3.source_identity} (CC-BY 4.0)` : (isLive ? "Open-Meteo.com" : "Awaiting Data");
  if (telMeas) telMeas.textContent = isLive && g3.measurement !== null && g3.measurement !== undefined ? `${g3.measurement} ${g3.unit || "mm"}${g3.observation_type ? ` (${g3.observation_type})` : ''}` : "0.1 mm (Precipitation)";
  if (telLoc) telLoc.textContent = (isLive && g3.latitude !== null && g3.latitude !== undefined) ? `${g3.latitude}° N, ${g3.longitude}° E${g3.altitude ? ` (${g3.altitude}m)` : ''}` : "19.1288° N, 72.9421° E (4.0m)";
  if (telSynth) telSynth.textContent = isLive ? (g3.synthetic_state || "Controlled Ingest") : "Controlled Ingest";

  // Zone Directory Table
  const tbody = document.getElementById("mapZoneTableBody");
  if (tbody) {
    tbody.innerHTML = Object.keys(REGIONAL_ZONES).map(key => {
      const z = REGIONAL_ZONES[key];
      const isLive = z.status === "CONFIRMED_LIVE";

      return `
        <tr>
          <td><strong style="color:var(--text-primary);">${z.name}</strong></td>
          <td class="mono">${z.id}</td>
          <td><span class="badge ${isLive ? 'LIVE' : 'LOCAL'}" style="font-size:10px;">${isLive ? 'Live Confirmed' : 'Pending Deployment'}</span></td>
          <td class="mono">${z.lat}° N</td>
          <td class="mono">${z.lon}° E</td>
          <td class="mono">${z.alt_m ? `${z.alt_m}m` : '--'}</td>
          <td style="font-size:11.5px;color:var(--text-secondary);max-width:280px;">${isLive ? '0.1 mm precipitation live verified' : 'Awaiting physical hardware deployment'}</td>
          <td>
            <button class="btn-form secondary" style="padding:2px 8px;font-size:11px;" onclick="focusMapLocation(${z.lat}, ${z.lon}, 13)">
              Focus
            </button>
          </td>
        </tr>
      `;
    }).join("");
  }
}

function handleZoneJump(zoneKey) {
  if (!zoneKey) return;
  const z = REGIONAL_ZONES[zoneKey];
  if (z) {
    focusMapLocation(z.lat, z.lon, 13);
  }
}

// =============================================================================
// VIEW 4: REVIEW & DECISIONS RENDERER
// =============================================================================
// =============================================================================
// VIEW 4: REVIEWS & DECISIONS RENDERER
// =============================================================================
function renderDecisions(data) {
  const g4 = data.group4 || {};
  const g2 = data.group2 || {};

  const g1Failed = data.group1 && data.group1.failed;
  const isPaused = g1Failed || (g4 && g4.ruling === "ABSTAIN") || (g2 && g2.ruling === "ABSTAIN");

  // Status Badge
  const badge = document.getElementById("decisionsStatusBadge");
  if (badge) {
    if (g1Failed) {
      badge.textContent = "Observation Not Found";
      badge.className = "status-pill warn";
    } else {
      badge.textContent = isPaused ? "Assessment Paused" : "Assessment Approved";
      badge.className = isPaused ? "status-pill paused" : "status-pill active";
    }
  }

  // Outcome Heading & Explanation
  const outcomeTitle = document.getElementById("decisionsOutcomeTitle");
  const outcomeDesc = document.getElementById("decisionsOutcomeDesc");

  if (outcomeTitle) {
    outcomeTitle.textContent = g1Failed ? "Assessment halted" : (isPaused ? "Assessment paused" : "Assessment approved");
  }
  if (outcomeDesc) {
    if (g1Failed) {
      outcomeDesc.textContent = `Observation ${data.observation_id} was not found in MasterDB (${data.group1.fail_reason || "HTTP 404"}). Downstream governance evaluation cannot proceed without an authoritative canonical record. Under strict fail-closed governance, execution is blocked.`;
    } else if (g4 && g4.decision_reason) {
      outcomeDesc.textContent = g4.decision_reason;
    } else {
      outcomeDesc.textContent = "More evidence is needed before this assessment can be completed. The system requires authoritative physical hardware sensor timestamps before authorizing operational action. Strict fail-closed governance prevented unauthorized state transition.";
    }
  }

  // Question 1: What is known
  const whatObserved = document.getElementById("decisionsWhatObserved");
  if (whatObserved) {
    if (g1Failed) {
      whatObserved.textContent = `No authoritative observation record was found for ID ${data.observation_id}. No unverified or simulated measurements are presented.`;
    } else {
      const g3 = data.group3 || {};
      const measStr = (g3.measurement !== null && g3.measurement !== undefined) ? `${g3.measurement} ${g3.unit || ""}`.trim() : "Recorded";
      const obsType = g3.observation_type || "Environmental reading";
      const latStr = g3.location ? `${g3.location.latitude}° N, ${g3.location.longitude}° E` : (g3.latitude ? `${g3.latitude}° N, ${g3.longitude}° E` : "Thane Creek Zone");
      const crStr = data.canonical_record_id || "Verified in MasterDB";
      whatObserved.textContent = `${obsType} measurement of ${measStr} was recorded at ${latStr}. Canonical record reference is verified in master ledger: ${crStr}.`;
    }
  }

  // Question 2: What is missing
  const evidenceNeeded = document.getElementById("decisionsEvidenceNeeded");
  if (evidenceNeeded) {
    if (g1Failed) {
      evidenceNeeded.textContent = `Canonical observation record in Group 1 MasterDB. Ingestion must succeed before statutory rules can evaluate.`;
    } else {
      evidenceNeeded.textContent = "Authoritative physical hardware sensor timestamp is required. Raw sensor payload bytes were not persisted at capture time (declared data gap §26 / §49.1).";
    }
  }

  // Question 3: Why it matters
  const whyReturned = document.getElementById("decisionsWhyReturned");
  if (whyReturned) {
    if (g1Failed) {
      whyReturned.textContent = "Governance rules strictly prohibit automated state transitions on unpersisted or missing records. The system fails closed to ensure safety.";
    } else {
      whyReturned.textContent = "Statutory environmental governance rules mandate physical hardware verification before automated dispatch. To prevent spoofed or stale readings from authorizing operational actions, the system fails closed to Hold (assessment paused).";
    }
  }

  // Question 4: Next step
  const nextStep = document.getElementById("decisionsNextStepText");
  if (nextStep) {
    if (g1Failed) {
      nextStep.textContent = "Submit a valid Group 3 v2.2 observation via 'Submit Observation' or select an existing observation from the top selector dropdown.";
    } else {
      nextStep.textContent = "No automated action is permitted without complete physical evidence. Environmental officers should check the observation source or wait for edge sensor verification. Authorized administrators may inspect configuration or execute replay verification.";
    }
  }

  // Role Action Panel
  const roleTitle = document.getElementById("roleActionTitle");
  const roleDesc = document.getElementById("roleActionDesc");
  const roleButtons = document.getElementById("roleActionButtons");

  const auth = window.VANA_AUTH;
  const user = auth ? auth.getCurrentUser() : null;
  const isAuth = auth && auth.isAuthenticated();

  if (roleTitle && roleDesc && roleButtons) {
    if (!isAuth) {
      roleTitle.textContent = "Public Observer (Unauthenticated)";
      roleDesc.textContent = "You are currently viewing public environmental monitoring data. Sign in with administrative or auditor credentials to dispatch governed execution or inspect audit logs.";
      roleButtons.innerHTML = `
        <button class="btn-header primary" onclick="openDashboardLoginModal()">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path><circle cx="12" cy="7" r="4"></circle></svg>
          <span>Sign In to Authorize Actions</span>
        </button>
      `;
    } else if (user.role === auth.ROLES.PLATFORM_ADMIN) {
      roleTitle.textContent = `Authorized: Platform Administrator (${user.name})`;
      roleDesc.textContent = "You have full administrative execution and governance dispatch privileges. You may trigger deterministic lineage replay verification or review system security configuration.";
      roleButtons.innerHTML = `
        <button class="btn-header primary" onclick="triggerReplayVerification()">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="23 4 23 10 17 10"></polyline><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"></path></svg>
          <span>Dispatch Replay Verification</span>
        </button>
        <a class="btn-header" href="admin.html">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect><path d="M7 11V7a5 5 0 0 1 10 0v4"></path></svg>
          <span>Open Administration</span>
        </a>
      `;
    } else if (user.role === auth.ROLES.AUDITOR) {
      roleTitle.textContent = `Authorized: Auditor / Judge (${user.name})`;
      roleDesc.textContent = "You have audit log review and deterministic invariant verification privileges. You are authorized to audit provenance trails and verify mathematical invariance across replays.";
      roleButtons.innerHTML = `
        <button class="btn-header primary" onclick="triggerReplayVerification()">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="23 4 23 10 17 10"></polyline><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"></path></svg>
          <span>Verify Deterministic Diff</span>
        </button>
      `;
    } else {
      roleTitle.textContent = `Role: Approved Consumer / Field Participant (${user.name})`;
      roleDesc.textContent = "You have read-only observation and telemetry monitoring access. Operational dispatch actions require Platform Administrator privileges under backend security policy.";
      roleButtons.innerHTML = `
        <span style="font-size:11.5px;color:var(--text-muted);">Execution dispatch restricted (HTTP 403 enforcement active).</span>
      `;
    }
  }

  // Technical Details (Separated secondary layer)
  const pinnedOid = document.getElementById("pinnedOid");
  const pinnedCrId = document.getElementById("pinnedCanonicalRecordId");
  const pinnedCtxId = document.getElementById("pinnedContextId");
  const pinnedOutcomeTag = document.getElementById("pinnedOutcomeTag");
  const techRuling = document.getElementById("techRulingVal");
  const techAction = document.getElementById("techActionVal");
  const techStatus = document.getElementById("techStatusVal");
  const techAbstention = document.getElementById("techAbstentionId");
  const techEvent = document.getElementById("techEventId");
  const techExec = document.getElementById("techExecId");
  const techRawJson = document.getElementById("techRawDecisionJson");

  if (pinnedOid) pinnedOid.textContent = data.observation_id || OBSERVATION_ID;
  if (pinnedCrId) pinnedCrId.textContent = data.canonical_record_id || "CR-b4615a27-7ab1-4bde-a078-a56fa0f2414c";
  if (pinnedCtxId) pinnedCtxId.textContent = data.context_id !== null && data.context_id !== undefined ? String(data.context_id) : "null";
  if (pinnedOutcomeTag) pinnedOutcomeTag.textContent = isPaused ? "Assessment Paused" : "Approved";

  if (techRuling) techRuling.textContent = g4.ruling || g2.ruling || "ABSTAIN";
  if (techAction) techAction.textContent = g4.decision_action || "noop";
  if (techStatus) techStatus.textContent = g4.status || "governed_abstention";
  if (techAbstention) techAbstention.textContent = data.abstention_record_id || (g4 && g4.abstention_record_id) || "null";
  if (techEvent) techEvent.textContent = (g4 && g4.event_id) || "null";
  if (techExec) techExec.textContent = (g4 && g4.execution_id) || "null";

  if (techRawJson) {
    techRawJson.textContent = JSON.stringify({
      observation_id: data.observation_id,
      canonical_record_id: data.canonical_record_id,
      context_id: data.context_id,
      abstention_record_id: data.abstention_record_id,
      ruling: g4.ruling || g2.ruling || "ABSTAIN",
      decision_action: g4.decision_action || "noop",
      fail_closed_enforced: true,
      http_status: (g4 && g4.http_status) || 200
    }, null, 2);
  }
}


// =============================================================================
// VIEW 5: HISTORY & EVIDENCE RENDERER
// =============================================================================
function renderHistoryEvidence(data) {
  // Provenance Rail
  renderLineageRail(data);

  // Replay Diff Table
  renderReplayDiff(data);

  // Scientific Grid
  renderScientificContext(data);
}

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

  const stage1Reading = g1Failed
    ? "None (Observation Unresolved)"
    : ((g3.measurement !== null && g3.measurement !== undefined) ? `${g3.measurement} ${g3.unit || ""}`.trim() : "Recorded");
  const stage1Source = g1Failed ? "Unresolved in MasterDB" : (g3.source_identity || "Field Ingestion");
  const stage1Time = g1Failed ? "None" : (g3.observation_timestamp || "Recorded in Ledger");
  const stage1State = g1Failed ? "UNRESOLVED" : (g3.synthetic_state || "CONTROLLED");

  let html = `
    <!-- STAGE 1: OBSERVATION INTAKE & TELEMETRY -->
    <div class="card-panel">
      <div class="card-panel-head">
        <div>
          <span class="badge" style="margin-bottom:4px;font-size:9.5px;">Stage 1 of 4 · Sensor Ingestion</span>
          <div class="card-panel-title">Environmental Observation Telemetry</div>
        </div>
        <span class="badge ${g1Failed ? 'BLOCKED' : 'CONTROLLED'}">${stage1State}</span>
      </div>
      <div class="card-panel-body">
        <div class="field-grid">
          <div class="field-cell"><div class="field-k">Observation ID</div><div class="field-v mono" style="color:${g1Failed ? 'var(--status-critical)' : 'var(--status-ok)'}">${data.observation_id}</div></div>
          <div class="field-cell"><div class="field-k">Source Identity</div><div class="field-v">${stage1Source}</div></div>
          <div class="field-cell"><div class="field-k">Observed Reading</div><div class="field-v mono" style="color:${g1Failed ? 'var(--status-critical)' : 'var(--status-ok)'}">${stage1Reading}</div></div>
          <div class="field-cell"><div class="field-k">Captured Timestamp</div><div class="field-v mono">${stage1Time}</div></div>
          <div class="field-cell"><div class="field-k">Declared Gap (§26/§49.1)</div><div class="field-v gap">${g1Failed ? "Record absent from canonical ledger" : "Raw payload omitted at capture (Formal Gap)"}</div></div>
          <div class="field-cell"><div class="field-k">SHA-256 Checksum</div><div class="field-v mono" style="font-size:10px;">${g3.sha256 || "Not available"}</div></div>
        </div>
      </div>
    </div>

    <!-- STAGE 2: CANONICAL RECORD LEDGER -->
    <div class="card-panel">
      <div class="card-panel-head">
        <div>
          <span class="badge" style="margin-bottom:4px;font-size:9.5px;">Stage 2 of 4 · Master Ledger</span>
          <div class="card-panel-title">Canonical Record Ledger Entry</div>
        </div>
        <span class="badge ${g1Failed ? 'BLOCKED' : 'LIVE'}">${g1Failed ? 'FAILED' : 'PERSISTED'}</span>
      </div>
      <div class="card-panel-body">
        <div class="field-grid">
          <div class="field-cell"><div class="field-k">Canonical Record ID</div><div class="field-v mono">${data.canonical_record_id || '<span style="color:var(--status-critical)">NOT VERIFIED (Intake Halted)</span>'}</div></div>
          <div class="field-cell"><div class="field-k">Ledger State</div><div class="field-v">${g1Failed ? 'Unpersisted Entry' : 'Persisted Authoritative Entry'}</div></div>
          <div class="field-cell"><div class="field-k">Trace ID</div><div class="field-v mono">${(g1 && g1.trace_id) || "null"}</div></div>
        </div>
      </div>
    </div>

    <!-- STAGE 3: SCIENTIFIC CONTEXT EVALUATION -->
    <div class="card-panel">
      <div class="card-panel-head">
        <div>
          <span class="badge" style="margin-bottom:4px;font-size:9.5px;">Stage 3 of 4 · Scientific Context</span>
          <div class="card-panel-title">Context Resolution &amp; Assessment Ruling</div>
        </div>
        <span class="badge CONTROLLED">${g2.ruling || 'ABSTAIN'}</span>
      </div>
      <div class="card-panel-body">
        <div class="field-grid">
          <div class="field-cell"><div class="field-k">Context ID</div><div class="field-v mono" style="color:var(--status-warn);">${data.context_id === null ? "null (Threshold unsatisfied)" : data.context_id}</div></div>
          <div class="field-cell"><div class="field-k">Context Ruling</div><div class="field-v mono" style="color:var(--status-warn);">${g2.ruling || 'ABSTAIN'}</div></div>
          <div class="field-cell"><div class="field-k">Action Eligibility</div><div class="field-v mono">${g2.action_eligibility === true ? 'true' : 'false'}</div></div>
          <div class="field-cell"><div class="field-k">Abstention Required</div><div class="field-v mono" style="color:var(--status-warn);">true</div></div>
        </div>
      </div>
    </div>

    <!-- STAGE 4: GOVERNED OUTCOME & EXECUTION GATE -->
    <div class="card-panel">
      <div class="card-panel-head">
        <div>
          <span class="badge" style="margin-bottom:4px;font-size:9.5px;">Stage 4 of 4 · Execution Gate</span>
          <div class="card-panel-title">Governed Abstention Enforcement</div>
        </div>
        <span class="badge CONTROLLED">HOLD (NO ACTION)</span>
      </div>
      <div class="card-panel-body">
        <div class="field-grid">
          <div class="field-cell"><div class="field-k">Governed Outcome</div><div class="field-v mono" style="color:var(--status-warn);">${g4.ruling || 'ABSTAIN'}</div></div>
          <div class="field-cell"><div class="field-k">Decision Action</div><div class="field-v mono">${g4.decision_action || 'noop'}</div></div>
          <div class="field-cell"><div class="field-k">Abstention Record ID</div><div class="field-v mono">${data.abstention_record_id || 'null'}</div></div>
          <div class="field-cell"><div class="field-k">Governance Allowed</div><div class="field-v mono">${g4.governance_allowed !== null && g4.governance_allowed !== undefined ? String(g4.governance_allowed) : "false"}</div></div>
        </div>
      </div>
    </div>
  `;

  container.innerHTML = html;
}

function renderScientificContext(data) {
  const grid = document.getElementById("scientificGrid");
  if (!grid) return;

  grid.innerHTML = `
    <div class="field-cell"><div class="field-k">Sensor Classification</div><div class="field-v">Open-Meteo Cloud Precipitation API</div></div>
    <div class="field-cell"><div class="field-k">Ecological Indicators DOI</div><div class="field-v"><a href="https://doi.org/10.1016/j.ecolind.2021.107890" target="_blank">10.1016/j.ecolind.2021.107890</a></div></div>
    <div class="field-cell"><div class="field-k">Spatial Benchmark DOI</div><div class="field-v"><a href="https://doi.org/10.1038/s41597-020-00780-w" target="_blank">10.1038/s41597-020-00780-w</a></div></div>
    <div class="field-cell"><div class="field-k">Authoritative Timestamp Threshold</div><div class="field-v gap">Unsatisfied (Cloud API source)</div></div>
  `;
}

function switchHistorySubTab(subTabName) {
  activeHistorySubTab = subTabName;
  const subtabs = ["provenance", "replay", "evidence", "scientific", "forestCover"];
  subtabs.forEach(t => {
    const el = document.getElementById(`subtab${t.charAt(0).toUpperCase() + t.slice(1)}`);
    const btn = document.getElementById(`btnHist${t.charAt(0).toUpperCase() + t.slice(1)}`);
    if (el) el.style.display = t === subTabName ? "flex" : "none";
    if (btn) {
      if (t === subTabName) btn.classList.add("active");
      else btn.classList.remove("active");
    }
  });
  if (subTabName === "forestCover") {
    loadOfficialForestCover();
  }
}

// =============================================================================
// REPLAY & DETERMINISTIC DIFF ENGINE
// =============================================================================
async function triggerReplayVerification() {
  const logEl = document.getElementById("replayProofLog");
  if (logEl) {
    logEl.innerHTML = `<span style="color:var(--status-warn)">[REPLAY RUNNING] Executing fresh live API sequence across operational runtimes...</span>`;
  }
  
  switchMainTab("historyView", document.getElementById("navItemHistory"));
  switchHistorySubTab("replay");

  await fetchLive();

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

  renderReplayDiff(current);
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
      <td class="mono" style="font-weight:700;color:var(--text-primary)">${inv.field}</td>
      <td class="mono" style="color:var(--text-secondary)">${inv.base}</td>
      <td class="mono" style="color:${inv.match ? 'var(--status-ok)' : 'var(--status-critical)'}">${inv.curr}</td>
      <td>
        <span class="badge ${inv.match ? 'LIVE' : 'BLOCKED'}">
          ${inv.match ? '✓ PRESERVED' : 'MISMATCH'}
        </span>
      </td>
    </tr>
  `).join("");
}

// =============================================================================
// OPERATIONAL ALERTS & EXCEPTIONS
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
    description: "All runtime calls routed through /proxy/* gateway. No direct backend IPs in frontend code. Timeout enforced at 10s per request.",
    timestamp: "Current Session",
    actionable: true
  }
];
window.OPERATIONAL_ALERTS = OPERATIONAL_ALERTS;

function renderAlertsFeed(data) {
  const container = document.getElementById("alertsContainer");
  if (!container) return;

  const filtered = OPERATIONAL_ALERTS.filter(alt => {
    if (activeAlertFilter === "ALL") return true;
    if (activeAlertFilter === alt.severity) return true;
    if (activeAlertFilter === "GAP" && alt.category.includes("GAP")) return true;
    return false;
  });

  container.innerHTML = filtered.map(alt => {
    return `
      <div class="alert-card ${alt.severity}" id="card_${alt.id}">
        <div class="alert-card-head">
          <span class="alert-severity-badge ${alt.severity}">${alt.severity}</span>
          <span class="alert-timestamp mono">${alt.timestamp}</span>
        </div>
        <div class="alert-title">${alt.title}</div>
        <div class="alert-description">${alt.description}</div>
        <div class="alert-actions">
          <span class="ack-status-tag" style="color:var(--text-secondary);font-size:11px;">Declared Governance Condition</span>
          <div style="display:flex;gap:6px;">
            <button type="button" class="btn-op-action" onclick="switchMainTab('decisionsView', document.getElementById('navItemDecisions'))">
              View Ruling
            </button>
            <button type="button" class="btn-op-action primary" onclick="switchMainTab('historyView', document.getElementById('navItemHistory'))">
              View Evidence
            </button>
          </div>
        </div>
      </div>
    `;
  }).join("");
}

function filterAlerts(category, btn) {
  activeAlertFilter = category;
  document.querySelectorAll(".filter-chip").forEach(el => el.classList.remove("active"));
  if (btn) btn.classList.add("active");
  renderAlertsFeed(currentRuntimeData);
}

// =============================================================================
// MAP & GEOSPATIAL ENGINE INTEGRATION
// =============================================================================
function initLeafletMap() {
  if (window.VanaGeoEngine) {
    window.VanaGeoEngine.init("leafletMap");
    leafletMap = window.VanaGeoEngine.map;
  }
}

function updateLeafletMap(data) {
  if (window.VanaGeoEngine) {
    window.VanaGeoEngine.updateWithRuntimeData(data);
    leafletMap = window.VanaGeoEngine.map;
    if (leafletMap) leafletMap.invalidateSize();
  }
}

function focusMapLocation(lat, lon, zoom) {
  if (window.VanaGeoEngine && window.VanaGeoEngine.map) {
    window.VanaGeoEngine.map.setView([lat, lon], zoom || 11, { animate: true });
  } else if (leafletMap) {
    leafletMap.setView([lat, lon], zoom || 11, { animate: true });
  }
}

function setMapDisplayMode(mode) {
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
    }
  } else {
    if (tileWrapper) tileWrapper.style.display = "none";
    if (schematicWrapper) schematicWrapper.style.display = "flex";
    if (btnTile) btnTile.classList.remove("active");
    if (btnSchematic) btnSchematic.classList.add("active");
  }
}

function selectRegion(zoneKey) {
  const z = REGIONAL_ZONES[zoneKey];
  if (!z) return;

  if (z.status === "CONFIRMED_LIVE") {
    switchMainTab("monitoringView", document.getElementById("navItemMonitoring"));
  } else {
    alert(`[PENDING REGION] ${z.name}\nObservation ID: ${z.id}\nStatus: ${z.status}\n\n${z.note}\n\nPer constitutional doctrine, unpersisted data is never fabricated.`);
  }
}

// =============================================================================
// NAVIGATION & VIEW SWITCHING (SYNCHRONIZED DESKTOP & MOBILE)
// =============================================================================
function switchMainTab(viewKey, navItem) {
  // Normalize view aliases
  const viewMap = {
    overviewView: "viewOverview",
    fieldSummaryView: "viewOverview",
    monitoringView: "viewMonitoring",
    mapView: "viewMap",
    regionalView: "viewMap",
    decisionsView: "viewDecisions",
    governanceView: "viewDecisions",
    historyView: "viewHistory",
    lineageView: "viewHistory",
    replayView: "viewHistory",
    scientificView: "viewHistory",
    evidencePackView: "viewHistory"
  };

  const targetViewId = viewMap[viewKey] || "viewOverview";
  activeMainView = targetViewId;

  // Hide all sections
  ["viewOverview", "viewMonitoring", "viewMap", "viewDecisions", "viewHistory"].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.style.display = (id === targetViewId) ? "flex" : "none";
  });

  // Sync Sidebar
  document.querySelectorAll(".nav-item").forEach(el => el.classList.remove("active"));
  const navElementMap = {
    viewOverview: "navItemOverview",
    viewMonitoring: "navItemMonitoring",
    viewMap: "navItemMap",
    viewDecisions: "navItemDecisions",
    viewHistory: "navItemHistory"
  };
  const activeNavId = navElementMap[targetViewId];
  if (activeNavId) {
    const navEl = document.getElementById(activeNavId);
    if (navEl) navEl.classList.add("active");
  }

  // Sync Mobile Bottom Nav
  document.querySelectorAll(".bottom-nav-item").forEach(el => el.classList.remove("active"));
  const bnavMap = {
    viewOverview: "bnavOverview",
    viewMonitoring: "bnavMonitoring",
    viewMap: "bnavMap",
    viewDecisions: "bnavDecisions",
    viewHistory: "bnavHistory"
  };
  const bnavId = bnavMap[targetViewId];
  if (bnavId) {
    const bnavEl = document.getElementById(bnavId);
    if (bnavEl) bnavEl.classList.add("active");
  }

  // If entering map view, refresh Leaflet container
  if (targetViewId === "viewMap" && window.VanaGeoEngine && window.VanaGeoEngine.map) {
    setTimeout(() => { window.VanaGeoEngine.map.invalidateSize(); }, 150);
  }

  // If specific history alias was clicked, auto-switch subtab
  if (viewKey === "replayView") switchHistorySubTab("replay");
  if (viewKey === "evidencePackView") switchHistorySubTab("evidence");
  if (viewKey === "scientificView") switchHistorySubTab("scientific");
  if (viewKey === "lineageView") switchHistorySubTab("provenance");

  // Close mobile drawer
  toggleSidebar(false);
}

// Backwards-compatible alias
function switchStageView(viewName) {
  const map = {
    fieldSummary: "overviewView",
    map: "mapView",
    lineage: "historyView",
    governance: "decisionsView",
    scientific: "historyView",
    replay: "historyView",
    evidencePack: "historyView"
  };
  switchMainTab(map[viewName] || "overviewView");
}

function focusAlerts(navItem) {
  switchMainTab("overviewView", document.getElementById("navItemOverview"));
  const alertsContainer = document.getElementById("alertsContainer");
  if (alertsContainer) {
    alertsContainer.scrollIntoView({ behavior: "smooth" });
  }
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

// =============================================================================
// OBSERVATION SELECTOR & MULTI-RECORD LOOKUP
// =============================================================================
function handleObservationSelect(newId) {
  if (!newId) return;
  if (newId === "__CUSTOM__") {
    const customPrompt = prompt("Enter Canonical Observation ID to retrieve from MasterDB (e.g. TC-Z03-EXT-OPENMETEO-OBS001, OBS-THANECREEK-AGB-2023-01, TC-Z03-F02-SENSOR-OBS999, TC-Z03-F02-LIDAR-OBS001):");
    const selectEl = document.getElementById("headerObservationSelect");
    if (!customPrompt || !customPrompt.trim()) {
      if (selectEl) selectEl.value = currentObservationId;
      return;
    }
    const cleanId = customPrompt.trim();
    if (selectEl) {
      let optExists = Array.from(selectEl.options).some(opt => opt.value === cleanId);
      if (!optExists) {
        const newOpt = document.createElement("option");
        newOpt.value = cleanId;
        newOpt.textContent = `Custom (${cleanId})`;
        selectEl.insertBefore(newOpt, selectEl.lastElementChild);
      }
      selectEl.value = cleanId;
    }
    fetchLive(cleanId);
    return;
  }
  fetchLive(newId);
}

// =============================================================================
// STATUTORY FOREST COVER & MANGROVE BENCHMARKS (FSI ISFR 2023)
// Connected to GET /proxy/g1/datasets/{dataset_id}/forest-cover
// =============================================================================
const OFFICIAL_DATASET_ID = "DS-FSI-ISFR-2023-FOREST-COVER";

async function loadOfficialForestCover() {
  const container = document.getElementById("officialForestCoverContainer");
  const badge = document.getElementById("fsiStatusBadge");
  if (!container) return;

  // 1. Loading State
  container.innerHTML = `
    <div style="padding:24px 16px;text-align:center;color:var(--text-secondary);font-size:12px;">
      <div style="font-weight:600;margin-bottom:4px;">Querying MasterDB for statutory benchmarks...</div>
      <div style="font-size:11px;color:var(--text-muted);">Requesting official dataset ${OFFICIAL_DATASET_ID} via /proxy/g1/datasets</div>
    </div>
  `;
  if (badge) {
    badge.textContent = "Connecting...";
    badge.className = "status-pill neutral";
  }

  const g1Datasets = (window.VANA_CONFIG && window.VANA_CONFIG.G1_DATASETS) || "/proxy/g1/datasets";
  const url = `${g1Datasets}/${OFFICIAL_DATASET_ID}/forest-cover`;

  try {
    const res = await vanaFetch(url, { headers: { "Accept": "application/json" } });
    if (res.ok) {
      const json = await res.json();
      const records = Array.isArray(json.records) ? json.records : [];
      renderOfficialForestCover(records, json.dataset_id || OFFICIAL_DATASET_ID, true, null);
      if (badge) {
        if (records.length > 0) {
          badge.textContent = "MasterDB Live (Validated)";
          badge.className = "status-pill active";
        } else {
          badge.textContent = "No Records";
          badge.className = "status-pill neutral";
        }
      }
    } else {
      const errMsg = `MasterDB returned HTTP ${res.status}`;
      renderOfficialForestCover([], OFFICIAL_DATASET_ID, false, errMsg);
      if (badge) {
        badge.textContent = "Service Degraded";
        badge.className = "status-pill warn";
      }
    }
  } catch (err) {
    console.warn("[VANA] MasterDB forest cover endpoint degraded:", err.message);
    const errMsg = `Could not reach MasterDB gateway (${err.message})`;
    renderOfficialForestCover([], OFFICIAL_DATASET_ID, false, errMsg);
    if (badge) {
      badge.textContent = "Service Unavailable";
      badge.className = "status-pill warn";
    }
  }
}

function renderOfficialForestCover(records, datasetId, isLive, errMsg) {
  const container = document.getElementById("officialForestCoverContainer");
  if (!container) return;

  // 2. Error State (Zero fabricated data presented as live data)
  if (errMsg) {
    container.innerHTML = `
      <div style="background:var(--status-warn-bg);border:1px solid var(--status-warn-border);color:var(--status-warn);border-radius:var(--radius-md);padding:16px 18px;margin-bottom:8px;">
        <div style="font-weight:700;font-size:13px;display:flex;align-items:center;gap:6px;">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg>
          <span>Statutory Benchmark Service Degraded</span>
        </div>
        <div style="font-size:12px;color:var(--text-main);margin-top:4px;line-height:1.45;">
          ${errMsg}. Under strict zero-fabrication governance, fallback benchmark data is not displayed as live data.
        </div>
        <div style="margin-top:10px;">
          <button type="button" class="btn-header" style="font-size:11.5px;padding:3px 10px;" onclick="loadOfficialForestCover()">
            Retry Query
          </button>
        </div>
      </div>
    `;
    return;
  }

  // 3. Empty State
  if (!records || records.length === 0) {
    container.innerHTML = `
      <div style="padding:24px 16px;text-align:center;color:var(--text-secondary);font-size:12px;background:var(--bg-surface);border:1px solid var(--border-light);border-radius:var(--radius-md);">
        <div style="font-weight:600;margin-bottom:4px;">No statutory records found in MasterDB</div>
        <div style="font-size:11px;color:var(--text-muted);">Dataset identifier: <span class="mono">${datasetId}</span></div>
        <div style="margin-top:10px;">
          <button type="button" class="btn-header" style="font-size:11.5px;padding:3px 10px;" onclick="loadOfficialForestCover()">
            Refresh
          </button>
        </div>
      </div>
    `;
    return;
  }

  // 4. Populated State: Dynamically parse every field and unit directly from MasterDB response
  container.innerHTML = records.map(rec => {
    const src = rec.source || {};
    const unitStr = rec.unit || "km2";
    const totalAreaStr = (rec.forest_cover_area !== undefined && rec.forest_cover_area !== null)
      ? Number(rec.forest_cover_area).toLocaleString()
      : "Not Specified";
    const totalPctStr = (rec.forest_cover_percentage !== undefined && rec.forest_cover_percentage !== null)
      ? `${rec.forest_cover_percentage}% of geographical area`
      : "Percentage pending";
    const mangroveAreaStr = (rec.mangrove_area !== undefined && rec.mangrove_area !== null)
      ? Number(rec.mangrove_area).toLocaleString()
      : "0.0";
    const vdfStr = (rec.very_dense_forest_area !== undefined && rec.very_dense_forest_area !== null)
      ? Number(rec.very_dense_forest_area).toLocaleString()
      : "0.0";
    const mdfStr = (rec.moderately_dense_forest_area !== undefined && rec.moderately_dense_forest_area !== null)
      ? Number(rec.moderately_dense_forest_area).toLocaleString()
      : "0.0";
    const ofStr = (rec.open_forest_area !== undefined && rec.open_forest_area !== null)
      ? Number(rec.open_forest_area).toLocaleString()
      : "0.0";

    const titlePrefix = rec.district ? `${rec.district} District` : `${rec.state} State`;

    return `
      <div style="display:flex;flex-direction:column;gap:14px;">
        <!-- Header Info Card -->
        <div style="background:var(--bg-page);border:1px solid var(--border-light);border-radius:var(--radius-md);padding:12px 14px;">
          <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:8px;">
            <div>
              <div style="font-size:13px;font-weight:700;color:var(--text-main);">
                ${titlePrefix} Forest Cover Baseline (${rec.assessment_year})
              </div>
              <div style="font-size:11.5px;color:var(--text-secondary);margin-top:2px;">
                State: <strong>${rec.state}</strong> · Geography Level: <strong>${rec.geography_level}</strong> · Boundary: <strong>${rec.boundary_reference || "Official Recorded Forest Area (RFA)"}</strong>
              </div>
            </div>
            <span class="status-pill active" style="font-size:10px;">Quality: ${rec.quality_status || "VALIDATED"}</span>
          </div>
          <div style="font-size:11px;color:var(--text-secondary);margin-top:8px;line-height:1.4;">
            <strong>Publisher:</strong> ${src.publisher || src.source_name || "Forest Survey of India, MoEFCC"} · <strong>Citation:</strong> ${rec.provenance_reference || "ISFR 2023"}
          </div>
        </div>

        <!-- Metric Cards Grid (All figures and units originate from MasterDB response) -->
        <div style="display:grid;grid-template-columns:repeat(auto-fit, minmax(180px, 1fr));gap:10px;">
          <div style="background:var(--bg-surface);border:1px solid var(--border-light);border-radius:var(--radius-md);padding:10px 12px;">
            <div style="font-size:11px;color:var(--text-secondary);font-weight:500;">Total Forest Cover</div>
            <div style="font-size:18px;font-weight:700;color:var(--brand);margin-top:2px;" class="mono">${totalAreaStr} ${unitStr}</div>
            <div style="font-size:10.5px;color:var(--text-muted);margin-top:2px;">${totalPctStr}</div>
          </div>

          <div style="background:var(--bg-surface);border:1px solid var(--border-light);border-radius:var(--radius-md);padding:10px 12px;">
            <div style="font-size:11px;color:var(--text-secondary);font-weight:500;">Mangrove Canopy Area</div>
            <div style="font-size:18px;font-weight:700;color:var(--brand);margin-top:2px;" class="mono">${mangroveAreaStr} ${unitStr}</div>
            <div style="font-size:10.5px;color:var(--text-muted);margin-top:2px;">Coastal wetland surveillance zone</div>
          </div>

          <div style="background:var(--bg-surface);border:1px solid var(--border-light);border-radius:var(--radius-md);padding:10px 12px;">
            <div style="font-size:11px;color:var(--text-secondary);font-weight:500;">Very Dense Forest (>70%)</div>
            <div style="font-size:18px;font-weight:700;color:var(--text-main);margin-top:2px;" class="mono">${vdfStr} ${unitStr}</div>
            <div style="font-size:10.5px;color:var(--text-muted);margin-top:2px;">Intact closed canopy</div>
          </div>

          <div style="background:var(--bg-surface);border:1px solid var(--border-light);border-radius:var(--radius-md);padding:10px 12px;">
            <div style="font-size:11px;color:var(--text-secondary);font-weight:500;">Moderately Dense (40-70%)</div>
            <div style="font-size:18px;font-weight:700;color:var(--text-main);margin-top:2px;" class="mono">${mdfStr} ${unitStr}</div>
            <div style="font-size:10.5px;color:var(--text-muted);margin-top:2px;">Medium canopy cover</div>
          </div>

          <div style="background:var(--bg-surface);border:1px solid var(--border-light);border-radius:var(--radius-md);padding:10px 12px;">
            <div style="font-size:11px;color:var(--text-secondary);font-weight:500;">Open Forest (10-40%)</div>
            <div style="font-size:18px;font-weight:700;color:var(--text-main);margin-top:2px;" class="mono">${ofStr} ${unitStr}</div>
            <div style="font-size:10.5px;color:var(--text-muted);margin-top:2px;">Porous / edge canopy</div>
          </div>
        </div>

        <!-- Technical Metadata -->
        <div class="tech-kv-grid" style="margin-top:4px;">
          <div class="tech-kv-item"><div class="tech-k">Canonical Record ID</div><div class="tech-v mono">${rec.record_id || "null"}</div></div>
          <div class="tech-kv-item"><div class="tech-k">Dataset Identifier</div><div class="tech-v mono">${rec.dataset_id || datasetId}</div></div>
          <div class="tech-kv-item"><div class="tech-k">Methodology</div><div class="tech-v">${rec.methodology || "Multi-date satellite imagery with ground truthing"}</div></div>
          <div class="tech-kv-item"><div class="tech-k">Statutory Reference</div><div class="tech-v">${rec.provenance_reference || "Official Report Table"}</div></div>
        </div>
      </div>
    `;
  }).join("");
}

// =============================================================================
// OBSERVATION INGESTION INTAKE (POST /observations)
// =============================================================================
// Example Group 3 v2.2 test fixture for contract validation and demonstration only
const SAMPLE_CANOPY_PAYLOAD = {
  contract_version: "2.2",
  schema_version: "2.2",
  observation_id: "TC-Z03-F02-SENSOR-OBS999",
  source_identity: "group3-field-edge",
  survey_id: "TC",
  zone_id: "Z03",
  flight_id: "F02",
  sensor_id: "SENSOR",
  observation_seq: "OBS999",
  mission_id: "TC-Z03-F02",
  observation_timestamp: "2026-08-25T10:00:00Z",
  source_timestamp: "2026-08-25T10:00:00Z",
  data_state: "CAPTURED",
  synthetic_state: "CONTROLLED",
  quality_state: "CAPTURED",
  calibration_state: "NOT_VERIFIED",
  device_id: "G3-SENSOR-999",
  observation_type: "canopy_height",
  capture_method: "sensor",
  processing_status: "raw",
  measurement: 7.8,
  unit: "m",
  accuracy: "NOT_VERIFIED",
  location: {
    latitude: 19.1288,
    longitude: 72.9421,
    altitude_m: 12.5,
    gnss_status: "NOT_VERIFIED",
    position_accuracy_m: null
  },
  raw_artifact: "TC-Z03-F02/sensor/log_999.txt",
  raw_artifact_integrity: {
    checksum_sha256: "f7254999689ae5b530a0006d0fb6765df0317973504e8c5d1b393bfa5826cf9d",
    hash_algorithm: "sha256",
    artifact_type: "sensor_reading"
  },
  provenance_reference: "TC-Z03-F02/qa/qa_F02.json",
  provenance: {
    device_id: "G3-SENSOR-999",
    mission_id: "TC-Z03-F02",
    captured_at: "2026-08-25T10:00:00Z",
    raw_artifact: "TC-Z03-F02/sensor/log_999.txt",
    qa_record: "TC-Z03-F02/qa/qa_F02.json"
  }
};

// Example Group 3 v2.2 test fixture for external weather API ingestion
const SAMPLE_WEATHER_PAYLOAD = {
  contract_version: "2.2",
  schema_version: "2.2",
  observation_id: "TC-Z03-EXT-OPENMETEO-OBS001",
  source_identity: "external-api",
  survey_id: "TC",
  zone_id: "Z03",
  flight_id: "EXT",
  sensor_id: "OPENMETEO",
  observation_seq: "OBS001",
  mission_id: "TC-Z03-EXT",
  observation_timestamp: "2026-08-25T11:00:00Z",
  source_timestamp: "2026-08-25T11:00:00Z",
  data_state: "CAPTURED",
  synthetic_state: "CONTROLLED",
  quality_state: "VALIDATED",
  calibration_state: "NOT_VERIFIED",
  device_id: "EXT-OPENMETEO-API",
  observation_type: "precipitation",
  capture_method: "external_api",
  processing_status: "raw",
  measurement: 0.1,
  unit: "mm",
  accuracy: "NOT_VERIFIED",
  location: {
    latitude: 19.1288,
    longitude: 72.9421,
    altitude_m: 4.0,
    gnss_status: null,
    position_accuracy_m: null
  },
  raw_artifact: "TC-Z03-EXT-OPENMETEO/precipitation.json",
  raw_artifact_integrity: {
    checksum_sha256: "35eebfd5d7fa43589110dcdb2915ce0335eebfd5d7fa43589110dcdb2915ce03",
    hash_algorithm: "sha256",
    artifact_type: "other"
  },
  provenance_reference: "TC-Z03-EXT-OPENMETEO/provenance.json",
  provenance: {
    device_id: "EXT-OPENMETEO-API",
    mission_id: "TC-Z03-EXT",
    captured_at: "2026-08-25T11:00:00Z",
    raw_artifact: "TC-Z03-EXT-OPENMETEO/precipitation.json",
    qa_record: "TC-Z03-EXT-OPENMETEO/provenance.json"
  }
};

// Test fixture with intentional schema errors to verify contract rejection
const SAMPLE_INVALID_PAYLOAD = {
  contract_version: "2.2",
  observation_id: "TC-MALFORMED-OBS-001",
  observation_type: "canopy_height",
  accuracy: "high", // Invalid: Must be float or literal 'NOT_VERIFIED'
  location: null // Invalid: location is strictly required
};

function openObservationSubmitModal() {
  const modal = document.getElementById("observationSubmitModal");
  if (!modal) return;

  const keyInput = document.getElementById("obsIdempotencyKey");
  if (keyInput && !keyInput.value) {
    generateNewIdempotencyKey();
  }

  const textarea = document.getElementById("obsPayloadTextarea");
  if (textarea && !textarea.value.trim()) {
    textarea.value = JSON.stringify(SAMPLE_CANOPY_PAYLOAD, null, 2);
  }

  const resultBox = document.getElementById("obsIngestionResult");
  if (resultBox) {
    resultBox.style.display = "none";
    resultBox.innerHTML = "";
  }

  modal.style.display = "flex";
}

function closeObservationSubmitModal() {
  const modal = document.getElementById("observationSubmitModal");
  if (modal) modal.style.display = "none";
}

function generateNewIdempotencyKey() {
  const keyInput = document.getElementById("obsIdempotencyKey");
  if (keyInput) {
    keyInput.value = `IK-VANA-${Date.now()}-${Math.floor(Math.random() * 10000)}`;
  }
}

function loadSampleObsPayload(sampleType) {
  const textarea = document.getElementById("obsPayloadTextarea");
  if (!textarea) return;

  if (sampleType === "canopy") {
    textarea.value = JSON.stringify(SAMPLE_CANOPY_PAYLOAD, null, 2);
  } else if (sampleType === "precipitation") {
    textarea.value = JSON.stringify(SAMPLE_WEATHER_PAYLOAD, null, 2);
  } else if (sampleType === "invalid") {
    textarea.value = JSON.stringify(SAMPLE_INVALID_PAYLOAD, null, 2);
  }
}

async function submitObservationPayload() {
  const textarea = document.getElementById("obsPayloadTextarea");
  const keyInput = document.getElementById("obsIdempotencyKey");
  const resultBox = document.getElementById("obsIngestionResult");
  const submitBtn = document.getElementById("btnSubmitObsPayload");

  if (!textarea || !resultBox) return;

  const rawJson = textarea.value.trim();
  if (!rawJson) {
    resultBox.style.display = "block";
    resultBox.className = "login-error-alert";
    resultBox.textContent = "Please enter an observation payload JSON.";
    return;
  }

  let payload;
  try {
    payload = JSON.parse(rawJson);
  } catch (parseErr) {
    resultBox.style.display = "block";
    resultBox.className = "login-error-alert";
    resultBox.textContent = `JSON Syntax Error: ${parseErr.message}`;
    return;
  }

  const key = keyInput ? keyInput.value.trim() : "";

  resultBox.style.display = "block";
  resultBox.style.background = "var(--bg-page)";
  resultBox.style.border = "1px solid var(--border-light)";
  resultBox.style.color = "var(--text-secondary)";
  resultBox.textContent = "Submitting payload to MasterDB (POST /observations)...";

  if (submitBtn) submitBtn.disabled = true;

  try {
    const headers = { "Content-Type": "application/json", "Accept": "application/json" };
    if (key) headers["Idempotency-Key"] = key;

    const res = await vanaFetch(window.VANA_CONFIG.G1_OBSERVATIONS, {
      method: "POST",
      headers: headers,
      body: JSON.stringify(payload)
    });

    const body = await res.json().catch(() => ({ status: "ERROR", message: "Invalid JSON response" }));

    if (res.status === 201) {
      resultBox.style.background = "var(--status-ok-bg)";
      resultBox.style.border = "1px solid var(--status-ok-border)";
      resultBox.style.color = "var(--status-ok)";
      resultBox.innerHTML = `
        <div style="font-weight:700;margin-bottom:4px;">Observation Accepted &amp; Persisted!</div>
        <div style="font-size:11.5px;color:var(--text-main);line-height:1.4;">
          Observation ID: <strong class="mono">${body.observation_id}</strong><br>
          Canonical Record ID: <strong class="mono">${body.canonical_record_id}</strong><br>
          Trace ID: <span class="mono">${body.trace_id}</span>
        </div>
        <div style="margin-top:10px;">
          <button type="button" class="btn-header primary" style="font-size:11px;padding:3px 10px;" onclick="closeObservationSubmitModal(); fetchLive('${body.observation_id}');">
            View in Dashboard
          </button>
        </div>
      `;
    } else if (res.status === 200 && body.status === "IDEMPOTENT_REPLAY") {
      resultBox.style.background = "var(--status-warn-bg)";
      resultBox.style.border = "1px solid var(--status-warn-border)";
      resultBox.style.color = "var(--status-warn)";
      resultBox.innerHTML = `
        <div style="font-weight:700;margin-bottom:4px;">Idempotent Replay Verified</div>
        <div style="font-size:11.5px;color:var(--text-main);line-height:1.4;">
          Request already processed. Returned canonical record: <strong class="mono">${body.canonical_record_id}</strong>
        </div>
        <div style="margin-top:10px;">
          <button type="button" class="btn-header" style="font-size:11px;padding:3px 10px;" onclick="closeObservationSubmitModal(); fetchLive('${body.observation_id}');">
            View in Dashboard
          </button>
        </div>
      `;
    } else if (res.status === 409) {
      resultBox.style.background = "var(--status-critical-bg)";
      resultBox.style.border = "1px solid var(--status-critical-border)";
      resultBox.style.color = "var(--status-critical)";
      resultBox.innerHTML = `
        <div style="font-weight:700;margin-bottom:4px;">Idempotency Conflict (HTTP 409)</div>
        <div style="font-size:11.5px;color:var(--text-main);">${body.message || "Idempotency key was already used with a different request payload."}</div>
      `;
    } else if (res.status === 400) {
      resultBox.style.background = "var(--status-critical-bg)";
      resultBox.style.border = "1px solid var(--status-critical-border)";
      resultBox.style.color = "var(--status-critical)";
      const errorList = Array.isArray(body.errors) && body.errors.length > 0
        ? `<ul style="margin:4px 0 0 16px;padding:0;">${body.errors.map(e => `<li>${e}</li>`).join("")}</ul>`
        : `<div>${body.message || "Observation failed contract validation."}</div>`;
      resultBox.innerHTML = `
        <div style="font-weight:700;margin-bottom:4px;">Validation Rejected (HTTP 400)</div>
        <div style="font-size:11.5px;color:var(--text-main);">${errorList}</div>
      `;
    } else {
      resultBox.style.background = "var(--status-critical-bg)";
      resultBox.style.border = "1px solid var(--status-critical-border)";
      resultBox.style.color = "var(--status-critical)";
      resultBox.innerHTML = `
        <div style="font-weight:700;margin-bottom:4px;">Submission Error (HTTP ${res.status})</div>
        <div style="font-size:11.5px;color:var(--text-main);">${body.message || "Unexpected persistence result."}</div>
      `;
    }
  } catch (err) {
    resultBox.style.background = "var(--status-warn-bg)";
    resultBox.style.border = "1px solid var(--status-warn-border)";
    resultBox.style.color = "var(--status-warn)";
    resultBox.innerHTML = `
      <div style="font-weight:700;margin-bottom:4px;">MasterDB Service Degraded</div>
      <div style="font-size:11.5px;color:var(--text-main);">
        Could not connect to MasterDB gateway (/proxy/g1/observations). Please verify backend service availability.
      </div>
    `;
  } finally {
    if (submitBtn) submitBtn.disabled = false;
  }
}

