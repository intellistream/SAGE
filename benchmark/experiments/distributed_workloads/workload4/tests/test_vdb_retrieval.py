"""
Workload 4 VDB 检索算子单元测试
"""

import pytest

from ..models import DocumentEvent, JoinedEvent, QueryEvent, VDBRetrievalResult
from ..vdb_retrieval import (
    LocalReranker,
    StageAggregator,
    VDBBranchRouter,
    VDBResultFilter,
    VDBResultMerger,
    VDBRetriever,
    build_vdb_4stage_pipeline,
    build_vdb_pipeline_stage,
)


@pytest.fixture
def sample_query_event():
    """创建测试用 QueryEvent"""
    return QueryEvent(
        query_id="q1",
        query_text="What is machine learning and its applications?",
        query_type="factual",
        category="technology",
        timestamp=1000.0,
        embedding=[0.1] * 1024,
    )


@pytest.fixture
def sample_doc_event():
    """创建测试用 DocumentEvent"""
    return DocumentEvent(
        doc_id="d1",
        doc_text="Machine learning is a subset of AI",
        doc_category="technology",
        timestamp=1001.0,
        embedding=[0.2] * 1024,
    )


@pytest.fixture
def sample_joined_event(sample_query_event, sample_doc_event):
    """创建测试用 JoinedEvent"""
    return JoinedEvent(
        joined_id="j1",
        query=sample_query_event,
        matched_docs=[sample_doc_event],
        join_timestamp=1002.0,
        semantic_score=0.85,
    )


@pytest.fixture
def sample_vdb_results():
    """创建测试用 VDB 检索结果"""
    return [
        VDBRetrievalResult(
            doc_id=f"doc_{i}",
            content=f"Content {i} about machine learning applications",
            score=0.9 - i * 0.1,
            source="vdb1",
            stage=1,
            metadata={"query_text": "machine learning applications"},
        )
        for i in range(5)
    ]


class TestVDBRetriever:
    """测试 VDBRetriever 算子"""

    def test_init(self):
        """测试初始化"""
        retriever = VDBRetriever(vdb_name="vdb1", top_k=20, stage=1)

        assert retriever.vdb_name == "vdb1"
        assert retriever.top_k == 20
        assert retriever.stage == 1

    def test_init_validation(self):
        """测试初始化验证"""
        # 无效的 vdb_name
        with pytest.raises(AssertionError):
            VDBRetriever(vdb_name="invalid", top_k=20, stage=1)

        # 无效的 stage
        with pytest.raises(AssertionError):
            VDBRetriever(vdb_name="vdb1", top_k=20, stage=5)

        # 无效的 top_k
        with pytest.raises(AssertionError):
            VDBRetriever(vdb_name="vdb1", top_k=0, stage=1)

    def test_execute_no_embedding(self, sample_joined_event):
        """测试无 embedding 时的处理"""
        retriever = VDBRetriever(vdb_name="vdb1", top_k=10, stage=1)

        # 移除 embedding
        sample_joined_event.query.embedding = None

        results = retriever.execute(sample_joined_event)

        assert results == []


class TestVDBResultFilter:
    """测试 VDBResultFilter 算子"""

    def test_init(self):
        """测试初始化"""
        filter_op = VDBResultFilter(threshold=0.6, adaptive=True)

        assert filter_op.threshold == 0.6
        assert filter_op.adaptive is True

    def test_execute_simple(self):
        """测试简单过滤"""
        filter_op = VDBResultFilter(threshold=0.7, adaptive=False)

        # 高分结果
        result_high = VDBRetrievalResult(
            doc_id="doc1", content="Test content", score=0.85, source="vdb1", stage=1
        )

        # 低分结果
        result_low = VDBRetrievalResult(
            doc_id="doc2", content="Test content", score=0.55, source="vdb1", stage=1
        )

        assert filter_op.execute(result_high) is True
        assert filter_op.execute(result_low) is False

        assert result_high.filtered is False
        assert result_low.filtered is True

    def test_execute_adaptive(self):
        """测试自适应阈值"""
        filter_op = VDBResultFilter(threshold=0.6, adaptive=True)

        # Stage 1 结果
        result_s1 = VDBRetrievalResult(
            doc_id="doc1", content="Test", score=0.62, source="vdb1", stage=1
        )

        # Stage 3 结果（阈值提高）
        result_s3 = VDBRetrievalResult(
            doc_id="doc2", content="Test", score=0.62, source="vdb1", stage=3
        )

        # Stage 1: threshold = 0.6, 0.62 > 0.6 -> pass
        assert filter_op.execute(result_s1) is True

        # Stage 3: threshold = 0.6 + 2*0.05 = 0.7, 0.62 < 0.7 -> filtered
        assert filter_op.execute(result_s3) is False


