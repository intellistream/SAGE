"""Session Management for SAGE Gateway.

Provides in-memory management plus simple persistence so chat sessions survive
gateway restarts.
"""

# pyright: reportMissingImports=false

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
import uuid
from typing import Any

from .storage import FileSessionStore, SessionStorage


@dataclass
class ChatMessage:
    """单条聊天消息"""

    role: str  # system, user, assistant
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }


MAX_TITLE_LENGTH = 60


@dataclass
class ChatSession:
    """聊天会话"""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    messages: list[ChatMessage] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    last_active: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.metadata.setdefault("title", "New Chat")

    def add_message(self, role: str, content: str, metadata: dict | None = None) -> ChatMessage:
        """添加消息到会话并更新时间戳/标题"""
        message = ChatMessage(role=role, content=content, metadata=metadata or {})
        self.messages.append(message)
        self.last_active = datetime.now()

        if role == "user" and not self.metadata.get("title"):
            self.metadata["title"] = self._generate_title_from_content(content)

        return message

    def get_messages(self, limit: int | None = None) -> list[dict]:
        """获取消息历史（OpenAI 格式）"""
        messages = [{"role": msg.role, "content": msg.content} for msg in self.messages]
        if limit:
            return messages[-limit:]
        return messages

    def clear_history(self) -> None:
        """清空历史记录"""
        self.messages = []
        self.last_active = datetime.now()

    def rename(self, title: str) -> None:
        self.metadata["title"] = title[:MAX_TITLE_LENGTH] if title else "New Chat"

    @property
    def title(self) -> str:
        return self.metadata.get("title", "New Chat")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "messages": [msg.to_dict() for msg in self.messages],
            "created_at": self.created_at.isoformat(),
            "last_active": self.last_active.isoformat(),
            "metadata": self.metadata,
        }

    def to_summary(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "created_at": self.created_at.isoformat(),
            "last_active": self.last_active.isoformat(),
            "message_count": len(self.messages),
        }

    @staticmethod
    def _generate_title_from_content(content: str) -> str:
        first_line = content.strip().splitlines()[0] if content.strip() else "New Chat"
        return first_line[:MAX_TITLE_LENGTH] or "New Chat"


class SessionManager:
    """会话管理器（内存+文件存储）"""

    def __init__(self, storage: SessionStorage | None = None):
        self._storage = storage or FileSessionStore.default()
        self._sessions: dict[str, ChatSession] = {}
        self._load_sessions()

    def _load_sessions(self) -> None:
        for payload in self._storage.load():
            session = self._hydrate_session(payload)
            self._sessions[session.id] = session

    def _hydrate_session(self, payload: dict) -> ChatSession:
        session = ChatSession(
            id=payload.get("id", str(uuid.uuid4())),
            created_at=self._parse_datetime(payload.get("created_at")),
            last_active=self._parse_datetime(payload.get("last_active")),
            metadata=payload.get("metadata", {}) or {},
        )
        for message_data in payload.get("messages", []):
            session.messages.append(
                ChatMessage(
                    role=message_data.get("role", "user"),
                    content=message_data.get("content", ""),
                    timestamp=self._parse_datetime(message_data.get("timestamp")),
                    metadata=message_data.get("metadata", {}) or {},
                )
            )
        return session

    def _persist(self) -> None:
        self._storage.save([session.to_dict() for session in self._sessions.values()])

    def persist(self) -> None:
        """公开持久化方法，便于外部在批量更新后落盘"""
        self._persist()

    def create_session(
        self, title: str | None = None, session_id: str | None = None
    ) -> ChatSession:
        session = ChatSession(id=session_id or str(uuid.uuid4()))
        if title:
            session.rename(title)
        self._sessions[session.id] = session
        self._persist()
        return session

    def get_or_create(self, session_id: str | None = None) -> ChatSession:
        """获取或创建会话"""
        if session_id and session_id in self._sessions:
            session = self._sessions[session_id]
            session.last_active = datetime.now()
            self._persist()
            return session

        return self.create_session(session_id=session_id)

    def get(self, session_id: str) -> ChatSession | None:
        """获取会话"""
        return self._sessions.get(session_id)

    def delete(self, session_id: str) -> bool:
        """删除会话"""
        if session_id in self._sessions:
            del self._sessions[session_id]
            self._persist()
            return True
        return False

    def cleanup_expired(self, max_age_minutes: int = 30) -> int:
        """清理过期会话"""
        now = datetime.now()
        expired = [
            sid
            for sid, sess in self._sessions.items()
            if (now - sess.last_active).total_seconds() > max_age_minutes * 60
        ]
        for sid in expired:
            del self._sessions[sid]
        if expired:
            self._persist()
        return len(expired)

    def list_sessions(self) -> list[dict]:
        """列出会话摘要"""
        return sorted(
            [session.to_summary() for session in self._sessions.values()],
            key=lambda item: item["last_active"],
            reverse=True,
        )

    def clear_session(self, session_id: str) -> bool:
        session = self.get(session_id)
        if not session:
            return False
        session.clear_history()
        self._persist()
        return True

    def rename_session(self, session_id: str, title: str) -> bool:
        session = self.get(session_id)
        if not session:
            return False
        session.rename(title)
        self._persist()
        return True

    def get_stats(self) -> dict:
        """获取统计信息"""
        return {
            "total_sessions": len(self._sessions),
            "total_messages": sum(len(s.messages) for s in self._sessions.values()),
        }

    @staticmethod
    def _parse_datetime(value: str | None) -> datetime:
        if not value:
            return datetime.now()
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return datetime.now()


# 全局会话管理器实例
_session_manager: SessionManager | None = None


def get_session_manager() -> SessionManager:
    """获取全局会话管理器实例"""
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager
