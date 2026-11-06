"""Command-line entry point."""

import argparse
from dataclasses import fields
from pathlib import Path

from .experiment import run_experiment
from .report import write_report
from .simulation import Config


def main(argv=None):
    parser = argparse.ArgumentParser(description="EAON experiment 4: hidden common cause (offline simulation)")
    for field in fields(Config):
        parser.add_argument("--" + field.name.replace("_", "-"), type=field.type, default=field.default)
    parser.add_argument("--output", type=Path, default=Path("runs/experiment-4"))
    parser.add_argument("--plots", action="store_true")
    args = parser.parse_args(argv)
    try:
        config = Config(**{field.name: getattr(args, field.name) for field in fields(Config)})
        write_report(run_experiment(config), args.output, plots=args.plots)
    except (ValueError, OSError) as exc:
        parser.error(str(exc))
    print(f"Reports: {args.output / 'report.md'} ; {args.output / 'report.json'}")
    return 0
