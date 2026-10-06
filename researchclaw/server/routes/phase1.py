"""Ultimate Granular FastAPI Suite for AutoResearchClaw Phase 1 (Stages 1-8).

Provides:
- 100% full CRUD on all artifacts
- Full Human-in-the-Loop (HITL) manual overrides & edits
- Individual Stage execution and telemetry
- Checkpoint management, health monitoring, and BibTeX export
"""

from __future__ import annotations

import asyncio
import dataclasses
import hashlib
import json
import logging
import os
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse, PlainTextResponse
from pydantic import BaseModel, Field

from researchclaw.adapters import AdapterBundle
from researchclaw.config import RCConfig
from researchclaw.pipeline.runner import execute_pipeline
from researchclaw.pipeline.stages import Stage

logger = logging.getLogger(__name__)

router = APIRouter()

_RUN_ID_RE = re.compile(r"^rc-\d{8}-\d{6}-[a-f0-9]+$")

STAGE_MAP = {
    1: {"name": "TOPIC_INIT", "enum": Stage.TOPIC_INIT, "desc": "Khởi tạo mục tiêu SMART & Khảo sát phần cứng"},
    2: {"name": "PROBLEM_DECOMPOSE", "enum": Stage.PROBLEM_DECOMPOSE, "desc": "Phân rã MECE & Đánh giá chất lượng đề tài"},
    3: {"name": "SEARCH_STRATEGY", "enum": Stage.SEARCH_STRATEGY, "desc": "Xây dựng kế hoạch tìm kiếm & câu truy vấn"},
    4: {"name": "LITERATURE_COLLECT", "enum": Stage.LITERATURE_COLLECT, "desc": "Thu thập bài báo từ OpenAlex, S2, arXiv"},
    5: {"name": "LITERATURE_SCREEN", "enum": Stage.LITERATURE_SCREEN, "desc": "Sàng lọc kép: Độ liên quan & Uy tín (Gate 5)"},
    6: {"name": "KNOWLEDGE_EXTRACT", "enum": Stage.KNOWLEDGE_EXTRACT, "desc": "Trích xuất Thẻ tri thức (Knowledge Cards)"},
    7: {"name": "SYNTHESIS", "enum": Stage.SYNTHESIS, "desc": "Tổng hợp trường phái & Tìm Research Gaps"},
    8: {"name": "HYPOTHESIS_GEN", "enum": Stage.HYPOTHESIS_GEN, "desc": "Tranh luận đa Agent & Tạo Giả thuyết khoa học"},
}


# --- Helpers ---

def _get_run_dir(run_id: str, create: bool = False) -> Path:
    if not _RUN_ID_RE.match(run_id):
        raise HTTPException(status_code=400, detail=f"Mã run_id không đúng định dạng chuẩn: {run_id}")
    rdir = Path("artifacts") / run_id
    if not rdir.exists():
        if create:
            rdir.mkdir(parents=True, exist_ok=True)
        else:
            raise HTTPException(status_code=404, detail=f"Không tìm thấy thư mục run {run_id} trong artifacts/")
    return rdir


def _read_stage_file(run_id: str, stage_num: int, filename: str) -> str:
    rdir = _get_run_dir(run_id)
    fp = rdir / f"stage-{stage_num:02d}" / filename
    if not fp.exists():
        raise HTTPException(status_code=404, detail=f"Chưa có file {filename} trong Stage {stage_num}")
    return fp.read_text(encoding="utf-8", errors="replace")


