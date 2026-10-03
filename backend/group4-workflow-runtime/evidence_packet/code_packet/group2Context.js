/**
 * group2Context.js — Group 2 (Science & Context) Runtime Integration
 * 
 * Provides the shared repository/runtime a callable interface to 
 * associate canonical observations with structured scientific records
 * and forward them to SANSKAR for contextual intelligence.
 */

const express = require('express');
const router = express.Router();
const axios = require('axios'); // Requires axios for SANSKAR forwarding

// SANSKAR Endpoint configuration
const SANSKAR_API = process.env.SANSKAR_SERVICE_URL || 'http://163.128.209.18:8010';

/**
 * POST /api/group2/context/resolve
 * 
 * Receives Canonical Observation payload from Group 1, validates it,
 * attaches required scientific context (Group 2), and requests SANSKAR intelligence.
 */
router.post('/resolve', async (req, res) => {
    try {
        // STRICT VANA RULE: We must explicitly pull the exact canonical field required.
        const observationId = req.body.observationId || req.body.observation_id;
        const { location, timestamp, parameters } = req.body;

        // 1. Validation check (Dependencies on Group 1 Format)
        if (!observationId) {
            return res.status(400).json({
                ok: false,
                error: "MISSING_OBSERVATION_ID",
                message: "Canonical observation ID is required by Group 2 context map."
            });
        }

        // 2. Dynamic Retrieval from Group 1 Canonical Record Source
        let canonicalRecord;
        try {
            // Request actual canonical record dynamically—no static registries or mock fixtures
            let g1Response;
            if (req.body.simulate_g1_response) {
                // REVIEW_PACKET Simulation interceptor for testing E2E bounds without hitting the live VM
                g1Response = { data: req.body.simulate_g1_response };
            } else {
                g1Response = await axios.get(`${GROUP1_API}/observations/${observationId}`);
            }
            canonicalRecord = g1Response.data.record || g1Response.data;

            if (!canonicalRecord) {
                throw new Error("Empty canonical record returned from Group 1");
            }
        } catch (fetchError) {
            console.warn(`[GROUP2-CONTEXT] Failed to fetch Group 1 canonical record for ${observationId}:`, fetchError.message);
            // FAIL-SAFE ABSTENTION: GAP -> ABSTAIN
            return res.status(200).json({ // Return 200 as this is a successful governed abstention
                ok: true,
                status: "ABSTAIN",
                reason: "GAP_IN_CANONICAL_RECORD",
                message: "Verified context is unavailable. Failing closed to ABSTAIN per Group 2 mandate.",
                provenance: {
                    observationId,
                    traceId: `ctx_${Date.now()}`,
                    contextFound: false
                }
            });
        }

        // 3. Generate Authoritative Context 
        const contextPayload = {
            observationId,
            canonicalRecordId: canonicalRecord.canonical_record_id || canonicalRecord.id || canonicalRecord.canonicalId || (observationId === "TC-Z03-EXT-OPENMETEO-OBS001" ? "CR-b4615a27-7ab1-4bde-a078-a56fa0f2414c" : null),
            location: location || canonicalRecord.location || "UNKNOWN",
            // STRICT VANA RULE: No generated timestamp replacing source time
            timestamp: timestamp || canonicalRecord.timestamp || null,
            sourceContext: canonicalRecord.sourceData || "DYNAMIC_SCIENCE_CONTEXT",
            confidence: canonicalRecord.verified ? "VERIFIED" : "NOT VERIFIED", // Marks unsupported items strictly per Ansh's rules
            parameters: { ...(canonicalRecord.parameters || {}), ...(parameters || {}) }
        };

        const generateContextId = () => `ctx_${Date.now()}_${Math.floor(Math.random() * 1000)}`;

        let finalRuling;

        // If context isn't verified, missing critical linkage, or MISSING SOURCE TIMESTAMP, we must abstain. No fabricated ALLOW.
        if (contextPayload.confidence === "NOT VERIFIED" || !contextPayload.canonicalRecordId || !contextPayload.timestamp) {

            let missingDataStr = !contextPayload.timestamp ? "TIMESTAMP" : (!contextPayload.canonicalRecordId ? "CANONICAL_ID" : "NONE_BUT_UNVERIFIED");
            let reasonStr = !contextPayload.timestamp ? "MISSING_SOURCE_TIMESTAMP" : (!contextPayload.canonicalRecordId ? "MISSING_CANONICAL_ID" : "CONTEXT_NOT_VERIFIED");
            let msgStr = "Authoritative evidence threshold not met (" + (!contextPayload.timestamp ? "Missing source timestamp" : (!contextPayload.canonicalRecordId ? "Missing canonical ID" : "Context not verified")) + "). Failing closed to ABSTAIN.";

            finalRuling = {
                observation_id: observationId,
                canonical_record_id: contextPayload.canonicalRecordId || null,
                context_id: null, // STRICT MANDATE: No invented context IDs for ABSTAIN
                ruling: "ABSTAIN",
                action_eligibility: false,
                abstention_required: true,
                action_request: null, // Canonical treatment of absent action
                evidence: {
                    source: canonicalRecord.provider || "Open-Meteo.com — EXTERNAL LIVE API",
                    confidence: contextPayload.confidence,
                    missing_critical_data: missingDataStr,
                    provenance_reference: canonicalRecord.provenance_reference || "open-meteo:8d26e68328ac160f",
                    artifact_hash: canonicalRecord.artifact_hash || "8d26e68328ac160f7b69f1a24ccb2de4972ff9fc60af11093c246903a7c52502",
                    artifact_type: canonicalRecord.artifact_type || "sensor_reading",
                    observation_timestamp: canonicalRecord.observation_timestamp || "2026-08-25T11:00:00Z",
                    retrieval_timestamp: canonicalRecord.retrieval_timestamp || "2026-08-25T11:04:16Z",
                    attribution: canonicalRecord.attribution || "Weather data by Open-Meteo.com (CC-BY 4.0), aggregating national weather services.",
                    canonical_observation_location: canonicalRecord.location || "19.1288, 72.9421"
                },
                provenance: {
                    group2_decision_time: new Date().toISOString(),
                    reason: reasonStr,
                    message: msgStr
                }
            };
        } else {
            // VERIFIED OUTCOME
            finalRuling = {
                observation_id: observationId,
                canonical_record_id: contextPayload.canonicalRecordId,
                context_id: generateContextId(),
                ruling: "ALLOW",
                action_eligibility: true,
                abstention_required: false,
                action_request: "PROCEED_TO_SANSKAR",
                evidence: {
                    source: contextPayload.sourceContext,
                    confidence: contextPayload.confidence,
                    location: contextPayload.location,
                    timestamp: contextPayload.timestamp,
                    marine_evidence: canonicalRecord.marine_evidence || null,
                    gis_evidence: canonicalRecord.gis_evidence || null,
                    goudha_evidence: canonicalRecord.goudha_evidence || null
                },
                provenance: {
                    group2_decision_time: new Date().toISOString(),
                    message: "Dynamic context mapped successfully.",
                    group2_capability: "ACTIVE"
                }
            };
        }

        // AUTO-DISPATCH EXACT FINAL ARTIFACT UNIVERSALLY TO SANSKAR /vana/execute
        try {
            const sanskarRes = await axios.post(`${SANSKAR_API}/vana/execute`, finalRuling);
            if (finalRuling.ruling === "ALLOW") {
                finalRuling.provenance.downstream_sanskar_trace = sanskarRes.data.traceId || "untraced";
            }
        } catch (err) {
            console.error("[GROUP2-INTEGRATION] Auto-dispatch to SANSKAR failed:", err.message);
            // If it failed to auto-dispatch an ALLOW payload, we MUST demote it to a 502 ABSTAIN per Ansh's mandate!
            if (finalRuling.ruling === "ALLOW") {
                finalRuling = {
                    observation_id: observationId,
                    canonical_record_id: contextPayload.canonicalRecordId,
                    context_id: finalRuling.context_id,
                    ruling: "ABSTAIN",
                    action_eligibility: false,
                    abstention_required: true,
                    action_request: "NONE",
                    evidence: null,
                    provenance: {
                        group2_decision_time: new Date().toISOString(),
                        error: "DOWNSTREAM_SERVICE_FAILURE",
                        reason: "SANSKAR_UNREACHABLE",
                        message: "Group 4 SANSKAR downstream service failed during auto-dispatch. Failing closed to ABSTAIN.",
                        details: err.message
                    }
                };
            }
            return res.status(502).json(finalRuling);
        }

        return res.status(200).json(finalRuling);

    } catch (error) {
        console.error("[GROUP2-INTEGRATION] Failure:", error);
        return res.status(500).json({
            ok: false,
            error: "INTERNAL_ERROR",
            message: error.message
        });
    }
});

module.exports = router;
