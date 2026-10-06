# PRODUCT REQUIREMENTS DOCUMENT (PRD)
# Paper Writing Module — AutoResearchClaw-based

**Version:** 1.0  
**Status:** Draft for Implementation  
**Product type:** AI-assisted Academic Paper Writing with Human-in-the-Loop (HITL)  
**Implementation strategy:** Reuse-first / fork-and-adapt AutoResearchClaw; do not build a new paper-writing engine from scratch.  
**Baseline upstream:** `aiming-lab/AutoResearchClaw` (target the latest validated v0.5.x-compatible commit at implementation time)  
**Primary upstream areas:** Phase G (Stages 16–19), Phase H (Stages 20–23), HITL Co-Pilot, claim/number verification, artifact/version management, export and citation verification.

---

## 1. Executive Summary

Paper Writing Module is an independent product that transforms externally generated research materials into a publication-ready academic paper with Human-in-the-Loop controls.

The product does **not** execute scientific experiments. It assumes that research, simulations, training jobs, measurements, data collection, and statistical processing may have been performed in external environments. The module receives the resulting research package and converts it into a structured manuscript.

The core product flow is:

```text
External Research Package
        ↓
Input Validation / Normalization
        ↓
AutoResearchClaw Compatibility Adapter
        ↓
Stage 16 — PAPER_OUTLINE
        ↓
HITL Outline Review
        ↓
Stage 17 — PAPER_DRAFT
        ↓
HITL Paper Co-Writer
        ↓
Stage 18 — PEER_REVIEW
        ↓
HITL Review Triage
        ↓
Stage 19 — PAPER_REVISION
        ↓
Stage 20 — QUALITY_GATE
        ↓
HITL Final Quality Approval
        ↓
Stage 21 — KNOWLEDGE_ARCHIVE
        ↓
Stage 22 — EXPORT_PUBLISH
        ↓
Stage 23 — CITATION_VERIFY
        ↓
Final Paper Package
```

The main engineering principle is:

> **Do not reimplement functionality already available in AutoResearchClaw.**

The product SHALL fork or vendor AutoResearchClaw and introduce the minimum adaptation layer required to start the pipeline from paper-writing rather than from research scoping.

---

# 2. Product Vision

Enable a researcher to provide completed or partially completed research materials from any external research environment and obtain a high-quality scientific manuscript while retaining control over scientific claims, writing decisions, review comments, and final publication output.

The product should behave as an **AI academic co-writer**, not as an autonomous replacement for the researcher.

---

# 3. Product Goals

## G1. Independent Paper Writing

Users can create a paper without running AutoResearchClaw Stages 1–15.

The system SHALL accept externally generated research inputs and enter the upstream paper-writing workflow directly.

## G2. Maximum AutoResearchClaw Reuse

Reuse upstream functionality whenever available, especially:

- Stage 16 `PAPER_OUTLINE`
- Stage 17 `PAPER_DRAFT`
- Stage 18 `PEER_REVIEW`
- Stage 19 `PAPER_REVISION`
- Stage 20 `QUALITY_GATE`
- Stage 21 `KNOWLEDGE_ARCHIVE`
- Stage 22 `EXPORT_PUBLISH`
- Stage 23 `CITATION_VERIFY`
- HITL Co-Pilot
- Paper Co-Writer
- SmartPause where applicable
- stage policies
- guidance injection
- snapshots/versioning
- resume capability
- VerifiedRegistry / anti-fabrication mechanisms
- claim verification mechanisms
- cost guardrails
- LLM configuration/provider abstraction
- citation verification
- LaTeX/template export
- artifact manifests and checksums where available.

## G3. Evidence-Grounded Writing

Experimental numbers and empirical findings must originate from user-supplied research evidence.

The module SHALL NOT invent missing experimental results.

## G4. Human-in-the-Loop Publication Workflow

Users must be able to review, edit, approve, reject, guide, or request regeneration at critical writing stages.

## G5. Publication-Ready Outputs

The product shall generate editable and submission-oriented outputs such as Markdown, LaTeX, bibliography, figures/tables bundle, verification reports, and PDF where compilation is supported.

## G6. Research-Environment Independence

The input research package may originate from any research environment:

- local workstation;
- HPC;
- Kubernetes;
- cloud infrastructure;
- Jupyter/Colab;
- laboratory instrumentation;
- simulation platforms;
- ML pipelines;
- database exports;
- external analytical systems.

The Paper Writing Module does not need to control those systems.

---

# 4. Non-Goals

The first product release SHALL NOT attempt to replace upstream research automation.

Specifically, the module will not be responsible for:

- generating research topics from scratch;
- literature discovery as a mandatory prerequisite;
- designing experiments;
- writing experiment code;
- running experiments;
- allocating GPU/HPC resources;
- debugging experiment execution;
- automatically pivoting hypotheses based on newly executed experiments;
- collecting sensor/lab data;
- training models;
- managing scientific instruments.

If literature, analysis, claims, or experiment data are missing, the module may flag gaps and ask for human input, but it must not silently fabricate them.

---

# 5. Upstream Foundation: AutoResearchClaw

The product SHALL be implemented as an adaptation of AutoResearchClaw rather than as a greenfield implementation.

AutoResearchClaw already provides the primary writing/finalization workflow:

| Stage | Upstream capability | Expected artifact |
|---|---|---|
| 16 | PAPER_OUTLINE | `outline.md` |
| 17 | PAPER_DRAFT | `paper_draft.md` |
| 18 | PEER_REVIEW | `reviews.md` |
| 19 | PAPER_REVISION | `paper_revised.md` |
| 20 | QUALITY_GATE | `quality_report.json` |
| 21 | KNOWLEDGE_ARCHIVE | `archive.md`, bundle metadata |
| 22 | EXPORT_PUBLISH | `paper_final.md`, `paper.tex`, `references.bib`, charts/code package as applicable |
| 23 | CITATION_VERIFY | `verification_report.json`, `references_verified.bib` |

