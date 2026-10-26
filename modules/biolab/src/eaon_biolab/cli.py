"""EAON launcher-compatible offline BioLab CLI."""
import argparse
import json
from .ingestion import SyntheticBioIngestion
from .validation import BioDataValidator

DEFAULT_CONFIG = {
    "target_metric": "heart_rate", "expected_unit": "bpm",
    "validation_rules": {"min_value": 30, "max_value": 220},
}


def main() -> int:
    parser = argparse.ArgumentParser(description="EAON BioLab M0")
    parser.add_argument("command", choices=["smoke"])
    parser.add_argument("--count", type=int, default=100)
    args = parser.parse_args()
    observations = SyntheticBioIngestion().generate_batch(args.count)
    validator = BioDataValidator(DEFAULT_CONFIG)
    errors = [validator.validate_observation(item) for item in observations]
    print(json.dumps({"experiment_id": "EXP-BIO-001", "count": len(observations),
                      "rejected": sum(bool(item) for item in errors)}, sort_keys=True))
    return int(any(errors))


if __name__ == "__main__":
    raise SystemExit(main())
