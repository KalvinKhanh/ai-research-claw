import json
import os
import re
from researchclaw.config import load_config
from researchclaw.llm.client import LLMClient

# Load env
for line in open(".env"):
    if "=" in line and not line.startswith("#"):
        k, v = line.strip().split("=", 1)
        os.environ[k] = v

client = LLMClient.from_rc_config(load_config("config.arc.yaml"))
prompt = """You are an expert research scientist. For the research topic:
"Does sparse autoencoder feature steering effectively prevent jailbreaks in aligned large language models?"
Output a valid JSON object with:
1. "title": working research title
2. "problem": problem statement
3. "objective": research objective
4. "sub_questions": list of 4 objects with "id", "text", "tests"
5. "hypotheses": list of 4 objects with "id", "statement", "falsify"
Return ONLY the raw JSON object, without markdown quotes."""

resp = client.chat(messages=[{"role": "user", "content": prompt}])
print("Raw content:")
print(resp.content)

# Clean markdown if present
content = resp.content.strip()
if content.startswith("```"):
    content = re.sub(r"^```(?:json)?\s*", "", content)
    content = re.sub(r"\s*```$", "", content)

parsed = json.loads(content)
print("\nParsed successfully!")
print("Title:", parsed.get("title"))
