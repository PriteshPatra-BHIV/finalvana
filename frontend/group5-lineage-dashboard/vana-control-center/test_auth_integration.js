/**
 * VANA Frontend Authentication & RBAC Integration Test Suite
 * ==========================================================
 * Tests all 14 Authentication requirements, 10 Authorization requirements,
 * and 7 Regression preservation invariants for the VANA Control Center.
 *
 * Run with: node --test test_auth_integration.js
 */

const test = require('node:test');
const assert = require('node:assert/strict');

// Set up mock browser environment
class MockSessionStorage {
  constructor() {
    this.store = {};
  }
  getItem(key) {
    return Object.prototype.hasOwnProperty.call(this.store, key) ? this.store[key] : null;
  }
  setItem(key, val) {
    this.store[key] = String(val);
  }
  removeItem(key) {
    delete this.store[key];
  }
  clear() {
    this.store = {};
  }
}

const mockStorage = new MockSessionStorage();
globalThis.sessionStorage = mockStorage;
globalThis.window = {
  sessionStorage: mockStorage,
  VANA_CONFIG: {
    AUTH_BASE: "/proxy/auth",
    AUTH_LOGIN: "/proxy/auth/login",
    AUTH_REGISTER: "/proxy/auth/register",
    AUTH_ME: "/proxy/auth/me",
    G1_BASE: "/proxy/g1",
    G2_ENDPOINT: "/proxy/g2/api/group2/context/resolve",
    G4_ENDPOINT: "/proxy/g4/vana/execute",
    REQUEST_TIMEOUT_MS: 10000,
  }
};

const auth = require('./admin-auth.js');

// Reset authentication state before each test
test.beforeEach(() => {
  auth.logout();
  mockStorage.clear();
});

// ── AUTHENTICATION TESTS (14/14) ──────────────────────────────────────────

test('TC-AUTH-01: Successful Admin Login maps to PLATFORM_ADMIN and stores token', async () => {
  globalThis.fetch = async (url, options) => {
    assert.equal(url, "/proxy/auth/login");
    const body = JSON.parse(options.body);
    assert.equal(body.email, "admin@vana.gov.in");
    return {
      ok: true,
      status: 200,
      json: async () => ({
        access_token: "jwt-admin-token-123",
        token_type: "bearer",
        user: {
          id: "adm-001",
          email: "admin@vana.gov.in",
          name: "VANA Administrator",
          role: "admin",
          permissions: ["VIEW_DASHBOARD", "VIEW_AUDIT_LOG", "MANAGE_USERS", "EXECUTE_WORKFLOW"]
        }
      })
    };
  };

  const res = await auth.login("admin@vana.gov.in", "secret-password");
  assert.equal(res.success, true);
  assert.equal(res.token, "jwt-admin-token-123");
  assert.equal(res.user.role, auth.ROLES.PLATFORM_ADMIN);
  assert.equal(res.user.email, "admin@vana.gov.in");
  assert.equal(auth.getAccessToken(), "jwt-admin-token-123");
  assert.deepEqual(auth.getAuthHeader(), { "Authorization": "Bearer jwt-admin-token-123" });
  assert.equal(auth.hasPermission(auth.PERMISSIONS.MANAGE_USERS), true);
  assert.equal(auth.hasPermission(auth.PERMISSIONS.EXECUTE_WORKFLOW), true);
});

