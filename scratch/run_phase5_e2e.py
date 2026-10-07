"""Phase 5 End-to-End Pipeline Verification Script.

Tests the full lifecycle:
1. Start run via POST /api/v1/projects/{project_id}/runs (Topic-to-Hypothesis flow)
2. Platform BE sends request to Engine ARC (PopperClient -> Engine ARC port 8001)
3. Connect SSE event stream at GET /api/v1/projects/{project_id}/runs/{run_id}/events/stream
4. Observe stages 1-5 streaming in real-time with sequential source_seq
5. Review gate triggers: status becomes awaiting_review
6. Answer gate via POST /api/v1/projects/{project_id}/runs/{run_id}/gates/{gate_id}
7. Observe engine unblocks and completes stages 6-8
8. Verify run completion, event sequence integrity, and gate records in DB.
"""

import asyncio
import json
import logging
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from platform_be.auth.sessions import (
    AuthSession,
    Principal,
    csrf_for_principal,
)
from platform_be.core.security import new_session_secret, token_digest
from platform_be.core.config import Settings
from platform_be.models.identity import User
from platform_be.models.project import Project, ProjectMembership
from platform_be.models.research import ResearchRun, RunEvent, RunGate

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("phase5_e2e")


async def main():
    settings = Settings()
    engine = create_async_engine(str(settings.database_url))
    session_factory = async_sessionmaker(engine)

    logger.info("=================================================================")
    logger.info("   PHASE 5: END-TO-END PIPELINE VERIFICATION TEST")
    logger.info("=================================================================")

    # 1. Prepare User, Project, ProjectMembership, and Session in DB
    async with session_factory() as db:
        user = await db.scalar(select(User).limit(1))
        if not user:
            user = User(
                id=uuid4(),
                email="admin@gmail.com",
                email_normalized="admin@gmail.com",
                display_name="Admin User",
                password_hash="dummyhash",
                status="active",
                email_verified_at=datetime.now(UTC),
                created_at=datetime.now(UTC),
            )
            db.add(user)
            await db.flush()

        project_id = uuid4()
        project = Project(
            id=project_id,
            name=f"Phase 5 Test Project {project_id.hex[:6]}",
            owner_user_id=user.id,
            status="researching",
            created_at=datetime.now(UTC),
        )
        db.add(project)
        await db.flush()

        membership = ProjectMembership(
            id=uuid4(),
            user_id=user.id,
            project_id=project.id,
            role_code="project_manager",
            status="active",
            created_by_user_id=user.id,
            created_at=datetime.now(UTC),
        )
        db.add(membership)

        user_id = user.id
        user_email = user.email

        raw_secret = new_session_secret()
        now = datetime.now(UTC)
        auth_session = AuthSession(
            id=uuid4(),
            user_id=user_id,
            token_digest=token_digest(raw_secret),
            created_at=now,
            last_seen_at=now,
            idle_expires_at=now + timedelta(hours=1),
            absolute_expires_at=now + timedelta(days=1),
        )
        db.add(auth_session)

        principal = Principal(user=user, session=auth_session, raw_secret=raw_secret)
        csrf = csrf_for_principal(principal, settings)

        await db.commit()

        logger.info(f"Created Test Project: {project_id}")
        logger.info(f"Authenticated as User: {user_email}")

    # 2. Setup HTTP Client targeting Platform BE
    client_headers = {
        "Origin": "http://localhost:3000",
        "X-CSRF-Token": csrf,
    }
    client_cookies = {
        settings.session_cookie_name: raw_secret,
    }

    async with httpx.AsyncClient(
        base_url="http://localhost:8000",
        headers=client_headers,
        cookies=client_cookies,
        timeout=60.0,
    ) as client:
        # 3. Create Topic-to-Hypothesis Run
        logger.info("\n--- STEP 1: POST /api/v1/projects/{project_id}/runs ---")
        run_payload = {
            "topic": "Neural dynamics of sleep spindle reactivation in memory",
            "domains": ["Neuroscience", "Cognitive Systems"],
            "review_mode": "copilot",
            "budget_usd": 5.0,
        }
        res = await client.post(f"/api/v1/projects/{project_id}/runs", json=run_payload)
        logger.info(f"Create Run Status: {res.status_code}")
        if res.status_code not in (201, 202):
            logger.error(f"Failed to create run: {res.text}")
            return False

        run_data = res.json()["data"]
        run_id = run_data["id"]
        logger.info(f"Run Created! Run ID: {run_id}, Initial Status: {run_data['status']}")

        # 4. Connect to SSE Stream and capture events in background
        logger.info("\n--- STEP 2: CONNECT SSE EVENT STREAM ---")
        received_sse_events = []
        gate_opened_event = asyncio.Event()
        run_ended_event = asyncio.Event()

        async def listen_sse():
            stream_url = f"/api/v1/projects/{project_id}/runs/{run_id}/events/stream"
            logger.info(f"Connecting to SSE: {stream_url}")
            try:
                async with client.stream("GET", stream_url, timeout=120.0) as stream_resp:
                    logger.info(f"SSE Connected with status: {stream_resp.status_code}")
                    buffer = ""
                    async for chunk in stream_resp.aiter_text():
                        buffer += chunk
                        while "\n\n" in buffer:
                            raw_event, buffer = buffer.split("\n\n", 1)
                            raw_event = raw_event.strip()
                            if not raw_event or raw_event.startswith(":"):
                                continue

                            lines = raw_event.split("\n")
                            event_type = "message"
                            event_data = ""
                            event_id = None
                            for line in lines:
                                if line.startswith("event:"):
                                    event_type = line.split(":", 1)[1].strip()
                                elif line.startswith("data:"):
                                    event_data = line.split(":", 1)[1].strip()
                                elif line.startswith("id:"):
                                    event_id = line.split(":", 1)[1].strip()

                            parsed_data = {}
                            if event_data:
                                try:
                                    parsed_data = json.loads(event_data)
                                except Exception:
                                    parsed_data = {"raw": event_data}

                            received_sse_events.append({
                                "type": event_type,
                                "id": event_id,
                                "data": parsed_data,
                            })

                            if event_type == "run-event":
                                evt_type = parsed_data.get("type")
                                stage = parsed_data.get("stage_key")
                                seq = parsed_data.get("seq")
                                logger.info(f"  [SSE #{seq}] {stage or 'global'} -> {evt_type}")
                                if evt_type == "gate.opened":
                                    logger.info("  >>> Detected gate.opened in SSE stream! <<<")
                                    gate_opened_event.set()

                            elif event_type == "run-ended":
                                logger.info(f"  >>> Detected run-ended in SSE stream! Status: {parsed_data.get('status')} <<<")
                                run_ended_event.set()
                                return
            except asyncio.CancelledError:
                pass
            except Exception as e:
                logger.warning(f"SSE listener stopped: {e}")

        sse_task = asyncio.create_task(listen_sse())

        # 5. Wait for gate.opened event (Screen gate at Stage 5)
        logger.info("\n--- STEP 3: AWAITING HUMAN-IN-THE-LOOP REVIEW GATE ---")
        try:
            await asyncio.wait_for(gate_opened_event.wait(), timeout=60.0)
        except TimeoutError:
            logger.error("Timed out waiting for gate.opened event!")
            sse_task.cancel()
            return False

        # 6. Verify Gate state in DB & API
        async with session_factory() as db:
            gate = await db.scalar(select(RunGate).where(RunGate.run_id == run_id))
            assert gate is not None, "RunGate row not found in DB!"
            gate_key = gate.gate_key
            spec = gate.spec
            logger.info(f"Gate retrieved: key={gate_key}, kind={gate.kind}")
            logger.info(f"Gate options: {spec.get('options')}")
            logger.info(f"Gate droppable: {spec.get('droppable')}")

            run = await db.scalar(select(ResearchRun).where(ResearchRun.id == run_id))
            assert run.status == "awaiting_review", f"Expected awaiting_review, got {run.status}"
            logger.info(f"Run status verified: {run.status}")

        # 7. Answer the Gate
        logger.info(f"\n--- STEP 4: ANSWER GATE ({gate_key}) VIA API ---")
        answer_payload = {
            "option_id": "approve",
            "dropped": ["paper_2022_03"] if "paper_2022_03" in spec.get("droppable", []) else [],
            "note": "Approved by PI. Dropped non-essential paper.",
        }
        gate_res = await client.post(
            f"/api/v1/projects/{project_id}/runs/{run_id}/gates/{gate_key}",
            json=answer_payload,
        )
        logger.info(f"Answer Gate Status: {gate_res.status_code}, Body: {gate_res.json()}")
        assert gate_res.status_code == 200, f"Failed to answer gate: {gate_res.text}"

        # 8. Wait for pipeline completion (Stages 6-8 + run.completed)
        logger.info("\n--- STEP 5: AWAITING COMPLETION (STAGES 6-8) ---")
        try:
            await asyncio.wait_for(run_ended_event.wait(), timeout=90.0)
        except TimeoutError:
            logger.error("Timed out waiting for run completion!")
            sse_task.cancel()
            return False

        # Clean up SSE task
        await asyncio.sleep(1.0)
        sse_task.cancel()

        # 9. Comprehensive DB Verification
        logger.info("\n--- STEP 6: VERIFY DATABASE INTEGRITY ---")
        async with session_factory() as db:
            db_run = await db.scalar(select(ResearchRun).where(ResearchRun.id == run_id))
            logger.info(f"Final Run Status: {db_run.status}")
            logger.info(f"Total Seq Count: {db_run.last_seq}")
            logger.info(f"Final Cost USD: {db_run.cost_usd}")
            assert db_run.status == "completed", f"Run should be completed, got {db_run.status}"

            db_events = (
                await db.scalars(
                    select(RunEvent).where(RunEvent.run_id == run_id).order_by(RunEvent.seq.asc())
                )
            ).all()

            logger.info(f"Stored Run Events Count: {len(db_events)}")
            assert len(db_events) > 0, "No events recorded in database!"

            # Verify strictly contiguous sequences
            for idx, evt in enumerate(db_events, start=1):
                assert evt.seq == idx, f"Sequence gap/mismatch at index {idx}: got {evt.seq}"

            db_gate = await db.scalar(select(RunGate).where(RunGate.run_id == run_id))
            assert db_gate.answered_at is not None, "Gate was not marked answered!"
            assert db_gate.answer["option_id"] == "approve", "Gate answer option mismatch!"
            logger.info(f"Gate Record: status=answered, option={db_gate.answer['option_id']}, resolved_seq={db_gate.resolved_seq}")

        logger.info("\n=================================================================")
        logger.info("   🎉 PHASE 5 END-TO-END VERIFICATION: 100% SUCCESS!")
        logger.info("=================================================================")
        return True


if __name__ == "__main__":
    result = asyncio.run(main())
    if not result:
        exit(1)
