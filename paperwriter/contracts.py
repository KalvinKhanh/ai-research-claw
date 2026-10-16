"""Input bundle and stage contracts for the PaperWriter service."""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum


class WriterStage(IntEnum):
    INTAKE = 1
    OUTLINE = 2  # GATE
    DRAFT = 3
    REVIEW = 4
    REVISE = 5
    EXPORT = 6  # GATE


WRITER_GATES: frozenset[WriterStage] = frozenset({WriterStage.OUTLINE, WriterStage.EXPORT})


@dataclass(frozen=True)
class BundleFile:
    """One artifact of the engine run dir consumed by the writer."""

    path: str  # relative to engine run dir
    required: bool = True


# Artifacts produced by the 8-stage engine (see researchclaw/pipeline/contracts.py).
INPUT_BUNDLE: tuple[BundleFile, ...] = (
    BundleFile("stage-01/goal.md"),
    BundleFile("stage-02/problem_tree.md"),
    BundleFile("stage-05/shortlist.jsonl"),
    BundleFile("stage-06/cards/"),
    BundleFile("stage-07/synthesis.md"),
    BundleFile("stage-08/hypotheses.md"),
    BundleFile("stage-08/novelty_report.json", required=False),
    # Optional future hook: experiment results from a separate experiment system.
    BundleFile("results/", required=False),
)


@dataclass(frozen=True)
class WriterStageContract:
    stage: WriterStage
    input_files: tuple[str, ...]
    output_files: tuple[str, ...]
    dod: str
    error_code: str
    max_retries: int = 1


WRITER_CONTRACTS: dict[WriterStage, WriterStageContract] = {
    WriterStage.INTAKE: WriterStageContract(
        WriterStage.INTAKE, (), ("evidence_index.json", "bundle_manifest.json"),
        "Bundle validated; every hypothesis linked to >=1 paper id", "W01_BUNDLE_INVALID", 0),
    WriterStage.OUTLINE: WriterStageContract(
        WriterStage.OUTLINE, ("evidence_index.json",), ("outline.md",),
        "IMRaD outline with each section bound to evidence ids", "W02_OUTLINE_BAD"),
    WriterStage.DRAFT: WriterStageContract(
        WriterStage.DRAFT, ("outline.md",), ("paper_draft.md",),
        "All sections drafted with citations from shortlist only", "W03_DRAFT_FAIL"),
    WriterStage.REVIEW: WriterStageContract(
        WriterStage.REVIEW, ("paper_draft.md",), ("reviews.json",),
        "Multi-reviewer feedback + claim-vs-evidence check", "W04_REVIEW_FAIL"),
    WriterStage.REVISE: WriterStageContract(
        WriterStage.REVISE, ("paper_draft.md", "reviews.json"), ("paper_revised.md",),
        "Review findings addressed; length guard passed", "W05_REVISE_FAIL"),
    WriterStage.EXPORT: WriterStageContract(
        WriterStage.EXPORT, ("paper_revised.md",),
        ("paper.tex", "references.bib", "verification_report.json"),
        "LaTeX + BibTeX produced; all citations verified", "W06_EXPORT_FAIL", 0),
}