The upstream implementation also provides Human-in-the-Loop modes and a Paper Co-Writer experience.

### Product implementation rule

Before writing a new subsystem, the development team MUST answer:

1. Does AutoResearchClaw already provide this capability?
2. Can it be reused through configuration?
3. Can it be wrapped?
4. Can it be extended through a small adapter/plugin?
5. Only if all previous answers are no may a new implementation be introduced.

---

# 6. Product Positioning

The product is not:

```text
Idea → Autonomous Research → Experiment → Paper
```

It is:

```text
External Research Materials
            ↓
      Paper Writing
            ↕
     Human Researcher
            ↓
      Final Manuscript
```

Its primary value is converting existing scientific evidence and research knowledge into a well-structured manuscript while preserving human authority.

---

# 7. Target Users

## 7.1 Primary Persona — Researcher / PhD Student

Needs to:

- combine research artifacts from multiple tools;
- create a first manuscript draft;
- control scientific language;
- prevent fabricated experimental claims;
- revise sections iteratively;
- generate journal/conference-ready LaTeX.

## 7.2 Secondary Persona — Research Supervisor

Needs to:

- inspect outline;
- review claims;
- comment on sections;
- approve or reject revisions;
- inspect review and quality reports.

## 7.3 Secondary Persona — Research Team

Needs to:

- collaborate on a draft;
- preserve versions;
- see who changed what;
- maintain consistent terminology.

---

# 8. Primary User Journey

```text
1. Create Paper Project
2. Select target venue/template
3. Upload/import Research Package
4. System validates package
5. System maps package to AutoResearchClaw-compatible context
6. Generate paper outline
7. Human reviews/edits/approves outline
8. Generate paper section-by-section
9. Human co-writes/edits/locks selected sections
10. System verifies empirical claims/numbers
11. Run simulated peer review
12. Human triages review comments
13. System revises paper
14. Run quality gate
15. Human gives final approval or requests revision
16. Verify citations
17. Export final publication package
```

---

# 9. Input Contract

The product accepts a **Research Paper Package**.

The source system is not relevant. The only requirement is that the package contains enough scientific material to support the paper.

Inputs are divided into Required, Recommended, and Optional categories.

---

# 10. Required Inputs

A paper job cannot enter Stage 17 unless the minimum required inputs are available.

## 10.1 Research Context

Required fields:

- working title or topic;
- research problem;
- objective and/or research question;
- research domain.

Example:

```yaml
research:
  title: "..."
  domain: "distributed systems"
  problem_statement: "..."
  objectives:
    - "..."
  research_questions:
    - id: RQ1
      statement: "..."
```

## 10.2 Methodology

The methodology must describe what was actually done.

May include:

- research design;
- proposed method;
- architecture;
- algorithms;
- datasets;
- baselines;
- evaluation metrics;
- experiment configuration;
- hardware/software environment;
- statistical methods.

Accepted formats:

- Markdown
- TXT
- JSON
- YAML
- PDF
- DOCX
- source code
- notebook exports
- image/diagram metadata.

## 10.3 Results / Evidence

At least one result source is required for empirical papers.

Accepted formats:

- CSV
- JSON
- JSONL
- Excel
- Parquet
- Markdown tables
- LaTeX tables
- statistical reports
- analysis documents.

Examples:

```text
results/
  metrics.csv
  experiment_summary.json
  statistical_tests.csv
  analysis.md
```

## 10.4 References

At least one of:

- `references.bib`;
- DOI list;
- structured reference JSON;
- PDF literature package;
- RIS;
- validated bibliography source.

---

# 11. Recommended Inputs

## 11.1 Literature Notes

Useful for:

- Introduction;
- Related Work;
- research gap;
- Discussion.

## 11.2 Research Gap

Example:

```yaml
research_gap:
  statement: "..."
  supporting_references:
    - REF-001
    - REF-014
```

## 11.3 Hypotheses

Example:

```yaml
hypotheses:
  - id: H1
    statement: "..."
    related_rq: RQ1
```

## 11.4 Experiment Metadata

```yaml
experiments:
  - id: EXP-001
    objective: "..."
    dataset: "..."
    baselines:
      - BASELINE-A
    metrics:
      - p95_latency
      - throughput
    runs:
      - RUN-001
      - RUN-002
```

## 11.5 Statistical Analysis

May contain:

- mean;
- median;
- standard deviation;
- confidence intervals;
- effect size;
- p-values;
- ANOVA;
- regression output;
- non-parametric tests.

---

# 12. Optional Inputs

## 12.1 Structured Claims

This is highly valuable but not mandatory.

```yaml
claims:
  - id: C-001
    type: empirical
    statement: "The proposed system reduces p95 latency."
    evidence:
      - RESULT-004
      - RESULT-005
```

## 12.2 Figures

Accepted formats:

- PNG
- JPEG
- SVG
- PDF
- EPS

Recommended metadata:

```yaml
figure:
  id: FIG-001
  caption: "..."
  related_experiments:
    - EXP-001
  supports_claims:
    - C-001
```

## 12.3 Tables

Accepted formats:

- CSV
- XLSX
- Markdown
- LaTeX
- JSON.

## 12.4 Source Code

Code is optional for writing but can improve method verification.

## 12.5 Author Writing Instructions

Examples:

```yaml
writing:
  language: English
  tone: formal-academic
  emphasis:
    - system evaluation
  avoid:
    - unsupported causal claims
  terminology:
    preferred:
      - "serverless architecture"
```

---

# 13. Publication Target Input

The user should be able to provide:

```yaml
publication:
  type: journal
  publisher: IEEE
  venue: "..."
  template: "..."
  paper_type: research_article
  language: English
  citation_style: IEEE
  page_or_word_limit: null
```

