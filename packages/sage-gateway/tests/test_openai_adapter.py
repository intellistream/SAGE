"""
Tests for OpenAI Adapter
"""

import pytest
from sage.gateway.adapters import ChatCompletionRequest, ChatMessage, OpenAIAdapter


@pytest.fixture
def adapter():
    return OpenAIAdapter()


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
