from __future__ import annotations

import html
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from eaon_metabench.models import CaseResult


def write_reports(
    output_dir: Path,
    model: str,
    provider: str,
    seed: int,
    summary: dict[str, Any],
    results: list[CaseResult],
) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    safe_model = "".join(char if char.isalnum() or char in "-_" else "_" for char in model)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    stem = f"{safe_model}_{provider}_seed-{seed}_{timestamp}"
    json_path = output_dir / f"{stem}.json"
    html_path = output_dir / f"{stem}.html"

    payload = {
        "metadata": {
            "model": model,
            "provider": provider,
            "seed": seed,
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "benchmark": "EAON MetaBench MVP",
            "version": "0.1.0",
        },
        "summary": summary,
        "results": [result.to_dict() for result in results],
    }
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    html_path.write_text(_render_html(payload), encoding="utf-8")
    return json_path, html_path


def _pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def _bar(label: str, value: float) -> str:
    width = max(0.0, min(100.0, value * 100))
    return f"""
    <div class="metric">
      <div class="metric-head"><span>{html.escape(label)}</span><strong>{_pct(value)}</strong></div>
      <div class="track"><div class="fill" style="width:{width:.2f}%"></div></div>
    </div>
    """


def _render_html(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    metadata = payload["metadata"]
    category_rows = "".join(
        f"<tr><td>{html.escape(name.replace('_', ' ').title())}</td>"
        f"<td>{values['count']}</td>"
        f"<td>{_pct(values['accuracy'])}</td>"
        f"<td>{_pct(values['calibration'])}</td>"
        f"<td>{values['median_latency_ms']:.1f} ms</td></tr>"
        for name, values in summary["categories"].items()
    )

    failures = [result for result in payload["results"] if not result["correct"]][:20]
    failure_rows = "".join(
        f"<tr><td>{html.escape(item['case_id'])}</td>"
        f"<td>{html.escape(item['category'])}</td>"
        f"<td><code>{html.escape(str(item['model_answer']))}</code></td>"
        f"<td>{html.escape(item['error'] or '')}</td></tr>"
        for item in failures
    ) or '<tr><td colspan="4">No failed cases.</td></tr>'

    metrics = "".join(
        [
            _bar("Overall score", summary["overall_score"]),
            _bar("Accuracy", summary["accuracy"]),
            _bar("Confidence calibration", summary["calibration_score"]),
            _bar("Abstention F1", summary["abstention_f1"]),
            _bar("Recovery & adaptation", summary["recovery_adaptation_score"]),
            _bar("Valid response format", summary["parse_rate"]),
        ]
    )

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>EAON MetaBench — {html.escape(metadata['model'])}</title>
<style>
:root {{ color-scheme: light dark; font-family: Inter, ui-sans-serif, system-ui, sans-serif; }}
body {{ max-width: 1050px; margin: 0 auto; padding: 32px 20px 64px; line-height: 1.5; }}
h1 {{ margin-bottom: 4px; }}
.subtle {{ opacity: .72; margin-top: 0; }}
.grid {{ display: grid; grid-template-columns: repeat(auto-fit,minmax(220px,1fr)); gap: 12px; margin: 22px 0; }}
.card {{ border: 1px solid #7775; border-radius: 14px; padding: 16px; }}
.big {{ font-size: 2rem; font-weight: 750; }}
.metric {{ margin: 16px 0; }}
.metric-head {{ display:flex; justify-content:space-between; gap:20px; margin-bottom:6px; }}
.track {{ height: 12px; border-radius: 999px; background: #7773; overflow: hidden; }}
.fill {{ height: 100%; border-radius: inherit; background: currentColor; opacity: .72; }}
table {{ width:100%; border-collapse:collapse; margin-top:12px; }}
th,td {{ text-align:left; padding:10px; border-bottom:1px solid #7774; vertical-align:top; }}
code {{ white-space:pre-wrap; overflow-wrap:anywhere; }}
section {{ margin-top: 34px; }}
</style>
</head>
<body>
<h1>EAON MetaBench MVP</h1>
<p class="subtle">Model: <strong>{html.escape(metadata['model'])}</strong> · Provider: {html.escape(metadata['provider'])} · Seed: {metadata['seed']}</p>
<div class="grid">
  <div class="card"><div class="subtle">Overall score</div><div class="big">{_pct(summary['overall_score'])}</div></div>
  <div class="card"><div class="subtle">Cases</div><div class="big">{summary['total_cases']}</div></div>
  <div class="card"><div class="subtle">Median latency</div><div class="big">{summary['median_latency_ms']:.0f} ms</div></div>
  <div class="card"><div class="subtle">P95 latency</div><div class="big">{summary['p95_latency_ms']:.0f} ms</div></div>
</div>
<section><h2>Cognitive metrics</h2>{metrics}</section>
<section>
<h2>Category profile</h2>
<table><thead><tr><th>Category</th><th>Cases</th><th>Accuracy</th><th>Calibration</th><th>Median latency</th></tr></thead>
<tbody>{category_rows}</tbody></table>
</section>
<section>
<h2>First failed cases</h2>
<table><thead><tr><th>Case</th><th>Category</th><th>Model answer</th><th>Parser/provider error</th></tr></thead>
<tbody>{failure_rows}</tbody></table>
</section>
</body></html>"""
