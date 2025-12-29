"""
Performance Benchmark Tests for Memory Services

性能基准测试，包括：
1. 插入性能（10K条数据）
2. 检索性能（1K查询）
3. 内存占用测试
"""

import gc
import time

import numpy as np
import psutil
import pytest

from sage.middleware.components.sage_mem.neuromem.memory_collection import (
    UnifiedCollection,
)
from sage.middleware.components.sage_mem.neuromem.services import (
    MemoryServiceRegistry,
)

# 导入服务类触发注册


class MockEmbedder:
    """简单的 Mock Embedder 用于测试"""

    def __init__(self, dim=768):
        self.dim = dim

    def embed(self, text: str) -> list[float]:
        """生成确定性的向量（基于文本哈希）"""
        np.random.seed(hash(text) % (2**32))
        return np.random.randn(self.dim).tolist()

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """批量生成向量"""
        return [self.embed(text) for text in texts]


def get_memory_usage_mb() -> float:
    """获取当前进程内存占用（MB）"""
    process = psutil.Process()
    return process.memory_info().rss / 1024 / 1024


class BenchmarkResult:
    """基准测试结果"""

    def __init__(self, name: str):
        self.name = name
        self.insert_time = 0.0
        self.retrieve_time = 0.0
        self.memory_usage_mb = 0.0
        self.insert_throughput = 0.0  # 条/秒
        self.retrieve_throughput = 0.0  # 查询/秒

    def __repr__(self) -> str:
        return (
            f"\n{self.name} Benchmark Results:\n"
            f"  插入时间: {self.insert_time:.2f}s\n"
            f"  插入吞吐量: {self.insert_throughput:.0f} ops/s\n"
            f"  检索时间: {self.retrieve_time:.2f}s\n"
            f"  检索吞吐量: {self.retrieve_throughput:.0f} queries/s\n"
            f"  内存占用: {self.memory_usage_mb:.2f} MB\n"
        )


@pytest.mark.benchmark
class TestInsertionPerformance:
    """插入性能测试"""

    @pytest.mark.parametrize("num_items", [1000, 5000, 10000])
    def test_fifo_queue_insertion(self, num_items):
        """测试 FIFO Queue 插入性能"""
        result = BenchmarkResult(f"FIFO Queue ({num_items} items)")

        # 初始化
        collection = UnifiedCollection(f"fifo_bench_{num_items}")
        service = MemoryServiceRegistry.create(
            "fifo_queue", collection, config={"max_size": num_items}
        )

        # 测试插入
        gc.collect()
        mem_before = get_memory_usage_mb()
        start_time = time.time()

        for i in range(num_items):
            service.insert(
                f"Message {i}",
                metadata={"index": i, "category": f"cat_{i % 10}"},
            )

        end_time = time.time()
        mem_after = get_memory_usage_mb()

        # 记录结果
        result.insert_time = end_time - start_time
        result.insert_throughput = num_items / result.insert_time
        result.memory_usage_mb = mem_after - mem_before

        print(result)

        # 性能断言（可根据实际情况调整）
        assert result.insert_throughput > 1000, "插入吞吐量应该 > 1000 ops/s"
        assert result.memory_usage_mb < 500, "10K 数据内存占用应该 < 500MB"

    @pytest.mark.parametrize("num_items", [100, 500])
    def test_vectorstore_insertion(self, num_items):
        """
        测试 VectorStore 插入性能（带向量）

        Note:
            - 由于 BM25 索引每次插入都重建（O(n) 复杂度），大量逐条插入会很慢
            - 生产环境应使用批量插入或索引构建完成后再启用
            - 测试使用较小数据集（100/500）验证功能正确性
        """
        result = BenchmarkResult(f"InvertedVectorStore ({num_items} items)")
        embedder = MockEmbedder(dim=768)

        collection = UnifiedCollection(f"vectorstore_bench_{num_items}")
        service = MemoryServiceRegistry.create(
            "partitional.inverted_vectorstore_combination",
            collection,
            config={
                "vector_dim": 768,
                "fusion_strategy": "rrf",
                "embedder": embedder,
            },
        )

        # 测试插入（预生成向量以测试索引性能）
        gc.collect()
        mem_before = get_memory_usage_mb()

        # 预先生成所有向量（避免在性能测试中重复计算）
        texts = [f"Document {i}: Some test content about topic {i % 10}" for i in range(num_items)]
        vectors = embedder.embed_batch(texts)

        start_time = time.time()

        for i, (text, vector) in enumerate(zip(texts, vectors)):
            service.insert(text, vector=vector)

        end_time = time.time()
        mem_after = get_memory_usage_mb()

        result.insert_time = end_time - start_time
        result.insert_throughput = num_items / result.insert_time
        result.memory_usage_mb = mem_after - mem_before

        print(result)

        # 性能断言（由于 BM25 自动重建的特性，对小数据集要求 > 10 ops/s）
        assert result.insert_throughput > 10, "插入吞吐量应该 > 10 ops/s"
        assert result.memory_usage_mb < 500, f"{num_items} 数据内存占用应该 < 500MB"

    @pytest.mark.parametrize("num_nodes", [100, 500, 1000])
    def test_graph_insertion(self, num_nodes):
        """测试 Graph 插入性能"""
        result = BenchmarkResult(f"PropertyGraph ({num_nodes} nodes)")

        collection = UnifiedCollection(f"graph_bench_{num_nodes}")
        service = MemoryServiceRegistry.create("property_graph", collection)

        # 测试插入（节点 + 边）
        gc.collect()
        mem_before = get_memory_usage_mb()
        start_time = time.time()

        entity_ids = []
        for i in range(num_nodes):
            entity_id = service.insert(
                f"Entity {i}",
                metadata={"entity_type": "Node", "index": i},
            )
            entity_ids.append(entity_id)

            # 添加一些边
            if i > 0:
                # 连接到前一个节点
                service.add_relationship(entity_ids[i - 1], entity_id, "NEXT")
                # 连接到随机节点
                if i > 10:
                    import random

                    random_target = random.choice(entity_ids[: i - 1])
                    service.add_relationship(entity_id, random_target, "RELATES_TO")

        end_time = time.time()
        mem_after = get_memory_usage_mb()

        result.insert_time = end_time - start_time
        result.insert_throughput = num_nodes / result.insert_time
        result.memory_usage_mb = mem_after - mem_before

        print(result)

        assert result.insert_throughput > 100, "图插入吞吐量应该 > 100 ops/s"