The module SHOULD reuse AutoResearchClaw's template/export capabilities.

New templates should be added as extensions to the upstream template system instead of building a separate rendering engine.

---

# 14. Input Package Structure

Recommended external package:

```text
paper-package/
├── manifest.yaml
├── research/
│   ├── context.md
│   ├── research_questions.yaml
│   ├── contributions.md
│   └── hypotheses.yaml
├── literature/
│   ├── references.bib
│   ├── literature_notes.md
│   └── papers/
├── methodology/
│   ├── methodology.md
│   ├── architecture.pdf
│   └── experiment_config.yaml
├── experiments/
│   ├── experiment_manifest.yaml
│   └── run_metadata/
├── results/
│   ├── experiment_summary.json
│   ├── metrics.csv
│   ├── statistics.csv
│   └── analysis.md
├── claims/
│   └── claims.yaml
├── figures/
├── tables/
└── publication/
    └── target.yaml
```

The exact physical structure may vary. The Intake Adapter SHALL normalize all supported layouts.

---

# 15. Input Completeness Levels

## Level 1 — Minimum

- research context;
- methodology;
- results;
- references.

Expected behavior:

- allow outline and draft;
- display warnings;
- require more human review.

## Level 2 — Standard

Level 1 plus:

- literature notes;
- research gap;
- experiment descriptions;
- statistical analysis;
- figures;
- tables.

Expected behavior:

- normal co-writer workflow.

## Level 3 — Evidence-Rich

Level 2 plus:

- hypotheses;
- structured claims;
- result/evidence IDs;
- experiment IDs;
- run IDs;
- claim-to-evidence relations.

Expected behavior:

- strongest anti-fabrication and traceability.

---

# 16. Input Validation

The product introduces a thin `ResearchPackageIntake` layer.

This is one of the few components that must be newly developed because AutoResearchClaw normally obtains context from Stages 1–15.

Validation categories:

## 16.1 Research Validation

- research problem exists;
- at least one objective/RQ exists;
- domain is known or can be classified.

## 16.2 Method Validation

- methodology content exists;
- experiment method and/or analytical method can be identified.

## 16.3 Result Validation

For empirical papers:

- result files are present;
- metrics can be parsed;
- numbers are finite;
- no obvious NaN/Inf-only data;
- experiment/result IDs resolve when supplied.

## 16.4 Literature Validation

- bibliography parses successfully;
- reference IDs are unique;
- required metadata is available where possible.

## 16.5 Artifact Validation

- figure/table paths exist;
- linked IDs resolve;
- unsupported file types are reported.

Output:

```json
{
  "status": "READY | READY_WITH_WARNINGS | BLOCKED",
  "errors": [],
  "warnings": [],
  "detected_inputs": {}
}
```

---

# 17. AutoResearchClaw Compatibility Adapter

This adapter is the key product-specific engineering component.

## 17.1 Purpose

Make externally generated research data appear to Stages 16–23 as valid upstream research context.

## 17.2 Strategy

Do NOT fork and rewrite Stage 16–23 logic.

Instead:

```text
External Research Package
        ↓
Normalizer
        ↓
Compatibility Adapter
        ↓
AutoResearchClaw artifact/context contract
        ↓
Existing Stage 16–23 implementation
```

## 17.3 Known upstream compatibility artifacts

The adapter must populate or expose, as applicable to the pinned upstream commit:

- research goal/context;
- literature/reference context;
- methodology/experiment context;
- `analysis.md`;
- `experiment_summary.json`;
- `decision.md` or equivalent proceed-ready context;
- figures/tables;
- bibliography;
- verified numeric registry inputs.

The adapter SHALL be tested against the exact upstream commit because internal schemas may evolve.

## 17.4 Proceed Decision

For paper-only workflows, the adapter may synthesize a compatibility decision indicating that the supplied evidence is ready for writing.

Example:

```text
Decision: PROCEED_TO_WRITING
Source: external-research-package
Human-confirmed: true
```

This is an integration artifact only; it must not imply that the product independently validated the scientific correctness of the research.

---

# 18. Paper-Only Execution Profile

Create a new execution profile:

```text
paper-only
```

Expected command conceptually:

```bash
researchclaw paper \
  --input ./paper-package \
  --mode co-pilot \
  --config config.paper.yaml
```

The exact CLI can be implemented as a thin wrapper around the upstream runner.

The `paper-only` profile SHALL:

1. skip Stages 1–15;
2. run package validation;
3. generate upstream-compatible context;
4. enter Stage 16;
5. preserve upstream artifact conventions;
6. preserve upstream resume/version behavior;
7. preserve HITL controls;
8. execute Stage 16–23 unless a product configuration disables optional stages.

---

# 19. Core Workflow

```text
PW-00 INPUT_INTAKE                 [NEW THIN LAYER]
        ↓
PW-01 NORMALIZE                    [NEW THIN LAYER]
        ↓
PW-02 ARC_COMPATIBILITY_ADAPTER    [NEW THIN LAYER]
        ↓
ARC-16 PAPER_OUTLINE               [REUSE]
        ↓
HITL-OUTLINE                       [REUSE/ADAPT]
        ↓
ARC-17 PAPER_DRAFT                 [REUSE]
        ↓
HITL-CO-WRITER                     [REUSE]
        ↓
CLAIM/NUMBER VERIFY                [REUSE WHERE AVAILABLE]
        ↓
ARC-18 PEER_REVIEW                 [REUSE]
        ↓
HITL-REVIEW_TRIAGE                 [ADAPT UPSTREAM HITL]
        ↓
ARC-19 PAPER_REVISION              [REUSE]
        ↓
ARC-20 QUALITY_GATE                [REUSE]
        ↓
HITL-FINAL APPROVAL                [REUSE]
        ↓
ARC-21 KNOWLEDGE_ARCHIVE           [REUSE]
        ↓
ARC-22 EXPORT_PUBLISH              [REUSE]
        ↓
ARC-23 CITATION_VERIFY             [REUSE]
        ↓
FINAL DELIVERABLES
```

