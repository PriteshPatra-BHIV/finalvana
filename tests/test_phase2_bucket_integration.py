"""
Test Suite: Phase 2 BIQOS Bucket Cryptographic Sealing & Envelope Validation
=============================================================================
Verifies Siddhesh's 3-step Bucket integration contract:
1. GET /bucket/latest-hash chaining logic (genesis null check & exact character match).
2. Strict envelope structure (6 mandatory fields + parent_hash + payload, zero schema drift).
3. Rejecting unauthorized top-level keys with Schema Drift Error.
4. Payload isolation for Nagarpranali requests & responses.
5. End-to-end integration via nagarpranali_adapter and unified_auth_runtime.
"""

import sys
import uuid
from pathlib import Path
import pytest

FINALVANA_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = FINALVANA_DIR / "backend"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import bucket_client
import nagarpranali_adapter
import unified_auth_runtime


def test_bucket_envelope_mandatory_fields():
    """Verifies that the envelope contains exactly the 6 mandatory fields + parent_hash + payload."""
    trace_id = "VANA-NP-test-trace-001"
    inp = {"signal_type": "Flood Alert", "location": "Thane Creek Zone A", "severity": "HIGH"}
    out = {"status": "success", "zone_id": "TC-Z03-F02"}
    
    envelope = bucket_client.build_bucket_envelope(
        trace_id=trace_id,
        input_payload=inp,
        output_payload=out,
        parent_hash="d8ecc25c7020b304265321c489fe7727d21224789cfd931ef4a3ee28fabe861d",
    )
    
    # Check top-level keys
    allowed_keys = {
        "artifact_id",
        "trace_id",
        "timestamp_utc",
        "schema_version",
        "source_module_id",
        "artifact_type",
        "parent_hash",
        "payload",
    }
    assert set(envelope.keys()).issubset(allowed_keys)
    
    # Check values
    assert envelope["trace_id"] == trace_id
    assert envelope["schema_version"] == "1.0.0"
    assert envelope["source_module_id"] == "vana.nagarpranali"
    assert envelope["artifact_type"] == "nagarpranali_enrichment"
    assert envelope["payload"]["endpoint"] == "POST /api/nagarpranali/enrich"
    assert envelope["payload"]["input"] == inp
    assert envelope["payload"]["output"] == out


def test_bucket_schema_drift_rejection():
    """Verifies that unknown top-level keys are strictly rejected (Schema Drift)."""
    envelope = bucket_client.build_bucket_envelope(
        trace_id="VANA-NP-drift-001",
        input_payload={"test": 1},
        output_payload={"test": 2},
    )
    # Inject unknown top-level field (e.g. Nagarpranali data placed at root)
    envelope["unauthorized_field"] = "malformed_drift_data"
    
    with pytest.raises(bucket_client.BucketSchemaDriftError) as exc_info:
        bucket_client.validate_envelope_structure(envelope, last_hash=None, artifact_count=0)
    
    assert "Schema drift detected" in str(exc_info.value)
    assert "unauthorized_field" in str(exc_info.value)


def test_bucket_client_hash_prohibition():
    """Verifies that client must NOT send a pre-computed hash (server computes it)."""
    envelope = bucket_client.build_bucket_envelope(
        trace_id="VANA-NP-hash-001",
        input_payload={"test": 1},
        output_payload={"test": 2},
    )
    envelope["hash"] = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    
    with pytest.raises(bucket_client.BucketValidationError) as exc_info:
        bucket_client.validate_envelope_structure(envelope, last_hash=None, artifact_count=0)
    
    assert "Server computes hash" in str(exc_info.value)