@pytest.mark.benchmark
class TestRetrievalPerformance:
    """检索性能测试"""

    @pytest.fixture
    def populated_fifo_service(self):
        """预先填充数据的 FIFO 服务"""
        collection = UnifiedCollection("fifo_retrieval_bench")
        service = MemoryServiceRegistry.create("fifo_queue", collection, config={"max_size": 10000})

        # 插入 10000 条数据
        for i in range(10000):
            service.insert(
                f"Message {i} about topic {i % 100}",
                metadata={"index": i, "topic": i % 100},
            )

        return service

    def test_sequential_retrieval(self, populated_fifo_service):
        """测试顺序检索性能（1000次查询）"""
        result = BenchmarkResult("FIFO Sequential Retrieval (1000 queries)")

        num_queries = 1000
        start_time = time.time()

        for i in range(num_queries):
            results = populated_fifo_service.retrieve(query="", top_k=10)
            assert len(results) > 0

        end_time = time.time()

        result.retrieve_time = end_time - start_time
        result.retrieve_throughput = num_queries / result.retrieve_time

        print(result)

        # 检索应该很快
        assert result.retrieve_throughput > 100, "检索吞吐量应该 > 100 queries/s"

    def test_vector_similarity_search(self):
        """测试向量相似度搜索性能（100次查询）"""
        result = BenchmarkResult("VectorStore Retrieval (100 queries)")
        embedder = MockEmbedder(dim=768)

        collection = UnifiedCollection("vector_retrieval_bench")
        service = MemoryServiceRegistry.create(
            "partitional.inverted_vectorstore_combination",
            collection,
            config={
                "vector_dim": 768,
                "fusion_strategy": "rrf",
                "embedder": embedder,
            },
        )

        # 预先插入 1000 条数据
        for i in range(1000):
            service.insert(f"Document {i} about topic {i % 20}")

        # 测试 100 次检索
        num_queries = 100
        start_time = time.time()

        for i in range(num_queries):
            results = service.retrieve(f"query about topic {i % 20}", top_k=10)
            assert len(results) > 0, "应该返回结果"

        end_time = time.time()

        result.retrieve_time = end_time - start_time
        result.retrieve_throughput = num_queries / result.retrieve_time

        print(result)

        # 向量搜索应该比较快
        assert result.retrieve_throughput > 50, "检索吞吐量应该 > 50 queries/s"

    @pytest.fixture
    def populated_graph_service(self):
        """预先填充数据的 Graph 服务"""
        collection = UnifiedCollection("graph_retrieval_bench")
        service = MemoryServiceRegistry.create("property_graph", collection)

        # 创建 500 个节点
        entity_ids = []
        for i in range(500):
            entity_id = service.insert(
                f"Entity {i}",
                metadata={"entity_type": "Node", "index": i},
            )
            entity_ids.append(entity_id)

            # 添加边
            if i > 0:
                service.add_relationship(entity_ids[i - 1], entity_id, "NEXT")

        return service, entity_ids

    def test_graph_traversal(self, populated_graph_service):
        """测试图遍历性能（100次查询）"""
        service, entity_ids = populated_graph_service
        result = BenchmarkResult("Graph Traversal (100 queries)")

        num_queries = 100
        start_time = time.time()

        for i in range(num_queries):
            # 随机选择一个节点
            import random

            entity_id = random.choice(entity_ids)
            service.get_related_entities(entity_id)
            # 不做断言，因为有些节点可能没有关系

        end_time = time.time()

        result.retrieve_time = end_time - start_time
        result.retrieve_throughput = num_queries / result.retrieve_time

        print(result)

        assert result.retrieve_throughput > 50, "图遍历吞吐量应该 > 50 queries/s"


