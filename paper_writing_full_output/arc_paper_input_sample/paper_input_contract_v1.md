# Paper Writing Input Contract v1.0
## Source-informed proposal for an AutoResearchClaw Stage 16–23 adapter

This contract is designed to minimize changes to AutoResearchClaw. The public external package is
human-friendly; an adapter materializes it into the artifact names and `stage-*` layout already
consumed by the upstream pipeline.

## 1. What the current source code actually requires

### Stage 16 contract
The upstream Stage 16 `PAPER_OUTLINE` contract declares:
- `analysis.md`
- `decision.md`

as required inputs and produces `outline.md`.

### Stage 17 empirical hard guard
The paper writer scans `stage-*/runs/*.json`, skips payloads whose `status == "simulated"`, and treats
a non-empty `metrics` or `key_metrics` dictionary as real parsed experiment evidence.

Therefore an empirical paper-only run should provide:
- at least one `runs/*.json` file;
- `status` other than `simulated`;
- non-empty `metrics` (preferred) or `key_metrics`.

### Peer-review evidence
The review stage searches prior artifacts for:
- `experiment/` and, when available, `experiment/main.py`;
- `runs/*.json`;
- `refinement_log.json`;
and counts the number of actual run JSON files.

### Quality gate
The quality gate cross-checks the most recent `experiment_summary.json`; the current implementation
uses `condition_summaries` to collect real metric values for fabrication checks.

### Canonical structured result
AutoResearchClaw's domain-integration guidance recommends a canonical `results.json` with:
- `primary_metric`
- `metric_key`
- `metrics`
- `hypotheses`
- `summary`
- `structured_results`

This proposal reuses that shape rather than creating a competing result schema.

## 2. External package — recommended public contract

```text
paper-input/
├── manifest.yaml
├── research/
│   ├── context.md
│   ├── questions.yaml
│   ├── hypotheses.yaml
│   └── contributions.md
├── literature/
│   ├── references.bib
│   └── notes.md
├── methodology/
│   ├── method.md
│   ├── experiment.yaml
│   ├── environment.yaml
│   └── code/
│       └── main.py
├── evidence/
│   ├── analysis.md
│   ├── decision.md
│   ├── experiment_summary.json
│   ├── refinement_log.json
│   ├── runs/
│   │   ├── run-001.json
│   │   ├── ...
│   │   └── results.json
│   ├── figures/
│   └── tables/
├── claims/
│   └── claims.yaml
├── publication/
│   ├── target.yaml
│   └── author_instructions.md
└── schemas/
    ├── manifest.schema.json
    └── run.schema.json
```

## 3. Minimal empirical package

For the adapter to reliably reach paper drafting without weakening upstream anti-fabrication logic:

```text
manifest.yaml
research/context.md
methodology/method.md
evidence/analysis.md
evidence/decision.md
evidence/runs/run-001.json
```

`literature/references.bib` and `publication/target.yaml` are strongly recommended for a useful
publication workflow, even though they are not declared by the Stage 16 contract itself.

## 4. Recommended evidence-rich package

Add:

```text
research/questions.yaml
research/hypotheses.yaml
literature/references.bib
literature/notes.md
methodology/experiment.yaml
methodology/environment.yaml
methodology/code/main.py
evidence/experiment_summary.json
evidence/runs/results.json
evidence/refinement_log.json
evidence/figures/*
evidence/tables/*
claims/claims.yaml
publication/target.yaml
publication/author_instructions.md
```

## 5. Adapter materialization

The adapter should generate a temporary upstream-compatible workspace:

```text
arc-run/
├── analysis_best.md
├── stage-1/goal.md
├── stage-7/synthesis.md
├── stage-8/hypotheses.md
├── stage-9/exp_plan.yaml
├── stage-10/experiment/main.py
├── stage-12/runs/
│   ├── run-001.json
│   └── results.json
├── stage-13/refinement_log.json
├── stage-14/
│   ├── analysis.md
│   └── experiment_summary.json
└── stage-15/decision.md
```

Then run the existing upstream Stage 16 onward.

The critical compatibility files are:
- `stage-14/analysis.md`
- `stage-15/decision.md`
- `stage-12/runs/*.json` for empirical drafting.

The remaining files enrich outline, review, quality checking, and reproducibility.

## 6. Proposed run JSON

```json
{
  "run_id": "RUN-001",
  "status": "success",
  "returncode": 0,
  "elapsed_sec": 12.34,
  "timed_out": false,
  "metrics": {
    "condition/metric_name": 1.234,
    "secondary_metric": 5.678
  },
  "stdout": "condition/metric_name: 1.234",
  "stderr": "",
  "provenance": {
    "external_run_id": "..."
  }
}
```

Rules:
- Prefer `metrics` over parsing numbers from prose.
- Use scalar JSON values for core metrics.
- Never label fabricated/synthetic publication evidence as `success`.
- Use `status: simulated` for synthetic pipeline-development fixtures that must be ignored by the
  upstream empirical writer.
- `results.json` is reserved for aggregate/structured results and is not counted as an individual run.

## 7. Proposed `experiment_summary.json`

```json
{
  "status": "success",
  "primary_metric": "latency_ms",
  "metric_key": "p95_latency_ms",
  "metric_direction": "minimize",
  "run_count": 5,
  "condition_summaries": {
    "baseline": {
      "status": "success",
      "mean_latency_ms": 100.0,
      "std_latency_ms": 5.0,
      "seed_count": 5
    },
    "proposed": {
      "status": "success",
      "mean_latency_ms": 75.0,
      "std_latency_ms": 4.0,
      "seed_count": 5
    }
  }
}
```

`condition_summaries` is important because the current quality-gate code scans it for numeric values.

## 8. Why `analysis_best.md`

The upstream helper `_read_best_analysis()` prefers root-level `analysis_best.md` before falling back
to prior `analysis.md` artifacts. The adapter can therefore copy a human-curated external analysis
to both:
- `analysis_best.md`
- `stage-14/analysis.md`

This preserves the Stage 16 contract while ensuring the most authoritative analysis is selected.

## 9. Why `experiment/main.py`

The peer-review stage explicitly looks for a prior `experiment/` directory and, if present,
`main.py`, then includes an excerpt as “Actual Experiment Code” when checking methodology claims.
External systems should therefore provide code when possible, but code remains optional for writing.

## 10. Bibliography

Keep `literature/references.bib` as the external contract because it is portable and maps naturally
to AutoResearchClaw's final `references.bib` / citation-verification flow.

The adapter should not pretend the bibliography was generated by ARC literature-search stages.
It should mark it as externally supplied and let Stage 23 verify it.

## 11. Figures

External figures should be supplied with source data where practical. The adapter should copy them
into the working/output chart area expected by the export layer and preserve their IDs/captions.
The exact internal destination should be kept inside the adapter because upstream chart/export
implementation may evolve.

## 12. Validation levels

### BLOCKED
- missing context;
- missing `analysis.md`;
- missing `decision.md`;
- empirical paper has no non-simulated run metrics.

### READY_WITH_WARNINGS
- no bibliography;
- no experiment summary;
- no code;
- no figure/table metadata;
- no structured claims.

### READY
- Stage-16 compatibility artifacts present;
- real structured run metrics present;
- bibliography present;
- method/context present;
- summary and publication target present.

## 13. Sample fixture included

The accompanying sample contains **real locally measured benchmark data** generated solely for
integration testing. It is intentionally not positioned as a novel scientific study.

Measured sample summary at package-generation time:
- loop-wrapper mean latency: 16.644221 ms
- vectorized mean latency: 0.927189 ms
- mean speedup: 17.956360x
- run count: 5