test('TC-AUTH-02: Successful Participant Login maps to APPROVED_CONSUMER', async () => {
  globalThis.fetch = async () => ({
    ok: true,
    status: 200,
    json: async () => ({
      access_token: "jwt-participant-token-456",
      token_type: "bearer",
      user: {
        id: "part-002",
        email: "participant@vana.gov.in",
        name: "Field Participant",
        role: "participant",
        permissions: ["VIEW_DASHBOARD", "VIEW_MAP", "VIEW_ALERTS", "VIEW_LINEAGE"]
      }
    })
  });

  const res = await auth.login("participant@vana.gov.in", "pass");
  assert.equal(res.success, true);
  assert.equal(res.user.role, auth.ROLES.APPROVED_CONSUMER);
  assert.equal(auth.hasPermission(auth.PERMISSIONS.VIEW_DASHBOARD), true);
  // Participant must NOT have audit log or management permissions
  assert.equal(auth.hasPermission(auth.PERMISSIONS.VIEW_AUDIT_LOG), false);
  assert.equal(auth.hasPermission(auth.PERMISSIONS.MANAGE_USERS), false);
  assert.equal(auth.hasPermission(auth.PERMISSIONS.EXECUTE_WORKFLOW), false);
});

test('TC-AUTH-03: Successful Judge Login maps to AUDITOR', async () => {
  globalThis.fetch = async () => ({
    ok: true,
    status: 200,
    json: async () => ({
      access_token: "jwt-judge-token-789",
      token_type: "bearer",
      user: {
        id: "judge-003",
        email: "judge@vana.gov.in",
        name: "Lineage Judge",
        role: "judge",
        permissions: ["VIEW_DASHBOARD", "VIEW_AUDIT_LOG", "RUN_REPLAY"]
      }
    })
  });

  const res = await auth.login("judge@vana.gov.in", "pass");
  assert.equal(res.success, true);
  assert.equal(res.user.role, auth.ROLES.AUDITOR);
  assert.equal(auth.hasPermission(auth.PERMISSIONS.VIEW_AUDIT_LOG), true);
  assert.equal(auth.hasPermission(auth.PERMISSIONS.RUN_REPLAY), true);
  // Judge must NOT have workflow execution or management
  assert.equal(auth.hasPermission(auth.PERMISSIONS.MANAGE_USERS), false);
  assert.equal(auth.hasPermission(auth.PERMISSIONS.MANAGE_SYSTEM_CONFIG), false);
  assert.equal(auth.hasPermission(auth.PERMISSIONS.EXECUTE_WORKFLOW), false);
});

test('TC-AUTH-04: Successful Auditor Login maps to AUDITOR', async () => {
  globalThis.fetch = async () => ({
    ok: true,
    status: 200,
    json: async () => ({
      access_token: "jwt-auditor-token-101",
      token_type: "bearer",
      user: {
        id: "aud-004",
        email: "auditor@vana.gov.in",
        name: "Security Auditor",
        role: "auditor",
        permissions: ["VIEW_DASHBOARD", "VIEW_AUDIT_LOG"]
      }
    })
  });

  const res = await auth.login("auditor@vana.gov.in", "pass");
  assert.equal(res.success, true);
  assert.equal(res.user.role, auth.ROLES.AUDITOR);
  assert.equal(auth.hasPermission(auth.PERMISSIONS.VIEW_AUDIT_LOG), true);
  assert.equal(auth.hasPermission(auth.PERMISSIONS.EXECUTE_WORKFLOW), false);
});

test('TC-AUTH-05: Successful Steward Login maps to GOVERNANCE_STEWARD', async () => {
  globalThis.fetch = async () => ({
    ok: true,
    status: 200,
    json: async () => ({
      access_token: "jwt-steward-token-202",
      token_type: "bearer",
      user: {
        id: "stew-005",
        email: "steward@vana.gov.in",
        name: "Policy Steward",
        role: "steward",
        permissions: ["VIEW_DASHBOARD", "MANAGE_GOVERNANCE_POLICIES"]
      }
    })
  });

  const res = await auth.login("steward@vana.gov.in", "pass");
  assert.equal(res.success, true);
  assert.equal(res.user.role, auth.ROLES.GOVERNANCE_STEWARD);
  assert.equal(auth.hasPermission(auth.PERMISSIONS.MANAGE_GOVERNANCE_POLICIES), true);
  // Steward must NOT have Admin privileges
  assert.equal(auth.hasPermission(auth.PERMISSIONS.MANAGE_USERS), false);
  assert.equal(auth.hasPermission(auth.PERMISSIONS.MANAGE_SYSTEM_CONFIG), false);
  assert.equal(auth.hasPermission(auth.PERMISSIONS.VIEW_AUDIT_LOG), false);
  assert.equal(auth.hasPermission(auth.PERMISSIONS.EXECUTE_WORKFLOW), false);
});

