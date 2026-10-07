"""Engine Runs API Router — Conforms to engine-handoff-topic-to-hypothesis.md.

Consolidates all Stage 1 to Stage 8 research operations into an asynchronous,
event-driven webhook architecture that connects AutoResearchClaw with Platform BE.
"""

from __future__ import annotations

import asyncio
from decimal import Decimal
import logging
import time
from typing import Any, Literal
from uuid import UUID, uuid4

import httpx
from fastapi import APIRouter, Header, HTTPException, Query, Request, status
from pydantic import BaseModel, Field, field_validator

from researchclaw.config import load_config
from researchclaw.llm.client import LLMClient

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Engine Runs (Platform BE Integration)"])

# ---------------------------------------------------------------------------
# Request & Response Schemas (Strictly matching engine-handoff spec)
# ---------------------------------------------------------------------------

class RunCreateRequest(BaseModel):
    platform_run_id: str = Field(description="UUID of the run from Platform BE (Idempotency Key)")
    topic: str = Field(min_length=12, max_length=1000, description="Research topic")
    domains: list[str] = Field(default_factory=list, max_items=6, description="Academic domains")
    review_mode: Literal["auto", "light", "copilot", "full"] = Field(
        default="copilot", description="Review mode controlling HITL gates"
    )
    budget_usd: Decimal = Field(default=Decimal("5.00"), gt=0, description="Max budget in USD")
    callback_url: str = Field(description="Webhook URL for event dispatching")

    @field_validator("topic")
    @classmethod
    def clean_topic(cls, v: str) -> str:
        s = v.strip()
        if len(s) < 12:
            raise ValueError("Topic must be at least 12 characters")
        return s

    @field_validator("domains")
    @classmethod
    def clean_domains(cls, v: list[str]) -> list[str]:
        cleaned = [d.strip() for d in v if d.strip()]
        return cleaned[:6]


class RunCreateResponse(BaseModel):
    popper_run_id: str
    status: Literal["running", "paused", "awaiting_review", "completed", "failed"]
    cost_usd: str
    message: str | None = None


class RunStateResponse(BaseModel):
    popper_run_id: str
    status: Literal["running", "paused", "awaiting_review", "completed", "failed"]
    cost_usd: str
    message: str | None = None
    last_source_seq: int


class GateAnswerRequest(BaseModel):
    option_id: str
    dropped: list[str] = Field(default_factory=list)
    note: str | None = None


class EventItem(BaseModel):
    source_seq: int
    type: str
    stage_key: str | None = None
    actor: str | None = None
    payload: dict[str, Any]


class EventsBatchResponse(BaseModel):
    events: list[EventItem]


# ---------------------------------------------------------------------------
# In-Memory Run Session & State Manager
# ---------------------------------------------------------------------------

class RunSession:
    def __init__(
        self,
        popper_run_id: str,
        request: RunCreateRequest,
        service_key: str | None = None,
    ) -> None:
        self.popper_run_id = popper_run_id
        self.platform_run_id = request.platform_run_id
        self.topic = request.topic
        self.domains = request.domains
        self.review_mode = request.review_mode
        self.budget_usd = request.budget_usd
        self.callback_url = request.callback_url.rstrip("/")
        self.service_key = service_key

        self.status: Literal["running", "paused", "awaiting_review", "completed", "failed"] = "running"
        self.cost_usd = Decimal("0.00")
        self.message: str | None = None
        self.current_source_seq = 0
        self.events: list[dict[str, Any]] = []

        # Flow control
        self.pause_event = asyncio.Event()
        self.pause_event.set()  # running by default
        self.gate_event = asyncio.Event()
        self.pending_gate: dict[str, Any] | None = None
        self.gate_answer: dict[str, Any] | None = None
        self.is_cancelled = False
        self.task: asyncio.Task[None] | None = None
        self._dispatch_queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self._dispatcher_task: asyncio.Task[None] | None = asyncio.create_task(self._dispatch_worker())

    async def emit_event(
        self,
        event_type: str,
        payload: dict[str, Any],
        stage_key: str | None = None,
        actor: str | None = None,
    ) -> dict[str, Any]:
        """Record an event with sequential source_seq and enqueue for FIFO dispatch."""
        if self.is_cancelled:
            return {}

        await self.pause_event.wait()

        self.current_source_seq += 1
        event = {
            "source_seq": self.current_source_seq,
            "type": event_type,
            "payload": payload,
        }
        if stage_key:
            event["stage_key"] = stage_key
        if actor:
            event["actor"] = actor

        self.events.append(event)
        self._dispatch_queue.put_nowait(event)
        return event

    async def _dispatch_worker(self) -> None:
        """Sequential single-flight worker ensuring strict FIFO ordering to Platform BE."""
        while not self.is_cancelled:
            try:
                first_event = await self._dispatch_queue.get()
            except asyncio.CancelledError:
                break
            batch = [first_event]
            while not self._dispatch_queue.empty():
                batch.append(self._dispatch_queue.get_nowait())

            await self._send_callback(batch)

    async def _send_callback(self, events: list[dict[str, Any]]) -> None:
        """Send events batch to callback_url with exponential retry."""
        if self.callback_url.endswith("/events"):
            url = self.callback_url
        else:
            url = f"{self.callback_url}/events"
        headers = {"Content-Type": "application/json"}
        if self.service_key:
            headers["X-Service-Key"] = self.service_key

        body = {"events": events}

        backoff = 1.0
        max_backoff = 30.0
        start_time = time.time()

        while not self.is_cancelled:
            try:
                async with httpx.AsyncClient(timeout=15.0) as client:
                    resp = await client.post(url, json=body, headers=headers)
                    if resp.status_code == 200:
                        return
                    if resp.status_code == 409:
                        logger.warning(f"Run {self.popper_run_id} terminated by Platform BE (409)")
                        self.is_cancelled = True
                        return
                    logger.warning(
                        f"Callback returned {resp.status_code}: {resp.text[:200]}. Retrying in {backoff}s..."
                    )
            except Exception as e:
                logger.warning(f"Callback dispatch error: {e}. Retrying in {backoff}s...")

            if time.time() - start_time > 1800:  # 30 mins
                logger.error("Callback retry threshold exceeded 30 mins")
                return

            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, max_backoff)


