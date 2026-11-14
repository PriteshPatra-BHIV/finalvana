const test = require('node:test');
const assert = require('node:assert/strict');
const Module = require('module');

// Intercept express and axios for zero-dependency native testing
const origRequire = Module.prototype.require;
let mockObservationData = null;

const routes = {};
const mockRouter = {
    options: (path, handler) => { routes[`OPTIONS ${path}`] = handler; },
    post: (path, handler) => { routes[`POST ${path}`] = handler; }
};
const mockExpress = () => mockRouter;
mockExpress.Router = () => mockRouter;

const mockAxios = {
    get: async (url) => {
        if (mockObservationData) {
            return mockObservationData;
        }
        throw new Error('Not found');
    }
};

Module.prototype.require = function(path) {
    if (path === 'express') return mockExpress;
    if (path === 'axios') return mockAxios;
    return origRequire.apply(this, arguments);
};

// Require group2Context cleanly using relative path
const group2Context = require('./group2Context');

// Helper to simulate request to route handler
async function callResolve(body) {
    let statusCode = 200;
    let responseBody = null;
    const req = {
        body,
        header: () => {}
    };
    const res = {
        header: () => res,
        status: (code) => {
            statusCode = code;
            return res;
        },
        json: (data) => {
            responseBody = data;
            return res;
        },
        send: (data) => {
            responseBody = data;
            return res;
        }
    };

    const handler = routes['POST /resolve'];
    if (!handler) throw new Error('POST /resolve handler not registered');
    await handler(req, res);
    return { status: statusCode, body: responseBody };
}

test('Group 2 Lineage Verification', async (t) => {
    t.afterEach(() => {
        mockObservationData = null;
    });

    await t.test('should preserve canonical_record_id, provenance_reference, and timestamps exactly', async () => {
        mockObservationData = {
            data: {
                observation: {
                    observation_id: 'OBS-TEST',
                    canonical_record_id: 'CR-TEST',
                    provenance_reference: 'source-test-123',
                    observation_timestamp: '2026-09-01T10:00:00Z'
                }
            }
        };

        const res = await callResolve({ observationId: 'OBS-TEST' });

        assert.strictEqual(res.status, 200);

        // Rules 1, 2, 3: Preserve exactly as received
        assert.strictEqual(res.body.canonical_record_id, 'CR-TEST');
        assert.strictEqual(res.body.evidence.provenance_reference, 'source-test-123');
        assert.strictEqual(res.body.evidence.observation_timestamp, '2026-09-01T10:00:00.000Z');

        // Rule 5: Never generate a canonical_record_id (must match source exactly)
        assert.doesNotMatch(res.body.canonical_record_id, /ctx_|uuid/);

        // Rule 6, 7: Never replace with "N/A" or source_id
        assert.notStrictEqual(res.body.evidence.provenance_reference, 'N/A');
    });

    await t.test('should ensure null values remain null structurally without fabricating metadata', async () => {
        mockObservationData = {
            data: {
                observation: {
                    observation_id: 'OBS-TEST-NULL',
                    canonical_record_id: null,
                    provenance_reference: null,
                    observation_timestamp: null
                }
            }
        };

        const res = await callResolve({ observationId: 'OBS-TEST-NULL' });

        assert.strictEqual(res.status, 200);

        // Rule 4: If any value is null, keep it null
        assert.strictEqual(res.body.canonical_record_id, null);
        assert.strictEqual(res.body.evidence.provenance_reference, null);
        assert.strictEqual(res.body.evidence.observation_timestamp, null);
    });
});
