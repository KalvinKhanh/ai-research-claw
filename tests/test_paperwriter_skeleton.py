from pathlib import Path

from fastapi.testclient import TestClient

from paperwriter.app import create_app
from paperwriter.contracts import WRITER_CONTRACTS, WriterStage
from paperwriter.intake import validate_bundle


def _make_run(tmp: Path) -> Path:
    for rel in ("stage-01/goal.md", "stage-02/problem_tree.md", "stage-05/shortlist.jsonl",
                "stage-06/cards/a.md", "stage-07/synthesis.md", "stage-08/hypotheses.md"):
        p = tmp / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("x", encoding="utf-8")
    return tmp


def test_contracts_cover_all_stages():
    assert set(WRITER_CONTRACTS) == set(WriterStage)


def test_bundle_validation(tmp_path):
    assert not validate_bundle(tmp_path).ok
    run = _make_run(tmp_path)
    report = validate_bundle(run)
    assert report.ok and not report.has_results


def test_create_run_idempotent_and_auth(tmp_path):
    run = _make_run(tmp_path)
    client = TestClient(create_app(service_key="k"))
    body = {"platform_run_id": "p1", "engine_run_dir": str(run)}
    assert client.post("/api/runs", json=body).status_code == 401
    h = {"X-Service-Key": "k"}
    r1 = client.post("/api/runs", json=body, headers=h)
    r2 = client.post("/api/runs", json=body, headers=h)
    assert r1.status_code == 202 and r1.json() == r2.json()
    assert r1.json()["mode"] == "proposal"
    assert client.get("/api/health").json()["status"] == "ok"
