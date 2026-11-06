import json
import os
import subprocess
import sys

import numpy as np
import pytest

from eaon_causality_lab import Config, run_experiment, simulate
from eaon_causality_lab.analysis import cross_correlation, granger
from eaon_causality_lab.report import write_report


def test_seed_and_stationary_generation():
    a, b = simulate(Config()), simulate(Config())
    for field in ("hidden", "x", "y"):
        np.testing.assert_array_equal(getattr(a, field), getattr(b, field))
        assert len(getattr(a, field)) == 2000
    assert not np.array_equal(a.x, simulate(Config(seed=43)).x)


@pytest.mark.parametrize("dx,dy", [(0, 3), (4, 1), (2, 2)])
def test_delays_have_no_wrapping(dx, dy):
    cfg = Config(delay_x=dx, delay_y=dy, noise=1e-8, ar=0, samples=1000)
    signals = simulate(cfg)
    assert cross_correlation(signals.x, signals.y, 5)["peak"]["lag"] == dy-dx
    np.testing.assert_allclose(signals.x[dx:], signals.hidden[:1000-dx], atol=1e-6)
    np.testing.assert_allclose(signals.y[dy:], signals.hidden[:1000-dy], atol=1e-6)


@pytest.mark.parametrize("seed", [0, 42, 107])
def test_intervention_and_positive_control_equations(seed):
    cfg = Config(seed=seed)
    base, changed = simulate(cfg), simulate(cfg, do_x=3)
    np.testing.assert_array_equal(base.y, changed.y)
    assert np.all(changed.x == 3)
    h_changed = simulate(cfg, do_hidden=3)
    assert np.all(h_changed.hidden == 3)
    assert not np.array_equal(base.x, h_changed.x)
    assert not np.array_equal(base.y, h_changed.y)
    np.testing.assert_allclose(h_changed.x[cfg.delay_x:]-base.x[cfg.delay_x:],
                               3-base.hidden[:-cfg.delay_x], atol=1e-12)
    np.testing.assert_allclose(h_changed.y[cfg.delay_y:]-base.y[cfg.delay_y:],
                               3-base.hidden[:-cfg.delay_y], atol=1e-12)
    control = simulate(cfg, beta=cfg.control_beta)
    intervened = simulate(cfg, beta=cfg.control_beta, do_x=3)
    delay = cfg.control_delay
    np.testing.assert_allclose(intervened.y[delay:]-control.y[delay:],
                               cfg.control_beta*(3-base.x[:-delay]), atol=1e-12)


def test_granger_direction_on_known_predictive_process():
    rng = np.random.default_rng(123)
    x = rng.normal(size=3000)
    y = np.concatenate(([0], x[:-1])) + rng.normal(scale=0.3, size=3000)
    result = granger(x, y, 2)
    rows = result["results"]
    forward = next(r for r in rows if r["direction"] == "X_to_Y" and r["lag"] == 1)
    assert forward["predictive_association"]
    assert forward["p_adjusted"] < 1e-10
    for row in rows:
        assert row["p_adjusted"] == min(1, row["p_raw"]*4)


def test_default_exhibits_false_causality_without_structural_effect():
    result = run_experiment(Config())
    assert result["observational"]["cross_correlation"]["peak"]["lag"] == 3
    assert any(r.get("predictive_association") for r in result["observational"]["granger"]["results"] if r["direction"] == "X_to_Y")
    assert result["interventions"]["do_X"]["Y"]["max_abs_delta"] == 0
    assert result["interventions"]["positive_control_do_X"]["Y"]["mean_abs_delta"] > 1


@pytest.mark.parametrize("kwargs", [
    {"seed": -1}, {"seed": True}, {"samples": 31}, {"samples": 32, "max_lag": 10},
    {"delay_x": -1}, {"delay_y": 2000}, {"noise": 0}, {"noise": float("nan")},
    {"ar": 1}, {"ar": -1}, {"max_lag": 0}, {"max_lag": 2.5}, {"alpha": 0},
    {"control_delay": 0}, {"control_beta": 0}, {"intervention_value": float("inf")},
])
def test_invalid_configuration(kwargs):
    with pytest.raises(ValueError):
        Config(**kwargs)


def test_degenerate_series_and_invalid_observations():
    assert cross_correlation(np.ones(100), np.arange(100), 3)["peak"] is None
    assert all(r["status"] == "unavailable" for r in granger(np.ones(100), np.arange(100), 3)["results"])
    for x, y in (([1, 2, 3, np.nan], [1, 2, 3, 4]), ([1, 2], [1]), ([[1, 2]], [[1, 2]])):
        with pytest.raises(ValueError):
            cross_correlation(x, y, 1)
    with pytest.raises(ValueError):
        granger(np.arange(10), np.arange(10), 3)


def test_reports_reproducible_and_strict_json(tmp_path):
    result = run_experiment(Config(samples=300, max_lag=4))
    write_report(result, tmp_path / "a")
    write_report(run_experiment(Config(samples=300, max_lag=4)), tmp_path / "b")
    for name in ("report.md", "report.json"):
        assert (tmp_path / "a" / name).read_bytes() == (tmp_path / "b" / name).read_bytes()
    decoded = json.loads((tmp_path / "a/report.json").read_text(encoding="utf-8"))
    assert decoded == result
    assert "cauzalitate structurala" in (tmp_path / "a/report.md").read_text(encoding="utf-8")
    assert not (tmp_path / "a/diagnostics.png").exists()


def test_optional_plot(tmp_path):
    pytest.importorskip("matplotlib")
    write_report(run_experiment(Config(samples=100, max_lag=2)), tmp_path, plots=True)
    assert (tmp_path / "diagnostics.png").read_bytes().startswith(b"\x89PNG\r\n\x1a\n")


def test_cli_installed_outside_repository(tmp_path):
    env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
    proc = subprocess.run([sys.executable, "-m", "eaon_causality_lab", "--samples", "100",
                           "--max-lag", "2", "--output", "result"], cwd=tmp_path,
                          env=env, text=True, capture_output=True)
    assert proc.returncode == 0, proc.stderr
    assert json.loads((tmp_path / "result/report.json").read_text())["experiment"] == 4
    bad = subprocess.run([sys.executable, "-m", "eaon_causality_lab", "--ar", "1"],
                         cwd=tmp_path, env=env, text=True, capture_output=True)
    assert bad.returncode == 2
    assert "abs(ar)<1" in bad.stderr
    assert not (tmp_path / "runs").exists()
