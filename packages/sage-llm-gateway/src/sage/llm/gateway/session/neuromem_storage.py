"""
NeuroMem-based Session Storage Backend

使用 SAGE 自己的 NeuroMem 组件进行 session 持久化，
展示 SAGE 的记忆存储能力，避免引入 Redis 等外部依赖。
"""

import json
import os
from typing import Any

from sage.middleware.components.sage_mem.neuromem.storage_engine.metadata_storage import (
    MetadataStorage,
)
from sage.middleware.components.sage_mem.neuromem.storage_engine.text_storage import (
    TextStorage,
)


class NeuroMemSessionStorage:
    """基于 NeuroMem 的 Session 存储后端

    使用 NeuroMem 的 TextStorage (存储 session JSON) 和 MetadataStorage (存储元数据)
    相比 Redis，NeuroMem 提供:
    - 本地文件持久化（无需额外服务）
    - SAGE 原生组件（展示框架能力）
    - 灵活的存储后端（可扩展到 Redis/PostgreSQL）

    实现 SessionStorage Protocol 接口
    """

    def __init__(self, data_dir: str | None = None):
        """初始化 NeuroMem 存储

        Args:
            data_dir: 数据目录，默认为 ~/.sage/gateway/neuromem_sessions
        """
        if data_dir is None:
            data_dir = os.path.expanduser("~/.sage/gateway/neuromem_sessions")

        os.makedirs(data_dir, exist_ok=True)

        self.data_dir = data_dir
        self.text_storage_path = os.path.join(data_dir, "sessions.json")
        self.metadata_storage_path = os.path.join(data_dir, "metadata.json")

        # 初始化 NeuroMem 存储引擎
        self.text_storage = TextStorage()
        self.metadata_storage = MetadataStorage()

        # 注册元数据字段
        self._register_metadata_fields()

        # 从磁盘加载现有数据
        self._load_from_disk()

    def _register_metadata_fields(self) -> None:
        """注册 session 元数据字段"""
        fields = [
            "created_at",
            "last_active",
            "title",
            "message_count",
            "total_tokens",
        ]
        for field in fields:
            if not self.metadata_storage.has_field(field):
                self.metadata_storage.add_field(field)

    def _load_from_disk(self) -> None:
        """从磁盘加载数据"""
        try:
            if os.path.exists(self.text_storage_path):
                self.text_storage.load_from_disk(self.text_storage_path)
            if os.path.exists(self.metadata_storage_path):
                self.metadata_storage.load_from_disk(self.metadata_storage_path)
        except Exception:
            # 如果加载失败，从空状态开始
            pass

    def save(self, sessions: list[dict[str, Any]]) -> None:
        """保存所有 session 到 NeuroMem

        Args:
            sessions: Session 数据列表
        """
        # 清空现有数据
        self.text_storage.clear()
        self.metadata_storage.clear()
        self._register_metadata_fields()

        # 存储每个 session
        for session_data in sessions:
            session_id = session_data["id"]

            # 存储 session JSON 到 TextStorage
            session_json = json.dumps(session_data, ensure_ascii=False)
            self.text_storage.store(session_id, session_json)

            # 存储元数据到 MetadataStorage
            metadata = {
                "created_at": session_data.get("created_at", ""),
                "last_active": session_data.get("last_active", ""),
                "title": session_data.get("metadata", {}).get("title", "New Chat"),
                "message_count": len(session_data.get("messages", [])),
                "total_tokens": session_data.get("metadata", {}).get("total_tokens", 0),
            }
            self.metadata_storage.store(session_id, metadata)

        # 持久化到磁盘
        self.text_storage.store_to_disk(self.text_storage_path)
        self.metadata_storage.store_to_disk(self.metadata_storage_path)

    def load(self) -> list[dict[str, Any]]:
        """从 NeuroMem 加载所有 session

        Returns:
            Session 数据列表
        """
        sessions = []
        all_ids = self.text_storage.get_all_ids()

        for session_id in all_ids:
            try:
                # 从 TextStorage 获取 session JSON
                session_json = self.text_storage.get(session_id)
                if session_json:
                    session_data = json.loads(session_json)
                    sessions.append(session_data)
            except (json.JSONDecodeError, Exception):
                # 跳过损坏的 session
                continue

        return sessions

    def get_stats(self) -> dict[str, Any]:
        """获取存储统计信息

        Returns:
            统计信息字典
        """
        all_ids = self.text_storage.get_all_ids()
        total_messages = 0
        total_tokens = 0

        for session_id in all_ids:
            metadata = self.metadata_storage.get(session_id)
            if metadata:
                total_messages += metadata.get("message_count", 0)
                total_tokens += metadata.get("total_tokens", 0)

        return {
            "total_sessions": len(all_ids),
            "total_messages": total_messages,
            "total_tokens": total_tokens,
            "storage_backend": "NeuroMem",
            "data_directory": self.data_dir,
        }

    def clear(self) -> None:
        """清空所有 session 数据"""
        self.text_storage.clear()
        self.metadata_storage.clear()
        self._register_metadata_fields()

        # 同步到磁盘
        self.text_storage.store_to_disk(self.text_storage_path)
        self.metadata_storage.store_to_disk(self.metadata_storage_path)

    @classmethod
    def default(cls) -> "NeuroMemSessionStorage":
        """创建默认的 NeuroMem 存储实例

        Returns:
            默认配置的 NeuroMemSessionStorage 实例
        """
        return cls()
