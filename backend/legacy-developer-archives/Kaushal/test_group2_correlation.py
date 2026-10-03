import unittest
from group2_correlation import (
    Group2CorrelationLayer, 
    LineageMissingError, 
    IdentityMismatchError, 
    ProvenanceMismatchError
)

class TestGroup2CorrelationLayer(unittest.TestCase):
    def setUp(self):
        self.layer = Group2CorrelationLayer()

    def test_1_exact_lineage(self):
        ctx = self.layer.resolve_context("TC-Z03-F02-LIDAR-OBS001", "REC-20260813-TC-Z03-001")
        self.assertEqual(ctx, "CTX-20260813-TC-Z03-001")
        
    def test_2_missing_group1_record(self):
        with self.assertRaises(LineageMissingError):
            self.layer.resolve_context("UNKNOWN-OBS", "UNKNOWN-REC")
            
    def test_3_wrong_observation(self):
        with self.assertRaises(IdentityMismatchError):
            self.layer.resolve_context("WRONG-OBS-001", "REC-20260813-TC-Z03-001")

    def test_4_wrong_canonical_record_id(self):
        with self.assertRaises(IdentityMismatchError):
            self.layer.resolve_context("TC-Z03-F02-LIDAR-OBS001", "REC-WRONG-001")

    def test_5_duplicate_identical_request(self):
        ctx1 = self.layer.resolve_context("TC-Z03-F02-LIDAR-OBS001", "REC-20260813-TC-Z03-001")
        ctx2 = self.layer.resolve_context("TC-Z03-F02-LIDAR-OBS001", "REC-20260813-TC-Z03-001")
        self.assertEqual(ctx1, ctx2)

    def test_6_provenance_mismatch(self):
        with self.assertRaises(ProvenanceMismatchError):
            self.layer.resolve_context("TC-Z03-F02-LIDAR-OBS001", "REC-20260813-TC-Z03-001", provenance=["WRONG_DOI"])

    def test_7_timestamp_mismatch(self):
        with self.assertRaises(ProvenanceMismatchError):
            self.layer.resolve_context("TC-Z03-F02-LIDAR-OBS001", "REC-20260813-TC-Z03-001", timestamp="1999-01-01T00:00:00Z")
            
    def test_8_device_mismatch(self):
        with self.assertRaises(ProvenanceMismatchError):
            self.layer.resolve_context("TC-Z03-F02-LIDAR-OBS001", "REC-20260813-TC-Z03-001", device_id="WRONG_DEVICE")

    def test_9_mission_mismatch(self):
        with self.assertRaises(ProvenanceMismatchError):
            self.layer.resolve_context("TC-Z03-F02-LIDAR-OBS001", "REC-20260813-TC-Z03-001", mission_id="WRONG_MISSION")

    def test_10_coordinate_mismatch(self):
        with self.assertRaises(ProvenanceMismatchError):
            self.layer.resolve_context("TC-Z03-F02-LIDAR-OBS001", "REC-20260813-TC-Z03-001", coordinates={"lat": 10.0, "lon": 10.0})

    def test_11_raw_artifact_mismatch(self):
        with self.assertRaises(ProvenanceMismatchError):
            self.layer.resolve_context("TC-Z03-F02-LIDAR-OBS001", "REC-20260813-TC-Z03-001", raw_artifact="WRONG_ARTIFACT")

    def test_12_controlled_origin(self):
        with self.assertRaises(ProvenanceMismatchError):
            self.layer.resolve_context("TC-Z03-F02-LIDAR-OBS001", "REC-20260813-TC-Z03-001", evidence_state="LIVE")
            
    def test_timestamp_semantic_equality(self):
        # 2026-08-13 09:14:22+00:00 vs 2026-08-13T09:14:22Z
        ctx = self.layer.resolve_context("TC-Z03-F02-LIDAR-OBS001", "REC-20260813-TC-Z03-001", timestamp="2026-08-13 09:14:22+00:00")
        self.assertEqual(ctx, "CTX-20260813-TC-Z03-001")

if __name__ == '__main__':
    unittest.main()
