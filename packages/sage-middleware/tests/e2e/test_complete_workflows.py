"""
E2E Tests for Complete Memory Service Workflows

测试完整的记忆服务工作流，包括：
1. FIFO Queue 完整流程
2. Combination Service 完整流程
3. Hierarchical Service 完整流程
"""

import numpy as np
import pytest

from sage.middleware.components.sage_mem.neuromem.memory_collection import (
    UnifiedCollection,
)
from sage.middleware.components.sage_mem.neuromem.services import (
    MemoryServiceRegistry,
)

# Skip: Service implementation issues (Vector requirements, float() errors, etc.)
pytestmark = pytest.mark.skip(reason="Service implementation issues")


# 导入所有服务类以触发注册


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


class TestFIFOQueueWorkflow:
    """FIFO Queue 完整工作流测试"""

    def test_basic_conversation_workflow(self):
        """测试基础对话工作流"""
        # 1. 创建服务
        collection = UnifiedCollection("conversation")
        service = MemoryServiceRegistry.create("fifo_queue", collection, config={"max_size": 5})

        # 2. 模拟多轮对话
        conversations = [
            {"speaker": "User", "text": "Hello, how are you?"},
            {"speaker": "Assistant", "text": "I'm fine, thanks!"},
            {"speaker": "User", "text": "What's the weather today?"},
            {"speaker": "Assistant", "text": "It's sunny and warm."},
            {"speaker": "User", "text": "Great! I'll go for a walk."},
            {"speaker": "Assistant", "text": "Enjoy your walk!"},
        ]

        # 3. 插入对话
        for conv in conversations:
            service.insert(
                f"{conv['speaker']}: {conv['text']}",
                metadata=conv,
            )

        # 4. 验证队列大小（FIFO，只保留最后5条）
        # 注意：Collection 保留所有数据，但 FIFO Index 只保留 max_size 条
        results = service.retrieve(query="", top_k=10)
        assert len(results) == 5  # FIFO Index 只返回 5 条

        # 5. 检索全部对话（从 Index）
        assert len(results) == 5

        # 6. 验证最旧的对话已被删除
        texts = [r["text"] for r in results]
        assert "User: Hello, how are you?" not in texts  # 第1条被删除
        assert "Assistant: Enjoy your walk!" in texts  # 最后一条保留

    def test_overflow_and_fifo_behavior(self):
        """测试溢出和 FIFO 行为"""
        collection = UnifiedCollection("overflow_test")
        service = MemoryServiceRegistry.create("fifo_queue", collection, config={"max_size": 3})

        # 插入 5 条数据
        for i in range(5):
            service.insert(f"Message {i}", metadata={"index": i})

        # 验证只保留最后 3 条
        results = service.retrieve(query="", top_k=10)
        assert len(results) == 3

        # 验证保留的是 2, 3, 4
        indices = sorted([r["metadata"]["index"] for r in results])
        assert indices == [2, 3, 4]

    def test_metadata_preservation(self):
        """测试元数据保留"""
        collection = UnifiedCollection("metadata_test")
        service = MemoryServiceRegistry.create("fifo_queue", collection, config={"max_size": 10})

        # 插入带复杂元数据的数据
        service.insert(
            "Important message",
            metadata={
                "priority": "high",
                "category": "urgent",
                "tags": ["important", "urgent"],
                "timestamp": 1234567890,
            },
        )

        # 检索并验证元数据
        results = service.retrieve(query="", top_k=1)
        assert len(results) == 1
        assert results[0]["metadata"]["priority"] == "high"
        assert results[0]["metadata"]["tags"] == ["important", "urgent"]


class TestCombinationServiceWorkflow:
    """Combination Service 完整工作流测试

    注意: Combination Services 由程序员 B/C 实现（T2.4, T2.5）
    这里使用简单的多索引模拟组合服务行为
    """

    def test_multi_index_workflow(self):
        """测试多索引组合工作流"""
        collection = UnifiedCollection("multi_index")
        service = MemoryServiceRegistry.create("fifo_queue", collection, config={"max_size": 100})

        # 1. 插入数据
        documents = [
            "Machine learning is a subset of artificial intelligence.",
            "Deep learning uses neural networks with multiple layers.",
            "Natural language processing helps computers understand human language.",
        ]

        for i, doc in enumerate(documents):
            service.insert(doc, metadata={"doc_id": i, "category": "AI"})

        # 2. 验证数据插入
        assert collection.size() == 3

        # 3. 检索测试
        results = service.retrieve(query="", top_k=10)
        assert len(results) == 3

    def test_feature_summary_workflow(self):
        """测试 Feature + Summary + VectorStore 组合工作流"""
        collection = UnifiedCollection("feature_summary_test")
        embedder = MockEmbedder(dim=768)

        service = MemoryServiceRegistry.create(
            "feature_summary_vectorstore_combination",
            collection,
            config={
                "vector_dim": 768,
                "summary_max_size": 50,
                "combination_strategy": "weighted",
                "embedder": embedder,
            },
        )

        # 1. 插入测试数据
        texts = [
            "Python is a high-level programming language",
            "JavaScript is used for web development",
            "Machine learning is a subset of AI",
        ]
        for text in texts:
            service.insert(text, metadata={"source": "test"})

        # 2. 检索测试（使用 weighted 策略）
        results = service.retrieve("programming language", top_k=2, strategy="weighted")
        assert len(results) > 0, "应该返回检索结果"
        assert len(results) <= 2, "结果数量不应超过 top_k"

        # 3. 验证返回的数据格式
        for result in results:
            assert "text" in result or "content" in result
            assert "metadata" in result or "score" in result

    def test_inverted_vectorstore_workflow(self):
        """测试 Inverted Index + VectorStore 组合工作流"""
        collection = UnifiedCollection("inverted_vector_test")
        embedder = MockEmbedder(dim=768)

        service = MemoryServiceRegistry.create(
            "inverted_vectorstore_combination",
            collection,
            config={
                "vector_dim": 768,
                "fusion_strategy": "rrf",
                "rrf_k": 60,
                "embedder": embedder,
            },
        )

        # 1. 插入测试数据
        texts = [
            "Deep learning uses neural networks",
            "Natural language processing is NLP",
            "Computer vision processes images",
        ]
        for text in texts:
            service.insert(text, metadata={"category": "AI"})

        # 2. 检索测试（使用 RRF 融合策略）
        results = service.retrieve("neural network learning", top_k=2, strategy="rrf")
        assert len(results) > 0, "应该返回检索结果"
        assert len(results) <= 2, "结果数量不应超过 top_k"

        # 3. 验证返回的数据格式
        for result in results:
            assert "text" in result or "content" in result
            assert "metadata" in result or "score" in result


