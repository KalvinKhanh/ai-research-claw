import json
import logging
from researchclaw.pipeline.llm_pipeline_generator import _get_llm_client, _assemble_contract, _clean_json_markdown

logging.basicConfig(level=logging.INFO)

topic = "Does cross-attention activation steering effectively mitigate visual hallucinations in multimodal clinical diagnosis models?"
domains = ["Multimodal Artificial Intelligence", "Medical Image Analysis", "Model Interpretability & Safety"]
domain_str = ", ".join(domains)
client = _get_llm_client()

print("--- TESTING STEP 1 ---")
p1 = f"""You are a Principal Investigator leading a scientific study.
Topic: "{topic}"
Fields: {domain_str}

Return a valid JSON object with:
1. "working_title": working title
2. "problem": problem statement (2-3 sentences)
3. "objective": empirical research objective (2-3 sentences)
4. "scope_boundary": boundary conditions
5. "success_criteria": measurable success metric with confidence intervals
6. "sub_questions": 3 to 4 items with "id" ("SQ1"..), "text", "tests", "covers"
7. "risks": 3 to 4 items with "id" ("R1"..), "sq_id", "text", "level"
8. "strategies": 3 items with "id" ("S1".."S3"), "title", "why"
9. "queries": 6 to 8 realistic search queries with "id" ("q1"..), "strategy_id", "text", "estimated_hits"
10. "gaps": 2 to 3 items with "id" ("G1"..), "text"
11. "hypotheses": 3 to 4 items with "id" ("H1"..), "statement", "short", "outcome", "exposure", "estimand", "method", "falsify"
12. "topic_scores": {{"novelty": 8, "specificity": 9, "feasibility": 8}}
13. "topic_advice": "Advice sentence"
Keep all descriptions concise (1-2 sentences each). Return ONLY raw JSON."""

r1 = client.chat(messages=[{"role": "user", "content": p1}], max_tokens=6000)
d1 = _clean_json_markdown(r1.content)
print("Step 1 SUCCESS! SQ:", len(d1["sub_questions"]), "Hypotheses:", len(d1["hypotheses"]))

print("--- TESTING STEP 2 ---")
hypo_summaries = [h.get("statement", "") for h in d1.get("hypotheses", [])]
p2 = f"""You are a senior scholarly Research Librarian.
For the topic: "{topic}" and hypotheses:
{json.dumps(hypo_summaries, indent=2)}

Generate a shortlist of 10 to 12 realistic peer-reviewed papers (venues: NeurIPS, ICML, CVPR, MICCAI, Nature Medicine, etc., years 2021-2025).
Also provide 3 realistic false-friend papers that were rejected.
Return a JSON object with:
"shortlist": list of 10 to 12 objects, each with:
  "id": "p1".."pN",
  "citation": "FirstAuthor et al., Year",
  "title": "Full realistic paper title",
  "venue": "Top venue name",
  "year": integer,
  "relevance": float 0.80-0.98,
  "quality": float 0.80-0.98,
  "reason": "1-sentence reason",
  "problem": "1-sentence problem",
  "method": "1-sentence method",
  "data": "Benchmark name",
  "metrics": "Metric name",
  "findings": "1-sentence key finding",
  "limitations": "1-sentence limitation"
"rejected": list of 3 objects with "id", "title", "venue", "false_friend", "reason", "relevance", "quality"
Keep all entries concise. Return ONLY raw JSON."""

r2 = client.chat(messages=[{"role": "user", "content": p2}], max_tokens=6000)
d2 = _clean_json_markdown(r2.content)
print("Step 2 SUCCESS! Shortlist papers:", len(d2["shortlist"]))

print("--- TESTING STEP 3 ---")
p3 = f"""You are orchestrating a scientific debate between:
- 'theorist': proposes claims based on literature
- 'methodologist': designs strict empirical tests
- 'skeptic': challenges confounders and falsification criteria

Topic: "{topic}"
Hypotheses: {json.dumps(hypo_summaries, indent=2)}
Gaps: {json.dumps([g.get('text') for g in d1.get('gaps', [])], indent=2)}

Generate a valid JSON object with:
1. "turns": list of 10 to 12 sequential debate turns with "id" ("t1"..), "actor" ('theorist'|'methodologist'|'skeptic'), "stance" ('propose'|'test'|'challenge'|'refine'), "about" (hypothesis id), "text" (1-2 sentences each).
2. "clusters": list of 3 to 4 schools of thought with "id", "title", "claim", "card_ids" (matching paper ids e.g. ["p1","p2"])
3. "tension": object with "between" and "text"
4. "overview": 3-sentence synthesis paragraph
5. "asides": list of 2 ideas set aside as limits with "id" ("C5", "C6"), "statement", "reason"
Keep entries concise. Return ONLY raw JSON."""

r3 = client.chat(messages=[{"role": "user", "content": p3}], max_tokens=6000)
d3 = _clean_json_markdown(r3.content)
print("Step 3 SUCCESS! Debate turns:", len(d3["turns"]))

contract = _assemble_contract(d1, d2, d3, topic, domains)
print("=== ASSEMBLE SUCCESS! ===")
print("First debate turn text:", contract["DEBATES"]["first"]["turns"][0]["text"])
print("Total raw hits:", contract["COLLECTED"]["raw"], "Unique:", contract["COLLECTED"]["unique"])
