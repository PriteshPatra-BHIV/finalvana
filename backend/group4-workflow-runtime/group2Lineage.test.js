const request = require('supertest');
const express = require('express');
const axios = require('axios');
const group2Context = require('../routes/group2Context');

jest.mock('axios');

const app = express();
app.use(express.json());
app.use('/api/group2/context', group2Context);

describe('Group 2 Lineage Verification', () => {
    afterEach(() => {
        jest.clearAllMocks();
    });

    it('should preserve canonical_record_id, provenance_reference, and timestamps exactly', async () => {
        axios.get.mockResolvedValueOnce({
            data: {
                observation: {
                    observation_id: 'OBS-TEST',
                    canonical_record_id: 'CR-TEST',
                    provenance_reference: 'source-test-123',
                    observation_timestamp: '2026-09-01T10:00:00Z'
                }
            }
        });

        const res = await request(app)
            .post('/api/group2/context/resolve')
            .send({ observationId: 'OBS-TEST' });

        expect(res.status).toBe(200);

        // Rules 1, 2, 3: Preserve exactly as received
        expect(res.body.canonical_record_id).toBe('CR-TEST');
        expect(res.body.evidence.provenance_reference).toBe('source-test-123');
        expect(res.body.evidence.observation_timestamp).toBe('2026-09-01T10:00:00.000Z');

        // Rule 5: Never generate a canonical_record_id (must match source exactly)
        expect(res.body.canonical_record_id).not.toMatch(/ctx_|uuid/);

        // Rule 6, 7: Never replace with "N/A" or source_id
        expect(res.body.evidence.provenance_reference).not.toBe('N/A');
    });

    it('should ensure null values remain null structurally without fabricating metadata', async () => {
        axios.get.mockResolvedValueOnce({
            data: {
                observation: {
                    observation_id: 'OBS-TEST-NULL',
                    canonical_record_id: null,
                    provenance_reference: null,
                    observation_timestamp: null
                }
            }
        });

        const res = await request(app)
            .post('/api/group2/context/resolve')
            .send({ observationId: 'OBS-TEST-NULL' });

        expect(res.status).toBe(200);

        // Rule 4: If any value is null, keep it null
        expect(res.body.canonical_record_id).toBeNull();
        expect(res.body.evidence.provenance_reference).toBeNull();
        expect(res.body.evidence.observation_timestamp).toBeNull();
    });
});
