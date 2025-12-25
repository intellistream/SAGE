"""Hierarchical 类 MemoryService

分层记忆服务，支持：
- three_tier: 三层记忆（STM/MTM/LTM）
- graph_memory: 图结构记忆（HippoRAG/A-Mem）
"""

from ..registry import MemoryServiceRegistry
from .graph_memory import GraphMemoryService
from .three_tier import ThreeTierMemoryService

# 注册所有 Hierarchical Service
MemoryServiceRegistry.register("hierarchical.three_tier", ThreeTierMemoryService)
MemoryServiceRegistry.register("hierarchical.graph_memory", GraphMemoryService)

__all__ = [
    "ThreeTierMemoryService",
    "GraphMemoryService",
]