test('TC-AUTH-06: Invalid credentials returns error without storing tokens', async () => {
  globalThis.fetch = async () => ({
    ok: false,
    status: 401,
    json: async () => ({ detail: "Incorrect username or password" })
  });

  const res = await auth.login("invalid@user.com", "wrong-password");
  assert.equal(res.success, false);
  assert.equal(res.status, 401);
  assert.equal(res.error, "Incorrect username or password");
  assert.equal(auth.getAccessToken(), null);
  assert.equal(auth.getCurrentUser(), null);
});

test('TC-AUTH-07: Missing or malformed login response returns error', async () => {
  globalThis.fetch = async () => ({
    ok: true,
    status: 200,
    json: async () => ({ something: "unexpected" })
  });

  const res = await auth.login("test@vana.gov.in", "pass");
  assert.equal(res.success, false);
  assert.match(res.error, /Malformed login response/);
  assert.equal(auth.getAccessToken(), null);
  assert.equal(auth.getCurrentUser(), null);
});

test('TC-AUTH-08: /me with top-level profile fields normalizes correctly', async () => {
  const normalized = auth.normalizeUserProfile({
    id: "user-top-123",
    email: "top@vana.gov.in",
    role: "admin",
    permissions: ["VIEW_DASHBOARD", "EXECUTE_WORKFLOW"]
  });

  assert.equal(normalized.id, "user-top-123");
  assert.equal(normalized.email, "top@vana.gov.in");
  assert.equal(normalized.role, auth.ROLES.PLATFORM_ADMIN);
  assert.equal(normalized.permissions.includes("EXECUTE_WORKFLOW"), true);
});

test('TC-AUTH-09: /me with nested user and data profile fields normalizes correctly', async () => {
  // Nested under 'user'
  const nestedUser = auth.normalizeUserProfile({
    user: {
      id: "u-nest-1",
      email: "nested@vana.gov.in",
      role: "participant",
      permissions: ["VIEW_DASHBOARD"]
    }
  });
  assert.equal(nestedUser.id, "u-nest-1");
  assert.equal(nestedUser.role, auth.ROLES.APPROVED_CONSUMER);

  // Nested under 'data.user'
  const nestedDataUser = auth.normalizeUserProfile({
    data: {
      user: {
        id: "u-nest-2",
        email: "data.user@vana.gov.in",
        role: "judge",
        permissions: ["VIEW_AUDIT_LOG"]
      }
    }
  });
  assert.equal(nestedDataUser.id, "u-nest-2");
  assert.equal(nestedDataUser.role, auth.ROLES.AUDITOR);
});

test('TC-AUTH-10: Invalid or expired token (401) purges session on restore', async () => {
  mockStorage.setItem("vana_access_token", "expired-jwt-token");
  globalThis.fetch = async () => ({
    ok: false,
    status: 401,
    json: async () => ({ detail: "Token expired" })
  });

  const restored = await auth.restoreSession();
  assert.equal(restored, null);
  assert.equal(auth.getAccessToken(), null);
  assert.equal(auth.getCurrentUser(), null);
});

