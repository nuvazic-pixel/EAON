"""M1 deterministic engine regression tests."""
from copy import deepcopy

from eaon_biolab.config import load_config
from eaon_biolab.experiment import run_experiment
from eaon_biolab.ingestion import SyntheticBioIngestion
from eaon_biolab.provenance import canonical_bytes, sha256


def batch(count=10):
    return SyntheticBioIngestion().generate_batch(count)


def test_reproducible_report():
    config = load_config()
    first = run_experiment(config, batch())
    assert first == run_experiment(config, batch())
    assert first["report_sha256"] == sha256(canonical_bytes({
        key: value for key, value in first.items() if key != "report_sha256"
    }))
    assert first["accepted"] == 10
    assert first["rejected"] == 0


def test_outlier_detection():
    records = batch(10)
    for item in records:
        item["value"] = 70.0
    records[-1]["value"] = 150.0
    result = run_experiment(load_config(), records)
    assert len(result["anomalies"]) == 1
    assert result["anomalies"][0]["observation_id"] == records[-1]["observation_id"]


def test_reject_invalid_without_polluting_statistics():
    records = batch(3)
    bad = deepcopy(records[0])
    bad["observation_id"] = "invalid"
    bad["value"] = 999
    result = run_experiment(load_config(), records + [bad])
    assert result["total"] == 4
    assert result["accepted"] == 3
    assert result["rejected"] == 1
    assert result["statistics"]["max"] < 999


def test_empty_batch_and_constant_values():
    empty = run_experiment(load_config(), [])
    assert empty["statistics"]["mean"] is None
    assert empty["anomalies"] == []
    records = batch(5)
    for item in records:
        item["value"] = 70
    assert run_experiment(load_config(), records)["anomalies"] == []


def test_input_mutation_changes_hash():
    records = batch()
    before = run_experiment(load_config(), records)
    records[0]["value"] = 80
    after = run_experiment(load_config(), records)
    assert before["input_sha256"] != after["input_sha256"]
    assert before["report_sha256"] != after["report_sha256"]
