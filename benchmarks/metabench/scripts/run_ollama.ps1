param(
    [string]$Model = "qwen3:8b",
    [int]$Cases = 40,
    [int]$Seed = 20260713,
    [int]$Timeout = 180
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path ".venv")) {
    python -m venv .venv
}

& .\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"

eaon-bench run `
    --provider ollama `
    --model $Model `
    --base-url "http://localhost:11434" `
    --cases $Cases `
    --seed $Seed `
    --timeout $Timeout
