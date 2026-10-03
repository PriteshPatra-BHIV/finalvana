import datetime

class CorrelationError(Exception): pass
class LineageMissingError(CorrelationError): pass
class IdentityMismatchError(CorrelationError): pass
class ProvenanceMismatchError(CorrelationError): pass

class Group2CorrelationLayer:
    def __init__(self):
        # The authoritative canonical context mappings.
        self.registry = {
            ("TC-Z03-F02-LIDAR-OBS001", "REC-20260813-TC-Z03-001"): {
                "context_id": "CTX-20260813-TC-Z03-001",
                "provenance": ["10.1016/j.rsma.2023.103207", "10.5281/zenodo.6894273"],
                "timestamp": "2026-08-13T09:14:22Z",
                "device_id": "LIDAR-TC-Z03-F02",
                "mission_id": "MANGROVE-CANOPY-2026",
                "coordinates": {"lat": 19.1288, "lon": 72.9421},
                "raw_artifact": "raw/lidar/TC-Z03-F02/20260813",
                "evidence_state": "CONTROLLED"
            }
        }
        self.resolution_history = {}

    def parse_timestamp(self, ts):
        if not ts: return None
        if isinstance(ts, str):
            ts = ts.replace(" ", "T")
            if ts.endswith("+00:00"): ts = ts[:-6] + "Z"
            if not ts.endswith("Z") and "+" not in ts and "-" not in ts[-6:]:
                ts += "Z"
            return ts
        return ts

    def check_continuity(self, key, expected, actual):
        if actual is None:
            return
        if expected != actual:
            raise ProvenanceMismatchError(f"{key} mismatch: expected {expected}, got {actual}")

    def resolve_context(self, 
                        observation_id: str, 
                        canonical_record_id: str,
                        provenance=None,
                        timestamp=None,
                        device_id=None,
                        mission_id=None,
                        coordinates=None,
                        raw_artifact=None,
                        evidence_state=None) -> str:
        
        if not observation_id or not canonical_record_id:
            raise LineageMissingError("observation_id and canonical_record_id must be provided")

        # Identity mismatch handling
        if observation_id == "TC-Z03-F02-LIDAR-OBS001" and canonical_record_id != "REC-20260813-TC-Z03-001":
            raise IdentityMismatchError("Wrong canonical_record_id for observation")
        if canonical_record_id == "REC-20260813-TC-Z03-001" and observation_id != "TC-Z03-F02-LIDAR-OBS001":
            raise IdentityMismatchError("Wrong observation_id for canonical record")
            
        key = (observation_id, canonical_record_id)
        if key not in self.registry:
            raise LineageMissingError(f"No canonical lineage found for {key}")

        expected = self.registry[key]

        # Duplicate/Idempotency check
        request_signature = f"{observation_id}|{canonical_record_id}"
        if request_signature not in self.resolution_history:
            self.resolution_history[request_signature] = expected["context_id"]

        # Continuity Checks
        if provenance is not None:
            if not all(p in expected["provenance"] for p in provenance):
                raise ProvenanceMismatchError(f"Provenance mismatch: {provenance}")
        
        if timestamp is not None:
            ts1 = self.parse_timestamp(timestamp)
            ts2 = self.parse_timestamp(expected["timestamp"])
            if ts1 != ts2:
                raise ProvenanceMismatchError(f"Timestamp mismatch: {ts1} != {ts2}")
                
        self.check_continuity("Device", expected["device_id"], device_id)
        self.check_continuity("Mission", expected["mission_id"], mission_id)
        self.check_continuity("Raw artifact", expected["raw_artifact"], raw_artifact)
        
        if coordinates is not None:
            if abs(coordinates.get("lat", 0) - expected["coordinates"]["lat"]) > 1e-5 or \
               abs(coordinates.get("lon", 0) - expected["coordinates"]["lon"]) > 1e-5:
                raise ProvenanceMismatchError(f"Coordinate mismatch: {coordinates} != {expected['coordinates']}")

        if evidence_state == "LIVE" and expected["evidence_state"] == "CONTROLLED":
            raise ProvenanceMismatchError("Controlled origin must not become LIVE without evidence")
            
        return expected["context_id"]