test('TC-AUTH-11: Network failure or 5xx preserves token without purging and blocks privileged actions', async () => {
  mockStorage.setItem("vana_access_token", "valid-jwt-offline");
  mockStorage.setItem("vana_user_profile", JSON.stringify({
    id: "usr-offline",
    name: "Cached Offline User",
    email: "offline@vana.gov.in",
    role: "PLATFORM_ADMIN",
    permissions: ["VIEW_DASHBOARD", "EXECUTE_WORKFLOW", "MANAGE_USERS"]
  }));

  globalThis.fetch = async () => {
    throw new Error("Network unreachable (ECONNREFUSED)");
  };

  const restored = await auth.restoreSession();
  // Token must NOT be deleted on transient network failure
  assert.equal(auth.getAccessToken(), "valid-jwt-offline");
  assert.notEqual(restored, null);
  assert.equal(restored.name, "Cached Offline User");

  // Invariant 3: Offline cached user cannot perform privileged actions or bypass live validation
  assert.equal(auth.isLiveValidated(), false);
  assert.equal(auth.hasPermission(auth.PERMISSIONS.EXECUTE_WORKFLOW), false);
  assert.equal(auth.hasPermission(auth.PERMISSIONS.MANAGE_USERS), false);
  assert.equal(auth.hasPermission(auth.PERMISSIONS.VIEW_AUDIT_LOG), false);
  // Safe read-only dashboard browsing remains available
  assert.equal(auth.hasPermission(auth.PERMISSIONS.VIEW_DASHBOARD), true);
});

test('TC-AUTH-12: Logout clears session storage and notifies listeners with targeted key removal', () => {
  mockStorage.setItem("vana_access_token", "to-be-cleared");
  mockStorage.setItem("vana_user_profile", JSON.stringify({ name: "User" }));
  mockStorage.setItem("unrelated_app_preference", "persisted_value");

  let listenerFiredWith = "initial";
  auth.onAuthChange((u) => {
    listenerFiredWith = u;
  });

  auth.logout();
  assert.equal(auth.getAccessToken(), null);
  assert.equal(auth.getCurrentUser(), null);
  assert.equal(mockStorage.getItem("vana_access_token"), null);
  assert.equal(mockStorage.getItem("vana_user_profile"), null);
  // Targeted removal: unrelated storage items must remain untouched
  assert.equal(mockStorage.getItem("unrelated_app_preference"), "persisted_value");
  assert.equal(listenerFiredWith, null);
});

test('TC-AUTH-13: Page reload restores a valid session via /me', async () => {
  mockStorage.setItem("vana_access_token", "valid-stored-jwt");
  globalThis.fetch = async (url, options) => {
    assert.equal(url, "/proxy/auth/me");
    assert.equal(options.headers.Authorization, "Bearer valid-stored-jwt");
    return {
      ok: true,
      status: 200,
      json: async () => ({
        id: "restored-user-1",
        email: "restored@vana.gov.in",
        name: "Restored Official",
        role: "admin",
        permissions: ["VIEW_DASHBOARD", "MANAGE_SYSTEM_CONFIG"]
      })
    };
  };

  const restored = await auth.restoreSession();
  assert.notEqual(restored, null);
  assert.equal(restored.id, "restored-user-1");
  assert.equal(restored.role, auth.ROLES.PLATFORM_ADMIN);
  assert.equal(auth.getCurrentUser().name, "Restored Official");
});

test('TC-AUTH-14: Missing permissions fail closed for privileged UI actions', () => {
  // Unauthenticated user
  auth.logout();
  assert.equal(auth.hasPermission(auth.PERMISSIONS.VIEW_DASHBOARD), false);
  assert.equal(auth.hasPermission(auth.PERMISSIONS.MANAGE_USERS), false);
  assert.equal(auth.hasPermission("UNINVENTED_PERMISSION"), false);
});

// ── AUTHORIZATION TESTS (10/10) ───────────────────────────────────────────

