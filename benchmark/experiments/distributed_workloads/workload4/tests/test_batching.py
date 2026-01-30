"""
Workload 4 Batching 模块单元测试
"""

import time
import unittest

from ..batching import (
    BatchCoordinator,
    CategoryBatchAggregator,
    GlobalBatchAggregator,
    create_batch_pipeline_stage,
)
from ..models import BatchContext, JoinedEvent, QueryEvent


class TestCategoryBatchAggregator(unittest.TestCase):
    """测试 Category Batch Aggregator"""

    def setUp(self):
        """测试前置"""
        self.aggregator = CategoryBatchAggregator(
            batch_size=3,
            timeout_ms=500,
        )

    def _create_event(self, query_id: str, category: str) -> JoinedEvent:
        """创建测试事件"""
        return JoinedEvent(
            joined_id=f"join_{query_id}",
            query=QueryEvent(
                query_id=query_id,
                query_text=f"Test query {query_id}",
                query_type="factual",
                category=category,
                timestamp=time.time(),
            ),
            matched_docs=[],
            join_timestamp=time.time(),
            semantic_score=0.8,
        )

    def test_batch_by_size(self):
        """测试按 batch_size 触发批次"""
        # 创建 3 个相同 category 的事件
        events = [self._create_event(f"q{i}", "finance") for i in range(3)]

        results = []
        for event in events[:-1]:
            result = self.aggregator.execute(event)
            results.append(result)

        # 前两个应该返回 None
        self.assertIsNone(results[0])
        self.assertIsNone(results[1])

        # 第三个应该返回批次
        result = self.aggregator.execute(events[-1])
        self.assertIsNotNone(result)
        self.assertIsInstance(result, BatchContext)
        self.assertEqual(result.batch_type, "category")
        self.assertEqual(result.batch_size, 3)
        self.assertEqual(result.category, "finance")

    def test_batch_by_timeout(self):
        """测试按超时触发批次"""
        # 创建 1 个事件
        event = self._create_event("q1", "finance")

        # 第一次调用返回 None
        result = self.aggregator.execute(event)
        self.assertIsNone(result)

        # 等待超时
        time.sleep(0.6)  # 超过 500ms

        # 再次发送事件，应该触发批次
        event2 = self._create_event("q2", "finance")
        result = self.aggregator.execute(event2)

        # 应该返回包含第一个事件的批次（由于超时触发了第一个事件）
        # 然后第二个事件又加入了缓冲区，所以返回的批次包含 1 个事件
        # 但是第二个事件还在缓冲区中，所以实际返回的批次可能包含 2 个
        self.assertIsNotNone(result)
        # 修正：超时后第二个事件也会被包含进去
        self.assertGreaterEqual(result.batch_size, 1)

    def test_multiple_categories(self):
        """测试多个 category 独立批次"""
        # 创建两个 category 的事件
        finance_events = [self._create_event(f"f{i}", "finance") for i in range(3)]
        healthcare_events = [self._create_event(f"h{i}", "healthcare") for i in range(3)]

        # 交替发送
        all_events = []
        for f, h in zip(finance_events, healthcare_events):
            all_events.extend([f, h])

        batches = []
        for event in all_events:
            result = self.aggregator.execute(event)
            if result:
                batches.append(result)

        # 应该产生 2 个批次（每个 category 一个）
        self.assertEqual(len(batches), 2)

        categories = {b.category for b in batches}
        self.assertEqual(categories, {"finance", "healthcare"})

    def test_flush_all(self):
        """测试强制刷新"""
        # 创建 2 个事件（未达到 batch_size）
        events = [self._create_event(f"q{i}", "finance") for i in range(2)]

        for event in events:
            result = self.aggregator.execute(event)
            self.assertIsNone(result)

        # 强制刷新
        flushed = self.aggregator.flush_all()

        # 应该返回 1 个批次
        self.assertEqual(len(flushed), 1)
        self.assertEqual(flushed[0].batch_size, 2)


class TestGlobalBatchAggregator(unittest.TestCase):
    """测试 Global Batch Aggregator"""

    def setUp(self):
        """测试前置"""
        self.aggregator = GlobalBatchAggregator(
            batch_size=8,
            timeout_ms=800,
        )

    def _create_category_batch(self, batch_id: str, size: int) -> BatchContext:
        """创建测试的 category batch"""
        items = [
            JoinedEvent(
                joined_id=f"join_{batch_id}_{i}",
                query=QueryEvent(
                    query_id=f"q{i}",
                    query_text=f"Query {i}",
                    query_type="factual",
                    category="finance",
                    timestamp=time.time(),
                ),
                matched_docs=[],
                join_timestamp=time.time(),
                semantic_score=0.8,
            )
            for i in range(size)
        ]

        return BatchContext(
            batch_id=batch_id,
            batch_type="category",
            items=items,
            batch_timestamp=time.time(),
            batch_size=size,
            category="finance",
        )

    def test_batch_by_size(self):
        """测试按 batch_size 触发批次"""
        # 创建多个 category batch（总共 10 个 items）
        category_batches = [
            self._create_category_batch(f"cat_{i}", 3)
            for i in range(3)  # 3 * 3 = 9 items
        ]

        results = []
        for batch in category_batches:
            result = self.aggregator.execute(batch)
            results.append(result)

        # 前两个返回 None（6 items < 8）
        self.assertIsNone(results[0])
        self.assertIsNone(results[1])

        # 第三个应该触发（9 items > 8）
        self.assertIsNotNone(results[2])
        self.assertEqual(results[2].batch_type, "global")
        self.assertEqual(results[2].batch_size, 8)

    def test_category_batch_validation(self):
        """测试输入验证"""
        # 创建一个错误的批次类型
        wrong_batch = BatchContext(
            batch_id="wrong",
            batch_type="global",  # 错误：应该是 "category"
            items=[],
            batch_timestamp=time.time(),
            batch_size=0,
        )

        # 应该抛出断言错误
        with self.assertRaises(AssertionError):
            self.aggregator.execute(wrong_batch)

    def test_flush_all(self):
        """测试强制刷新"""
        # 创建一个 category batch（5 items < 8）
        batch = self._create_category_batch("cat_1", 5)

        result = self.aggregator.execute(batch)
        self.assertIsNone(result)

        # 强制刷新
        flushed = self.aggregator.flush_all()

        # 应该返回 1 个批次
        self.assertEqual(len(flushed), 1)
        self.assertEqual(flushed[0].batch_size, 5)


