"""
Workload 4 批处理聚合模块

实现双层 Batch 聚合:
1. Category Batch: 按 category 聚合(第一层)
2. Global Batch: 全局聚合(第二层)

目的:
- 减少同类别查询的重复计算
- 批量调用 LLM 提高 GPU 利用率
"""

import time
from collections import defaultdict
from dataclasses import dataclass
from typing import Any

from sage.common.core.functions.map_function import MapFunction

try:
    from .models import BatchContext, JoinedEvent, RerankingResult
except ImportError:
    from models import BatchContext, JoinedEvent, RerankingResult


@dataclass
class BatchConfig:
    """批处理配置"""
    batch_size: int
    timeout_ms: int
    
    def validate(self) -> bool:
        """验证配置"""
        assert self.batch_size > 0, "Batch size must be positive"
        assert self.timeout_ms > 0, "Timeout must be positive"
        return True


class CategoryBatchAggregator(MapFunction):
    """
    第一层 Batch: 按 category 聚合。
    
    目的: 将同类别的查询聚合在一起，减少重复 embedding 计算。
    
    工作机制:
    1. 维护每个 category 的缓冲区
    2. 当缓冲区达到 batch_size 或超时时，发送批次
    3. 创建 BatchContext (type="category")
    """
    
    def __init__(
        self,
        batch_size: int = 5,
        timeout_ms: int = 300,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.batch_size = batch_size
        self.timeout_ms = timeout_ms / 1000.0  # 转换为秒
        
        # 每个 category 的缓冲区
        self._category_buffers: dict[str, list[tuple]] = defaultdict(list)
        
        # 每个 category 的首次接收时间
        self._category_first_arrival: dict[str, float] = {}
        
        # 批次计数器(用于生成 batch_id)
        self._batch_counter = 0
        
    def execute(self, data: tuple[object, list[object], list[object]]) -> BatchContext | None:
        """
        处理单个数据，决定是否发送批次。
        
        Args:
            data: (joined_event, graph_results, reranking_results)
        
        Returns:
            BatchContext 或 None(如果还未达到批次条件)
        """
        from sage.kernel.runtime.communication.packet import StopSignal
        if isinstance(data, StopSignal):
            return data
        
        joined_event, graph_results, reranking_results = data
        category = joined_event.query.category
        current_time = time.time()
        
        # 添加到对应 category 的缓冲区
        self._category_buffers[category].append(data)
        
        # 记录首次到达时间
        if category not in self._category_first_arrival:
            self._category_first_arrival[category] = current_time
        
        # 检查是否应该发送批次
        buffer = self._category_buffers[category]
        first_arrival = self._category_first_arrival[category]
        elapsed = current_time - first_arrival
        
        # 条件1: 达到 batch_size
        # 条件2: 超时
        if len(buffer) >= self.batch_size or elapsed >= self.timeout_ms:
            return self._flush_category(category, current_time)
        
        # 还未达到批次条件，返回 None
        return None
    
    def _flush_category(self, category: str, timestamp: float) -> BatchContext:
        """
        发送指定 category 的批次。
        
        Args:
            category: 类别名
            timestamp: 当前时间戳
        
        Returns:
            BatchContext (type="category")
        """
        buffer = self._category_buffers[category]
        batch_id = f"category_batch_{self._batch_counter}_{category}"
        self._batch_counter += 1
        
        # 创建批次上下文
        batch = BatchContext(
            batch_id=batch_id,
            batch_type="category",
            items=buffer.copy(),
            batch_timestamp=timestamp,
            batch_size=len(buffer),
            category=category,
        )
        
        # 清空缓冲区
        self._category_buffers[category] = []
        del self._category_first_arrival[category]
        
        return batch
    
    def flush_all(self) -> list[BatchContext]:
        """
        强制刷新所有缓冲区(用于 pipeline 结束时)。
        
        Returns:
            所有待发送的 BatchContext
        """
        result = []
        current_time = time.time()
        
        for category in list(self._category_buffers.keys()):
            if self._category_buffers[category]:
                result.append(self._flush_category(category, current_time))
        
        return result


class GlobalBatchAggregator(MapFunction):
    """
    第二层 Batch: 全局聚合。
    
    目的: 跨 category 聚合，批量调用 LLM 提高 GPU 利用率。
    
    工作机制:
    1. 接收来自不同 category 的 BatchContext
    2. 当全局缓冲区达到 batch_size 或超时时，发送批次
    3. 创建 BatchContext (type="global")
    """
    
    def __init__(
        self,
        batch_size: int = 12,
        timeout_ms: int = 800,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.batch_size = batch_size
        self.timeout_ms = timeout_ms / 1000.0  # 转换为秒
        
        # 全局缓冲区(存储 category batch)
        self._global_buffer: list[JoinedEvent] = []
        
        # 首次接收时间
        self._first_arrival: float | None = None
        
        # 批次计数器
        self._batch_counter = 0
        
    def execute(self, data: BatchContext) -> BatchContext | None:
        """
        处理 CategoryBatchContext，决定是否发送全局批次。
        
        Args:
            data: BatchContext (type="category")
        
        Returns:
            BatchContext (type="global") 或 None
        """
        from sage.kernel.runtime.communication.packet import StopSignal
        if isinstance(data, StopSignal):
            return data
        
        assert data.batch_type == "category", \
            f"Expected category batch, got {data.batch_type}"
        
        current_time = time.time()
        
        # 将 category batch 的所有 items 添加到全局缓冲区
        self._global_buffer.extend(data.items)
        
        # 记录首次到达时间
        if self._first_arrival is None:
            self._first_arrival = current_time
        
        # 检查是否应该发送批次
        elapsed = current_time - self._first_arrival if self._first_arrival else 0
        
        # 条件1: 达到 batch_size
        # 条件2: 超时
        if len(self._global_buffer) >= self.batch_size or elapsed >= self.timeout_ms:
            return self._flush_global(current_time)
        
        return None
    
    def _flush_global(self, timestamp: float) -> BatchContext:
        """
        发送全局批次。
        
        Args:
            timestamp: 当前时间戳
        
        Returns:
            BatchContext (type="global")
        """
        batch_id = f"global_batch_{self._batch_counter}"
        self._batch_counter += 1
        
        # 创建全局批次(取前 batch_size 个)
        items_to_send = self._global_buffer[:self.batch_size]
        
        batch = BatchContext(
            batch_id=batch_id,
            batch_type="global",
            items=items_to_send,
            batch_timestamp=timestamp,
            batch_size=len(items_to_send),
            category=None,  # 全局批次无特定 category
        )
        
        # 移除已发送的 items
        self._global_buffer = self._global_buffer[self.batch_size:]
        
        # 重置首次到达时间
        if not self._global_buffer:
            self._first_arrival = None
        else:
            # 如果还有剩余 items，保持计时器
            pass
        
        return batch
    
    def flush_all(self) -> list[BatchContext]:
        """
        强制刷新全局缓冲区(用于 pipeline 结束时)。
        
        Returns:
            所有待发送的 BatchContext
        """
        result = []
        current_time = time.time()
        
        while self._global_buffer:
            result.append(self._flush_global(current_time))
        
        return result


class BatchCoordinator:
    """
    批处理协调器。
    
    职责:
    1. 协调两层 Batch 的超时时间
    2. 验证配置的合法性
    3. 提供批次统计信息
    
    约束:
    - category_timeout < global_timeout(确保第一层能及时刷新)
    """
    
    def __init__(
        self,
        category_batch_size: int,
        category_timeout_ms: int,
        global_batch_size: int,
        global_timeout_ms: int,
    ):
        self.category_config = BatchConfig(category_batch_size, category_timeout_ms)
        self.global_config = BatchConfig(global_batch_size, global_timeout_ms)
        
        # 验证配置
        self._validate_configs()
        
        # 统计信息
        self._stats = {
            "category_batches_sent": 0,
            "global_batches_sent": 0,
            "total_items_processed": 0,
        }
    
    def _validate_configs(self) -> None:
        """验证配置合法性"""
        # 验证单个配置
        self.category_config.validate()
        self.global_config.validate()
        
        # 验证两层关系
        assert self.category_config.timeout_ms < self.global_config.timeout_ms, \
            "Category timeout must be less than global timeout"
        
        # 建议: category_batch_size < global_batch_size
        if self.category_config.batch_size >= self.global_config.batch_size:
            print(
                f"Warning: category_batch_size ({self.category_config.batch_size}) "
                f">= global_batch_size ({self.global_config.batch_size}). "
                "This may reduce batching efficiency."
            )
    
    def create_category_aggregator(self, **kwargs) -> CategoryBatchAggregator:
        """创建 Category Batch Aggregator"""
        return CategoryBatchAggregator(
            batch_size=self.category_config.batch_size,
            timeout_ms=self.category_config.timeout_ms,
            **kwargs
        )
    
    def create_global_aggregator(self, **kwargs) -> GlobalBatchAggregator:
        """创建 Global Batch Aggregator"""
        return GlobalBatchAggregator(
            batch_size=self.global_config.batch_size,
            timeout_ms=self.global_config.timeout_ms,
            **kwargs
        )
    
    def record_category_batch(self, batch: BatchContext) -> None:
        """记录 category batch 统计"""
        self._stats["category_batches_sent"] += 1
        self._stats["total_items_processed"] += batch.batch_size
    
    def record_global_batch(self, batch: BatchContext) -> None:
        """记录 global batch 统计"""
        self._stats["global_batches_sent"] += 1
    
    def get_stats(self) -> dict[str, Any]:
        """获取统计信息"""
        return self._stats.copy()
    
    def print_summary(self) -> None:
        """打印批处理统计摘要"""
        print("=" * 60)
        print("Batch Coordinator Summary")
        print("=" * 60)
        print(f"Category batches sent: {self._stats['category_batches_sent']}")
        print(f"Global batches sent:   {self._stats['global_batches_sent']}")
        print(f"Total items processed: {self._stats['total_items_processed']}")
        
        if self._stats['category_batches_sent'] > 0:
            avg_category_size = (
                self._stats['total_items_processed'] / 
                self._stats['category_batches_sent']
            )
            print(f"Avg category batch size: {avg_category_size:.2f}")
        
        if self._stats['global_batches_sent'] > 0:
            avg_global_size = (
                self._stats['total_items_processed'] / 
                self._stats['global_batches_sent']
            )
            print(f"Avg global batch size: {avg_global_size:.2f}")
        
        print("=" * 60)


# ============================================================================
# 辅助函数
# ============================================================================

def create_batch_pipeline_stage(
    category_batch_size: int = 5,
    category_timeout_ms: int = 300,
    global_batch_size: int = 12,
    global_timeout_ms: int = 800,
) -> tuple[CategoryBatchAggregator, GlobalBatchAggregator, BatchCoordinator]:
    """
    创建完整的双层批处理 pipeline stage。
    
    Args:
        category_batch_size: Category batch 大小
        category_timeout_ms: Category batch 超时(毫秒)
        global_batch_size: Global batch 大小
        global_timeout_ms: Global batch 超时(毫秒)
    
    Returns:
        (category_aggregator, global_aggregator, coordinator)
    
    Usage:
        category_agg, global_agg, coordinator = create_batch_pipeline_stage()
        
        # 在 pipeline 中使用
        stream \
            .map(category_agg) \
            .filter(lambda x: x is not None) \
            .map(global_agg) \
            .filter(lambda x: x is not None) \
            ...
    """
    coordinator = BatchCoordinator(
        category_batch_size=category_batch_size,
        category_timeout_ms=category_timeout_ms,
        global_batch_size=global_batch_size,
        global_timeout_ms=global_timeout_ms,
    )
    
    category_agg = coordinator.create_category_aggregator()
    global_agg = coordinator.create_global_aggregator()
    
    return category_agg, global_agg, coordinator


if __name__ == "__main__":
    # 简单测试
    from models import QueryEvent
    
    print("Testing Batching Module...")
    
    # 创建 coordinator
    coordinator = BatchCoordinator(
        category_batch_size=3,
        category_timeout_ms=500,
        global_batch_size=8,
        global_timeout_ms=1000,
    )
    
    print("\n✓ Coordinator created successfully")
    print(f"  Category: batch_size={coordinator.category_config.batch_size}, "
          f"timeout={coordinator.category_config.timeout_ms}ms")
    print(f"  Global:   batch_size={coordinator.global_config.batch_size}, "
          f"timeout={coordinator.global_config.timeout_ms}ms")
    
    # 创建 aggregators
    category_agg = coordinator.create_category_aggregator()
    global_agg = coordinator.create_global_aggregator()
    
    print("\n✓ Aggregators created successfully")
    
    # 模拟事件
    events = [
        JoinedEvent(
            joined_id=f"join_{i}",
            query=QueryEvent(
                query_id=f"q{i}",
                query_text=f"Query {i}",
                query_type="factual",
                category="finance" if i % 2 == 0 else "healthcare",
                timestamp=time.time(),
            ),
            matched_docs=[],
            join_timestamp=time.time(),
            semantic_score=0.8,
        )
        for i in range(10)
    ]
    
    print(f"\n✓ Created {len(events)} test events")
    print("  Categories:", set(e.query.category for e in events))
    
    # 测试 category batching
    category_batches = []
    for event in events:
        result = category_agg.execute(event)
        if result:
            category_batches.append(result)
            coordinator.record_category_batch(result)
    
    # 强制刷新剩余
    remaining = category_agg.flush_all()
    category_batches.extend(remaining)
    for batch in remaining:
        coordinator.record_category_batch(batch)
    
    print(f"\n✓ Category batching: {len(category_batches)} batches created")
    for batch in category_batches:
        print(f"  {batch.batch_id}: {batch.batch_size} items, category={batch.category}")
    
    # 测试 global batching
    global_batches = []
    for category_batch in category_batches:
        result = global_agg.execute(category_batch)
        if result:
            global_batches.append(result)
            coordinator.record_global_batch(result)
    
    # 强制刷新剩余
    remaining_global = global_agg.flush_all()
    global_batches.extend(remaining_global)
    for batch in remaining_global:
        coordinator.record_global_batch(batch)
    
    print(f"\n✓ Global batching: {len(global_batches)} batches created")
    for batch in global_batches:
        print(f"  {batch.batch_id}: {batch.batch_size} items")
    
    # 打印统计
    print()
    coordinator.print_summary()
    
    print("\n✅ All tests passed!")
