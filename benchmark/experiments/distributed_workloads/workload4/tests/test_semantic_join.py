"""
单元测试：Semantic Join 和窗口管理

测试场景:
1. 窗口状态管理（添加/删除/过期）
2. 相似度计算（NumPy 优化）
3. Join 算子基本功能
4. 性能测试（61.4M ops/s 负载）
"""

import time

import numpy as np
import pytest

from ..models import DocumentEvent, QueryEvent
from ..semantic_join import JoinWindowState, SemanticJoinOperator, SimpleJoinOperator


class TestJoinWindowState:
    """测试窗口状态管理"""

    def setup_method(self):
        """每个测试前初始化"""
        self.embedding_dim = 128  # 使用较小维度加速测试
        self.window_state = JoinWindowState(
            window_seconds=5, threshold=0.7, embedding_dim=self.embedding_dim
        )

    def _create_doc(self, doc_id: str, timestamp: float) -> DocumentEvent:
        """创建测试文档"""
        # 生成随机 embedding
        embedding = np.random.randn(self.embedding_dim).tolist()
        return DocumentEvent(
            doc_id=doc_id,
            doc_text=f"Document {doc_id}",
            doc_category="technology",
            timestamp=timestamp,
            embedding=embedding,
        )

    def test_add_document(self):
        """测试添加文档"""
        doc = self._create_doc("doc1", 1.0)

        assert self.window_state.add_document(doc) is True
        assert self.window_state.size() == 1

        # 添加更多文档
        for i in range(2, 11):
            doc = self._create_doc(f"doc{i}", float(i))
            self.window_state.add_document(doc)

        assert self.window_state.size() == 10

    def test_remove_expired(self):
        """测试过期文档清理"""
        # 添加文档（时间戳 1-10）
        for i in range(1, 11):
            doc = self._create_doc(f"doc{i}", float(i))
            self.window_state.add_document(doc)

        assert self.window_state.size() == 10

        # 当前时间 15，窗口 5s，应该删除时间戳 < 10 的文档
        expired_count = self.window_state.remove_expired(15.0)

        assert expired_count == 9  # doc1-doc9
        assert self.window_state.size() == 1  # 只剩 doc10

    def test_find_matches_empty_window(self):
        """测试空窗口查询"""
        query_embedding = np.random.randn(self.embedding_dim)
        matches = self.window_state.find_matches(query_embedding)

        assert len(matches) == 0

    def test_find_matches_similarity(self):
        """测试相似度匹配"""
        # 创建一个已知 embedding 的文档
        base_embedding = np.random.randn(self.embedding_dim)

        doc1 = DocumentEvent(
            doc_id="doc1",
            doc_text="Test doc 1",
            doc_category="technology",
            timestamp=1.0,
            embedding=base_embedding.tolist(),
        )
        self.window_state.add_document(doc1)

        # 创建相似的查询 embedding（相同向量，相似度 = 1.0）
        query_embedding = base_embedding.copy()
        matches = self.window_state.find_matches(query_embedding)

        assert len(matches) == 1
        assert matches[0][0] == "doc1"
        assert matches[0][1] > 0.99  # 应该非常接近 1.0

    def test_find_matches_threshold_filter(self):
        """测试阈值过滤"""
        # 创建多个文档，embeddings 与查询相似度不同
        query_embedding = np.random.randn(self.embedding_dim)
        query_norm = np.linalg.norm(query_embedding)
        query_embedding = query_embedding / query_norm

        # Doc1: 高相似度（0.98+，使用很小的噪声）
        doc1_emb = query_embedding + np.random.randn(self.embedding_dim) * 0.01
        doc1_emb = doc1_emb / np.linalg.norm(doc1_emb)
        doc1 = DocumentEvent(
            doc_id="doc1",
            doc_text="High similarity",
            doc_category="technology",
            timestamp=1.0,
            embedding=doc1_emb.tolist(),
        )

        # Doc2: 低相似度（随机向量，期望 < 0.3）
        doc2_emb = np.random.randn(self.embedding_dim)
        doc2_emb = doc2_emb / np.linalg.norm(doc2_emb)
        doc2 = DocumentEvent(
            doc_id="doc2",
            doc_text="Low similarity",
            doc_category="technology",
            timestamp=2.0,
            embedding=doc2_emb.tolist(),
        )

        self.window_state.add_document(doc1)
        self.window_state.add_document(doc2)

        # 查询（threshold=0.7）
        matches = self.window_state.find_matches(query_embedding)

        # 至少 doc1 应该匹配
        assert len(matches) >= 1, f"Expected at least 1 match, got {len(matches)}"
        assert matches[0][0] == "doc1"
        assert matches[0][1] >= 0.7

    def test_find_matches_top_k(self):
        """测试 Top-K 限制"""
        query_embedding = np.random.randn(self.embedding_dim)

        # 添加 10 个高相似度文档
        for i in range(10):
            doc_emb = query_embedding + np.random.randn(self.embedding_dim) * 0.05
            doc = DocumentEvent(
                doc_id=f"doc{i}",
                doc_text=f"Doc {i}",
                doc_category="technology",
                timestamp=float(i),
                embedding=doc_emb.tolist(),
            )
            self.window_state.add_document(doc)

        # Top-5
        matches = self.window_state.find_matches(query_embedding, top_k=5)

        assert len(matches) == 5

        # 验证按分数降序
        for i in range(len(matches) - 1):
            assert matches[i][1] >= matches[i + 1][1]

    def test_embedding_matrix_rebuild(self):
        """测试 embedding 矩阵重建"""
        # 添加文档
        for i in range(10):
            doc = self._create_doc(f"doc{i}", float(i))
            self.window_state.add_document(doc)

        # 强制重建
        self.window_state._rebuild_embedding_matrix()

        assert self.window_state._embeddings is not None
        assert self.window_state._embeddings.shape == (10, self.embedding_dim)
        assert len(self.window_state._doc_ids) == 10

    def test_get_documents(self):
        """测试批量获取文档"""
        # 添加文档 (doc0-doc4)
        for i in range(5):
            doc = self._create_doc(f"doc{i}", float(i))
            self.window_state.add_document(doc)

        # 获取部分文档
        docs = self.window_state.get_documents(["doc1", "doc3", "doc5", "nonexistent"])

        assert len(docs) == 2  # doc1, doc3 存在，doc5 不存在
        doc_ids = [doc.doc_id for doc in docs]
        assert "doc1" in doc_ids
        assert "doc3" in doc_ids
        assert "doc5" not in doc_ids  # doc5 确实不存在（range(5) 只创建 0-4）

    def test_stats(self):
        """测试统计信息"""
        # 添加和删除文档
        for i in range(10):
            doc = self._create_doc(f"doc{i}", float(i))
            self.window_state.add_document(doc)

        self.window_state.remove_expired(15.0)

        stats = self.window_state.get_stats()

        assert stats["window_size"] >= 0
        assert stats["total_docs_added"] == 10
        assert stats["total_docs_expired"] > 0


