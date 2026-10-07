import sys
import asyncio
sys.stdout.reconfigure(encoding="utf-8")

from researchclaw.pipeline.full_runner import execute_full_pipeline

class MockSession:
    def __init__(self, topic, domains):
        self.topic = topic
        self.domains = domains
        self.review_mode = "auto"
        self.popper_run_id = "test-run-1"
        self.events = []
        self.status = "running"
        self.message = ""
        self.gate_event = asyncio.Event()
        self.gate_answer = {}

    async def emit_event(self, event_type, payload, stage_key=None, actor=None):
        self.events.append((event_type, payload, stage_key, actor))
        if event_type == "agent.message":
            print(f"[{actor or 'agent'} thinking]: {payload.get('delta', '')}", end="", flush=True)
            if payload.get("done"):
                print("")
        elif event_type in ("stage.started", "step.started", "topic.evaluated", "run.status", "stage.completed"):
            print(f"\n>> EVENT: {event_type} | actor={actor} | payload={payload}")
        return {"type": event_type, "payload": payload}

async def run_test():
    print("==================================================")
    print("TESTING: 'tôi muốn ăn cơm' (Chủ đề phi khoa học)")
    print("==================================================")
    s1 = MockSession("tôi muốn ăn cơm", ["rice"])
    await execute_full_pipeline(s1)
    print("\nTotal events emitted:", len(s1.events))
    event_types = [e[0] for e in s1.events]
    print("Event sequence:", event_types)
    has_failed = any(e[0] == "run.status" and e[1].get("status") == "failed" for e in s1.events)
    has_search = any("search" in e[0] for e in s1.events)
    print(f"Halted at Stage 1 Scope: {has_failed}")
    print(f"Ran Search (should be False): {has_search}")

asyncio.run(run_test())