def _read_stage_json(run_id: str, stage_num: int, filename: str) -> Any:
    text = _read_stage_file(run_id, stage_num, filename)
    try:
        return json.loads(text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Không thể parse JSON từ {filename}: {e}")


def _write_stage_file(run_id: str, stage_num: int, filename: str, content: str) -> dict[str, str]:
    rdir = _get_run_dir(run_id, create=True)
    stg_dir = rdir / f"stage-{stage_num:02d}"
    stg_dir.mkdir(parents=True, exist_ok=True)
    fp = stg_dir / filename
    fp.write_text(content, encoding="utf-8")
    return {"status": "updated", "run_id": run_id, "file": f"stage-{stage_num:02d}/{filename}"}


def _load_config(
    topic: Optional[str] = None,
    domains: Optional[list[str]] = None,
    provider: Optional[str] = None,
    model: Optional[str] = None
) -> RCConfig:
    cfg_path = Path("config.arc.yaml") if Path("config.arc.yaml").exists() else Path("config.yaml")
    cfg = RCConfig.load(cfg_path, check_paths=False)
    if topic:
        new_res = dataclasses.replace(cfg.research, topic=topic, domains=domains or cfg.research.domains)
        cfg = dataclasses.replace(cfg, research=new_res)
    if provider or model:
        new_llm = dataclasses.replace(
            cfg.llm,
            provider=provider or cfg.llm.provider,
            primary_model=model or cfg.llm.primary_model
        )
        cfg = dataclasses.replace(cfg, llm=new_llm)
    return cfg


def _run_single_stage_sync(
    run_id: str,
    stage_num: int,
    topic: Optional[str] = None,
    auto_approve: bool = True,
    provider: Optional[str] = None,
    model: Optional[str] = None
) -> dict[str, Any]:
    run_dir = _get_run_dir(run_id, create=True)
    cfg = _load_config(topic=topic, provider=provider, model=model)
    stage_enum = STAGE_MAP[stage_num]["enum"]

    results = execute_pipeline(
        run_dir=run_dir,
        run_id=run_id,
        config=cfg,
        adapters=AdapterBundle(),
        from_stage=stage_enum,
        to_stage=stage_enum,
        auto_approve_gates=auto_approve,
        skip_noncritical=False
    )
    res = results[0] if results else None
    return {
        "run_id": run_id,
        "stage": stage_num,
        "stage_name": STAGE_MAP[stage_num]["name"],
        "status": res.status.value if res else "done",
        "artifacts": list(res.artifacts) if res else []
    }


# ==============================================================================
# 0. PHASE 1: FULL ORCHESTRATION & RUNS MANAGEMENT
# ==============================================================================

class Phase1StartRequest(BaseModel):
    topic: str = Field(..., description="Chủ đề nghiên cứu", examples=["Stale or Malicious? Byzantine Defences in Asynchronous FL"])
    domains: list[str] = Field(default=["machine-learning", "distributed-systems"])
    llm_provider: Optional[str] = Field(default=None, description="Nhà cung cấp LLM: 'bedrock', 'openai', 'gemini' (để trống sẽ dùng config mặc định)", examples=["bedrock"])
    model: Optional[str] = Field(default=None, description="Mã Model ID (ví dụ: us.anthropic.claude-3-5-sonnet-20241022-v2:0 trên Bedrock)", examples=["us.anthropic.claude-3-5-sonnet-20241022-v2:0"])
    quality_threshold: float = Field(default=4.0)
    auto_approve: bool = Field(default=True)


class TextContentUpdate(BaseModel):
    content: str = Field(..., description="Nội dung văn bản mới cần cập nhật")


_active_state: dict[str, Any] = {"is_running": False, "run_id": None, "topic": None, "current_stage": None, "last_log": None, "error": None}
_active_task: Optional[asyncio.Task[Any]] = None
_lock = asyncio.Lock()


async def _batch_worker(run_id: str, topic: str, domains: list[str], quality_threshold: float, auto_approve: bool, provider: Optional[str] = None, model: Optional[str] = None):
    global _active_state
    run_dir = _get_run_dir(run_id, create=True)
    cfg = _load_config(topic=topic, domains=domains, provider=provider, model=model)
    _active_state.update({"is_running": True, "run_id": run_id, "topic": topic, "current_stage": 1, "error": None, "last_log": f"Bắt đầu chạy Stage 1..8 cho {run_id}"})
    try:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: execute_pipeline(
                run_dir=run_dir,
                run_id=run_id,
                config=cfg,
                adapters=AdapterBundle(),
                from_stage=Stage.TOPIC_INIT,
                to_stage=Stage.HYPOTHESIS_GEN,
                auto_approve_gates=auto_approve,
                skip_noncritical=False
            )
        )
        _active_state.update({"last_log": "Hoàn tất trọn vẹn Phase 1 (Stages 1-8)!", "current_stage": 8})
    except Exception as exc:
        logger.exception("Batch run failed")
        _active_state.update({"error": str(exc), "last_log": f"Lỗi: {exc}"})
    finally:
        _active_state["is_running"] = False


@router.post("/api/phase1/start", tags=["0. Phase 1: Full Orchestration & Runs Management"])
async def start_phase1(req: Phase1StartRequest) -> dict[str, Any]:
    """Chạy tự động toàn bộ 8 Stages của Phase 1 trong background."""
    global _active_state, _active_task
    async with _lock:
        if _active_state["is_running"]:
            raise HTTPException(status_code=409, detail=f"Pipeline đang chạy cho {_active_state['run_id']}")
        ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        thash = hashlib.sha256(req.topic.encode()).hexdigest()[:6]
        run_id = f"rc-{ts}-{thash}"
        _active_state.update({"is_running": True, "run_id": run_id, "topic": req.topic, "current_stage": 1})

    _active_task = asyncio.create_task(_batch_worker(run_id, req.topic, req.domains, req.quality_threshold, req.auto_approve, provider=req.llm_provider, model=req.model))
    return {
        "message": "Đã khởi động tiến trình Phase 1 thành công",
        "run_id": run_id,
        "status": "running",
        "output_dir": str((Path("artifacts") / run_id).resolve())
    }


