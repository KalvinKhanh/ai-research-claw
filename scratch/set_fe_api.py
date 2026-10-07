from pathlib import Path

env_path = Path(r"d:\ai-platform-project\ai-research-platform-fe\.env")
content = """NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_APP_URL=http://localhost:3000
NEXT_PUBLIC_ENV=development

# Where research runs come from: "mock" plays a scripted run in the browser, "api" uses the backend.
# Restart `npm run dev` after changing it.
NEXT_PUBLIC_RUN_STREAM_SOURCE=api
"""

env_path.write_text(content, encoding="utf-8")
print(".env successfully updated to NEXT_PUBLIC_RUN_STREAM_SOURCE=api")
