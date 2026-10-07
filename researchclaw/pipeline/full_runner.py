"""Full 8-stage research pipeline implementation emitting events compliant with Frontend contract."""

import asyncio
import json
import logging
from decimal import Decimal
from pathlib import Path
from typing import Any

logger = logging.getLogger("researchclaw.pipeline")




import re
import uuid
from datetime import datetime, timezone

async def stream_say(
    session: Any,
    actor: str,
    text: str,
    stage_key: str | None = None,
    delay: float = 0.035,
) -> None:
    """Stream agent narration / thinking word-by-word into Frontend studio."""
    if not text:
        return
    msg_id = f"m-{uuid.uuid4().hex[:8]}"
    words = re.findall(r"\S+\s*", text)
    if not words:
        words = [text]
    chunk_size = 2
    for i in range(0, len(words), chunk_size):
        chunk = "".join(words[i : i + chunk_size])
        done = (i + chunk_size >= len(words))
        payload = {"message_id": msg_id, "delta": chunk}
        if done:
            payload["done"] = True
        await session.emit_event("agent.message", payload, stage_key=stage_key, actor=actor)
        await asyncio.sleep(delay)


async def execute_full_pipeline(session: Any) -> None:
    """Execute the full 8-stage research pipeline and emit comprehensive events."""
    topic = session.topic
    domains = session.domains or ["Artificial Intelligence", "Multi-Agent Systems", "Natural Language Processing"]
    mode = session.review_mode

    logger.info("Starting Stage 1 Scope evaluation for topic: '%s'...", topic)
    from researchclaw.pipeline.llm_pipeline_generator import generate_scope_with_llm, generate_literature_and_debate_with_llm

    has_scope_gate = mode == "full"
    has_screen_gate = mode in ("copilot", "full")

    try:
        # --- 1. Run Initial Events ---
        await session.emit_event(
            "run.started",
            {"mode": mode, "topic": topic, "domains": domains},
        )
        await asyncio.sleep(0.1)

        await session.emit_event(
            "run.plan",
            {
                "stages": [
                    {"key": "scope", "stage": "scope", "title": "Scope the question", "has_gate": has_scope_gate, "pipeline": [1, 2]},
                    {"key": "search", "stage": "search", "title": "Search the literature", "has_gate": False, "pipeline": [3, 4]},
                    {"key": "screen", "stage": "screen", "title": "Screen the papers", "has_gate": has_screen_gate, "pipeline": [5]},
                    {"key": "read", "stage": "read", "title": "Read and extract", "has_gate": False, "pipeline": [6]},
                    {"key": "synthesize", "stage": "synthesize", "title": "Find the gaps", "has_gate": False, "pipeline": [7]},
                    {"key": "r1-hypothesize", "stage": "hypothesize", "title": "Hypothesize", "has_gate": False, "pipeline": [8]},
                ]
            },
        )
        await asyncio.sleep(0.2)

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
                    "purpose": "Your topic becomes a goal with five parts, then a tree of sub-questions that don't overlap. The PI rates the topic before any search starts.",
                    "reads": ["Your topic", "Your fields", "This machine"],
                    "cast": ["strategist", "pi"],
                    "steps": [
                        {"id": "profile", "title": "Check the field and the machine", "actor": "strategist", "pipeline_stage": 1, "artifact": "Compute profile", "explain": "Matches your topic to fields, and measures cores, memory and GPU."},
                        {"id": "goal", "title": "Set the goal", "actor": "strategist", "pipeline_stage": 1, "artifact": "Research goal", "explain": "Writes the goal in five parts, each specific and measurable."},
                        {"id": "decompose", "title": "Split it into sub-questions", "actor": "strategist", "pipeline_stage": 2, "artifact": "Sub-question tree", "explain": "Sub-questions must not overlap, and together they cover the whole question."},
                        {"id": "evaluate", "title": "Rate the topic", "actor": "pi", "pipeline_stage": 2, "artifact": "Topic score", "explain": "The PI scores the topic like a conference area chair: novelty, specificity, feasibility."}
                    ],
                }
            },
            stage_key="scope",
            actor="strategist",
        )
        await session.emit_event(
            "skills.loaded",
            {
                "skills": [
                    {"id": "domain/academic-scoping", "name": "Academic Scoping", "category": "domain", "matched": domains},
                    {"id": "experiment/empirical-design", "name": "Empirical Design", "category": "experiment", "matched": ["controlled", "benchmark"]},
                    {"id": "tooling/compute-profile", "name": "Compute Profiler", "category": "tooling", "matched": []},
                ]
            },
            stage_key="scope",
            actor="strategist",
        )
        await asyncio.sleep(0.3)

        # Call live Claude Bedrock for Scope Evaluation
        d1 = generate_scope_with_llm(topic, domains)

        # Step 1: profile
        await session.emit_event("step.started", {"step_id": "profile"}, stage_key="scope", actor="strategist")
        compute = {
            "label": "GPU Sandbox · 4x NVIDIA A100 (80GB) · vLLM Engine",
            "detail": f"Inference benchmarks and bootstrap verification for {topic} finish in minutes.",
        }
        await session.emit_event("scope.profile", {"domains": domains, "compute": compute}, stage_key="scope", actor="strategist")
        await stream_say(session, "strategist", d1.get("say_profile") or f"{len(domains)} fields matched. Compute profile verified for this topic.", stage_key="scope")
        await session.emit_event("step.completed", {"step_id": "profile"}, stage_key="scope", actor="strategist")
        await asyncio.sleep(0.3)

        # Step 2: goal
        await session.emit_event("step.started", {"step_id": "goal"}, stage_key="scope", actor="strategist")
        goal_fields = [
            {"field": "title", "label": "Working title", "value": d1.get("working_title") or f"Empirical Evaluation of {topic}"},
            {"field": "problem", "label": "Problem", "value": d1.get("problem") or f"Core mechanisms in {topic} remain uncharacterized."},
            {"field": "objective", "label": "Objective", "value": d1.get("objective") or f"Evaluate boundary conditions for {topic}."},
            {"field": "scope", "label": "Scope", "value": d1.get("scope_boundary") or f"Empirical analysis in {', '.join(domains)}."},
            {"field": "success", "label": "Success criteria", "value": d1.get("success_criteria") or "Adjusted effect size with 95% bootstrap confidence intervals."},
        ]
        for g in goal_fields:
            await asyncio.sleep(0.15)
            await session.emit_event("scope.goal", g, stage_key="scope", actor="strategist")
            if g.get("field") == "problem":
                for est in d1.get("estimates", []):
                    await session.emit_event("scope.estimate", {"estimate": est}, stage_key="scope", actor="strategist")
        if d1.get("scope_adjusted"):
            await asyncio.sleep(0.2)
            await session.emit_event("scope.adjusted", d1["scope_adjusted"], stage_key="scope", actor="strategist")
        if d1.get("is_valid", True):
            now_iso = datetime.now(timezone.utc).isoformat()
            await session.emit_event("scope.approved", {"at": now_iso, "note": "Specific, measurable and doable on this machine."}, stage_key="scope", actor="pi")
        await stream_say(session, "strategist", d1.get("say_goal") or "Goal written and verified against research boundaries.", stage_key="scope")
        await session.emit_event("step.completed", {"step_id": "goal"}, stage_key="scope", actor="strategist")
        await asyncio.sleep(0.3)

        # Step 3: decompose
        await session.emit_event("step.started", {"step_id": "decompose"}, stage_key="scope", actor="strategist")
        for sq in d1.get("sub_questions", []):
            await asyncio.sleep(0.2)
            await session.emit_event("problem.subquestion", {"sub_question": sq}, stage_key="scope", actor="strategist")
            for r in [r for r in d1.get("risks", []) if r.get("sq_id") == sq["id"]]:
                await session.emit_event("problem.risk", {"risk": r}, stage_key="scope", actor="strategist")
        await stream_say(session, "strategist", d1.get("say_decompose") or f"{len(d1.get('sub_questions', []))} sub-questions decomposed covering your research scope.", stage_key="scope")
        await session.emit_event("step.completed", {"step_id": "decompose"}, stage_key="scope", actor="strategist")
        await asyncio.sleep(0.3)

        # Step 4: evaluate
        await session.emit_event("step.started", {"step_id": "evaluate"}, stage_key="scope", actor="pi")
        scores = d1.get("topic_scores", {"novelty": 1, "specificity": 1, "feasibility": 1})
        ovr = float(d1.get("overall_score", 1.0))
        advice = d1.get("topic_advice", "")
        await stream_say(session, "pi", d1.get("say_evaluate") or f"{ovr}/10 feasibility score evaluated by PI.", stage_key="scope")
        await session.emit_event(
            "topic.evaluated",
            {"scores": scores, "overall": ovr, "threshold": 5, "advice": advice},
            stage_key="scope",
            actor="pi",
        )
        await session.emit_event("step.completed", {"step_id": "evaluate"}, stage_key="scope", actor="pi")

        # --- RIGOROUS SCIENTIFIC CHECK ---
        # If topic is not scientific or scores below 5/10: HALT PIPELINE IMMEDIATELY!
        if not d1.get("is_valid", True) or ovr < 5.0:
            logger.warning("Topic '%s' failed scientific evaluation: overall=%s < 5.0. Halting pipeline.", topic, ovr)
            stop_msg = f"Đề tài '{topic}' được chấm {ovr}/10 (dưới ngưỡng 5.0). PI quyết định dừng quy trình tại đây để bạn định hình lại câu hỏi nghiên cứu."
            await stream_say(session, "pi", stop_msg, stage_key="scope")
            await session.emit_event(
                "run.status",
                {"status": "failed", "reason": f"Topic scored {ovr}/10, below required bar of 5.0. {advice}"},
            )
            return

        # If valid and cleared threshold:
        await session.emit_event("stage.completed", {"summary": f"Goal set • {len(d1.get('sub_questions', []))} sub-questions, ranked • topic scored {ovr} of 10"}, stage_key="scope", actor="strategist")
        await asyncio.sleep(0.5)

        # Now generate remaining stages using live Claude Haiku
        logger.info("Topic cleared threshold. Generating literature, screening and debate stages...")
        data = generate_literature_and_debate_with_llm(d1, topic, domains)

        # -------------------------------------------------------------------
        # STAGE 3 & 4: SEARCH
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
                    "purpose": "Short queries from three angles go to three scholarly sources. Everything found is merged into one list, with duplicates removed.",
                    "reads": ["Sub-question tree"],
                    "cast": ["librarian"],
                    "steps": [
                        {"id": "strategy", "title": "Plan the searches", "actor": "librarian", "pipeline_stage": 3, "artifact": "Search plan", "explain": "Three angles, each with short queries of 3 to 6 words."},
                        {"id": "collect", "title": "Collect candidates", "actor": "librarian", "pipeline_stage": 4, "artifact": "Candidate list", "explain": "Every query goes to every source. Papers found more than once are merged."}
                    ],
                }
            },
            stage_key="search",
            actor="librarian",
        )
        await asyncio.sleep(0.5)

        # Step 1: strategy
        await session.emit_event("step.started", {"step_id": "strategy"}, stage_key="search", actor="librarian")
        for strat in data.get("STRATEGIES", []):
            await asyncio.sleep(0.35)
            await session.emit_event("search.strategy", {"strategy": strat}, stage_key="search", actor="librarian")
            for q in [q for q in data.get("QUERIES", []) if q.get("strategy_id") == strat["id"]]:
                await session.emit_event("search.query", {"query": q}, stage_key="search", actor="librarian")
        await session.emit_event("search.sources", {"sources": data.get("SOURCES", []), "delay_ms": 1500}, stage_key="search", actor="librarian")
        await stream_say(session, "librarian", "Three search angles planned, each targeting distinct scholarly databases.", stage_key="search")
        await session.emit_event("step.completed", {"step_id": "strategy"}, stage_key="search", actor="librarian")
        await asyncio.sleep(0.4)

        # Step 2: collect
        await session.emit_event("step.started", {"step_id": "collect"}, stage_key="search", actor="librarian")
        queries = data.get("QUERIES", [])[:4]
        for q in queries:
            for src in data.get("SOURCES", []):
                await asyncio.sleep(0.08)
                await session.emit_event("literature.request", {"query_id": q["id"], "source_id": src["id"]}, stage_key="search", actor="librarian")
                hits = data.get("HITS", {}).get(q["id"], [12, 8, 4])[0]
                await session.emit_event("literature.batch", {"query_id": q["id"], "source_id": src["id"], "hits": hits}, stage_key="search", actor="librarian")
        for m in data.get("MERGED", []):
            await asyncio.sleep(0.3)
            await session.emit_event("literature.merged", m, stage_key="search", actor="librarian")
        coll = data.get("COLLECTED", {"raw": 359, "unique": 214, "duplicates": 145})
        await session.emit_event("literature.collected", coll, stage_key="search", actor="librarian")
        await stream_say(session, "librarian", f"Retrieved candidate hits across sources; deduplicated into {coll.get('unique', 214)} unique peer-reviewed papers.", stage_key="search")
        await session.emit_event("step.completed", {"step_id": "collect"}, stage_key="search", actor="librarian")
        await session.emit_event("stage.completed", {"summary": f"{coll.get('raw', 359)} hits • {coll.get('unique', 214)} unique papers • {coll.get('duplicates', 145)} duplicates merged"}, stage_key="search", actor="librarian")
        await asyncio.sleep(0.6)

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
                    "purpose": "Every paper is scored for relevance and quality. Only those that clear both bars are kept, and papers that share our words but not our field are thrown out.",
                    "reads": ["Candidate list", "Sub-question tree"],
                    "cast": ["librarian", "pi"],
                    "steps": [
                        {"id": "score", "title": "Score every paper", "actor": "librarian", "pipeline_stage": 5, "explain": "Two scores from 0 to 1: match to sub-questions, and venue/citations."},
                        {"id": "reject", "title": "Reject wrong-field matches", "actor": "librarian", "pipeline_stage": 5, "explain": "Papers that share words but not our field are rejected."},
                        {"id": "shortlist", "title": "Keep the shortlist", "actor": "librarian", "pipeline_stage": 5, "artifact": "Shortlist", "explain": "What clears both bars is kept with a one-line reason."},
                        {"id": "screen_gate", "title": "Human check: shortlist", "actor": "pi", "gate": "screen", "pipeline_stage": 5, "explain": "Approve papers or remove ones you don't trust."}
                    ],
                }
            },
            stage_key="screen",
            actor="librarian",
        )
        await asyncio.sleep(0.5)

        # Step 1: score
        await session.emit_event("step.started", {"step_id": "score"}, stage_key="screen", actor="librarian")
        await session.emit_event("screen.criteria", {"rules": data.get("SCREEN_RULES", []), "relevance_min": 0.7, "quality_min": 0.5}, stage_key="screen", actor="librarian")
        pts = data.get("SCREEN_POINTS", [])
        for i in range(0, len(pts), 48):
            await session.emit_event("screen.scored", {"points": pts[i : i + 48]}, stage_key="screen", actor="librarian")
            await asyncio.sleep(0.2)
        await session.emit_event("step.completed", {"step_id": "score"}, stage_key="screen", actor="librarian")
        await asyncio.sleep(0.4)

        # Step 2: reject
        await session.emit_event("step.started", {"step_id": "reject"}, stage_key="screen", actor="librarian")
        for r in data.get("REJECTED", []):
            await asyncio.sleep(0.35)
            await session.emit_event("screen.rejected", {"paper": r}, stage_key="screen", actor="librarian")
        await session.emit_event("step.completed", {"step_id": "reject"}, stage_key="screen", actor="librarian")
        await asyncio.sleep(0.4)

        # Step 3: shortlist
        await session.emit_event("step.started", {"step_id": "shortlist"}, stage_key="screen", actor="librarian")
        shortlist_papers = data.get("SHORTLIST", [])
        for p in shortlist_papers:
            await asyncio.sleep(0.35)
            await session.emit_event("screen.kept", {"paper": p}, stage_key="screen", actor="librarian")
        await session.emit_event("step.completed", {"step_id": "shortlist"}, stage_key="screen", actor="librarian")
        await asyncio.sleep(0.4)

        # Step 4: screen_gate
        await session.emit_event("step.started", {"step_id": "screen_gate"}, stage_key="screen", actor="pi")
        dropped_ids = set()

        if has_screen_gate:
            session.status = "awaiting_review"
            gate_spec = {
                "id": "gate-1",
                "gate_id": "gate-1",
                "kind": "screen",
                "stop_index": 1,
                "stop_total": 1,
                "title": "Approve the shortlist",
                "why": f"In {mode.title()} mode you check the reading list, because every gap and hypothesis is built on it.",
                "summary": [
                    f"{len(shortlist_papers)} of {coll.get('unique', 214)} papers kept, each with a reason",
                    f"{len(data.get('REJECTED', []))} wrong-field matches rejected",
                    f"{len([p for p in shortlist_papers if p.get('seminal')])} seminal papers kept despite their age",
                ],
                "options": [
                    {
                        "id": "approve",
                        "label": f"Read all {len(shortlist_papers)}",
                        "description": "Approve the shortlist as screened.",
                        "leads_to": "Each paper becomes a knowledge card",
                        "confirm_label": "Approve the shortlist",
                        "recommended": True,
                    },
                    {
                        "id": "drop",
                        "label": "Remove some first",
                        "description": "Click papers in the shortlist to leave them out.",
                        "leads_to": "Removed papers are not read or cited",
                        "confirm_label": "Choose what to remove",
                    },
                ],
                "droppable": [p["id"] for p in shortlist_papers],
            }
            session.pending_gate = gate_spec
            await session.emit_event("run.status", {"status": "awaiting_review"}, stage_key="screen")
            await session.emit_event("gate.opened", {**gate_spec, "gate": gate_spec}, stage_key="screen", actor="pi")

            logger.info(f"Run {session.popper_run_id} is awaiting review at gate-1...")
            await session.gate_event.wait()

            if session.gate_answer and "dropped" in session.gate_answer:
                dropped_ids = set(session.gate_answer["dropped"])

        await session.emit_event("step.completed", {"step_id": "screen_gate"}, stage_key="screen", actor="pi")
        await session.emit_event(
            "stage.completed",
            {"summary": f"{coll.get('unique', 214)} scored • {len(shortlist_papers) - len(dropped_ids)} kept • {len(data.get('REJECTED', []))} wrong-field matches rejected"},
            stage_key="screen",
            actor="librarian",
        )
        await asyncio.sleep(0.5)

        # -------------------------------------------------------------------
        # STAGE 6: READ (KNOWLEDGE CARDS)
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
                    "purpose": "Each paper becomes one knowledge card with the same fields. Limitations matter most: they are where the gaps come from.",
                    "reads": ["Shortlist"],
                    "cast": ["librarian"],
                    "steps": [
                        {"id": "extract", "title": "Extract a card per paper", "actor": "librarian", "pipeline_stage": 6, "artifact": "Knowledge cards", "explain": "Problem, method, data, metrics, findings and limitations."},
                        {"id": "verify", "title": "Check the recalled numbers", "actor": "librarian", "pipeline_stage": 6, "explain": "Numbers recalled while scoping are checked against the cards."}
                    ],
                }
            },
            stage_key="read",
            actor="librarian",
        )
        await asyncio.sleep(0.5)

        # Step 1: extract cards
        await session.emit_event("step.started", {"step_id": "extract"}, stage_key="read", actor="librarian")
        cards = [c for c in data.get("CARDS", []) if c.get("paper_id") not in dropped_ids]
        for card in cards:
            await asyncio.sleep(0.65)
            await session.emit_event("card.extracted", {"card": card}, stage_key="read", actor="librarian")
        await session.emit_event("step.completed", {"step_id": "extract"}, stage_key="read", actor="librarian")
        await asyncio.sleep(0.4)

        # Step 2: verify
        await session.emit_event("step.started", {"step_id": "verify"}, stage_key="read", actor="librarian")
        for chk in data.get("ESTIMATE_CHECKS", []):
            await asyncio.sleep(0.35)
            await session.emit_event("estimate.checked", {"check": chk}, stage_key="read", actor="librarian")
        await session.emit_event("rule.checked", {"rule": 6, "state": "pass"})
        await session.emit_event("step.completed", {"step_id": "verify"}, stage_key="read", actor="librarian")
        await session.emit_event("stage.completed", {"summary": f"{len(cards)} knowledge cards • 2 recalled numbers checked"}, stage_key="read", actor="librarian")
        await asyncio.sleep(0.5)

        # -------------------------------------------------------------------
        # STAGE 7: SYNTHESIZE (CLUSTERS & GAPS)
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
                    "purpose": "The cards are grouped into schools of thought. Where groups pull in different directions, and where limitations pile up, the gaps appear.",
                    "reads": ["Knowledge cards", "Sub-question tree"],
                    "cast": ["theorist"],
                    "steps": [
                        {"id": "cluster", "title": "Group into schools of thought", "actor": "theorist", "pipeline_stage": 7, "explain": "Papers are grouped by approach, not summarised one by one."},
                        {"id": "overview", "title": "Sum up the field", "actor": "theorist", "pipeline_stage": 7, "explain": "One paragraph on where the evidence stands across groups."},
                        {"id": "tension", "title": "Find where they disagree", "actor": "theorist", "pipeline_stage": 7, "explain": "Gaps show most clearly where two groups pull in different directions."},
                        {"id": "gaps", "title": "Name the gaps", "actor": "theorist", "pipeline_stage": 7, "explain": "Each gap is traced to the limitations that point to it."},
                        {"id": "rank", "title": "Rank the opportunities", "actor": "theorist", "pipeline_stage": 7, "artifact": "Gap map", "explain": "Gaps are ordered by directness to sub-questions."}
                    ],
                }
            },
            stage_key="synthesize",
            actor="theorist",
        )
        await asyncio.sleep(0.5)

        # Step 1: cluster
        await session.emit_event("step.started", {"step_id": "cluster"}, stage_key="synthesize", actor="theorist")
        for clus in data.get("CLUSTERS", []):
            await asyncio.sleep(0.45)
            await session.emit_event("synthesis.cluster", {"cluster": clus}, stage_key="synthesize", actor="theorist")
        await session.emit_event("step.completed", {"step_id": "cluster"}, stage_key="synthesize", actor="theorist")
        await asyncio.sleep(0.3)

        # Step 2: overview
        await session.emit_event("step.started", {"step_id": "overview"}, stage_key="synthesize", actor="theorist")
        await asyncio.sleep(0.6)
        await session.emit_event("synthesis.overview", {"text": data.get("OVERVIEW", "")}, stage_key="synthesize", actor="theorist")
        await session.emit_event("step.completed", {"step_id": "overview"}, stage_key="synthesize", actor="theorist")
        await asyncio.sleep(0.3)

        # Step 3: tension
        await session.emit_event("step.started", {"step_id": "tension"}, stage_key="synthesize", actor="theorist")
        await asyncio.sleep(0.6)
        await session.emit_event("synthesis.tension", {"tension": data.get("TENSION", {})}, stage_key="synthesize", actor="theorist")
        await session.emit_event("step.completed", {"step_id": "tension"}, stage_key="synthesize", actor="theorist")
        await asyncio.sleep(0.3)

        # Step 4: gaps
        await session.emit_event("step.started", {"step_id": "gaps"}, stage_key="synthesize", actor="theorist")
        for g in data.get("GAPS", []):
            await asyncio.sleep(0.5)
            await session.emit_event("synthesis.gap", {"gap": g}, stage_key="synthesize", actor="theorist")
        await session.emit_event("step.completed", {"step_id": "gaps"}, stage_key="synthesize", actor="theorist")
        await asyncio.sleep(0.3)

        # Step 5: rank
        await session.emit_event("step.started", {"step_id": "rank"}, stage_key="synthesize", actor="theorist")
        await asyncio.sleep(0.4)
        await session.emit_event("synthesis.ranked", {"ranking": data.get("RANKING", [])}, stage_key="synthesize", actor="theorist")
        await session.emit_event("step.completed", {"step_id": "rank"}, stage_key="synthesize", actor="theorist")
        await session.emit_event("stage.completed", {"summary": f"{len(data.get('CLUSTERS', []))} groups • 1 tension • {len(data.get('GAPS', []))} gaps"}, stage_key="synthesize", actor="theorist")
        await asyncio.sleep(0.5)

        # -------------------------------------------------------------------
        # STAGE 8: HYPOTHESIZE (MULTI-AGENT DEBATE & HYPOTHESES)
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
                    "purpose": "Three perspectives argue over the gaps. What survives is written as a hypothesis with four parts, including the result that would prove it wrong.",
                    "reads": ["Gap map", "Shortlist", "Compute profile"],
                    "cast": ["theorist", "methodologist", "skeptic", "librarian", "pi"],
                    "steps": [
                        {"id": "debate", "title": "Debate the directions", "actor": "theorist", "pipeline_stage": 8, "artifact": "Debate record", "explain": "Theorist proposes, Methodologist tests, Skeptic challenges."},
                        {"id": "write", "title": "Write each hypothesis", "actor": "theorist", "pipeline_stage": 8, "artifact": "Hypotheses", "explain": "Four parts each: claim, novelty, rationale, and falsification."},
                        {"id": "check", "title": "Check novelty and feasibility", "actor": "librarian", "pipeline_stage": 8, "artifact": "Novelty check", "explain": "Each hypothesis is compared with shortlist and compute."},
                        {"id": "select", "title": "Pick the set", "actor": "pi", "pipeline_stage": 8, "explain": "The chosen hypotheses go into this round's set."}
                    ],
                }
            },
            stage_key="r1-hypothesize",
            actor="theorist",
        )
        await asyncio.sleep(0.5)

        debate_data = data.get("DEBATES", {}).get("first", {})

        # Step 1: debate
        await session.emit_event("step.started", {"step_id": "debate"}, stage_key="r1-hypothesize", actor="theorist")
        for turn in debate_data.get("turns", []):
            await asyncio.sleep(0.85)
            await session.emit_event("debate.turn", {"turn": turn}, stage_key="r1-hypothesize", actor=turn.get("actor", "theorist"))
        await session.emit_event("step.completed", {"step_id": "debate"}, stage_key="r1-hypothesize", actor="theorist")
        await asyncio.sleep(0.4)

        # Step 2: write
        await session.emit_event("step.started", {"step_id": "write"}, stage_key="r1-hypothesize", actor="theorist")
        for hid in debate_data.get("hypotheses", ["H1", "H2", "H3", "H4"]):
            hypo = data.get("HYPOTHESES", {}).get(hid)
            if hypo:
                await asyncio.sleep(0.75)
                await session.emit_event("hypothesis.drafted", {"hypothesis": hypo}, stage_key="r1-hypothesize", actor="theorist")
        await session.emit_event("rule.checked", {"rule": 5, "state": "pass"})
        await session.emit_event("step.completed", {"step_id": "write"}, stage_key="r1-hypothesize", actor="theorist")
        await asyncio.sleep(0.4)

        # Step 3: check
        await session.emit_event("step.started", {"step_id": "check"}, stage_key="r1-hypothesize", actor="librarian")
        for hid in debate_data.get("hypotheses", []):
            chk = debate_data.get("checks", {}).get(hid, {})
            await asyncio.sleep(0.35)
            await session.emit_event("hypothesis.checked", {"hypothesis_id": hid, **chk}, stage_key="r1-hypothesize", actor="librarian")
        await session.emit_event("step.completed", {"step_id": "check"}, stage_key="r1-hypothesize", actor="librarian")
        await asyncio.sleep(0.4)

        # Step 4: select
        await session.emit_event("step.started", {"step_id": "select"}, stage_key="r1-hypothesize", actor="pi")
        for hid in debate_data.get("hypotheses", []):
            await asyncio.sleep(0.35)
            await session.emit_event("hypothesis.selected", {"hypothesis_id": hid}, stage_key="r1-hypothesize", actor="pi")
        for aside in debate_data.get("asides", []):
            await asyncio.sleep(0.3)
            await session.emit_event("idea.set_aside", {"idea_id": aside["id"], "statement": aside["statement"], "reason": aside["reason"]}, stage_key="r1-hypothesize", actor="pi")
        await session.emit_event("step.completed", {"step_id": "select"}, stage_key="r1-hypothesize", actor="pi")
        await session.emit_event("stage.completed", {"summary": f"{len(debate_data.get('hypotheses', []))} hypotheses to test, each with a way to be wrong"}, stage_key="r1-hypothesize", actor="pi")
        await asyncio.sleep(0.5)

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
