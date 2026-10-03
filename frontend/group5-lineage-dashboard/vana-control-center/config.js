/**
 * VANA Control Center — API Configuration
 *
 * Single source of truth for all backend endpoint configuration.
 * Loaded before app.js. Defines window.VANA_CONFIG.
 *
 * Deployment model:
 *   Local dev  — Python proxy on :8080 rewrites /proxy/* → real backends
 *   Production — Vercel rewrites /proxy/* → real backends (server-side, no mixed-content)
 *
 * No secrets, API keys, or direct backend IPs belong here.
 * All routes use /proxy/* so this file is identical in every environment.
 */
(function () {
  "use strict";

  window.VANA_CONFIG = Object.freeze({
    // -------------------------------------------------------------------------
    // Group 1 — Canonical Observation Retrieval
    // Route: GET /proxy/g1/observations/{observation_id}
    // -------------------------------------------------------------------------
    G1_BASE: "/proxy/g1",

    // -------------------------------------------------------------------------
    // Group 2 — Scientific Context & Decision Resolve
    // Route: POST /proxy/g2/api/group2/context/resolve
    // -------------------------------------------------------------------------
    G2_ENDPOINT: "/proxy/g2/api/group2/context/resolve",

    // -------------------------------------------------------------------------
    // Group 4 — Governed Execution & Abstention Gate
    // Route: POST /proxy/g4/vana/execute
    // -------------------------------------------------------------------------
    G4_ENDPOINT: "/proxy/g4/vana/execute",

    // -------------------------------------------------------------------------
    // Network timeout for all API calls (milliseconds)
    // A stalled backend will be declared failed after this duration.
    // -------------------------------------------------------------------------
    REQUEST_TIMEOUT_MS: 10000,
  });

  console.log("[VANA Config] Endpoints loaded:", {
    G1: window.VANA_CONFIG.G1_BASE,
    G2: window.VANA_CONFIG.G2_ENDPOINT,
    G4: window.VANA_CONFIG.G4_ENDPOINT,
    TIMEOUT: window.VANA_CONFIG.REQUEST_TIMEOUT_MS + "ms",
  });
})();