@router.get("/api/phase1/status", tags=["0. Phase 1: Full Orchestration & Runs Management"])
async def get_phase1_status() -> dict[str, Any]:
    """Xem tiến độ thời gian thực của Phase 1."""
    run_id = _active_state.get("run_id")
    stages = []
    run_dir = Path("artifacts") / run_id if run_id else None
    for n in range(1, 9):
        st = "pending"
        arts = []
        if run_dir and run_dir.exists():
            sdir = run_dir / f"stage-{n:02d}"
            if sdir.exists():
                arts = [f.name for f in sdir.iterdir() if f.is_file()]
                if (sdir / "decision.json").exists():
                    st = "completed"
                elif _active_state["is_running"] and n == _active_state.get("current_stage"):
                    st = "running"
        stages.append({"stage": n, "name": STAGE_MAP[n]["name"], "status": st, "artifacts": arts})
    done = sum(1 for s in stages if s["status"] == "completed")
    return {
        "is_running": _active_state["is_running"],
        "run_id": run_id,
        "topic": _active_state.get("topic"),
        "progress_percentage": int((done / 8) * 100),
        "stages": stages,
        "last_log": _active_state.get("last_log"),
        "error": _active_state.get("error")
    }


@router.post("/api/phase1/stop", tags=["0. Phase 1: Full Orchestration & Runs Management"])
async def stop_phase1() -> dict[str, str]:
    """Hủy tiến trình đang chạy."""
    global _active_task, _active_state
    if not _active_state["is_running"] or not _active_task:
        raise HTTPException(status_code=404, detail="Không có pipeline nào đang chạy")
    _active_task.cancel()
    _active_state["is_running"] = False
    return {"status": "stopped"}


@router.get("/api/phase1/runs", tags=["0. Phase 1: Full Orchestration & Runs Management"])
async def list_runs() -> list[dict[str, Any]]:
    """Liệt kê toàn bộ các phiên chạy trong artifacts/."""
    art = Path("artifacts")
    if not art.exists():
        return []
    res = []
    for d in sorted(art.iterdir(), reverse=True):
        if d.is_dir() and _RUN_ID_RE.match(d.name):
            g = d / "stage-01" / "goal.md"
            t = ""
            if g.exists():
                for line in g.read_text(encoding="utf-8").splitlines():
                    if line.startswith("# Topic:") or line.startswith("## Working title"):
                        t = line.replace("# Topic:", "").replace("## Working title", "").strip()
                        break
            res.append({
                "run_id": d.name,
                "topic": t,
                "has_stage8_hypotheses": (d / "stage-08" / "hypotheses.md").exists()
            })
    return res


@router.get("/api/phase1/runs/{run_id}/summary", tags=["0. Phase 1: Full Orchestration & Runs Management"])
async def get_run_phase1_summary(run_id: str) -> dict[str, Any]:
    """Lấy gói tổng hợp kết quả học thuật Phase 1 của một run."""
    rdir = _get_run_dir(run_id)
    cards_dir = rdir / "stage-06" / "cards"
    cards_count = len(list(cards_dir.glob("*.json"))) if cards_dir.exists() else 0
    return {
        "run_id": run_id,
        "stage_1_goal": (rdir / "stage-01" / "goal.md").read_text(encoding="utf-8") if (rdir / "stage-01" / "goal.md").exists() else "",
        "stage_2_problem_tree": (rdir / "stage-02" / "problem_tree.md").read_text(encoding="utf-8") if (rdir / "stage-02" / "problem_tree.md").exists() else "",
        "stage_2_evaluation": json.loads((rdir / "stage-02" / "topic_evaluation.json").read_text(encoding="utf-8")) if (rdir / "stage-02" / "topic_evaluation.json").exists() else None,
        "stage_3_search_plan": (rdir / "stage-03" / "search_plan.yaml").read_text(encoding="utf-8") if (rdir / "stage-03" / "search_plan.yaml").exists() else "",
        "stage_3_queries": json.loads((rdir / "stage-03" / "queries.json").read_text(encoding="utf-8")) if (rdir / "stage-03" / "queries.json").exists() else [],
        "stage_4_references_count": len((rdir / "stage-04" / "references.bib").read_text(encoding="utf-8").split("@")) - 1 if (rdir / "stage-04" / "references.bib").exists() else 0,
        "stage_5_shortlist_count": len((rdir / "stage-05" / "shortlist.jsonl").read_text(encoding="utf-8").strip().splitlines()) if (rdir / "stage-05" / "shortlist.jsonl").exists() else 0,
        "stage_6_knowledge_cards_count": cards_count,
        "stage_7_synthesis": (rdir / "stage-07" / "synthesis.md").read_text(encoding="utf-8") if (rdir / "stage-07" / "synthesis.md").exists() else "",
        "stage_8_hypotheses": (rdir / "stage-08" / "hypotheses.md").read_text(encoding="utf-8") if (rdir / "stage-08" / "hypotheses.md").exists() else "",
        "stage_8_novelty_report": json.loads((rdir / "stage-08" / "novelty_report.json").read_text(encoding="utf-8")) if (rdir / "stage-08" / "novelty_report.json").exists() else None,
    }


