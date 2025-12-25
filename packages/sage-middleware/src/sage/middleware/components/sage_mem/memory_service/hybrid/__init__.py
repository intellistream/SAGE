"""Hybrid 类 MemoryService - 混合索引存储

Layer: L4 (Middleware)

设计原则：
- 一个 Service 对应一个 Collection（严格 1:1）
- 一份数据 + 多种索引类型（VDB + KV + Graph）
- 支持多路检索融合（weighted / rrf / union）

包含的 Service：
- multi_index: 多索引混合记忆（Mem0 / EmotionalRAG）

Author: SAGE Team
Created: 2025-12-24
"""

from __future__ import annotations

# 注册到 Registry
from sage.middleware.components.sage_mem.memory_service.registry import (
    MemoryServiceRegistry,
)

# 导入所有 Hybrid Service
from .multi_index import MultiIndexMemoryService

# 注册 Hybrid 类 Service
MemoryServiceRegistry.register("hybrid.multi_index", MultiIndexMemoryService)

__all__ = [
    "MultiIndexMemoryService",
]
