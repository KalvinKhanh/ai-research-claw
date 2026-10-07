"""23-stage ResearchClaw pipeline state machine.

Defines the stage sequence, status transitions, gate logic, and rollback rules.
Migrated from arc/state_machine.py (19 stages) with the following changes:
  - SEARCH_PLAN + SOURCE_CONNECT → SEARCH_STRATEGY
  - RELEVANCE_SCREEN + QUALITY_SCREEN → LITERATURE_SCREEN
  - CLUSTER_TOPICS + GAP_ANALYSIS → SYNTHESIS
  - EXPERIMENT_DESIGN split → EXPERIMENT_DESIGN + CODE_GENERATION
  - EXECUTE split → EXPERIMENT_RUN + ITERATIVE_REFINE
  - WRITE_DRAFT split → PAPER_OUTLINE + PAPER_DRAFT
  - Added PAPER_REVISION, QUALITY_GATE, EXPORT_PUBLISH
  - RETROSPECTIVE_ARCHIVE split → KNOWLEDGE_ARCHIVE (+ QUALITY_GATE + EXPORT_PUBLISH)
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, IntEnum
from typing import Iterable


class Stage(IntEnum):
    """8-stage research pipeline (idea2hypothesis)."""

    # Phase A: Research Scoping
    TOPIC_INIT = 1
    PROBLEM_DECOMPOSE = 2

    # Phase B: Literature Discovery
    SEARCH_STRATEGY = 3
    LITERATURE_COLLECT = 4
    LITERATURE_SCREEN = 5  # GATE
    KNOWLEDGE_EXTRACT = 6

    # Phase C: Knowledge Synthesis
    SYNTHESIS = 7
    HYPOTHESIS_GEN = 8


class StageStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    BLOCKED_APPROVAL = "blocked_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    PAUSED = "paused"
    RETRYING = "retrying"
    FAILED = "failed"
    DONE = "done"


class TransitionEvent(str, Enum):
    START = "start"
    SUCCEED = "succeed"
    APPROVE = "approve"
    REJECT = "reject"
    TIMEOUT = "timeout"
    FAIL = "fail"
    RETRY = "retry"
    RESUME = "resume"
    PAUSE = "pause"


# ---------------------------------------------------------------------------
# Stage navigation
# ---------------------------------------------------------------------------

STAGE_SEQUENCE: tuple[Stage, ...] = tuple(Stage)

NEXT_STAGE: dict[Stage, Stage | None] = {
    stage: STAGE_SEQUENCE[idx + 1] if idx + 1 < len(STAGE_SEQUENCE) else None
    for idx, stage in enumerate(STAGE_SEQUENCE)
}

PREVIOUS_STAGE: dict[Stage, Stage | None] = {
    stage: STAGE_SEQUENCE[idx - 1] if idx > 0 else None
    for idx, stage in enumerate(STAGE_SEQUENCE)
}

# ---------------------------------------------------------------------------
# Gate stages — require approval before proceeding
# ---------------------------------------------------------------------------

GATE_STAGES: frozenset[Stage] = frozenset(
    {
        Stage.LITERATURE_SCREEN,
    }
)

# Gate rollback targets: when a gate rejects, where to roll back
GATE_ROLLBACK: dict[Stage, Stage] = {
    Stage.LITERATURE_SCREEN: Stage.LITERATURE_COLLECT,  # reject → re-collect
}

# ---------------------------------------------------------------------------
# Research decision rollback targets (unused in 8-stage pipeline)
# ---------------------------------------------------------------------------

DECISION_ROLLBACK: dict[str, Stage] = {}

MAX_DECISION_PIVOTS: int = 2

# ---------------------------------------------------------------------------
# Noncritical stages — can be skipped on failure without aborting pipeline
# ---------------------------------------------------------------------------

NONCRITICAL_STAGES: frozenset[Stage] = frozenset()

# ---------------------------------------------------------------------------
# Phase groupings (for UI and reporting)
# ---------------------------------------------------------------------------

PHASE_MAP: dict[str, tuple[Stage, ...]] = {
    "A: Research Scoping": (Stage.TOPIC_INIT, Stage.PROBLEM_DECOMPOSE),
    "B: Literature Discovery": (
        Stage.SEARCH_STRATEGY,
        Stage.LITERATURE_COLLECT,
        Stage.LITERATURE_SCREEN,
        Stage.KNOWLEDGE_EXTRACT,
    ),
    "C: Knowledge Synthesis": (Stage.SYNTHESIS, Stage.HYPOTHESIS_GEN),
}


# ---------------------------------------------------------------------------
# Transition logic
# ---------------------------------------------------------------------------

TRANSITION_MAP: dict[StageStatus, frozenset[StageStatus]] = {
    StageStatus.PENDING: frozenset({StageStatus.RUNNING}),
    StageStatus.RUNNING: frozenset(
        {StageStatus.DONE, StageStatus.BLOCKED_APPROVAL, StageStatus.FAILED}
    ),
    StageStatus.BLOCKED_APPROVAL: frozenset(
        {StageStatus.APPROVED, StageStatus.REJECTED, StageStatus.PAUSED}
    ),
    StageStatus.APPROVED: frozenset({StageStatus.DONE}),
    StageStatus.REJECTED: frozenset({StageStatus.PENDING}),
    StageStatus.PAUSED: frozenset({StageStatus.RUNNING}),
    StageStatus.RETRYING: frozenset({StageStatus.RUNNING}),
    StageStatus.FAILED: frozenset({StageStatus.RETRYING, StageStatus.PAUSED}),
    StageStatus.DONE: frozenset(),
}


@dataclass(frozen=True)
class TransitionOutcome:
    stage: Stage
    status: StageStatus
    next_stage: Stage | None
    rollback_stage: Stage | None = None
    checkpoint_required: bool = False
    decision: str = "proceed"


def gate_required(
    stage: Stage,
    hitl_required_stages: Iterable[int] | None = None,
    *,
    profile: str | None = None,
) -> bool:
    """Check whether a stage requires human-in-the-loop approval."""
    if stage not in GATE_STAGES:
        return False
    if hitl_required_stages is not None:
        return int(stage) in frozenset(hitl_required_stages)
    return True  # Default: all gate stages require approval


def default_rollback_stage(stage: Stage) -> Stage:
    """Return the configured rollback target, or the previous stage."""
    return GATE_ROLLBACK.get(stage) or PREVIOUS_STAGE.get(stage) or stage


def advance(
    stage: Stage,
    status: StageStatus,
    event: TransitionEvent | str,
    *,
    hitl_required_stages: Iterable[int] | None = None,
    rollback_stage: Stage | None = None,
) -> TransitionOutcome:
    """Compute the next state given current stage, status, and event.

    Raises ValueError on unsupported transitions.
    """
    event = TransitionEvent(event)
    target_rollback = rollback_stage or default_rollback_stage(stage)

    # START → RUNNING
    if event is TransitionEvent.START and status in {
        StageStatus.PENDING,
        StageStatus.RETRYING,
        StageStatus.PAUSED,
    }:
        return TransitionOutcome(
            stage=stage, status=StageStatus.RUNNING, next_stage=stage
        )

    # SUCCEED while RUNNING
    if event is TransitionEvent.SUCCEED and status is StageStatus.RUNNING:
        if gate_required(stage, hitl_required_stages):
            return TransitionOutcome(
                stage=stage,
                status=StageStatus.BLOCKED_APPROVAL,
                next_stage=stage,
                checkpoint_required=False,
                decision="block",
            )
        return TransitionOutcome(
            stage=stage,
            status=StageStatus.DONE,
            next_stage=NEXT_STAGE[stage],
            checkpoint_required=True,
        )

    # APPROVE while BLOCKED
    if event is TransitionEvent.APPROVE and status is StageStatus.BLOCKED_APPROVAL:
        return TransitionOutcome(
            stage=stage,
            status=StageStatus.DONE,
            next_stage=NEXT_STAGE[stage],
            checkpoint_required=True,
        )

    # REJECT while BLOCKED → rollback
    if event is TransitionEvent.REJECT and status is StageStatus.BLOCKED_APPROVAL:
        return TransitionOutcome(
            stage=target_rollback,
            status=StageStatus.PENDING,
            next_stage=target_rollback,
            rollback_stage=target_rollback,
            checkpoint_required=True,
            decision="pivot",
        )

    # TIMEOUT while BLOCKED → pause
    if event is TransitionEvent.TIMEOUT and status is StageStatus.BLOCKED_APPROVAL:
        return TransitionOutcome(
            stage=stage,
            status=StageStatus.PAUSED,
            next_stage=stage,
            checkpoint_required=True,
            decision="block",
        )

    # FAIL while RUNNING
    if event is TransitionEvent.FAIL and status is StageStatus.RUNNING:
        return TransitionOutcome(
            stage=stage,
            status=StageStatus.FAILED,
            next_stage=stage,
            checkpoint_required=True,
            decision="retry",
        )

    # RETRY while FAILED
    if event is TransitionEvent.RETRY and status is StageStatus.FAILED:
        return TransitionOutcome(
            stage=stage,
            status=StageStatus.RETRYING,
            next_stage=stage,
            decision="retry",
        )

    # RESUME while PAUSED
    if event is TransitionEvent.RESUME and status is StageStatus.PAUSED:
        return TransitionOutcome(
            stage=stage, status=StageStatus.RUNNING, next_stage=stage
        )

    # PAUSE while FAILED
    if event is TransitionEvent.PAUSE and status is StageStatus.FAILED:
        return TransitionOutcome(
            stage=stage,
            status=StageStatus.PAUSED,
            next_stage=stage,
            checkpoint_required=True,
            decision="block",
        )

    raise ValueError(
        f"Unsupported transition: {status.value} + {event.value} for stage {int(stage)}"
    )