@router.get("/api/phase1/runs/{run_id}/checkpoint", tags=["0. Phase 1: Full Orchestration & Runs Management"])
async def get_checkpoint(run_id: str) -> dict[str, Any]:
    """Lấy thông tin checkpoint hiện tại của run."""
    rdir = _get_run_dir(run_id)
    chk = rdir / "checkpoint.json"
    if not chk.exists():
        raise HTTPException(status_code=404, detail="Chưa có checkpoint.json trong run này")
    return json.loads(chk.read_text(encoding="utf-8"))


@router.get("/api/phase1/runs/{run_id}/health-overview", tags=["0. Phase 1: Full Orchestration & Runs Management"])
async def get_health_overview(run_id: str) -> list[dict[str, Any]]:
    """Tổng hợp thời gian thực thi và trạng thái sức khỏe của từng Stage 1..8."""
    rdir = _get_run_dir(run_id)
    report = []
    for n in range(1, 9):
        hf = rdir / f"stage-{n:02d}" / "stage_health.json"
        if hf.exists():
            report.append(json.loads(hf.read_text(encoding="utf-8")))
        else:
            report.append({"stage_id": f"{n:02d}", "status": "pending"})
    return report


@router.delete("/api/phase1/runs/{run_id}", tags=["0. Phase 1: Full Orchestration & Runs Management"])
async def delete_run(run_id: str) -> dict[str, str]:
    """Xóa bỏ một phiên chạy khỏi thư mục artifacts/."""
    rdir = _get_run_dir(run_id)
    shutil.rmtree(rdir)
    return {"status": "deleted", "run_id": run_id}


# ==============================================================================
# 1. STAGE 1: TOPIC_INIT
# ==============================================================================

class Stage1RunRequest(BaseModel):
    topic: str = Field(..., description="Chủ đề nghiên cứu", examples=["Stale or Malicious? Byzantine Defences in Asynchronous FL"])
    run_id: Optional[str] = Field(default=None, description="Mã run_id tùy chọn. Nếu không có sẽ tự sinh mới")
    llm_provider: Optional[str] = Field(default=None, description="Nhà cung cấp LLM: 'bedrock', 'openai', 'gemini'", examples=["bedrock"])
    model: Optional[str] = Field(default=None, description="Mã Model ID Bedrock", examples=["us.anthropic.claude-3-5-sonnet-20241022-v2:0"])


@router.post("/api/stage1/run", tags=["Stage 1: Topic Init"])
async def run_stage_1(req: Stage1RunRequest) -> dict[str, Any]:
    """Khởi chạy riêng Stage 1: Xác định mục tiêu SMART & Khảo sát phần cứng máy tính."""
    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    thash = hashlib.sha256(req.topic.encode()).hexdigest()[:6]
    run_id = req.run_id or f"rc-{ts}-{thash}"
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, lambda: _run_single_stage_sync(run_id, 1, topic=req.topic, provider=req.llm_provider, model=req.model))


@router.get("/api/stage1/{run_id}/goal", tags=["Stage 1: Topic Init"])
async def get_stage1_goal(run_id: str) -> PlainTextResponse:
    """Lấy nội dung toàn văn file mục tiêu nghiên cứu goal.md."""
    return PlainTextResponse(_read_stage_file(run_id, 1, "goal.md"))


@router.put("/api/stage1/{run_id}/goal", tags=["Stage 1: Topic Init"])
async def update_stage1_goal(run_id: str, body: TextContentUpdate) -> dict[str, str]:
    """[HITL] Cho phép người dùng chỉnh sửa trực tiếp nội dung mục tiêu nghiên cứu goal.md."""
    return _write_stage_file(run_id, 1, "goal.md", body.content)


@router.get("/api/stage1/{run_id}/hardware", tags=["Stage 1: Topic Init"])
async def get_stage1_hardware(run_id: str) -> dict[str, Any]:
    """Lấy thông số cấu hình phần cứng đã quét (GPU, VRAM, CPU cores)."""
    return _read_stage_json(run_id, 1, "hardware_profile.json")


@router.get("/api/stage1/{run_id}/decision", tags=["Stage 1: Topic Init"])
async def get_stage1_decision(run_id: str) -> dict[str, Any]:
    """Lấy quyết định phê duyệt pass/fail của Stage 1 (decision.json)."""
    return _read_stage_json(run_id, 1, "decision.json")