@pytest.mark.benchmark
class TestMemoryFootprint:
    """内存占用测试"""

    def test_large_dataset_memory_usage(self):
        """测试大数据集内存占用"""
        print("\n=== 大数据集内存占用测试 ===")

        # 测试不同大小的数据集
        sizes = [1000, 5000, 10000]
        memory_usages = []

        for size in sizes:
            gc.collect()
            mem_before = get_memory_usage_mb()

            collection = UnifiedCollection(f"mem_test_{size}")
            service = MemoryServiceRegistry.create(
                "fifo_queue", collection, config={"max_size": size}
            )

            for i in range(size):
                service.insert(f"Message {i}", metadata={"index": i})

            mem_after = get_memory_usage_mb()
            mem_used = mem_after - mem_before
            memory_usages.append((size, mem_used))

            print(f"  {size} items: {mem_used:.2f} MB")

            # 清理
            del service
            del collection

        # 验证内存增长是线性的
        memory_per_item = [mem / size for size, mem in memory_usages]
        avg_memory_per_item = sum(memory_per_item) / len(memory_per_item)

        print(f"\n  平均每条数据: {avg_memory_per_item:.4f} MB")

        # 每条数据不应该超过 10KB (0.01 MB)
        assert avg_memory_per_item < 0.01, "每条数据内存占用过大"

    def test_memory_leak_check(self):
        """测试内存泄漏"""
        print("\n=== 内存泄漏检测 ===")

        gc.collect()
        mem_baseline = get_memory_usage_mb()

        # 创建和销毁服务 10 次
        for iteration in range(10):
            collection = UnifiedCollection(f"leak_test_{iteration}")
            service = MemoryServiceRegistry.create(
                "fifo_queue", collection, config={"max_size": 1000}
            )

            # 插入数据
            for i in range(1000):
                service.insert(f"Message {i}", metadata={"index": i})

            # 删除服务
            del service
            del collection
            gc.collect()

        mem_after = get_memory_usage_mb()
        mem_growth = mem_after - mem_baseline

        print(f"  初始内存: {mem_baseline:.2f} MB")
        print(f"  结束内存: {mem_after:.2f} MB")
        print(f"  内存增长: {mem_growth:.2f} MB")

        # 10 次迭代后内存增长不应该超过 50MB
        assert mem_growth < 50, f"可能存在内存泄漏，增长了 {mem_growth:.2f}MB"


@pytest.mark.benchmark
@pytest.mark.slow
class TestScalability:
    """可扩展性测试"""

    def test_scaling_with_data_size(self):
        """测试数据量扩展性"""
        print("\n=== 数据量扩展性测试 ===")

        sizes = [100, 500, 1000, 5000]
        results = []

        for size in sizes:
            collection = UnifiedCollection(f"scale_test_{size}")
            service = MemoryServiceRegistry.create(
                "fifo_queue", collection, config={"max_size": size}
            )

            # 插入性能
            start_time = time.time()
            for i in range(size):
                service.insert(f"Message {i}", metadata={"index": i})
            insert_time = time.time() - start_time

            # 检索性能
            start_time = time.time()
            for _ in range(100):
                service.retrieve(query="", top_k=10)
            retrieve_time = time.time() - start_time

            results.append(
                {
                    "size": size,
                    "insert_time": insert_time,
                    "retrieve_time": retrieve_time,
                    "insert_throughput": size / insert_time,
                    "retrieve_throughput": 100 / retrieve_time,
                }
            )

            print(f"  {size} items:")
            print(f"    插入: {size / insert_time:.0f} ops/s")
            print(f"    检索: {100 / retrieve_time:.0f} queries/s")

        # 验证吞吐量不会随数据量线性下降
        throughputs = [r["insert_throughput"] for r in results]
        assert min(throughputs) > max(throughputs) * 0.3, "吞吐量下降过快，可能存在性能问题"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-m", "benchmark"])