# In-memory store for active and completed runs
_ACTIVE_RUNS: dict[str, RunSession] = {}
_PLATFORM_MAP: dict[str, str] = {}  # platform_run_id -> popper_run_id


# ---------------------------------------------------------------------------
# Background Pipeline Execution (Stages 1 to 8)
# ---------------------------------------------------------------------------

from researchclaw.pipeline.full_runner import execute_full_pipeline

async def _execute_pipeline(session: RunSession) -> None:
    """Execute the full 8-stage research pipeline with complete Frontend contract events."""
    await execute_full_pipeline(session)

async def _legacy_pipeline(session: RunSession) -> None:

    try:
        # --- 1. Run Initial Events ---
        await session.emit_event(
            "run.started",
            {"mode": mode, "topic": topic, "domains": domains},
        )

        has_scope_gate = mode == "full"
        has_screen_gate = mode in ("copilot", "full")

        await session.emit_event(
            "run.plan",
            {
                "stages": [
                    {
                        "key": "scope",
                        "stage": "scope",
                        "title": "Scope the question",
                        "has_gate": has_scope_gate,
                        "pipeline": [1, 2],
                    },
                    {
                        "key": "search",
                        "stage": "search",
                        "title": "Search the literature",
                        "has_gate": False,
                        "pipeline": [3, 4],
                    },
                    {
                        "key": "screen",
                        "stage": "screen",
                        "title": "Screen the papers",
                        "has_gate": has_screen_gate,
                        "pipeline": [5],
                    },
                    {
                        "key": "read",
                        "stage": "read",
                        "title": "Read and extract",
                        "has_gate": False,
                        "pipeline": [6],
                    },
                    {
                        "key": "synthesize",
                        "stage": "synthesize",
                        "title": "Find the gaps",
                        "has_gate": False,
                        "pipeline": [7],
                    },
                    {
                        "key": "r1-hypothesize",
                        "stage": "hypothesize",
                        "title": "Hypothesize",
                        "has_gate": False,
                        "pipeline": [8],
                    },
                ]
            },
        )

        # -------------------------------------------------------------------
        # STAGE 1 & 2: SCOPE
        # -------------------------------------------------------------------
        await session.emit_event(
            "stage.started",
            {
                "plan": {
                    "key": "scope",
                    "stage": "scope",
                    "title": "Scope the question",
                    "has_gate": has_scope_gate,
                    "pipeline": [1, 2],
                    "purpose": "Analyze research feasibility, compute environment, and decompose sub-questions.",
                    "reads": ["Your topic", "Your fields"],
                    "cast": ["strategist", "pi"],
                    "steps": [
                        {"id": "profile", "title": "Check environment", "actor": "strategist", "explain": "Inspect compute and resources", "pipeline_stage": 1, "artifact": "Compute profile"},
                        {"id": "goal", "title": "Set the goal", "actor": "strategist", "explain": "Formalize research problem statement", "pipeline_stage": 1, "artifact": "Research goal"},
                        {"id": "decompose", "title": "Decompose into sub-questions", "actor": "strategist", "explain": "Break down into actionable hypotheses", "pipeline_stage": 2, "artifact": "Sub-question tree"},
                        {"id": "evaluate", "title": "Rate the topic", "actor": "pi", "explain": "Score feasibility and novelty", "pipeline_stage": 2, "artifact": "Topic score"},
                    ],
                }
            },
            stage_key="scope",
            actor="strategist",
        )

        # Step 1: profile
        await session.emit_event("step.started", {"step_id": "profile"}, stage_key="scope", actor="strategist")
        await asyncio.sleep(1.0)
        await session.emit_event(
            "scope.profile",
            {"gpu_count": 1, "gpu_model": "NVIDIA RTX / Cloud Virtual Node", "vram_gb": 24, "disk_gb": 120},
            stage_key="scope",
            actor="strategist",
        )
        await session.emit_event(
            "agent.message",
            {"message_id": "msg-scope-1", "text": "Hardware and environment verified. Ready for research decomposition.", "done": True},
            stage_key="scope",
            actor="strategist",
        )
        await session.emit_event("step.completed", {"step_id": "profile"}, stage_key="scope", actor="strategist")

        # Step 2: goal
        await session.emit_event("step.started", {"step_id": "goal"}, stage_key="scope", actor="strategist")
        await asyncio.sleep(1.2)
        await session.emit_event(
            "scope.goal",
            {"statement": f"Investigate core mechanisms and empirical evidence for: {topic}", "fields": domains, "budget_usd": str(session.budget_usd)},
            stage_key="scope",
            actor="strategist",
        )
        await session.emit_event(
            "agent.message",
            {"message_id": "msg-scope-2", "text": f"Defined research goal across {', '.join(domains)}.", "done": True},
            stage_key="scope",
            actor="strategist",
        )
        await session.emit_event("step.completed", {"step_id": "goal"}, stage_key="scope", actor="strategist")

        # Step 3: decompose
        await session.emit_event("step.started", {"step_id": "decompose"}, stage_key="scope", actor="strategist")
        await asyncio.sleep(1.5)
        await session.emit_event(
            "problem.subquestion",
            {"sub_question": {"id": "SQ1", "text": f"What are the baseline correlation factors in {domains[0]}?", "priority": 1, "tests": "Literature cross-examination", "covers": ["Primary factors"]}},
            stage_key="scope",
            actor="strategist",
        )
        await session.emit_event(
            "problem.subquestion",
            {"sub_question": {"id": "SQ2", "text": "What confounding variables distort observational claims?", "priority": 2, "tests": "Counter-factual synthesis", "covers": ["Confounding control"]}},
            stage_key="scope",
            actor="strategist",
        )
        await session.emit_event(
            "problem.risk",
            {"risk": {"id": "R1", "sq_id": "SQ1", "text": "Sparse public benchmarks or conflicting metric definitions", "level": "medium"}},
            stage_key="scope",
            actor="strategist",
        )
        await session.emit_event(
            "agent.message",
            {"message_id": "msg-scope-3", "text": "Decomposed the problem into 2 core sub-questions and identified critical risks.", "done": True},
            stage_key="scope",
            actor="strategist",
        )
        await session.emit_event("step.completed", {"step_id": "decompose"}, stage_key="scope", actor="strategist")

        # Step 4: evaluate
        await session.emit_event("step.started", {"step_id": "evaluate"}, stage_key="scope", actor="pi")
        await asyncio.sleep(1.0)
        await session.emit_event(
            "problem.score",
            {"overall": 8.7, "novelty": 8.5, "feasibility": 9.0, "clarity": 8.6, "verdict": "approved"},
            stage_key="scope",
            actor="pi",
        )
        await session.emit_event(
            "agent.message",
            {"message_id": "msg-scope-4", "text": "Principal Investigator scored feasibility at 8.7/10. Greenlit for literature search.", "done": True},
            stage_key="scope",
            actor="pi",
        )
        await session.emit_event("step.completed", {"step_id": "evaluate"}, stage_key="scope", actor="pi")
        await session.emit_event("stage.completed", {"summary": "Scoped topic with 2 sub-questions and 8.7 feasibility rating."}, stage_key="scope", actor="pi")

        # -------------------------------------------------------------------
        # STAGE 3 & 4: SEARCH & CITATION
        # -------------------------------------------------------------------
        await session.emit_event(
            "stage.started",
            {
                "plan": {
                    "key": "search",
                    "stage": "search",
                    "title": "Search the literature",
                    "has_gate": False,
                    "pipeline": [3, 4],
                    "purpose": "Query academic repositories, expand citation graph, and deduplicate candidates.",
                    "reads": ["Sub-question tree"],
                    "cast": ["librarian"],
                    "steps": [
                        {"id": "query_gen", "title": "Formulate search queries", "actor": "librarian", "explain": "Translate sub-questions into search operators", "pipeline_stage": 3, "artifact": "Query plan"},
                        {"id": "harvest", "title": "Harvest academic papers", "actor": "librarian", "explain": "Fetch candidate papers from ArXiv and Semantic Scholar", "pipeline_stage": 3, "artifact": "Harvested papers"},
                        {"id": "dedup", "title": "Cluster & deduplicate", "actor": "librarian", "explain": "Merge citation duplicates", "pipeline_stage": 4, "artifact": "Unique paper corpus"},
                    ],
                }
            },
            stage_key="search",
            actor="librarian",
        )

        await session.emit_event("step.started", {"step_id": "query_gen"}, stage_key="search", actor="librarian")
        await asyncio.sleep(1.2)
        await session.emit_event(
            "search.strategy",
            {"strategy": {"id": "S1", "name": "Direct Keyword & Boolean Strategy", "terms": [topic.split()[0], "evaluation", "empirical methodology"]}},
            stage_key="search",
            actor="librarian",
        )
        await session.emit_event(
            "search.query",
            {"query": {"id": "q1", "strategy_id": "S1", "text": f"{topic} empirical study benchmarks"}},
            stage_key="search",
            actor="librarian",
        )
        await session.emit_event("step.completed", {"step_id": "query_gen"}, stage_key="search", actor="librarian")

        await session.emit_event("step.started", {"step_id": "harvest"}, stage_key="search", actor="librarian")
        await asyncio.sleep(1.8)
        # Sample realistic papers
        sample_papers = [
            {"id": "paper_2024_01", "title": "Empirical Dynamics in Autonomous Research Architectures", "authors": ["Dr. J. Smith", "A. Lee"], "year": 2024, "venue": "NeurIPS", "citations": 42},
            {"id": "paper_2023_02", "title": "Systematic Methodology for Multi-Agent Literature Extraction", "authors": ["M. Chen", "R. Davis"], "year": 2023, "venue": "ICLR", "citations": 88},
            {"id": "paper_2022_03", "title": "Foundational Limitations in Observational Causal Bounds", "authors": ["K. Walker"], "year": 2022, "venue": "Nature Machine Intelligence", "citations": 150},
        ]
        for p in sample_papers:
            await session.emit_event("search.paper", {"paper": p}, stage_key="search", actor="librarian")
        await session.emit_event("step.completed", {"step_id": "harvest"}, stage_key="search", actor="librarian")

        await session.emit_event("step.started", {"step_id": "dedup"}, stage_key="search", actor="librarian")
        await asyncio.sleep(1.0)
        await session.emit_event("search.cluster", {"unique_count": 3, "duplicates_merged": 1}, stage_key="search", actor="librarian")
        await session.emit_event(
            "agent.message",
            {"message_id": "msg-search-1", "text": "Harvested 3 high-impact relevant papers, deduplicated successfully.", "done": True},
            stage_key="search",
            actor="librarian",
        )
        await session.emit_event("step.completed", {"step_id": "dedup"}, stage_key="search", actor="librarian")
        await session.emit_event("stage.completed", {"summary": "Retrieved 3 unique candidate papers across target domains."}, stage_key="search", actor="librarian")

        # -------------------------------------------------------------------
        # STAGE 5: SCREEN (HUMAN IN THE LOOP GATE)
        # -------------------------------------------------------------------
        await session.emit_event(
            "stage.started",
            {
                "plan": {
                    "key": "screen",
                    "stage": "screen",
                    "title": "Screen the papers",
                    "has_gate": has_screen_gate,
                    "pipeline": [5],
                    "purpose": "Filter papers according to relevance, methodology rigor, and human review.",
                    "reads": ["Unique paper corpus"],
                    "cast": ["theorist", "pi"],
                    "steps": [
                        {"id": "criteria", "title": "Apply screening criteria", "actor": "theorist", "explain": "Calculate relevance and rigor scores", "pipeline_stage": 5, "artifact": "Screened scores"},
                        {"id": "shortlist", "title": "Generate shortlist", "actor": "theorist", "explain": "Produce candidate shortlist for PI approval", "pipeline_stage": 5, "artifact": "Paper shortlist"},
                        {"id": "screen_gate", "title": "Human check: paper shortlist", "actor": "pi", "explain": "Review and drop non-essential literature", "gate": "screen", "pipeline_stage": 5, "artifact": "Approved literature"},
                    ],
                }
            },
            stage_key="screen",
            actor="theorist",
        )

        await session.emit_event("step.started", {"step_id": "criteria"}, stage_key="screen", actor="theorist")
        await asyncio.sleep(1.2)
        await session.emit_event(
            "screen.criterion",
            {"criteria": [{"id": "c1", "name": "Direct Domain Relevance", "weight": 0.6}, {"id": "c2", "name": "Empirical Rigor", "weight": 0.4}]},
            stage_key="screen",
            actor="theorist",
        )
        for p in sample_papers:
            rel = 9.2 if p["id"] != "paper_2022_03" else 7.8
            await session.emit_event(
                "screen.scored",
                {
                    "points": [{"id": p["id"], "relevance": rel, "quality": 8.5}],
                    "paper_id": p["id"],
                    "score": rel,
                    "decision": "include",
                },
                stage_key="screen",
                actor="theorist",
            )
        await session.emit_event("step.completed", {"step_id": "criteria"}, stage_key="screen", actor="theorist")

        await session.emit_event("step.started", {"step_id": "shortlist"}, stage_key="screen", actor="theorist")
        await asyncio.sleep(1.0)
        shortlist_ids = [p["id"] for p in sample_papers]
        await session.emit_event("screen.shortlist", {"paper_ids": shortlist_ids, "count": len(shortlist_ids)}, stage_key="screen", actor="theorist")
        await session.emit_event("step.completed", {"step_id": "shortlist"}, stage_key="screen", actor="theorist")

        # Step: screen_gate
        await session.emit_event("step.started", {"step_id": "screen_gate"}, stage_key="screen", actor="pi")
        await session.emit_event(
            "agent.message",
            {"message_id": "msg-screen-gate", "text": "Screening complete. Shortlist of 3 papers prepared for human review.", "done": True},
            stage_key="screen",
            actor="pi",
        )

        if has_screen_gate:
            session.status = "awaiting_review"
            session.pending_gate = {
                "gate_id": "gate-1",
                "options": [{"id": "approve", "label": "Approve literature shortlist"}, {"id": "drop", "label": "Drop selected papers"}],
                "droppable": shortlist_ids,
            }

            # Emit awaiting_review status and gate.opened
            await session.emit_event("run.status", {"status": "awaiting_review"}, stage_key="screen")
            await session.emit_event(
                "gate.opened",
                {
                    "gate_id": "gate-1",
                    "kind": "screen",
                    "title": "Review Paper Shortlist",
                    "options": session.pending_gate["options"],
                    "droppable": session.pending_gate["droppable"],
                },
                stage_key="screen",
                actor="pi",
            )

            logger.info(f"Run {session.popper_run_id} is awaiting gate-1 approval from human reviewer...")
            # Wait until gate is resolved via POST /runs/{id}/gates/{gate_id}
            await session.gate_event.wait()

            # Process dropped papers if any
            if session.gate_answer and "dropped" in session.gate_answer:
                dropped = set(session.gate_answer["dropped"])
                surviving_papers = [p for p in sample_papers if p["id"] not in dropped]
            else:
                surviving_papers = sample_papers
            session.status = "running"
        else:
            surviving_papers = sample_papers

        await session.emit_event("step.completed", {"step_id": "screen_gate"}, stage_key="screen", actor="pi")
        await session.emit_event("stage.completed", {"summary": f"Approved {len(surviving_papers)} papers for deep reading."}, stage_key="screen", actor="pi")

        # -------------------------------------------------------------------
        # STAGE 6: READ & CLAIM EXTRACTION
        # -------------------------------------------------------------------
        await session.emit_event(
            "stage.started",
            {
                "plan": {
                    "key": "read",
                    "stage": "read",
                    "title": "Read and extract",
                    "has_gate": False,
                    "pipeline": [6],
                    "purpose": "Perform deep reading of shortlisted papers and extract structured claim cards.",
                    "reads": ["Approved literature"],
                    "cast": ["theorist", "skeptic"],
                    "steps": [
                        {"id": "read_papers", "title": "Extract evidence cards", "actor": "theorist", "explain": "Extract claims, evidence, and bounds", "pipeline_stage": 6, "artifact": "Claim cards"},
                        {"id": "skeptic_audit", "title": "Audit methodological claims", "actor": "skeptic", "explain": "Inspect assumptions and statistical rigor", "pipeline_stage": 6, "artifact": "Audit report"},
                    ],
                }
            },
            stage_key="read",
            actor="theorist",
        )

        await session.emit_event("step.started", {"step_id": "read_papers"}, stage_key="read", actor="theorist")
        await asyncio.sleep(1.8)
        claim_cards = [
            {"id": "C1", "paper_id": surviving_papers[0]["id"], "claim": "Autonomous feedback loops demonstrate statistically significant convergence gains.", "confidence": 0.89},
            {"id": "C2", "paper_id": surviving_papers[-1]["id"], "claim": "Observational correlation degrades when unmeasured environmental latencies occur.", "confidence": 0.84},
        ]
        for c in claim_cards:
            await session.emit_event("read.card", {"card": c}, stage_key="read", actor="theorist")
        await session.emit_event("step.completed", {"step_id": "read_papers"}, stage_key="read", actor="theorist")

        await session.emit_event("step.started", {"step_id": "skeptic_audit"}, stage_key="read", actor="skeptic")
        await asyncio.sleep(1.2)
        await session.emit_event(
            "agent.message",
            {"message_id": "msg-read-1", "text": "Audited claims: high internal validity with verifiable empirical replications.", "done": True},
            stage_key="read",
            actor="skeptic",
        )
        await session.emit_event("step.completed", {"step_id": "skeptic_audit"}, stage_key="read", actor="skeptic")
        await session.emit_event("stage.completed", {"summary": f"Extracted {len(claim_cards)} verified claim cards."}, stage_key="read", actor="theorist")

        # -------------------------------------------------------------------
        # STAGE 7: SYNTHESIZE & GAP DISCOVERY
        # -------------------------------------------------------------------
        await session.emit_event(
            "stage.started",
            {
                "plan": {
                    "key": "synthesize",
                    "stage": "synthesize",
                    "title": "Find the gaps",
                    "has_gate": False,
                    "pipeline": [7],
                    "purpose": "Synthesize claims across papers, expose contradictions, and map research gaps.",
                    "reads": ["Claim cards"],
                    "cast": ["methodologist", "skeptic"],
                    "steps": [
                        {"id": "map_gaps", "title": "Map knowledge gaps", "actor": "methodologist", "explain": "Isolate unaddressed theoretical frontiers", "pipeline_stage": 7, "artifact": "Gap map"},
                    ],
                }
            },
            stage_key="synthesize",
            actor="methodologist",
        )

        await session.emit_event("step.started", {"step_id": "map_gaps"}, stage_key="synthesize", actor="methodologist")
        await asyncio.sleep(1.8)
        await session.emit_event(
            "synth.gap",
            {"gap": {"id": "G1", "title": "Absence of real-time multi-agent arbitration benchmarks", "severity": "high", "unaddressed_by": [p["id"] for p in surviving_papers]}},
            stage_key="synthesize",
            actor="methodologist",
        )
        await session.emit_event(
            "agent.message",
            {"message_id": "msg-synth-1", "text": "Synthesized literature landscape: identified 1 major unaddressed research gap (G1).", "done": True},
            stage_key="synthesize",
            actor="methodologist",
        )
        await session.emit_event("step.completed", {"step_id": "map_gaps"}, stage_key="synthesize", actor="methodologist")
        await session.emit_event("stage.completed", {"summary": "Synthesized literature and isolated key empirical gap G1."}, stage_key="synthesize", actor="methodologist")

        # -------------------------------------------------------------------
        # STAGE 8: HYPOTHESIZE
        # -------------------------------------------------------------------
        await session.emit_event(
            "stage.started",
            {
                "plan": {
                    "key": "r1-hypothesize",
                    "stage": "hypothesize",
                    "title": "Hypothesize",
                    "has_gate": False,
                    "pipeline": [8],
                    "purpose": "Formulate testable scientific hypotheses targeting identified knowledge gaps.",
                    "reads": ["Gap map"],
                    "cast": ["pi"],
                    "steps": [
                        {"id": "formulate", "title": "Generate hypothesis candidates", "actor": "pi", "explain": "Construct formal falsifiable statements", "pipeline_stage": 8, "artifact": "Hypothesis candidates"},
                        {"id": "select", "title": "Final hypothesis selection", "actor": "pi", "explain": "Pick top hypothesis with verifiable evaluation protocol", "pipeline_stage": 8, "artifact": "Selected hypothesis set"},
                    ],
                }
            },
            stage_key="r1-hypothesize",
            actor="pi",
        )

        await session.emit_event("step.started", {"step_id": "formulate"}, stage_key="r1-hypothesize", actor="pi")
        await asyncio.sleep(2.0)
        hypotheses = [
            {"id": "H1", "statement": f"Integrating adaptive causal pruning into multi-agent systems reduces latency by over 30% while preserving empirical alignment on: {topic}.", "score": 9.3},
            {"id": "H2", "statement": f"Explicit counterfactual validation tokens prevent degenerative consensus in autonomous agent tournaments.", "score": 8.7},
        ]
        for h in hypotheses:
            await session.emit_event("hypo.candidate", {"hypothesis": h}, stage_key="r1-hypothesize", actor="pi")
        await session.emit_event("step.completed", {"step_id": "formulate"}, stage_key="r1-hypothesize", actor="pi")

        await session.emit_event("step.started", {"step_id": "select"}, stage_key="r1-hypothesize", actor="pi")
        await asyncio.sleep(1.2)
        await session.emit_event(
            "hypo.selected",
            {"selected_id": "H1", "justification": "Highest empirical testability and strongest alignment with identified gap G1."},
            stage_key="r1-hypothesize",
            actor="pi",
        )
        await session.emit_event(
            "agent.message",
            {"message_id": "msg-hypo-1", "text": "PI finalized selected hypothesis H1 with rigorous validation protocol.", "done": True},
            stage_key="r1-hypothesize",
            actor="pi",
        )
        await session.emit_event("step.completed", {"step_id": "select"}, stage_key="r1-hypothesize", actor="pi")
        await session.emit_event("stage.completed", {"summary": "Selected hypothesis H1 successfully formulated."}, stage_key="r1-hypothesize", actor="pi")

        # -------------------------------------------------------------------
        # RUN COMPLETION
        # -------------------------------------------------------------------
        session.status = "completed"
        session.cost_usd = Decimal("0.18")
        await session.emit_event("run.completed", {}, stage_key=None, actor=None)
        logger.info(f"Run {session.popper_run_id} completed successfully.")

    except asyncio.CancelledError:
        logger.info(f"Run {session.popper_run_id} was cancelled.")
        session.status = "failed"
        session.message = "Cancelled by user"
    except Exception as e:
        logger.exception(f"Error executing run {session.popper_run_id}: {e}")
        session.status = "failed"
        session.message = str(e)
        await session.emit_event("run.status", {"status": "failed", "reason": str(e)})


