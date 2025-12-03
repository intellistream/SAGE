"""
Integration tests for SAGE Gateway Server
"""

import time
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from sage.gateway.adapters import (
    ChatCompletionChoice,
    ChatCompletionResponse,
    ChatCompletionUsage,
    ChatMessage,
)
from sage.gateway.server import app

client = TestClient(app)


def test_root_endpoint():
    """测试根路径"""
    response = client.get("/")
    assert response.status_code == 200
    assert "service" in response.json()
    assert response.json()["service"] == "SAGE Gateway"


def test_health_endpoint():
    """测试健康检查"""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_chat_completions_non_stream():
    """测试非流式 chat completions"""
    # Mock the adapter's chat_completions to avoid RAG Pipeline dependency
    mock_response = ChatCompletionResponse(
        id="test-id-123",
        object="chat.completion",
        created=int(time.time()),
        model="sage-default",
        choices=[
            ChatCompletionChoice(
                index=0,
                message=ChatMessage(role="assistant", content="Hello, I am SAGE."),
                finish_reason="stop",
            )
        ],
        usage=ChatCompletionUsage(prompt_tokens=10, completion_tokens=20, total_tokens=30),
    )

    with patch(
        "sage.gateway.server.openai_adapter.chat_completions",
        new_callable=AsyncMock,
        return_value=mock_response,
    ):
        response = client.post(
            "/v1/chat/completions",
            json={
                "model": "sage-default",
                "messages": [{"role": "user", "content": "Hello"}],
                "stream": False,
            },
        )

    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert data["object"] == "chat.completion"
    assert len(data["choices"]) == 1
    assert data["choices"][0]["message"]["role"] == "assistant"


def test_sessions_list():
    """测试会话列表"""
    # Mock the adapter for session creation
    mock_response = ChatCompletionResponse(
        id="test-session-id",
        object="chat.completion",
        created=int(time.time()),
        model="sage-default",
        choices=[
            ChatCompletionChoice(
                index=0,
                message=ChatMessage(role="assistant", content="Test response"),
                finish_reason="stop",
            )
        ],
        usage=ChatCompletionUsage(prompt_tokens=5, completion_tokens=10, total_tokens=15),
    )

    with patch(
        "sage.gateway.server.openai_adapter.chat_completions",
        new_callable=AsyncMock,
        return_value=mock_response,
    ):
        # 先创建一个会话
        client.post(
            "/v1/chat/completions",
            json={
                "model": "sage-default",
                "messages": [{"role": "user", "content": "Test"}],
                "session_id": "test-session",
            },
        )

    # 获取会话列表
    response = client.get("/sessions")
    assert response.status_code == 200
    assert "sessions" in response.json()


def test_session_delete():
    """测试删除会话"""
    # 直接通过 session manager 创建会话（不通过 chat completions）
    from sage.gateway.session import get_session_manager

    session_manager = get_session_manager()
    session = session_manager.get_or_create("delete-test")
    session.add_message("user", "Test message")
    session_manager.persist()

    # 删除会话
    response = client.delete("/sessions/delete-test")
    assert response.status_code == 200
    assert response.json()["status"] == "deleted"


def test_session_delete_not_found():
    """测试删除不存在的会话"""
    response = client.delete("/sessions/nonexistent-session-12345")
    assert response.status_code == 404
