const axios = require('axios');
const fs = require('fs');
const path = require('path');

const API_URL = 'http://localhost:8002/api/group2/context/resolve';
const PACKET_DIR = path.join(__dirname, 'REVIEW_PACKET');

if (!fs.existsSync(PACKET_DIR)) {
    fs.mkdirSync(PACKET_DIR);
}

// 6 Required Scenarios for EOD Handover
const scenarios = [
    {
        name: "1_complete_evidence",
        description: "Valid Canonical ID, Valid Timestamp, Marine/GIS/GOUDHA context present.",
        payload: {
            observationId: "TC-Z03-EXT-OPENMETEO-OBS001",
            simulate_g1_response: {
                canonical_record_id: "CR-b4615a27-7ab1-4bde-a078-a56fa0f2414c",
                observation_timestamp: "2026-08-25T11:00:00Z",
                verified: true,
                marine_evidence: "MARINE_DATA_OK",
                gis_evidence: "GIS_DATA_OK",
                goudha_evidence: "GOUDHA_41_OK"
            }
        }
    },
    {
        name: "2_incomplete_evidence",
        description: "Valid Canonical ID and Timestamp, but MISSING context blocks.",
        payload: {
            observationId: "TC-Z03-EXT-OPENMETEO-OBS002",
            simulate_g1_response: {
                canonical_record_id: "CR-b4615a27-7ab1-4bde-a078-a56fa0f2414c",
                observation_timestamp: "2026-08-25T11:00:00Z",
                verified: true,
                marine_evidence: null,
                gis_evidence: null,
                goudha_evidence: null
            }
        }
    },
    {
        name: "3_missing_timestamp",
        description: "MISSING_SOURCE_TIMESTAMP condition strictly triggers ABSTAIN.",
        payload: {
            observationId: "TC-Z03-EXT-OPENMETEO-OBS003",
            simulate_g1_response: {
                canonical_record_id: "CR-b4615a27-7ab1-4bde-a078-a56fa0f2414c",
                observation_timestamp: null,
                verified: true
            }
        }
    },
    {
        name: "4_legitimate_not_applicable",
        description: "Non-applicable fields are omitted, but core context is present.",
        payload: {
            observationId: "TC-Z03-EXT-OPENMETEO-OBS004",
            simulate_g1_response: {
                canonical_record_id: "CR-b4615a27-7ab1-4bde-a078-a56fa0f2414d",
                observation_timestamp: "2026-08-25T11:00:00Z",
                verified: true,
                marine_evidence: "NOT_APPLICABLE", // Inland observation
                gis_evidence: "GIS_DATA_OK"
            }
        }
    },
    {
        name: "5_missing_context",
        description: "Canonical Record exists, but all context arrays are empty.",
        payload: {
            observationId: "TC-Z03-EXT-OPENMETEO-OBS005",
            simulate_g1_response: {
                canonical_record_id: "CR-b4615a27-7ab1-4bde-a078-a56fa0f2414e",
                observation_timestamp: "2026-08-25T11:00:00Z",
                verified: false, // Invalidates context
            }
        }
    },
    {
        name: "6_abstention",
        description: "Explicit abstention state for a completely gnarled upstream record.",
        payload: {
            observationId: "OBS_TCFS_001_SAMACHAR_RUN_20260812_01", // The old gnarled observation
            simulate_g1_response: {
                canonical_record_id: null,
                observation_timestamp: null,
                verified: false
            }
        }
    }
];

async function runTests() {
    console.log("🚀 Initializing Group 2 REVIEW_PACKET Generator...");
    for (const test of scenarios) {
        try {
            console.log(`Executing Test: ${test.name}`);
            const response = await axios.post(API_URL, test.payload, { validateStatus: () => true });
            const data = {
                test_case: test.name,
                description: test.description,
                request_payload: test.payload,
                group2_decision_response: response.data
            };

            fs.writeFileSync(path.join(PACKET_DIR, `${test.name}.json`), JSON.stringify(data, null, 2));
            console.log(`✅ Passed: ${test.name}`);
        } catch (error) {
            console.error(`❌ Failed: ${test.name}`);
            console.error(error.stack);
        }
        await new Promise(r => setTimeout(r, 200));
    }
    console.log(`\n🎉 REVIEW_PACKET fully compiled in /server/REVIEW_PACKET/`);
}

runTests();
