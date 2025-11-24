"""Tests for OpenAI Adapter."""

from types import MethodType
from unittest.mock import MagicMock

import pytest
from sage.gateway.adapters import ChatCompletionRequest, ChatMessage, OpenAIAdapter


@pytest.fixture
def adapter(monkeypatch, tmp_path):
    # 使用临时存储，避免污染真实环境
    session_file = tmp_path / "sessions.json"
    monkeypatch.setenv("SAGE_GATEWAY_SESSION_FILE_PATH", str(session_file))

    monkeypatch.delenv("SAGE_CHAT_API_KEY", raising=False)
    monkeypatch.delenv("ALIBABA_API_KEY", raising=False)
    monkeypatch.delenv("DASHSCOPE_API_KEY", raising=False)

    dummy_pipeline = MagicMock()
    dummy_pipeline.process.return_value = {
        "answer": "Echo: Hello",
        "sources": [],
        "metadata": {},
        "content": "Echo: Hello",
    }

    monkeypatch.setattr(
        "sage.gateway.rag_pipeline.RAGPipelineService",
        lambda: dummy_pipeline,
    )

    adapter = OpenAIAdapter()
    adapter.rag_pipeline = dummy_pipeline
    adapter._pipeline_started = True

    return adapter


@pytest.mark.asyncio
async def test_chat_completions_basic(adapter):
    """测试基本的 chat completions"""
    request = ChatCompletionRequest(
        model="sage-default",
        messages=[ChatMessage(role="user", content="Hello")],
        stream=False,
    )

    response = await adapter.chat_completions(request)

    assert response.model == "sage-default"
    assert len(response.choices) == 1
    assert response.choices[0].message.role == "assistant"
    assert "Echo" in response.choices[0].message.content


@pytest.mark.asyncio
async def test_chat_completions_stream(adapter):
    """测试流式 chat completions"""
    request = ChatCompletionRequest(
        model="sage-default",
        messages=[ChatMessage(role="user", content="Hi")],
        stream=True,
    )

    response = await adapter.chat_completions(request)

    # 收集所有流式响应
    chunks = []
    async for chunk in response:
        chunks.append(chunk)

    assert len(chunks) > 0
    assert any("data:" in chunk for chunk in chunks)
    assert any("[DONE]" in chunk for chunk in chunks)


@pytest.mark.asyncio
async def test_session_persistence(adapter):
    """测试会话持久化"""
    session_id = "test-session"

    # 第一条消息
    request1 = ChatCompletionRequest(
        model="sage-default",
        messages=[ChatMessage(role="user", content="My name is Alice")],
        session_id=session_id,
    )
    await adapter.chat_completions(request1)

    # 第二条消息（同一会话）
    request2 = ChatCompletionRequest(
        model="sage-default",
        messages=[ChatMessage(role="user", content="What's my name?")],
        session_id=session_id,
    )
    await adapter.chat_completions(request2)

    # 验证会话中有两条消息
    session = adapter.session_manager.get(session_id)
    assert len(session.messages) >= 2


@pytest.mark.asyncio
async def test_chat_completions_store_memory(adapter):
    adapter.rag_pipeline.process.return_value = {"content": "Hi", "sources": []}
    store_spy = MagicMock()
    adapter.session_manager.store_dialog_to_memory = store_spy

    request = ChatCompletionRequest(
        model="sage-default",
        messages=[ChatMessage(role="user", content="hello store")],
        stream=False,
    )

    await adapter.chat_completions(request)

    store_spy.assert_called_once()


@pytest.mark.asyncio
async def test_execute_sage_pipeline_workflow_response(adapter):
    adapter.rag_pipeline.process.return_value = {
        "type": "workflow",
        "workflow_data": {"visual_pipeline": {"nodes": [], "connections": []}},
        "content": "workflow ready",
    }

    request = ChatCompletionRequest(
        model="sage-default",
        messages=[ChatMessage(role="user", content="帮我创建一个工作流")],
    )
    session = adapter.session_manager.get_or_create("workflow-test")

    result = await adapter._execute_sage_pipeline(request, session)

    assert "```json" in result
    assert "workflow ready" in result


@pytest.mark.asyncio
async def test_execute_sage_pipeline_error_response(adapter):
    adapter.rag_pipeline.process.return_value = {
        "type": "error",
        "content": "failed",
    }

    request = ChatCompletionRequest(
        model="sage-default",
        messages=[ChatMessage(role="user", content="error")],
    )
    session = adapter.session_manager.get_or_create("error-test")

    result = await adapter._execute_sage_pipeline(request, session)

    assert result == "failed"


@pytest.mark.asyncio
async def test_execute_sage_pipeline_fallback_on_exception(adapter):
    adapter.rag_pipeline.process.side_effect = RuntimeError("boom")

    async def fake_fallback(self, request, user_input):
        return "fallback"

    adapter._fallback_direct_llm = MethodType(fake_fallback, adapter)

    request = ChatCompletionRequest(
        model="sage-default",
        messages=[ChatMessage(role="user", content="hello")],
    )
    session = adapter.session_manager.get_or_create("fallback-test")

    result = await adapter._execute_sage_pipeline(request, session)

    assert result == "fallback"
