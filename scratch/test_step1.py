import json
import logging
from researchclaw.pipeline.llm_pipeline_generator import _get_llm_client

client = _get_llm_client()
topic = "Does cross-attention activation steering effectively mitigate visual hallucinations in multimodal clinical diagnosis models?"
domain_str = "Multimodal Artificial Intelligence, Medical Image Analysis, Model Interpretability & Safety"

p1 = f"""You are a Principal Investigator leading a scientific study.
Topic: "{topic}"
Fields: {domain_str}

Return a valid JSON object with:
1. "working_title": working title
2. "problem": problem statement (2-3 sentences)
3. "objective": empirical research objective (2-3 sentences)
4. "scope_boundary": boundary conditions
5. "success_criteria": measurable success metric with confidence intervals
6. "sub_questions": 3 items with "id" ("SQ1"..), "text", "tests", "covers"
7. "risks": 3 items with "id" ("R1"..), "sq_id", "text", "level"
8. "strategies": 3 items with "id" ("S1".."S3"), "title", "why"
9. "queries": 6 search queries with "id" ("q1"..), "strategy_id", "text", "estimated_hits"
10. "gaps": 3 items with "id" ("G1"..), "text"
11. "hypotheses": 3 items with "id" ("H1"..), "statement", "short", "outcome", "exposure", "estimand", "method", "falsify"
12. "topic_scores": {{"novelty": 8, "specificity": 9, "feasibility": 8}}
13. "topic_advice": "Advice sentence"
Keep all descriptions concise (1-2 sentences each). Return ONLY raw JSON."""

r1 = client.chat(messages=[{"role": "user", "content": p1}], max_tokens=6000)
print("Length of content:", len(r1.content))
print("Last 150 chars:", repr(r1.content[-150:]))
try:
    d = json.loads(r1.content.strip().removeprefix("```json").removesuffix("```").strip())
    print("SUCCESSFULLY PARSED JSON! Keys:", list(d.keys()))
except Exception as e:
    print("JSON PARSE ERROR:", e)
