from __future__ import annotations

import json
import logging
import math
import re
import time as _time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import yaml

from researchclaw.adapters import AdapterBundle
from researchclaw.config import RCConfig
from researchclaw.llm import create_llm_client
from researchclaw.llm.client import LLMClient
from researchclaw.prompts import PromptManager
from researchclaw.pipeline.stages import (
    Stage,
    StageStatus,
    TransitionEvent,
    TransitionOutcome,
    advance,
    gate_required,
)
from researchclaw.pipeline.contracts import CONTRACTS, StageContract

logger = logging.getLogger(__name__)


from researchclaw.pipeline._domain import _prompt_bank_domain_from_config  # noqa: E402
from researchclaw.pipeline._helpers import (  # noqa: E402
    StageResult,
    _read_prior_artifact,
    _utcnow_iso,
    _write_stage_meta,
)
from researchclaw.pipeline.stage_impls._paper_writing import (  # noqa: E402
    _execute_paper_draft,
    _execute_paper_outline,
)

# ---------------------------------------------------------------------------
# Stages 18-23 (extracted to stage_impls/_review_publish.py)
# ---------------------------------------------------------------------------
from researchclaw.pipeline.stage_impls._review_publish import (  # noqa: E402
    _execute_peer_review,
    _execute_paper_revision,
    _execute_quality_gate,
    _execute_export_publish,
    _execute_citation_verify,
    _sanitize_fabricated_data,
    _collect_experiment_evidence,
    _check_citation_relevance,
    _remove_bibtex_entries,
    _remove_citations_from_text,
)


def _get_hitl_session(adapters: AdapterBundle) -> Any:
    """Retrieve the HITLSession from the adapter bundle (if any)."""
    return getattr(adapters, "hitl", None)


def _run_hitl_pre_stage(
    stage: Stage, run_dir: Path, adapters: AdapterBundle,
    config: RCConfig | None = None,
) -> StageResult | None:
    """HITL pre-stage hook: pause before execution if policy requires.

    Returns a StageResult to skip the stage, or None to proceed normally.
    """
    session = _get_hitl_session(adapters)
    if session is None:
        return None

    stage_num = int(stage)
    if not session.should_pause_before(stage_num):
        return None

    from researchclaw.hitl.intervention import HumanAction, PauseReason

    # Collect output file names from contract (mode-aware: collider_agent → collider_plan.md)
    contract = CONTRACTS.get(stage)
    output_files = tuple(contract.output_files) if contract else ()

    session.pause(
        stage_num,
        stage.name,
        PauseReason.PRE_STAGE,
        context_summary=f"About to execute {stage.name}",
        output_files=output_files,
    )
    human_input = session.wait_for_human()

    if human_input.action == HumanAction.SKIP:
        return StageResult(
            stage=stage,
            status=StageStatus.DONE,
            artifacts=(),
            decision="proceed",
        )
    if human_input.action == HumanAction.ABORT:
        return StageResult(
            stage=stage,
            status=StageStatus.FAILED,
            artifacts=(),
            error="Aborted by user",
            decision="abort",
        )

    # Inject guidance if provided
    if human_input.guidance:
        stage_dir = run_dir / f"stage-{stage_num:02d}"
        stage_dir.mkdir(parents=True, exist_ok=True)
        guidance_file = stage_dir / "hitl_guidance.md"
        guidance_file.write_text(human_input.guidance, encoding="utf-8")

    return None  # Proceed with execution