---

# 20. Stage 16 — Paper Outline

Reuse AutoResearchClaw `PAPER_OUTLINE`.

Requirements:

- generate a section-level outline;
- map research materials to sections;
- map supplied figures/tables where possible;
- map RQs/hypotheses/claims to candidate sections;
- support target venue constraints.

Typical structure:

```text
1. Introduction
2. Background / Related Work
3. Method / System Design
4. Experimental Setup
5. Results
6. Discussion
7. Limitations
8. Conclusion
```

The structure must remain configurable.

Output:

```text
stage-16/outline.md
```

Optional product metadata:

```text
stage-16/outline_map.json
```

---

# 21. HITL — Outline Review

The human researcher can:

- approve;
- edit;
- reorder sections;
- add/remove sections;
- regenerate part or all;
- inject guidance;
- lock the outline.

The implementation SHOULD reuse the upstream HITL collaboration and stage-policy mechanisms.

Required state transitions:

```text
GENERATED
  ↓
UNDER_HUMAN_REVIEW
  ├── APPROVED
  ├── EDITED_AND_APPROVED
  └── REGENERATE
```

---

# 22. Stage 17 — Paper Draft

Reuse AutoResearchClaw `PAPER_DRAFT`.

Upstream behavior to preserve:

- section-by-section generation;
- long-form academic drafting;
- anti-fabrication guard;
- use of experiment metrics;
- title/abstract guidance;
- human co-writing support.

The product SHOULD encourage generation in a scientifically safe order:

```text
Method / System Design
        ↓
Experimental Setup
        ↓
Results
        ↓
Discussion
        ↓
Related Work
        ↓
Introduction
        ↓
Conclusion
        ↓
Abstract
```

This may be implemented through prompt/config changes without replacing the upstream writer.

Output:

```text
stage-17/paper_draft.md
```

---

# 23. Drafting Rules

## FR-WRITE-001 — No fabricated numerical evidence

The model must not introduce experiment numbers that cannot be resolved to supplied verified data.

## FR-WRITE-002 — Missing data marker

If necessary information is missing:

```text
[AUTHOR INPUT REQUIRED: ...]
```

or an equivalent structured issue SHALL be created.

## FR-WRITE-003 — Preserve negative results

Negative or non-significant findings must not be automatically removed simply because they weaken the narrative.

## FR-WRITE-004 — Claim strength

Language must reflect evidence strength.

Examples:

Prefer:

- “is associated with”
- “the results suggest”
- “outperformed in the evaluated settings”

rather than unsupported universal/causal statements.

## FR-WRITE-005 — Human authority

Explicit human edits must not be silently overwritten.

---

# 24. Paper Co-Writer / HITL Drafting

Reuse the upstream Paper Co-Writer.

The product SHALL support the three collaboration patterns already represented upstream:

### AI-first

AI produces sections; human edits/refines.

### Human-first

Human supplies key text; AI expands, restructures, or polishes.

### Interleaved

Human and AI take responsibility for different sections.

Product requirements:

- section-level editing;
- section-level regenerate;
- AI polish;
- guidance injection;
- human comments;
- section lock;
- revision snapshots;
- diff/change summary where available.

A locked section SHALL only be changed after explicit unlock/approval.

---

# 25. Verified Numbers / Anti-Fabrication

Reuse upstream VerifiedRegistry and related sanitization/claim verification capabilities wherever technically compatible.

The new input adapter SHALL load externally supplied numerical results into the upstream verification mechanism.

Example conceptual registry:

```yaml
verified_values:
  - result_id: RESULT-012
    metric: p95_latency
    value: 124.2
    unit: ms
    experiment_id: EXP-001
```

Acceptance rule:

> Any quantitative empirical statement in generated paper content must either map to a verified value/evidence object or be flagged for human review.

Do not create a separate numeric verification system unless upstream extension proves impossible.

---

# 26. Stage 18 — Peer Review

Reuse AutoResearchClaw `PEER_REVIEW`.

Minimum product requirements:

- at least two reviewer perspectives;
- methodology review;
- evidence/results review;
- baseline/ablation critique where relevant;
- claim-vs-evidence critique;
- writing/presentation critique;
- numeric or rubric-based scoring.

Output:

```text
stage-18/reviews.md
```

Optional structured review:

```text
stage-18/reviews.json
```

---

# 27. HITL Review Triage

The user shall classify review comments:

```text
ACCEPT
REJECT
DEFER
NEEDS_DISCUSSION
```

Additional fields:

- author response;
- planned action;
- affected section;
- priority.

The revision engine shall only act on accepted comments unless an automatic policy explicitly allows otherwise.

---

# 28. Stage 19 — Paper Revision

Reuse AutoResearchClaw `PAPER_REVISION`.

Preserve the upstream revision-length guard where possible.

Inputs:

- paper draft;
- accepted reviewer comments;
- human guidance;
- verification issues.

Output:

```text
stage-19/paper_revised.md
```

The product SHALL maintain:

```text
revision_log.json
```

Example:

```json
{
  "review_comment_id": "R2-C04",
  "decision": "ACCEPT",
  "action": "Expanded limitations discussion",
  "section": "Discussion"
}
```

---

# 29. Stage 20 — Quality Gate

Reuse AutoResearchClaw `QUALITY_GATE`.

Expected report:

```text
stage-20/quality_report.json
```

Quality dimensions should preserve the upstream mechanism and may be extended through configuration for:

- structure;
- writing clarity;
- methodology consistency;
- result grounding;
- claim strength;
- citation coverage;
- figure/table completeness;
- venue compliance.

