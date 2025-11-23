"""Tests for Session Manager."""

from datetime import datetime, timedelta
from pathlib import Path

import pytest

from sage.gateway.session import ChatSession, SessionManager
from sage.gateway.session.storage import FileSessionStore


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


@pytest.fixture()
def temp_storage(tmp_path: Path) -> FileSessionStore:
    return FileSessionStore(path=tmp_path / "sessions.json")


def test_session_manager_get_or_create(temp_storage):
    """测试会话管理器的获取或创建"""
    manager = SessionManager(storage=temp_storage)

    # 创建新会话
    session1 = manager.get_or_create()
    assert session1.id is not None

    # 获取现有会话
    session2 = manager.get_or_create(session1.id)
    assert session2.id == session1.id


def test_session_manager_delete(temp_storage):
    """测试删除会话"""
    manager = SessionManager(storage=temp_storage)
    session = manager.get_or_create()

    assert manager.delete(session.id) is True
    assert manager.get(session.id) is None


def test_session_manager_stats(temp_storage):
    """测试统计信息"""
    manager = SessionManager(storage=temp_storage)

    # 清除所有会话
    for session_id in list(manager._sessions.keys()):
        manager.delete(session_id)

    # 创建一个新会话
    session = manager.get_or_create()
    session.add_message("user", "Test")

    stats = manager.get_stats()
    assert stats["total_sessions"] == 1
    assert stats["total_messages"] == 1

    manager.delete(session.id)


def test_store_and_retrieve_memory_short_term(temp_storage):
    manager = SessionManager(
        storage=temp_storage, max_memory_dialogs=5, memory_backend="short_term"
    )
    session = manager.get_or_create("mem-session")

    manager.store_dialog_to_memory(session.id, "你好", "您好，有什么可以帮您？")

    history = manager.retrieve_memory_history(session.id)
    assert "user: 你好" in history
    assert "assistant: 您好，有什么可以帮您？" in history


def test_cleanup_expired_sessions(temp_storage):
    manager = SessionManager(storage=temp_storage)
    session = manager.get_or_create("old-session")
    session.last_active = datetime.now() - timedelta(minutes=120)
    manager.persist()

    cleaned = manager.cleanup_expired(max_age_minutes=30)
    assert cleaned == 1
    assert manager.get("old-session") is None


def test_list_sessions_sorted(temp_storage):
    manager = SessionManager(storage=temp_storage)
    first = manager.get_or_create("first")
    first.add_message("user", "hello")

    second = manager.get_or_create("second")
    second.add_message("user", "later")
    second.last_active = datetime.now() + timedelta(seconds=1)
    manager.persist()

    summaries = manager.list_sessions()
    assert summaries[0]["id"] == "second"