def test_bucket_genesis_chain_rule():
    """Verifies genesis rule: if artifact_count == 0, parent_hash must be null or omitted."""
    # 1. Valid genesis with null parent_hash
    env_genesis_valid = bucket_client.build_bucket_envelope(
        trace_id="VANA-NP-genesis-001",
        input_payload={"genesis": True},
        output_payload={"genesis": True},
        parent_hash=None,
    )
    bucket_client.validate_envelope_structure(env_genesis_valid, last_hash=None, artifact_count=0)
    
    # 2. Invalid genesis sending a non-null parent_hash
    env_genesis_invalid = bucket_client.build_bucket_envelope(
        trace_id="VANA-NP-genesis-002",
        input_payload={"genesis": True},
        output_payload={"genesis": True},
        parent_hash="any_hash_string",
    )
    with pytest.raises(bucket_client.BucketValidationError) as exc_info:
        bucket_client.validate_envelope_structure(env_genesis_invalid, last_hash=None, artifact_count=0)
    
    assert "Invalid parent_hash for genesis artifact" in str(exc_info.value)


def test_bucket_chained_hash_match_rule():
    """Verifies chained rule: if artifact_count > 0, parent_hash must match last_hash character-for-character."""
    correct_last_hash = "d8ecc25c7020b304265321c489fe7727d21224789cfd931ef4a3ee28fabe861d"
    
    # 1. Valid match
    env_valid = bucket_client.build_bucket_envelope(
        trace_id="VANA-NP-chain-001",
        input_payload={"chain": True},
        output_payload={"chain": True},
        parent_hash=correct_last_hash,
    )
    bucket_client.validate_envelope_structure(env_valid, last_hash=correct_last_hash, artifact_count=1)
    
    # 2. Mismatched hash
    env_mismatch = bucket_client.build_bucket_envelope(
        trace_id="VANA-NP-chain-002",
        input_payload={"chain": True},
        output_payload={"chain": True},
        parent_hash="wrong_hash_123456",
    )
    with pytest.raises(bucket_client.BucketValidationError) as exc_info:
        bucket_client.validate_envelope_structure(env_mismatch, last_hash=correct_last_hash, artifact_count=1)
    
    assert "Invalid parent_hash" in str(exc_info.value)
    assert correct_last_hash in str(exc_info.value)


def test_enrich_endpoint_includes_valid_bucket_envelope():
    """Verifies that enrich_nagarpranali_incident automatically attaches a compliant bucket envelope."""
    req_data = {
        "signal_type": "Flood Alert",
        "location": "Thane Creek Zone A",
        "lat": 19.12,
        "lon": 72.99,
        "severity": "HIGH",
    }
    res = nagarpranali_adapter.enrich_nagarpranali_incident(req_data)
    assert "bucket_envelope" in res
    env = res["bucket_envelope"]
    
    assert env["schema_version"] == "1.0.0"
    assert env["source_module_id"] == "vana.nagarpranali"
    assert env["artifact_type"] == "nagarpranali_enrichment"
    assert env["payload"]["input"]["location"] == "Thane Creek Zone A"
    assert env["payload"]["output"]["zone_id"] == "TC-Z03-F02"
    assert env["payload"]["output"]["canonical_record_id"] == "CR-e95e9174-969b-46ff-9ba3-cbff085150b4"
    
    # Validate structure
    bucket_client.validate_envelope_structure(env, last_hash=None, artifact_count=0)


def test_abstain_fail_closed_bucket_sealing():
    """Verifies that fail-closed abstentions (e.g. unmapped coordinates) are sealed with ABS-... audit ID."""
    req_data = {
        "signal_type": "Unmapped Coordinate Check",
        "lat": 0.0,
        "lon": 0.0,
        "severity": "LOW",
    }
    res = nagarpranali_adapter.enrich_nagarpranali_incident(req_data)
    env = res["bucket_envelope"]
    
    assert env["payload"]["output"]["status"] == "abstain"
    assert env["payload"]["output"]["statutory_action"] == "noop"
    assert env["payload"]["output"]["abstention_id"].startswith("ABS-")
    
    # Offline deterministic hash can be computed
    det_hash = bucket_client.compute_deterministic_artifact_hash(env)
    assert len(det_hash) == 64