The product SHALL NOT create a second independent quality-scoring engine for MVP.

---

# 30. Final HITL Approval

The researcher must be able to:

```text
APPROVE
RETURN_TO_REVISION
RETURN_TO_OUTLINE
EDIT_MANUALLY
REJECT
```

Default publication configuration:

```text
human_final_approval_required: true
```

Final export should not be marked “approved” unless a human explicitly approves it.

---

# 31. Stage 21 — Knowledge Archive

Reuse upstream `KNOWLEDGE_ARCHIVE`.

For this product, archive content may include:

- paper writing decisions;
- author guidance;
- reviewer decisions;
- unresolved issues;
- terminology preferences;
- version history.

Do not expand this into a new research knowledge-management product in MVP.

---

# 32. Stage 22 — Export / Publish

Reuse upstream `EXPORT_PUBLISH`.

Primary outputs:

```text
paper_final.md
paper.tex
references.bib
```

When the deployment includes a supported LaTeX engine:

```text
paper.pdf
```

Other possible outputs:

```text
figures/
charts/
tables/
manifest.json
```

DOCX is a future/optional adapter. It should not replace the upstream Markdown/LaTeX path.

---

# 33. Stage 23 — Citation Verification

Reuse AutoResearchClaw `CITATION_VERIFY`.

Required behavior:

- verify reference identity where possible;
- detect metadata mismatch;
- detect unresolved references;
- detect bibliography/in-text inconsistencies;
- flag questionable relevance for review;
- output verified bibliography.

Expected outputs:

```text
verification_report.json
references_verified.bib
```

The product SHALL expose flagged citation issues to the human before the publication package is marked final.

---

# 34. HITL Modes

Reuse upstream modes instead of defining a second HITL framework.

Product-supported modes:

| Mode | Product behavior |
|---|---|
| `full-auto` | no mandatory human interruption; draft/exploration only |
| `gate-only` | only major approval gates |
| `checkpoint` | pause at key writing boundaries |
| `step-by-step` | pause after every paper-writing stage |
| `co-pilot` | recommended production mode |
| `custom` | per-stage configuration |
| `express` | minimal high-value intervention if supported by pinned upstream |

Default:

```yaml
hitl:
  enabled: true
  mode: co-pilot
```

For real publication workflow, the product SHOULD require final human approval even when upstream is capable of full automation, unless the user explicitly changes this policy.

---

# 35. Recommended HITL Policy for Paper-Only Mode

```yaml
paper_only:
  stage_policies:

    16:
      pause_after: true
      require_approval: true
      allow_edit_output: true
      allow_inject_prompt: true

    17:
      enable_collaboration: true
      pause_after: true
      allow_edit_output: true
      allow_inject_prompt: true

    18:
      pause_after: true
      require_approval: false

    19:
      pause_after: false

    20:
      require_approval: true
      pause_after: true

    23:
      pause_after: true
```

Exact configuration keys should follow the pinned upstream implementation rather than introduce incompatible equivalents.

---

# 36. Product State Model

```text
CREATED
   ↓
INPUT_VALIDATING
   ↓
INPUT_READY
   ↓
OUTLINE_GENERATING
   ↓
OUTLINE_REVIEW
   ↓
OUTLINE_APPROVED
   ↓
DRAFTING
   ↓
DRAFT_REVIEW
   ↓
PEER_REVIEW
   ↓
REVIEW_TRIAGE
   ↓
REVISING
   ↓
QUALITY_GATE
   ↓
FINAL_APPROVAL
   ↓
CITATION_VERIFY
   ↓
EXPORTING
   ↓
COMPLETED
```

Rollback:

```text
FINAL_APPROVAL → REVISING
FINAL_APPROVAL → OUTLINE_REVIEW
QUALITY_GATE → OUTLINE_REVIEW or REVISING
CITATION_VERIFY → REVISING
```

Reuse upstream resume/version/snapshot capabilities for persistence.

---

# 37. Output Package

Recommended final package:

```text
deliverables/
├── paper_final.md
├── paper.tex
├── paper.pdf                  # when compilation available
├── references.bib
├── references_verified.bib
│
├── figures/
├── tables/
│
├── reports/
│   ├── input_validation_report.json
│   ├── quality_report.json
│   ├── verification_report.json
│   └── claim_verification_report.json   # if available
│
├── history/
│   ├── outline.md
│   ├── paper_draft.md
│   ├── reviews.md
│   ├── paper_revised.md
│   └── revision_log.json
│
└── manifest.json
```

Primary user-facing deliverables:

1. `paper.pdf`
2. `paper.tex`
3. `paper_final.md`
4. `references_verified.bib`

---

# 38. Functional Requirements

## FR-001 — Create Paper Project

User can create a new paper-writing project.

## FR-002 — Upload Research Package

User can upload/import supported research files.

## FR-003 — Validate Input

System reports readiness, warnings, and blocking issues.

## FR-004 — Normalize Inputs

System converts heterogeneous input into an internal canonical representation.

## FR-005 — Build AutoResearchClaw Compatibility Context

System creates the inputs required for Stages 16–23.

## FR-006 — Start at Stage 16

System can execute paper writing without running Stages 1–15.

## FR-007 — Generate Outline

Reuse Stage 16.

## FR-008 — Human Outline Approval

Human can edit, approve, reject, regenerate.

## FR-009 — Generate Draft

Reuse Stage 17.

## FR-010 — Co-Writer

Reuse/extend upstream Paper Co-Writer.

## FR-011 — Section Locking

Product extension: human may lock sections from automatic revision.

## FR-012 — Evidence/Number Guard

Reuse VerifiedRegistry/anti-fabrication.

## FR-013 — Peer Review

Reuse Stage 18.

## FR-014 — Review Triage

Human can accept/reject/defer comments.

## FR-015 — Revise Paper

Reuse Stage 19.

