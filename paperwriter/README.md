# PaperWriter

The paper-writing half of AutoResearchClaw as a library. Give it a topic,
hypotheses and a reference list; it returns a LaTeX paper whose citations were
checked against Crossref / OpenAlex / arXiv.

```
outline (16) → draft (17) → peer review (18) → revision (19)
             → quality gate (20) → LaTeX export (22) → citation verify (23)
```

## Use from another project

```bash
pip install -e path/to/ai-research-claw        # or: pip install paperwriter
```

```python
from paperwriter import write_paper

result = write_paper(
    {
        "topic": "A survey of topic modelling for journal trend forecasting",
        "hypotheses": ["H1: topic models surface emerging topics earlier than citation counts"],
        "literature": [
            {"title": "…", "authors": ["A. Author"], "year": 2024, "venue": "…", "doi": "10.…"},
        ],
        # optional: "goal", "synthesis" (markdown notes)
    },
    "out/",                       # run directory; each call replaces earlier stage-NN/ output there
    config="config.yaml",         # needs an `llm:` section (see config.researchclaw.example.yaml)
)
print(result.ok, result.paper_tex, result.citations)
```

Or from the shell: `paperwriter input.json -o out/ -c config.yaml`.

Deliverables are collected in `out/final/`: `paper.md`, `paper.tex`,
`references.bib`, `verification_report.json`. Per-stage artifacts stay in
`out/stage-NN/`, and `out/result.json` records the outcome of every stage.

Pass `llm=` to reuse your own client (any object with
`chat(messages, **kwargs) -> LLMResponse`) instead of building one from `config`.

## Scope

- **Literature-first only.** The run is forced to `project.mode: docs-first`, so
  the writer never needs experiment results. Because there is no experiment
  data, the numeric-fabrication checks (verified-value registry, table
  sanitizer) have nothing to compare against and are inactive; avoiding invented
  result numbers relies on the prompts and the review stages, and has only been
  exercised with a fake LLM so far.
- Citations come only from the supplied `literature`. Stage 23 verifies them and
  drops unverifiable ones; the library then removes the same keys from
  `paper.tex`, so `final/` never cites a key missing from `references.bib`.
- No figure input yet (stage 22 only ships experiment charts).
- A rejected quality gate sends the paper back to the outline up to
  `max_rewrites` times (default 1), then the run fails with `result.error` set.
- `export.target_conference` defaults to `generic`; override it in `config`.

## What was removed

Stages 1–15 (topic, literature search, experiments, analysis), the knowledge
archive stage (21), the old `researchclaw` CLI/server/runner, and every module
not reachable from the writing stages. The stage numbers 16–20, 22 and 23 and
the `stage-NN/` directory names are unchanged, so run directories stay
compatible with the full pipeline.
