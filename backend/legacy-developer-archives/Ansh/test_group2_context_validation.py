"""
Test Suite for Group 2 Scientific Context Validator
Validates positive, negative, GAP, malformed DOI, contradictory, and Group 4 handoff boundaries.
"""

import unittest
from group2_context_validator import Group2ContextValidator

class TestGroup2ContextValidation(unittest.TestCase):

    def setUp(self):
        self.validator = Group2ContextValidator()

    def test_valid_context_accepted(self):
        """Valid context record with proper scientific citation returns VERIFIED and is_actionable=True."""
        record = {
            "context_id": "ctx-tc-001",
            "parameter_name": "expected_canopy_height",
            "parameter_value": {"min": 3.5, "max": 6.5, "mean": 4.8},
            "unit": "m",
            "temporal_validity": "2020-2026",
            "source_citation": "Standing carbon stock of Thane Creek mangrove ecosystem, ScienceDirect, 2023",
            "scientific_citation_doi": "10.1016/j.rsma.2023.103207",
            "spatial_reference_doi": "10.5281/zenodo.6894273",
            "confidence_score": 0.85,
            "validation_status": "VERIFIED"
        }
        res = self.validator.validate_context(record)
        self.assertEqual(res["classification"], "VERIFIED")
        self.assertTrue(res["is_actionable"])
        
        handoff = self.validator.format_group4_handoff(res)
        self.assertEqual(handoff["handoff_type"], "VALIDATED_SCIENTIFIC_CONTEXT")
        self.assertTrue(handoff["actionable"])
        self.assertIsNotNone(handoff["action_request"])
        self.assertEqual(handoff["action_request"]["product"], "VANA")

    def test_unsupported_parameter_returns_gap(self):
        """Unsupported parameter returns GAP and is_actionable=False."""
        record = {
            "context_id": "ctx-tc-002",
            "parameter_name": "martian_soil_pressure",
            "parameter_value": 101.3,
            "confidence_score": 0.9,
            "validation_status": "VERIFIED",
            "source_citation": "NASA Study 2024"
        }
        res = self.validator.validate_context(record)
        self.assertEqual(res["classification"], "GAP")
        self.assertFalse(res["is_actionable"])
        self.assertEqual(res["validation_evidence"], "GAP_UNSUPPORTED_PARAMETER")

        handoff = self.validator.format_group4_handoff(res)
        self.assertEqual(handoff["handoff_type"], "UNSUPPORTED_CONTEXT_ABSTENTION")
        self.assertFalse(handoff["actionable"])
        self.assertIsNone(handoff["action_request"])

    def test_null_reference_value_returns_gap(self):
        """Null reference value / zero confidence returns GAP without fabrication."""
        record = {
            "context_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
            "parameter_name": "canopy_height",
            "parameter_value": None,
            "confidence_score": 0.0,
            "validation_status": "GAP",
            "source_citation": "GAP"
        }
        res = self.validator.validate_context(record)
        self.assertEqual(res["classification"], "GAP")
        self.assertFalse(res["is_actionable"])
        self.assertEqual(res["validated_record"]["parameter_value"], None)
        self.assertEqual(res["validated_record"]["validation_status"], "GAP")

        handoff = self.validator.format_group4_handoff(res)
        self.assertEqual(handoff["handoff_type"], "UNSUPPORTED_CONTEXT_ABSTENTION")
        self.assertFalse(handoff["actionable"])
        self.assertIsNone(handoff["action_request"])

    def test_invalid_malformed_doi_rejected(self):
        """Claimed VERIFIED record with malformed DOI/citation returns REJECTED."""
        record = {
            "context_id": "ctx-tc-004",
            "parameter_name": "canopy_height",
            "parameter_value": 5.0,
            "confidence_score": 0.8,
            "validation_status": "VERIFIED",
            "source_citation": "invalid_citation_string",
            "scientific_citation_doi": "invalid-doi-123"
        }
        res = self.validator.validate_context(record)
        self.assertEqual(res["classification"], "REJECTED")
        self.assertFalse(res["is_actionable"])
        self.assertEqual(res["validation_evidence"], "REJECTED_MALFORMED_DOI")

    def test_contradictory_range_rejected(self):
        """Record with min > max range baseline returns REJECTED."""
        record = {
            "context_id": "ctx-tc-005",
            "parameter_name": "canopy_height",
            "parameter_value": {"min": 6.5, "max": 3.5},
            "confidence_score": 0.8,
            "validation_status": "VERIFIED",
            "source_citation": "ScienceDirect Elsevier 2023 Study"
        }
        res = self.validator.validate_context(record)
        self.assertEqual(res["classification"], "REJECTED")
        self.assertFalse(res["is_actionable"])
        self.assertEqual(res["validation_evidence"], "REJECTED_CONTRADICTORY_RANGE")

    def test_stale_temporal_context_adapted(self):
        """Historical context outside current validity returns ADAPT."""
        record = {
            "context_id": "ctx-tc-006",
            "parameter_name": "canopy_height",
            "parameter_value": 4.5,
            "confidence_score": 0.8,
            "temporal_validity": "1990-1995",
            "validation_status": "VERIFIED",
            "source_citation": "Historical Mangrove Survey 1995"
        }
        res = self.validator.validate_context(record)
        self.assertEqual(res["classification"], "ADAPT")
        self.assertFalse(res["is_actionable"])

    def test_gap_cannot_become_action_request_boundary(self):
        """Strict acceptance check: GAP context CANNOT become an Action Request for Group 4."""
        record = {
            "context_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
            "parameter_name": "canopy_height",
            "parameter_value": None,
            "confidence_score": 0.0,
            "validation_status": "GAP",
            "source_citation": "GAP"
        }
        res = self.validator.validate_context(record)
        handoff = self.validator.format_group4_handoff(res)

        # Boundary Assertions
        self.assertNotEqual(handoff["handoff_type"], "ACTION_REQUEST")
        self.assertEqual(handoff["handoff_type"], "UNSUPPORTED_CONTEXT_ABSTENTION")
        self.assertFalse(handoff["actionable"])
        self.assertEqual(handoff["governance_intent"], "ABSTAIN")
        self.assertIsNone(handoff["action_request"])

if __name__ == "__main__":
    unittest.main()
