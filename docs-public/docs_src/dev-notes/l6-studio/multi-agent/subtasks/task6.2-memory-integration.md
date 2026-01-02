# Task 6.2: Memory 集成服务

## 目标

实现 Memory 集成服务，连接 sage-memory 的短期/长期记忆。

## 依赖

- sage-memory 包
- Task 3.2 (AgentOrchestrator)

## 文件位置

`packages/sage-studio/src/sage/studio/services/memory_integration.py`

## 提示词

````
请实现 Memory 集成服务，连接 sage-memory 的记忆功能。

## 背景
SAGE Studio 已有 MemorySettings.tsx，需要后端集成 sage-memory。
记忆类型:
- 短期记忆: 会话上下文
- 长期记忆: 用户偏好、历史知识

## 要求
1. 文件位置: packages/sage-studio/src/sage/studio/services/memory_integration.py

2. 功能:
   - 存储/检索会话上下文
   - 存储/检索用户长期记忆
   - 记忆相关性评分

3. 与 AgentOrchestrator 集成:
   - 处理消息前加载相关记忆
   - 处理完成后更新记忆

## 代码模板
```python
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
            from sage.memory import MemoryStore, ShortTermMemory, LongTermMemory

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
            self._fallback_memory.append(MemoryItem(
                id=f"mem_{len(self._fallback_memory)}",
                content=f"User: {user_message}\nAssistant: {assistant_response}",
                type="short_term",
                metadata=metadata,
            ))

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
            self._fallback_memory.append(MemoryItem(
                id=f"mem_{len(self._fallback_memory)}",
                content=content,
                type="long_term",
                metadata=metadata,
            ))

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
                results.append(MemoryItem(
                    id=item.id,
                    content=item.content,
                    type="short_term",
                    metadata=item.metadata,
                    relevance=item.score,
                ))

            # 长期记忆
            long_items = await self.long_term.search(query, top_k=max_items // 2)
            for item in long_items:
                results.append(MemoryItem(
                    id=item.id,
                    content=item.content,
                    type="long_term",
                    metadata=item.metadata,
                    relevance=item.score,
                ))
        else:
            # Fallback: 简单关键词匹配
            for item in self._fallback_memory[-max_items:]:
                if any(word in item.content.lower() for word in query.lower().split()):
                    item.relevance = 0.5
                    results.append(item)

        # 按相关性排序
        results.sort(key=lambda x: x.relevance, reverse=True)
        return results[:max_items]

    async def clear_short_term(self) -> None:
        """清除短期记忆"""
        if self._available:
            await self.short_term.clear()
        else:
            self._fallback_memory = [
                m for m in self._fallback_memory if m.type != "short_term"
            ]

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
                "short_term_count": len([m for m in self._fallback_memory if m.type == "short_term"]),
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
````

## 注意

- sage-memory 不可用时使用 fallback
- 短期/长期记忆分开管理
- 会话级别缓存实例

```

## 验收标准
- [ ] 正确连接 sage-memory
- [ ] 支持短期/长期记忆
- [ ] Fallback 机制正常
- [ ] 检索结果按相关性排序
```
