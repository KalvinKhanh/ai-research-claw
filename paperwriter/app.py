"""FastAPI app factory for the PaperWriter service."""

from __future__ import annotations

import os

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from paperwriter import __version__
from paperwriter.routes import runs


def create_app(service_key: str | None = None) -> FastAPI:
    key = service_key if service_key is not None else os.environ.get("PAPERWRITER_SERVICE_KEY", "")
    app = FastAPI(title="PaperWriter", version=__version__)

    @app.middleware("http")
    async def service_key_guard(request: Request, call_next):
        if key and request.url.path.startswith("/api/runs") and request.headers.get("X-Service-Key") != key:
            return JSONResponse({"detail": "invalid service key"}, status_code=401)
        return await call_next(request)

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "service": "paperwriter", "version": __version__}

    app.include_router(runs.router)
    return app


app = create_app()
