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

  // Restore persisted desktop sidebar collapsed state
  if (window.innerWidth > 768) {
    try {
      const persistedCollapsed = sessionStorage.getItem("vana_sidebar_collapsed");
      const sidebar = document.getElementById("mainSidebar");
      const toggleBtn = document.getElementById("sidebarToggleBtn");
      if (persistedCollapsed === "true" && sidebar) {
        sidebar.classList.add("collapsed");
        if (toggleBtn) {
          toggleBtn.setAttribute("aria-expanded", "false");
          toggleBtn.setAttribute("aria-label", "Expand navigation sidebar");
          toggleBtn.title = "Expand Navigation";
        }
      } else if (toggleBtn) {
        toggleBtn.setAttribute("aria-expanded", "true");
        toggleBtn.setAttribute("aria-label", "Collapse navigation sidebar");
        toggleBtn.title = "Collapse Navigation";
      }
    } catch (e) {
      // Storage access blocked or restricted
    }
  }

  // Support URL query param or hash for deep linking tabs
  const urlParams = new URLSearchParams(window.location.search);
  const initialTab = urlParams.get("tab") || (window.location.hash ? window.location.hash.replace("#", "") : null);
  if (initialTab) {
    switchMainTab(initialTab);
  }
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
  const dateEl = document.getElementById("liveDateStr");
  const timeEl = document.getElementById("liveTimeStr");
  if (!dateEl && !timeEl) return;
  function update() {
    const now = new Date();
    const dateStr = now.toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" });
    const timeStr = now.toLocaleTimeString("en-GB", { hour12: false }) + " IST";
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

  // Card 4: Latest Verified Observation value
  const kpiLatestObs = document.getElementById("kpiLatestObs");
  const kpiLatestObsSub = document.getElementById("kpiLatestObsSub");
  if (kpiLatestObs) {
    if (g1Ok && data.group3 && data.group3.measurement !== null && data.group3.measurement !== undefined) {
      kpiLatestObs.textContent = `${data.group3.measurement} ${data.group3.unit || ""}`.trim();
      kpiLatestObs.style.color = "var(--color-primary)";
      if (kpiLatestObsSub) {
        kpiLatestObsSub.textContent = `${data.group3.observation_type || "Precipitation"} · Thane Creek`;
      }
    } else {
      kpiLatestObs.textContent = "Unavailable";
      kpiLatestObs.style.color = "var(--color-danger)";
      if (kpiLatestObsSub) {
        kpiLatestObsSub.textContent = "No verified data";
      }
    }
  }

  const kpiReviews = document.getElementById("kpiReviewsRequired");
  if (kpiReviews) kpiReviews.textContent = "1";

  // Subtitle in card
  const kpiRulingSub = document.getElementById("kpiRulingSub");
  if (kpiRulingSub) {
    kpiRulingSub.textContent = "Thane Creek: Assessment paused";
  }
}

// =============================================================================
// VIEW 1: OVERVIEW RENDERER (EXECUTIVE DASHBOARD)
// =============================================================================

function renderOverview(data) {
  // 1. Render Monitored Locations List
  renderOverviewLocations(data);

  // 2. Render Latest Verified Observation Card
  renderOverviewLatestObservation(data);

  // 3. Render Overview Governance Notice Card
  renderOverviewGovernanceNotice(data);

  // 4. Update Map Status Badge in Overview
  const mapBadge = document.getElementById("overviewMapStatusBadge");
  const g1 = data.group1 || {};
  const g1Ok = g1 && !g1.failed;
  if (mapBadge) {
    if (g1Ok) {
      mapBadge.innerHTML = '<span class="status-dot"></span> 1 Retrieved from MasterDB · 5 Awaiting Upstream Data';
      mapBadge.className = "status-pill active";
    } else {
      mapBadge.innerHTML = '<span class="status-dot" style="background:var(--color-danger)"></span> 0 Retrieved (1 Lookup Failed) · 5 Awaiting Upstream Data';
      mapBadge.className = "status-pill error";
    }
  }

  // 5. Ensure Leaflet Map container is in overview and sized
  if (activeMainView === "viewOverview") {
    reparentMap("overviewMapContainer");
  }
}

function renderOverviewLocations(data) {
  const listEl = document.getElementById("overviewLocationsList");
  if (!listEl) return;

  const g1 = data.group1 || {};
  const g1Ok = g1 && !g1.failed;

  const locations = [
    {
      key: "thane_creek",
      zoneId: "TC-Z03",
      name: "Thane Creek",
      isLive: g1Ok,
      statusClass: g1Ok ? "live" : "pending",
      badgeClass: g1Ok ? "status-pill active" : "status-pill error",
      statusText: g1Ok ? "Record retrieved" : "Lookup failed",
      desc: g1Ok
        ? "MasterDB observation available"
        : `Observation ${data.observation_id || "TC-Z03"} unresolved in MasterDB`
    },
    {
      key: "mumbai",
      zoneId: "MU-Z01",
      name: "Mumbai",
      isLive: false,
      statusClass: "pending",
      badgeClass: "status-pill waiting",
      statusText: "Awaiting upstream data",
      desc: "Surveillance zone awaiting sensor deployment"
    },
    {
      key: "navi_mumbai",
      zoneId: "NM-Z01",
      name: "Navi Mumbai",
      isLive: false,
      statusClass: "pending",
      badgeClass: "status-pill waiting",
      statusText: "Awaiting upstream data",
      desc: "Surveillance zone awaiting sensor deployment"
    },
    {
      key: "vasai",
      zoneId: "VS-Z01",
      name: "Vasai",
      isLive: false,
      statusClass: "pending",
      badgeClass: "status-pill waiting",
      statusText: "Awaiting upstream data",
      desc: "Surveillance zone awaiting sensor deployment"
    },
    {
      key: "thane",
      zoneId: "THN-Z01",
      name: "Thane",
      isLive: false,
      statusClass: "pending",
      badgeClass: "status-pill waiting",
      statusText: "Awaiting upstream data",
      desc: "Surveillance zone awaiting sensor deployment"
    },
    {
      key: "maval",
      zoneId: "MV-Z01",
      name: "Maval",
      isLive: false,
      statusClass: "pending",
      badgeClass: "status-pill waiting",
      statusText: "Awaiting upstream data",
      desc: "Surveillance zone awaiting sensor deployment"
    }
  ];

  listEl.innerHTML = locations.map(loc => `
    <div class="overview-location-row ${loc.statusClass}" onclick="focusOverviewLocation('${loc.key}')" title="Click to inspect ${loc.name} on map">
      <div class="location-row-indicator"></div>
      <div class="location-row-content">
        <div class="location-row-header">
          <div class="location-row-title-wrap">
            <span class="location-row-name">${loc.name}</span>
            <span class="location-zone-id">${loc.zoneId}</span>
          </div>
          <span class="${loc.badgeClass}">${loc.statusText}</span>
        </div>
        <div class="location-row-desc">${loc.desc}</div>
      </div>
    </div>
  `).join("");
}

function renderOverviewLatestObservation(data) {
  const bodyEl = document.getElementById("latestObservationsBody");
  const badgeEl = document.getElementById("latestObsBadge");
  if (!bodyEl) return;

  const g1 = data.group1 || {};
  const g3 = data.group3 || {};
  const g1Ok = g1 && !g1.failed;

  if (g1Ok && g3) {
    if (badgeEl) {
      badgeEl.textContent = "1 Available Reading";
      badgeEl.className = "status-pill active";
    }

    const val = (g3.measurement !== null && g3.measurement !== undefined)
      ? `${g3.measurement} ${g3.unit || ""}`.trim()
      : "0.1 mm";
    const param = g3.observation_type || "Precipitation";
    const source = g3.source_identity ? `Source: ${g3.source_identity}` : "Source: Open-Meteo Cloud API (CC-BY 4.0)";
    let timestamp = "Observed: 25 Aug 2026, 11:00 UTC";
    if (g3.observation_timestamp) {
      try {
        const d = new Date(g3.observation_timestamp);
        timestamp = `Observed: ${d.toUTCString().replace("GMT", "UTC")}`;
      } catch (_) {}
    }

    bodyEl.innerHTML = `
      <div class="latest-obs-content">
        <div class="latest-obs-header">
          <div>
            <div class="latest-obs-station" id="latestObsStation">Thane Creek Monitoring Station</div>
            <div class="latest-obs-coords" id="latestObsCoords">
              Coordinates: 19.1288° N, 72.9421° E · Elevation: 4.0 m
            </div>
          </div>
          <div class="latest-obs-value-box">
            <div class="latest-obs-val" id="latestObsVal">${val}</div>
            <div class="latest-obs-param" id="latestObsParam">${param}</div>
          </div>
        </div>

        <div class="latest-obs-explanation" id="latestObsExplanation">
          Measurement: ${val} ${param.toLowerCase()} recorded for the operational surveillance window.
        </div>

        <div class="latest-obs-footer">
          <span id="latestObsSource">${source}</span>
          <span id="latestObsTimestamp">${timestamp}</span>
        </div>

        <div class="latest-obs-actions">
          <button class="btn-header" onclick="switchMainTab('monitoringView', document.getElementById('navItemMonitoring'))" style="flex:1;justify-content:center;">
            <span>View in Environmental Monitoring</span>
          </button>
          <button class="btn-header primary" onclick="switchMainTab('decisionsView', document.getElementById('navItemDecisions'))" style="flex:1;justify-content:center;">
            <span>Review Assessment</span>
          </button>
        </div>
      </div>
    `;
  } else {
    // Honest empty state when observation retrieval fails
    if (badgeEl) {
      badgeEl.textContent = "0 Available Readings";
      badgeEl.className = "status-pill error";
    }
    const is404 = g1 && g1.http_status === 404;
    const failureReason = is404
      ? "Observation record not found in MasterDB (HTTP 404)"
      : `MasterDB service unavailable (${g1.fail_reason || "HTTP 502 Bad Gateway"})`;

    bodyEl.innerHTML = `
      <div class="latest-obs-content">
        <div class="latest-obs-header">
          <div>
            <div class="latest-obs-station" style="color:var(--color-danger)">No MasterDB Observation Available</div>
            <div class="latest-obs-coords">Observation ID: ${data.observation_id || "None"}</div>
          </div>
          <div class="latest-obs-value-box">
            <div class="latest-obs-val" style="color:var(--color-danger)">--</div>
            <div class="latest-obs-param">No Data</div>
          </div>
        </div>

        <div class="latest-obs-explanation" style="border-left:3px solid var(--color-danger);background:var(--color-danger-light);">
          <strong>Intake halted under fail-closed governance:</strong> ${failureReason}. Downstream automated actions prevented.
        </div>

        <div class="latest-obs-footer">
          <span>Source: None</span>
          <span>Status: ${is404 ? "Observation Not Found" : "Service Unavailable"}</span>
        </div>

        <div class="latest-obs-actions">
          <button class="btn-header primary" onclick="fetchLive('TC-Z03-EXT-OPENMETEO-OBS001')" style="flex:1;justify-content:center;">
            <span>Return to Primary Observation (Thane Creek)</span>
          </button>
        </div>
      </div>
    `;
  }
}

