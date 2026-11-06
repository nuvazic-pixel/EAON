"""Offline synthetic causality experiments; no inference about real-world causes."""

from .simulation import Config, simulate
from .experiment import run_experiment

__all__ = ["Config", "simulate", "run_experiment"]
