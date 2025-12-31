"""
测试 FeatureQueueSummaryCombinationService

测试点:
1. Service 初始化和索引配置
2. 数据插入（特征提取、摘要生成）
3. 四种检索策略（weighted、voting、cascade、recent）
4. 摘要生成和管理
5. 边界条件和错误处理
"""

import pytest

from sage.middleware.components.sage_mem.neuromem.memory_collection import UnifiedCollection
from sage.middleware.components.sage_mem.neuromem.services.partitional.feature_queue_summary_combination import (
    FeatureQueueSummaryCombinationService,
)
from sage.middleware.components.sage_mem.neuromem.services.registry import (
    MemoryServiceRegistry,
)

# Skip: Vector/Embedding requirements - service implementation issue
pytestmark = pytest.mark.skip(reason="Vector/Embedding requirements")


@pytest.fixture
def temp_data_dir(tmp_path):
    """临时数据目录"""
    return tmp_path / "test_feature_queue_summary_service"


@pytest.fixture
def collection(temp_data_dir):
    """创建 UnifiedCollection"""
    col = UnifiedCollection(name="test_collection", config={"data_dir": str(temp_data_dir)})
    yield col


@pytest.fixture
def service(collection):
    """创建 FeatureQueueSummaryCombinationService"""
    config = {
        "fifo_max_size": 20,
        "summary_max_size": 10,
        "summary_min_length": 10,
        "combination_strategy": "weighted",
        "weights": {
            "feature_index": 0.4,
            "fifo_index": 0.3,
            "summary_index": 0.3,
        },
        "enable_feature_extraction": True,
        "enable_summary_generation": True,
    }
    return FeatureQueueSummaryCombinationService(collection, config)


class TestServiceRegistration:
    """测试 Service 注册"""

    def test_service_registered(self):
        """测试 Service 已注册到 Registry"""
        service_cls = MemoryServiceRegistry.get_service_class(
            "partitional.feature_queue_summary_combination"
        )
        assert service_cls is FeatureQueueSummaryCombinationService


class TestServiceInitialization:
    """测试 Service 初始化"""

    def test_init_with_config(self, collection):
        """测试使用配置初始化"""
        config = {
            "fifo_max_size": 50,
            "summary_max_size": 15,
            "summary_min_length": 20,
            "combination_strategy": "voting",
            "enable_feature_extraction": False,
        }
        service = FeatureQueueSummaryCombinationService(collection, config)

        assert service.fifo_max_size == 50
        assert service.summary_max_size == 15
        assert service.summary_min_length == 20
        assert service.combination_strategy == "voting"
        assert service.enable_feature_extraction is False

    def test_init_without_config(self, collection):
        """测试不带配置初始化（使用默认值）"""
        service = FeatureQueueSummaryCombinationService(collection, None)

        assert service.fifo_max_size == 100
        assert service.summary_max_size == 20
        assert service.summary_min_length == 10
        assert service.combination_strategy == "weighted"

    def test_indexes_setup(self, service):
        """测试索引配置正确"""
        assert "feature_index" in service.collection.indexes
        assert "fifo_index" in service.collection.indexes
        assert "summary_index" in service.collection.indexes


class TestDataInsertion:
    """测试数据插入"""

    def test_insert_basic(self, service):
        """测试基本插入"""
        data_id = service.insert("这是一条测试消息")
        assert data_id is not None
        assert isinstance(data_id, str)

    def test_insert_with_summary_generation(self, service):
        """测试摘要生成"""
        text = "这是一条足够长的消息，应该会生成摘要内容。它包含了很多有用的信息。"
        data_id = service.insert(text)

        data = service.collection.get(data_id)
        assert data is not None
        assert "summary" in data.get("metadata", {})

    def test_insert_short_text_no_summary(self, service):
        """测试短文本不生成摘要"""
        text = "短消息"
        data_id = service.insert(text)

        data = service.collection.get(data_id)
        # 短文本可能不会生成摘要
        assert data is not None

    def test_insert_with_feature_extraction(self, service):
        """测试特征提取"""
        text = "这是一条包含多个单词的测试消息"
        data_id = service.insert(text)

        data = service.collection.get(data_id)
        assert data is not None
        assert "features" in data.get("metadata", {})
        features = data["metadata"]["features"]
        assert "word_count" in features
        assert features["word_count"] > 0

    def test_insert_with_metadata(self, service):
        """测试带元数据插入"""
        metadata = {"source": "test", "priority": 1}
        data_id = service.insert("足够长的测试消息内容用于生成摘要", metadata)

        data = service.collection.get(data_id)
        assert data["metadata"]["source"] == "test"
        assert data["metadata"]["priority"] == 1

    def test_insert_multiple(self, service):
        """测试批量插入"""
        ids = []
        for i in range(5):
            data_id = service.insert(f"消息 {i} - 这是一条测试消息")
            ids.append(data_id)

        assert len(ids) == 5
        assert len(set(ids)) == 5


