from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class MemoryItem:
    """记忆项"""

    id: str
    content: str
    type: str  # "short_term", "long_term"
    metadata: dict[str, Any]
    relevance: float = 0.0


class MemoryIntegrationService:
    """记忆集成服务

    连接 sage-memory，提供记忆存储和检索。
    """

    def __init__(self, session_id: str):
        self.session_id = session_id
        self._init_memory_backend()

    def _init_memory_backend(self):
        """初始化记忆后端"""
        try:
            from sage.memory import LongTermMemory, MemoryStore, ShortTermMemory

            self.store = MemoryStore(session_id=self.session_id)
            self.short_term = ShortTermMemory(store=self.store)
            self.long_term = LongTermMemory(store=self.store)
            self._available = True
        except ImportError:
            logger.warning("sage-memory not available, using fallback")
            self._available = False
            self._fallback_memory: list[MemoryItem] = []

    async def add_interaction(
        self,
        user_message: str,
        assistant_response: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """添加交互到短期记忆"""
        metadata = metadata or {}

        if self._available:
            await self.short_term.add(
                content=f"User: {user_message}\nAssistant: {assistant_response}",
                metadata={"type": "interaction", **metadata},
            )
        else:
            self._fallback_memory.append(
                MemoryItem(
                    id=f"mem_{len(self._fallback_memory)}",
                    content=f"User: {user_message}\nAssistant: {assistant_response}",
                    type="short_term",
                    metadata=metadata,
                )
            )

    async def add_knowledge(
        self,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """添加知识到长期记忆"""
        metadata = metadata or {}

        if self._available:
            await self.long_term.add(
                content=content,
                metadata={"type": "knowledge", **metadata},
            )
        else:
            self._fallback_memory.append(
                MemoryItem(
                    id=f"mem_{len(self._fallback_memory)}",
                    content=content,
                    type="long_term",
                    metadata=metadata,
                )
            )

    async def add_evidence_batch(
        self,
        items: list[MemoryItem] | list[dict[str, Any]],
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Store retrieved evidence into long-term memory for future recall."""

        meta = metadata or {}
        for item in items:
            if isinstance(item, MemoryItem):
                await self.add_knowledge(item.content, {"evidence": True, **meta})
            else:
                content = item.get("content")
                if content:
                    await self.add_knowledge(content, {"evidence": True, **meta})

    async def retrieve_context(
        self,
        query: str,
        max_items: int = 5,
    ) -> list[MemoryItem]:
        """检索相关上下文"""
        results = []

        if self._available:
            # 短期记忆
            short_items = await self.short_term.search(query, top_k=max_items // 2)
            for item in short_items:
                results.append(
                    MemoryItem(
                        id=item.id,
                        content=item.content,
                        type="short_term",
                        metadata=item.metadata,
                        relevance=item.score,
                    )
                )

            # 长期记忆
            long_items = await self.long_term.search(query, top_k=max_items // 2)
            for item in long_items:
                results.append(
                    MemoryItem(
                        id=item.id,
                        content=item.content,
                        type="long_term",
                        metadata=item.metadata,
                        relevance=item.score,
                    )
                )
        else:
            # Fallback: 简单关键词匹配
            for item in self._fallback_memory[-max_items:]:
                if any(word in item.content.lower() for word in query.lower().split()):
                    # 简单的相关性模拟
                    relevance = 0.5
                    results.append(
                        MemoryItem(
                            id=item.id,
                            content=item.content,
                            type=item.type,
                            metadata=item.metadata,
                            relevance=relevance,
                        )
                    )

            # 如果没有找到匹配项，但有最近的短期记忆，也返回一些作为上下文
            if not results:
                short_term_items = [m for m in self._fallback_memory if m.type == "short_term"]
                for item in short_term_items[-2:]:  # 取最近2条
                    results.append(
                        MemoryItem(
                            id=item.id,
                            content=item.content,
                            type=item.type,
                            metadata=item.metadata,
                            relevance=0.1,  # 低相关性，仅作为最近上下文
                        )
                    )

        # 按相关性排序
        results.sort(key=lambda x: x.relevance, reverse=True)
        return results[:max_items]

    async def clear_short_term(self) -> None:
        """清除短期记忆"""
        if self._available:
            await self.short_term.clear()
        else:
            self._fallback_memory = [m for m in self._fallback_memory if m.type != "short_term"]

    async def get_summary(self) -> dict[str, Any]:
        """获取记忆摘要"""
        if self._available:
            return {
                "short_term_count": await self.short_term.count(),
                "long_term_count": await self.long_term.count(),
                "available": True,
            }
        else:
            return {
                "short_term_count": len(
                    [m for m in self._fallback_memory if m.type == "short_term"]
                ),
                "long_term_count": len([m for m in self._fallback_memory if m.type == "long_term"]),
                "available": False,
            }


# 会话记忆缓存
_memory_instances: dict[str, MemoryIntegrationService] = {}


def get_memory_service(session_id: str) -> MemoryIntegrationService:
    """获取会话的记忆服务"""
    if session_id not in _memory_instances:
        _memory_instances[session_id] = MemoryIntegrationService(session_id)
    return _memory_instances[session_id]
