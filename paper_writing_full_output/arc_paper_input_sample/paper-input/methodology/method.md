# Methodology

A one-dimensional NumPy array of length 180,000 was generated using `numpy.linspace`.
A rolling mean with window size 32 was computed by two numerically equivalent methods.

- **python_loop**: cumulative-sum values are computed and then appended to a Python list.
- **numpy_vectorized**: the same cumulative-sum expression is returned directly as a NumPy array.

Each condition was measured in the same Python process using `time.perf_counter()`.
Five independent executions were recorded by the sample-package builder.
The implementations were checked with `numpy.allclose` before metrics were accepted.

Primary metric: wall-clock latency in milliseconds.
Secondary metric: speedup ratio `loop_latency / vectorized_latency`.

This benchmark is intentionally small and exists solely as a real-data integration fixture.
