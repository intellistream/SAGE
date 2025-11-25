"""Session Management for SAGE Gateway.

Provides in-memory management plus simple persistence so chat sessions survive
gateway restarts.

Supports multiple storage backends:
- FileSessionStore: JSON file storage (default)
- NeuroMemSessionStorage: SAGE's NeuroMem component (展示 SAGE 能力)
"""

# pyright: reportMissingImports=false

from __future__ import annotations

import logging
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from sage.middleware.components.sage_mem.neuromem.memory_collection import (
    BaseMemoryCollection,
)
from sage.middleware.components.sage_mem.neuromem.memory_manager import MemoryManager
from sage.middleware.components.sage_mem.services.memory_service_factory import (
    MemoryServiceFactory,
)

# Import sage-memory components
from sage.middleware.components.sage_mem.services.short_term_memory_service import (
    ShortTermMemoryService,
)

from .storage import FileSessionStore, SessionStorage

logger = logging.getLogger(__name__)


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
    """会话管理器（内存+文件存储）

    支持多种记忆体后端：
    - short_term: 短期记忆服务（滑动窗口，默认）
    - vdb: 向量数据库记忆（语义检索）
    - kv: 键值对记忆（快速查询）
    - graph: 图记忆（关系推理）
    """

    def __init__(
        self,
        storage: SessionStorage | None = None,
        max_memory_dialogs: int = 10,
        memory_backend: str = "short_term",
        memory_config: dict[str, Any] | None = None,
    ):
        """初始化会话管理器

        Args:
            storage: 会话存储后端
            max_memory_dialogs: 短期记忆最大对话轮数（仅 short_term 后端）
            memory_backend: 记忆体后端类型 (short_term/vdb/kv/graph)
            memory_config: 记忆体配置（各后端的特定配置）
        """
        self._storage = storage or FileSessionStore.default()
        self._sessions: dict[str, ChatSession] = {}

        # sage-memory: 为每个session维护独立的记忆服务
        self._memory_services: dict[str, ShortTermMemoryService | BaseMemoryCollection] = {}
        self._max_memory_dialogs = max_memory_dialogs
        self._memory_backend = memory_backend
        self._memory_config = memory_config or {}

        # 如果使用 neuromem collection，初始化 MemoryManager
        if memory_backend in ("vdb", "kv", "graph"):
            self._memory_manager = MemoryManager()
        else:
            self._memory_manager = None

        self._load_sessions()

    def _load_sessions(self) -> None:
        for payload in self._storage.load():
            session = self._hydrate_session(payload)
            self._sessions[session.id] = session

            # 为加载的会话创建记忆服务
            self._memory_services[session.id] = self._create_memory_service(session.id)

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

        # 为新session创建独立的记忆服务
        self._memory_services[session.id] = self._create_memory_service(session.id)

        self._persist()
        return session

    def _create_memory_service(
        self, session_id: str
    ) -> ShortTermMemoryService | BaseMemoryCollection:
        """为会话创建记忆服务

        根据配置的后端类型创建不同的记忆服务：
        - short_term: 短期记忆（滑动窗口）
        - vdb: 向量数据库（语义检索）
        - kv: 键值存储（快速查询）
        - graph: 图记忆（关系推理）
        """
        if self._memory_backend == "short_term":
            # 使用 MemoryServiceFactory 创建短期记忆服务
            return MemoryServiceFactory.create_instance(
                "short_term_memory", max_dialog=self._max_memory_dialogs
            )

        elif self._memory_backend == "vdb":
            # 向量数据库记忆
            index_name = f"vdb_index_{session_id}"
            config = {
                "name": f"session_{session_id}_vdb",
                "backend_type": "VDB",
                "description": f"Vector memory for session {session_id}",
            }
            collection = self._memory_manager.create_collection(config)

            # 创建索引
            index_config = {
                "name": index_name,
                "embedding_model": self._memory_config.get("embedding_model", "hash"),
                "dim": self._memory_config.get("embedding_dim", 384),
                "backend_type": "FAISS",
                "description": "Session vector index",
                "index_parameter": {},
            }
            collection.create_index(index_config)

            # 保存 index_name 用于后续操作
            collection._gateway_index_name = index_name
            return collection

        elif self._memory_backend == "kv":
            # 键值存储记忆
            index_name = f"kv_index_{session_id}"
            config = {
                "name": f"session_{session_id}_kv",
                "backend_type": "KV",
                "description": f"KV memory for session {session_id}",
            }
            collection = self._memory_manager.create_collection(config)

            # 创建索引
            index_config = {
                "name": index_name,
                "index_type": self._memory_config.get("default_index_type", "bm25s"),
                "description": "Session KV index",
            }
            collection.create_index(index_config)

            # 保存 index_name 用于后续操作
            collection._gateway_index_name = index_name
            return collection

        elif self._memory_backend == "graph":
            # 图记忆
            config = {
                "name": f"session_{session_id}_graph",
                "backend_type": "Graph",
                "description": f"Graph memory for session {session_id}",
            }
            return self._memory_manager.create_collection(config)

        else:
            # 默认使用短期记忆
            return ShortTermMemoryService(max_dialog=self._max_memory_dialogs)

    def get_or_create(self, session_id: str | None = None) -> ChatSession:
        """获取或创建会话"""
        if session_id and session_id in self._sessions:
            session = self._sessions[session_id]
            session.last_active = datetime.now()
            self._persist()
            return session

        session = self.create_session(session_id=session_id)

        # 确保记忆服务存在
        if session.id not in self._memory_services:
            self._memory_services[session.id] = self._create_memory_service(session.id)

        return session

    def get(self, session_id: str) -> ChatSession | None:
        """获取会话"""
        return self._sessions.get(session_id)

    def delete(self, session_id: str) -> bool:
        """删除会话"""
        if session_id in self._sessions:
            del self._sessions[session_id]

            # 清理关联的记忆服务
            if session_id in self._memory_services:
                memory_service = self._memory_services[session_id]

                # 对于 neuromem collection，需要通过 MemoryManager 删除
                if (
                    self._memory_backend in ("vdb", "kv", "graph")
                    and self._memory_manager
                    and isinstance(memory_service, BaseMemoryCollection)
                ):
                    try:
                        collection_name = f"session_{session_id}_{self._memory_backend}"
                        self._memory_manager.delete_collection(collection_name)
                    except Exception as e:
                        logger.warning(f"Failed to delete memory collection: {e}")

                del self._memory_services[session_id]

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

    def get_memory_service(
        self, session_id: str
    ) -> ShortTermMemoryService | BaseMemoryCollection | None:
        """获取会话的记忆服务

        Args:
            session_id: 会话ID

        Returns:
            对应的记忆服务实例，如果会话不存在则返回 None
        """
        # 如果会话不存在，返回 None
        if session_id not in self._sessions:
            return None

        # 如果记忆服务不存在，自动创建
        if session_id not in self._memory_services:
            self._memory_services[session_id] = self._create_memory_service(session_id)

        return self._memory_services.get(session_id)

    def store_dialog_to_memory(
        self, session_id: str, user_message: str, assistant_message: str
    ) -> None:
        """将一轮对话存储到记忆服务

        支持多种后端：
        - short_term: 使用滑动窗口存储
        - vdb: 向量化后存储到向量数据库
        - kv: 以键值对形式存储
        - graph: 构建对话关系图

        Args:
            session_id: 会话ID
            user_message: 用户消息
            assistant_message: 助手回复
        """
        memory_service = self.get_memory_service(session_id)
        if not memory_service:
            return

        if self._memory_backend == "short_term":
            # 短期记忆服务使用原有格式
            dialog = [
                {"speaker": "user", "text": user_message},
                {"speaker": "assistant", "text": assistant_message},
            ]
            memory_service.insert(dialog)

        elif self._memory_backend in ("vdb", "kv", "graph"):
            # neuromem collection 使用统一的存储接口
            import time

            # 合并对话内容
            combined_text = f"User: {user_message}\nAssistant: {assistant_message}"

            # 元数据
            metadata = {
                "session_id": session_id,
                "user_message": user_message,
                "assistant_message": assistant_message,
                "timestamp": time.time(),
            }

            # 存储到 collection
            if self._memory_backend == "vdb":
                # VDB 需要 index_name 参数
                index_name = getattr(memory_service, "_gateway_index_name", None)
                if index_name:
                    memory_service.insert(
                        index_name=index_name, raw_data=combined_text, metadata=metadata
                    )
            elif self._memory_backend == "kv":
                # KV 需要 index_names 参数（可变参数）
                index_name = getattr(memory_service, "_gateway_index_name", None)
                if index_name:
                    memory_service.insert(combined_text, metadata, index_name)
            else:
                # Graph 使用 BaseMemoryCollection 的 insert 接口
                memory_service.insert(raw_text=combined_text, metadata=metadata)

    def retrieve_memory_history(self, session_id: str) -> str:
        """获取会话的历史记忆

        支持多种后端：
        - short_term: 返回滑动窗口内的对话
        - vdb/kv/graph: 通过 retrieve 方法检索对话片段

        Args:
            session_id: 会话ID

        Returns:
            格式化的记忆历史字符串
        """
        memory_service = self.get_memory_service(session_id)
        if not memory_service:
            return ""

        if self._memory_backend == "short_term":
            # 短期记忆服务使用原有格式
            memory_data = memory_service.retrieve()

            if not memory_data:
                return ""

            history_parts = []
            for item in memory_data:
                dialog = item.get("dialog", [])
                for turn in dialog:
                    speaker = turn.get("speaker", "unknown")
                    text = turn.get("text", "")
                    history_parts.append(f"{speaker}: {text}")

            return "\n".join(history_parts)

        elif self._memory_backend in ("vdb", "kv", "graph"):
            # neuromem collection 使用 retrieve 方法
            try:
                if self._memory_backend == "vdb":
                    # VDB 需要 raw_data 和 index_name 参数进行语义检索
                    index_name = getattr(memory_service, "_gateway_index_name", None)
                    if not index_name:
                        return ""

                    # 使用空查询检索所有内容（通过元数据过滤）
                    results = memory_service.retrieve(
                        raw_data="",  # VDB 需要查询文本
                        index_name=index_name,
                        topk=self._memory_config.get("max_retrieve", 100),
                        with_metadata=True,
                        session_id=session_id,  # 元数据过滤
                    )

                elif self._memory_backend == "kv":
                    # KV 需要 raw_text 参数进行关键词检索
                    index_name = getattr(memory_service, "_gateway_index_name", None)
                    if not index_name:
                        return ""

                    results = memory_service.retrieve(
                        raw_text="",  # KV 需要查询文本
                        index_name=index_name,
                        topk=self._memory_config.get("max_retrieve", 100),
                        with_metadata=True,
                        session_id=session_id,  # 元数据过滤
                    )

                else:  # graph
                    # Graph 使用 BaseMemoryCollection 的 retrieve 接口
                    results = memory_service.retrieve(
                        with_metadata=True,
                        session_id=session_id,  # 元数据过滤
                    )

                if not results:
                    return ""

                # 按时间戳排序（如果有）
                results_sorted = sorted(
                    results, key=lambda x: x.get("metadata", {}).get("timestamp", 0)
                )

                # 格式化结果
                history_parts = []
                for result in results_sorted:
                    metadata = result.get("metadata", {})
                    user_msg = metadata.get("user_message", "")
                    assistant_msg = metadata.get("assistant_message", "")

                    if user_msg:
                        history_parts.append(f"user: {user_msg}")
                    if assistant_msg:
                        history_parts.append(f"assistant: {assistant_msg}")

                return "\n".join(history_parts)

            except Exception as e:
                logger.warning(f"Failed to retrieve memory from {self._memory_backend}: {e}")
                return ""

        return ""

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


