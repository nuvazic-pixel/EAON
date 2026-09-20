#!/usr/bin/env bash
set -euo pipefail

MODEL="${1:-qwen3:8b}"
CASES="${2:-40}"
SEED="${3:-20260713}"

python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
eaon-bench run --provider ollama --model "$MODEL" --cases "$CASES" --seed "$SEED"