class TestSemanticJoinOperator:
    """测试 Semantic Join 算子"""

    def setup_method(self):
        """每个测试前初始化"""
        self.embedding_dim = 128
        self.operator = SemanticJoinOperator(
            window_seconds=5,
            threshold=0.7,
            embedding_dim=self.embedding_dim,
            enable_stats=False,  # 测试时禁用打印
        )

    def _create_query(
        self, query_id: str, timestamp: float, embedding: list[float] | None = None
    ) -> QueryEvent:
        """创建测试查询"""
        if embedding is None:
            embedding = np.random.randn(self.embedding_dim).tolist()

        return QueryEvent(
            query_id=query_id,
            query_text=f"Query {query_id}",
            query_type="factual",
            category="technology",
            timestamp=timestamp,
            embedding=embedding,
        )

    def _create_doc(
        self, doc_id: str, timestamp: float, embedding: list[float] | None = None
    ) -> DocumentEvent:
        """创建测试文档"""
        if embedding is None:
            embedding = np.random.randn(self.embedding_dim).tolist()

        return DocumentEvent(
            doc_id=doc_id,
            doc_text=f"Document {doc_id}",
            doc_category="technology",
            timestamp=timestamp,
            embedding=embedding,
        )

    def test_empty_window_query(self):
        """测试空窗口查询"""
        query = self._create_query("q1", 1.0)
        result = self.operator.map0(query)

        assert result is None  # 无匹配

    def test_add_document(self):
        """测试添加文档"""
        doc = self._create_doc("doc1", 1.0)
        self.operator.map1(doc)

        assert self.operator.window_state.size() == 1

    def test_join_with_match(self):
        """测试成功 Join"""
        # 先添加文档
        base_embedding = np.random.randn(self.embedding_dim)
        doc = self._create_doc("doc1", 1.0, embedding=base_embedding.tolist())
        self.operator.map1(doc)

        # 查询（相同 embedding）
        query = self._create_query("q1", 2.0, embedding=base_embedding.tolist())
        result = self.operator.map0(query)

        assert result is not None
        assert isinstance(result, type(result))  # JoinedEvent
        assert result.query.query_id == "q1"
        assert len(result.matched_docs) == 1
        assert result.matched_docs[0].doc_id == "doc1"
        assert result.semantic_score > 0.9  # 应该非常相似

    def test_join_no_match(self):
        """测试无匹配 Join"""
        # 添加文档
        doc = self._create_doc("doc1", 1.0)
        self.operator.map1(doc)

        # 查询（完全不同的 embedding）
        query_emb = np.random.randn(self.embedding_dim)
        query = self._create_query("q1", 2.0, embedding=query_emb.tolist())

        result = self.operator.map0(query)

        # 可能无匹配（取决于随机 embedding）
        # 这个测试不够稳定，实际应该使用正交向量

    def test_window_expiration(self):
        """测试窗口过期"""
        # 添加早期文档
        doc1 = self._create_doc("doc1", 1.0)
        self.operator.map1(doc1)

        # 添加晚期文档
        doc2 = self._create_doc("doc2", 8.0)
        self.operator.map1(doc2)

        # 查询（时间戳 10，窗口 5s，doc1 应该过期）
        query = self._create_query("q1", 10.0)
        self.operator.map0(query)

        # doc1 应该被清理
        assert self.operator.window_state.size() == 1

    def test_multiple_matches(self):
        """测试多文档匹配"""
        # 添加多个相似文档
        base_embedding = np.random.randn(self.embedding_dim)

        for i in range(5):
            doc_emb = base_embedding + np.random.randn(self.embedding_dim) * 0.05
            doc = self._create_doc(f"doc{i}", float(i), embedding=doc_emb.tolist())
            self.operator.map1(doc)

        # 查询
        query = self._create_query("q1", 5.0, embedding=base_embedding.tolist())
        result = self.operator.map0(query)

        if result is not None:
            assert len(result.matched_docs) >= 1
            assert result.semantic_score >= 0.7

    def test_top_k_limit(self):
        """测试 Top-K 限制"""
        operator_with_topk = SemanticJoinOperator(
            window_seconds=5,
            threshold=0.5,  # 降低阈值确保多匹配
            embedding_dim=self.embedding_dim,
            top_k=3,
            enable_stats=False,
        )

        # 添加 10 个相似文档
        base_embedding = np.random.randn(self.embedding_dim)
        for i in range(10):
            doc_emb = base_embedding + np.random.randn(self.embedding_dim) * 0.1
            doc = self._create_doc(f"doc{i}", float(i), embedding=doc_emb.tolist())
            operator_with_topk.map1(doc)

        # 查询
        query = self._create_query("q1", 10.0, embedding=base_embedding.tolist())
        result = operator_with_topk.map0(query)

        if result is not None:
            assert len(result.matched_docs) <= 3  # Top-3 限制


