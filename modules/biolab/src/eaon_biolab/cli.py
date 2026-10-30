"""EAON launcher-compatible offline BioLab CLI."""
import argparse
import json
from .config import CONFIG_PATH, load_config
from .ingestion import SyntheticBioIngestion
from .provenance import build_audit
from .validation import BioDataValidator


def main() -> int:
    parser = argparse.ArgumentParser(description="EAON BioLab M0")
    parser.add_argument("command", choices=["smoke"])
    parser.add_argument("--count", type=int, default=100)
    parser.add_argument("--config", default=str(CONFIG_PATH))
    args = parser.parse_args()
    config = load_config(args.config)
    observations = SyntheticBioIngestion().generate_batch(
        args.count,
        sampling_frequency_seconds=config["sampling_frequency_seconds"],
        metric=config["target_metric"],
        unit=config["expected_unit"],
    )
    validator = BioDataValidator(config)
    errors = [validator.validate_observation(item) for item in observations]
    audit = build_audit(args.config, observations, sum(bool(item) for item in errors))
    audit["experiment_id"] = config["experiment_id"]
    print(json.dumps(audit, sort_keys=True))
    return int(any(errors))


if __name__ == "__main__":
    raise SystemExit(main())