## FR-016 — Quality Gate

Reuse Stage 20.

## FR-017 — Human Final Approval

Required by default.

## FR-018 — Export

Reuse Stage 22.

## FR-019 — Citation Verification

Reuse Stage 23.

## FR-020 — Resume

Interrupted projects can resume from the last valid state.

## FR-021 — Version History

Human and AI edits are traceable.

## FR-022 — Guidance Injection

Human can add instructions before relevant stages.

## FR-023 — LLM Provider Configuration

Reuse upstream configuration/provider abstraction.

## FR-024 — Cost Guardrails

Reuse upstream cost monitoring where applicable.

---

# 39. Canonical Internal Model

Only create an internal canonical model if required for the external input adapter.

It should remain small.

```text
PaperProject
ResearchContext
ResearchQuestion[]
Hypothesis[]
LiteratureSource[]
Methodology
Experiment[]
Result[]
Claim[]
Figure[]
Table[]
PublicationTarget
WritingInstruction[]
```

The canonical model is not intended to replace AutoResearchClaw's internal data model.

Its job is to normalize external data and then map it into upstream-compatible artifacts.

---

# 40. Proposed Manifest

Example `manifest.yaml`:

```yaml
schema_version: "1.0"

project:
  id: PAPER-001
  title: "..."
  domain: "machine-learning"

research:
  context: research/context.md
  questions: research/research_questions.yaml
  hypotheses: research/hypotheses.yaml
  contributions: research/contributions.md

literature:
  bibliography: literature/references.bib
  notes: literature/literature_notes.md
  paper_directory: literature/papers/

methodology:
  document: methodology/methodology.md
  config: methodology/experiment_config.yaml
  architecture: methodology/architecture.pdf

results:
  summary: results/experiment_summary.json
  metrics:
    - results/metrics.csv
  statistics:
    - results/statistical_tests.csv
  analysis: results/analysis.md

claims:
  file: claims/claims.yaml

figures:
  directory: figures/

tables:
  directory: tables/

publication:
  config: publication/target.yaml

writing:
  instructions: publication/writing_instructions.yaml
```

---

# 41. Product Architecture

```text
┌──────────────────────────────────────────────┐
│                 Web / CLI UI                 │
└──────────────────────┬───────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────┐
│          Paper Project Application Layer     │
│                                              │
│  Project / Upload / Status / HITL / Export   │
└──────────────────────┬───────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────┐
│          External Package Adapter            │
│                                              │
│ Intake → Validate → Normalize → ARC Context  │
└──────────────────────┬───────────────────────┘
                       │
                       ▼
╔══════════════════════════════════════════════╗
║          AutoResearchClaw Core               ║
║                                              ║
║  HITL / Stage Policies / SmartPause          ║
║  VerifiedRegistry / Claim Verification       ║
║  Stage 16 Paper Outline                      ║
║  Stage 17 Paper Draft                        ║
║  Stage 18 Peer Review                        ║
║  Stage 19 Revision                           ║
║  Stage 20 Quality Gate                       ║
║  Stage 21 Archive                            ║
║  Stage 22 Export                             ║
║  Stage 23 Citation Verify                    ║
║  Resume / Artifacts / Snapshots / Config     ║
╚══════════════════════╤═══════════════════════╝
                       │
                       ▼
┌──────────────────────────────────────────────┐
│               Deliverables                  │
│ MD / TEX / PDF / BIB / Reports / History    │
└──────────────────────────────────────────────┘
```

---

# 42. Reuse Matrix

| Capability | Approach | Build new? |
|---|---|---:|
| LLM configuration | AutoResearchClaw | No |
| Pipeline runner | AutoResearchClaw wrapper | No |
| Stage 16 outline | AutoResearchClaw | No |
| Stage 17 draft | AutoResearchClaw | No |
| Paper Co-Writer | AutoResearchClaw HITL | No |
| HITL policies | AutoResearchClaw | No |
| SmartPause | AutoResearchClaw | No |
| human guidance injection | AutoResearchClaw | No |
| snapshots/version behavior | AutoResearchClaw | No |
| resume | AutoResearchClaw | No |
| experiment number verification | VerifiedRegistry | No, adapt loader |
| claim verification | AutoResearchClaw | No, extend only if required |
| peer review | Stage 18 | No |
| revision | Stage 19 | No |
| quality gate | Stage 20 | No |
| archive | Stage 21 | No |
| LaTeX export | Stage 22 | No |
| citation verify | Stage 23 | No |
| bibliography output | AutoResearchClaw | No |
| input package validation | product adapter | **Yes** |
| external file normalization | product adapter | **Yes** |
| ARC compatibility mapping | product adapter | **Yes** |
| paper-only execution wrapper | thin wrapper | **Yes** |
| section lock UI metadata | product layer | Small extension |
| review triage UI | product layer | Small extension |
| project dashboard | product layer | Optional |
| DOCX export | adapter | Future |

---

# 43. Fork and Upstream Strategy

The product MUST maintain a low-divergence fork.

Recommended Git strategy:

```text
origin   = product fork
upstream = aiming-lab/AutoResearchClaw
```

Rules:

1. pin a known-good upstream commit for each product release;
2. preserve upstream architecture;
3. avoid editing upstream Stage 16–23 core unless necessary;
4. place product logic in clearly separated modules;
5. upstream-compatible patches should be contributed upstream when appropriate;
6. maintain contract tests for the compatibility adapter;
7. run regression tests when rebasing/upgrading upstream.

Suggested logical directory additions:

```text
product/
  paper_only/
    intake/
    normalization/
    adapters/
    api/
    ui/
    tests/
```

Exact path should follow the actual fork conventions.

---

# 44. License and Attribution

AutoResearchClaw is distributed under the MIT license.

The implementation SHALL:

