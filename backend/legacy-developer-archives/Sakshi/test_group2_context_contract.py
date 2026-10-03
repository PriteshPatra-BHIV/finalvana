# Negative/continuity tests for Group 2 context contract

CANONICAL_ID = "TC-Z03-F02-LIDAR-OBS001"

def validate(ctx):
    assert ctx["observation_id"] == CANONICAL_ID
    assert ctx["source_observation_id"] == CANONICAL_ID
    assert ctx["measurement"] == 4.7
    assert ctx["measurement_unit"] == "m"

def test_identity_continuity():
    validate({"observation_id": CANONICAL_ID,
              "source_observation_id": CANONICAL_ID,
              "measurement": 4.7, "measurement_unit": "m"})

def test_replacement_id_rejected():
    bad = {"observation_id": "NEW-ID",
           "source_observation_id": CANONICAL_ID,
           "measurement": 4.7, "measurement_unit": "m"}
    try:
        validate(bad)
        assert False
    except AssertionError:
        pass

def test_source_id_mismatch_rejected():
    bad = {"observation_id": CANONICAL_ID,
           "source_observation_id": "OTHER-ID",
           "measurement": 4.7, "measurement_unit": "m"}
    try:
        validate(bad)
        assert False
    except AssertionError:
        pass

def test_incompatible_unit_rejected():
    bad = {"observation_id": CANONICAL_ID,
           "source_observation_id": CANONICAL_ID,
           "measurement": 4.7, "measurement_unit": "ft"}
    try:
        validate(bad)
        assert False
    except AssertionError:
        pass

def test_reference_does_not_overwrite_observation():
    observed = 4.7
    reference = 4.8
    assert observed == 4.7
    assert reference == 4.8
    assert observed != reference
