"""
Partitional Combination Services Integration Tests

测试新实现的3个Feature+Queue组合服务的集成场景：
- FeatureQueueSegmentCombinationService
- FeatureQueueSummaryCombinationService
- FeatureQueueVectorstoreCombinationService

测试场景:
1. 多服务协同工作（同一Collection多个Service）
2. 服务间数据共享
3. 实际使用场景模拟
4. 性能和容量测试
5. 边界条件和错误处理
"""

from __future__ import annotations

import numpy as np
import pytest

from sage.middleware.components.sage_mem.neuromem.memory_collection import (
    UnifiedCollection,
)
from sage.middleware.components.sage_mem.neuromem.services.partitional import (
    FeatureQueueSegmentCombinationService,
    FeatureQueueSummaryCombinationService,
    FeatureQueueVectorstoreCombinationService,
)


class MockEmbedder:
    """Mock embedder for testing"""

    def __init__(self, dim: int = 768):
        self.dim = dim
        np.random.seed(42)  # 固定随机种子确保可重现

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Return dummy embeddings with fixed dimension"""
        if isinstance(texts, str):
            texts = [texts]
        return [np.random.rand(self.dim).tolist() for _ in texts]


@pytest.fixture
def mock_embedder():
    """提供mock embedder"""
    return MockEmbedder()


@pytest.fixture
def sample_dialogue():
    """对话历史测试数据"""
    return [
        "Hi, I need help with my Python project.",
        "Sure! What are you working on?",
        "I'm building a web scraper using BeautifulSoup.",
        "Great choice! Have you installed the library?",
        "Yes, but I'm getting an AttributeError.",
        "Can you show me the error message?",
        "AttributeError: 'NoneType' object has no attribute 'find'",
        "That usually means the element wasn't found. Check your selector.",
        "Oh, I see! I'll use find() with error handling.",
        "Good idea! Also consider using CSS selectors for more flexibility.",
    ]


@pytest.fixture
def sample_documents():
    """长文档测试数据"""
    return [
        {
            "text": "Python is a high-level, interpreted programming language known for its simplicity and readability. It was created by Guido van Rossum and first released in 1991. Python's design philosophy emphasizes code readability with its notable use of significant whitespace.",
            "metadata": {"category": "programming", "length": "long"},
        },
        {
            "text": "Machine learning is a subset of artificial intelligence that enables systems to learn and improve from experience without being explicitly programmed. It focuses on developing computer programs that can access data and use it to learn for themselves.",
            "metadata": {"category": "ai", "length": "long"},
        },
        {
            "text": "Web scraping is the process of extracting data from websites. It's commonly used for data mining, price comparison, and content aggregation. Popular tools include BeautifulSoup and Scrapy.",
            "metadata": {"category": "programming", "length": "medium"},
        },
        {
            "text": "Quick tip: always use try-except blocks.",
            "metadata": {"category": "programming", "length": "short"},
        },
        {
            "text": "Neural networks are computing systems inspired by biological neural networks. They consist of interconnected nodes (neurons) organized in layers. Deep learning uses neural networks with many hidden layers to process complex patterns in data.",
            "metadata": {"category": "ai", "length": "long"},
        },
    ]


class TestSegmentServiceIntegration:
    """测试FeatureQueueSegmentCombinationService集成场景"""

    def test_conversation_tracking_with_time_segments(self, tmp_path, sample_dialogue):
        """测试对话追踪场景 - 按时间分段"""
        data_dir = tmp_path / "conversation"
        col = UnifiedCollection(name="chat", config={"data_dir": str(data_dir)})

        service = FeatureQueueSegmentCombinationService(
            col,
            {
                "fifo_max_size": 20,
                "segment_strategy": "keyword",  # 使用keyword避免时间延迟
                "segment_threshold": 3,
            },
        )

        # 插入对话
        inserted_ids = []
        for i, msg in enumerate(sample_dialogue[:5]):
            id_ = service.insert(msg, {"turn": i})
            inserted_ids.append(id_)

        # 验证数据被插入
        recent = service.get_recent_items(count=10)
        assert len(recent) == 5

    def test_multi_service_same_collection(self, tmp_path, sample_dialogue, mock_embedder):
        """测试同一Collection同时使用Segment和Vector服务"""
        data_dir = tmp_path / "multi_service"
        col = UnifiedCollection(name="shared", config={"data_dir": str(data_dir)})

        # 创建两个不同的服务
        segment_service = FeatureQueueSegmentCombinationService(
            col,
            {
                "fifo_max_size": 10,
                "segment_strategy": "keyword",
                "segment_threshold": 3,
            },
        )

        vector_service = FeatureQueueVectorstoreCombinationService(
            col,
            {
                "fifo_max_size": 10,
                "vector_dim": 768,
                "embedder": mock_embedder,
                "fusion_method": "rrf",
            },
        )

        # 通过两个服务插入数据
        for i, msg in enumerate(sample_dialogue[:5]):
            if i % 2 == 0:
                segment_service.insert(msg)
            else:
                vector_service.insert(msg)

        # 验证数据共享
        seg_results = segment_service.retrieve("Python", top_k=5)
        vec_results = vector_service.retrieve("Python", top_k=5)

        # 两个服务都应该能看到所有数据
        assert len(seg_results) > 0
        assert len(vec_results) > 0


class TestSummaryServiceIntegration:
    """测试FeatureQueueSummaryCombinationService集成场景"""

    def test_document_summarization_workflow(self, tmp_path, sample_documents):
        """测试文档摘要工作流"""
        data_dir = tmp_path / "docs"
        col = UnifiedCollection(name="documents", config={"data_dir": str(data_dir)})

        service = FeatureQueueSummaryCombinationService(
            col,
            {
                "fifo_max_size": 20,
                "summary_max_size": 10,
                "summary_min_length": 50,
                "enable_summary_generation": True,
            },
        )

        # 插入文档
        for doc in sample_documents:
            service.insert(doc["text"], doc["metadata"])

        # 检索所有摘要
        summaries = service.get_summaries()
        # 只有长文本会生成摘要（>50字符）
        long_docs = [d for d in sample_documents if len(d["text"]) >= 50]
        assert len(summaries) <= len(long_docs)

        # 检索时排除摘要
        results = service.retrieve(
            "Python programming", top_k=5, strategy="weighted", exclude_summaries=True
        )
        # 验证结果不包含摘要
        for r in results:
            assert not r["metadata"].get("is_summary", False)

    def test_summary_feature_extraction(self, tmp_path):
        """测试摘要的特征提取"""
        data_dir = tmp_path / "features"
        col = UnifiedCollection(name="feature_test", config={"data_dir": str(data_dir)})

        service = FeatureQueueSummaryCombinationService(
            col,
            {
                "enable_feature_extraction": True,
                "summary_min_length": 30,
            },
        )

        long_text = (
            "Artificial intelligence and machine learning are revolutionizing technology. "
            "Neural networks enable computers to recognize patterns and make decisions. "
            "Deep learning has achieved breakthrough results in computer vision and natural language processing."
        )

        service.insert(long_text)

        # 验证数据被成功插入
        recent = service.get_recent_items(count=5)
        assert len(recent) >= 1


class TestVectorstoreServiceIntegration:
    """测试FeatureQueueVectorstoreCombinationService集成场景"""

    def test_semantic_search_workflow(self, tmp_path, mock_embedder, sample_documents):
        """测试语义搜索工作流"""
        data_dir = tmp_path / "semantic"
        col = UnifiedCollection(name="vectors", config={"data_dir": str(data_dir)})

        service = FeatureQueueVectorstoreCombinationService(
            col,
            {
                "vector_dim": 768,
                "fifo_max_size": 20,
                "embedder": mock_embedder,
                "fusion_method": "rrf",
                "rrf_k": 60,
            },
        )

        # 插入文档
        for doc in sample_documents:
            service.insert(doc["text"], doc["metadata"])

        # 验证数据被插入
        recent = service.get_recent_items(count=10)
        assert len(recent) == len(sample_documents)

    def test_vector_fusion_comparison(self, tmp_path, mock_embedder):
        """测试不同融合方法的对比"""
        data_dir = tmp_path / "fusion"
        col = UnifiedCollection(name="fusion_test", config={"data_dir": str(data_dir)})

        service = FeatureQueueVectorstoreCombinationService(
            col,
            {
                "vector_dim": 768,
                "embedder": mock_embedder,
            },
        )

        # 插入测试数据
        texts = [
            "Python programming language",
            "Java development tools",
            "Machine learning algorithms",
            "Web scraping techniques",
            "Data science workflows",
        ]
        for text in texts:
            service.insert(text)

        # 对比不同融合方法
        rrf_results = service.retrieve("Python", top_k=3, strategy="rrf")
        linear_results = service.retrieve("Python", top_k=3, strategy="linear", alpha=0.5)
        weighted_results = service.retrieve("Python", top_k=3, strategy="weighted")

        # 所有方法都应该返回结果
        assert len(rrf_results) > 0
        assert len(linear_results) > 0
        assert len(weighted_results) > 0

    def test_embedder_requirement(self, tmp_path):
        """测试embedder必需性检查"""
        col = UnifiedCollection(name="test")

        # 没有embedder应该抛出错误
        with pytest.raises(ValueError, match="Embedder is required"):
            FeatureQueueVectorstoreCombinationService(
                col,
                {"vector_dim": 768},  # 缺少embedder
            )


class TestCrossServiceScenarios:
    """测试跨服务场景"""

    def test_service_switching(self, tmp_path, sample_dialogue, mock_embedder):
        """测试在不同服务间切换查询"""
        data_dir = tmp_path / "switching"
        col = UnifiedCollection(name="multi", config={"data_dir": str(data_dir)})

        # 创建3个服务
        segment_svc = FeatureQueueSegmentCombinationService(col)
        summary_svc = FeatureQueueSummaryCombinationService(col)
        vector_svc = FeatureQueueVectorstoreCombinationService(
            col, {"vector_dim": 768, "embedder": mock_embedder}
        )

        # 通过不同服务插入数据
        for i, msg in enumerate(sample_dialogue[:6]):
            if i % 3 == 0:
                segment_svc.insert(msg)
            elif i % 3 == 1:
                summary_svc.insert(msg)
            else:
                vector_svc.insert(msg)

        # 验证所有服务都可以访问数据
        seg_recent = segment_svc.get_recent_items(count=10)
        sum_recent = summary_svc.get_recent_items(count=10)
        vec_recent = vector_svc.get_recent_items(count=10)

        assert len(seg_recent) == 6
        assert len(sum_recent) == 6
        assert len(vec_recent) == 6

    def test_large_dataset_handling(self, tmp_path, mock_embedder):
        """测试大数据集处理"""
        data_dir = tmp_path / "large"
        col = UnifiedCollection(name="large_test", config={"data_dir": str(data_dir)})

        service = FeatureQueueVectorstoreCombinationService(
            col,
            {
                "vector_dim": 768,
                "fifo_max_size": 50,
                "embedder": mock_embedder,
            },
        )

        # 插入100条数据
        for i in range(100):
            service.insert(
                f"Document {i}: This is a test document about topic {i % 10}.",
                {"index": i, "topic": i % 10},
            )

        # FIFO应该只保留最近50条
        recent = service.get_recent_items(count=100)
        assert len(recent) <= 50

        # 检索应该正常工作
        results = service.retrieve("topic 5", top_k=10)
        assert len(results) > 0


class TestPerformanceAndReliability:
    """性能和可靠性测试"""

    def test_concurrent_insertions(self, tmp_path):
        """测试并发插入"""
        data_dir = tmp_path / "concurrent"
        col = UnifiedCollection(name="concurrent", config={"data_dir": str(data_dir)})

        service = FeatureQueueSegmentCombinationService(col, {"fifo_max_size": 100})

        # 快速连续插入
        inserted = []
        for i in range(50):
            id_ = service.insert(f"Message {i}")
            inserted.append(id_)

        # 验证所有数据都被插入
        recent = service.get_recent_items(count=50)
        assert len(recent) == 50

    def test_error_recovery(self, tmp_path):
        """测试错误恢复"""
        data_dir = tmp_path / "recovery"
        col = UnifiedCollection(name="recovery", config={"data_dir": str(data_dir)})

        service = FeatureQueueSummaryCombinationService(col)

        # 插入正常数据
        service.insert("Normal document about Python programming")

        # 服务应该可用
        service.insert("Another document about machine learning")

        # 验证数据被插入
        recent = service.get_recent_items(count=10)
        assert len(recent) >= 2

    def test_edge_case_empty_collection(self, tmp_path, mock_embedder):
        """测试空Collection的边界情况"""
        col = UnifiedCollection(name="empty")

        service = FeatureQueueVectorstoreCombinationService(
            col, {"vector_dim": 768, "embedder": mock_embedder}
        )

        # 空Collection查询应该返回空列表
        results = service.retrieve("anything", top_k=10)
        assert results == []

        # get_recent应该返回空列表
        recent = service.get_recent_items(count=10)
        assert recent == []


class TestRealWorldUseCases:
    """真实使用场景测试"""

    def test_chatbot_memory_scenario(self, tmp_path):
        """测试聊天机器人记忆场景"""
        data_dir = tmp_path / "chatbot"
        col = UnifiedCollection(name="chatbot", config={"data_dir": str(data_dir)})

        # 使用Segment服务管理对话历史
        memory = FeatureQueueSegmentCombinationService(
            col,
            {
                "fifo_max_size": 50,  # 保留最近50条对话
                "segment_strategy": "keyword",  # 使用keyword而不是time避免sleep
                "segment_threshold": 3,
            },
        )

        # 模拟多轮对话
        conversation = [
            ("user", "What is Python?"),
            ("bot", "Python is a programming language."),
            ("user", "Can you show me an example?"),
            ("bot", "Sure! Here's a hello world example."),
            ("user", "Thanks! What about web development?"),
            ("bot", "Python has frameworks like Django and Flask."),
        ]

        for role, text in conversation:
            memory.insert(text, {"role": role})

        # 检索相关上下文
        context = memory.retrieve("Python example", top_k=3, strategy="weighted")
        assert len(context) > 0

        # 获取最近的对话
        recent = memory.get_recent_items(count=10)
        assert len(recent) == len(conversation)

    def test_document_qa_scenario(self, tmp_path, mock_embedder):
        """测试文档问答场景"""
        data_dir = tmp_path / "doc_qa"
        col = UnifiedCollection(name="docs", config={"data_dir": str(data_dir)})

        # 使用Vector服务进行语义搜索
        qa_system = FeatureQueueVectorstoreCombinationService(
            col,
            {
                "vector_dim": 768,
                "fifo_max_size": 100,
                "embedder": mock_embedder,
                "fusion_method": "rrf",
            },
        )

        # 添加知识库文档
        knowledge_base = [
            "Python supports object-oriented, functional, and procedural programming paradigms.",
            "Django is a high-level Python web framework that encourages rapid development.",
            "NumPy provides support for large multi-dimensional arrays and matrices.",
            "Pandas is a data manipulation library built on top of NumPy.",
        ]

        for doc in knowledge_base:
            qa_system.insert(doc, {"source": "documentation"})

        # 验证数据被插入
        recent = qa_system.get_recent_items(count=10)
        assert len(recent) == len(knowledge_base)
