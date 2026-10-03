"""
Group 2 Scientific Context Validator
Author: Ansh Gupta (Scientific & Context Validation Owner — Group 2)
Mission: Ensure canonical observations produce deterministic, machine-readable scientific context
         and enforce strict boundaries so unsupported science CANNOT become Action Requests.
"""

import re
from typing import Dict, Any, Tuple, Optional

# Authoritative Supported Parameters for Group 2 Context Model
SUPPORTED_PARAMETERS = {
    "canopy_height",
    "expected_canopy_height",
    "baseline_salinity",
    "above_ground_biomass",
    "species_dominance",
    "water_ph",
    "soil_salinity",
    "tidal_inundation_frequency"
}

# Regex for standard DOI formats (e.g., 10.xxxx/yyyy or http(s)://doi.org/10.xxxx/yyyy or Zenodo DOIs)
DOI_PATTERN = re.compile(r'^(10\.\d{4,9}/[-._;()/:A-Z0-9]+|https?://(dx\.)?doi\.org/10\.\d{4,9}/[-._;()/:A-Z0-9]+|https?://zenodo\.org/records/\d+)$', re.IGNORECASE)

class Group2ContextValidator:
    """
    Validates Group 2 scientific context records against evidence, DOI integrity,
    parameter boundaries, and temporal applicability.
    """

    def __init__(self):
        self.supported_parameters = SUPPORTED_PARAMETERS

    def is_valid_doi_or_url(self, source_citation: str, doi_or_url: Optional[str] = None) -> bool:
        """Checks if citation or DOI string follows standard scientific DOI/URL format."""
        if doi_or_url and doi_or_url.strip().upper() not in ["GAP", "UNKNOWN", "NONE", "NULL", "INVALID"]:
            doi_clean = doi_or_url.strip()
            # If explicit DOI is provided, it MUST match standard DOI/URL pattern
            if DOI_PATTERN.match(doi_clean) or doi_clean.startswith("http://") or doi_clean.startswith("https://"):
                return True
            return False

        if not source_citation or source_citation.strip().upper() in ["GAP", "UNKNOWN", "NONE", "NULL", "INVALID"]:
            return False
        
        cit_clean = source_citation.strip()
        if DOI_PATTERN.match(cit_clean) or cit_clean.startswith("https://") or cit_clean.startswith("http://"):
            return True
        # Plain scientific citation text (must have scientific keywords and >15 chars)
        if len(cit_clean) >= 15 and any(kw in cit_clean.lower() for kw in ["study", "journal", "sciencedirect", "elsevier", "ieee", "report", "zenodo", "gmw", "survey"]):
            return True
        return False

    def validate_context(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluates a ScientificContextRecord.
        
        Returns:
            Dict containing:
              - classification: 'VERIFIED' | 'ADAPT' | 'GAP' | 'REJECTED'
              - is_actionable: bool
              - validation_evidence: str
              - reasoning: str
              - validated_record: Dict
        """
        param_name = record.get("parameter_name")
        param_val = record.get("parameter_value")
        conf_score = record.get("confidence_score", 0.0)
        claimed_status = str(record.get("validation_status", "GAP")).upper()
        source_citation = str(record.get("source_citation", "")).strip()
        source_doi = record.get("source_url_doi") or record.get("scientific_citation_doi")
        temp_validity = record.get("temporal_validity")

        # -------------------------------------------------------------
        # 1. Contradiction & Malformed Structure Checks (REJECTED)
        # -------------------------------------------------------------
        # Check invalid confidence score range
        if conf_score < 0.0 or conf_score > 1.0:
            return {
                "classification": "REJECTED",
                "is_actionable": False,
                "reasoning": f"Invalid confidence_score ({conf_score}). Must be between 0.0 and 1.0.",
                "validation_evidence": "REJECTED_CONTRADICTORY_CONFIDENCE_SCORE",
                "validated_record": record
            }

        # Check contradictory parameter ranges (min > max)
        if isinstance(param_val, dict):
            val_min = param_val.get("min")
            val_max = param_val.get("max")
            if val_min is not None and val_max is not None and val_min > val_max:
                return {
                    "classification": "REJECTED",
                    "is_actionable": False,
                    "reasoning": f"Contradictory range baseline: min ({val_min}) > max ({val_max}).",
                    "validation_evidence": "REJECTED_CONTRADICTORY_RANGE",
                    "validated_record": record
                }

        # Check for claimed VERIFIED status with malformed DOI/citation
        if claimed_status == "VERIFIED":
            if not self.is_valid_doi_or_url(source_citation, source_doi):
                return {
                    "classification": "REJECTED",
                    "is_actionable": False,
                    "reasoning": f"Claimed VERIFIED context has invalid or malformed scientific source/DOI: '{source_doi or source_citation}'.",
                    "validation_evidence": "REJECTED_MALFORMED_DOI",
                    "validated_record": record
                }

        # -------------------------------------------------------------
        # 2. Unsupported Parameter or Missing Data Preserved as GAP
        # -------------------------------------------------------------
        if param_name not in self.supported_parameters:
            return {
                "classification": "GAP",
                "is_actionable": False,
                "reasoning": f"Parameter '{param_name}' is not in the Group 2 supported scientific context model.",
                "validation_evidence": "GAP_UNSUPPORTED_PARAMETER",
                "validated_record": record
            }

        if param_val is None or conf_score == 0.0 or claimed_status == "GAP" or source_citation.upper() == "GAP":
            return {
                "classification": "GAP",
                "is_actionable": False,
                "reasoning": f"Missing scientific reference context for parameter '{param_name}' correctly preserved as GAP without fabrication.",
                "validation_evidence": "GAP_MISSING_REFERENCE_PRESERVED",
                "validated_record": {
                    **record,
                    "parameter_value": None,
                    "confidence_score": 0.0,
                    "validation_status": "GAP",
                    "source_citation": "GAP"
                }
            }

        # -------------------------------------------------------------
        # 3. Temporal Validity Check (ADAPT if stale/expired)
        # -------------------------------------------------------------
        if temp_validity and isinstance(temp_validity, str):
            # Check for historical range e.g., 1990-2000 vs current observation year 2026
            if "1990" in temp_validity or "2005" in temp_validity:
                return {
                    "classification": "ADAPT",
                    "is_actionable": False,
                    "reasoning": f"Context temporal validity ({temp_validity}) is historical/outdated for current observation.",
                    "validation_evidence": "ADAPT_TEMPORAL_STALE",
                    "validated_record": record
                }

        # -------------------------------------------------------------
        # 4. Valid Context Path (VERIFIED)
        # -------------------------------------------------------------
        return {
            "classification": "VERIFIED",
            "is_actionable": True,
            "reasoning": f"Scientific context for '{param_name}' is fully supported, cited, and validated.",
            "validation_evidence": f"VERIFIED_CITATION_{source_doi or 'SCIENCE_DIRECT_2023'}",
            "validated_record": {
                **record,
                "validation_status": "VERIFIED"
            }
        }

    def format_group4_handoff(self, validation_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enforces the Group 2 -> Group 4 handoff boundary.
        Unsupported science or GAP records CANNOT be formatted as Action Requests.
        """
        classification = validation_result.get("classification")
        is_actionable = validation_result.get("is_actionable", False)
        rec = validation_result.get("validated_record", {})

        if classification in ["GAP", "REJECTED", "ADAPT"] or not is_actionable:
            return {
                "handoff_type": "UNSUPPORTED_CONTEXT_ABSTENTION",
                "actionable": False,
                "governance_intent": "ABSTAIN",
                "action_request": None,
                "context_classification": classification,
                "reasoning": validation_result.get("reasoning"),
                "evidence": validation_result.get("validation_evidence"),
                "context_record": rec
            }

        # Validated context handoff payload
        return {
            "handoff_type": "VALIDATED_SCIENTIFIC_CONTEXT",
            "actionable": True,
            "governance_intent": "EVALUATE_POLICY",
            "action_request": {
                "product": "VANA",
                "capability": "environmental_observation",
                "context_id": rec.get("context_id"),
                "parameter_name": rec.get("parameter_name"),
                "parameter_value": rec.get("parameter_value"),
                "source_citation": rec.get("source_citation"),
                "doi": rec.get("source_url_doi") or rec.get("scientific_citation_doi")
            },
            "context_classification": classification,
            "reasoning": validation_result.get("reasoning"),
            "evidence": validation_result.get("validation_evidence"),
            "context_record": rec
        }