# ---------------------------------------------------------------------------
# API Endpoints (8 Clean Endpoints)
# ---------------------------------------------------------------------------

@router.post(
    "/runs",
    status_code=status.HTTP_201_CREATED,
    response_model=RunCreateResponse,
    summary="Start a new research run (Asynchronous Webhook Worker)",
)
async def start_run(
    req: RunCreateRequest,
    x_service_key: str | None = Header(None, alias="X-Service-Key"),
) -> Any:
    """Start an 8-stage research run from topic to hypothesis."""
    # Idempotency check: if platform_run_id already started, return existing run
    if req.platform_run_id in _PLATFORM_MAP:
        existing_id = _PLATFORM_MAP[req.platform_run_id]
        existing_session = _ACTIVE_RUNS[existing_id]
        return RunCreateResponse(
            popper_run_id=existing_session.popper_run_id,
            status=existing_session.status,
            cost_usd=str(existing_session.cost_usd),
            message=existing_session.message,
        )

    popper_run_id = f"eng-{uuid4().hex[:12]}"
    session = RunSession(popper_run_id, req, service_key=x_service_key)
    _ACTIVE_RUNS[popper_run_id] = session
    _PLATFORM_MAP[req.platform_run_id] = popper_run_id

    # Spawn background worker
    session.task = asyncio.create_task(_execute_pipeline(session))

    return RunCreateResponse(
        popper_run_id=popper_run_id,
        status="running",
        cost_usd="0.00",
        message=None,
    )


