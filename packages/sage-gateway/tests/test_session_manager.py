"""
Tests for Session Manager
"""

from sage.gateway.session import ChatSession, SessionManager


def test_session_creation():
    """测试会话创建"""
    session = ChatSession()
    assert session.id is not None
    assert len(session.messages) == 0


def test_add_message():
    """测试添加消息"""
    session = ChatSession()
    msg = session.add_message("user", "Hello")

    assert msg.role == "user"
    assert msg.content == "Hello"
    assert len(session.messages) == 1


def test_get_messages():
    """测试获取消息"""
    session = ChatSession()
    session.add_message("user", "Hi")
    session.add_message("assistant", "Hello")

    messages = session.get_messages()
    assert len(messages) == 2
    assert messages[0]["role"] == "user"
    assert messages[1]["role"] == "assistant"


def test_session_manager_get_or_create():
    """测试会话管理器的获取或创建"""
    manager = SessionManager()

    # 创建新会话
    session1 = manager.get_or_create()
    assert session1.id is not None

    # 获取现有会话
    session2 = manager.get_or_create(session1.id)
    assert session2.id == session1.id


def test_session_manager_delete():
    """测试删除会话"""
    manager = SessionManager()
    session = manager.get_or_create()

    assert manager.delete(session.id) is True
    assert manager.get(session.id) is None


def test_session_manager_stats():
    """测试统计信息"""
    manager = SessionManager()
    session = manager.get_or_create()
    session.add_message("user", "Test")

    stats = manager.get_stats()
    assert stats["total_sessions"] == 1
    assert stats["total_messages"] == 1
