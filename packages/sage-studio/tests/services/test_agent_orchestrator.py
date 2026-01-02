from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from sage.libs.agentic.workflows.router import WorkflowRoute
from sage.studio.models.agent_step import AgentStep
from sage.studio.services import memory_integration
from sage.studio.services.agent_orchestrator import AgentOrchestrator


@pytest.mark.asyncio
async def test_agentic_evidence_ingested(monkeypatch):
    # Force memory service to fallback implementation
    monkeypatch.setattr(memory_integration, "_memory_instances", {})

    def _stub_init(self):
        self._available = False
        self._fallback_memory = []

    monkeypatch.setattr(
        memory_integration.MemoryIntegrationService, "_init_memory_backend", _stub_init
    )

    orchestrator = AgentOrchestrator()

    decision = SimpleNamespace(
        route=WorkflowRoute.AGENTIC,
        intent=SimpleNamespace(value="agentic"),
        confidence=0.9,
        matched_keywords=[],
        should_index=True,
    )

    orchestrator.workflow_router.decide = AsyncMock(return_value=decision)
    orchestrator.knowledge_manager.ingest_texts = AsyncMock(return_value=1)

    async def fake_run(message, history):
        yield AgentStep.create(
            "tool_result",
            "found",
            raw_results=[{"content": "evidence text", "source": "mock"}],
        )
        yield "final"

    orchestrator.researcher_agent.run = fake_run

    items = []
    async for item in orchestrator.process_message("question", "sess-123"):
        items.append(item)

    orchestrator.knowledge_manager.ingest_texts.assert_called_once()

    mem = memory_integration.get_memory_service("sess-123")
    assert any(m.metadata.get("evidence") for m in getattr(mem, "_fallback_memory", []))
    assert "final" in "".join(str(x) for x in items if isinstance(x, str))


def test_resolve_gateway_base_url_env(monkeypatch):
    monkeypatch.setenv("SAGE_GATEWAY_BASE_URL", "http://env-host:9999")
    orch = AgentOrchestrator()
    assert orch._resolve_gateway_base_url() == "http://env-host:9999"


@pytest.mark.asyncio
async def test_call_gateway_chat_uses_resolved_base(monkeypatch):
    orch = AgentOrchestrator()
    orch._resolve_gateway_base_url = MagicMock(return_value="http://example.com")

    async def _fake_post(url, json):
        class _Resp:
            status_code = 200

            def json(self):
                return {"choices": [{"message": {"content": "hi"}}]}

        _fake_post.called_url = url
        _fake_post.called_json = json
        return _Resp()

    class _Client:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        post = _fake_post

    monkeypatch.setattr("httpx.AsyncClient", lambda timeout, trust_env: _Client())

    out = await orch._call_gateway_chat(
        message="m",
        session_id="s",
        context_items=[],
        evidence=[],
    )

    assert out == "hi"
    assert _fake_post.called_url == "http://example.com/v1/chat/completions"
    assert _fake_post.called_json["session_id"] == "s"
