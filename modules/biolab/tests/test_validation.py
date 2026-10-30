import pytest
from eaon_biolab.ingestion import SyntheticBioIngestion
from eaon_biolab.validation import BioDataValidator

CONFIG = {"target_metric": "heart_rate", "expected_unit": "bpm",
          "validation_rules": {"min_value": 30, "max_value": 220}}


@pytest.fixture
def observation():
    return SyntheticBioIngestion().generate_batch(1)[0]


@pytest.fixture
def validator():
    return BioDataValidator(CONFIG)


def test_valid(validator, observation):
    assert validator.validate_observation(observation) == []


def test_bio_001_missing_fields(validator, observation):
    del observation["subject_id"]
    assert "Missing required field: subject_id" in validator.validate_observation(observation)


@pytest.mark.parametrize("timestamp", ["broken", "2026-01-01T10:00:00", 123, "2026-13-01T10:00:00Z"])
def test_bio_002_timestamp(validator, observation, timestamp):
    observation["timestamp"] = timestamp
    assert "Invalid ISO timestamp format" in validator.validate_observation(observation)


@pytest.mark.parametrize("unit", ["m/s", "Hz", ""])
def test_bio_003_unit(validator, observation, unit):
    observation["unit"] = unit
    assert any("Incompatible unit" in e for e in validator.validate_observation(observation))


@pytest.mark.parametrize("value", [True, float("nan"), float("inf"), 221, 29, "72"])
def test_invalid_values(validator, observation, value):
    observation["value"] = value
    assert any("invalid type" in e for e in validator.validate_observation(observation))


def test_wrong_metric(validator, observation):
    observation["metric"] = "temperature"
    assert any("Incompatible metric" in e for e in validator.validate_observation(observation))


def test_deterministic():
    ingestion = SyntheticBioIngestion()
    assert ingestion.generate_batch(20) == ingestion.generate_batch(20)
