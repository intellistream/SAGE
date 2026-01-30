"""
Workload 4 Sources 单元测试

测试双流源算子和 Embedding 预计算算子。
"""

import sys
import time
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

# 添加父目录到路径
parent_dir = Path(__file__).parent.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

from models import DocumentEvent, QueryEvent
from sources import (
    EmbeddingPrecompute,
    Workload4DocumentSource,
    Workload4QuerySource,
    create_document_source,
    create_embedding_precompute,
    create_query_source,
)


class TestWorkload4QuerySource(unittest.TestCase):
    """测试查询源算子"""

    def test_query_generation(self):
        """测试查询生成基本功能"""
        source = Workload4QuerySource(
            num_tasks=10,
            qps=100.0,  # 高QPS以加快测试
            seed=42,
        )

        queries = list(source.execute())

        # 验证数量
        self.assertEqual(len(queries), 10)

        # 验证类型
        for query in queries:
            self.assertIsInstance(query, QueryEvent)
            self.assertIn(query.query_type, ["factual", "analytical", "exploratory"])
            self.assertIn(query.category, ["finance", "healthcare", "technology", "general"])
            self.assertIsNotNone(query.query_text)
            self.assertIsNotNone(query.timestamp)
            self.assertIsNone(query.embedding)  # 初始为 None

    def test_query_id_format(self):
        """测试查询 ID 格式"""
        source = Workload4QuerySource(num_tasks=5, qps=100.0)
        queries = list(source.execute())

        expected_ids = ["q_000000", "q_000001", "q_000002", "q_000003", "q_000004"]
        actual_ids = [q.query_id for q in queries]

        self.assertEqual(actual_ids, expected_ids)

    def test_query_distribution(self):
        """测试查询类型和类别分布"""
        source = Workload4QuerySource(
            num_tasks=1000,
            qps=1000.0,
            seed=42,
        )

        queries = list(source.execute())

        # 统计类型分布
        type_counts = {"factual": 0, "analytical": 0, "exploratory": 0}
        category_counts = {"finance": 0, "healthcare": 0, "technology": 0, "general": 0}

        for query in queries:
            type_counts[query.query_type] += 1
            category_counts[query.category] += 1

        # 验证分布接近预期（允许 10% 误差）
        total = len(queries)
        self.assertAlmostEqual(type_counts["factual"] / total, 0.4, delta=0.1)
        self.assertAlmostEqual(type_counts["analytical"] / total, 0.35, delta=0.1)
        self.assertAlmostEqual(type_counts["exploratory"] / total, 0.25, delta=0.1)

        self.assertAlmostEqual(category_counts["finance"] / total, 0.30, delta=0.1)
        self.assertAlmostEqual(category_counts["healthcare"] / total, 0.25, delta=0.1)

    def test_qps_control(self):
        """测试 QPS 控制（粗略测试）"""
        source = Workload4QuerySource(num_tasks=20, qps=10.0)

        start = time.time()
        queries = list(source.execute())
        elapsed = time.time() - start

        # 20 个查询，10 QPS，应该约 2 秒
        # 允许较大误差（系统调度、GC等影响）
        self.assertGreater(elapsed, 1.5)
        self.assertLess(elapsed, 3.0)


class TestWorkload4DocumentSource(unittest.TestCase):
    """测试文档源算子"""

    def test_document_generation(self):
        """测试文档生成基本功能"""
        source = Workload4DocumentSource(
            num_docs=10,
            qps=100.0,
            seed=42,
        )

        docs = list(source.execute())

        # 验证数量
        self.assertEqual(len(docs), 10)

        # 验证类型
        for doc in docs:
            self.assertIsInstance(doc, DocumentEvent)
            self.assertIn(doc.doc_category, ["finance", "healthcare", "technology", "general"])
            self.assertIsNotNone(doc.doc_text)
            self.assertIsNotNone(doc.timestamp)
            self.assertIsNone(doc.embedding)
            self.assertIsInstance(doc.metadata, dict)

    def test_document_id_format(self):
        """测试文档 ID 格式"""
        source = Workload4DocumentSource(num_docs=5, qps=100.0)
        docs = list(source.execute())

        expected_ids = ["d_000000", "d_000001", "d_000002", "d_000003", "d_000004"]
        actual_ids = [d.doc_id for d in docs]

        self.assertEqual(actual_ids, expected_ids)

    def test_knowledge_base_integration(self):
        """测试知识库集成"""
        kb = [
            {"title": "Test Doc 1", "content": "This is test document 1"},
            {"title": "Test Doc 2", "content": "This is test document 2"},
        ]

        source = Workload4DocumentSource(
            num_docs=10,
            qps=100.0,
            knowledge_base=kb,
            seed=42,
        )

        docs = list(source.execute())

        # 验证文档使用了知识库内容
        kb_contents = {item["content"] for item in kb}
        for doc in docs:
            # 所有文档应该来自知识库
            self.assertIn(doc.doc_text, kb_contents)
            self.assertEqual(doc.metadata.get("source"), "knowledge_base")


