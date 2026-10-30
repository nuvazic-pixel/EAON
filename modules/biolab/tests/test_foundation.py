import json
from pathlib import Path

import pytest
from eaon_biolab.config import CONFIG_PATH, load_config
from eaon_biolab.ingestion import SyntheticBioIngestion
from eaon_biolab.provenance import build_audit
from eaon_biolab.validation import BioDataValidator


def test_config_load():
    config = load_config()
    assert config["sampling_frequency_seconds"] == 60
    assert config["validation_rules"]["min_value"] == 30


def test_config_rejects_duplicate(tmp_path):
    file = tmp_path / "bad.yaml"
    file.write_text(CONFIG_PATH.read_text() + "\nexpected_unit: \"bpm\"\n")
    with pytest.raises(ValueError):
        load_config(file)


def test_config_drives_batch():
    config = load_config()
    batch = SyntheticBioIngestion().generate_batch(
        3, sampling_frequency_seconds=config["sampling_frequency_seconds"],
        metric=config["target_metric"], unit=config["expected_unit"])
    assert all(not BioDataValidator(config).validate_observation(x) for x in batch)
    assert batch[1]["timestamp"] == "2026-01-01T10:01:00Z"


def test_provenance_stable():
    batch = SyntheticBioIngestion().generate_batch(5)
    a = build_audit(CONFIG_PATH, batch, 0)
    assert a == build_audit(CONFIG_PATH, batch, 0)
    assert len(a["batch_sha256"]) == 64
    assert a["batch_sha256"] != build_audit(CONFIG_PATH, batch[:-1], 0)["batch_sha256"]