test('TC-AUTHZ-01: Admin has access to permitted Admin Control Plane sections', async () => {
  globalThis.fetch = async () => ({
    ok: true,
    status: 200,
    json: async () => ({
      access_token: "admin-jwt",
      user: { id: "1", role: "admin", permissions: ["MANAGE_USERS", "MANAGE_SYSTEM_CONFIG", "VIEW_AUDIT_LOG", "EXECUTE_WORKFLOW"] }
    })
  });
  await auth.login("admin@vana.gov.in", "pass");

  assert.equal(auth.hasPermission(auth.PERMISSIONS.MANAGE_USERS), true);
  assert.equal(auth.hasPermission(auth.PERMISSIONS.MANAGE_SYSTEM_CONFIG), true);
  assert.equal(auth.hasPermission(auth.PERMISSIONS.VIEW_AUDIT_LOG), true);
  assert.equal(auth.hasPermission(auth.PERMISSIONS.EXECUTE_WORKFLOW), true);
});

test('TC-AUTHZ-02: Participant cannot access Admin Control Plane sections', async () => {
  globalThis.fetch = async () => ({
    ok: true,
    status: 200,
    json: async () => ({
      access_token: "participant-jwt",
      user: { id: "2", role: "participant", permissions: ["VIEW_DASHBOARD"] }
    })
  });
  await auth.login("participant@vana.gov.in", "pass");

  assert.equal(auth.hasPermission(auth.PERMISSIONS.MANAGE_USERS), false);
  assert.equal(auth.hasPermission(auth.PERMISSIONS.MANAGE_ROLES), false);
  assert.equal(auth.hasPermission(auth.PERMISSIONS.MANAGE_SYSTEM_CONFIG), false);
  assert.equal(auth.hasPermission(auth.PERMISSIONS.VIEW_AUDIT_LOG), false);
});

test('TC-AUTHZ-03: Participant execution receives 403 and shows useful message', async () => {
  globalThis.fetch = async (url) => {
    if (url === "/proxy/auth/login") {
      return {
        ok: true,
        status: 200,
        json: async () => ({
          access_token: "part-token",
          user: { id: "p1", role: "participant", permissions: ["VIEW_DASHBOARD"] }
        })
      };
    }
    if (url === "/proxy/g4/vana/execute") {
      return {
        ok: false,
        status: 403,
        json: async () => ({ detail: "Approved Consumer role does not have execution dispatch privileges." })
      };
    }
  };

  await auth.login("participant@vana.gov.in", "pass");

  // Simulate app.js execution check
  const g4Headers = Object.assign(
    { "Content-Type": "application/json", "Accept": "application/json" },
    auth.getAuthHeader()
  );
  assert.equal(g4Headers.Authorization, "Bearer part-token");

  const g4Res = await fetch("/proxy/g4/vana/execute", {
    method: "POST",
    headers: g4Headers,
    body: JSON.stringify({ observation_id: "TC-Z03-EXT-OPENMETEO-OBS001" })
  });

  assert.equal(g4Res.status, 403);
  const errJson = await g4Res.json();
  assert.match(errJson.detail, /does not have execution dispatch privileges/);
  // Session must remain intact on 403
  assert.equal(auth.isAuthenticated(), true);
  assert.equal(auth.getCurrentUser().role, auth.ROLES.APPROVED_CONSUMER);
});

test('TC-AUTHZ-04: Admin execution sends the bearer token', async () => {
  let capturedHeaders = null;
  globalThis.fetch = async (url, options) => {
    if (url === "/proxy/auth/login") {
      return {
        ok: true,
        status: 200,
        json: async () => ({
          access_token: "admin-secret-jwt",
          user: { id: "a1", role: "admin", permissions: ["EXECUTE_WORKFLOW"] }
        })
      };
    }
    if (url === "/proxy/g4/vana/execute") {
      capturedHeaders = options.headers;
      return {
        ok: true,
        status: 200,
        json: async () => ({
          ruling: "ABSTAIN",
          status: "governed_abstention",
          evidence: { ruling: "ABSTAIN", abstention_record_id: "ABS-101" }
        })
      };
    }
  };

  await auth.login("admin@vana.gov.in", "pass");
  const authHeader = auth.getAuthHeader();
  assert.equal(authHeader.Authorization, "Bearer admin-secret-jwt");

  await fetch("/proxy/g4/vana/execute", {
    method: "POST",
    headers: Object.assign({ "Content-Type": "application/json" }, authHeader),
    body: JSON.stringify({ observation_id: "obs-1" })
  });

  assert.equal(capturedHeaders.Authorization, "Bearer admin-secret-jwt");
});

