# Result Analysis

## Dataset / Workload
The benchmark used an array of 180,000 float64 values and a rolling window of 32.

## Executions
A total of 5 measured executions were recorded.

## Aggregate Results

| Condition | Mean latency (ms) | Std. dev. (ms) |
|---|---:|---:|
| Python-loop wrapper | 16.644221 | 1.528168 |
| NumPy vectorized | 0.927189 | 0.054550 |

The mean speedup ratio was **17.956360×**.
The vectorized implementation reduced mean measured latency by **94.429363%**
relative to the loop-wrapper baseline for this integration fixture.

## Correctness
Outputs from both implementations were checked with `numpy.allclose` in every execution.

## Interpretation
Within this fixture and on the machine used to generate these files, H1 is supported because
the vectorized implementation had lower mean latency. This result is not intended to establish
a general scientific performance claim across machines or workloads.

## Limitations
- Single machine/environment.
- Small benchmark.
- Five runs only.
- No warm-up protocol or CPU-affinity control.
- Intended for adapter/pipeline testing, not publication.
