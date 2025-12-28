"""
================================================================================
MemoryRetrieval - 记忆检索算子（重构后）
================================================================================

[架构定位]
Pipeline: PreInsert → MemoryInsert → PostInsert → PreRetrieval → MemoryRetrieval(当前) → PostRetrieval
前驱: PreRetrieval（负责查询预处理，生成 query_embedding）
后继: PostRetrieval（检索后处理，如重排序、过滤、增强）

[核心职责]
纯透传模式：调用记忆服务的 retrieve 方法，返回原始检索结果

[输入数据结构] (由 PreRetrieval 生成)
data = {
    "question": str,                    # 必须：查询问题
    "query_embedding": list[float],     # 可选：查询向量（由 PreRetrieval 生成）
    "metadata": dict,                   # 可选：元数据
    "retrieve_mode": str,               # 检索模式: "passive" | "active" | ...
    "retrieve_params": dict,            # 检索参数（服务特定）
    ...其他透传字段...
}

[输出数据结构]
data（原样透传）+ memory_data + retrieval_stats = {
    "memory_data": list[dict],          # 检索到的原始记忆数据
    "retrieval_stats": {                # 检索统计
        "retrieved": int,               # 检索数量
        "time_ms": float,               # 检索耗时（毫秒）
        "service_name": str,            # 服务名称
    }
}

[设计原则]
1. 单一职责：只负责调用服务的 retrieve 方法，不做结果处理
2. 纯透传：PreRetrieval 已统一设置查询参数，MemoryRetrieval 直接使用
3. 性能监控：记录检索耗时，供性能分析使用
4. 错误容忍：提供超时控制和重试机制

[T5 重构目标]
✅ 简化为纯透传层（< 80 行）
✅ 统一的性能监控
✅ 结构化日志输出
✅ 支持超时控制
"""

from __future__ import annotations

import time
from dataclasses import asdict, dataclass
from typing import Any

from sage.common.core import MapFunction


@dataclass
class RetrievalStats:
    """检索统计"""

    retrieved: int  # 检索数量
    time_ms: float  # 检索耗时（毫秒）
    service_name: str  # 服务名称


class MemoryRetrieval(MapFunction):
    """记忆检索算子（重构后）- 纯透传模式

    职责：
    1. 调用记忆服务的 retrieve 方法
    2. 统计检索性能
    3. 透传结果给 PostRetrieval
    """

    def __init__(self, config=None):
        """初始化 MemoryRetrieval

        Args:
            config: RuntimeConfig 对象
        """
        super().__init__()
        self.config = config
        self.service_name = config.get("services.register_memory_service", "short_term_memory")
        self.verbose = config.get("runtime.memory_test_verbose", True)

        # 检索参数（从服务配置读取）
        service_cfg = f"services.{self.service_name}"
        self.retrieval_top_k = config.get(f"{service_cfg}.retrieval_top_k", 10)

    def execute(self, data: dict[str, Any]) -> dict[str, Any]:
        """执行记忆检索

        Args:
            data: 由 PreRetrieval 输出的数据，包含查询参数

        Returns:
            原始数据 + memory_data + retrieval_stats
        """
        start_time = time.perf_counter()
        start = time.time()

        # 1. 提取查询参数
        query = data.get("question")
        vector = data.get("query_embedding")
        metadata = data.get("metadata", {})
        # Note: retrieve_mode and retrieve_params are from PreRetrieval but not used by ShortTermMemoryService
        # They can be used by future service implementations if needed

        # 2. 调用服务检索
        results = self.call_service(
            self.service_name,
            method="retrieve",
            query=query,
            vector=vector,
            metadata=metadata,
            top_k=self.retrieval_top_k,
            timeout=60.0,
        )

        # 3. 统计性能
        elapsed = (time.time() - start) * 1000
        stats = RetrievalStats(
            retrieved=len(results) if results else 0,
            time_ms=elapsed,
            service_name=self.service_name,
        )

        # 4. 添加结果和统计
        data["memory_data"] = results
        data["retrieval_stats"] = asdict(stats)

        # 5. 日志输出
        if self.verbose:
            self.logger.info(f"Retrieved {stats.retrieved} items in {stats.time_ms:.2f}ms")

        # 6. 记录阶段耗时
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        data.setdefault("stage_timings", {})["memory_retrieval_ms"] = elapsed_ms

        return data