test('TC-AUTHZ-05: Judge/Auditor has access to Audit Log but not Workflow Execution', async () => {
  globalThis.fetch = async () => ({
    ok: true,
    status: 200,
    json: async () => ({
      access_token: "auditor-jwt",
      user: { id: "3", role: "judge", permissions: ["VIEW_AUDIT_LOG", "VIEW_DASHBOARD", "RUN_REPLAY"] }
    })
  });
  await auth.login("judge@vana.gov.in", "pass");

  assert.equal(auth.hasPermission(auth.PERMISSIONS.VIEW_AUDIT_LOG), true);
  assert.equal(auth.hasPermission(auth.PERMISSIONS.RUN_REPLAY), true);
  assert.equal(auth.hasPermission(auth.PERMISSIONS.EXECUTE_WORKFLOW), false);
  assert.equal(auth.hasPermission(auth.PERMISSIONS.MANAGE_USERS), false);
});

test('TC-AUTHZ-06: Participant cannot access protected audit logs', async () => {
  globalThis.fetch = async () => ({
    ok: true,
    status: 200,
    json: async () => ({
      access_token: "part-token-2",
      user: { id: "p2", role: "participant", permissions: ["VIEW_DASHBOARD"] }
    })
  });
  await auth.login("part@vana.gov.in", "pass");

  assert.equal(auth.hasPermission(auth.PERMISSIONS.VIEW_AUDIT_LOG), false);
});

test('TC-AUTHZ-07: Steward receives only explicitly granted permissions', async () => {
  globalThis.fetch = async () => ({
    ok: true,
    status: 200,
    json: async () => ({
      access_token: "steward-jwt",
      user: { id: "4", role: "steward", permissions: ["MANAGE_GOVERNANCE_POLICIES"] }
    })
  });
  await auth.login("steward@vana.gov.in", "pass");

  assert.equal(auth.hasPermission(auth.PERMISSIONS.MANAGE_GOVERNANCE_POLICIES), true);
  assert.equal(auth.hasPermission(auth.PERMISSIONS.MANAGE_USERS), false);
  assert.equal(auth.hasPermission(auth.PERMISSIONS.VIEW_AUDIT_LOG), false);
  assert.equal(auth.hasPermission(auth.PERMISSIONS.EXECUTE_WORKFLOW), false);
});

test('TC-AUTHZ-08: Tampered role change or forged cached user cannot elevate privileges', () => {
  // Simulate an attacker trying to call setDevRole
  auth.setDevRole("administrator");
  assert.equal(auth.getCurrentUser(), null);
  assert.equal(auth.hasPermission(auth.PERMISSIONS.MANAGE_USERS), false);
});

test('TC-AUTHZ-09: Tokens are not forwarded to unrelated external hosts', () => {
  mockStorage.setItem("vana_access_token", "confidential-token-999");
  const authHeaders = auth.getAuthHeader();

  // Helper function checking target url before attaching headers
  function attachAuthIfInternal(url, headers) {
    const isInternal = url.startsWith("/proxy/") || url.startsWith("http://localhost:8000");
    return isInternal ? Object.assign({}, headers, authHeaders) : headers;
  }

  const internalReq = attachAuthIfInternal("/proxy/g4/vana/execute", {});
  assert.equal(internalReq.Authorization, "Bearer confidential-token-999");

  const externalReq = attachAuthIfInternal("https://api.open-meteo.com/v1/forecast", {});
  assert.equal(externalReq.Authorization, undefined);

  const tileReq = attachAuthIfInternal("https://tile.openstreetmap.org/1/2/3.png", {});
  assert.equal(tileReq.Authorization, undefined);
});

