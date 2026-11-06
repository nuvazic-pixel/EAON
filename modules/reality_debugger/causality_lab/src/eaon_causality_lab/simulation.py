"""Structural equations with shared exogenous noise for paired interventions."""

from dataclasses import dataclass
import math

import numpy as np


@dataclass(frozen=True)
class Config:
    seed: int = 42
    samples: int = 2000
    delay_x: int = 1
    delay_y: int = 4
    noise: float = 0.4
    ar: float = 0.7
    max_lag: int = 8
    alpha: float = 0.05
    intervention_value: float = 3.0
    control_beta: float = 0.8
    control_delay: int = 1

    def __post_init__(self):
        for name in ("seed", "samples", "delay_x", "delay_y", "max_lag", "control_delay"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"{name} must be a nonnegative integer")
        if self.samples < 32 or not 1 <= self.max_lag or self.samples <= 3 * self.max_lag + 2:
            raise ValueError("samples must be >=32 and >3*max_lag+2; max_lag must be >=1")
        if max(self.delay_x, self.delay_y, self.control_delay) >= self.samples:
            raise ValueError("delays must be smaller than samples")
        if self.control_delay < 1:
            raise ValueError("control_delay must be >=1")
        for name in ("noise", "ar", "alpha", "intervention_value", "control_beta"):
            if not math.isfinite(getattr(self, name)):
                raise ValueError(f"{name} must be finite")
        if self.noise <= 0 or abs(self.ar) >= 1 or not 0 < self.alpha < 1:
            raise ValueError("require noise>0, abs(ar)<1 and 0<alpha<1")
        if self.control_beta == 0 or self.intervention_value == 0:
            raise ValueError("intervention_value and control_beta must be nonzero")


@dataclass(frozen=True)
class Signals:
    hidden: np.ndarray
    x: np.ndarray
    y: np.ndarray


def simulate(config: Config, *, beta: float = 0.0, do_x: float | None = None,
             do_hidden: float | None = None) -> Signals:
    """Replace X or H equations over the entire simulated history (including warmup).

    H[t]=ar*H[t-1]+u[t]; X[t]=H[t-dx]+ex[t];
    Y[t]=H[t-dy]+beta*X[t-control_delay]+ey[t].
    beta=0 is experiment 4; beta!=0 is a positive-control world.
    """
    for value in (beta, do_x, do_hidden):
        if value is not None and not math.isfinite(value):
            raise ValueError("structural parameters and interventions must be finite")
    rng = np.random.Generator(np.random.PCG64(config.seed))
    pad = max(config.delay_x, config.delay_y) + config.control_delay
    total = config.samples + pad
    # Stationary initialization avoids a heuristic burn-in near abs(ar)=1.
    hidden = np.empty(total)
    hidden[0] = rng.normal(scale=1 / math.sqrt(1 - config.ar**2))
    innovations = rng.normal(size=total)
    ex = rng.normal(scale=config.noise, size=total)
    ey = rng.normal(scale=config.noise, size=total)
    for t in range(1, total):
        hidden[t] = config.ar * hidden[t - 1] + innovations[t]
    if do_hidden is not None:
        hidden[:] = do_hidden
    indices = np.arange(total)
    x = hidden[np.maximum(indices - config.delay_x, 0)] + ex
    if do_x is not None:
        x[:] = do_x
    y = hidden[np.maximum(indices - config.delay_y, 0)] + ey
    y += beta * x[np.maximum(indices - config.control_delay, 0)]
    return Signals(hidden[pad:].copy(), x[pad:].copy(), y[pad:].copy())
