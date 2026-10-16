"""Run endpoints. Skeleton: validates the bundle and registers the run idempotently."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from paperwriter.intake import validate_bundle

router = APIRouter(prefix="/api/runs", tags=["runs"])

# platform_run_id -> run record (in-memory for the skeleton; persistence is a later step)
_RUNS: dict[str, dict[str, Any]] = {}


class CreateRun(BaseModel):
    platform_run_id: str
    engine_run_dir: str
    callback_url: str | None = None


@router.post("", status_code=202)
def create_run(body: CreateRun) -> dict[str, Any]:
    existing = _RUNS.get(body.platform_run_id)
    if existing:
        return existing  # idempotent on platform_run_id
    report = validate_bundle(body.engine_run_dir)
    if not report.ok:
        raise HTTPException(422, {"missing_required": report.missing_required})
    record = {
        "run_id": f"pw-{uuid.uuid4().hex[:12]}",
        "platform_run_id": body.platform_run_id,
        "status": "accepted",
        "mode": "with_results" if report.has_results else "proposal",
        "bundle": {"present": report.present, "missing_optional": report.missing_optional},
    }
    _RUNS[body.platform_run_id] = record
    return record


@router.get("/{platform_run_id}")
def get_run(platform_run_id: str) -> dict[str, Any]:
    if platform_run_id not in _RUNS:
        raise HTTPException(404, "run not found")
    return _RUNS[platform_run_id]
