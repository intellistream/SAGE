"""MemoryService 重构版本 - 纯 Registry 模式

Layer: L4 (Middleware)

设计原则：
1. 移除 Factory 层，采用纯 Registry 模式
2. Service 类自己负责从配置创建实例（通过 from_config）
3. 支持层级命名（如 "partitional.vector_memory"）

三大类：
- Partitional：去中心化存储
  - vector_memory: 向量记忆（FAISS 索引）
  - key_value_memory: 文本记忆（BM25S 索引）
  - short_term_memory: 短期记忆（滑窗+VDB）
  - vector_hash_memory: LSH 哈希记忆

- Hierarchical：有层级结构
  - graph_memory: 图记忆
  - three_tier: 三层记忆（STM/MTM/LTM）
  - two_tier: 两层记忆（Short/Long）

- Hybrid：混合结构
  - multi_index: 多索引混合（VDB+KV+Graph）✅
  - rrf_fusion: RRF 融合检索（待实现）

Usage:
    >>> from sage.middleware.components.sage_mem.memory_service import (
    >>>     MemoryServiceRegistry,
    >>>     BaseMemoryService,
    >>> )
    >>>
    >>> # 获取 Service 类
    >>> service_class = MemoryServiceRegistry.get("partitional.vector_memory")
    >>>
    >>> # 从配置创建 ServiceFactory
    >>> factory = service_class.from_config(service_name, config)
    >>>
    >>> # 在 Pipeline 中注册
    >>> env.register_service_factory(service_name, factory)
"""

from .base_service import BaseMemoryService
from .registry import MemoryServiceRegistry

__all__ = [
    "BaseMemoryService",
    "MemoryServiceRegistry",
]