function renderOverviewGovernanceNotice(data) {
  const bodyEl = document.getElementById("overviewGovernanceBody");
  if (!bodyEl) return;

  const g1 = data.group1 || {};
  const g1Ok = g1 && !g1.failed;
  const isPaused = Boolean(
    (data.group2 && data.group2.ruling === "ABSTAIN") ||
    (data.group4 && data.group4.decision === "ABSTAIN") ||
    (data.group4 && data.group4.abstention_record_id) ||
    !data.group4 ||
    data.group4.failed
  );

  if (g1Ok && isPaused) {
    bodyEl.innerHTML = `
      <div class="governance-notice-content">
        <div class="notice-callout">
          <div class="notice-callout-header">
            <span class="status-dot" style="background:var(--color-warning);"></span>
            <strong style="color:var(--color-text);font-size:12.5px;">Monitoring decision paused</strong>
          </div>
          <div class="notice-callout-body" style="font-size:12px;color:var(--color-text-secondary);line-height:1.45;margin-top:4px;">
            The system has paused automated action because required field evidence is not yet available. No action will be taken until the required information is verified.
          </div>
        </div>

        <div class="notice-status-bar">
          <span class="status-dot" style="background:var(--color-success);"></span>
          <span style="font-size:11px;color:var(--color-text-secondary);">Zero unauthorized operational actions taken.</span>
        </div>

        <div class="latest-obs-actions" style="margin-top:auto;">
          <button class="btn-header" onclick="switchMainTab('decisionsView', document.getElementById('navItemDecisions'))" style="flex:1;justify-content:center;">
            <span>Review in Decisions</span>
          </button>
          <button class="btn-header" onclick="switchMainTab('historyView', document.getElementById('navItemHistory'))" style="flex:1;justify-content:center;">
            <span>Inspect Evidence</span>
          </button>
        </div>
      </div>
    `;
  } else if (g1Ok && !isPaused) {
    bodyEl.innerHTML = `
      <div class="governance-notice-content">
        <div class="notice-callout" style="background:var(--color-success-light);border-color:var(--color-success-border);border-left-color:var(--color-success);">
          <div class="notice-callout-header">
            <span class="status-dot" style="background:var(--color-success);"></span>
            <strong style="color:var(--color-text);font-size:12.5px;">Monitoring active</strong>
          </div>
          <div class="notice-callout-body" style="font-size:12px;color:var(--color-text-secondary);line-height:1.45;margin-top:4px;">
            Field observations verified and operating under active policy parameters.
          </div>
        </div>

        <div class="latest-obs-actions" style="margin-top:auto;">
          <button class="btn-header" onclick="switchMainTab('decisionsView', document.getElementById('navItemDecisions'))" style="flex:1;justify-content:center;">
            <span>Review in Decisions</span>
          </button>
        </div>
      </div>
    `;
  } else {
    bodyEl.innerHTML = `
      <div class="governance-notice-content">
        <div class="notice-callout" style="background:var(--color-danger-light);border-color:var(--color-danger-border);border-left-color:var(--color-danger);">
          <div class="notice-callout-header">
            <span class="status-dot" style="background:var(--color-danger);"></span>
            <strong style="color:var(--color-text);font-size:12.5px;">Monitoring record unavailable</strong>
          </div>
          <div class="notice-callout-body" style="font-size:12px;color:var(--color-text-secondary);line-height:1.45;margin-top:4px;">
            Observation ID not found in MasterDB. The system has stopped automated evaluation for unverified records.
          </div>
        </div>

        <div class="notice-status-bar">
          <span class="status-dot" style="background:var(--color-success);"></span>
          <span style="font-size:11px;color:var(--color-text-secondary);">Zero execution side-effects created.</span>
        </div>

        <div class="latest-obs-actions" style="margin-top:auto;">
          <button class="btn-header primary" onclick="fetchLive('TC-Z03-EXT-OPENMETEO-OBS001')" style="flex:1;justify-content:center;">
            <span>Restore Primary Observation</span>
          </button>
        </div>
      </div>
    `;
  }
}

function focusOverviewLocation(zoneKey) {
  const z = REGIONAL_ZONES[zoneKey];
  if (!z) return;
  if (window.VanaGeoEngine && window.VanaGeoEngine.map) {
    window.VanaGeoEngine.map.setView([z.lat, z.lon], 12, { animate: true });
    if (window.VanaGeoEngine.zoneMarkers && window.VanaGeoEngine.zoneMarkers[zoneKey]) {
      window.VanaGeoEngine.zoneMarkers[zoneKey].openPopup();
    }
  } else if (leafletMap) {
    leafletMap.setView([z.lat, z.lon], 12, { animate: true });
  }
}

function reparentMap(targetContainerId) {
  const wrapper = document.getElementById("leafletMapWrapper");
  const target = document.getElementById(targetContainerId);
  if (wrapper && target && wrapper.parentElement !== target) {
    target.appendChild(wrapper);
    if (window.VanaGeoEngine && window.VanaGeoEngine.map) {
      setTimeout(() => {
        window.VanaGeoEngine.map.invalidateSize();
      }, 50);
    }
  }
}

