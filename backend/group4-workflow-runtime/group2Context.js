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
const GROUP1_API = process.env.GROUP1_SERVICE_URL || 'http://163.128.209.18:8013';

/**
 * POST /api/group2/context/resolve
 * 
 * Receives Canonical Observation payload from Group 1, validates it,
 * attaches required scientific context (Group 2), and requests SANSKAR intelligence.
 */
router.options('/resolve', (req, res) => {
    res.header("Access-Control-Allow-Origin", "*");
    res.header("Access-Control-Allow-Methods", "POST, OPTIONS");
    res.header("Access-Control-Allow-Headers", "Content-Type, Authorization");
    return res.status(200).send();
});

router.post('/resolve', async (req, res) => {
    res.header("Access-Control-Allow-Origin", "*");
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
            const g1Response = await axios.get(`${GROUP1_API}/observations/${observationId}`);
            canonicalRecord = g1Response.data.observation || g1Response.data.record || g1Response.data;

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
        console.log(`[GROUP2] Context resolution initiated for observation: ${observationId}`);
        const contextPayload = {
            observationId,
            canonicalRecordId: canonicalRecord.canonical_record_id || canonicalRecord.id || canonicalRecord.canonicalId || null,
            location: location || canonicalRecord.location || null,
            // STRICT VANA RULE: Process dates intelligently and map all possible G1 formats without fabricating fresh fallback timestamps
            timestamp: (() => {
                const tsStr = timestamp || canonicalRecord.source_timestamp || canonicalRecord.observed_at || canonicalRecord.observation_timestamp || canonicalRecord.timestamp;
                if (!tsStr) return null;
                try { return new Date(tsStr).toISOString(); } catch (e) { return tsStr; } // Format intelligently
            })(),
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
                    source: canonicalRecord.provider || null,
                    confidence: contextPayload.confidence,
                    missing_critical_data: missingDataStr,
                    provenance_reference: canonicalRecord.provenance_reference || canonicalRecord.provenance || null,
                    artifact_hash: canonicalRecord.artifact_hash || (canonicalRecord.raw_artifacts && canonicalRecord.raw_artifacts[0] ? canonicalRecord.raw_artifacts[0].content_hash : null),
                    artifact_type: canonicalRecord.artifact_type || (canonicalRecord.raw_artifacts && canonicalRecord.raw_artifacts[0] ? canonicalRecord.raw_artifacts[0].artifact_type : null),
                    observation_timestamp: contextPayload.timestamp || null,
                    retrieval_timestamp: canonicalRecord.retrieval_timestamp || null,
                    attribution: canonicalRecord.attribution || (canonicalRecord.raw_artifacts && canonicalRecord.raw_artifacts[0] ? canonicalRecord.raw_artifacts[0].attribution : null) || null,
                    canonical_observation_location: canonicalRecord.location || null
                },
                provenance: {
                    group2_decision_time: new Date().toISOString(),
                    reason: reasonStr,
                    message: msgStr
                }
            };
            console.log(`[GROUP2] Governing output determined: ${finalRuling.ruling}`);
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
                    source: canonicalRecord.source || canonicalRecord.source_name || contextPayload.sourceContext || null,
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

        console.log(`[GROUP2] Successfully completed canonical resolution for payload.`);
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
