"""Partitional 类 MemoryService

无中心化存储，数据分散在不同分区/桶中，无全局索引。

典型结构：
- 哈希桶
- LSH 索引
- 向量索引（FAISS）
- KV 存储

Layer: L4 (Middleware)
"""

from __future__ import annotations

# 导入 Registry 进行注册
from ..registry import MemoryServiceRegistry
from .key_value_memory import KeyValueMemoryService
from .short_term_memory import ShortTermMemoryService
from .vector_hash_memory import VectorHashMemoryService
from .vector_memory import VectorMemoryService

# 注册所有 Partitional Service
MemoryServiceRegistry.register("partitional.short_term_memory", ShortTermMemoryService)
MemoryServiceRegistry.register("partitional.vector_memory", VectorMemoryService)
MemoryServiceRegistry.register("partitional.key_value_memory", KeyValueMemoryService)
MemoryServiceRegistry.register("partitional.vector_hash_memory", VectorHashMemoryService)

__all__ = [
    "ShortTermMemoryService",
    "VectorMemoryService",
    "KeyValueMemoryService",
    "VectorHashMemoryService",
]
