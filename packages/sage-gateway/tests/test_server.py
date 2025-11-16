"""
Integration tests for SAGE Gateway Server
"""

from fastapi.testclient import TestClient

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
    # 创建会话
    client.post(
        "/v1/chat/completions",
        json={
            "model": "sage-default",
            "messages": [{"role": "user", "content": "Test"}],
            "session_id": "delete-test",
        },
    )

    # 删除会话
    response = client.delete("/sessions/delete-test")
    assert response.status_code == 200
    assert response.json()["status"] == "deleted"
