"""``write_paper``: run the writing stages over a :class:`PaperInput`."""

from __future__ import annotations

import copy
import dataclasses
import json
import logging
import re
import shutil
import uuid
from pathlib import Path
from typing import Any, Mapping

import yaml

from paperwriter.models import PaperInput, PaperResult, StageOutcome
from paperwriter.seed import seed_run_dir
from researchclaw.adapters import AdapterBundle
from researchclaw.config import RCConfig
from researchclaw.llm import create_llm_client
from researchclaw.pipeline.contracts import CONTRACTS
from researchclaw.pipeline.executor import execute_stage
from researchclaw.pipeline.stages import (
    GATE_ROLLBACK,
    NEXT_STAGE,
    Stage,
    StageStatus,
)

logger = logging.getLogger(__name__)

ConfigLike = RCConfig | Mapping[str, Any] | str | Path | None

# Final deliverables are gathered here so host projects need not know stage numbers.
FINAL_DIR = "final"


def _deep_merge(base: dict[str, Any], over: Mapping[str, Any]) -> dict[str, Any]:
    for key, value in over.items():
        if isinstance(value, Mapping) and isinstance(base.get(key), dict):
            _deep_merge(base[key], value)
        else:
            base[key] = copy.deepcopy(value)
    return base


def build_config(paper: PaperInput, run_dir: Path, config: ConfigLike) -> RCConfig:
    """Resolve ``config`` into an :class:`RCConfig` for a literature-first paper.

    ``config`` may be an ``RCConfig``, a mapping or YAML path with (at least) an
    ``llm`` section, or ``None`` (then the LLM must come from the ``llm`` argument).
    The project is always forced to ``docs-first`` and the topic taken from the input.
    """
    if isinstance(config, RCConfig):
        return dataclasses.replace(
            config,
            project=dataclasses.replace(config.project, mode="docs-first"),
            research=dataclasses.replace(config.research, topic=paper.topic),
        )

    user: Mapping[str, Any] = {}
    if isinstance(config, (str, Path)):
        user = yaml.safe_load(Path(config).read_text(encoding="utf-8")) or {}
    elif config is not None:
        user = config

    data: dict[str, Any] = {
        "project": {"name": "paperwriter"},
        "research": {"topic": paper.topic, "quality_threshold": 4.0},
        "runtime": {"timezone": "UTC"},
        "notifications": {"channel": "console"},
        "knowledge_base": {"backend": "markdown", "root": str(run_dir / "kb")},
        "llm": {
            "provider": "openai-compatible",
            "base_url": "http://localhost/v1",
            "api_key_env": "OPENAI_API_KEY",
        },
        "security": {"hitl_required_stages": []},
        "export": {"target_conference": "generic"},  # surveys are not conference-format papers
    }
    _deep_merge(data, user)
    data["project"]["mode"] = "docs-first"
    data["research"]["topic"] = paper.topic
    return RCConfig.from_dict(data, project_root=run_dir, check_paths=False)


def _outcome(stage: Stage, result: Any) -> StageOutcome:
    return StageOutcome(
        stage=stage.name,
        number=int(stage),
        status=result.status.value,
        error=result.error,
        artifacts=tuple(result.artifacts),
    )


def _collect_final(run_dir: Path) -> dict[str, Path | None]:
    """Copy the deliverables into ``final/`` and return their paths."""
    sources = {
        "paper_markdown": (
            run_dir / "stage-23" / "paper_final_verified.md"
            if (run_dir / "stage-23" / "paper_final_verified.md").is_file()
            else run_dir / "stage-22" / "paper_final.md",
            "paper.md",
        ),
        "paper_tex": (run_dir / "stage-22" / "paper.tex", "paper.tex"),
        "references_bib": (run_dir / "stage-23" / "references_verified.bib", "references.bib"),
        "verification_report": (
            run_dir / "stage-23" / "verification_report.json",
            "verification_report.json",
        ),
    }
    final = run_dir / FINAL_DIR
    out: dict[str, Path | None] = {}
    for key, (src, name) in sources.items():
        if src.is_file():
            final.mkdir(exist_ok=True)
            shutil.copy2(src, final / name)
            out[key] = final / name
        else:
            out[key] = None
    tex, bib = out.get("paper_tex"), out.get("references_bib")
    if tex and bib:
        text = tex.read_text(encoding="utf-8")
        cleaned = _strip_unknown_cites(text, _bib_keys(bib.read_text(encoding="utf-8")))
        if cleaned != text:
            tex.write_text(cleaned, encoding="utf-8")
    return out


_CITE_RE = re.compile(r"\\(cite[a-zA-Z]*)(\[[^\]]*\])*\{([^}]*)\}")
_BIB_KEY_RE = re.compile(r"@\w+\s*\{\s*([^,\s]+)\s*,")


def _bib_keys(bib_text: str) -> set[str]:
    return set(_BIB_KEY_RE.findall(bib_text))