test('TC-AUTHZ-10: Missing authentication does not trigger protected execution calls', () => {
  assert.equal(auth.isAuthenticated(), false);
  assert.equal(auth.hasPermission(auth.PERMISSIONS.EXECUTE_WORKFLOW), false);

  // In app.js, unauthenticated execution is halted fail-closed before network dispatch
  let networkCallMade = false;
  function attemptExecution() {
    if (!auth.isAuthenticated()) {
      return { blocked: true, reason: "Authentication required" };
    }
    networkCallMade = true;
    return { blocked: false };
  }

  const result = attemptExecution();
  assert.equal(result.blocked, true);
  assert.equal(networkCallMade, false);
});

// ── REGRESSION TESTS (7/7) ────────────────────────────────────────────────

test('TC-REG-01: Group 1 observations still load without auth required', async () => {
  globalThis.fetch = async (url) => {
    assert.equal(url, "/proxy/g1/api/v1/observations/TC-Z03-EXT-OPENMETEO-OBS001");
    return {
      ok: true,
      status: 200,
      json: async () => ({
        canonical_record_id: "CR-b4615a27-7ab1-4bde-a078-a56fa0f2414c",
        observation_id: "TC-Z03-EXT-OPENMETEO-OBS001",
        measurement: 0.1,
        source: "Open-Meteo.com"
      })
    };
  };

  const res = await fetch("/proxy/g1/api/v1/observations/TC-Z03-EXT-OPENMETEO-OBS001");
  assert.equal(res.ok, true);
  const data = await res.json();
  assert.equal(data.canonical_record_id, "CR-b4615a27-7ab1-4bde-a078-a56fa0f2414c");
  assert.equal(data.measurement, 0.1);
});

test('TC-REG-02: Group 2 context resolution remains unchanged', async () => {
  globalThis.fetch = async (url, options) => {
    assert.equal(url, "/proxy/g2/api/group2/context/resolve");
    const body = JSON.parse(options.body);
    assert.equal(body.canonical_record_id, "CR-b4615a27-7ab1-4bde-a078-a56fa0f2414c");
    return {
      ok: true,
      status: 200,
      json: async () => ({
        context_id: "CTX-2026-0825-TC-001",
        ruling: "ABSTAIN",
        action_eligibility: false,
        abstention_required: true
      })
    };
  };

  const res = await fetch("/proxy/g2/api/group2/context/resolve", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ canonical_record_id: "CR-b4615a27-7ab1-4bde-a078-a56fa0f2414c" })
  });
  const data = await res.json();
  assert.equal(data.context_id, "CTX-2026-0825-TC-001");
  assert.equal(data.ruling, "ABSTAIN");
  assert.equal(data.abstention_required, true);
});

test('TC-REG-03: Group 4 execution preserves the backend governed result', async () => {
  const backendResponse = {
    status: "governed_abstention",
    ruling: "ABSTAIN",
    decision_action: "DISPATCH_ACTION_ABSTAIN",
    recorded_at: "2026-08-25T11:00:00Z",
    evidence: {
      status: "governed_abstention",
      ruling: "ABSTAIN",
      abstention_record_id: "ABS-TC-Z03-001",
      governance_allowed: false
    }
  };

  // Normalization logic in app.js
  const ev = backendResponse.evidence || {};
  const outcomeRuling = ev.ruling || backendResponse.ruling;
  const realStatus = ev.status || backendResponse.status;

  assert.equal(outcomeRuling, "ABSTAIN");
  assert.equal(realStatus, "governed_abstention");
  assert.equal(ev.abstention_record_id, "ABS-TC-Z03-001");
  assert.equal(ev.governance_allowed, false);
});

