from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.progress import BarColumn, Progress, TextColumn, TimeElapsedColumn
from rich.table import Table

from eaon_metabench.adapters import OllamaAdapter, PerfectMockAdapter
from eaon_metabench.compare import load_report
from eaon_metabench.report import write_reports
from eaon_metabench.runner import run_suite
from eaon_metabench.scoring import summarize
from eaon_metabench.suites import generate_metacognition_suite

app = typer.Typer(no_args_is_help=True, help="EAON cognitive benchmark harness.")
console = Console()


@app.callback()
def main() -> None:
    """EAON cognitive benchmark harness."""


@app.command()
def run(
    provider: Annotated[str, typer.Option(help="Provider: ollama or mock.")] = "ollama",
    model: Annotated[str, typer.Option(help="Model identifier.")] = "qwen3:8b",
    base_url: Annotated[str, typer.Option(help="Ollama base URL.")] = "http://localhost:11434",
    cases: Annotated[int, typer.Option(min=6, help="Number of generated cases.")] = 36,
    seed: Annotated[int, typer.Option(help="Reproducible private test seed.")] = 42,
    timeout: Annotated[float, typer.Option(min=1, help="Provider timeout in seconds.")] = 120.0,
    temperature: Annotated[float, typer.Option(min=0, max=2)] = 0.0,
    output_dir: Annotated[Path, typer.Option(help="Report directory.")] = Path("results"),
) -> None:
    """Run the metacognition suite and generate JSON/HTML reports."""
    provider_key = provider.strip().lower()
    if provider_key == "ollama":
        adapter = OllamaAdapter(
            model=model,
            base_url=base_url,
            timeout=timeout,
            temperature=temperature,
        )
    elif provider_key == "mock":
        adapter = PerfectMockAdapter()
    else:
        raise typer.BadParameter("Provider must be 'ollama' or 'mock'.")

    suite = generate_metacognition_suite(count=cases, seed=seed)
    progress = Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("{task.completed}/{task.total}"),
        TimeElapsedColumn(),
        console=console,
    )

    with progress:
        task_id = progress.add_task(f"Evaluating {model}", total=len(suite))

        def update(_index: int, _total: int, _result: object) -> None:
            progress.advance(task_id)

        results = run_suite(adapter=adapter, cases=suite, progress=update)

    summary = summarize(results)
    json_path, html_path = write_reports(
        output_dir=output_dir,
        model=model,
        provider=provider_key,
        seed=seed,
        summary=summary,
        results=results,
    )

    table = Table(title="EAON MetaBench Result")
    table.add_column("Metric")
    table.add_column("Score", justify="right")
    table.add_row("Overall", f"{summary['overall_score'] * 100:.1f}%")
    table.add_row("Accuracy", f"{summary['accuracy'] * 100:.1f}%")
    table.add_row("Calibration", f"{summary['calibration_score'] * 100:.1f}%")
    table.add_row("Abstention F1", f"{summary['abstention_f1'] * 100:.1f}%")
    table.add_row("Recovery/adaptation", f"{summary['recovery_adaptation_score'] * 100:.1f}%")
    table.add_row("Parse rate", f"{summary['parse_rate'] * 100:.1f}%")
    table.add_row("Median latency", f"{summary['median_latency_ms']:.1f} ms")
    console.print(table)
    console.print(f"JSON report: [bold]{json_path}[/bold]")
    console.print(f"HTML report: [bold]{html_path}[/bold]")


@app.command()
def compare(
    reports: Annotated[list[Path], typer.Argument(help="Two or more JSON reports.")],
) -> None:
    """Compare model profiles from existing JSON reports."""
    if len(reports) < 2:
        raise typer.BadParameter("Provide at least two JSON reports.")

    table = Table(title="EAON MetaBench Comparison")
    table.add_column("Model")
    table.add_column("Overall", justify="right")
    table.add_column("Accuracy", justify="right")
    table.add_column("Calibration", justify="right")
    table.add_column("Abstention F1", justify="right")
    table.add_column("Recovery", justify="right")
    table.add_column("Latency", justify="right")

    payloads = [load_report(path) for path in reports]
    payloads.sort(key=lambda item: item["summary"]["overall_score"], reverse=True)
    for payload in payloads:
        meta = payload["metadata"]
        summary = payload["summary"]
        table.add_row(
            str(meta["model"]),
            f"{summary['overall_score'] * 100:.1f}%",
            f"{summary['accuracy'] * 100:.1f}%",
            f"{summary['calibration_score'] * 100:.1f}%",
            f"{summary['abstention_f1'] * 100:.1f}%",
            f"{summary['recovery_adaptation_score'] * 100:.1f}%",
            f"{summary['median_latency_ms']:.0f} ms",
        )
    console.print(table)


if __name__ == "__main__":
    app()