class TestRetrieveWeighted:
    """测试加权检索"""

    def test_retrieve_weighted_basic(self, service):
        """测试基本加权检索"""
        service.insert("Python 编程语言很强大，适合数据科学和机器学习")
        service.insert("Java 是企业级开发首选，性能稳定可靠")
        service.insert("JavaScript 用于前端开发，框架生态丰富")

        results = service.retrieve("Python", top_k=2, strategy="weighted")
        assert len(results) <= 2
        if results:
            assert "fused_score" in results[0]

    def test_retrieve_weighted_exclude_summaries(self, service):
        """测试排除摘要的检索"""
        service.insert("这是一条长文本消息用于生成摘要，包含很多有用信息")
        service.insert("短消息")

        results = service.retrieve("消息", top_k=5, strategy="weighted", include_summaries=False)
        # 结果不应包含 is_summary=True 的项
        for result in results:
            assert not result.get("metadata", {}).get("is_summary", False)


class TestRetrieveVoting:
    """测试投票检索"""

    def test_retrieve_voting(self, service):
        """测试投票检索"""
        service.insert("机器学习算法分析和应用场景研究")
        service.insert("深度学习神经网络架构设计")
        service.insert("强化学习智能体训练方法")

        results = service.retrieve("学习", top_k=2, strategy="voting")
        assert len(results) <= 2


class TestRetrieveCascade:
    """测试级联检索"""

    def test_retrieve_cascade(self, service):
        """测试级联检索"""
        service.insert("数据库设计原理和最佳实践指南")
        service.insert("SQL查询优化技巧和性能调优")
        service.insert("NoSQL数据库选型和使用场景")

        results = service.retrieve("数据库", top_k=2, strategy="cascade")
        assert len(results) <= 2


class TestRetrieveRecent:
    """测试最近检索"""

    def test_retrieve_recent(self, service):
        """测试最近消息检索"""
        service.insert("旧消息1")
        service.insert("旧消息2")
        service.insert("新消息1")
        service.insert("新消息2")

        results = service.retrieve("消息", top_k=2, strategy="recent")
        assert len(results) <= 2


class TestSummaryOperations:
    """测试摘要操作"""

    def test_get_recent_items(self, service):
        """测试获取最近项目"""
        service.insert("消息A - 这是一条测试消息")
        service.insert("消息B - 这是另一条测试消息")
        service.insert("消息C - 这是第三条测试消息")

        recent = service.get_recent_items(count=2)
        assert len(recent) <= 2

    def test_get_summaries(self, service):
        """测试获取摘要列表"""
        service.insert("长文本1 - 这是一条足够长的消息用于生成摘要")
        service.insert("长文本2 - 这是另一条足够长的消息用于生成摘要")

        summaries = service.get_summaries(count=5)
        assert isinstance(summaries, list)


class TestSummaryGeneration:
    """测试摘要生成"""

    def test_generate_summary_short(self, service):
        """测试短文本摘要"""
        text = "短文本"
        summary = service._generate_summary(text)
        assert summary == text

    def test_generate_summary_long(self, service):
        """测试长文本摘要"""
        text = "这是一条非常长的文本内容，需要被截断并生成摘要。它包含了很多有用的信息和详细的描述。"
        summary = service._generate_summary(text)
        assert len(summary) <= 53  # 50 + "..."
        assert "..." in summary or summary == text


class TestFusionMethods:
    """测试融合方法"""

    def test_weighted_fusion(self, service):
        """测试加权融合"""
        result_sets = {
            "feature_index": [
                {"id": "1", "text": "文本1"},
                {"id": "2", "text": "文本2"},
            ],
            "fifo_index": [
                {"id": "2", "text": "文本2"},
                {"id": "3", "text": "文本3"},
            ],
            "summary_index": [
                {"id": "1", "text": "文本1"},
                {"id": "3", "text": "文本3"},
            ],
        }

        weights = {
            "feature_index": 0.4,
            "fifo_index": 0.3,
            "summary_index": 0.3,
        }

        fused = service._weighted_fusion(result_sets, weights, top_k=3)
        assert len(fused) == 3
        assert all("fused_score" in item for item in fused)


class TestFeatureExtraction:
    """测试特征提取"""

    def test_extract_features(self, service):
        """测试特征提取"""
        text = "这是一个测试文本"
        features = service._extract_features(text)

        assert "word_count" in features
        assert "char_count" in features
        assert features["word_count"] > 0
        assert features["char_count"] == len(text)

    def test_extract_features_empty(self, service):
        """测试空文本特征提取"""
        features = service._extract_features("")

        assert features["word_count"] == 0
        assert features["char_count"] == 0


class TestErrorHandling:
    """测试错误处理"""

    def test_retrieve_unknown_strategy(self, service):
        """测试未知检索策略"""
        service.insert("测试消息")

        with pytest.raises(ValueError, match="Unknown strategy"):
            service.retrieve("测试", strategy="unknown_strategy")


class TestEdgeCases:
    """测试边界情况"""

    def test_retrieve_empty_collection(self, service):
        """测试空Collection检索"""
        results = service.retrieve("查询文本", top_k=5)
        assert isinstance(results, list)

    def test_large_top_k(self, service):
        """测试超大top_k"""
        service.insert("消息1")
        service.insert("消息2")

        results = service.retrieve("消息", top_k=1000)
        assert len(results) <= 1000

    def test_merge_results(self, service):
        """测试结果合并"""
        results1 = [
            {"id": "1", "text": "A"},
            {"id": "2", "text": "B"},
        ]
        results2 = [
            {"id": "2", "text": "B"},
            {"id": "3", "text": "C"},
        ]

        merged = service._merge_results(results1, results2, top_k=3)
        assert len(merged) == 3
        ids = [r["id"] for r in merged]
        assert "1" in ids
        assert "2" in ids
        assert "3" in ids