@router.get("/api/stage1/{run_id}/health", tags=["Stage 1: Topic Init"])
async def get_stage1_health(run_id: str) -> dict[str, Any]:
    """Xem thời gian chạy và số lượng artifacts của Stage 1."""
    return _read_stage_json(run_id, 1, "stage_health.json")


# ==============================================================================
# 2. STAGE 2: PROBLEM_DECOMPOSE
# ==============================================================================

@router.post("/api/stage2/{run_id}/run", tags=["Stage 2: Problem Decompose"])
async def run_stage_2(run_id: str) -> dict[str, Any]:
    """Khởi chạy riêng Stage 2: Phân rã MECE vấn đề thành Sub-Questions và chấm điểm đề tài."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, lambda: _run_single_stage_sync(run_id, 2))


@router.get("/api/stage2/{run_id}/problem-tree", tags=["Stage 2: Problem Decompose"])
async def get_stage2_problem_tree(run_id: str) -> PlainTextResponse:
    """Lấy cây vấn đề nghiên cứu (problem_tree.md) gồm SQ1..SQ4, Priorities, Risks."""
    return PlainTextResponse(_read_stage_file(run_id, 2, "problem_tree.md"))


@router.put("/api/stage2/{run_id}/problem-tree", tags=["Stage 2: Problem Decompose"])
async def update_stage2_problem_tree(run_id: str, body: TextContentUpdate) -> dict[str, str]:
    """[HITL] Cho phép người dùng chỉnh sửa câu hỏi nghiên cứu và rủi ro trong problem_tree.md."""
    return _write_stage_file(run_id, 2, "problem_tree.md", body.content)


@router.get("/api/stage2/{run_id}/evaluation", tags=["Stage 2: Problem Decompose"])
async def get_stage2_evaluation(run_id: str) -> dict[str, Any]:
    """Lấy bảng chấm điểm học thuật IMP-35 (Novelty, Specificity, Feasibility)."""
    return _read_stage_json(run_id, 2, "topic_evaluation.json")


@router.get("/api/stage2/{run_id}/decision", tags=["Stage 2: Problem Decompose"])
async def get_stage2_decision(run_id: str) -> dict[str, Any]:
    """Lấy quyết định phê duyệt pass/fail của Stage 2 (decision.json)."""
    return _read_stage_json(run_id, 2, "decision.json")


@router.get("/api/stage2/{run_id}/health", tags=["Stage 2: Problem Decompose"])
async def get_stage2_health(run_id: str) -> dict[str, Any]:
    """Xem thời gian chạy và số lượng artifacts của Stage 2."""
    return _read_stage_json(run_id, 2, "stage_health.json")


# ==============================================================================
# 3. STAGE 3: SEARCH_STRATEGY
# ==============================================================================

@router.post("/api/stage3/{run_id}/run", tags=["Stage 3: Search Strategy"])
async def run_stage_3(run_id: str) -> dict[str, Any]:
    """Khởi chạy riêng Stage 3: Hoạch định chiến lược truy vấn văn hiến đa tầng."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, lambda: _run_single_stage_sync(run_id, 3))


@router.get("/api/stage3/{run_id}/plan", tags=["Stage 3: Search Strategy"])
async def get_stage3_search_plan(run_id: str) -> PlainTextResponse:
    """Lấy kế hoạch tìm kiếm YAML (search_plan.yaml)."""
    return PlainTextResponse(_read_stage_file(run_id, 3, "search_plan.yaml"))


@router.put("/api/stage3/{run_id}/plan", tags=["Stage 3: Search Strategy"])
async def update_stage3_search_plan(run_id: str, body: TextContentUpdate) -> dict[str, str]:
    """[HITL] Cho phép người dùng chỉnh sửa cấu trúc kế hoạch tìm kiếm YAML."""
    return _write_stage_file(run_id, 3, "search_plan.yaml", body.content)


@router.get("/api/stage3/{run_id}/queries", tags=["Stage 3: Search Strategy"])
async def get_stage3_queries(run_id: str) -> list[str]:
    """Lấy danh sách các câu truy vấn tinh gọn (queries.json)."""
    return _read_stage_json(run_id, 3, "queries.json")


@router.put("/api/stage3/{run_id}/queries", tags=["Stage 3: Search Strategy"])
async def update_stage3_queries(run_id: str, queries: list[str]) -> dict[str, Any]:
    """[HITL] Cho phép người dùng thêm bớt danh sách từ khóa tìm kiếm trước khi cào bài."""
    return _write_stage_file(run_id, 3, "queries.json", json.dumps(queries, indent=2))


@router.get("/api/stage3/{run_id}/sources", tags=["Stage 3: Search Strategy"])
async def get_stage3_sources(run_id: str) -> Any:
    """Lấy danh mục các nguồn học thuật được kích hoạt (sources.json)."""
    return _read_stage_json(run_id, 3, "sources.json")