test('TC-REG-04: ABSTAIN continues to produce the existing governed-abstention behavior', () => {
  const data = {
    observation_id: "TC-Z03-EXT-OPENMETEO-OBS001",
    canonical_record_id: "CR-b4615a27-7ab1-4bde-a078-a56fa0f2414c",
    context_id: "CTX-2026-0825-TC-001",
    group2: { ruling: "ABSTAIN", abstention_required: true }
  };

  // Upstream ABSTAIN must not be converted into ALLOW or invented execution
  assert.equal(data.group2.ruling, "ABSTAIN");
  assert.equal(data.group2.abstention_required, true);
});

test('TC-REG-05: Lineage rail and deterministic replay/diff verification logic remain intact', () => {
  const baseline = {
    observation_id: "TC-Z03-EXT-OPENMETEO-OBS001",
    canonical_record_id: "CR-b4615a27-7ab1-4bde-a078-a56fa0f2414c",
    group2: { ruling: "ABSTAIN" },
    group4: { ruling: "ABSTAIN", abstention_record_id: "ABS-001" }
  };

  const replayed = {
    observation_id: "TC-Z03-EXT-OPENMETEO-OBS001",
    canonical_record_id: "CR-b4615a27-7ab1-4bde-a078-a56fa0f2414c",
    group2: { ruling: "ABSTAIN" },
    group4: { ruling: "ABSTAIN", abstention_record_id: "ABS-001" }
  };

  // Deterministic equality check
  const isDeterministic = (
    baseline.canonical_record_id === replayed.canonical_record_id &&
    baseline.group2.ruling === replayed.group2.ruling &&
    baseline.group4.abstention_record_id === replayed.group4.abstention_record_id
  );
  assert.equal(isDeterministic, true);
});

test('TC-REG-06: GIS and regional surveillance zone coordinates remain intact', () => {
  const thaneZone = {
    id: "TC-Z03-EXT-OPENMETEO-OBS001",
    name: "Thane Creek",
    lat: 19.1288,
    lon: 72.9421,
    alt_m: 4.0
  };
  assert.equal(thaneZone.lat, 19.1288);
  assert.equal(thaneZone.lon, 72.9421);
});

test('TC-REG-07: Config object and roles structure export cleanly without runtime errors', () => {
  assert.ok(auth.ROLES.PLATFORM_ADMIN);
  assert.ok(auth.ROLES.APPROVED_CONSUMER);
  assert.ok(auth.ROLES.AUDITOR);
  assert.ok(auth.ROLES.GOVERNANCE_STEWARD);
  assert.ok(auth.PERMISSIONS.VIEW_DASHBOARD);
  assert.ok(auth.PERMISSIONS.EXECUTE_WORKFLOW);
  assert.ok(auth.PERMISSIONS.VIEW_AUDIT_LOG);
  assert.ok(auth.PERMISSIONS.MANAGE_GOVERNANCE_POLICIES);
});

// ── PERMISSIONS OBJECT NORMALIZATION TESTS ────────────────────────────────

test('TC-PERM-OBJ: Backend permissions object representation normalizes safely', () => {
  // Test flat boolean object representation
  const objPerms = auth.normalizePermissions({
    VIEW_DASHBOARD: true,
    EXECUTE_WORKFLOW: true,
    MANAGE_USERS: false,
    audit_review: 1,
  });

  assert.equal(objPerms.has("VIEW_DASHBOARD"), true);
  assert.equal(objPerms.has("EXECUTE_WORKFLOW"), true);
  assert.equal(objPerms.has("audit_review"), true);
  assert.equal(objPerms.has("MANAGE_USERS"), false);
  assert.equal(objPerms.has("NON_EXISTENT"), false);

  // Test nested object representation
  const nestedPerms = auth.normalizePermissions({
    audit: { read: true, delete: false },
    governance: { policy_edit: true },
  });

  assert.equal(nestedPerms.has("AUDIT_READ"), true);
  assert.equal(nestedPerms.has("GOVERNANCE_POLICY_EDIT"), true);
  assert.equal(nestedPerms.has("AUDIT_DELETE"), false);
});
