"""
VANA - BIQOS Bucket Integration Client
=====================================
Implements the 3-Step Cryptographic Sealing Contract for BIQOS Bucket:
1. Fetch latest parent hash via GET /bucket/latest-hash.
2. Build strictly typed envelope (zero schema drift, 6 mandatory fields + parent_hash + payload).
3. Submit envelope via POST /bucket/artifact.

Author: Pratik Bhuvad (Integration Assurance Owner, VANA)
Collaborators: Siddhesh Narkar & Rajarya (TANTRA / BIQOS)
"""

import os
import json
import uuid
import hashlib
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple
import urllib.request
import urllib.error

BUCKET_BASE_URL_DEFAULT = os.environ.get("BIQOS_BUCKET_URL", "http://localhost:8000")

ALLOWED_ENVELOPE_FIELDS = {
    "artifact_id",
    "trace_id",
    "timestamp_utc",
    "schema_version",
    "source_module_id",
    "artifact_type",
    "parent_hash",
    "payload",
    "hash",  # Note: Server computes hash; client must NOT send hash unless server returns it
}

MANDATORY_ENVELOPE_FIELDS = {
    "artifact_id",
    "trace_id",
    "timestamp_utc",
    "schema_version",
    "source_module_id",
    "artifact_type",
}


class BucketSchemaDriftError(Exception):
    """Raised when an unknown top-level field is detected in the envelope."""
    pass


class BucketValidationError(Exception):
    """Raised when mandatory envelope invariants are violated."""
    pass


def validate_envelope_structure(envelope: Dict[str, Any], last_hash: Optional[str] = None, artifact_count: int = 0) -> None:
    """
    Strict validation against BIQOS schema drift and chaining rules.
    """
    # 1. Schema Drift Check: No unauthorized top-level keys
    extra_keys = set(envelope.keys()) - ALLOWED_ENVELOPE_FIELDS
    if extra_keys:
        raise BucketSchemaDriftError(
            f"Unknown envelope field: {list(extra_keys)}. Schema drift detected."
        )

    # 2. Client must not send pre-computed hash
    if "hash" in envelope and envelope["hash"] is not None:
        raise BucketValidationError("Envelope contains 'hash'. Server computes hash — client must not send one.")

    # 3. Mandatory Fields Check
    for field in MANDATORY_ENVELOPE_FIELDS:
        if field not in envelope or not envelope[field]:
            raise BucketValidationError(f"Missing mandatory envelope field: '{field}'")

    # 4. Strict Type / Constant Invariants
    if envelope["schema_version"] != "1.0.0":
        raise BucketValidationError(
            f"Invalid schema_version: Expected '1.0.0', got '{envelope['schema_version']}'"
        )

    if envelope["source_module_id"] != "vana.nagarpranali":
        raise BucketValidationError(
            f"Invalid source_module_id: Expected 'vana.nagarpranali', got '{envelope['source_module_id']}'"
        )

    if envelope["artifact_type"] != "nagarpranali_enrichment":
        raise BucketValidationError(
            f"Invalid artifact_type: Expected 'nagarpranali_enrichment', got '{envelope['artifact_type']}'"
        )

    # 5. Payload Check
    if "payload" not in envelope or not isinstance(envelope["payload"], dict):
        raise BucketValidationError("Envelope 'payload' is required and must be a JSON object dictionary.")

    # 6. Chaining Invariants
    parent_hash = envelope.get("parent_hash")
    if artifact_count == 0:
        if parent_hash is not None and parent_hash != "":
            raise BucketValidationError(
                "Invalid parent_hash for genesis artifact (artifact_count == 0). parent_hash must be null or omitted."
            )
    else:
        if not parent_hash:
            raise BucketValidationError(
                f"parent_hash is required when artifact_count > 0. Expected: {last_hash}"
            )
        if last_hash and parent_hash != last_hash:
            raise BucketValidationError(
                f"Invalid parent_hash. Expected: {last_hash}, Got: {parent_hash}"
            )


def compute_deterministic_artifact_hash(envelope: Dict[str, Any]) -> str:
    """
    Deterministic SHA-256 calculation for offline/local audit verification.
    """
    canonical_json = json.dumps(envelope, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()


def fetch_latest_hash(base_url: str = BUCKET_BASE_URL_DEFAULT, timeout: float = 2.0) -> Tuple[Optional[str], int]:
    """
    Step 1: Fetch current parent hash from Bucket via GET /bucket/latest-hash.
    Returns (last_hash, artifact_count).
    """
    url = f"{base_url.rstrip('/')}/bucket/latest-hash"
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("last_hash"), int(data.get("artifact_count", 0))
    except Exception as e:
        # Return offline fallback indicators
        return None, 0


def build_bucket_envelope(
    trace_id: str,
    input_payload: Dict[str, Any],
    output_payload: Dict[str, Any],
    parent_hash: Optional[str] = None,
    artifact_id: Optional[str] = None,
    endpoint: str = "POST /api/nagarpranali/enrich",
) -> Dict[str, Any]:
    """
    Step 2: Build the Required Bucket Envelope Template.
    Guarantees strict compliance with the 6 mandatory fields + parent_hash + payload.
    """
    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    envelope = {
        "artifact_id": artifact_id or str(uuid.uuid4()),
        "trace_id": trace_id,
        "timestamp_utc": now_utc,
        "schema_version": "1.0.0",
        "source_module_id": "vana.nagarpranali",
        "artifact_type": "nagarpranali_enrichment",
        "parent_hash": parent_hash,
        "payload": {
            "endpoint": endpoint,
            "input": input_payload,
            "output": output_payload,
        },
    }
    return envelope


def submit_artifact_to_bucket(
    envelope: Dict[str, Any],
    base_url: str = BUCKET_BASE_URL_DEFAULT,
    timeout: float = 2.0,
    auth_token: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Step 3: Submit envelope to POST /bucket/artifact.
    """
    url = f"{base_url.rstrip('/')}/bucket/artifact"
    payload_bytes = json.dumps(envelope).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    if auth_token:
        headers["Authorization"] = f"Bearer {auth_token}"

    req = urllib.request.Request(url, data=payload_bytes, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8")
        raise RuntimeError(f"Bucket rejected artifact HTTP {e.code}: {err_body}") from e
    except Exception as e:
        # Offline or unreachable
        return {
            "status": "OFFLINE_RECORDED",
            "message": f"Bucket endpoint {url} unreachable. Envelope preserved with local deterministic hash.",
            "envelope": envelope,
            "local_hash": compute_deterministic_artifact_hash(envelope),
        }