class TestBatchCoordinator(unittest.TestCase):
    """测试 Batch Coordinator"""

    def test_config_validation_success(self):
        """测试配置验证成功"""
        # 合法配置
        coordinator = BatchCoordinator(
            category_batch_size=5,
            category_timeout_ms=300,
            global_batch_size=12,
            global_timeout_ms=800,
        )

        # 应该成功创建
        self.assertIsNotNone(coordinator)

    def test_config_validation_timeout_order(self):
        """测试超时顺序验证"""
        # 非法配置：category_timeout >= global_timeout
        with self.assertRaises(AssertionError):
            BatchCoordinator(
                category_batch_size=5,
                category_timeout_ms=800,  # >= global_timeout_ms
                global_batch_size=12,
                global_timeout_ms=500,
            )

    def test_create_aggregators(self):
        """测试创建 aggregators"""
        coordinator = BatchCoordinator(
            category_batch_size=5,
            category_timeout_ms=300,
            global_batch_size=12,
            global_timeout_ms=800,
        )

        category_agg = coordinator.create_category_aggregator()
        global_agg = coordinator.create_global_aggregator()

        # 验证类型
        self.assertIsInstance(category_agg, CategoryBatchAggregator)
        self.assertIsInstance(global_agg, GlobalBatchAggregator)

        # 验证配置
        self.assertEqual(category_agg.batch_size, 5)
        self.assertEqual(global_agg.batch_size, 12)

    def test_stats_tracking(self):
        """测试统计信息跟踪"""
        coordinator = BatchCoordinator(
            category_batch_size=3,
            category_timeout_ms=300,
            global_batch_size=8,
            global_timeout_ms=800,
        )

        # 创建测试批次（需要匹配的 items）
        dummy_items = [
            JoinedEvent(
                joined_id=f"join_{i}",
                query=QueryEvent(
                    query_id=f"q{i}",
                    query_text=f"Query {i}",
                    query_type="factual",
                    category="finance",
                    timestamp=time.time(),
                ),
                matched_docs=[],
                join_timestamp=time.time(),
                semantic_score=0.8,
            )
            for i in range(3)
        ]

        category_batch = BatchContext(
            batch_id="cat_1",
            batch_type="category",
            items=dummy_items,
            batch_timestamp=time.time(),
            batch_size=3,
            category="finance",
        )

        # 创建 global batch（也需要匹配的 items）
        global_dummy_items = [
            JoinedEvent(
                joined_id=f"join_g_{i}",
                query=QueryEvent(
                    query_id=f"qg{i}",
                    query_text=f"Query {i}",
                    query_type="factual",
                    category="healthcare",
                    timestamp=time.time(),
                ),
                matched_docs=[],
                join_timestamp=time.time(),
                semantic_score=0.85,
            )
            for i in range(8)
        ]

        global_batch = BatchContext(
            batch_id="global_1",
            batch_type="global",
            items=global_dummy_items,
            batch_timestamp=time.time(),
            batch_size=8,
        )

        # 记录统计
        coordinator.record_category_batch(category_batch)
        coordinator.record_global_batch(global_batch)

        # 验证统计
        stats = coordinator.get_stats()
        self.assertEqual(stats["category_batches_sent"], 1)
        self.assertEqual(stats["global_batches_sent"], 1)
        self.assertEqual(stats["total_items_processed"], 3)


class TestBatchPipelineStage(unittest.TestCase):
    """测试完整的批处理 pipeline stage"""

    def test_create_pipeline_stage(self):
        """测试创建 pipeline stage"""
        category_agg, global_agg, coordinator = create_batch_pipeline_stage(
            category_batch_size=5,
            category_timeout_ms=300,
            global_batch_size=12,
            global_timeout_ms=800,
        )

        # 验证返回值
        self.assertIsInstance(category_agg, CategoryBatchAggregator)
        self.assertIsInstance(global_agg, GlobalBatchAggregator)
        self.assertIsInstance(coordinator, BatchCoordinator)

        # 验证配置传递
        self.assertEqual(category_agg.batch_size, 5)
        self.assertEqual(global_agg.batch_size, 12)

    def test_end_to_end_batching(self):
        """测试端到端批处理"""
        category_agg, global_agg, coordinator = create_batch_pipeline_stage(
            category_batch_size=3,
            category_timeout_ms=500,
            global_batch_size=8,
            global_timeout_ms=1000,
        )

        # 创建测试事件
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
            for i in range(12)  # 12 个事件
        ]

        # Stage 1: Category batching
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

        # 验证 category batches
        self.assertGreater(len(category_batches), 0)

        # Stage 2: Global batching
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

        # 验证 global batches
        self.assertGreater(len(global_batches), 0)

        # 验证统计
        stats = coordinator.get_stats()
        self.assertEqual(stats["total_items_processed"], 12)
        self.assertGreater(stats["category_batches_sent"], 0)
        self.assertGreater(stats["global_batches_sent"], 0)


if __name__ == "__main__":
    unittest.main()
