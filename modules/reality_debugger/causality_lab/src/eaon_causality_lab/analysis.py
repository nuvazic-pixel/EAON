"""Observational statistics, deliberately without causal verdicts."""

import contextlib
import io

import numpy as np
from statsmodels.tools.sm_exceptions import InfeasibleTestError
from statsmodels.tsa.stattools import grangercausalitytests


def _pair(x, y):
    x, y = np.asarray(x, dtype=float), np.asarray(y, dtype=float)
    if x.ndim != 1 or y.ndim != 1 or x.size != y.size or x.size < 4:
        raise ValueError("expected equal-length 1D series with at least four samples")
    if not np.isfinite(x).all() or not np.isfinite(y).all():
        raise ValueError("series must contain only finite values")
    return x, y


def cross_correlation(x, y, max_lag: int) -> dict:
    """Pearson r on overlapping samples: positive lag = X leads Y."""
    x, y = _pair(x, y)
    if not isinstance(max_lag, int) or isinstance(max_lag, bool) or not 0 <= max_lag <= len(x)-3:
        raise ValueError("max_lag must leave at least three overlapping samples")
    rows = []
    for lag in range(-max_lag, max_lag + 1):
        a, b = (x[:-lag], y[lag:]) if lag > 0 else (x[-lag:], y[:lag]) if lag < 0 else (x, y)
        r = None if np.ptp(a) == 0 or np.ptp(b) == 0 else float(np.corrcoef(a, b)[0, 1])
        rows.append({"lag": lag, "r": r, "overlap": len(a)})
    valid = [row for row in rows if row["r"] is not None]
    return {"convention": "corr(X[t], Y[t+lag]); positive lag means X leads Y",
            "peak": max(valid, key=lambda row: abs(row["r"])) if valid else None,
            "values": rows}


def granger(x, y, max_lag: int, alpha: float = 0.05) -> dict:
    """SSR F tests in both directions with Bonferroni over 2*max_lag tests.

    These are predictive associations, not tests for structural causality.
    """
    x, y = _pair(x, y)
    if (not isinstance(max_lag, int) or isinstance(max_lag, bool) or max_lag < 1
            or len(x) <= 3 * max_lag + 2 or not 0 < alpha < 1):
        raise ValueError("invalid alpha/lag or too few samples for Granger tests")
    rows = []
    for name, target, source in (("X_to_Y", y, x), ("Y_to_X", x, y)):
        try:
            # statsmodels expects [target, source]. Suppress its printed tables,
            # without using the deprecated verbose argument or suppressing warnings.
            with contextlib.redirect_stdout(io.StringIO()):
                tests = grangercausalitytests(np.column_stack([target, source]), max_lag)
            for lag, result in tests.items():
                f, p, df_denom, df_num = result[0]["ssr_ftest"]
                if not np.isfinite([f, p, df_denom, df_num]).all():
                    raise InfeasibleTestError("nonfinite test result")
                adjusted = min(1.0, float(p) * 2 * max_lag)
                rows.append({"direction": name, "lag": int(lag), "f": float(f),
                             "p_raw": float(p), "p_adjusted": adjusted,
                             "df_denom": float(df_denom), "df_num": float(df_num),
                             "predictive_association": adjusted < alpha, "status": "ok"})
        except (InfeasibleTestError, np.linalg.LinAlgError, ValueError) as exc:
            rows = [row for row in rows if row["direction"] != name]
            rows.append({"direction": name, "status": "unavailable", "reason": str(exc)})
    return {"test": "ssr_ftest", "correction": "Bonferroni over both directions and all lags",
            "family_size": 2 * max_lag, "alpha": alpha, "results": rows}