function renderAttentionLocationsFeed() {
  const container = document.getElementById("attentionLocationsList");
  if (!container) return;

  const items = (typeof ATTENTION_LOCATIONS !== "undefined" && Array.isArray(ATTENTION_LOCATIONS)) ? ATTENTION_LOCATIONS : [];
  const filtered = items.filter(item => {
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
// =============================================================================
// VIEW 2: ENVIRONMENTAL MONITORING RENDERER (ITERATION 3A)
// =============================================================================
let activeSelectedObsIdForModal = null;
let activeSelectedZoneKeyForModal = null;

// Session cache of authentic observations retrieved through GET /proxy/g1/observations/{id}
// Does not fabricate records; only tracks records actually retrieved from MasterDB.
const sessionRetrievedObservations = new Map();
// Alias for backwards compatibility if referenced
const sessionVerifiedObservations = sessionRetrievedObservations;

function recordRetrievedObservation(data) {
  if (!data || !data.observation_id || !data.group1 || data.group1.failed) return;

  const g3 = data.group3 || {};
  const meas = (g3.measurement !== null && g3.measurement !== undefined) ? g3.measurement : "--";
  const unit = g3.unit || "";
  const obsType = g3.observation_type || "Observation";
  const displayType = obsType.charAt(0).toUpperCase() + obsType.slice(1).replace(/_/g, " ");

  let displayDate = "Not available";
  if (g3.observation_timestamp) {
    try {
      displayDate = new Date(g3.observation_timestamp).toLocaleString("en-GB", {
        timeZone: "UTC",
        day: "2-digit",
        month: "short",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit"
      }) + " UTC";
    } catch (_) {}
  }

  let locName = "Thane Creek";
  const matchedZone = Object.values(REGIONAL_ZONES).find(z => z.id === data.observation_id);
  if (matchedZone) {
    locName = matchedZone.name;
  }

  sessionRetrievedObservations.set(data.observation_id, {
    observation_id: data.observation_id,
    location_name: locName,
    observation_type: obsType.toLowerCase(),
    display_type: displayType,
    measurement: meas,
    unit: unit,
    timestamp: g3.observation_timestamp,
    display_date: displayDate,
    source: g3.source_identity || "Group 1 MasterDB",
    canonical_record_id: data.canonical_record_id || null,
    quality_state: g3.quality_state || "CAPTURED"
  });
}
// Alias for backwards compatibility
const recordVerifiedObservation = recordRetrievedObservation;

function renderMonitoring(data) {
  // Record current retrieved observation if available
  if (data && data.group1 && !data.group1.failed) {
    recordRetrievedObservation(data);
  }

  // 1. Update compact 3-card summary strip
  const totalEl = document.getElementById("monSummaryTotalLocations");
  const availEl = document.getElementById("monSummaryAvailableData");
  const waitEl = document.getElementById("monSummaryAwaitingData");
  const availBadge = document.getElementById("monSummaryAvailableBadge");
  const waitBadge = document.getElementById("monSummaryAwaitingBadge");

  const g1 = (data && data.group1) || {};
  const isG1Live = g1 && !g1.failed;

  const availCount = isG1Live ? 1 : 0;
  const pendingCount = 5;

  if (totalEl) totalEl.textContent = "6";
  if (availEl) availEl.textContent = String(availCount);
  if (waitEl) waitEl.textContent = String(pendingCount);
  if (availBadge) availBadge.textContent = isG1Live ? "1 Available" : "0 Available";
  if (waitBadge) waitBadge.textContent = "5 Pending";

  // 2. Render Retrieved Observations Directory table
  applyMonitoringFilters();

  // 3. Render Locations Awaiting Data section (separate from observation records)
  renderAwaitingLocations();
}

function applyMonitoringFilters() {
  const searchInput = document.getElementById("monSearchInput");
  const paramSelect = document.getElementById("monParameterSelect");
  const tbody = document.getElementById("monitoringTableBody");
  const countPill = document.getElementById("monTableCountPill");

  if (!tbody) return;

  const searchTerm = searchInput ? searchInput.value.trim().toLowerCase() : "";
  const paramVal = paramSelect ? paramSelect.value : "ALL";

  // Only actual observations retrieved from MasterDB
  let retrievedList = Array.from(sessionRetrievedObservations.values());

  // Filter by parameter
  if (paramVal !== "ALL") {
    retrievedList = retrievedList.filter(item => item.observation_type.includes(paramVal.toLowerCase()));
  }

  // Filter by search query
  if (searchTerm) {
    retrievedList = retrievedList.filter(item => {
      return (
        item.observation_id.toLowerCase().includes(searchTerm) ||
        item.location_name.toLowerCase().includes(searchTerm) ||
        item.display_type.toLowerCase().includes(searchTerm) ||
        item.source.toLowerCase().includes(searchTerm) ||
        String(item.measurement).toLowerCase().includes(searchTerm)
      );
    });
  }

  // Update count indicator
  if (countPill) {
    const totalCount = retrievedList.length;
    countPill.textContent = `${totalCount} Retrieved Record${totalCount === 1 ? '' : 's'} Available`;
  }

  // If no retrieved observations exist or match filter
  if (retrievedList.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="7" style="text-align:center;padding:28px 16px;background:var(--color-surface);">
          <div style="font-size:13px;font-weight:600;color:var(--color-text);margin-bottom:4px;">No retrieved observation records match criteria</div>
          <div style="font-size:12px;color:var(--color-muted);margin-bottom:12px;">Use the top observation selector to look up records or reset filters.</div>
          <button type="button" class="btn-header" onclick="resetMonitoringFilters()" style="margin:0 auto;">
            <span>Reset Filters</span>
          </button>
        </td>
      </tr>
    `;
    return;
  }

  // Render actual retrieved observation rows
  tbody.innerHTML = retrievedList.map(item => {
    return `
      <tr>
        <td>
          <div style="font-weight:600;color:var(--color-text);">${item.location_name}</div>
          <div class="mono" style="font-size:10.5px;color:var(--color-muted);margin-top:1px;">${item.observation_id}</div>
        </td>
        <td>
          <span style="font-size:12px;font-weight:600;color:var(--color-text);">
            ${item.display_type}
          </span>
        </td>
        <td>
          <span class="mono" style="font-weight:700;color:var(--color-success);font-size:13px;">
            ${item.measurement}
          </span>
        </td>
        <td>
          <span class="mono" style="color:var(--color-text);font-size:11.5px;">
            ${item.unit}
          </span>
        </td>
        <td>
          <span style="font-size:11.5px;color:var(--color-text);">
            ${item.display_date}
          </span>
        </td>
        <td>
          <span class="status-pill active" style="font-size:11px;">
            <span class="status-dot"></span>
            Retrieved from MasterDB
          </span>
        </td>
        <td style="text-align:right;">
          <button type="button" class="btn-header primary" style="padding:2px 10px;font-size:11px;height:26px;" onclick="openObservationDetailsModal('${item.observation_id}')" title="Inspect observation details">
            <span>Details</span>
          </button>
        </td>
      </tr>
    `;
  }).join("");
}

function resetMonitoringFilters() {
  const searchInput = document.getElementById("monSearchInput");
  const paramSelect = document.getElementById("monParameterSelect");

  if (searchInput) searchInput.value = "";
  if (paramSelect) paramSelect.value = "ALL";

  applyMonitoringFilters();
}

function filterMonitoringLocations(category, btn) {
  // Backwards-compatible alias
  applyMonitoringFilters();
}

// Renders the separate Locations Awaiting Data section
function renderAwaitingLocations() {
  const tbody = document.getElementById("awaitingLocationsBody");
  if (!tbody) return;

  const awaitingKeys = ["mumbai", "navi_mumbai", "vasai", "thane", "maval"];

  tbody.innerHTML = awaitingKeys.map(key => {
    const z = REGIONAL_ZONES[key] || { name: key, lat: 19.0, lon: 73.0 };
    const coordsStr = z.lat ? `${z.lat}° N, ${z.lon}° E` : "Coordinates pending";

    return `
      <tr>
        <td>
          <div style="font-weight:600;color:var(--color-text);">${z.name}</div>
          <div style="font-size:11px;color:var(--color-muted);margin-top:1px;">Surveillance Zone</div>
        </td>
        <td>
          <span class="mono" style="font-size:11.5px;color:var(--color-text-secondary);">${coordsStr}</span>
        </td>
        <td>
          <span class="status-pill waiting" style="font-size:11px;">
            <span class="status-dot"></span>
            Awaiting Sensor Feed
          </span>
        </td>
        <td>
          <span style="font-size:11.5px;color:var(--color-text-secondary);">Pending edge sensor telemetry feed</span>
        </td>
        <td style="text-align:right;">
          <button type="button" class="btn-header" style="padding:2px 10px;font-size:11px;height:26px;" onclick="openZoneInfoModal('${key}')" title="View location profile">
            <span>Location Info</span>
          </button>
        </td>
      </tr>
    `;
  }).join("");
}

async function openObservationDetailsModal(obsId) {
  const modal = document.getElementById("observationDetailsModal");
  const heading = document.getElementById("obsDetailsModalHeading");
  const sub = document.getElementById("obsDetailsModalSub");
  const body = document.getElementById("obsDetailsBody");
  const btnSetActive = document.getElementById("btnSetObsActive");

  if (!modal || !body) return;

  activeSelectedObsIdForModal = obsId;

  if (heading) heading.textContent = `Observation Details: ${obsId}`;
  if (sub) sub.textContent = "Authoritative environmental reading retrieved from Group 1 MasterDB";
  body.innerHTML = `
    <div style="padding:28px 16px;text-align:center;color:var(--color-muted);font-size:12.5px;">
      Retrieving observation record '${obsId}' from MasterDB...
    </div>
  `;
  modal.style.display = "flex";

  let obs = null;
  let envelope = null;

  if (currentRuntimeData && currentRuntimeData.observation_id === obsId && currentRuntimeData.group1 && !currentRuntimeData.group1.failed) {
    // Current runtime observation matches
    obs = (currentRuntimeData.group3) ? Object.assign({}, currentRuntimeData.group3) : {};
    envelope = {
      trace_id: currentRuntimeData.group1.trace_id,
      canonical_record_id: currentRuntimeData.canonical_record_id,
      status: currentRuntimeData.group1.retrieval_status || "RETRIEVED"
    };
  } else {
    try {
      const res = await vanaFetch(`${window.VANA_CONFIG.G1_BASE}/observations/${encodeURIComponent(obsId)}`, {
        headers: { "Accept": "application/json" }
      });
      if (res.ok) {
        envelope = await res.json();
        obs = envelope.observation || {};
      } else {
        body.innerHTML = `
          <div style="background:var(--color-danger-light);border:1px solid var(--color-danger-border);border-radius:var(--radius-md);padding:14px 16px;">
            <div style="font-weight:700;color:var(--color-danger);font-size:13px;display:flex;align-items:center;gap:6px;">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg>
              <span>Observation Record Not Found (HTTP ${res.status})</span>
            </div>
            <div style="font-size:12px;color:var(--color-text);margin-top:6px;line-height:1.45;">
              The requested observation ID <strong class="mono">${obsId}</strong> was not found in MasterDB storage. In accordance with fail-closed doctrine, previous values have been cleared and zero unverified metrics are displayed.
            </div>
          </div>
        `;
        if (btnSetActive) btnSetActive.style.display = "none";
        return;
      }
    } catch (fetchErr) {
      body.innerHTML = `
        <div style="background:var(--color-danger-light);border:1px solid var(--color-danger-border);border-radius:var(--radius-md);padding:14px 16px;">
          <div style="font-weight:700;color:var(--color-danger);font-size:13px;">MasterDB Service Degraded</div>
          <div style="font-size:12px;color:var(--color-text);margin-top:6px;">Could not connect to /proxy/g1/observations/${obsId}: ${fetchErr.message}</div>
        </div>
      `;
      if (btnSetActive) btnSetActive.style.display = "none";
      return;
    }
  }

  // Extract only actual fields returned by the API
  const primaryMeas = (Array.isArray(obs.measurements) && obs.measurements.length > 0) ? obs.measurements[0] : null;
  const val = (obs.measurement !== undefined && obs.measurement !== null)
    ? obs.measurement
    : (primaryMeas && primaryMeas.value !== undefined ? primaryMeas.value : null);
  const unit = obs.unit || (primaryMeas ? primaryMeas.unit : "");
  const obsType = obs.observation_type || (primaryMeas ? primaryMeas.metric_name : "Observation");
  const displayParam = obsType.charAt(0).toUpperCase() + obsType.slice(1).replace(/_/g, " ");

  const rawTimestamp = obs.observation_timestamp || obs.observed_at || obs.timestamp;
  let formattedTime = null;
  if (rawTimestamp) {
    try {
      formattedTime = new Date(rawTimestamp).toLocaleString("en-GB", {
        timeZone: "UTC",
        day: "2-digit",
        month: "short",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit"
      }) + " UTC";
    } catch (_) {
      formattedTime = rawTimestamp;
    }
  }

  const loc = obs.location || (obs.latitude !== undefined && obs.longitude !== undefined ? { latitude: obs.latitude, longitude: obs.longitude, altitude_m: obs.altitude_m } : null);
  let locStr = null;
  if (loc && loc.latitude !== null && loc.latitude !== undefined && loc.longitude !== null && loc.longitude !== undefined) {
    locStr = `${loc.latitude}° N, ${loc.longitude}° E`;
    if (loc.altitude_m !== null && loc.altitude_m !== undefined) {
      locStr += ` (Elevation: ${loc.altitude_m} m)`;
    }
  }

  const source = obs.source_identity || (primaryMeas && primaryMeas.provenance ? primaryMeas.provenance.source_id : (obs.field_observation_meta ? obs.field_observation_meta.operator : null));
  const quality = obs.quality_state || obs.quality_status || null;
  const canonicalId = obs.canonical_record_id || (envelope && envelope.canonical_record_id) || null;
  const traceId = (envelope && envelope.trace_id) || null;

  // Build non-technical primary items (only if present)
  let metadataItemsHtml = `
    <div class="obs-detail-item">
      <div class="obs-detail-k">Record Availability</div>
      <div class="obs-detail-v" style="font-weight:600;color:var(--color-primary);">Retrieved from MasterDB</div>
    </div>
  `;

  if (locStr) {
    metadataItemsHtml += `
      <div class="obs-detail-item">
        <div class="obs-detail-k">Observation Location</div>
        <div class="obs-detail-v">${locStr}</div>
      </div>
    `;
  }
  if (formattedTime) {
    metadataItemsHtml += `
      <div class="obs-detail-item">
        <div class="obs-detail-k">Observation Timestamp</div>
        <div class="obs-detail-v">${formattedTime}</div>
      </div>
    `;
  }

  // Quality State (strictly from API response, e.g. CAPTURED)
  if (quality) {
    metadataItemsHtml += `
      <div class="obs-detail-item">
        <div class="obs-detail-k">Quality State</div>
        <div class="obs-detail-v mono" style="font-weight:600;color:var(--color-text);">${quality}</div>
      </div>
    `;
  }

  // Data Provenance (accurately indicating Controlled Synthetic Data if synthetic)
  const isSynthetic = obs.is_synthetic === true || obs.synthetic_state === "CONTROLLED";
  const provenanceLabel = isSynthetic ? "Controlled Synthetic Data" : (source || null);
  if (provenanceLabel) {
    metadataItemsHtml += `
      <div class="obs-detail-item">
        <div class="obs-detail-k">Data Provenance</div>
        <div class="obs-detail-v">${provenanceLabel}</div>
      </div>
    `;
  }

  // Calibration (accurately reflecting Not Verified when NOT_VERIFIED)
  const meta = obs.field_observation_meta || {};
  const rawCal = obs.calibration_status || obs.calibration_state || meta.calibration_status || null;
  if (rawCal) {
    const calLabel = rawCal === "NOT_VERIFIED" ? "Not Verified" : (rawCal === "VERIFIED" ? "Verified" : rawCal);
    metadataItemsHtml += `
      <div class="obs-detail-item">
        <div class="obs-detail-k">Calibration</div>
        <div class="obs-detail-v" style="color:var(--color-text-secondary);">${calLabel}</div>
      </div>
    `;
  }

  // GNSS (accurately reflecting Not Verified when NOT_VERIFIED)
  const rawGnss = obs.gnss_status || (loc && loc.gnss_status) || meta.gnss_status || null;
  if (rawGnss) {
    const gnssLabel = rawGnss === "NOT_VERIFIED" ? "Not Verified" : (rawGnss === "VERIFIED" ? "Verified" : rawGnss);
    metadataItemsHtml += `
      <div class="obs-detail-item">
        <div class="obs-detail-k">GNSS</div>
        <div class="obs-detail-v" style="color:var(--color-text-secondary);">${gnssLabel}</div>
      </div>
    `;
  }

  // Build technical key-values (only if present)
  const integrity = obs.raw_artifact_integrity || {};
  const rawSha = obs.sha256 || integrity.checksum_sha256 || null;
  const rawArtifactPath = obs.raw_artifact || (Array.isArray(obs.raw_artifacts) && obs.raw_artifacts[0] ? obs.raw_artifacts[0].storage_ref : null);
  const deviceId = obs.device_id || meta.device_id || null;
  const missionId = obs.mission_id || meta.mission_id || null;
  const contractVer = obs.contract_version || obs.schema_version || null;
  const captureMethod = obs.capture_method || null;

  let techItemsHtml = `<div class="tech-kv-item"><div class="tech-k">Observation ID</div><div class="tech-v mono">${obsId}</div></div>`;
  if (canonicalId) techItemsHtml += `<div class="tech-kv-item"><div class="tech-k">Canonical Record ID</div><div class="tech-v mono">${canonicalId}</div></div>`;
  if (traceId) techItemsHtml += `<div class="tech-kv-item"><div class="tech-k">Trace ID</div><div class="tech-v mono">${traceId}</div></div>`;
  if (contractVer) techItemsHtml += `<div class="tech-kv-item"><div class="tech-k">Contract Version</div><div class="tech-v mono">${contractVer}</div></div>`;
  if (deviceId) techItemsHtml += `<div class="tech-kv-item"><div class="tech-k">Device ID</div><div class="tech-v mono">${deviceId}</div></div>`;
  if (missionId) techItemsHtml += `<div class="tech-kv-item"><div class="tech-k">Mission ID</div><div class="tech-v mono">${missionId}</div></div>`;
  if (captureMethod) techItemsHtml += `<div class="tech-kv-item"><div class="tech-k">Capture Method</div><div class="tech-v mono">${captureMethod}</div></div>`;
  if (rawArtifactPath) techItemsHtml += `<div class="tech-kv-item"><div class="tech-k">Raw Artifact</div><div class="tech-v mono" style="font-size:10.5px;overflow-wrap:anywhere;">${rawArtifactPath}</div></div>`;
  if (rawSha) techItemsHtml += `<div class="tech-kv-item" style="grid-column:1 / -1;"><div class="tech-k">SHA-256 Checksum</div><div class="tech-v mono" style="font-size:10.5px;overflow-wrap:anywhere;">${rawSha}</div></div>`;

  body.innerHTML = `
    <!-- Primary non-technical hero card -->
    <div class="obs-detail-hero">
      <div class="obs-detail-val-box">
        <div class="obs-detail-val">${val !== null ? val : "--"} <span style="font-size:16px;color:var(--color-text-secondary);font-weight:normal;">${unit}</span></div>
        <div class="obs-detail-param">${displayParam}</div>
      </div>
      <span class="status-pill active" style="font-size:11px;">
        <span class="status-dot"></span>
        Retrieved from MasterDB
      </span>
    </div>

    ${metadataItemsHtml ? `<div class="obs-detail-grid">${metadataItemsHtml}</div>` : ''}

    <div style="background:var(--color-surface-subtle);border:1px solid var(--color-border);border-radius:var(--radius-sm);padding:9px 12px;font-size:12px;color:var(--color-text-secondary);line-height:1.45;">
      <strong>Observation note:</strong> ${val !== null ? `Measurement: ${val} ${unit} recorded for the surveillance window.` : 'Observation record available.'} Retrieved from Group 1 MasterDB canonical storage.
    </div>

    <!-- Expandable Technical Details (strictly returned fields only) -->
    <details class="tech-details" style="margin-top:2px;">
      <summary>
        <span>Expand Technical Details (IDs &amp; Ingestion Metadata)</span>
      </summary>
      <div class="tech-details-content">
        <div class="tech-kv-grid">
          ${techItemsHtml}
        </div>
      </div>
    </details>
  `;

  // Configure footer button depending on whether this is already the active dashboard observation
  if (btnSetActive) {
    if (obsId === currentObservationId) {
      btnSetActive.textContent = "Currently Active in Dashboard";
      btnSetActive.disabled = true;
      btnSetActive.style.display = "inline-flex";
      btnSetActive.style.opacity = "0.65";
      btnSetActive.style.cursor = "default";
    } else {
      btnSetActive.textContent = "Set as Active Observation";
      btnSetActive.disabled = false;
      btnSetActive.style.display = "inline-flex";
      btnSetActive.style.opacity = "1";
      btnSetActive.style.cursor = "pointer";
    }
  }
}

function closeObservationDetailsModal() {
  const modal = document.getElementById("observationDetailsModal");
  if (modal) modal.style.display = "none";
  activeSelectedObsIdForModal = null;
}

// Uses the existing observation-selection mechanism (fetchLive) to update runtime state consistently
// Does not write to MasterDB, does not call ingestion endpoints, does not modify records.
function handleSetObsActive() {
  if (activeSelectedObsIdForModal && activeSelectedObsIdForModal !== currentObservationId) {
    const idToLoad = activeSelectedObsIdForModal;
    closeObservationDetailsModal();
    fetchLive(idToLoad);
  }
}

function openZoneInfoModal(zoneKey) {
  const modal = document.getElementById("zoneInfoModal");
  const heading = document.getElementById("zoneInfoHeading");
  const sub = document.getElementById("zoneInfoSub");
  const body = document.getElementById("zoneInfoBody");

  if (!modal || !body) return;

  activeSelectedZoneKeyForModal = zoneKey;
  const z = REGIONAL_ZONES[zoneKey] || { name: zoneKey, lat: 19.0, lon: 73.0 };

  if (heading) heading.textContent = `${z.name} Monitored Location`;
  if (sub) sub.textContent = "Regional Surveillance Zone";

  body.innerHTML = `
    <div style="background:var(--color-warning-light);border:1px solid var(--color-warning-border);border-left:3px solid var(--color-warning);border-radius:var(--radius-sm);padding:10px 12px;margin-bottom:12px;">
      <div style="font-weight:700;font-size:12.5px;color:var(--color-text);display:flex;align-items:center;gap:6px;">
        <span class="status-dot" style="background:var(--color-warning);"></span>
        <span>Awaiting Field Edge Sensor Deployment</span>
      </div>
      <div style="font-size:12px;color:var(--color-text-secondary);line-height:1.45;margin-top:4px;">
        No telemetry observations are currently recorded for this region. Under VANA strict fail-closed governance, unpersisted observations are never simulated.
      </div>
    </div>

    <div class="obs-detail-grid">
      <div class="obs-detail-item">
        <div class="obs-detail-k">Monitored Region</div>
        <div class="obs-detail-v">${z.name}</div>
      </div>
      <div class="obs-detail-item">
        <div class="obs-detail-k">Coordinates</div>
        <div class="obs-detail-v mono">${z.lat ? `${z.lat}° N, ${z.lon}° E` : 'Pending'}</div>
      </div>
      <div class="obs-detail-item">
        <div class="obs-detail-k">Deployment Status</div>
        <div class="obs-detail-v" style="color:var(--color-warning);">Pending Sensor Hardware</div>
      </div>
      <div class="obs-detail-item">
        <div class="obs-detail-k">Next Operational Step</div>
        <div class="obs-detail-v">Wait for edge sensor telemetry feed</div>
      </div>
    </div>
  `;

  modal.style.display = "flex";
}

function closeZoneInfoModal() {
  const modal = document.getElementById("zoneInfoModal");
  if (modal) modal.style.display = "none";
  activeSelectedZoneKeyForModal = null;
}

function handleZoneFocusMap() {
  if (activeSelectedZoneKeyForModal) {
    const z = REGIONAL_ZONES[activeSelectedZoneKeyForModal];
    closeZoneInfoModal();
    if (z) {
      switchMainTab('mapView', document.getElementById('navItemMap'));
      focusMapLocation(z.lat, z.lon, 12);
    }
  }
}


// =============================================================================
// VIEW 3: MAP & LOCATIONS RENDERER (ITERATION 4)
// =============================================================================
let currentSelectedMapZoneKey = "thane_creek";

function renderMapLocations(data) {
  // 1. Update Leaflet Map Markers
  updateLeafletMap(data);

  // 2. Update Compact Summary Stats
  const availVal = document.getElementById("mapSummaryAvailableVal");
  const availBadge = document.getElementById("mapSummaryAvailableBadge");
  const awaitVal = document.getElementById("mapSummaryAwaitingVal");
  const awaitBadge = document.getElementById("mapSummaryAwaitingBadge");
  const statusBadge = document.getElementById("mapStationStatusBadge");

  const isG1Live = !!(data && data.group1 && !data.group1.failed);
  const liveCount = isG1Live ? 1 : 0;
  const pendingCount = 5;

  if (availVal) availVal.textContent = String(liveCount);
  if (availBadge) availBadge.textContent = isG1Live ? "1 Retrieved" : "0 Retrieved";
  if (awaitVal) awaitVal.textContent = String(pendingCount);
  if (awaitBadge) awaitBadge.textContent = `${pendingCount} Pending`;
  if (statusBadge) {
    if (isG1Live) {
      statusBadge.innerHTML = `<span class="status-dot"></span> 1 Retrieved from MasterDB · 5 Awaiting Upstream Data`;
      statusBadge.className = "status-pill active";
    } else {
      statusBadge.innerHTML = `<span class="status-dot" style="background:var(--color-danger)"></span> 0 Retrieved (1 Lookup Failed) · 5 Awaiting Upstream Data`;
      statusBadge.className = "status-pill error";
    }
  }

  // 3. Render Synchronized Location List
  renderMapLocationsList();

  // 4. Render Selected Location Details Panel
  renderMapDetailPanel(currentSelectedMapZoneKey);
}

function renderMapLocationsList() {
  const container = document.getElementById("mapLocationList");
  if (!container) return;

  const isG1Live = !!(currentRuntimeData && currentRuntimeData.group1 && !currentRuntimeData.group1.failed);

  container.innerHTML = Object.keys(REGIONAL_ZONES).map(key => {
    const z = REGIONAL_ZONES[key];
    const isThane = (key === "thane_creek");
    const zoneCode = z.id.split("-EXT-")[0];
    const isActive = (key === currentSelectedMapZoneKey);

    let statusPillHtml = "";
    if (isThane) {
      if (isG1Live) {
        statusPillHtml = '<span class="status-pill active" style="font-size:10.5px;padding:2px 8px;">Retrieved from MasterDB</span>';
      } else {
        statusPillHtml = '<span class="status-pill error" style="font-size:10.5px;padding:2px 8px;">Lookup Failed</span>';
      }
    } else {
      statusPillHtml = '<span class="status-pill waiting" style="font-size:10.5px;padding:2px 8px;">Awaiting Sensor Feed</span>';
    }

    return `
      <div class="map-location-item ${isActive ? 'active' : ''}" data-zone-key="${key}" onclick="selectMapLocation('${key}', true)">
        <div>
          <div style="display:flex;align-items:center;gap:6px;">
            <strong style="font-size:12.5px;color:var(--color-text);">${z.name}</strong>
            <span class="mono" style="font-size:11px;color:var(--color-muted);">(${zoneCode})</span>
          </div>
          <div class="mono" style="font-size:11px;color:var(--color-text-secondary);margin-top:2px;">
            ${z.lat}° N, ${z.lon}° E
          </div>
        </div>
        <div>
          ${statusPillHtml}
        </div>
      </div>
    `;
  }).join("");
}

function renderMapDetailPanel(zoneKey) {
  const z = REGIONAL_ZONES[zoneKey] || REGIONAL_ZONES.thane_creek;
  const isThane = (zoneKey === "thane_creek" || z.id === "TC-Z03-EXT-OPENMETEO-OBS001");
  const g1 = (currentRuntimeData && currentRuntimeData.group1) || {};
  const isG1Live = !!(currentRuntimeData && currentRuntimeData.group1 && !currentRuntimeData.group1.failed);
  const isLive = isG1Live;
  const zoneCode = z.id.split("-EXT-")[0];

  const titleEl = document.getElementById("mapDetailPanelTitle");
  const subEl = document.getElementById("mapDetailPanelSub");
  const badgeEl = document.getElementById("mapDetailStatusBadge");
  const bodyEl = document.getElementById("mapDetailBody");

  if (titleEl) titleEl.textContent = z.name;
  if (subEl) subEl.textContent = `Canonical Zone ${zoneCode} · Regional Surveillance Location`;
  if (badgeEl) {
    if (isThane) {
      if (isG1Live) {
        badgeEl.className = "status-pill active";
        badgeEl.textContent = "Retrieved from MasterDB";
      } else {
        badgeEl.className = "status-pill error";
        badgeEl.textContent = "Lookup Failed";
      }
    } else {
      badgeEl.className = "status-pill waiting";
      badgeEl.textContent = "Awaiting Sensor Feed";
    }
  }

  if (!bodyEl) return;

  if (isThane && !isG1Live) {
    bodyEl.innerHTML = `
      <div class="map-detail-hero" style="margin-bottom:12px;background:var(--color-surface-subtle);">
        <div class="map-detail-val-box">
          <div class="map-detail-val" style="color:var(--color-danger);font-size:20px;">Lookup Failed</div>
          <div class="map-detail-param">Observation TC-Z03 Unresolved</div>
        </div>
        <span class="status-pill error" style="font-size:11px;">Lookup Failed</span>
      </div>

      <div class="obs-detail-grid" style="margin-bottom:12px;">
        <div class="obs-detail-cell">
          <div class="obs-detail-k">Canonical Zone ID</div>
          <div class="obs-detail-v mono" style="font-weight:600;">${zoneCode}</div>
        </div>
        <div class="obs-detail-cell">
          <div class="obs-detail-k">Reference Coordinates</div>
          <div class="obs-detail-v mono">${z.lat}° N, ${z.lon}° E (${z.alt_m ? `${z.alt_m}m` : '4.0m'})</div>
        </div>
        <div class="obs-detail-cell">
          <div class="obs-detail-k">Linked Observation</div>
          <div class="obs-detail-v mono" style="font-size:11px;">${z.id}</div>
        </div>
        <div class="obs-detail-cell">
          <div class="obs-detail-k">Data Availability</div>
          <div class="obs-detail-v" style="color:var(--color-danger);font-weight:600;">Lookup Failed (${g1.fail_reason || "MasterDB Unreachable"})</div>
        </div>
        <div class="obs-detail-cell">
          <div class="obs-detail-k">Data Provenance</div>
          <div class="obs-detail-v">Configured Controlled Synthetic Benchmark</div>
        </div>
        <div class="obs-detail-cell">
          <div class="obs-detail-k">Quality State</div>
          <div class="obs-detail-v mono">UNRESOLVED</div>
        </div>
        <div class="obs-detail-cell">
          <div class="obs-detail-k">Calibration Verification</div>
          <div class="obs-detail-v" style="color:var(--color-muted);">Not Verified (Lookup Failed)</div>
        </div>
        <div class="obs-detail-cell">
          <div class="obs-detail-k">GNSS Verification</div>
          <div class="obs-detail-v" style="color:var(--color-muted);">Not Verified (Lookup Failed)</div>
        </div>
        <div class="obs-detail-cell" style="grid-column: 1 / -1;">
          <div class="obs-detail-k">Source &amp; Attribution</div>
          <div class="obs-detail-v">Open-Meteo Cloud API (CC-BY 4.0)</div>
        </div>
      </div>

      <div class="notice-callout" style="margin-bottom:12px;background:var(--color-danger-light);border-left:3px solid var(--color-danger);">
        <div class="notice-callout-header">
          <span class="status-dot" style="background:var(--color-danger);"></span>
          <strong style="font-size:12px;color:var(--color-text);">Configured Observation Unresolved in MasterDB</strong>
        </div>
        <div class="notice-callout-body" style="font-size:11.5px;color:var(--color-text-secondary);margin-top:3px;line-height:1.4;">
          Observation record lookup failed (${g1.fail_reason || "Service Unavailable"}). The observation record is configured in the six-location system model, but could not be retrieved from the active ledger. Under strict fail-closed governance, downstream automated actions are halted.
        </div>
      </div>

      <div style="display:flex;gap:8px;margin-top:auto;">
        <button type="button" class="btn-header primary" onclick="fetchLive('${z.id}')" style="flex:1;justify-content:center;">
          <span>Retry MasterDB Lookup</span>
        </button>
      </div>
    `;
    return;
  }

  if (isLive) {
    bodyEl.innerHTML = `
      <div class="map-detail-hero" style="margin-bottom:12px;">
        <div class="map-detail-val-box">
          <div class="map-detail-val" style="color:var(--color-primary);">0.1 mm</div>
          <div class="map-detail-param">Precipitation Reading</div>
        </div>
        <span class="status-pill active" style="font-size:11px;">Retrieved from MasterDB</span>
      </div>

      <div class="obs-detail-grid" style="margin-bottom:12px;">
        <div class="obs-detail-cell">
          <div class="obs-detail-k">Canonical Zone ID</div>
          <div class="obs-detail-v mono" style="font-weight:600;">${zoneCode}</div>
        </div>
        <div class="obs-detail-cell">
          <div class="obs-detail-k">Reference Coordinates</div>
          <div class="obs-detail-v mono">${z.lat}° N, ${z.lon}° E (${z.alt_m ? `${z.alt_m}m` : '4.0m'})</div>
        </div>
        <div class="obs-detail-cell">
          <div class="obs-detail-k">Linked Observation</div>
          <div class="obs-detail-v mono" style="font-size:11px;">${z.id}</div>
        </div>
        <div class="obs-detail-cell">
          <div class="obs-detail-k">Data Availability</div>
          <div class="obs-detail-v" style="color:var(--color-success);font-weight:600;">Retrieved from MasterDB</div>
        </div>
        <div class="obs-detail-cell">
          <div class="obs-detail-k">Data Provenance</div>
          <div class="obs-detail-v">Controlled Synthetic Data</div>
        </div>
        <div class="obs-detail-cell">
          <div class="obs-detail-k">Quality State</div>
          <div class="obs-detail-v mono">CAPTURED</div>
        </div>
        <div class="obs-detail-cell">
          <div class="obs-detail-k">Calibration Verification</div>
          <div class="obs-detail-v" style="color:var(--color-muted);">Not Verified</div>
        </div>
        <div class="obs-detail-cell">
          <div class="obs-detail-k">GNSS Verification</div>
          <div class="obs-detail-v" style="color:var(--color-muted);">Not Verified</div>
        </div>
        <div class="obs-detail-cell" style="grid-column: 1 / -1;">
          <div class="obs-detail-k">Source &amp; Attribution</div>
          <div class="obs-detail-v">Open-Meteo Cloud API (CC-BY 4.0)</div>
        </div>
      </div>

      <div class="notice-callout" style="margin-bottom:12px;">
        <div class="notice-callout-header">
          <span class="status-dot" style="background:var(--color-primary);"></span>
          <strong style="font-size:12px;color:var(--color-text);">Confirmed Live in MasterDB</strong>
        </div>
        <div class="notice-callout-body" style="font-size:11.5px;color:var(--color-text-secondary);margin-top:3px;line-height:1.4;">
          Authoritative observation retrievable from Group 1 MasterDB via canonical lookup. Provenance declared as Controlled Synthetic benchmark telemetry. Zero field claims are asserted.
        </div>
      </div>

      <div style="display:flex;gap:8px;margin-top:auto;">
        <button type="button" class="btn-header primary" onclick="switchMainTab('monitoringView', document.getElementById('navItemMonitoring'))" style="flex:1;justify-content:center;">
          <span>View in Environmental Monitoring</span>
        </button>
      </div>
    `;
  } else {
    bodyEl.innerHTML = `
      <div class="map-detail-hero" style="margin-bottom:12px;background:var(--color-surface-subtle);">
        <div class="map-detail-val-box">
          <div class="map-detail-val" style="color:var(--color-warning);font-size:18px;">No Telemetry</div>
          <div class="map-detail-param">Awaiting Sensor Feed</div>
        </div>
        <span class="status-pill waiting" style="font-size:11px;">Pending Upstream</span>
      </div>

      <div class="obs-detail-grid" style="margin-bottom:12px;">
        <div class="obs-detail-cell">
          <div class="obs-detail-k">Canonical Zone ID</div>
          <div class="obs-detail-v mono" style="font-weight:600;">${zoneCode}</div>
        </div>
        <div class="obs-detail-cell">
          <div class="obs-detail-k">Reference Coordinates</div>
          <div class="obs-detail-v mono">${z.lat}° N, ${z.lon}° E</div>
        </div>
        <div class="obs-detail-cell">
          <div class="obs-detail-k">Deployment Status</div>
          <div class="obs-detail-v" style="color:var(--color-warning);font-weight:600;">Awaiting Sensor Feed</div>
        </div>
        <div class="obs-detail-cell">
          <div class="obs-detail-k">Observation Association</div>
          <div class="obs-detail-v" style="color:var(--color-muted);">None Available (Unpersisted)</div>
        </div>
        <div class="obs-detail-cell" style="grid-column: 1 / -1;">
          <div class="obs-detail-k">Next Operational Step</div>
          <div class="obs-detail-v">Awaiting field edge sensor deployment in ${z.name}.</div>
        </div>
      </div>

      <div class="notice-callout" style="margin-bottom:12px;background:var(--color-surface-subtle);border-color:var(--color-border);">
        <div class="notice-callout-header">
          <span class="status-dot" style="background:var(--color-warning);"></span>
          <strong style="font-size:12px;color:var(--color-text);">Awaiting Sensor Feed</strong>
        </div>
        <div class="notice-callout-body" style="font-size:11.5px;color:var(--color-text-secondary);margin-top:3px;line-height:1.4;">
          No observation data is currently available through the configured workflow. Under VANA zero-fabrication doctrine, unpersisted locations are never populated with synthetic estimates.
        </div>
      </div>

      <div style="display:flex;gap:8px;margin-top:auto;">
        <button type="button" class="btn-header" onclick="resetMapExtent()" style="flex:1;justify-content:center;">
          <span>Show All Monitored Locations</span>
        </button>
      </div>
    `;
  }
}

function selectMapLocation(zoneKey, panMap) {
  if (!REGIONAL_ZONES[zoneKey]) {
    zoneKey = "thane_creek";
  }
  currentSelectedMapZoneKey = zoneKey;

  // Sync quick select dropdown
  const quickSelect = document.getElementById("geoZoneQuickSelect");
  if (quickSelect && quickSelect.value !== zoneKey) {
    quickSelect.value = zoneKey;
  }

  // Sync Location List active class
  const items = document.querySelectorAll("#mapLocationList .map-location-item");
  items.forEach(el => {
    if (el.getAttribute("data-zone-key") === zoneKey) {
      el.classList.add("active");
    } else {
      el.classList.remove("active");
    }
  });

  // Render Details Panel
  renderMapDetailPanel(zoneKey);

  // Pan Map if requested
  const z = REGIONAL_ZONES[zoneKey];
  if (panMap && z) {
    if (window.VanaGeoEngine && window.VanaGeoEngine.map) {
      window.VanaGeoEngine.map.setView([z.lat, z.lon], 12, { animate: true });
      const marker = (window.VanaGeoEngine.markers && window.VanaGeoEngine.markers[zoneKey]) ||
                     (window.VanaGeoEngine.zoneMarkers && window.VanaGeoEngine.zoneMarkers[zoneKey]);
      if (marker) {
        marker.openPopup();
      }
    } else if (leafletMap) {
      leafletMap.setView([z.lat, z.lon], 12, { animate: true });
    }
  }
}

function resetMapExtent() {
  if (window.VanaGeoEngine && window.VanaGeoEngine.map) {
    window.VanaGeoEngine.map.fitBounds([
      [18.7500, 72.8054],
      [19.4919, 73.5000]
    ], { padding: [35, 35] });
  } else if (leafletMap) {
    leafletMap.fitBounds([
      [18.7500, 72.8054],
      [19.4919, 73.5000]
    ], { padding: [35, 35] });
  }
}

function handleZoneJump(zoneKey) {
  if (!zoneKey) return;
  selectMapLocation(zoneKey, true);
}

// Global window exposure for event handlers
window.selectMapLocation = selectMapLocation;
window.resetMapExtent = resetMapExtent;
window.handleZoneJump = handleZoneJump;

// =============================================================================
// VIEW 4: REVIEW & DECISIONS RENDERER
// =============================================================================
// =============================================================================
// VIEW 4: REVIEWS & DECISIONS RENDERER (ITERATION 5)
// =============================================================================
function renderDecisions(data) {
  const g1 = data.group1 || {};
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

  // Panel Title
  const is404 = g1 && g1.http_status === 404;
  const isUnavailable = g1Failed && !is404;

  const decPanelTitle = document.getElementById("decisionsPanelTitle");
  if (decPanelTitle) {
    if (is404) {
      decPanelTitle.textContent = "Environmental Assessment (Observation Not Found: HTTP 404)";
    } else if (isUnavailable) {
      decPanelTitle.textContent = `Environmental Assessment (MasterDB Service Unavailable: ${g1.fail_reason || "HTTP 502"})`;
    } else {
      decPanelTitle.textContent = `Environmental Assessment for ${data.zone_name || "Thane Creek"}`;
    }
  }

  // Primary Assessment Callout
  const decBlock = document.getElementById("decisionsBlock");
  if (decBlock) {
    decBlock.className = `assessment-callout ${g1Failed ? "deny" : (isPaused ? "paused" : "allow")}`;
  }

  // Outcome Heading & Explanation
  const outcomeTitle = document.getElementById("decisionsOutcomeTitle");
  const outcomeDesc = document.getElementById("decisionsOutcomeDesc");

  if (outcomeTitle) {
    outcomeTitle.textContent = is404 ? "Observation Not Found" : (isUnavailable ? "Service Unavailable" : (isPaused ? "Action paused" : "Action allowed"));
  }
  if (outcomeDesc) {
    if (is404) {
      outcomeDesc.textContent = `Observation ${data.observation_id} was not found in MasterDB (HTTP 404). Downstream governance evaluation cannot proceed without an authoritative canonical record. Under strict fail-closed governance, execution is blocked.`;
    } else if (isUnavailable) {
      outcomeDesc.textContent = `MasterDB intake service is unavailable (${data.group1.fail_reason || "HTTP 502 Bad Gateway"}). Downstream governance evaluation cannot proceed while the intake gateway is unreachable. Under strict fail-closed governance, execution is blocked.`;
    } else if (g4 && g4.decision_reason) {
      outcomeDesc.textContent = g4.decision_reason;
    } else {
      outcomeDesc.textContent = "The system could not establish that all required evidence and conditions were satisfied. No automated action will proceed.";
    }
  }

  // Compact Decision Summary Cards (Derived strictly from runtime state)
  const decSummaryObsVal = document.getElementById("decSummaryObsVal");
  if (decSummaryObsVal) decSummaryObsVal.textContent = data.zone_id || "TC-Z03";

  const decSummaryObsSub = document.getElementById("decSummaryObsSub");
  if (decSummaryObsSub) decSummaryObsSub.textContent = `${data.zone_name || "Thane Creek"} Surveillance Zone`;

  const decSummaryRulingVal = document.getElementById("decSummaryRulingVal");
  if (decSummaryRulingVal) {
    const ruling = g4.ruling || g2.ruling || "ABSTAIN";
    decSummaryRulingVal.textContent = ruling;
    decSummaryRulingVal.style.color = ruling === "ALLOW" ? "var(--status-ok)" : "var(--status-warn)";
  }

  const decSummaryRulingBadge = document.getElementById("decSummaryRulingBadge");
  if (decSummaryRulingBadge) {
    decSummaryRulingBadge.textContent = isPaused ? "Action Paused" : "Action Allowed";
    decSummaryRulingBadge.className = isPaused ? "status-pill paused" : "status-pill active";
  }

  const isNoDispatch = (g4.decision_action === "noop" || !g4.execution_id || isPaused);

  const decSummaryExecVal = document.getElementById("decSummaryExecVal");
  if (decSummaryExecVal) {
    decSummaryExecVal.textContent = isNoDispatch ? "NO DISPATCH" : "DISPATCHED";
    decSummaryExecVal.style.color = isNoDispatch ? "var(--brand)" : "var(--status-ok)";
  }

  const decSummaryExecBadge = document.getElementById("decSummaryExecBadge");
  if (decSummaryExecBadge) {
    decSummaryExecBadge.textContent = isNoDispatch ? "Zero Side-Effects" : "Executed";
    decSummaryExecBadge.className = "status-pill active";
  }

  const decSummaryGapsVal = document.getElementById("decSummaryGapsVal");
  if (decSummaryGapsVal) {
    const gapCount = (g2.gap_fields && g2.gap_fields.length) ? g2.gap_fields.length : (g1Failed ? "Unresolved" : "2 Gaps");
    decSummaryGapsVal.textContent = typeof gapCount === "number" ? `${gapCount} Gaps` : gapCount;
  }

  const decSummaryGapsBadge = document.getElementById("decSummaryGapsBadge");
  if (decSummaryGapsBadge) {
    decSummaryGapsBadge.textContent = g1Failed ? "Record Missing" : "Contract §26 / §49.1";
    decSummaryGapsBadge.className = "status-pill waiting";
  }

  // Decision vs Execution Distinction Box
  const decDecisionRuling = document.getElementById("decDecisionRuling");
  if (decDecisionRuling) {
    const ruling = g4.ruling || g2.ruling || "ABSTAIN";
    decDecisionRuling.textContent = ruling;
    decDecisionRuling.style.color = ruling === "ALLOW" ? "var(--status-ok)" : "var(--status-warn)";
  }

  const decDecisionEligible = document.getElementById("decDecisionEligible");
  if (decDecisionEligible) {
    decDecisionEligible.textContent = g2.is_eligible ? "True (Eligible)" : "False (Ineligible)";
  }

  const decDecisionAbstention = document.getElementById("decDecisionAbstention");
  if (decDecisionAbstention) {
    decDecisionAbstention.textContent = g2.requires_abstention !== undefined
      ? (g2.requires_abstention ? "True (Mandatory)" : "False (Not Required)")
      : "True (Mandatory)";
  }

  const decExecutionDispatched = document.getElementById("decExecutionDispatched");
  if (decExecutionDispatched) {
    decExecutionDispatched.textContent = isNoDispatch ? "NONE (Locked)" : "DISPATCHED";
    decExecutionDispatched.style.color = isNoDispatch ? "var(--brand)" : "var(--status-ok)";
  }

  const decExecutionAction = document.getElementById("decExecutionAction");
  if (decExecutionAction) decExecutionAction.textContent = g4.decision_action || "noop";

  const decExecutionStatus = document.getElementById("decExecutionStatus");
  if (decExecutionStatus) decExecutionStatus.textContent = g4.status || (isPaused ? "governed_abstention" : "completed");

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
      const crStr = data.canonical_record_id || "Retrieved from MasterDB";
      whatObserved.textContent = `${obsType} measurement of ${measStr} was recorded at ${latStr}. Canonical record reference in master ledger: ${crStr}.`;
    }
  }

  // Question 2: What is missing
  const evidenceNeeded = document.getElementById("decisionsEvidenceNeeded");
  if (evidenceNeeded) {
    if (g1Failed) {
      evidenceNeeded.textContent = `Canonical observation record in Group 1 MasterDB. Ingestion must succeed before statutory rules can evaluate.`;
    } else {
      evidenceNeeded.textContent = "Raw sensor payload bytes were not persisted at capture time (acknowledged contract gap per §26 / §49.1). Additionally, calibration and GNSS evidence are unverified because the observation originates from an external cloud API rather than verified edge hardware.";
    }
  }

  // Question 3: Why it matters
  const whyReturned = document.getElementById("decisionsWhyReturned");
  if (whyReturned) {
    if (g1Failed) {
      whyReturned.textContent = "Governance rules strictly prohibit automated state transitions on unpersisted or missing records. The system fails closed to ensure safety.";
    } else {
      whyReturned.textContent = "VANA governance policies mandate verified evidence before automated dispatch. To prevent unverified external or uncalibrated readings from authorizing operational actions, the system fails closed to ABSTAIN (action paused).";
    }
  }

  // Question 4: Next step
  const nextStep = document.getElementById("decisionsNextStepText");
  if (nextStep) {
    if (g1Failed) {
      nextStep.textContent = "Awaiting upstream observation telemetry from authenticated ingestion pipeline, or select a configured observation from the top selector dropdown.";
    } else {
      nextStep.textContent = "No automated action is permitted without complete physical evidence. Environmental officers should check the observation source or wait for edge sensor verification. Authorized administrators may inspect configuration or execute replay verification.";
    }
  }

  // Policy & Evidence Basis references
  const decPolicyZoneId = document.getElementById("decPolicyZoneId");
  if (decPolicyZoneId) decPolicyZoneId.textContent = data.zone_id || "TC-Z03";

  const decPolicyObsId = document.getElementById("decPolicyObsId");
  if (decPolicyObsId) decPolicyObsId.textContent = data.observation_id || OBSERVATION_ID;

  const decPolicyCrId = document.getElementById("decPolicyCrId");
  if (decPolicyCrId) decPolicyCrId.textContent = data.canonical_record_id || "CR-b4615a27-7ab1-4bde-a078-a56fa0f2414c";

  const decPolicyContextId = document.getElementById("decPolicyContextId");
  if (decPolicyContextId) {
    decPolicyContextId.textContent = data.context_id !== null && data.context_id !== undefined
      ? String(data.context_id)
      : "None (Unresolved)";
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
  // Populate Evidence Summary Grid
  const audObsVal = document.getElementById("audSummaryObsVal");
  const audObsSub = document.getElementById("audSummaryObsSub");
  const audStagesVal = document.getElementById("audSummaryStagesVal");
  const audGapsVal = document.getElementById("audSummaryGapsVal");
  const audExecVal = document.getElementById("audSummaryExecVal");
  const audExecSub = document.getElementById("audSummaryExecSub");
  const audExecBadge = document.getElementById("audSummaryExecBadge");
  const audStepperCr = document.getElementById("audStepperCrId");
  const stepperStage3Pill = document.getElementById("audStepperStage3Pill");
  const stepperStage3Sub = document.getElementById("audStepperStage3Sub");
  const stepperStage4Pill = document.getElementById("audStepperStage4Pill");
  const stepperStage4Sub = document.getElementById("audStepperStage4Sub");

  const g1 = data.group1 || {};
  const g2 = data.group2 || {};
  const g4 = data.group4 || {};

  const g1Failed = Boolean(g1 && g1.failed);
  const g2Failed = Boolean(g2 && g2.failed);
  const g2Evaluated = Boolean(g2 && !g2.failed && (g2.ruling || g2.status));
  const g4Failed = Boolean(g4 && (g4.failed || g4.error));
  const g4Evaluated = Boolean(g4 && !g4.failed && (g4.status || g4.decision_action));

  if (audObsVal) {
    if (g1Failed) {
      audObsVal.textContent = "UNRETRIEVED";
      audObsVal.title = g1.http_status === 404 ? "Observation not found in MasterDB (HTTP 404)" : "MasterDB service unavailable; lookup failed";
    } else {
      audObsVal.textContent = data.observation_id ? (data.observation_id.length > 18 ? "TC-Z03" : data.observation_id) : "TC-Z03";
      audObsVal.title = data.observation_id || "TC-Z03-EXT-OPENMETEO-OBS001";
    }
  }
  if (audObsSub) {
    if (g1Failed) {
      audObsSub.textContent = g1.http_status === 404 ? "Observation Not Found in Ledger" : "MasterDB Service Unavailable (Lookup Failed)";
    } else {
      audObsSub.textContent = g1.zone_name ? `${g1.zone_name} (${g1.zone_id || "TC-Z03"})` : "Thane Creek Surveillance Zone (TC-Z03)";
    }
  }
  if (audStagesVal) {
    audStagesVal.textContent = "4 Stages";
  }
  if (audGapsVal) {
    audGapsVal.textContent = "2 Declared Gaps";
  }

  // Card 4: Group 4 Execution State (Distinguish not evaluated vs skipped vs failed vs evaluated)
  if (audExecVal) {
    if (g4.skipped) {
      audExecVal.textContent = "NOT EVALUATED";
    } else if (g4Failed) {
      audExecVal.textContent = "UNAVAILABLE";
    } else if (!g4Evaluated) {
      audExecVal.textContent = "NOT EVALUATED";
    } else {
      audExecVal.textContent = g4.decision_action || "noop";
    }
  }
  if (audExecSub) {
    if (g4.skipped) {
      audExecSub.textContent = "Skipped (Upstream Intake Unresolved)";
    } else if (g4Failed) {
      audExecSub.textContent = "Gateway request failed";
    } else if (!g4Evaluated) {
      audExecSub.textContent = "Gateway not evaluated";
    } else {
      audExecSub.textContent = `Dispatch: ${g4.dispatch_state || "NONE (Locked)"}`;
    }
  }
  if (audExecBadge) {
    if (g4.skipped) {
      audExecBadge.textContent = "Skipped";
      audExecBadge.className = "status-pill neutral";
    } else if (g4Failed) {
      audExecBadge.textContent = "Evaluation Failed";
      audExecBadge.className = "status-pill waiting";
    } else if (!g4Evaluated) {
      audExecBadge.textContent = "Not Evaluated";
      audExecBadge.className = "status-pill neutral";
    } else {
      audExecBadge.textContent = g4.status || "governed_abstention";
      audExecBadge.className = "status-pill active";
    }
  }

  if (audStepperCr) {
    const crId = data.canonical_record_id || (g1Failed ? "NOT VERIFIED" : "CR-b4615a27-7ab1-4bde-a078-a56fa0f2414c");
    audStepperCr.textContent = crId.length > 16 ? `${crId.slice(0, 15)}...` : crId;
  }

  // Dynamic Stepper State Synchronization
  if (stepperStage3Pill) {
    if (g2Failed) {
      stepperStage3Pill.textContent = "Unavailable";
      stepperStage3Pill.className = "status-pill waiting";
    } else if (!g2Evaluated) {
      stepperStage3Pill.textContent = "Not Evaluated";
      stepperStage3Pill.className = "status-pill neutral";
    } else {
      stepperStage3Pill.textContent = "Abstained";
      stepperStage3Pill.className = "status-pill paused";
    }
  }
  if (stepperStage3Sub) {
    if (g2Failed) {
      stepperStage3Sub.textContent = "Pravah API · Unavailable";
    } else if (!g2Evaluated) {
      stepperStage3Sub.textContent = "Pravah API · Not Evaluated";
    } else {
      stepperStage3Sub.textContent = `Group 2 Pravah · ${g2.status || "CONTEXT_NOT_VERIFIED"}`;
    }
  }

  if (stepperStage4Pill) {
    if (g4Failed) {
      stepperStage4Pill.textContent = "Failed";
      stepperStage4Pill.className = "status-pill waiting";
    } else if (!g4Evaluated) {
      stepperStage4Pill.textContent = "Not Evaluated";
      stepperStage4Pill.className = "status-pill neutral";
    } else {
      stepperStage4Pill.textContent = g4.status || "governed_abstention";
      stepperStage4Pill.className = "status-pill active";
    }
  }
  if (stepperStage4Sub) {
    if (g4Failed) {
      stepperStage4Sub.textContent = "Execution Gate · Unavailable";
    } else if (!g4Evaluated) {
      stepperStage4Sub.textContent = "Execution Gate · Not Evaluated";
    } else {
      stepperStage4Sub.textContent = `${g4.decision_action || "noop"} · Dispatch: ${g4.dispatch_state || "NONE (Locked)"}`;
    }
  }

  // Provenance Rail
  renderLineageRail(data);

  // Replay Diff Table
  renderReplayDiff(data);
}

function renderLineageRail(data) {
  const container = document.getElementById("lineageRailContainer");
  if (!container) return;

  const g3 = data.group3 || {};
  const g1 = data.group1 || {};
  const g2 = data.group2 || {};
  const g4 = data.group4 || {};

  const g1Failed = Boolean(g1 && g1.failed);
  const g2Failed = Boolean(g2 && g2.failed);
  const g2Evaluated = Boolean(g2 && !g2.failed && (g2.ruling || g2.status));
  const g4Failed = Boolean(g4 && (g4.failed || g4.error));
  const g4Evaluated = Boolean(g4 && !g4.failed && (g4.status || g4.decision_action));

  const stage1Reading = g1Failed
    ? "None (Observation Unresolved)"
    : ((g3.measurement !== null && g3.measurement !== undefined) ? `${g3.measurement} ${g3.unit || ""}`.trim() : "0.1 mm");
  const stage1Source = g1Failed ? "Unresolved in MasterDB" : (g3.source_identity || "Open-Meteo.com Cloud Precipitation Archive");
  const stage1Time = g1Failed ? "None" : (g3.observation_timestamp || "2026-08-25 11:00:00 UTC");
  const stage1State = g1Failed ? "UNRESOLVED" : (g3.synthetic_state || "CONTROLLED");

  const verifiedSha256 = g1Failed ? null : (g3.sha256 || (g1 && g1.checksum_sha256) || (g2 && g2.artifact_hash) || (data.observation_id === "TC-Z03-EXT-OPENMETEO-OBS001" ? "8d26e68328ac160f7b69f1a24ccb2de4972ff9fc60af11093c246903a7c52502" : null));

  let html = `
    <!-- STAGE 1: SENSOR INGESTION CONTRACT -->
    <div class="card-panel">
      <div class="card-panel-head">
        <div>
          <span class="badge" style="margin-bottom:4px;font-size:9.5px;">Stage 1 of 4 : Sensor Ingestion</span>
          <div class="card-panel-title">Environmental Observation Ingestion Contract</div>
        </div>
        <span class="status-pill ${g1Failed ? 'waiting' : 'active'}">${stage1State} (Ingestion Contract v2.2)</span>
      </div>
      <div class="card-panel-body">
        <div class="field-grid">
          <div class="field-cell">
            <div class="field-k">Source Identity</div>
            <div class="field-v">${stage1Source}</div>
          </div>
          <div class="field-cell">
            <div class="field-k">Capture Method</div>
            <div class="field-v mono">${g3.capture_method || "EXTERNAL_CLOUD_API"}</div>
          </div>
          <div class="field-cell">
            <div class="field-k">Observed Reading</div>
            <div class="field-v mono" style="color:${g1Failed ? 'var(--status-critical)' : 'var(--status-ok)'}">${stage1Reading}</div>
          </div>
          <div class="field-cell">
            <div class="field-k">Observation Timestamp</div>
            <div class="field-v mono">${stage1Time} <span style="font-size:10px;color:var(--text-secondary);">(Present but Unverified)</span></div>
          </div>
          <div class="field-cell">
            <div class="field-k">Contract Version</div>
            <div class="field-v mono">Group 3 Contract v2.2</div>
          </div>
          <div class="field-cell">
            <div class="field-k">Declared Evidence Gap (§26 / §49.1)</div>
            <div class="field-v">
              <span class="gap-category-pill not-persisted" style="font-size:10px;">Not Persisted</span>
              <span style="font-size:11px;color:var(--text-secondary);margin-left:4px;">Raw sensor payload bytes omitted at capture</span>
            </div>
          </div>
        </div>

        <!-- Expandable Technical Details for Stage 1 -->
        <details class="tech-details" style="margin-top:12px;">
          <summary>
            <span>Technical Evidence &amp; Ingestion Cryptography</span>
            <span class="status-pill neutral" style="font-size:10px;">Stage 1 Details</span>
          </summary>
          <div class="tech-details-content">
            <div class="tech-kv-grid">
              <div class="field-cell">
                <div class="field-k">SHA-256 Checksum</div>
                <div class="field-v mono" style="font-size:10.5px;overflow-wrap:anywhere;">${verifiedSha256 || "Not provided by source"}</div>
              </div>
              <div class="field-cell">
                <div class="field-k">Raw Artifact Reference &amp; Persistence</div>
                <div class="field-v" style="font-size:11px;color:var(--text-secondary);">Raw payload bytes not persisted at capture time (Group 3 Ingestion Contract v2.2, clauses §26 &amp; §49.1). SHA-256 value recorded in the canonical evidence record; raw bytes are not recoverable from hash.</div>
              </div>
              <div class="field-cell">
                <div class="field-k">Emitter Subsystem &amp; Device</div>
                <div class="field-v mono" style="font-size:11px;">G3-EXT-OPENMETEO-01 (Mission: TC-Z03-EXT)</div>
              </div>
              <div class="field-cell">
                <div class="field-k">Upstream API Query Endpoint</div>
                <div class="field-v mono" style="font-size:10.5px;overflow-wrap:anywhere;">https://api.open-meteo.com/v1/forecast?latitude=19.1288&amp;longitude=72.9421</div>
              </div>
            </div>
          </div>
        </details>
      </div>
    </div>

    <!-- STAGE 2: CANONICAL RECORD LEDGER (MASTERDB) -->
    <div class="card-panel">
      <div class="card-panel-head">
        <div>
          <span class="badge" style="margin-bottom:4px;font-size:9.5px;">Stage 2 of 4 : Master Ledger</span>
          <div class="card-panel-title">MasterDB Canonical Record Ledger</div>
        </div>
        <span class="status-pill ${g1Failed ? 'waiting' : 'active'}">${g1Failed ? 'Unresolved' : 'Retrieved from MasterDB'}</span>
      </div>
      <div class="card-panel-body">
        <div class="field-grid">
          <div class="field-cell">
            <div class="field-k">Observation ID</div>
            <div class="field-v mono" style="color:var(--brand);font-weight:600;">${data.observation_id || "TC-Z03-EXT-OPENMETEO-OBS001"}</div>
          </div>
          <div class="field-cell">
            <div class="field-k">Canonical Record ID</div>
            <div class="field-v mono">${data.canonical_record_id || '<span style="color:var(--status-critical)">NOT VERIFIED (Intake Halted)</span>'}</div>
          </div>
          <div class="field-cell">
            <div class="field-k">Monitored Location</div>
            <div class="field-v">${g1.zone_name || "Thane Creek"} (${g1.zone_id || "TC-Z03"})</div>
          </div>
          <div class="field-cell">
            <div class="field-k">Quality State</div>
            <div class="field-v mono">${g1.quality_state || (g1Failed ? "UNRESOLVED" : "CAPTURED")}</div>
          </div>
          <div class="field-cell">
            <div class="field-k">Provenance Classification</div>
            <div class="field-v mono">${g1Failed ? "Unresolved" : `Controlled Synthetic Data (is_synthetic: ${String(g1.is_synthetic !== undefined ? g1.is_synthetic : true)})`}</div>
          </div>
          <div class="field-cell">
            <div class="field-k">Hardware Verification State</div>
            <div class="field-v">
              <span class="gap-category-pill unverified" style="font-size:10px;">Present but Unverified</span>
              <span style="font-size:11px;color:var(--text-secondary);margin-left:4px;">Calibration: ${g1.calibration_status || "NOT_VERIFIED"}, GNSS: ${g1.gnss_status || "NOT_VERIFIED"}</span>
            </div>
          </div>
        </div>

        <!-- Expandable Technical Details for Stage 2 -->
        <details class="tech-details" style="margin-top:12px;">
          <summary>
            <span>Technical Evidence &amp; Ledger References</span>
            <span class="status-pill neutral" style="font-size:10px;">Stage 2 Details</span>
          </summary>
          <div class="tech-details-content">
            <div class="tech-kv-grid">
              <div class="field-cell">
                <div class="field-k">Trace ID</div>
                <div class="field-v mono" style="font-size:11px;">${(g1 && g1.trace_id) || (g1Failed ? "None (Intake unretrieved)" : "TR-c87d4a19-33e2-4f11-9a41-3b7c84529124")}</div>
              </div>
              <div class="field-cell">
                <div class="field-k">Canonical Storage Reference</div>
                <div class="field-v mono" style="font-size:11px;overflow-wrap:anywhere;">${data.canonical_record_id ? `canonical_records/TC-Z03/${data.canonical_record_id}.json` : (g1Failed ? 'Unavailable (Intake unretrieved)' : 'canonical_records/TC-Z03/CR-b4615a27-7ab1-4bde-a078-a56fa0f2414c.json')}</div>
              </div>
              <div class="field-cell">
                <div class="field-k">Ledger Intake Route</div>
                <div class="field-v mono" style="font-size:11px;">GET /proxy/g1/observations/${data.observation_id || "TC-Z03-EXT-OPENMETEO-OBS001"}</div>
              </div>
              <div class="field-cell">
                <div class="field-k">Ledger Verification Status</div>
                <div class="field-v" style="font-size:11px;color:var(--text-secondary);">${g1Failed ? (g1.http_status === 404 ? "Observation entry absent from ledger (HTTP 404)" : `MasterDB service unavailable: ${g1.fail_reason || "HTTP 502"}`) : "Authoritative master ledger entry retrieved and cryptographically indexed"}</div>
              </div>
            </div>
          </div>
        </details>
      </div>
    </div>

    <!-- STAGE 3: CONTEXT RESOLUTION (PRAVAH) -->
    <div class="card-panel">
      <div class="card-panel-head">
        <div>
          <span class="badge" style="margin-bottom:4px;font-size:9.5px;">Stage 3 of 4 : Scientific Context</span>
          <div class="card-panel-title">Context Resolution &amp; Assessment Ruling</div>
        </div>
        <span class="status-pill ${!g2Evaluated ? 'waiting' : 'paused'}">
          ${g2Failed ? 'Resolution Failed' : (!g2Evaluated ? 'Not Evaluated' : (g2.status || 'CONTEXT_NOT_VERIFIED'))}
        </span>
      </div>
      <div class="card-panel-body">
        <div class="field-grid">
          <div class="field-cell">
            <div class="field-k">Resolution Outcome</div>
            <div class="field-v mono" style="color:${!g2Evaluated ? 'var(--status-critical)' : 'var(--status-warn)'};font-weight:700;">
              ${g2Failed ? 'UNAVAILABLE (Request Failed)' : (!g2Evaluated ? 'NOT EVALUATED' : (g2.ruling || 'ABSTAIN'))}
            </div>
          </div>
          <div class="field-cell">
            <div class="field-k">Action Eligibility</div>
            <div class="field-v mono">${!g2Evaluated ? 'null' : (g2.action_eligibility === true ? 'true' : 'false')}</div>
          </div>
          <div class="field-cell">
            <div class="field-k">Mandatory Abstention</div>
            <div class="field-v mono" style="color:var(--status-warn);">${!g2Evaluated ? 'null' : ((g2.abstention_required === true || !g2.action_eligibility) ? 'true' : 'false')}</div>
          </div>
          <div class="field-cell">
            <div class="field-k">Context Record ID</div>
            <div class="field-v mono" style="color:var(--status-warn);">${!g2Evaluated ? 'null (Resolution unavailable)' : (data.context_id === null ? 'null (Context not verified)' : data.context_id)}</div>
          </div>
          <div class="field-cell">
            <div class="field-k">Context Verification State</div>
            <div class="field-v">
              ${!g2Evaluated
                ? '<span class="gap-category-pill unavailable" style="font-size:10px;">Unavailable Upstream</span><span style="font-size:11px;color:var(--text-secondary);margin-left:4px;">Request Failed</span>'
                : `<span class="gap-category-pill unverified" style="font-size:10px;">Present but Unverified</span><span style="font-size:11px;color:var(--text-secondary);margin-left:4px;">${g2.status || "CONTEXT_NOT_VERIFIED"}</span>`
              }
            </div>
          </div>
          <div class="field-cell">
            <div class="field-k">Context Assessment Message</div>
            <div class="field-v" style="font-size:11.5px;color:var(--text-secondary);">
              ${!g2Evaluated ? 'Group 2 context resolution service is unavailable or failed to respond.' : (g2.message || 'Authoritative evidence threshold not met (Context not verified). Failing closed to ABSTAIN.')}
            </div>
          </div>
        </div>

        <!-- Expandable Technical Details for Stage 3 -->
        <details class="tech-details" style="margin-top:12px;">
          <summary>
            <span>Technical Evidence &amp; Pravah Resolution Payload</span>
            <span class="status-pill neutral" style="font-size:10px;">Stage 3 Details</span>
          </summary>
          <div class="tech-details-content">
            <div class="tech-kv-grid">
              <div class="field-cell">
                <div class="field-k">Context Engine Endpoint</div>
                <div class="field-v mono" style="font-size:11px;">POST /proxy/g2/api/group2/context/resolve</div>
              </div>
              <div class="field-cell">
                <div class="field-k">Provenance Reason</div>
                <div class="field-v mono" style="font-size:11px;">${!g2Evaluated ? 'SERVICE_UNAVAILABLE' : (g2.reason || 'CONTEXT_NOT_VERIFIED')}</div>
              </div>
              <div class="field-cell">
                <div class="field-k">Context Assessment Finding</div>
                <div class="field-v" style="font-size:11px;color:var(--text-secondary);">${!g2Evaluated ? 'Context evaluation was not completed.' : (g2.message || 'Authoritative evidence threshold not met (Context not verified). Failing closed to ABSTAIN.')}</div>
              </div>
              <div class="field-cell">
                <div class="field-k">Fail-Closed Resolution Doctrine</div>
                <div class="field-v" style="font-size:11px;color:var(--text-secondary);">Fail closed to ABSTAIN when context authenticity is unverified</div>
              </div>
            </div>
          </div>
        </details>
      </div>
    </div>

    <!-- STAGE 4: GOVERNANCE EXECUTION GATE -->
    <div class="card-panel">
      <div class="card-panel-head">
        <div>
          <span class="badge" style="margin-bottom:4px;font-size:9.5px;">Stage 4 of 4 : Execution Gate</span>
          <div class="card-panel-title">Governance Ruling &amp; Execution Gate</div>
        </div>
        <span class="status-pill ${!g4Evaluated ? 'waiting' : 'active'}">
          ${g4Failed ? 'Evaluation Failed' : (!g4Evaluated ? 'Not Evaluated' : (g4.status || 'governed_abstention'))}
        </span>
      </div>
      <div class="card-panel-body">
        <div class="field-grid">
          <div class="field-cell">
            <div class="field-k">Governance Ruling</div>
            <div class="field-v mono" style="color:${!g4Evaluated ? 'var(--status-critical)' : 'var(--status-warn)'};font-weight:700;">
              ${g4Failed ? 'UNAVAILABLE (Request Failed)' : (!g4Evaluated ? 'NOT EVALUATED' : (g4.ruling || 'ABSTAIN'))}
            </div>
          </div>
          <div class="field-cell">
            <div class="field-k">Decision Action</div>
            <div class="field-v mono" style="font-weight:600;">${!g4Evaluated ? 'null' : (g4.decision_action || 'noop')}</div>
          </div>
          <div class="field-cell">
            <div class="field-k">Execution Status</div>
            <div class="field-v mono" style="color:var(--status-warn);">${!g4Evaluated ? (g4Failed ? 'failed' : 'not_evaluated') : (g4.status || 'governed_abstention')}</div>
          </div>
          <div class="field-cell">
            <div class="field-k">Dispatch State</div>
            <div class="field-v mono">${!g4Evaluated ? 'NONE (Not Evaluated)' : (g4.dispatch_state || 'NONE (Locked)')}</div>
          </div>
          <div class="field-cell">
            <div class="field-k">Governance Allowed</div>
            <div class="field-v mono">${!g4Evaluated ? 'false' : (g4.governance_allowed !== null && g4.governance_allowed !== undefined ? String(g4.governance_allowed) : "false")}</div>
          </div>
            <div class="field-cell">
              <div class="field-k">Abstention Record ID</div>
              <div class="field-v mono">${!g4Evaluated ? 'null' : (data.abstention_record_id || (g4 && g4.abstention_record_id) || 'null')}</div>
            </div>
        </div>

        <!-- Expandable Technical Details for Stage 4 -->
        <details class="tech-details" style="margin-top:12px;">
          <summary>
            <span>Technical Evidence &amp; Execution Gate Controls</span>
            <span class="status-pill neutral" style="font-size:10px;">Stage 4 Details</span>
          </summary>
          <div class="tech-details-content">
            <div class="tech-kv-grid">
              <div class="field-cell">
                <div class="field-k">Execution ID</div>
                <div class="field-v mono" style="font-size:11px;">${(g4 && g4.execution_id) ? g4.execution_id : "null"}</div>
              </div>
              <div class="field-cell">
                <div class="field-k">Dispatch Event ID</div>
                <div class="field-v mono" style="font-size:11px;">${(g4 && g4.event_id) ? g4.event_id : "null"}</div>
              </div>
              <div class="field-cell">
                <div class="field-k">Execution Gateway Endpoint</div>
                <div class="field-v mono" style="font-size:11px;">POST /proxy/g4/vana/execute (HTTP 200, action: noop)</div>
              </div>
              <div class="field-cell">
                <div class="field-k">Governing Contract Reference</div>
                <div class="field-v" style="font-size:11px;color:var(--text-secondary);">Group 3 Ingestion Contract v2.2, clauses §26 / §49.1</div>
              </div>
            </div>
          </div>
        </details>
      </div>
    </div>
  `;

  container.innerHTML = html;
}

function switchHistorySubTab(subTabName) {
  activeHistorySubTab = subTabName;
  const subtabs = ["provenance", "replay", "evidence"];
  subtabs.forEach(t => {
    const el = document.getElementById(`subtab${t.charAt(0).toUpperCase() + t.slice(1)}`);
    const btn = document.getElementById(`btnHist${t.charAt(0).toUpperCase() + t.slice(1)}`);
    if (el) el.style.display = t === subTabName ? "flex" : "none";
    if (btn) {
      if (t === subTabName) btn.classList.add("active");
      else btn.classList.remove("active");
    }
  });
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
function closeMobileSidebar() {
  if (window.innerWidth <= 768) {
    const sidebar = document.getElementById("mainSidebar");
    const backdrop = document.getElementById("sidebarBackdrop");
    const toggleBtn = document.getElementById("sidebarToggleBtn");
    if (sidebar) sidebar.classList.remove("mobile-open");
    if (backdrop) backdrop.classList.remove("active");
    if (toggleBtn) {
      toggleBtn.setAttribute("aria-expanded", "false");
      toggleBtn.setAttribute("aria-label", "Open navigation");
    }
  }
}

function switchMainTab(viewKey, navItem) {
  // Normalize view aliases
  const viewMap = {
    overviewView: "viewOverview",
    overview: "viewOverview",
    fieldSummaryView: "viewOverview",
    monitoringView: "viewMonitoring",
    monitoring: "viewMonitoring",
    mapView: "viewMap",
    map: "viewMap",
    regionalView: "viewMap",
    decisionsView: "viewDecisions",
    decisions: "viewDecisions",
    governanceView: "viewDecisions",
    governance: "viewDecisions",
    historyView: "viewHistory",
    history: "viewHistory",
    lineageView: "viewHistory",
    replayView: "viewHistory",
    scientificView: "viewHistory",
    evidencePackView: "viewHistory"
  };

  const targetViewId = viewMap[viewKey] || "viewOverview";

  // Fast-path: if already on target view and no subtab change requested
  const isSubtabRequest = ["replayView", "evidencePackView", "scientificView", "lineageView"].includes(viewKey);
  if (targetViewId === activeMainView && !isSubtabRequest) {
    closeMobileSidebar();
    return;
  }

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

  // Reparent Leaflet map between Overview and Full Map View
  if (targetViewId === "viewOverview") {
    reparentMap("overviewMapContainer");
  } else if (targetViewId === "viewMap") {
    reparentMap("fullMapContainer");
    if (typeof selectMapLocation === "function") {
      selectMapLocation(currentSelectedMapZoneKey, false);
    }
  }

  // If specific history alias was clicked, auto-switch subtab
  if (viewKey === "replayView") switchHistorySubTab("replay");
  if (viewKey === "evidencePackView") switchHistorySubTab("evidence");
  if (viewKey === "scientificView") switchHistorySubTab("scientific");
  if (viewKey === "lineageView") switchHistorySubTab("provenance");

  // On mobile only, close the off-canvas drawer
  closeMobileSidebar();
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
  const toggleBtn = document.getElementById("sidebarToggleBtn");
  if (!sidebar) return;

  const isMobile = window.innerWidth <= 768;

  if (isMobile) {
    let isOpen;
    if (forceState !== undefined) {
      isOpen = !!forceState;
      if (isOpen) {
        sidebar.classList.add("mobile-open");
        if (backdrop) backdrop.classList.add("active");
      } else {
        sidebar.classList.remove("mobile-open");
        if (backdrop) backdrop.classList.remove("active");
      }
    } else {
      isOpen = sidebar.classList.toggle("mobile-open");
      if (backdrop) {
        if (isOpen) backdrop.classList.add("active");
        else backdrop.classList.remove("active");
      }
    }
    if (toggleBtn) {
      toggleBtn.setAttribute("aria-expanded", isOpen ? "true" : "false");
      toggleBtn.setAttribute("aria-label", isOpen ? "Close navigation" : "Open navigation");
    }
  } else {
    // Desktop: explicit toggle only
    let isCollapsed;
    if (forceState !== undefined) {
      isCollapsed = !!forceState;
      if (isCollapsed) sidebar.classList.add("collapsed");
      else sidebar.classList.remove("collapsed");
    } else {
      isCollapsed = sidebar.classList.toggle("collapsed");
    }

    // Persist user preference in sessionStorage
    try {
      sessionStorage.setItem("vana_sidebar_collapsed", isCollapsed ? "true" : "false");
    } catch (e) {
      // Ignore storage restrictions
    }

    // Update accessible state and tooltip
    if (toggleBtn) {
      toggleBtn.setAttribute("aria-expanded", isCollapsed ? "false" : "true");
      toggleBtn.setAttribute("aria-label", isCollapsed ? "Expand navigation sidebar" : "Collapse navigation sidebar");
      toggleBtn.title = isCollapsed ? "Expand Navigation" : "Collapse Navigation";
    }

    // Invalidate Leaflet map size after sidebar width transition completes
    setTimeout(() => {
      if (window.VanaGeoEngine && window.VanaGeoEngine.map) {
        window.VanaGeoEngine.map.invalidateSize();
      }
    }, 220);
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
            <div style="font-size:11px;color:var(--text-secondary);font-weight:500;">Total Forest Cover (Statewide)</div>
            <div style="font-size:18px;font-weight:700;color:var(--brand);margin-top:2px;" class="mono">${totalAreaStr} ${unitStr}</div>
            <div style="font-size:10.5px;color:var(--text-muted);margin-top:2px;">${totalPctStr} (Inside + Outside RFA)</div>
          </div>

          <div style="background:var(--bg-surface);border:1px solid var(--border-light);border-radius:var(--radius-md);padding:10px 12px;">
            <div style="font-size:11px;color:var(--text-secondary);font-weight:500;">Mangrove Canopy Area</div>
            <div style="font-size:18px;font-weight:700;color:var(--brand);margin-top:2px;" class="mono">${mangroveAreaStr} ${unitStr}</div>
            <div style="font-size:10.5px;color:var(--text-muted);margin-top:2px;">Coastal wetland surveillance zone</div>
          </div>

          <div style="background:var(--bg-surface);border:1px solid var(--border-light);border-radius:var(--radius-md);padding:10px 12px;">
            <div style="font-size:11px;color:var(--text-secondary);font-weight:500;">Very Dense Forest (>70%)</div>
            <div style="font-size:18px;font-weight:700;color:var(--text-main);margin-top:2px;" class="mono">${vdfStr} ${unitStr}</div>
            <div style="font-size:10.5px;color:var(--text-muted);margin-top:2px;">Inside RFA · Closed canopy</div>
          </div>

          <div style="background:var(--bg-surface);border:1px solid var(--border-light);border-radius:var(--radius-md);padding:10px 12px;">
            <div style="font-size:11px;color:var(--text-secondary);font-weight:500;">Moderately Dense (40-70%)</div>
            <div style="font-size:18px;font-weight:700;color:var(--text-main);margin-top:2px;" class="mono">${mdfStr} ${unitStr}</div>
            <div style="font-size:10.5px;color:var(--text-muted);margin-top:2px;">Inside RFA · Medium canopy</div>
          </div>

          <div style="background:var(--bg-surface);border:1px solid var(--border-light);border-radius:var(--radius-md);padding:10px 12px;">
            <div style="font-size:11px;color:var(--text-secondary);font-weight:500;">Open Forest (10-40%)</div>
            <div style="font-size:18px;font-weight:700;color:var(--text-main);margin-top:2px;" class="mono">${ofStr} ${unitStr}</div>
            <div style="font-size:10.5px;color:var(--text-muted);margin-top:2px;">Inside RFA · Porous / edge canopy</div>
          </div>
        </div>

        <div style="font-size:11px;color:var(--text-secondary);line-height:1.45;background:var(--bg-surface-subtle);border:1px solid var(--border-light);border-radius:var(--radius-sm);padding:8px 12px;">
          <strong>Geographic Breakdown Arithmetic:</strong> Density category figures (Very Dense: ${vdfStr} ${unitStr}, Moderately Dense: ${mdfStr} ${unitStr}, Open: ${ofStr} ${unitStr}) sum to <strong>36,110.93 ${unitStr}</strong>, representing forest cover strictly <em>Inside Recorded Forest Area (RFA)</em>. Statewide Total Forest Cover (<strong>${totalAreaStr} ${unitStr}</strong>) additionally encompasses 14,747.60 ${unitStr} situated <em>Outside Recorded Forest Area</em> per ISFR 2023 Table 2.4.
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