@router.get("/api/stage3/{run_id}/decision", tags=["Stage 3: Search Strategy"])
async def get_stage3_decision(run_id: str) -> dict[str, Any]:
    """Lấy quyết định phê duyệt pass/fail của Stage 3."""
    return _read_stage_json(run_id, 3, "decision.json")


@router.get("/api/stage3/{run_id}/health", tags=["Stage 3: Search Strategy"])
async def get_stage3_health(run_id: str) -> dict[str, Any]:
    """Xem thời gian chạy và số lượng artifacts của Stage 3."""
    return _read_stage_json(run_id, 3, "stage_health.json")


# ==============================================================================
# 4. STAGE 4: LITERATURE_COLLECT
# ==============================================================================

@router.post("/api/stage4/{run_id}/run", tags=["Stage 4: Literature Collect"])
async def run_stage_4(run_id: str) -> dict[str, Any]:
    """Khởi chạy riêng Stage 4: Cào bài báo từ OpenAlex, Semantic Scholar, arXiv."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, lambda: _run_single_stage_sync(run_id, 4))


@router.get("/api/stage4/{run_id}/candidates", tags=["Stage 4: Literature Collect"])
async def get_stage4_candidates(run_id: str, limit: int = Query(50, ge=1, le=500)) -> list[dict[str, Any]]:
    """Lấy danh sách ứng viên bài báo thô đã cào được (JSONL parsed)."""
    text = _read_stage_file(run_id, 4, "candidates.jsonl")
    items = []
    for line in text.splitlines():
        if line.strip():
            try:
                items.append(json.loads(line))
            except Exception:
                pass
            if len(items) >= limit:
                break
    return items


@router.get("/api/stage4/{run_id}/download-bibtex", tags=["Stage 4: Literature Collect"])
async def download_stage4_bibtex(run_id: str) -> FileResponse:
    """Tải trực tiếp file references.bib chuẩn LaTeX."""
    rdir = _get_run_dir(run_id)
    f = rdir / "stage-04" / "references.bib"
    if not f.exists():
        raise HTTPException(status_code=404, detail="Chưa có file references.bib")
    return FileResponse(path=f, filename=f"{run_id}_references.bib", media_type="text/plain")


@router.get("/api/stage4/{run_id}/references-text", tags=["Stage 4: Literature Collect"])
async def get_stage4_references_text(run_id: str) -> PlainTextResponse:
    """Xem trực tiếp nội dung văn bản của file references.bib."""
    return PlainTextResponse(_read_stage_file(run_id, 4, "references.bib"))


@router.get("/api/stage4/{run_id}/stats", tags=["Stage 4: Literature Collect"])
async def get_stage4_stats(run_id: str) -> dict[str, Any]:
    """Xem thống kê thu thập từ các nguồn (search_meta.json)."""
    return _read_stage_json(run_id, 4, "search_meta.json")


@router.get("/api/stage4/{run_id}/decision", tags=["Stage 4: Literature Collect"])
async def get_stage4_decision(run_id: str) -> dict[str, Any]:
    """Lấy quyết định phê duyệt pass/fail của Stage 4."""
    return _read_stage_json(run_id, 4, "decision.json")


@router.get("/api/stage4/{run_id}/health", tags=["Stage 4: Literature Collect"])
async def get_stage4_health(run_id: str) -> dict[str, Any]:
    """Xem thời gian chạy và số lượng artifacts của Stage 4."""
    return _read_stage_json(run_id, 4, "stage_health.json")


# ==============================================================================
# 5. STAGE 5: LITERATURE_SCREEN (GATE)
# ==============================================================================

@router.post("/api/stage5/{run_id}/run", tags=["Stage 5: Literature Screen (Gate)"])
async def run_stage_5(run_id: str, auto_approve: bool = Query(True)) -> dict[str, Any]:
    """Khởi chạy riêng Stage 5: Sàng lọc kép độ liên quan & uy tín học thuật."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, lambda: _run_single_stage_sync(run_id, 5, auto_approve=auto_approve))


@router.get("/api/stage5/{run_id}/shortlist", tags=["Stage 5: Literature Screen (Gate)"])
async def get_stage5_shortlist(run_id: str) -> list[dict[str, Any]]:
    """Lấy danh sách Top 10-20 bài báo tinh hoa đã vượt qua vòng sàng lọc."""
    text = _read_stage_file(run_id, 5, "shortlist.jsonl")
    items = []
    for line in text.splitlines():
        if line.strip():
            try:
                items.append(json.loads(line))
            except Exception:
                pass
    return items