def _run_hitl_post_stage(
    stage: Stage, result: StageResult, run_dir: Path, adapters: AdapterBundle,
    config: RCConfig | None = None,
) -> StageResult:
    """HITL post-stage hook: pause after execution for review.

    Returns the (possibly modified) StageResult.
    """
    session = _get_hitl_session(adapters)
    if session is None:
        return result

    # --- CostGuard: check budget thresholds ---
    stage_num = int(stage)
    try:
        from researchclaw.hitl.cost_guard import CostGuard

        budget = 0.0
        if hasattr(session, "config") and session.config:
            budget = getattr(session.config, "cost_budget_usd", 0.0) or 0.0
        guard = CostGuard(budget_usd=budget)
        if budget > 0 and guard.should_pause(run_dir):
            from researchclaw.hitl.intervention import HumanAction, PauseReason

            session.pause(
                stage_num,
                stage.name,
                PauseReason.COST_BUDGET_EXCEEDED,
                context_summary=f"Cost budget alert: {guard.format_display(run_dir)}",
            )
            human_input = session.wait_for_human()
            if human_input.action == HumanAction.ABORT:
                return StageResult(
                    stage=stage,
                    status=StageStatus.FAILED,
                    artifacts=result.artifacts,
                    error="Aborted due to cost",
                    decision="abort",
                )
    except Exception as _cg_exc:
        logger.debug("CostGuard check skipped: %s", _cg_exc)

    _smart_pause_triggered = False
    if not session.should_pause_after(stage_num):
        # Policy doesn't require pause, but SmartPause might
        try:
            from researchclaw.hitl.smart_pause import SmartPause

            sp = SmartPause(threshold=0.7, run_dir=run_dir)
            q_score = None
            stage_dir = run_dir / f"stage-{stage_num:02d}"
            prm_file = stage_dir / "prm_score.json"
            if prm_file.exists():
                import json as _sp_json

                prm_data = _sp_json.loads(prm_file.read_text(encoding="utf-8"))
                q_score = prm_data.get("prm_score")
            should_smart_pause, _signal = sp.should_pause(
                stage_num, stage.name, quality_score=q_score
            )
            if not should_smart_pause:
                return result
            # SmartPause triggered — fall through to pause logic
            _smart_pause_triggered = True
        except Exception as _sp_exc:
            logger.debug("SmartPause check skipped: %s", _sp_exc)
            return result

    from researchclaw.hitl.intervention import HumanAction, PauseReason

    # Determine pause reason
    reason = PauseReason.CONFIDENCE_LOW if _smart_pause_triggered else PauseReason.POST_STAGE
    policy = session.get_policy(stage_num)
    if policy.require_approval:
        reason = PauseReason.GATE_APPROVAL
    if (
        policy.min_quality_score > 0
        and result.status == StageStatus.DONE
    ):
        # Check quality score from stage health
        stage_dir = run_dir / f"stage-{stage_num:02d}"
        try:
            import json as _json_mod
            health_file = stage_dir / "stage_health.json"
            if health_file.exists():
                health = _json_mod.loads(health_file.read_text(encoding="utf-8"))
                prm_file = stage_dir / "prm_score.json"
                if prm_file.exists():
                    prm = _json_mod.loads(prm_file.read_text(encoding="utf-8"))
                    score = prm.get("prm_score", 1.0)
                    if score < policy.min_quality_score:
                        reason = PauseReason.QUALITY_BELOW_THRESHOLD
        except (OSError, ValueError):
            pass

    # Build context summary from stage artifacts
    contract = CONTRACTS.get(stage)
    output_files = tuple(contract.output_files) if contract else ()
    context_lines = [
        f"Stage {stage_num} ({stage.name}) completed: {result.status.value}",
    ]
    if result.artifacts:
        context_lines.append(f"Artifacts: {', '.join(result.artifacts)}")
    if result.error:
        context_lines.append(f"Error: {result.error}")

    # Read first 500 chars of key output files for summary
    stage_dir = run_dir / f"stage-{stage_num:02d}"
    for fname in output_files[:3]:
        fpath = stage_dir / fname
        if fpath.is_file():
            try:
                text = fpath.read_text(encoding="utf-8")[:500]
                context_lines.append(f"\n--- {fname} ---\n{text}")
            except (OSError, UnicodeDecodeError):
                pass

    session.pause(
        stage_num,
        stage.name,
        reason,
        context_summary="\n".join(context_lines),
        output_files=output_files,
    )
    human_input = session.wait_for_human()

    if human_input.action == HumanAction.APPROVE:
        return result

    if human_input.action == HumanAction.REJECT:
        return StageResult(
            stage=stage,
            status=StageStatus.REJECTED,
            artifacts=result.artifacts,
            error=human_input.message or "Rejected by human reviewer",
            decision="pivot",
            evidence_refs=result.evidence_refs,
        )

    if human_input.action == HumanAction.EDIT:
        # Human already edited files via the adapter
        return result

    if human_input.action == HumanAction.SKIP:
        return StageResult(
            stage=stage,
            status=StageStatus.DONE,
            artifacts=result.artifacts,
            decision="proceed",
            evidence_refs=result.evidence_refs,
        )

    if human_input.action == HumanAction.ABORT:
        return StageResult(
            stage=stage,
            status=StageStatus.FAILED,
            artifacts=result.artifacts,
            error="Aborted by user",
            decision="abort",
            evidence_refs=result.evidence_refs,
        )

    if human_input.action == HumanAction.COLLABORATE:
        session.enter_collaboration(stage_num, stage.name)
        try:
            result = _run_collaboration_loop(
                stage, result, run_dir, adapters, session, config=config
            )
        except Exception as _collab_exc:
            logger.warning("Collaboration failed: %s", _collab_exc)
        session.exit_collaboration()
        return result

    if human_input.action == HumanAction.INJECT:
        # Save guidance for potential re-run
        if human_input.guidance:
            guidance_file = stage_dir / "hitl_guidance.md"
            guidance_file.write_text(human_input.guidance, encoding="utf-8")
        return result

    return result


