"""Experiment 4 and paired structural interventions."""

from dataclasses import asdict
from importlib.metadata import version
import platform

import numpy as np

from .analysis import cross_correlation, granger
from .simulation import Config, simulate


CAUTIONS = [
    "Corelatia si predictia Granger nu dovedesc cauzalitate structurala; H este ascuns analizei.",
    "Procesul observat este stationar prin constructie (abs(ar)<1), nu printr-un test ADF.",
    "P-valorile F sunt exploratorii: confuzia latenta, reziduurile autocorelate si ordinul finit pot invalida calibrarea.",
    "Bonferroni acopera ambele directii si lagurile din aceasta rulare, nu cautari repetate de seed/parametri.",
    "Varful cross-correlation este descriptiv; nu are interval de incredere sau semnificatie cauzala.",
    "Interventiile sunt demonstratii in modelul cunoscut, cu zgomot pereche; nu sunt dovezi despre lumea reala.",
    "Efect zero in acest model nu exclude efecte in alte modele; Granger nesemnificativ nu dovedeste absenta cauzalitatii.",
]


def _effect(before, after):
    delta = after - before
    return {"mean_delta": float(np.mean(delta)), "mean_abs_delta": float(np.mean(abs(delta))),
            "max_abs_delta": float(np.max(abs(delta)))}


def run_experiment(config: Config) -> dict:
    observed = simulate(config)
    do_x = simulate(config, do_x=config.intervention_value)
    do_h = simulate(config, do_hidden=config.intervention_value)
    control = simulate(config, beta=config.control_beta)
    control_do = simulate(config, beta=config.control_beta, do_x=config.intervention_value)
    return {
        "schema_version": "1.0", "experiment": 4, "config": asdict(config),
        "environment": {"python": platform.python_version(),
                        **{name: version(name) for name in ("numpy", "scipy", "statsmodels", "eaon-causality-lab")}},
        "rng": "numpy PCG64; identical seed and exogenous draws in paired worlds",
        "ground_truth": {"graph": "H -> X; H -> Y; no X -> Y or Y -> X",
                         "expected_alignment_lag": config.delay_y - config.delay_x,
                         "positive_control": "H -> X; H -> Y; X[t-control_delay] -> Y[t]"},
        "observational": {"cross_correlation": cross_correlation(observed.x, observed.y, config.max_lag),
                          "granger": granger(observed.x, observed.y, config.max_lag, config.alpha)},
        "interventions": {
            "semantics": "replace equation by constant over entire history; paired exogenous noise",
            "value": config.intervention_value,
            "do_X": {"X": _effect(observed.x, do_x.x), "Y": _effect(observed.y, do_x.y)},
            "do_H": {"X": _effect(observed.x, do_h.x), "Y": _effect(observed.y, do_h.y)},
            "positive_control_do_X": {"beta": config.control_beta, "delay": config.control_delay,
                                      "Y": _effect(control.y, control_do.y)},
        },
        "interpretation": "Asocierea observationala poate proveni din H. do(X) lasa Y identic in modelul fara legatura; controlul cu X -> Y raspunde interventiei.",
        "cautions": CAUTIONS,
    }