def _strip_unknown_cites(tex: str, known: set[str]) -> str:
    """Drop cite-family keys that are not in the shipped bibliography.

    Stage 22 writes ``paper.tex`` before stage 23 removes unverifiable
    references from the bibliography, so the two can disagree.
    """

    def repl(m: re.Match[str]) -> str:
        keys = [k.strip() for k in m.group(3).split(",") if k.strip()]
        kept = [k for k in keys if k in known]
        if len(kept) == len(keys):
            return m.group(0)
        if not kept:
            return ""
        return m.group(0)[: m.start(3) - m.start(0)] + ",".join(kept) + "}"

    return _CITE_RE.sub(repl, tex)


# Files written at the run root / by stages that must not leak into a fresh run.
_STALE_ROOT_FILES = ("result.json", "degradation_signal.json", "iteration_context.json")


def _reset_run_dir(run_dir: Path) -> None:
    for d in run_dir.glob("stage-*"):
        if d.is_dir():
            shutil.rmtree(d)
    shutil.rmtree(run_dir / FINAL_DIR, ignore_errors=True)
    for name in _STALE_ROOT_FILES:
        (run_dir / name).unlink(missing_ok=True)


def _write_iteration_context(run_dir: Path, iteration: int) -> None:
    """Hand the rejected draft's review feedback to the outline rewrite (stage 16)."""
    reviews = run_dir / "stage-18" / "reviews.md"
    score = None
    weaknesses: list[str] = []
    report = run_dir / "stage-20" / "quality_report.json"
    if report.is_file():
        try:
            data = json.loads(report.read_text(encoding="utf-8"))
            score = data.get("score_1_to_10")
            weaknesses = [str(w) for w in data.get("weaknesses", [])]
        except (OSError, ValueError, AttributeError):
            pass
    excerpt = reviews.read_text(encoding="utf-8") if reviews.is_file() else ""
    if weaknesses:
        bullets = "\n".join(f"- {w}" for w in weaknesses)
        excerpt += f"\n\nQuality gate weaknesses:\n{bullets}"
    (run_dir / "iteration_context.json").write_text(
        json.dumps(
            {"iteration": iteration, "quality_score": score, "reviews_excerpt": excerpt[:3000]},
            indent=2,
        ),
        encoding="utf-8",
    )


def write_paper(
    paper: PaperInput | Mapping[str, Any],
    output_dir: str | Path,
    *,
    config: ConfigLike = None,
    llm: Any | None = None,
    auto_approve_gates: bool = True,
    max_rewrites: int = 1,
    run_id: str | None = None,
) -> PaperResult:
    """Write a literature-first paper from ``topic + hypotheses + literature``.

    Runs outline → draft → peer review → revision → quality gate → LaTeX export →
    citation verification inside ``output_dir``. Every call starts fresh: earlier
    ``stage-NN`` directories, ``final/`` and ``result.json`` there are replaced.
    Deliverables end up in ``output_dir/final``.

    ``llm`` injects a ready-made client (anything with ``chat(messages, **kw)``);
    otherwise one is built from ``config.llm``. ``max_rewrites`` bounds how often a
    rejected quality gate sends the paper back to the outline.
    """
    if not isinstance(paper, PaperInput):
        paper = PaperInput.from_dict(paper)
    if not paper.literature:
        raise ValueError("literature must contain at least one reference")

    if llm is None and config is None:
        raise ValueError("pass `config` (with an `llm` section) or an `llm` client")

    run_dir = Path(output_dir).resolve()
    run_dir.mkdir(parents=True, exist_ok=True)
    _reset_run_dir(run_dir)
    cfg = build_config(paper, run_dir, config)
    if llm is None:
        llm = create_llm_client(cfg)
    run_id = run_id or f"pw-{uuid.uuid4().hex[:10]}"
    adapters = AdapterBundle()

    seed_run_dir(paper, run_dir)

    result = PaperResult(ok=False, run_dir=run_dir)
    stage: Stage | None = Stage.PAPER_OUTLINE
    attempts: dict[Stage, int] = {}
    rewrites = 0

    while stage is not None:
        logger.info("[%s] %s ...", run_id, stage.name)
        res = execute_stage(
            stage,
            run_dir=run_dir,
            run_id=run_id,
            config=cfg,
            adapters=adapters,
            auto_approve_gates=auto_approve_gates,
            llm=llm,
        )
        result.stages.append(_outcome(stage, res))

        if res.status == StageStatus.DONE:
            stage = NEXT_STAGE[stage]
        elif res.status == StageStatus.BLOCKED_APPROVAL:
            result.error = f"{stage.name} is waiting for approval"
            break
        else:
            attempts[stage] = attempts.get(stage, 0) + 1
            if attempts[stage] <= CONTRACTS[stage].max_retries:
                continue  # retry the same stage
            rollback = GATE_ROLLBACK.get(stage)
            if rollback is not None and rewrites < max_rewrites:
                rewrites += 1
                attempts.clear()
                _write_iteration_context(run_dir, iteration=rewrites + 1)
                stage = rollback
                continue
            result.error = f"{stage.name} failed: {res.error}"
            break
    else:
        result.ok = True

    for key, path in _collect_final(run_dir).items():
        setattr(result, key, path)
    if result.verification_report:
        try:
            report = json.loads(result.verification_report.read_text(encoding="utf-8"))
            result.citations = dict(report.get("summary", {}))
        except (OSError, ValueError):
            pass
    (run_dir / "result.json").write_text(
        json.dumps(result.to_dict(), indent=2), encoding="utf-8"
    )
    return result