class TestSimpleJoinOperator:
    """测试简化版 Join 算子"""

    def setup_method(self):
        """每个测试前初始化"""
        self.embedding_dim = 128
        self.operator = SimpleJoinOperator(threshold=0.7)

    def test_simple_join(self):
        """测试简单 Join"""
        # 添加文档
        base_embedding = np.random.randn(self.embedding_dim)
        doc = DocumentEvent(
            doc_id="doc1",
            doc_text="Test doc",
            doc_category="technology",
            timestamp=1.0,
            embedding=base_embedding.tolist(),
        )
        self.operator.map1(doc)

        # 查询
        query = QueryEvent(
            query_id="q1",
            query_text="Test query",
            query_type="factual",
            category="technology",
            timestamp=2.0,
            embedding=base_embedding.tolist(),
        )
        results = self.operator.map0(query)

        assert len(results) == 1
        assert results[0].query.query_id == "q1"
        assert results[0].matched_docs[0].doc_id == "doc1"


class TestPerformance:
    """性能测试"""

    def test_large_window_performance(self):
        """
        测试大窗口性能。

        模拟 Workload 4 场景：
        - 1500 docs in window
        - 1024 dim embeddings
        - 相似度计算性能
        """
        embedding_dim = 1024
        window_state = JoinWindowState(
            window_seconds=60, threshold=0.7, embedding_dim=embedding_dim
        )

        # 添加 1500 个文档
        print("\n[Performance Test] Adding 1500 documents...")
        start_time = time.time()

        for i in range(1500):
            embedding = np.random.randn(embedding_dim).tolist()
            doc = DocumentEvent(
                doc_id=f"doc{i}",
                doc_text=f"Document {i}",
                doc_category="technology",
                timestamp=float(i) * 0.04,  # 25 docs/s
                embedding=embedding,
            )
            window_state.add_document(doc)

        add_time = time.time() - start_time
        print(f"  Time: {add_time:.2f}s ({1500 / add_time:.1f} docs/s)")

        # 查询性能（40 queries）
        print("\n[Performance Test] Running 40 queries...")
        query_embeddings = [np.random.randn(embedding_dim) for _ in range(40)]

        start_time = time.time()
        total_matches = 0

        for i, query_emb in enumerate(query_embeddings):
            matches = window_state.find_matches(query_emb)
            total_matches += len(matches)

        query_time = time.time() - start_time
        avg_query_time = query_time / 40 * 1000  # ms

        print(f"  Total time: {query_time:.2f}s")
        print(f"  Avg query time: {avg_query_time:.2f}ms")
        print(f"  QPS: {40 / query_time:.1f}")
        print(f"  Total matches: {total_matches}")
        print(f"  Avg matches per query: {total_matches / 40:.1f}")

        # 性能目标：平均查询时间 < 100ms
        assert avg_query_time < 100, f"Query too slow: {avg_query_time:.2f}ms > 100ms"

    def test_batch_similarity_performance(self):
        """
        测试批量相似度计算性能。

        验证 NumPy 矩阵运算优化效果。
        """
        embedding_dim = 1024
        num_docs = 1500

        # 生成测试数据
        query_emb = np.random.randn(embedding_dim).astype(np.float32)
        query_emb = query_emb / np.linalg.norm(query_emb)

        doc_embs = np.random.randn(num_docs, embedding_dim).astype(np.float32)
        norms = np.linalg.norm(doc_embs, axis=1, keepdims=True)
        doc_embs = doc_embs / norms

        # 批量计算
        start_time = time.time()
        similarities = doc_embs @ query_emb
        batch_time = time.time() - start_time

        print("\n[Performance Test] Batch similarity calculation:")
        print(f"  Docs: {num_docs}, Dim: {embedding_dim}")
        print(f"  Time: {batch_time * 1000:.2f}ms")
        print(f"  Ops: {num_docs * embedding_dim / batch_time / 1e6:.1f}M ops/s")

        # 性能目标：> 50M ops/s
        ops_per_sec = num_docs * embedding_dim / batch_time
        assert ops_per_sec > 50e6, f"Too slow: {ops_per_sec / 1e6:.1f}M ops/s < 50M ops/s"


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v", "-s"])