@router.put("/api/stage5/{run_id}/shortlist", tags=["Stage 5: Literature Screen (Gate)"])
async def update_stage5_shortlist(run_id: str, papers: list[dict[str, Any]]) -> dict[str, str]:
    """[HITL] Cho phép người dùng trực tiếp thêm/bớt các bài báo trong danh sách shortlist."""
    lines = [json.dumps(p) for p in papers]
    return _write_stage_file(run_id, 5, "shortlist.jsonl", "\n".join(lines))


@router.post("/api/stage5/{run_id}/approve", tags=["Stage 5: Literature Screen (Gate)"])
async def approve_stage5_gate(run_id: str, reason: str = Query("Approved by researcher")) -> dict[str, str]:
    """[HITL GATE] Phê duyệt thủ công cổng chất lượng Stage 5 để cho phép pipeline tiếp tục."""
    decision_data = {
        "status": "APPROVED",
        "reason": reason,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    _write_stage_file(run_id, 5, "decision.json", json.dumps(decision_data, indent=2))
    return {"status": "gate_approved", "run_id": run_id}


@router.get("/api/stage5/{run_id}/decision", tags=["Stage 5: Literature Screen (Gate)"])
async def get_stage5_decision(run_id: str) -> dict[str, Any]:
    """Lấy quyết định phê duyệt pass/fail của Gate Stage 5."""
    return _read_stage_json(run_id, 5, "decision.json")


@router.get("/api/stage5/{run_id}/health", tags=["Stage 5: Literature Screen (Gate)"])
async def get_stage5_health(run_id: str) -> dict[str, Any]:
    """Xem thời gian chạy và số lượng artifacts của Stage 5."""
    return _read_stage_json(run_id, 5, "stage_health.json")


# ==============================================================================
# 6. STAGE 6: KNOWLEDGE_EXTRACT
# ==============================================================================

@router.post("/api/stage6/{run_id}/run", tags=["Stage 6: Knowledge Extract"])
async def run_stage_6(run_id: str) -> dict[str, Any]:
    """Khởi chạy riêng Stage 6: Bóc tách Thẻ tri thức từ danh sách Shortlist."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, lambda: _run_single_stage_sync(run_id, 6))


@router.get("/api/stage6/{run_id}/cards", tags=["Stage 6: Knowledge Extract"])
async def list_stage6_cards(run_id: str) -> list[str]:
    """Liệt kê danh sách tên tất cả các thẻ tri thức đã trích xuất."""
    rdir = _get_run_dir(run_id)
    cdir = rdir / "stage-06" / "cards"
    if not cdir.exists():
        return []
    return [p.name for p in sorted(cdir.glob("*.json"))]


@router.get("/api/stage6/{run_id}/cards-merged", tags=["Stage 6: Knowledge Extract"])
async def get_stage6_all_cards_merged(run_id: str) -> list[dict[str, Any]]:
    """Gộp toàn bộ nội dung của tất cả các Thẻ tri thức thành 1 danh sách JSON hoàn chỉnh."""
    rdir = _get_run_dir(run_id)
    cdir = rdir / "stage-06" / "cards"
    if not cdir.exists():
        return []
    cards = []
    for p in sorted(cdir.glob("*.json")):
        try:
            cards.append(json.loads(p.read_text(encoding="utf-8")))
        except Exception:
            pass
    return cards


@router.get("/api/stage6/{run_id}/cards/{card_name}", tags=["Stage 6: Knowledge Extract"])
async def get_stage6_card_detail(run_id: str, card_name: str) -> dict[str, Any]:
    """Xem nội dung chi tiết của một Thẻ tri thức cụ thể."""
    rdir = _get_run_dir(run_id)
    cf = rdir / "stage-06" / "cards" / card_name
    if not cf.exists():
        raise HTTPException(status_code=404, detail=f"Không tìm thấy thẻ {card_name}")
    return json.loads(cf.read_text(encoding="utf-8"))


@router.get("/api/stage6/{run_id}/decision", tags=["Stage 6: Knowledge Extract"])
async def get_stage6_decision(run_id: str) -> dict[str, Any]:
    """Lấy quyết định phê duyệt pass/fail của Stage 6."""
    return _read_stage_json(run_id, 6, "decision.json")


@router.get("/api/stage6/{run_id}/health", tags=["Stage 6: Knowledge Extract"])
async def get_stage6_health(run_id: str) -> dict[str, Any]:
    """Xem thời gian chạy và số lượng artifacts của Stage 6."""
    return _read_stage_json(run_id, 6, "stage_health.json")


# ==============================================================================
# 7. STAGE 7: SYNTHESIS
# ==============================================================================

@router.post("/api/stage7/{run_id}/run", tags=["Stage 7: Synthesis"])
async def run_stage_7(run_id: str) -> dict[str, Any]:
    """Khởi chạy riêng Stage 7: Gom cụm trường phái & Xác định các khoảng trống học thuật."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, lambda: _run_single_stage_sync(run_id, 7))


@router.get("/api/stage7/{run_id}/synthesis", tags=["Stage 7: Synthesis"])
async def get_stage7_synthesis(run_id: str) -> PlainTextResponse:
    """Lấy báo cáo tổng hợp văn hiến toàn văn (synthesis.md)."""
    return PlainTextResponse(_read_stage_file(run_id, 7, "synthesis.md"))


@router.put("/api/stage7/{run_id}/synthesis", tags=["Stage 7: Synthesis"])
async def update_stage7_synthesis(run_id: str, body: TextContentUpdate) -> dict[str, str]:
    """[HITL] Cho phép người dùng chỉnh sửa báo cáo tổng hợp văn hiến synthesis.md."""
    return _write_stage_file(run_id, 7, "synthesis.md", body.content)


@router.get("/api/stage7/{run_id}/decision", tags=["Stage 7: Synthesis"])
async def get_stage7_decision(run_id: str) -> dict[str, Any]:
    """Lấy quyết định phê duyệt pass/fail của Stage 7."""
    return _read_stage_json(run_id, 7, "decision.json")


@router.get("/api/stage7/{run_id}/health", tags=["Stage 7: Synthesis"])
async def get_stage7_health(run_id: str) -> dict[str, Any]:
    """Xem thời gian chạy và số lượng artifacts của Stage 7."""
    return _read_stage_json(run_id, 7, "stage_health.json")


# ==============================================================================
# 8. STAGE 8: HYPOTHESIS_GEN
# ==============================================================================

@router.post("/api/stage8/{run_id}/run", tags=["Stage 8: Hypothesis Gen"])
async def run_stage_8(run_id: str) -> dict[str, Any]:
    """Khởi chạy riêng Stage 8: Tranh luận đa Agent để sinh Giả thuyết khoa học khả bác."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, lambda: _run_single_stage_sync(run_id, 8))


@router.get("/api/stage8/{run_id}/hypotheses", tags=["Stage 8: Hypothesis Gen"])
async def get_stage8_hypotheses(run_id: str) -> PlainTextResponse:
    """Lấy danh sách các giả thuyết khoa học chính thức (hypotheses.md)."""
    return PlainTextResponse(_read_stage_file(run_id, 8, "hypotheses.md"))


@router.put("/api/stage8/{run_id}/hypotheses", tags=["Stage 8: Hypothesis Gen"])
async def update_stage8_hypotheses(run_id: str, body: TextContentUpdate) -> dict[str, str]:
    """[HITL] Cho phép người dùng chỉnh sửa hoàn thiện các giả thuyết khoa học trước khi bước sang Stage 9."""
    return _write_stage_file(run_id, 8, "hypotheses.md", body.content)


@router.get("/api/stage8/{run_id}/novelty", tags=["Stage 8: Hypothesis Gen"])
async def get_stage8_novelty(run_id: str) -> dict[str, Any]:
    """Lấy báo cáo thẩm định tính mới lạ của giả thuyết (novelty_report.json)."""
    return _read_stage_json(run_id, 8, "novelty_report.json")


@router.get("/api/stage8/{run_id}/perspectives", tags=["Stage 8: Hypothesis Gen"])
async def list_stage8_perspectives(run_id: str) -> list[str]:
    """Liệt kê danh sách các biên bản tranh luận góc nhìn đa Agent."""
    rdir = _get_run_dir(run_id)
    pdir = rdir / "stage-08" / "perspectives"
    if not pdir.exists():
        return []
    return [p.name for p in sorted(pdir.iterdir()) if p.is_file()]


@router.get("/api/stage8/{run_id}/perspectives/{filename}", tags=["Stage 8: Hypothesis Gen"])
async def get_stage8_perspective_detail(run_id: str, filename: str) -> PlainTextResponse:
    """Đọc chi tiết biên bản tranh luận của một góc nhìn cụ thể (Theorist, Skeptic, v.v.)."""
    rdir = _get_run_dir(run_id)
    fp = rdir / "stage-08" / "perspectives" / filename
    if not fp.exists():
        raise HTTPException(status_code=404, detail=f"Không tìm thấy file {filename}")
    return PlainTextResponse(fp.read_text(encoding="utf-8", errors="replace"))


@router.get("/api/stage8/{run_id}/decision", tags=["Stage 8: Hypothesis Gen"])
async def get_stage8_decision(run_id: str) -> dict[str, Any]:
    """Lấy quyết định phê duyệt pass/fail của Stage 8."""
    return _read_stage_json(run_id, 8, "decision.json")


@router.get("/api/stage8/{run_id}/health", tags=["Stage 8: Hypothesis Gen"])
async def get_stage8_health(run_id: str) -> dict[str, Any]:
    """Xem thời gian chạy và số lượng artifacts của Stage 8."""
    return _read_stage_json(run_id, 8, "stage_health.json")
