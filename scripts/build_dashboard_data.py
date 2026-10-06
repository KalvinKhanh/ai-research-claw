import json
import os
import glob

def get_latest_run_dir(base_artifacts=r"d:\AutoResearchClaw\artifacts"):
    runs = [os.path.join(base_artifacts, d) for d in os.listdir(base_artifacts) if d.startswith("rc-") and os.path.isdir(os.path.join(base_artifacts, d))]
    # Sort by mtime descending
    runs.sort(key=lambda d: os.path.getmtime(d), reverse=True)
    for r in runs:
        if os.path.exists(os.path.join(r, "stage-01")):
            return r
    return runs[0] if runs else None

def build_data(target_run_dir=None):
    base_artifacts = r"d:\AutoResearchClaw\artifacts"
    if target_run_dir and os.path.exists(target_run_dir):
        run_dir = target_run_dir
    else:
        run_dir = get_latest_run_dir(base_artifacts)

    if not run_dir:
        print("No run directory found in artifacts!")
        return

    out_file = r"d:\AutoResearchClaw\dashboard\data.js"
    os.makedirs(os.path.dirname(out_file), exist_ok=True)
    run_id = os.path.basename(run_dir)

    # Read topic from novelty report, goal.md, config or fallback
    topic = "Contrastive decoding and uncertainty-aware calibration for hallucination mitigation in large language models"
    nov_file = os.path.join(run_dir, "stage-08", "novelty_report.json")
    goal_file = os.path.join(run_dir, "stage-01", "goal.md")
    cfg_file = os.path.join(run_dir, "config.yaml")

    if os.path.exists(nov_file):
        try:
            with open(nov_file, encoding="utf-8") as f:
                n_data = json.load(f)
                if n_data.get("topic"):
                    topic = n_data["topic"]
        except Exception:
            pass
    elif os.path.exists(goal_file):
        try:
            with open(goal_file, encoding="utf-8") as f:
                for line in f:
                    if line.strip().startswith("## Topic"):
                        next_line = next(f, "").strip()
                        if next_line:
                            topic = next_line
                            break
        except Exception:
            pass
    elif os.path.exists(cfg_file):
        try:
            import yaml
            with open(cfg_file, encoding="utf-8") as f:
                cfg = yaml.safe_load(f)
                if cfg and "research" in cfg and "topic" in cfg["research"]:
                    topic = cfg["research"]["topic"]
        except Exception:
            pass

    data = {
        "run_id": run_id,
        "topic": topic,
        "benchmark": "QASPER (Allen Institute for AI)",
        "approach": "Discourse-Conditioned Reranker (DCR)",
        "target_model": "Llama-3-8B-Instruct / Mistral-7B-Instruct (4-bit/8-bit)",
        "mode": "Co-pilot (HITL Active)",
        "status": "Phase 1 Completed (Stages 1-8)",
        "stages": {},
        "literature": {},
        "hitl": {},
        "hardware": {}
    }

    # 1. Hardware profile
    hw_file = os.path.join(run_dir, "stage-01", "hardware_profile.json")
    if os.path.exists(hw_file):
        with open(hw_file, encoding="utf-8") as f:
            data["hardware"] = json.load(f)

    # 2. Stages 1-8 details
    stage_names = {
        1: "Topic Initialization & Scoping",
        2: "Problem Tree Decomposition",
        3: "Search Strategy & Queries",
        4: "Literature Collection (Crawling)",
        5: "Literature Screening (Gate)",
        6: "Knowledge Extraction (Paper Cards)",
        7: "Literature Synthesis & Gap Analysis",
        8: "Hypothesis Generation & Multi-Perspective Debate"
    }

    for s_num in range(1, 9):
        s_key = f"stage-{s_num:02d}"
        s_dir = os.path.join(run_dir, s_key)
        info = {
            "stage_number": s_num,
            "stage_key": s_key,
            "name": stage_names.get(s_num, f"Stage {s_num}"),
            "status": "done",
            "duration_sec": 0,
            "artifacts": []
        }

        # Health
        health_path = os.path.join(s_dir, "stage_health.json")
        if os.path.exists(health_path):
            with open(health_path, encoding="utf-8") as f:
                h = json.load(f)
                info["duration_sec"] = h.get("duration_sec", 0)
                info["status"] = h.get("status", "done")
                info["timestamp"] = h.get("timestamp", "")

        # Decision
        dec_path = os.path.join(s_dir, "decision.json")
        if os.path.exists(dec_path):
            with open(dec_path, encoding="utf-8") as f:
                d = json.load(f)
                info["decision"] = d.get("decision", "proceed")
                info["output_artifacts"] = d.get("output_artifacts", [])

        # Stage specific payloads
        if s_num == 1:
            with open(os.path.join(s_dir, "goal.md"), encoding="utf-8") as f:
                info["goal_md"] = f.read()

        elif s_num == 2:
            with open(os.path.join(s_dir, "problem_tree.md"), encoding="utf-8") as f:
                info["problem_tree_md"] = f.read()

        elif s_num == 3:
            with open(os.path.join(s_dir, "queries.json"), encoding="utf-8") as f:
                info["queries_data"] = json.load(f)
            with open(os.path.join(s_dir, "sources.json"), encoding="utf-8") as f:
                info["sources_data"] = json.load(f)

        elif s_num == 4:
            with open(os.path.join(s_dir, "search_meta.json"), encoding="utf-8") as f:
                info["search_meta"] = json.load(f)

        elif s_num == 5:
            shortlist_papers = []
            with open(os.path.join(s_dir, "shortlist.jsonl"), encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        shortlist_papers.append(json.loads(line))
            info["shortlist"] = shortlist_papers

        elif s_num == 6:
            cards = []
            for c_path in sorted(glob.glob(os.path.join(s_dir, "cards", "*.md"))):
                with open(c_path, encoding="utf-8") as f:
                    cards.append({
                        "filename": os.path.basename(c_path),
                        "content": f.read()
                    })
            info["cards"] = cards

        elif s_num == 7:
            with open(os.path.join(s_dir, "synthesis.md"), encoding="utf-8") as f:
                info["synthesis_md"] = f.read()

        elif s_num == 8:
            with open(os.path.join(s_dir, "novelty_report.json"), encoding="utf-8") as f:
                info["novelty_report"] = json.load(f)
            with open(os.path.join(s_dir, "hypotheses.md"), encoding="utf-8") as f:
                info["hypotheses_md"] = f.read()
            
            perspectives = {}
            p_dir = os.path.join(s_dir, "perspectives")
            for p_file in ["innovator.md", "pragmatist.md", "contrarian.md"]:
                fp = os.path.join(p_dir, p_file)
                if os.path.exists(fp):
                    with open(fp, encoding="utf-8") as f:
                        perspectives[p_file.replace(".md", "")] = f.read()
            info["perspectives"] = perspectives

        data["stages"][s_key] = info

    # 3. Literature aggregation from candidates.jsonl (Stage 4)
    cand_file = os.path.join(run_dir, "stage-04", "candidates.jsonl")
    candidates = []
    year_dist = {}
    source_dist = {}
    venue_dist = {}

    with open(cand_file, encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            item = json.loads(line)
            y = item.get("year") or "Unknown"
            year_dist[str(y)] = year_dist.get(str(y), 0) + 1
            
            src = item.get("source") or "unknown"
            source_dist[src] = source_dist.get(src, 0) + 1
            
            v = item.get("venue") or "Other/Unspecified"
            venue_dist[v] = venue_dist.get(v, 0) + 1
            
            candidates.append({
                "id": item.get("paper_id"),
                "title": item.get("title"),
                "year": item.get("year"),
                "venue": v,
                "citations": item.get("citation_count", 0) or 0,
                "source": src,
                "doi": item.get("doi", ""),
                "arxiv_id": item.get("arxiv_id", ""),
                "url": item.get("url", ""),
                "abstract": (item.get("abstract") or "")[:400]
            })

    # Top venues
    sorted_venues = sorted(venue_dist.items(), key=lambda x: x[1], reverse=True)[:10]

    # Top cited
    top_cited = sorted(candidates, key=lambda x: x["citations"], reverse=True)[:15]

    data["literature"] = {
        "total_candidates": len(candidates),
        "year_distribution": dict(sorted(year_dist.items())),
        "source_distribution": source_dist,
        "top_venues": dict(sorted_venues),
        "top_cited": top_cited,
        "candidates": candidates,
        "shortlist_count": len(data["stages"]["stage-05"].get("shortlist", []))
    }

    # 4. HITL Session and Interventions
    hitl_session_file = os.path.join(run_dir, "hitl", "session.json")
    if os.path.exists(hitl_session_file):
        with open(hitl_session_file, encoding="utf-8") as f:
            data["hitl"]["session"] = json.load(f)

    interventions = []
    hitl_int_file = os.path.join(run_dir, "hitl", "interventions.jsonl")
    if os.path.exists(hitl_int_file):
        with open(hitl_int_file, encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    interventions.append(json.loads(line))
    data["hitl"]["interventions"] = interventions

    # 5. Checkpoint
    chk_file = os.path.join(run_dir, "checkpoint.json")
    if os.path.exists(chk_file):
        with open(chk_file, encoding="utf-8") as f:
            data["checkpoint"] = json.load(f)

    # Write out as window.AUTORESEARCH_DATA = { ... };
    with open(out_file, "w", encoding="utf-8") as f:
        f.write("// Auto-generated by AutoResearchClaw Dashboard Builder\n")
        f.write("window.AUTORESEARCH_DATA = ")
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write(";\n")

    print(f"Successfully generated {out_file} ({os.path.getsize(out_file)/1024:.1f} KB)")

if __name__ == "__main__":
    build_data()
