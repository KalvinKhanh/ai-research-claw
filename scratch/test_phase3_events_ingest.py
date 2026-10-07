import asyncio
import httpx
from uuid import uuid4
from datetime import datetime, UTC
# pyrefly: ignore [missing-import]
from sqlalchemy import select
# pyrefly: ignore [missing-import]
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
# pyrefly: ignore [missing-import]
from platform_be.core.config import Settings
# pyrefly: ignore [missing-import]
from platform_be.models.identity import User
# pyrefly: ignore [missing-import]
from platform_be.models.project import Project
# pyrefly: ignore [missing-import]
from platform_be.models.research import ResearchRun, RunEvent, RunGate

settings = Settings()
engine = create_async_engine(str(settings.database_url))
async_session_factory = async_sessionmaker(engine)

async def test_events_ingest():
    async with async_session_factory() as db:
        user = await db.scalar(select(User))
        if not user:
            user = User(
                id=uuid4(),
                email="test_user@example.com",
                display_name="Test User",
                password_scrypt="dummyhash",
                created_at=datetime.now(UTC),
            )
            db.add(user)
            await db.flush()

        project_id = uuid4()
        project = Project(
            id=project_id,
            name=f"Test Project {project_id.hex[:6]}",
            owner_user_id=user.id,
            status="researching",
            created_at=datetime.now(UTC),
        )
        db.add(project)
        await db.flush()

        run_id = uuid4()
        run = ResearchRun(
            id=run_id,
            project_id=project.id,
            created_by_user_id=user.id,
            topic="Test Sleep & Scores",
            status="queued",
            budget_usd=5.00,
            created_at=datetime.now(UTC),
        )
        db.add(run)
        await db.commit()
        print(f"Created test run: {run_id}")

    # Now make HTTP call to internal popper endpoint
    async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
        headers = {"X-Service-Key": "arc_internal_service_secret_key_32chars_min"}
        events_payload = {
            "events": [
                {
                    "source_seq": 1,
                    "type": "run.started",
                    "payload": {"mode": "copilot", "topic": "Test Sleep & Scores"}
                },
                {
                    "source_seq": 2,
                    "type": "scope.goal",
                    "stage_key": "scope",
                    "actor": "strategist",
                    "payload": {"statement": "Investigate sleep and score correlations"}
                },
                {
                    "source_seq": 3,
                    "type": "gate.opened",
                    "stage_key": "screen",
                    "actor": "pi",
                    "payload": {
                        "gate_id": "gate-1",
                        "kind": "screen",
                        "options": [{"id": "approve"}],
                        "droppable": ["paper-1"]
                    }
                }
            ]
        }

        resp = await client.post(
            f"/api/v1/internal/popper/runs/{run_id}/events",
            json=events_payload,
            headers=headers
        )
        print("POST /internal/popper/runs/{id}/events response:", resp.status_code, resp.json())
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["accepted"] == 3
        assert data["last_source_seq"] == 3

    # Verify Database rows
    async with async_session_factory() as db:
        events = (await db.scalars(select(RunEvent).where(RunEvent.run_id == run_id).order_by(RunEvent.seq))).all()
        print(f"Verified run_events in DB: count = {len(events)}")
        assert len(events) == 3
        assert events[0].seq == 1 and events[0].type == "run.started"
        assert events[1].seq == 2 and events[1].stage_key == "scope"
        assert events[2].seq == 3 and events[2].type == "gate.opened"

        gate = await db.scalar(select(RunGate).where(RunGate.run_id == run_id))
        print("Verified run_gate in DB:", gate.gate_key, "kind:", gate.kind)
        assert gate is not None and gate.gate_key == "gate-1"

        updated_run = await db.scalar(select(ResearchRun).where(ResearchRun.id == run_id))
        print("Verified research_runs status:", updated_run.status, "last_seq:", updated_run.last_seq)
        assert updated_run.status == "awaiting_review"
        assert updated_run.last_seq == 3

    print("\n🎉 PHASE 3 EVENTS INGESTION TEST PASSED 100%!")

asyncio.run(test_events_ingest())