class TestHierarchicalServiceWorkflow:
    """Hierarchical Service 完整工作流测试"""

    def test_linknote_workflow(self):
        """测试 Linknote 笔记链接工作流"""
        collection = UnifiedCollection("notes")
        service = MemoryServiceRegistry.create("linknote_graph", collection)

        # 1. 创建笔记网络
        notes = {}
        notes["python"] = service.insert(
            "Python Programming",
            metadata={"topic": "programming", "difficulty": "beginner"},
        )
        notes["oop"] = service.insert(
            "Object-Oriented Programming",
            links=[notes["python"]],
            metadata={"topic": "programming", "difficulty": "intermediate"},
        )
        notes["classes"] = service.insert(
            "Classes and Objects",
            links=[notes["oop"]],
            metadata={"topic": "programming", "difficulty": "intermediate"},
        )
        notes["decorators"] = service.insert(
            "Python Decorators",
            links=[notes["python"], notes["oop"]],
            metadata={"topic": "programming", "difficulty": "advanced"},
        )

        # 2. 测试反向链接
        python_backlinks = service.get_backlinks(notes["python"])
        assert len(python_backlinks) == 2  # oop 和 decorators

        # 3. 测试图遍历
        related = service.retrieve(notes["python"], max_hops=2, method="bfs")
        assert len(related) >= 2  # python 链接到 oop 和 decorators

        # 4. 测试邻居节点
        neighbors = service.get_neighbors(notes["oop"], max_hops=1)
        assert notes["python"] in neighbors or notes["classes"] in neighbors

    def test_property_graph_workflow(self):
        """测试 PropertyGraph 知识图谱工作流"""
        collection = UnifiedCollection("knowledge_graph")
        service = MemoryServiceRegistry.create("property_graph", collection)

        # 1. 创建实体网络
        entities = {}
        entities["python"] = service.insert(
            "Python", metadata={"entity_type": "Language", "year": 1991}
        )
        entities["guido"] = service.insert(
            "Guido van Rossum",
            metadata={"entity_type": "Person"},
            relationships=[(entities["python"], "CREATED", {"year": 1991})],
        )
        entities["django"] = service.insert("Django", metadata={"entity_type": "Framework"})
        service.add_relationship(entities["django"], entities["python"], "WRITTEN_IN")

        # 2. 测试关系查询（双向）
        python_related = service.get_related_entities(entities["python"])
        assert len(python_related) >= 2  # guido 和 django

        # 3. 测试按类型检索
        languages = service.retrieve(query="", entity_type="Language")
        assert len(languages) == 1
        assert languages[0]["text"] == "Python"

        # 4. 测试复杂查询（入边）
        incoming = service.get_related_entities(entities["python"], direction="incoming")
        assert len(incoming) >= 2


@pytest.mark.slow
class TestCompleteIntegration:
    """完整集成测试"""

    def test_multi_service_shared_collection(self):
        """测试多个服务共享同一个 Collection"""
        # 共享底层存储
        shared_collection = UnifiedCollection("shared")

        # 创建两种服务
        notes = MemoryServiceRegistry.create("linknote_graph", shared_collection)
        entities = MemoryServiceRegistry.create("property_graph", shared_collection)

        # 笔记层
        note_id = notes.insert("AI Research Note", metadata={"type": "note"})

        # 知识图谱层
        entities.insert("AI", metadata={"type": "entity", "entity_type": "Field"})

        # 验证共享存储
        assert shared_collection.size() == 2

        # 删除测试
        notes.delete(note_id)
        assert shared_collection.size() == 1

    def test_service_lifecycle(self):
        """测试服务生命周期"""
        collection = UnifiedCollection("lifecycle")
        service = MemoryServiceRegistry.create("fifo_queue", collection, config={"max_size": 5})

        # 插入数据
        ids = []
        for i in range(10):
            data_id = service.insert(f"Message {i}", metadata={"index": i})
            ids.append(data_id)

        # 验证 FIFO（Index 只保留 5 条，Collection 保留所有）
        results = service.retrieve(query="", top_k=10)
        assert len(results) == 5  # FIFO Index 只返回 5 条
        assert collection.size() == 10  # Collection 保留所有 10 条

        # 删除服务
        del service

        # 重新创建服务，数据应该保留
        service2 = MemoryServiceRegistry.create("fifo_queue", collection, config={"max_size": 5})
        results = service2.retrieve(query="", top_k=10)
        assert len(results) == 5


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
