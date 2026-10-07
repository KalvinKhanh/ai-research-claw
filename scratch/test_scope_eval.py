import sys
sys.stdout.reconfigure(encoding="utf-8")

from researchclaw.pipeline.llm_pipeline_generator import _get_llm_client, _clean_json_markdown

client = _get_llm_client()

def test_eval(topic, domains):
    domain_str = ", ".join(domains)
    prompt = f"""You are a senior Principal Investigator (PI) and Area Chair at a top academic research venue.
Your job is to strictly evaluate the proposed topic and formalize Stage 1 (Scope) of the research pipeline.

Topic: "{topic}"
Fields: {domain_str}

FIRST: Rigorously determine if "{topic}" is a legitimate scientific / empirical research topic.
If it is casual conversation, personal talk, everyday food/drink/eating (e.g. "tôi muốn ăn cơm", "ăn cơm", "chào bạn", "hello"), nonsense words, jokes, or non-academic statements:
- It is NOT valid scientific research!
- Return valid JSON with:
  "is_valid": false,
  "rejection_reason": "Topic is casual conversation or non-scientific text, not an empirical research problem.",
  "topic_scores": {{"novelty": 1, "specificity": 1, "feasibility": 1}},
  "overall_score": 1.0,
  "topic_advice": "Chủ đề này không phải là một vấn đề nghiên cứu khoa học thực nghiệm. Vui lòng nhập một câu hỏi nghiên cứu có biến số và giả thuyết có thể kiểm chứng.",
  "working_title": "{topic}",
  "problem": "Vấn đề chưa được định hình theo phương pháp luận khoa học.",
  "objective": "Cần xác định lại mục tiêu nghiên cứu cụ thể.",
  "scope_boundary": "Nằm ngoài phạm vi nghiên cứu khoa học thực nghiệm.",
  "success_criteria": "Chưa đạt tiêu chuẩn kiểm định khoa học.",
  "sub_questions": [
    {{"id": "SQ1", "text": "Xác định câu hỏi nghiên cứu học thuật thực tế cho đề tài", "priority": 1, "covers": ["clarity"]}}
  ],
  "risks": [
    {{"id": "R1", "sq_id": "SQ1", "text": "Đề tài thiếu cơ sở lý thuyết và dữ liệu thực nghiệm", "level": "high"}}
  ],
  "estimates": [
    {{"id": "E1", "text": "Không có số liệu định lượng hợp lệ"}}
  ],
  "say_profile": "Lĩnh vực chưa phù hợp với một đề tài nghiên cứu khoa học chính thống.",
  "say_goal": "Không thể thiết lập mục tiêu khoa học vì đề tài không mang tính học thuật.",
  "say_decompose": "Không thể phân tách thành các câu hỏi phụ khoa học khả thi.",
  "say_evaluate": "PI nhận xét: Đề tài không đạt tiêu chuẩn nghiên cứu khoa học (1.0/10). Dừng quy trình để định hình lại đề tài."

IF it IS a legitimate academic/empirical research topic:
- Evaluate novelty (1-10), specificity (1-10), feasibility (1-10) realistically.
- Return valid JSON with:
  "is_valid": true,
  "topic_scores": {{"novelty": 8, "specificity": 9, "feasibility": 8}},
  "overall_score": 8.3,
  "topic_advice": "1 strategic recommendation sentence from the PI",
  "working_title": "Concise working title",
  "problem": "Problem statement (2 sentences)",
  "objective": "Empirical research objective (2 sentences)",
  "scope_boundary": f"Boundary conditions in {domain_str}",
  "success_criteria": "Measurable success metric with confidence intervals",
  "estimates": [
    {{"id": "E1", "text": "Estimated effect size or improvement percentage"}},
    {{"id": "E2", "text": "Estimated mediator or baseline statistic"}}
  ],
  "scope_adjusted": {{"field": "scope", "to": "Narrowed primary scope", "reason": "Focus on core causal mechanisms"}},
  "sub_questions": 3 to 4 items with "id" ("SQ1"..), "text", "priority", "tests", "covers",
  "risks": 3 to 4 items with "id" ("R1"..), "sq_id", "text", "level",
  "gaps": 2 to 3 items with "id" ("G1"..), "text",
  "hypotheses_seeds": 3 to 4 items with "id" ("H1"..), "statement", "outcome", "exposure", "estimand", "method", "falsify",
  "say_profile": "Agent narration for compute & field check (1-2 sentences)",
  "say_goal": "Agent narration for goal formulation (1-2 sentences)",
  "say_decompose": "Agent narration for sub-question tree (1-2 sentences)",
  "say_evaluate": "PI narration summarizing score and whether greenlit (1-2 sentences)"

Return ONLY raw JSON. Keep descriptions concise (1 sentence each).
"""
    res = client.chat(messages=[{"role": "user", "content": prompt}], max_tokens=4000)
    data = _clean_json_markdown(res.content)
    print(f"=== RESULT FOR '{topic}' ===")
    print(f"is_valid: {data.get('is_valid')}")
    print(f"overall_score: {data.get('overall_score')}")
    print(f"scores: {data.get('topic_scores')}")
    print(f"advice: {data.get('topic_advice')}")
    print(f"say_evaluate: {data.get('say_evaluate')}")

print("\nTesting 'CRISPR' with max_tokens=4000...")
test_eval("CRISPR off-target cleavage prediction using diffusion state-space models", ["Computational Biology", "Deep Learning"])
