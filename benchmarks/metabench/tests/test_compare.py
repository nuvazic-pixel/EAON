import json
from pathlib import Path

from eaon_metabench.compare import load_report


def test_load_report(tmp_path: Path) -> None:
    report = {
        "metadata": {"model": "x"},
        "summary": {
            "overall_score": 1.0,
            "accuracy": 1.0,
            "calibration_score": 1.0,
            "abstention_f1": 1.0,
            "recovery_adaptation_score": 1.0,
            "parse_rate": 1.0,
            "median_latency_ms": 1.0,
        },
    }
    path = tmp_path / "report.json"
    path.write_text(json.dumps(report), encoding="utf-8")
    assert load_report(path)["metadata"]["model"] == "x"