- retain applicable copyright/license notices;
- include the upstream MIT license;
- document significant modifications;
- preserve attribution;
- record the upstream commit/tag used by every released product version.

This PRD does not replace legal review for commercial distribution.

---

# 45. API Requirements

A web/API implementation MAY expose:

## Create project

```http
POST /paper-projects
```

## Upload package

```http
POST /paper-projects/{id}/inputs
```

## Validate

```http
POST /paper-projects/{id}/validate
```

## Start paper workflow

```http
POST /paper-projects/{id}/run
```

with:

```json
{
  "mode": "co-pilot",
  "start_stage": 16
}
```

## Get status

```http
GET /paper-projects/{id}/status
```

## Submit human guidance

```http
POST /paper-projects/{id}/guidance
```

## Approve/reject stage

```http
POST /paper-projects/{id}/stages/{stage}/decision
```

## Download deliverables

```http
GET /paper-projects/{id}/deliverables
```

These APIs should wrap upstream functionality rather than duplicate the pipeline state machine.

---

# 46. User Interface Requirements

MVP UI:

### Project Screen

- paper title;
- status;
- target venue;
- current stage;
- current HITL request.

### Input Screen

- upload files;
- detected data categories;
- readiness report;
- warnings/errors.

### Outline Screen

- editable outline;
- regenerate section;
- approve.

### Co-Writer Screen

- manuscript navigation;
- section editor;
- AI actions;
- section lock;
- guidance input;
- version comparison.

### Review Screen

- reviewer comments;
- accept/reject/defer;
- author response.

### Quality Screen

- quality score/report;
- required actions;
- final approve/return.

### Export Screen

- Markdown;
- LaTeX;
- PDF;
- bibliography;
- verification report.

---

# 47. Non-Functional Requirements

## NFR-01 — Reproducibility

Record:

- product version;
- upstream AutoResearchClaw commit;
- config;
- prompts/custom skills where applicable;
- input manifest checksum;
- artifact checksums where available.

## NFR-02 — Recoverability

A job must resume after interruption without restarting completed writing stages unnecessarily.

Reuse upstream resume behavior.

## NFR-03 — Auditability

Record:

- AI-generated changes;
- human edits;
- approvals;
- rejections;
- guidance;
- review triage;
- final approval.

## NFR-04 — Data Integrity

Original uploaded research inputs must remain immutable.

Derived normalized copies may be regenerated.

## NFR-05 — Provider Independence

Reuse the upstream LLM abstraction to avoid hard-coding a single provider.

## NFR-06 — Cost Control

Expose upstream cost budget controls where available.

## NFR-07 — Privacy

Private research content should not be sent to services not explicitly configured by the user.

The product must clearly show which LLM/external verification services will receive content.

---

# 48. Safety / Scientific Integrity Requirements

## SI-01

Never fabricate experimental measurements.

## SI-02

Never silently replace supplied scientific results.

## SI-03

Never claim statistical significance unless supported by supplied/verified analysis.

## SI-04

Flag unsupported citations.

## SI-05

Flag unsupported empirical claims.

## SI-06

Human final approval is required by default.

## SI-07

AI review scores are advisory, not publication decisions.

---

# 49. MVP Scope

## MVP Must Have

1. fork/pin AutoResearchClaw;
2. Research Package intake;
3. input validator;
4. normalization adapter;
5. compatibility adapter;
6. paper-only runner starting at Stage 16;
7. Stage 16 outline;
8. HITL outline approval;
9. Stage 17 draft;
10. Paper Co-Writer;
11. VerifiedRegistry loading from external results;
12. Stage 18 peer review;
13. review triage;
14. Stage 19 revision;
15. Stage 20 quality gate;
16. final human approval;
17. Stage 22 Markdown/LaTeX export;
18. Stage 23 citation verification;
19. project resume;
20. version/snapshot history.

Stage 21 archive should remain enabled if it does not create significant integration friction.

## MVP Should Have

- figures/tables ingestion;
- target venue configuration;
- LaTeX-to-PDF compilation;
- claim verification report;
- diff view;
- section locking.

## MVP Will Not Have

- experiment execution;
- automated research planning;
- experiment code generation;
- HPC orchestration;
- full collaborative multi-user editing;
- general-purpose knowledge graph;
- custom Word layout engine.

---

# 50. Phase 2

Potential additions:

- broader journal templates;
- DOCX output;
- Overleaf integration if upstream support is stable;
- collaborative author comments;
- reviewer rebuttal / response letter;
- resubmission workflow;
- journal switching;
- author style memory;
- richer evidence-to-sentence traceability;
- external API/webhook ingestion;
- connectors to research repositories.

Prefer upstream features when they become available.

---

# 51. Acceptance Criteria

## AC-01 — External-only research

Given a research package with methodology, results, and references, the system can produce a manuscript without executing AutoResearchClaw Stages 1–15.

## AC-02 — No experiment execution

No experiment code is executed as part of the paper-only workflow.

## AC-03 — Stage reuse

Stages 16–23 execute using upstream or minimally modified AutoResearchClaw implementation.

## AC-04 — Outline HITL

User can edit and approve outline before drafting.

## AC-05 — Co-writing

User can edit at least one section and continue the workflow without losing edits.

## AC-06 — Number integrity

A generated empirical number that is not present in verified input data is blocked, sanitized, or flagged.

## AC-07 — Peer review

The pipeline generates multiple reviewer perspectives and exposes them to the user.

## AC-08 — Review triage

User decisions about reviewer comments are persisted and used in revision.

## AC-09 — Final approval

Final manuscript cannot enter “approved final” status without explicit human approval under the default production policy.

## AC-10 — Citation verification

A citation verification report is included in deliverables.

## AC-11 — Export

At minimum the product exports:

- Markdown;
- LaTeX;
- BibTeX.

PDF must be exported when a LaTeX compiler is available.