def _run_collaboration_loop(
    stage: Stage,
    result: StageResult,
    run_dir: Path,
    adapters: AdapterBundle,
    session: Any,
    *,
    config: RCConfig | None = None,
) -> StageResult:
    """Run an interactive collaboration loop for a stage.

    The human and AI take turns discussing and refining the stage output.
    The loop continues until the human approves or aborts.
    """
    from researchclaw.hitl.collaboration import CollaborationSession
    from researchclaw.hitl.intervention import HumanAction, PauseReason

    stage_num = int(stage)
    contract = CONTRACTS.get(stage)
    output_files = tuple(contract.output_files) if contract else ()

    collab = CollaborationSession(run_dir=run_dir)

    # Try to get LLM client and topic
    llm_client = None
    topic = ""
    try:
        if config is not None:
            from researchclaw.llm import create_llm_client
            llm_client = create_llm_client(config)
            topic_obj = getattr(config, "research", None)
            topic = topic_obj.topic if topic_obj else "Research"
        else:
            topic = "Research"
    except Exception:
        topic = "Research"

    collab.initialize(
        stage_num, stage.name, topic, run_dir, artifacts=output_files,
    )

    print(f"\n  Entering collaboration mode for Stage {stage_num} ({stage.name})")
    print("  Commands: 'done' finalize | 'abort' cancel | 'show <file>' view | 'edit <file>' edit | 'files' list")
    print("  Or type a message to chat with AI.\n")

    # Simple collaboration loop via stdin
    while True:
        try:
            user_input = input("  You > ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not user_input:
            continue

        lower = user_input.lower()

        if lower in ("done", "approve", "finalize"):
            collab.finalize()
            print("  Collaboration finalized.")
            break

        if lower in ("abort", "quit", "cancel"):
            print("  Collaboration cancelled.")
            break

        # List available artifacts
        if lower == "files":
            for fname in collab.shared_artifacts:
                mod = " [modified]" if fname in collab._modified_artifacts else ""
                print(f"    {fname}{mod}")
            continue

        # Show artifact content
        if lower.startswith("show "):
            fname = user_input[5:].strip()
            if fname in collab.shared_artifacts:
                content = collab.shared_artifacts[fname]
                print(f"\n  --- {fname} ({len(content)} chars) ---")
                print(content[:3000])
                if len(content) > 3000:
                    print(f"  ... ({len(content) - 3000} chars truncated)")
                print(f"  --- end {fname} ---\n")
            else:
                print(f"  File not found: {fname}. Use 'files' to list available artifacts.")
            continue

        # Interactive edit: read from stdin until <<<END>>>
        if lower.startswith("edit "):
            fname = user_input[5:].strip()
            if fname not in collab.shared_artifacts:
                print(f"  File not found: {fname}. Use 'files' to list available artifacts.")
                continue
            print(f"  Editing {fname}. Paste new content, then type <<<END>>> on its own line:")
            lines = []
            while True:
                try:
                    line = input()
                except (EOFError, KeyboardInterrupt):
                    break
                if line.strip() == "<<<END>>>":
                    break
                lines.append(line)
            new_content = "\n".join(lines)
            collab.human_edits_artifact(fname, new_content)
            print(f"  [{fname} updated — {len(new_content)} chars written]")
            continue

        # Regular chat message
        collab.human_says(user_input)

        # Get AI response
        if llm_client is not None:
            rev_before = len(collab.revision_history)
            response = collab.ai_responds(llm_client)
            print(f"\n  AI > {response}\n")
            # Report any artifact edits the AI made
            for rev in collab.revision_history[rev_before:]:
                if rev.get("action") == "ai_proposal":
                    print(f"  [AI edited: {rev['file']}]")
        else:
            print("  AI > [LLM not available for chat — your input is recorded]\n")

    return result


_STAGE_EXECUTORS: dict[Stage, Callable[..., StageResult]] = {
    Stage.PAPER_OUTLINE: _execute_paper_outline,
    Stage.PAPER_DRAFT: _execute_paper_draft,
    Stage.PEER_REVIEW: _execute_peer_review,
    Stage.PAPER_REVISION: _execute_paper_revision,
    Stage.QUALITY_GATE: _execute_quality_gate,
    Stage.EXPORT_PUBLISH: _execute_export_publish,
    Stage.CITATION_VERIFY: _execute_citation_verify,
}


def execute_stage(
    stage: Stage,
    *,
    run_dir: Path,
    run_id: str,
    config: RCConfig,
    adapters: AdapterBundle,
    auto_approve_gates: bool = False,
    llm: LLMClient | None = None,
) -> StageResult:
    """Execute one pipeline stage, validate outputs, and apply gate logic.

    ``llm`` injects a ready-made client (e.g. a fake in tests, or one owned by
    the host project); when omitted a client is built from ``config.llm``.
    """

    # --- HITL pre-stage hook ---
    hitl_result = _run_hitl_pre_stage(stage, run_dir, adapters, config=config)
    if hitl_result is not None:
        return hitl_result

    stage_dir = run_dir / f"stage-{int(stage):02d}"
    stage_dir.mkdir(parents=True, exist_ok=True)
    _t_health_start = _time.monotonic()
    contract: StageContract = CONTRACTS[stage]

    if contract.input_files:
        for input_file in contract.input_files:
            found = _read_prior_artifact(run_dir, input_file)
            if found is None:
                result = StageResult(
                    stage=stage,
                    status=StageStatus.FAILED,
                    artifacts=(),
                    error=f"Missing input: {input_file} (required by {stage.name})",
                    decision="retry",
                )
                _write_stage_meta(stage_dir, stage, run_id, result)
                return result

    bridge = config.openclaw_bridge
    if bridge.use_message and config.notifications.on_stage_start:
        adapters.message.notify(
            config.notifications.channel,
            f"stage-{int(stage):02d}-start",
            f"Starting {stage.name}",
        )
    if bridge.use_memory:
        adapters.memory.append("stages", f"{run_id}:{int(stage)}:running")

    if llm is None:
        try:
            if config.llm.provider == "acp":
                llm = create_llm_client(config)
            else:
                candidate = LLMClient.from_rc_config(config)
                if candidate.config.base_url and candidate.config.api_key:
                    llm = candidate
        except Exception as _llm_exc:  # noqa: BLE001
            logger.warning("LLM client creation failed: %s", _llm_exc)
            llm = None

    try:
        _ = advance(stage, StageStatus.PENDING, TransitionEvent.START)
        executor = _STAGE_EXECUTORS[stage]
        prompts = PromptManager(
            config.prompts.custom_file or None,  # type: ignore[attr-defined]
            domain=_prompt_bank_domain_from_config(config),
            extra_prompts={
                stage_key: path_or_text
                for stage_key, path_or_text in getattr(config.prompts, "extra_prompts", ())  # type: ignore[attr-defined]
            } or None,
        )
        try:
            result = executor(
                stage_dir, run_dir, config, adapters, llm=llm, prompts=prompts
            )
        except TypeError as exc:
            if "unexpected keyword argument 'prompts'" not in str(exc):
                raise
            result = executor(stage_dir, run_dir, config, adapters, llm=llm)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Stage %s failed", stage.name)
        result = StageResult(
            stage=stage,
            status=StageStatus.FAILED,
            artifacts=(),
            error=str(exc),
            decision="retry",
        )

    if result.status == StageStatus.DONE:
        for output_file in contract.output_files:
            if output_file.endswith("/"):
                path = stage_dir / output_file.rstrip("/")
                if not path.is_dir() or not any(path.iterdir()):
                    result = StageResult(
                        stage=stage,
                        status=StageStatus.FAILED,
                        artifacts=result.artifacts,
                        error=f"Missing output directory: {output_file}",
                        decision="retry",
                        evidence_refs=result.evidence_refs,
                    )
                    break
            else:
                path = stage_dir / output_file
                if not path.exists() or path.stat().st_size == 0:
                    result = StageResult(
                        stage=stage,
                        status=StageStatus.FAILED,
                        artifacts=result.artifacts,
                        error=f"Missing or empty output: {output_file}",
                        decision="retry",
                        evidence_refs=result.evidence_refs,
                    )
                    break

    if gate_required(stage, config.security.hitl_required_stages):
        if auto_approve_gates:
            if bridge.use_memory:
                adapters.memory.append("gates", f"{run_id}:{int(stage)}:auto-approved")
        else:
            result = StageResult(
                stage=result.stage,
                status=StageStatus.BLOCKED_APPROVAL,
                artifacts=result.artifacts,
                error=result.error,
                decision="block",
                evidence_refs=result.evidence_refs,
            )
            if bridge.use_message and config.notifications.on_gate_required:
                adapters.message.notify(
                    config.notifications.channel,
                    f"gate-{int(stage):02d}",
                    f"Approval required for {stage.name}",
                )

    if bridge.use_memory:
        adapters.memory.append("stages", f"{run_id}:{int(stage)}:{result.status.value}")

    _write_stage_meta(stage_dir, stage, run_id, result)

    _t_health_end = _time.monotonic()
    stage_health = {
        "stage_id": f"{int(stage):02d}-{stage.name.lower()}",
        "run_id": run_id,
        "duration_sec": round(_t_health_end - _t_health_start, 2),
        "status": result.status.value,
        "artifacts_count": len(result.artifacts),
        "error": result.error,
        "timestamp": _utcnow_iso(),
    }
    try:
        (stage_dir / "stage_health.json").write_text(
            json.dumps(stage_health, indent=2), encoding="utf-8"
        )
    except OSError:
        pass

    # --- HITL post-stage hook ---
    result = _run_hitl_post_stage(stage, result, run_dir, adapters, config=config)

    return result
