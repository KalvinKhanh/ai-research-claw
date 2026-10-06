"""Integration fixture: benchmark Python-loop vs NumPy vectorized rolling mean.

This is intentionally simple. It exists to demonstrate the input contract,
not to represent a publishable scientific contribution.
"""
from __future__ import annotations

import json
import time
import numpy as np

N = 180_000
WINDOW = 32
REPEATS = 1

def rolling_mean_python(x: np.ndarray, w: int) -> np.ndarray:
    # Cumulative-sum implementation expressed with a Python-side wrapper.
    # Kept separate as a baseline for the integration fixture.
    out = []
    c = np.cumsum(np.insert(x, 0, 0.0))
    vals = (c[w:] - c[:-w]) / float(w)
    for v in vals:
        out.append(v)
    return np.asarray(out)

def rolling_mean_numpy(x: np.ndarray, w: int) -> np.ndarray:
    c = np.cumsum(np.insert(x, 0, 0.0))
    return (c[w:] - c[:-w]) / float(w)

def main() -> None:
    x = np.linspace(0.0, 1.0, N, dtype=np.float64)

    t0 = time.perf_counter()
    a = rolling_mean_python(x, WINDOW)
    t1 = time.perf_counter()

    t2 = time.perf_counter()
    b = rolling_mean_numpy(x, WINDOW)
    t3 = time.perf_counter()

    assert np.allclose(a, b)

    loop_ms = (t1 - t0) * 1000.0
    vec_ms = (t3 - t2) * 1000.0

    result = {
        "primary_metric": vec_ms,
        "metric_key": "numpy_vectorized_latency_ms",
        "metrics": {
            "python_loop_latency_ms": loop_ms,
            "numpy_vectorized_latency_ms": vec_ms,
            "speedup_x": loop_ms / vec_ms,
        },
        "hypotheses": {
            "h1": {
                "supported": bool(vec_ms < loop_ms),
                "value": loop_ms / vec_ms,
                "details": "Vectorized implementation should have lower latency."
            }
        },
        "summary": "NumPy vectorized and Python-loop wrapper return numerically equivalent outputs.",
        "structured_results": {
            "artifacts": {"figures": [], "data": []}
        }
    }
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