@router.get(
    "/runs/{popper_run_id}",
    response_model=RunStateResponse,
    summary="Get current run status by popper_run_id or platform_run_id",
)
async def get_run_status(popper_run_id: str) -> RunStateResponse:
    # Resolve if caller supplied a platform_run_id UUID instead
    resolved_id = _PLATFORM_MAP.get(popper_run_id, popper_run_id)
    session = _ACTIVE_RUNS.get(resolved_id)
    if not session:
        raise HTTPException(status_code=404, detail="Run not found")

    return RunStateResponse(
        popper_run_id=session.popper_run_id,
        status=session.status,
        cost_usd=str(session.cost_usd),
        message=session.message,
        last_source_seq=session.current_source_seq,
    )


@router.get(
    "/runs",
    response_model=RunStateResponse,
    summary="Find run by platform_run_id query parameter",
)
async def find_run(
    platform_run_id: str = Query(..., description="Platform Run UUID")
) -> RunStateResponse:
    if platform_run_id not in _PLATFORM_MAP:
        raise HTTPException(status_code=404, detail="Run with given platform_run_id not found")

    popper_id = _PLATFORM_MAP[platform_run_id]
    session = _ACTIVE_RUNS[popper_id]
    return RunStateResponse(
        popper_run_id=session.popper_run_id,
        status=session.status,
        cost_usd=str(session.cost_usd),
        message=session.message,
        last_source_seq=session.current_source_seq,
    )


