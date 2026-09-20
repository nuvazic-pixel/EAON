# EAON MetaBench MVP

A local-first benchmark harness for measuring whether an AI system:

- knows when information is insufficient;
- detects contradictions;
- adapts when rules change;
- repairs an incorrect intermediate answer;
- reports confidence that matches actual correctness.

The first release targets **metacognition and recovery**. It is intentionally small, deterministic, auditable, and easy to connect to Ollama.

## 1. Install

```bash
cd eaon-metabench-mvp
python -m venv .venv
```

Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

Linux/macOS:

```bash
source .venv/bin/activate
pip install -e ".[dev]"
```

## 2. Verify with the built-in mock model

```bash
eaon-bench run --provider mock --model perfect-mock --cases 24 --seed 42
```

The command writes JSON and HTML reports into `results/`.

## 3. Run against Ollama

Start Ollama and ensure your model is available:

```bash
ollama list
```

Then run:

```bash
eaon-bench run \
  --provider ollama \
  --model qwen3:8b \
  --base-url http://localhost:11434 \
  --cases 40 \
  --seed 20260713
```

Windows PowerShell equivalent:

```powershell
eaon-bench run --provider ollama --model qwen3:8b --base-url http://localhost:11434 --cases 40 --seed 20260713
```

For the larger local model mentioned in the EAON setup:

```powershell
eaon-bench run --provider ollama --model qwen3-coder-next:q4_K_M --cases 40 --seed 20260713 --timeout 300
```

## 4. Compare two models

Run both with the same seed and number of cases:

```bash
eaon-bench run --provider ollama --model qwen3:8b --cases 60 --seed 77
eaon-bench run --provider ollama --model qwen3-coder-next:q4_K_M --cases 60 --seed 77
```

Use the generated HTML reports to compare:

- overall score;
- task accuracy;
- confidence calibration;
- abstention F1;
- contradiction detection;
- rule-shift adaptation;
- repair/recovery;
- latency.

## 5. Output contract

Each task tells the model to return one JSON object:

```json
{
  "decision": "answer",
  "answer": "42",
  "confidence": 0.91,
  "reason": "Brief explanation"
}
```

Allowed decisions are `answer` and `abstain`. Confidence must be between 0 and 1.

## 6. Scoring

The MVP score is:

```text
overall = 45% accuracy
        + 25% confidence calibration
        + 15% abstention quality
        + 15% recovery/adaptation
```

The report also keeps category-level metrics separate so a strong average cannot hide a weak cognitive dimension.

## 7. Why runtime-generated cases?

Cases are generated procedurally from a seed. This gives us:

- reproducibility when comparing models;
- a private seed for less predictable evaluation;
- easy expansion to thousands of variants;
- less dependence on a static public question bank.

This is not a guarantee against contamination, but it is a better MVP foundation than publishing one fixed answer sheet.

## 8. Architecture

```text
src/eaon_metabench/
├── adapters/       # Ollama and mock system adapters
├── suites/         # Procedural cognitive task generators
├── cli.py          # CLI entry point
├── models.py       # Typed data contracts
├── parsing.py      # Robust JSON response parser
├── report.py       # JSON + HTML report generation
├── runner.py       # Evaluation execution
└── scoring.py      # Metrics and weighted score
```

## 9. Next EAON integration

The next layer should persist model cognitive profiles and expose a routing API:

```text
incoming task
    ↓
task classifier
    ↓
cognitive requirements vector
    ↓
model profile registry
    ↓
best model / agent / tool chain
    ↓
post-task evaluator updates profile
```

That turns benchmarking into active orchestration: EAON selects a model based on measured strengths, not branding or intuition.

## 10. One-command Windows run

From PowerShell in the project folder:

```powershell
.\scripts\run_ollama.ps1 -Model "qwen3:8b" -Cases 40 -Seed 20260713
```

## 11. Compare generated reports

```powershell
eaon-bench compare results\model_a.json results\model_b.json
```