class TestLocalReranker:
    """测试 LocalReranker 算子"""

    def test_init(self):
        """测试初始化"""
        reranker = LocalReranker(top_k=10, k1=1.5, b=0.75)

        assert reranker.top_k == 10
        assert reranker.k1 == 1.5
        assert reranker.b == 0.75

    def test_execute_empty(self):
        """测试空输入"""
        reranker = LocalReranker(top_k=10)

        results = reranker.execute([])

        assert results == []

    def test_execute_no_query(self):
        """测试无查询文本时的处理"""
        reranker = LocalReranker(top_k=3)

        results = [
            VDBRetrievalResult(
                doc_id=f"doc_{i}",
                content=f"Content {i}",
                score=0.9 - i * 0.1,
                source="vdb1",
                stage=1,
                metadata={},  # 没有 query_text
            )
            for i in range(5)
        ]

        reranked = reranker.execute(results)

        # 应该按原始分数排序返回
        assert len(reranked) == 3
        assert reranked[0].doc_id == "doc_0"
        assert reranked[1].doc_id == "doc_1"
        assert reranked[2].doc_id == "doc_2"

    def test_execute_with_bm25(self, sample_vdb_results):
        """测试 BM25 重排序"""
        reranker = LocalReranker(top_k=3)

        reranked = reranker.execute(sample_vdb_results)

        assert len(reranked) <= 3
        # 所有结果应该有 rerank_score
        for result in reranked:
            assert result.rerank_score is not None

    def test_tokenize(self):
        """测试分词功能"""
        reranker = LocalReranker(top_k=10)

        tokens = reranker._tokenize("What is Machine Learning and its Applications?")

        # 应该移除停用词和标点
        assert "what" not in tokens  # 停用词
        assert "machine" in tokens
        assert "learning" in tokens
        assert "applications" in tokens


class TestStageAggregator:
    """测试 StageAggregator 算子"""

    def test_init(self):
        """测试初始化"""
        aggregator = StageAggregator(num_stages=4)

        assert aggregator.num_stages == 4

    def test_execute_empty(self):
        """测试空输入"""
        aggregator = StageAggregator(num_stages=4)

        results = aggregator.execute([])

        assert results == []

    def test_execute_deduplication(self):
        """测试去重功能"""
        aggregator = StageAggregator(num_stages=4)

        # 创建有重复的结果
        stage1_results = [
            VDBRetrievalResult(
                doc_id="doc_1", content="Content 1", score=0.85, source="vdb1", stage=1
            ),
            VDBRetrievalResult(
                doc_id="doc_2", content="Content 2", score=0.75, source="vdb1", stage=1
            ),
        ]

        stage2_results = [
            VDBRetrievalResult(
                doc_id="doc_1",  # 重复
                content="Content 1",
                score=0.90,  # 更高分
                source="vdb1",
                stage=2,
            ),
            VDBRetrievalResult(
                doc_id="doc_3", content="Content 3", score=0.80, source="vdb1", stage=2
            ),
        ]

        aggregated = aggregator.execute([stage1_results, stage2_results])

        # 应该去重，保留 3 个文档
        assert len(aggregated) == 3

        # doc_1 应该保留更高的分数 (0.90)
        doc_1 = next(r for r in aggregated if r.doc_id == "doc_1")
        assert doc_1.score == 0.90
        assert doc_1.stage == 2

    def test_execute_sorting(self):
        """测试排序功能"""
        aggregator = StageAggregator(num_stages=2)

        stage_results = [
            [
                VDBRetrievalResult(
                    doc_id=f"doc_{i}",
                    content=f"Content {i}",
                    score=0.5 + i * 0.1,
                    source="vdb1",
                    stage=1,
                )
                for i in range(5)
            ]
        ]

        aggregated = aggregator.execute(stage_results)

        # 应该按分数降序排列
        for i in range(len(aggregated) - 1):
            assert aggregated[i].score >= aggregated[i + 1].score


class TestVDBBranchRouter:
    """测试 VDBBranchRouter 算子"""

    def test_init(self):
        """测试初始化"""
        router = VDBBranchRouter(routing_strategy="round_robin")

        assert router.routing_strategy == "round_robin"

    def test_round_robin(self, sample_joined_event):
        """测试轮询路由"""
        router = VDBBranchRouter(routing_strategy="round_robin")

        branch1, _ = router.execute(sample_joined_event)
        branch2, _ = router.execute(sample_joined_event)
        branch3, _ = router.execute(sample_joined_event)

        # 应该轮流路由
        assert branch1 == "vdb1"
        assert branch2 == "vdb2"
        assert branch3 == "vdb1"

    def test_category_routing(self, sample_query_event, sample_doc_event):
        """测试类别路由"""
        router = VDBBranchRouter(routing_strategy="category")

        # finance -> vdb1
        finance_event = JoinedEvent(
            joined_id="j1",
            query=QueryEvent(
                query_id="q1",
                query_text="Test",
                query_type="factual",
                category="finance",
                timestamp=1000.0,
            ),
            matched_docs=[sample_doc_event],
            join_timestamp=1001.0,
            semantic_score=0.8,
        )

        # technology -> vdb2
        tech_event = JoinedEvent(
            joined_id="j2",
            query=QueryEvent(
                query_id="q2",
                query_text="Test",
                query_type="factual",
                category="technology",
                timestamp=1000.0,
            ),
            matched_docs=[sample_doc_event],
            join_timestamp=1001.0,
            semantic_score=0.8,
        )

        branch1, _ = router.execute(finance_event)
        branch2, _ = router.execute(tech_event)

        assert branch1 == "vdb1"
        assert branch2 == "vdb2"