@router.get(
    "/runs/{popper_run_id}/events",
    response_model=EventsBatchResponse,
    summary="Fetch events for sync/recovery (after_source_seq)",
)
async def get_run_events(
    popper_run_id: str,
    after_source_seq: int = Query(0, ge=0),
    limit: int = Query(500, ge=1, le=1000),
) -> EventsBatchResponse:
    resolved_id = _PLATFORM_MAP.get(popper_run_id, popper_run_id)
    session = _ACTIVE_RUNS.get(resolved_id)
    if not session:
        raise HTTPException(status_code=404, detail="Run not found")

    filtered = [
        EventItem(**evt)
        for evt in session.events
        if evt["source_seq"] > after_source_seq
    ][:limit]

    return EventsBatchResponse(events=filtered)


@router.post(
    "/runs/{popper_run_id}/gates/{gate_id}",
    summary="Submit human decision for gate (Screen Gate)",
)
async def submit_gate_answer(
    popper_run_id: str,
    gate_id: str,
    answer: GateAnswerRequest,
) -> dict[str, Any]:
    resolved_id = _PLATFORM_MAP.get(popper_run_id, popper_run_id)
    session = _ACTIVE_RUNS.get(resolved_id)
    if not session:
        raise HTTPException(status_code=404, detail="Run not found")

    if session.status != "awaiting_review" or not session.pending_gate:
        # Check if already resolved idempotently
        if session.gate_answer and session.gate_answer.get("option_id") == answer.option_id:
            return {"status": "ok", "message": "Gate already resolved"}
        raise HTTPException(status_code=409, detail="GATE_NOT_OPEN")

    if session.pending_gate.get("gate_id") != gate_id:
        raise HTTPException(status_code=404, detail="Gate ID mismatch")

    # Record answer and unblock pipeline
    session.gate_answer = answer.model_dump()
    session.pending_gate = None
    session.gate_event.set()

    return {"status": "ok", "message": "Gate answer accepted"}


