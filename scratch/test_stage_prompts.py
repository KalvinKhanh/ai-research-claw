import json
import os
import re
import time
from researchclaw.config import load_config
from researchclaw.llm.client import LLMClient

# Load env
for line in open(".env"):
    if "=" in line and not line.startswith("#"):
        k, v = line.strip().split("=", 1)
        os.environ[k] = v

client = LLMClient.from_rc_config(load_config("config.arc.yaml"))

def extract_json(text: str) -> dict:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    return json.loads(cleaned.strip())

topic = "Does sparse autoencoder feature steering effectively prevent jailbreaks in aligned large language models?"

t0 = time.time()
print(f"1. Calling Claude Haiku 4.5 for Topic Scoping & Hypotheses...")
p1 = f"""You are a top AI research scientist. For the research topic:
"{topic}"
Return a valid JSON object with:
1. "title": working academic title
2. "problem": 2-sentence problem statement
3. "objective": 2-sentence research objective
4. "scope": specific scope boundary
5. "sub_questions": 4 items with "id" (SQ1..SQ4), "text", "tests", "covers" (list of strings)
6. "hypotheses": 4 items with "id" (H1..H4), "statement", "short", "outcome", "exposure", "falsify" (string)
7. "gaps": 3 research gaps with "id" (G1..G3), "text"
Return ONLY raw JSON."""

r1 = client.chat(messages=[{"role": "user", "content": p1}], max_tokens=2048)
d1 = extract_json(r1.content)
print(f"Done in {time.time()-t0:.2f}s!")
print("Title:", d1.get("title"))
print("H1:", d1.get("hypotheses", [{}])[0].get("statement"))

t1 = time.time()
print(f"\n2. Calling Claude Haiku 4.5 for Debate Turns...")
p2 = f"""Given the topic "{topic}" and hypotheses:
{json.dumps([h.get('statement') for h in d1.get('hypotheses', [])])}
Generate 12 multi-agent debate turns between 'theorist', 'methodologist', and 'skeptic'.
Return JSON with "turns": list of 12 objects with "actor" ('theorist'|'methodologist'|'skeptic') and "text".
Return ONLY raw JSON."""

r2 = client.chat(messages=[{"role": "user", "content": p2}], max_tokens=2048)
d2 = extract_json(r2.content)
print(f"Done in {time.time()-t1:.2f}s!")
print("Turn 0:", d2.get("turns", [{}])[0])
print("Turn 1:", d2.get("turns", [{}])[1])
print("Turn 2:", d2.get("turns", [{}])[2])
