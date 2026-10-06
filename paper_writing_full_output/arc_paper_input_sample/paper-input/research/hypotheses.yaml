hypotheses:
  - id: H1
    related_rq: RQ1
    statement: >
      The direct NumPy vectorized implementation has lower mean execution latency
      than the Python-side loop wrapper for the fixed benchmark workload.
    measurable_prediction:
      metric: latency_ms
      direction: lower
    failure_condition: >
      Mean vectorized latency is greater than or equal to mean loop-wrapper latency.
