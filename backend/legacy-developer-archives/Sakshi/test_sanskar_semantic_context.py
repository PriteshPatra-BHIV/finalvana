import copy

OBS_ID = "TC-Z03-F02-LIDAR-OBS001"

OBSERVATION = {
    "observation_id": OBS_ID,
    "parameter": "canopy_height",
    "value": 4.7,
    "unit": "m",
    "timestamp": "2026-08-13T09:14:22Z",
    "location": {"lat": 19.1288, "lon": 72.9421},
    "geo_id": "GEO-TC-Z03",
}

PROVENANCE = {
    "source_id": "SRC-SCI-THANE-CREEK-2023",
    "citation": (
        "Standing carbon stock of Thane Creek mangrove ecosystem: "
        "An integrated approach using allometry and remote sensing techniques (2023)"
    ),
    "verification_status": "VERIFIED",
    "confidence": 0.85,
    "quality": "VALIDATED",
    "uncertainty": None,
}

SCIENTIFIC_CONTEXT = {
    "context_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
    "parameter_name": "expected_canopy_height",
    "parameter_value": {"value": 4.8, "range": [3.5, 6.5], "unit": "m"},
    "validation_status": "VERIFIED",
    "confidence_score": 0.85,
    "source_doi": "10.1016/j.rsma.2023.103207",
}


def semantic_contextualize(observation, provenance, context):
    # Reference implementation of the semantic acceptance contract.
    return {
        "observation": copy.deepcopy(observation),
        "provenance": copy.deepcopy(provenance),
        "scientific_context": copy.deepcopy(context),
        "contextual_result": {
            "parameter_evaluated": "canopy_height",
            "reference_value": context["parameter_value"]["value"],
            "deviation": None,
            "anomaly_detected": None,
            "assessment": None,
        },
        "trace": {"trace_id": None},
    }


def test_observation_id_preserved():
    result = semantic_contextualize(OBSERVATION, PROVENANCE, SCIENTIFIC_CONTEXT)
    assert result["observation"]["observation_id"] == OBS_ID


def test_location_preserved():
    result = semantic_contextualize(OBSERVATION, PROVENANCE, SCIENTIFIC_CONTEXT)
    assert result["observation"]["location"] == {"lat": 19.1288, "lon": 72.9421}


def test_timestamp_preserved():
    result = semantic_contextualize(OBSERVATION, PROVENANCE, SCIENTIFIC_CONTEXT)
    assert result["observation"]["timestamp"] == "2026-08-13T09:14:22Z"


def test_measurement_parameter_and_unit_preserved():
    result = semantic_contextualize(OBSERVATION, PROVENANCE, SCIENTIFIC_CONTEXT)
    assert result["observation"]["parameter"] == "canopy_height"
    assert result["observation"]["value"] == 4.7
    assert result["observation"]["unit"] == "m"


def test_geo_id_preserved():
    result = semantic_contextualize(OBSERVATION, PROVENANCE, SCIENTIFIC_CONTEXT)
    assert result["observation"]["geo_id"] == "GEO-TC-Z03"


def test_provenance_preserved():
    result = semantic_contextualize(OBSERVATION, PROVENANCE, SCIENTIFIC_CONTEXT)
    assert result["provenance"]["source_id"] == PROVENANCE["source_id"]
    assert result["provenance"]["citation"] == PROVENANCE["citation"]
    assert result["provenance"]["verification_status"] == "VERIFIED"


def test_confidence_quality_uncertainty_are_separate():
    result = semantic_contextualize(OBSERVATION, PROVENANCE, SCIENTIFIC_CONTEXT)
    assert result["provenance"]["confidence"] == 0.85
    assert result["provenance"]["quality"] == "VALIDATED"
    assert result["provenance"]["uncertainty"] is None


def test_verified_context_is_consumed_without_mutating_observation():
    original = copy.deepcopy(OBSERVATION)
    result = semantic_contextualize(OBSERVATION, PROVENANCE, SCIENTIFIC_CONTEXT)
    assert OBSERVATION == original
    assert result["observation"]["value"] == 4.7
    assert result["contextual_result"]["reference_value"] == 4.8


def test_dual_traceability():
    result = semantic_contextualize(OBSERVATION, PROVENANCE, SCIENTIFIC_CONTEXT)
    assert result["observation"]["observation_id"] == OBS_ID
    assert result["provenance"]["source_id"] == PROVENANCE["source_id"]
    assert result["provenance"]["citation"]


def test_reference_does_not_replace_observation():
    result = semantic_contextualize(OBSERVATION, PROVENANCE, SCIENTIFIC_CONTEXT)
    assert result["observation"]["value"] == 4.7
    assert result["contextual_result"]["reference_value"] == 4.8
    assert result["observation"]["value"] != result["contextual_result"]["reference_value"]