## AC-12 — Resume

An interrupted project resumes from persisted state.

## AC-13 — Provenance

Final manifest records the AutoResearchClaw upstream version/commit used.

---

# 52. Test Strategy

## 52.1 Upstream Regression Tests

Run existing AutoResearchClaw tests for the pinned version.

Product changes must not break core upstream behavior.

## 52.2 Adapter Contract Tests

Test input packages:

- minimum package;
- full evidence-rich package;
- missing result package;
- broken bibliography;
- missing figure;
- malformed CSV;
- unsupported type.

## 52.3 Anti-Fabrication Tests

Seed known metrics and assert generated paper does not invent alternative numbers.

## 52.4 HITL Tests

Test:

- approve;
- reject;
- edit;
- guidance;
- regenerate;
- section lock;
- resume after pause.

## 52.5 Citation Tests

Test real, missing, duplicate, malformed and mismatched bibliography entries.

## 52.6 End-to-End Golden Project

Maintain at least one fixed research package with expected:

- outline;
- section structure;
- known results;
- known references;
- final deliverable layout.

---

# 53. Risks and Mitigations

## Risk 1 — Upstream changes internal artifact schemas

Mitigation:

- pin upstream versions;
- adapter contract tests;
- upgrade only after compatibility validation.

## Risk 2 — Over-forking AutoResearchClaw

Mitigation:

- wrappers/adapters before core modifications;
- minimal patch surface;
- separate product modules.

## Risk 3 — Paper writer expects artifacts normally generated by Stages 1–15

Mitigation:

- compatibility adapter;
- fixture tests;
- populate upstream context rather than rewriting Stage 16.

## Risk 4 — External result schemas vary greatly

Mitigation:

- canonical intake model;
- plugin parser architecture;
- manifest-based explicit mapping.

## Risk 5 — Hallucinated claims

Mitigation:

- VerifiedRegistry;
- claim verification;
- required human approval;
- evidence-rich input level.

## Risk 6 — Citation APIs unavailable

Mitigation:

- mark verification status;
- do not silently mark citations verified;
- allow human resolution.

## Risk 7 — Upstream prompts optimized for autonomous pipeline assumptions

Mitigation:

- custom prompt/config layer;
- keep upstream writer code;
- inject external-context instructions.

---

# 54. Implementation Priorities

## P0 — Foundation

- fork/pin upstream;
- understand Stage 16–23 input contracts;
- build adapter fixtures;
- get Stage 16–23 to run using external sample data.

## P1 — Product MVP

- intake API/UI;
- validation;
- co-pilot flow;
- paper-only runner;
- verified result import;
- deliverables.

## P2 — Publication UX

- section lock/diff;
- journal selection;
- PDF compile;
- review triage UI.

## P3 — Advanced Integration

- richer external resource connectors;
- team collaboration;
- reviewer rebuttal;
- venue switching.

---

# 55. Engineering Definition of Done

The product is considered technically ready for MVP when:

```text
External Research Package
        ↓
paper-only adapter
        ↓
AutoResearchClaw Stage 16
        ↓
human edits outline
        ↓
AutoResearchClaw Stage 17
        ↓
human co-writes sections
        ↓
AutoResearchClaw Stage 18
        ↓
human triages review
        ↓
AutoResearchClaw Stage 19
        ↓
AutoResearchClaw Stage 20
        ↓
human final approval
        ↓
AutoResearchClaw Stage 22
        ↓
AutoResearchClaw Stage 23
        ↓
paper.md + paper.tex + bibliography + reports
```

with no experiment executed internally and no unverified empirical number silently introduced.

---

# 56. Product Decision Summary

The key architectural decision is:

> **Do not extract the idea of AutoResearchClaw and rewrite it. Use AutoResearchClaw itself as the writing engine.**

New code should be limited primarily to:

```text
External Input
    ↓
Validation
    ↓
Normalization
    ↓
Compatibility Adapter
    ↓
Paper-Only Runner
    ↓
Product UI/API
```

while the scientific writing pipeline remains:

```text
AutoResearchClaw
Stage 16 → 17 → 18 → 19 → 20 → 21 → 22 → 23
```

This minimizes engineering cost, preserves the upstream anti-fabrication/HITL/export capabilities, and makes it possible to continue benefiting from future AutoResearchClaw improvements.

---

# 57. Upstream Reference Baseline

Implementation team should review and pin the corresponding upstream files before development:

- `README.md`
- `RESEARCHCLAW_CLAUDE.md`
- `docs/integration-guide.md`
- `docs/HITL_GUIDE.md`
- `docs/DOMAIN_INTEGRATION_GUIDE.md`
- `config.researchclaw.example.yaml`
- `pyproject.toml`
- relevant implementation under `researchclaw/`
- relevant HITL implementation under `researchclaw/hitl/`
- upstream tests related to HITL, writing, verification, export, and resume.

Baseline product assumptions from upstream include:

- 23-stage pipeline;
- Stages 16–19 dedicated to Paper Writing;
- Stages 20–23 dedicated to finalization;
- Paper Co-Writer with section-by-section human collaboration;
- multiple HITL intervention modes;
- claim/anti-fabrication mechanisms;
- LaTeX/template export;
- citation verification;
- artifact versioning/checksums/resume features;
- MIT license.

Before coding, the team SHALL record the exact upstream commit hash in the product repository.

---

# 58. Final Product Principle

The module should only need to know:

```text
WHAT was studied
WHY it was studied
HOW it was studied
WHAT results were obtained
WHAT references support the narrative
WHAT constraints the target publication imposes
WHAT the human author approves
```

It should not need to know:

```text
WHERE the experiment ran
HOW external infrastructure was orchestrated
HOW long the experiment took
WHICH external platform generated the artifacts
```

As long as the research package satisfies the input contract, the same writing workflow can be reused for different research domains and execution environments.

