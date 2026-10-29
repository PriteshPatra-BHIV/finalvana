/**
 * VANA Control Center: API Configuration
 *
 * Single source of truth for all backend endpoint configuration.
 * Loaded before app.js. Defines window.VANA_CONFIG.
 *
 * Deployment model:
 *   Local dev : Python proxy on :8080 rewrites /proxy/* → real backends
 *   Production: Vercel rewrites /proxy/* → real backends (server-side, no mixed-content)
 *
 * No secrets, API keys, or direct backend IPs belong here.
 * All routes use /proxy/* so this file is identical in every environment.
 */
(function () {
  "use strict";

  // Determine base API URL override if configured via environment (e.g. in staging/prod)
  // Resolution priority:
  //   1. window.VITE_API_URL or window.__ENV__.VITE_API_URL (injected runtime globals)
  //   2. <meta name="vite-api-url" content="..."> (injected via deployment/build step)
  //   3. process.env.VITE_API_URL (in Node.js SSR / test runners)
  // Otherwise default to the /proxy/* gateway matching local dev and Vercel rewrites.
  var envApiUrl = "";
  if (typeof window !== "undefined") {
    var metaEl = typeof document !== "undefined" ? document.querySelector('meta[name="vite-api-url"]') : null;
    var metaVal = metaEl ? metaEl.getAttribute("content") : "";
    envApiUrl = (window.VITE_API_URL || (window.__ENV__ && window.__ENV__.VITE_API_URL) || metaVal || "").trim();
  } else if (typeof process !== "undefined" && process.env && process.env.VITE_API_URL) {
    envApiUrl = process.env.VITE_API_URL.trim();
  }

  if (envApiUrl && envApiUrl.endsWith("/")) {
    envApiUrl = envApiUrl.slice(0, -1);
  }

  var vanaConfig = Object.freeze({
    // -------------------------------------------------------------------------
    // Unified Authentication & RBAC API Endpoints
    // Consistent route convention: /auth/* (with /api/v1/auth/* backend aliases)
    // -------------------------------------------------------------------------
    AUTH_BASE: envApiUrl ? envApiUrl + "/auth" : "/proxy/auth",
    AUTH_LOGIN: envApiUrl ? envApiUrl + "/auth/login" : "/proxy/auth/login",
    AUTH_REGISTER: envApiUrl ? envApiUrl + "/auth/register" : "/proxy/auth/register",
    AUTH_ME: envApiUrl ? envApiUrl + "/auth/me" : "/proxy/auth/me",

    // -------------------------------------------------------------------------
    // Group 1: Canonical Observation Retrieval & Statutory Datasets
    // Route: GET /proxy/g1/observations/{observation_id}
    // Route: POST /proxy/g1/observations
    // Route: GET /proxy/g1/datasets/{dataset_id}/forest-cover
    // -------------------------------------------------------------------------
    G1_BASE: "/proxy/g1",
    G1_OBSERVATIONS: "/proxy/g1/observations",
    G1_DATASETS: "/proxy/g1/datasets",
    G1_OFFICIAL: "/proxy/g1/official",

    // -------------------------------------------------------------------------
    // Group 2: Scientific Context & Decision Resolve
    // Route: POST /proxy/g2/api/group2/context/resolve
    // -------------------------------------------------------------------------
    G2_ENDPOINT: "/proxy/g2/api/group2/context/resolve",

    // -------------------------------------------------------------------------
    // Group 4: Governed Execution & Abstention Gate
    // Route: POST /proxy/g4/vana/execute (served by unified runtime)
    // -------------------------------------------------------------------------
    G4_ENDPOINT: envApiUrl ? envApiUrl + "/vana/execute" : "/proxy/g4/vana/execute",

    // -------------------------------------------------------------------------
    // Network timeout for all API calls (milliseconds)
    // -------------------------------------------------------------------------
    REQUEST_TIMEOUT_MS: 10000,
  });

  if (typeof window !== "undefined") {
    window.VANA_CONFIG = vanaConfig;
    console.log("[VANA Config] Endpoints loaded:", {
      AUTH_LOGIN: window.VANA_CONFIG.AUTH_LOGIN,
      AUTH_ME: window.VANA_CONFIG.AUTH_ME,
      G1: window.VANA_CONFIG.G1_BASE,
      G2: window.VANA_CONFIG.G2_ENDPOINT,
      G4: window.VANA_CONFIG.G4_ENDPOINT,
      TIMEOUT: window.VANA_CONFIG.REQUEST_TIMEOUT_MS + "ms",
    });
  }

  if (typeof module !== "undefined" && module.exports) {
    module.exports = vanaConfig;
  }
})();