@router.post(
    "/runs/{popper_run_id}/pause",
    summary="Pause run at next safe step",
)
async def pause_run(popper_run_id: str) -> dict[str, str]:
    resolved_id = _PLATFORM_MAP.get(popper_run_id, popper_run_id)
    session = _ACTIVE_RUNS.get(resolved_id)
    if not session:
        raise HTTPException(status_code=404, detail="Run not found")

    if session.status in ("completed", "failed"):
        raise HTTPException(status_code=409, detail="RUN_FINISHED")

    session.pause_event.clear()
    session.status = "paused"
    return {"status": "ok", "message": "Run paused"}


@router.post(
    "/runs/{popper_run_id}/resume",
    summary="Resume paused run",
)
async def resume_run(popper_run_id: str) -> dict[str, str]:
    resolved_id = _PLATFORM_MAP.get(popper_run_id, popper_run_id)
    session = _ACTIVE_RUNS.get(resolved_id)
    if not session:
        raise HTTPException(status_code=404, detail="Run not found")

    if session.status in ("completed", "failed"):
        raise HTTPException(status_code=409, detail="RUN_FINISHED")

    session.status = "running"
    session.pause_event.set()
    return {"status": "ok", "message": "Run resumed"}


@router.post(
    "/runs/{popper_run_id}/cancel",
    summary="Cancel and release run resources",
)
async def cancel_run(popper_run_id: str) -> dict[str, str]:
    resolved_id = _PLATFORM_MAP.get(popper_run_id, popper_run_id)
    session = _ACTIVE_RUNS.get(resolved_id)
    if not session:
        raise HTTPException(status_code=404, detail="Run not found")

    session.is_cancelled = True
    session.pause_event.set()
    session.gate_event.set()
    if session.task and not session.task.done():
        session.task.cancel()

    session.status = "failed"
    session.message = "Cancelled by user"
    return {"status": "ok", "message": "Run cancelled"}
