"""Deterministic Markdown/JSON reports with optional headless plots."""

import json
from pathlib import Path

from .simulation import Config, simulate


def write_report(result: dict, output: str | Path, *, plots: bool = False) -> None:
    plt = None
    if plots:
        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
        except ImportError as exc:
            raise ValueError("Plots require: pip install 'eaon-causality-lab[plots]'") from exc
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    config = Config(**result["config"])
    cross = result["observational"]["cross_correlation"]
    lines = ["# EAON Causality Lab — Experimentul 4", "", result["interpretation"], "",
             "## Reproducere", "", "```json", json.dumps(result["config"], indent=2), "```", "",
             f"Mediu: `{json.dumps(result['environment'], sort_keys=True)}`", "",
             f"RNG: {result['rng']}", "", "## Model si asociere observationala", "",
             result["ground_truth"]["graph"], "", cross["convention"], "",
             f"Varf descriptiv: `{cross['peak']}`", "",
             "Granger SSR F; Bonferroni pe ambele directii si toate lagurile.", "",
             "| Directie | Lag | F | p brut | p ajustat | Asociere predictiva |",
             "|---|---:|---:|---:|---:|---|"]
    for row in result["observational"]["granger"]["results"]:
        if row["status"] == "ok":
            lines.append(f"| {row['direction']} | {row['lag']} | {row['f']:.6g} | {row['p_raw']:.6g} | {row['p_adjusted']:.6g} | {row['predictive_association']} |")
        else:
            lines.append(f"| {row['direction']} | — | — | — | — | indisponibil: {row['reason']} |")
    lines += ["", "## Interventii simulate", "", "```json",
              json.dumps(result["interventions"], indent=2), "```", "", "## Limite", ""]
    lines += [f"- {caution}" for caution in result["cautions"]]
    if plt is not None:
        observed = simulate(config)
        changed = simulate(config, do_x=config.intervention_value)
        control = simulate(config, beta=config.control_beta)
        control_do = simulate(config, beta=config.control_beta, do_x=config.intervention_value)
        fig, axes = plt.subplots(3, 1, figsize=(10, 9), constrained_layout=True)
        count = min(250, config.samples)
        for label, values in (("H (oracle only)", observed.hidden), ("X", observed.x), ("Y", observed.y)):
            axes[0].plot(values[:count], label=label, alpha=0.8)
        axes[0].set_title("Shared hidden cause with different delays")
        axes[0].legend()
        axes[1].plot([r["lag"] for r in cross["values"]], [r["r"] for r in cross["values"]], marker="o")
        axes[1].set(xlabel="Lag (positive: X leads Y)", ylabel="Pearson r")
        axes[2].plot((changed.y-observed.y)[:count], label="No X -> Y")
        axes[2].plot((control_do.y-control.y)[:count], label="Positive control X -> Y", alpha=0.8)
        axes[2].set(xlabel="Sample", ylabel="Paired change in Y after do(X)")
        axes[2].legend()
        fig.savefig(output / "diagnostics.png", dpi=140)
        plt.close(fig)
        lines += ["", "![Diagnostic plots](diagnostics.png)"]
    (output / "report.json").write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False)+"\n", encoding="utf-8")
    (output / "report.md").write_text("\n".join(lines)+"\n", encoding="utf-8")