class TestEmbeddingPrecompute(unittest.TestCase):
    """测试 Embedding 预计算算子"""

    @patch("requests.post")
    def test_query_embedding(self, mock_post):
        """测试查询 embedding 计算"""
        # Mock API 响应
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": [{"embedding": [0.1] * 1024}]}
        mock_post.return_value = mock_response

        # 创建算子
        precompute = EmbeddingPrecompute(
            embedding_base_url="http://test:8090/v1",
            embedding_model="test-model",
        )

        # 创建查询事件
        query = QueryEvent(
            query_id="q_001",
            query_text="test query",
            query_type="factual",
            category="finance",
            timestamp=time.time(),
        )

        # 执行
        result = precompute.execute(query)

        # 验证
        self.assertIsInstance(result, QueryEvent)
        self.assertIsNotNone(result.embedding)
        self.assertEqual(len(result.embedding), 1024)
        self.assertEqual(result.embedding[0], 0.1)

        # 验证 API 调用
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        self.assertEqual(call_args[0][0], "http://test:8090/v1/embeddings")
        self.assertEqual(call_args[1]["json"]["input"], ["test query"])

    @patch("requests.post")
    def test_document_embedding(self, mock_post):
        """测试文档 embedding 计算"""
        # Mock API 响应
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": [{"embedding": [0.2] * 1024}]}
        mock_post.return_value = mock_response

        precompute = EmbeddingPrecompute()

        doc = DocumentEvent(
            doc_id="d_001",
            doc_text="test document",
            doc_category="technology",
            timestamp=time.time(),
        )

        result = precompute.execute(doc)

        self.assertIsInstance(result, DocumentEvent)
        self.assertIsNotNone(result.embedding)
        self.assertEqual(len(result.embedding), 1024)

    @patch("requests.post")
    def test_api_failure_handling(self, mock_post):
        """测试 API 失败处理"""
        # Mock API 失败
        mock_post.side_effect = Exception("API Error")

        precompute = EmbeddingPrecompute(max_retries=1)

        query = QueryEvent(
            query_id="q_001",
            query_text="test",
            query_type="factual",
            category="finance",
            timestamp=time.time(),
        )

        # 应该使用零向量占位，不抛出异常
        result = precompute.execute(query)

        self.assertIsNotNone(result.embedding)
        self.assertEqual(result.embedding, [0.0] * 1024)


class TestFactoryFunctions(unittest.TestCase):
    """测试工厂函数"""

    def test_create_query_source(self):
        """测试查询源工厂函数"""
        config = {
            "num_tasks": 50,
            "query_qps": 20.0,
            "seed": 123,
        }

        source = create_query_source(config)

        self.assertIsInstance(source, Workload4QuerySource)
        self.assertEqual(source.num_tasks, 50)
        self.assertEqual(source.qps, 20.0)
        self.assertEqual(source.seed, 123)

    def test_create_document_source(self):
        """测试文档源工厂函数"""
        config = {
            "num_tasks": 100,
            "query_qps": 40.0,
            "doc_qps": 25.0,
            "seed": 456,
        }

        source = create_document_source(config)

        self.assertIsInstance(source, Workload4DocumentSource)
        # 文档数 = duration * doc_qps = (100/40) * 25 = 62.5 ≈ 62
        self.assertAlmostEqual(source.num_docs, 62, delta=2)

    def test_create_embedding_precompute(self):
        """测试 embedding 预计算工厂函数"""
        config = {
            "embedding_base_url": "http://custom:9090/v1",
            "embedding_model": "custom-model",
            "embedding_batch_size": 64,
        }

        precompute = create_embedding_precompute(config)

        self.assertIsInstance(precompute, EmbeddingPrecompute)
        self.assertEqual(precompute.embedding_base_url, "http://custom:9090/v1")
        self.assertEqual(precompute.embedding_model, "custom-model")
        self.assertEqual(precompute.batch_size, 64)


class TestEndToEnd(unittest.TestCase):
    """端到端测试"""

    @patch("requests.post")
    def test_query_source_to_embedding(self, mock_post):
        """测试从查询源到 embedding 的完整流程"""
        # Mock embedding API
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": [{"embedding": [0.5] * 1024}]}
        mock_post.return_value = mock_response

        # 创建源
        source = Workload4QuerySource(num_tasks=5, qps=100.0)
        precompute = EmbeddingPrecompute()

        # 模拟 pipeline
        results = []
        for query in source.execute():
            if query is not None:
                query_with_emb = precompute.execute(query)
                results.append(query_with_emb)

        # 验证
        self.assertEqual(len(results), 5)
        for query in results:
            self.assertIsNotNone(query.embedding)
            self.assertEqual(len(query.embedding), 1024)


if __name__ == "__main__":
    unittest.main()