def _create_storage_backend() -> SessionStorage:
    """根据环境变量创建存储后端

    支持的后端:
    - file: JSON 文件存储 (默认)
    - neuromem: SAGE NeuroMem 存储 (推荐，展示 SAGE 能力)

    环境变量:
    - SAGE_GATEWAY_SESSION_BACKEND: 后端类型 (file/neuromem)
    - SAGE_GATEWAY_SESSION_FILE_PATH: file 后端路径
    - SAGE_GATEWAY_SESSION_NEUROMEM_PATH: neuromem 后端路径
    """
    backend_type = os.getenv("SAGE_GATEWAY_SESSION_BACKEND", "file").lower()

    if backend_type == "neuromem":
        try:
            from .neuromem_storage import NeuroMemSessionStorage

            data_dir = os.getenv("SAGE_GATEWAY_SESSION_NEUROMEM_PATH")
            if data_dir:
                return NeuroMemSessionStorage(data_dir=data_dir)
            return NeuroMemSessionStorage.default()
        except ImportError:
            # NeuroMem 依赖未安装，降级到文件存储
            import warnings

            warnings.warn(
                "NeuroMem backend requested but not available, falling back to file storage"
            )
            return FileSessionStore.default()
    else:
        # 默认使用文件存储
        file_path = os.getenv("SAGE_GATEWAY_SESSION_FILE_PATH")
        if file_path:
            from pathlib import Path

            return FileSessionStore(path=Path(file_path))
        return FileSessionStore.default()


def get_session_manager() -> SessionManager:
    """获取全局会话管理器实例"""
    global _session_manager
    if _session_manager is None:
        storage = _create_storage_backend()
        _session_manager = SessionManager(storage=storage)
    return _session_manager