class TestVDBResultMerger:
    """测试 VDBResultMerger 算子"""

    def test_init(self):
        """测试初始化"""
        merger = VDBResultMerger(merge_strategy="score_based", top_k=30)

        assert merger.merge_strategy == "score_based"
        assert merger.top_k == 30

    def test_score_based_merge(self):
        """测试基于分数的合并"""
        merger = VDBResultMerger(merge_strategy="score_based", top_k=5)

        vdb1_results = [
            VDBRetrievalResult(
                doc_id=f"vdb1_doc_{i}",
                content=f"Content {i}",
                score=0.9 - i * 0.1,
                source="vdb1",
                stage=1,
            )
            for i in range(3)
        ]

        vdb2_results = [
            VDBRetrievalResult(
                doc_id=f"vdb2_doc_{i}",
                content=f"Content {i}",
                score=0.85 - i * 0.1,
                source="vdb2",
                stage=1,
            )
            for i in range(3)
        ]

        merged = merger.execute(vdb1_results, vdb2_results)

        assert len(merged) <= 5
        # 应该按分数排序
        for i in range(len(merged) - 1):
            assert merged[i].score >= merged[i + 1].score

    def test_interleave_merge(self):
        """测试交替合并"""
        merger = VDBResultMerger(merge_strategy="interleave", top_k=10)

        vdb1_results = [
            VDBRetrievalResult(
                doc_id=f"vdb1_doc_{i}", content=f"Content {i}", score=0.9, source="vdb1", stage=1
            )
            for i in range(3)
        ]

        vdb2_results = [
            VDBRetrievalResult(
                doc_id=f"vdb2_doc_{i}", content=f"Content {i}", score=0.9, source="vdb2", stage=1
            )
            for i in range(3)
        ]

        merged = merger.execute(vdb1_results, vdb2_results)

        # 应该交替排列（去重后）
        assert len(merged) == 6
        # 检查交替模式
        sources = [r.source for r in merged]
        # 交替模式应该是 vdb1, vdb2, vdb1, vdb2, ...
        for i in range(0, len(sources), 2):
            if i < len(sources):
                assert sources[i] == "vdb1"
            if i + 1 < len(sources):
                assert sources[i + 1] == "vdb2"

    def test_deduplication(self):
        """测试去重功能"""
        merger = VDBResultMerger(merge_strategy="score_based", top_k=10)

        vdb1_results = [
            VDBRetrievalResult(
                doc_id="doc_1", content="Content", score=0.85, source="vdb1", stage=1
            )
        ]

        vdb2_results = [
            VDBRetrievalResult(
                doc_id="doc_1",  # 重复
                content="Content",
                score=0.90,  # 更高分
                source="vdb2",
                stage=1,
            )
        ]

        merged = merger.execute(vdb1_results, vdb2_results)

        # 应该只有一个结果
        assert len(merged) == 1
        # 应该保留更高分的
        assert merged[0].score == 0.90
        assert merged[0].source == "vdb2"


class TestHelperFunctions:
    """测试辅助函数"""

    def test_build_vdb_pipeline_stage(self):
        """测试单个 stage 构建"""
        retriever, filter_op, reranker = build_vdb_pipeline_stage(
            vdb_name="vdb1", stage=1, top_k=20, filter_threshold=0.6, rerank_top_k=15
        )

        assert isinstance(retriever, VDBRetriever)
        assert retriever.vdb_name == "vdb1"
        assert retriever.stage == 1
        assert retriever.top_k == 20

        assert isinstance(filter_op, VDBResultFilter)
        assert filter_op.threshold == 0.6

        assert isinstance(reranker, LocalReranker)
        assert reranker.top_k == 15

    def test_build_vdb_4stage_pipeline(self):
        """测试 4-stage 流水线构建"""
        stages = build_vdb_4stage_pipeline(vdb_name="vdb1")

        assert len(stages) == 4

        # Stage 1-3 应该有完整的算子链
        for i in range(3):
            retriever, filter_op, reranker = stages[i]
            assert isinstance(retriever, VDBRetriever)
            assert isinstance(filter_op, VDBResultFilter)
            assert isinstance(reranker, LocalReranker)
            assert retriever.stage == i + 1

        # Stage 4 没有 filter 和 rerank
        retriever, filter_op, reranker = stages[3]
        assert isinstance(retriever, VDBRetriever)
        assert retriever.stage == 4
        assert filter_op is None
        assert reranker is None

    def test_build_vdb_4stage_pipeline_custom_config(self):
        """测试自定义配置的 4-stage 构建"""
        config = {
            "stage1_top_k": 30,
            "stage1_threshold": 0.7,
            "stage1_rerank": 20,
        }

        stages = build_vdb_4stage_pipeline(vdb_name="vdb2", config=config)

        # 检查 Stage 1 使用了自定义配置
        retriever, filter_op, reranker = stages[0]
        assert retriever.top_k == 30
        assert filter_op.threshold == 0.7
        assert reranker.top_k == 20


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
