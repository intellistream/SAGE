from fastapi.testclient import TestClient

import sage.studio.config.backend.api as api
from sage.studio.models.agent_step import AgentStep


class _StubOrchestrator:
    def __init__(self):
        self.calls = []

    async def process_message(
        self,
        *,
        message: str,
        session_id: str,
        history: list | None = None,
        should_index: bool = False,
        metadata: dict | None = None,
        evidence: list | None = None,
    ):
        self.calls.append(
            {
                "message": message,
                "session_id": session_id,
                "history": history or [],
                "should_index": should_index,
                "metadata": metadata or {},
                "evidence": evidence or [],
            }
        )
        yield AgentStep.create("reasoning", "route")
        yield "answer"


def test_agent_chat_sync_forwards_payload(monkeypatch):
    stub = _StubOrchestrator()
    monkeypatch.setattr(api, "get_orchestrator", lambda: stub)

    client = TestClient(api.app)
    payload = {
        "message": "q1",
        "session_id": "sess-1",
        "history": [{"role": "user", "content": "prev"}],
        "should_index": True,
        "metadata": {"route": "agentic"},
        "evidence": [{"content": "ev"}],
    }

    resp = client.post("/api/chat/agent/sync", json=payload)

    assert resp.status_code == 200
    body = resp.json()
    assert body["response"] == "answer"
    assert body["steps"][0]["type"] == "reasoning"

    assert len(stub.calls) == 1
    call = stub.calls[0]
    assert call["message"] == "q1"
    assert call["session_id"] == "sess-1"
    assert call["should_index"] is True
    assert call["metadata"]["route"] == "agentic"
    assert call["evidence"] == [{"content": "ev"}]
