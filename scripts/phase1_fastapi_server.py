"""Standalone Launcher for AutoResearchClaw Phase 1 FastAPI & Swagger Server."""

import os
import sys
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

# Load .env if present
env_file = BASE_DIR / ".env"
if env_file.exists():
    with open(env_file, encoding="utf-8") as f:
        for line in f:
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.strip().split("=", 1)
                os.environ[k.strip()] = v.strip()

from researchclaw.config import RCConfig
from researchclaw.server.app import create_app
import uvicorn

def main():
    config_file = BASE_DIR / "config.arc.yaml"
    if not config_file.exists():
        config_file = BASE_DIR / "config.yaml"

    config = RCConfig.load(config_file, check_paths=False)
    app = create_app(config)

    port = int(os.environ.get("PORT", 8000))
    host = "0.0.0.0"

    print("=" * 65)
    print("   AUTORESEARCHCLAW - PHASE 1 FASTAPI & SWAGGER SERVER")
    print("=" * 65)
    print(f"🚀 Server running on: http://localhost:{port}")
    print(f"📖 SWAGGER UI DOCS:   http://localhost:{port}/docs")
    print(f"📑 REDOC DOCS:        http://localhost:{port}/redoc")
    print(f"📡 API Health Check:  http://localhost:{port}/api/health")
    print("=" * 65)
    print("Nhấn Ctrl + C để dừng server.")
    print("=" * 65)

    uvicorn.run(app, host=host, port=port, log_level="info")

if __name__ == "__main__":
    main()
