import sys
import json
import time
from pathlib import Path

FINALVANA_DIR = Path(__file__).resolve().parent
BACKEND_DIR = FINALVANA_DIR / "backend"
sys.path.insert(0, str(BACKEND_DIR))

import unified_auth_runtime
import nagarpranali_adapter
import bucket_client

print("Executing Phase 4 Live Runtime Invocations...")
t_start = time.time()

# 1. Scenario A: Citizen Flood Alert at Thane Creek Zone A
req_a = unified_auth_runtime.NagarpranaliEnrichRequest(
    signal_type="Flood Alert",
    location="Thane Creek Zone A",
    lat=19.12,
    lon=72.99,
    incident_type="Mangrove Buffer Siltation & Waterlogging",
    severity="HIGH",
)
res_a = unified_auth_runtime.enrich_nagarpranali(req_a)

# 2. Scenario B: Fail-Closed Unmapped Coordinates
req_b = unified_auth_runtime.NagarpranaliEnrichRequest(
    signal_type="Civic Hazard",
    lat=0.0,
    lon=0.0,
    severity="LOW",
)
res_b = unified_auth_runtime.enrich_nagarpranali(req_b)

# 3. Scenario C: Empty Location Fail-Closed
req_c = unified_auth_runtime.NagarpranaliLifecycleRequest(
    signal_type="Civic Hazard",
    location="   ",
)
res_c = unified_auth_runtime.run_nagarpranali_lifecycle(req_c)

# 4. Scenario D: Full 5-Stage Nagarpranali + VANA Operational Lifecycle
req_d = unified_auth_runtime.NagarpranaliLifecycleRequest(
    signal_type="Flood Alert",
    location="Thane Creek Zone A",
    incident_type="Mangrove Siltation & Waterlogging",
    severity="HIGH",
    lat=19.12,
    lon=72.99,
)
res_d = unified_auth_runtime.run_nagarpranali_lifecycle(req_d)

# 5. Citizen UX Card Format Test
ux_card = nagarpranali_adapter.format_citizen_ux_card(
    lat=19.12,
    lon=72.99,
    location_name="Thane Creek Zone A",
    signal_type="Citizen Waterlogging Report",
)

t_end = time.time()
execution_time_ms = round((t_end - t_start) * 1000, 2)

evidence_packet = {
    "execution_timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    "total_execution_ms": execution_time_ms,
    "scenario_a_verified": {
        "status": res_a["environmental_intelligence"]["status"],
        "zone_id": res_a["environmental_intelligence"]["zone_id"],
        "protection_class": res_a["environmental_intelligence"]["protection_class"],
        "tree_canopy_density": res_a["environmental_intelligence"]["tree_canopy_density"],
        "canonical_record_id": res_a["environmental_intelligence"]["canonical_record_id"],
        "statutory_action": res_a["environmental_intelligence"]["statutory_action"],
        "recommended_escalation": res_a["recommended_escalation"],
        "plain_language_action": res_a["plain_language_action"],
        "bucket_envelope": res_a["bucket_envelope"],
    },
    "scenario_b_fail_closed": {
        "status": res_b["environmental_intelligence"]["status"],
        "governance_status": res_b["environmental_intelligence"]["governance_status"],
        "statutory_action": res_b["environmental_intelligence"]["statutory_action"],
        "abstention_id": res_b["environmental_intelligence"]["abstention_id"],
        "reason": res_b["environmental_intelligence"]["reason"],
    },
    "scenario_c_negative_input": {
        "success": res_c["success"],
        "governance_ruling": res_c["governance_ruling"],
        "decision_text": res_c["decision_text"],
    },
    "scenario_d_lifecycle": {
        "success": res_d["success"],
        "signalId": res_d["signalId"],
        "telemetryId": res_d["telemetryId"],
        "incidentId": res_d["incidentId"],
        "decisionId": res_d["decisionId"],
        "replayId": res_d["replayId"],
        "governance_ruling": res_d["governance_ruling"],
        "ai_guidance": res_d["ai_guidance"],
        "replay_timeline": res_d["replay_timeline"],
    },
    "citizen_ux_card": ux_card,
}

evidence_file = FINALVANA_DIR / "phase4_runtime_evidence.json"
with open(evidence_file, "w", encoding="utf-8") as f:
    json.dump(evidence_packet, f, indent=2)

print(f"Runtime Scenarios successfully executed in {execution_time_ms} ms.")
print(f"Evidence file saved to: {evidence_file}")
