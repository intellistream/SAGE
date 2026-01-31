"""
Workload 4 重排序模块的单元测试。
"""

import tempfile
import time
from pathlib import Path

import numpy as np
import pytest

from ..models import (
    ClusteringResult,
    JoinedEvent,
    QueryEvent,
    RerankingResult,
    VDBRetrievalResult,
)
from ..reranking import (
    MMRDiversityFilter,
    MultiDimensionalReranker,
    visualize_score_breakdown,
    visualize_score_distribution,
)

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def sample_query() -> QueryEvent:
    """创建示例查询事件"""
    return QueryEvent(
        query_id="q1",
        query_text="What is machine learning and its applications",
        query_type="factual",
        category="technology",
        timestamp=time.time(),
        embedding=np.random.randn(128).tolist(),
    )


@pytest.fixture
def sample_vdb_results() -> list[VDBRetrievalResult]:
    """创建示例 VDB 检索结果"""
    results = []
    current_time = time.time()

    for i in range(20):
        results.append(
            VDBRetrievalResult(
                doc_id=f"doc_{i}",
                content=f"Document {i} about machine learning and data science applications",
                score=0.9 - i * 0.03,  # 递减分数
                source="vdb1",
                stage=1,
                metadata={
                    "timestamp": current_time - i * 3600,  # 1 小时间隔
                    "citations": max(0, 50 - i * 5),  # 递减引用数
                    "centrality": max(0.1, 0.9 - i * 0.04),
                    "source": "verified" if i < 10 else "general",
                },
            )
        )

    return results


@pytest.fixture
def sample_clustering_info() -> list[ClusteringResult]:
    """创建示例聚类信息"""
    return [
        ClusteringResult(
            cluster_id=0,
            representative_doc_id="doc_0",
            cluster_docs=["doc_0", "doc_1", "doc_2"],
            cluster_size=3,
        ),
        ClusteringResult(
            cluster_id=1,
            representative_doc_id="doc_3",
            cluster_docs=["doc_3", "doc_4", "doc_5", "doc_6"],
            cluster_size=4,
        ),
        ClusteringResult(
            cluster_id=-1,  # 噪音点
            representative_doc_id="doc_7",
            cluster_docs=["doc_7"],
            cluster_size=1,
        ),
    ]


@pytest.fixture
def sample_joined_event(sample_query) -> JoinedEvent:
    """创建示例 Join 事件"""
    from ..models import DocumentEvent

    return JoinedEvent(
        joined_id=f"joined_{sample_query.query_id}_{int(time.time())}",
        query=sample_query,
        matched_docs=[
            DocumentEvent(
                doc_id="doc_match_1",
                doc_text="Matched document 1",
                doc_category="technology",
                timestamp=time.time(),
            )
        ],
        join_timestamp=time.time(),
        semantic_score=0.85,
    )


# ============================================================================
# MultiDimensionalReranker Tests
# ============================================================================


def test_reranker_initialization():
    """测试重排序器初始化"""
    # 默认权重
    reranker = MultiDimensionalReranker()
    assert reranker.top_k == 15
    assert sum(reranker.weights.values()) == pytest.approx(1.0, abs=0.01)

    # 自定义权重
    custom_weights = {
        "semantic": 0.4,
        "freshness": 0.3,
        "diversity": 0.1,
        "authority": 0.1,
        "coverage": 0.1,
    }
    reranker = MultiDimensionalReranker(score_weights=custom_weights, top_k=10)
    assert reranker.top_k == 10
    assert reranker.weights == custom_weights


def test_reranker_invalid_weights():
    """测试无效权重检测"""
    invalid_weights = {
        "semantic": 0.5,
        "freshness": 0.3,
        "diversity": 0.1,
        "authority": 0.1,
        "coverage": 0.1,  # 总和 = 1.1
    }

    with pytest.raises(ValueError, match="权重总和应为 1.0"):
        MultiDimensionalReranker(score_weights=invalid_weights)


def test_reranker_execute_empty_results(sample_joined_event):
    """测试空结果处理"""
    reranker = MultiDimensionalReranker()

    data = (sample_joined_event, [], None)
    results = reranker.execute(data)

    assert results == []


def test_reranker_execute_basic(sample_joined_event, sample_vdb_results, sample_clustering_info):
    """测试基本重排序功能"""
    reranker = MultiDimensionalReranker(top_k=10, enable_profiling=True)

    data = (sample_joined_event, sample_vdb_results, sample_clustering_info)
    results = reranker.execute(data)

    # 检查结果数量
    assert len(results) == 10

    # 检查排序（final_score 降序）
    for i in range(len(results) - 1):
        assert results[i].final_score >= results[i + 1].final_score

    # 检查 rank 填充
    for i, result in enumerate(results):
        assert result.rank == i + 1

    # 检查评分分解
    for result in results:
        assert "semantic" in result.score_breakdown
        assert "freshness" in result.score_breakdown
        assert "diversity" in result.score_breakdown
        assert "authority" in result.score_breakdown
        assert "coverage" in result.score_breakdown

        # 所有分数应在 [0, 1]
        for score in result.score_breakdown.values():
            assert 0 <= score <= 1


def test_reranker_freshness_score():
    """测试新鲜度评分"""
    reranker = MultiDimensionalReranker()

    current_time = time.time()

    # 新文档（1 小时前）
    fresh_score = reranker._compute_freshness_score(
        doc_timestamp=current_time - 3600,
        current_time=current_time,
        half_life_hours=24,
    )
    assert 0.9 < fresh_score <= 1.0

    # 旧文档（48 小时前）
    old_score = reranker._compute_freshness_score(
        doc_timestamp=current_time - 48 * 3600,
        current_time=current_time,
        half_life_hours=24,
    )
    assert 0.2 < old_score < 0.3  # 2^(-48/24) = 0.25

    # 非常旧的文档
    very_old_score = reranker._compute_freshness_score(
        doc_timestamp=current_time - 1000 * 3600,
        current_time=current_time,
        half_life_hours=24,
    )
    assert very_old_score < 0.01  # 接近 0


def test_reranker_diversity_score():
    """测试多样性评分"""
    reranker = MultiDimensionalReranker()

    cluster_map = {
        "doc_1": 0,
        "doc_2": 0,
        "doc_3": 1,
    }

    # 在 cluster 中的文档
    score_in_cluster = reranker._compute_diversity_score("doc_1", cluster_map)
    assert score_in_cluster == 0.6

    # 噪音点（不在 cluster 中）
    score_noise = reranker._compute_diversity_score("doc_999", cluster_map)
    assert score_noise == 0.8

    # 没有聚类信息
    score_no_cluster = reranker._compute_diversity_score("doc_1", {})
    assert score_no_cluster == 0.5


def test_reranker_authority_score():
    """测试权威性评分"""
    reranker = MultiDimensionalReranker()

    # 高权威性（高引用 + 高中心性）
    high_auth_metadata = {
        "citations": 100,
        "centrality": 0.9,
        "source": "authoritative",
    }
    high_score = reranker._compute_authority_score(high_auth_metadata)
    assert high_score >= 0.9

    # 低权威性
    low_auth_metadata = {
        "citations": 0,
        "centrality": 0.0,
        "source": "general",
    }
    low_score = reranker._compute_authority_score(low_auth_metadata)
    assert low_score == 0.5  # 只有来源分数


def test_reranker_coverage_score():
    """测试覆盖度评分"""
    reranker = MultiDimensionalReranker()

    query_text = "machine learning deep neural networks"

    # 高覆盖度
    high_coverage_doc = "Machine learning and deep neural networks are widely used"
    high_score = reranker._compute_coverage_score(query_text, high_coverage_doc)
    assert high_score >= 0.75  # 覆盖 3/4 关键词

    # 低覆盖度
    low_coverage_doc = "This document talks about something completely different"
    low_score = reranker._compute_coverage_score(query_text, low_coverage_doc)
    assert low_score < 0.3


def test_reranker_performance(sample_joined_event, sample_vdb_results):
    """测试重排序性能（20个文档 < 30ms）"""
    reranker = MultiDimensionalReranker(top_k=15)

    data = (sample_joined_event, sample_vdb_results, None)

    start_time = time.perf_counter()
    results = reranker.execute(data)
    elapsed_ms = (time.perf_counter() - start_time) * 1000

    print(f"重排序 20 个文档耗时: {elapsed_ms:.2f}ms")

    assert len(results) == 15
    assert elapsed_ms < 30  # 性能要求


# ============================================================================
# MMRDiversityFilter Tests
# ============================================================================


def test_mmr_filter_initialization():
    """测试 MMR 过滤器初始化"""
    # 默认参数
    mmr_filter = MMRDiversityFilter()
    assert mmr_filter.lambda_param == 0.7
    assert mmr_filter.top_k == 10

    # 自定义参数
    mmr_filter = MMRDiversityFilter(lambda_param=0.5, top_k=5)
    assert mmr_filter.lambda_param == 0.5
    assert mmr_filter.top_k == 5


def test_mmr_filter_invalid_lambda():
    """测试无效 lambda 参数"""
    with pytest.raises(ValueError, match="lambda_param 应在"):
        MMRDiversityFilter(lambda_param=1.5)

    with pytest.raises(ValueError, match="lambda_param 应在"):
        MMRDiversityFilter(lambda_param=-0.1)


def test_mmr_filter_empty_results(sample_query):
    """测试空结果处理"""
    mmr_filter = MMRDiversityFilter()

    data = (sample_query, [])
    results = mmr_filter.execute(data)

    assert results == []


def test_mmr_filter_few_results(sample_query):
    """测试结果数少于 top_k"""
    mmr_filter = MMRDiversityFilter(top_k=10)

    reranking_results = [
        RerankingResult(
            doc_id=f"doc_{i}",
            content=f"Content {i}",
            final_score=0.9 - i * 0.1,
            score_breakdown={"semantic": 0.9 - i * 0.1},
            rank=i + 1,
        )
        for i in range(5)
    ]

    data = (sample_query, reranking_results)
    results = mmr_filter.execute(data)

    # 结果数 < top_k，直接返回
    assert len(results) == 5
    assert results == reranking_results


def test_mmr_filter_no_embeddings(sample_query):
    """测试没有 embedding 的情况"""
    query_no_emb = QueryEvent(
        query_id="q1",
        query_text="test query",
        query_type="factual",
        category="general",
        timestamp=time.time(),
        embedding=None,  # 没有 embedding
    )

    mmr_filter = MMRDiversityFilter(top_k=5)

    reranking_results = [
        RerankingResult(
            doc_id=f"doc_{i}",
            content=f"Content {i}",
            final_score=0.9 - i * 0.05,
            score_breakdown={"semantic": 0.9 - i * 0.05},
            rank=i + 1,
        )
        for i in range(10)
    ]

    data = (query_no_emb, reranking_results)
    results = mmr_filter.execute(data)

    # 没有 embedding，返回前 top_k
    assert len(results) == 5


def test_mmr_filter_basic_functionality(sample_query):
    """测试 MMR 基本功能"""
    mmr_filter = MMRDiversityFilter(lambda_param=0.7, top_k=5, enable_profiling=True)

    # 创建有 embedding 的重排序结果
    reranking_results = []
    for i in range(10):
        # 创建相似的 embeddings（通过添加小噪声）
        base_embedding = np.random.randn(128)
        embedding = base_embedding + np.random.randn(128) * 0.1

        reranking_results.append(
            RerankingResult(
                doc_id=f"doc_{i}",
                content=f"Content {i}",
                final_score=0.9 - i * 0.05,
                score_breakdown={
                    "semantic": 0.9 - i * 0.05,
                    "embedding": embedding.tolist(),  # 添加 embedding
                },
                rank=i + 1,
            )
        )

    data = (sample_query, reranking_results)
    results = mmr_filter.execute(data)

    # 检查结果数量
    assert len(results) == 5

    # 检查 rank 更新
    for i, result in enumerate(results):
        assert result.rank == i + 1


def test_mmr_filter_diversity_trade_off(sample_query):
    """测试 MMR lambda 参数的多样性权衡"""
    # 创建重排序结果
    reranking_results = []
    for i in range(10):
        embedding = np.random.randn(128)
        reranking_results.append(
            RerankingResult(
                doc_id=f"doc_{i}",
                content=f"Content {i}",
                final_score=0.9 - i * 0.05,
                score_breakdown={
                    "semantic": 0.9 - i * 0.05,
                    "embedding": embedding.tolist(),
                },
                rank=i + 1,
            )
        )

    # 高 lambda（更重视相关性）
    mmr_high_lambda = MMRDiversityFilter(lambda_param=0.9, top_k=5)
    results_high = mmr_high_lambda.execute((sample_query, reranking_results))

    # 低 lambda（更重视多样性）
    mmr_low_lambda = MMRDiversityFilter(lambda_param=0.3, top_k=5)
    results_low = mmr_low_lambda.execute((sample_query, reranking_results))

    # 两者结果应该不同（低 lambda 会选择更多样的文档）
    assert len(results_high) == 5
    assert len(results_low) == 5

    # 高 lambda 应更接近原始排序
    high_ids = [r.doc_id for r in results_high]
    low_ids = [r.doc_id for r in results_low]

    # 打印结果用于调试
    print(f"High lambda: {high_ids}")
    print(f"Low lambda: {low_ids}")


def test_mmr_filter_performance(sample_query):
    """测试 MMR 性能"""
    mmr_filter = MMRDiversityFilter(top_k=10)

    # 创建 20 个结果
    reranking_results = []
    for i in range(20):
        embedding = np.random.randn(128)
        reranking_results.append(
            RerankingResult(
                doc_id=f"doc_{i}",
                content=f"Content {i}",
                final_score=0.9 - i * 0.03,
                score_breakdown={
                    "semantic": 0.9 - i * 0.03,
                    "embedding": embedding.tolist(),
                },
                rank=i + 1,
            )
        )

    data = (sample_query, reranking_results)

    start_time = time.perf_counter()
    results = mmr_filter.execute(data)
    elapsed_ms = (time.perf_counter() - start_time) * 1000

    print(f"MMR 过滤 20 → 10 耗时: {elapsed_ms:.2f}ms")

    assert len(results) == 10
    assert elapsed_ms < 50  # 宽松的性能要求


# ============================================================================
# Visualization Tests
# ============================================================================


def test_visualize_score_breakdown_empty():
    """测试空结果可视化"""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / "empty.png"

        # 应该打印警告但不崩溃
        visualize_score_breakdown([], str(output_path))

        # 文件不应该创建
        assert not output_path.exists()


def test_visualize_score_breakdown_basic():
    """测试基本可视化功能"""
    # 创建示例结果
    reranking_results = []
    for i in range(5):
        reranking_results.append(
            RerankingResult(
                doc_id=f"doc_{i}",
                content=f"Content {i}",
                final_score=0.8 - i * 0.1,
                score_breakdown={
                    "semantic": 0.9 - i * 0.1,
                    "freshness": 0.7 + i * 0.05,
                    "diversity": 0.6,
                    "authority": 0.5 + i * 0.08,
                    "coverage": 0.75 - i * 0.05,
                },
                rank=i + 1,
            )
        )

    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / "score_breakdown.png"

        # 可视化
        visualize_score_breakdown(reranking_results, str(output_path))

        # 检查文件是否创建（如果 matplotlib 可用）
        try:
            import matplotlib

            assert output_path.exists()
            assert output_path.stat().st_size > 0
        except ImportError:
            # matplotlib 不可用，跳过检查
            pass


def test_visualize_score_distribution_basic():
    """测试评分分布可视化"""
    from ..reranking import visualize_score_distribution

    # 创建示例结果
    reranking_results = []
    for i in range(10):
        reranking_results.append(
            RerankingResult(
                doc_id=f"doc_{i}",
                content=f"Content {i}",
                final_score=0.8 - i * 0.05,
                score_breakdown={
                    "semantic": 0.9 - i * 0.05,
                    "freshness": 0.6 + i * 0.03,
                    "diversity": 0.7,
                    "authority": 0.5 + i * 0.04,
                    "coverage": 0.8 - i * 0.04,
                },
                rank=i + 1,
            )
        )

    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / "score_distribution.png"

        # 可视化
        visualize_score_distribution(reranking_results, str(output_path))

        # 检查文件是否创建（如果 matplotlib 可用）
        try:
            import matplotlib

            assert output_path.exists()
            assert output_path.stat().st_size > 0
        except ImportError:
            pass


# ============================================================================
# Integration Tests
# ============================================================================


def test_reranker_mmr_integration(
    sample_joined_event, sample_vdb_results, sample_clustering_info, sample_query
):
    """测试重排序 + MMR 的集成"""
    # 第一步：重排序
    reranker = MultiDimensionalReranker(top_k=15)
    reranked = reranker.execute((sample_joined_event, sample_vdb_results, sample_clustering_info))

    assert len(reranked) == 15

    # 第二步：MMR 多样性过滤
    # 为结果添加 embedding
    for result in reranked:
        result.score_breakdown["embedding"] = np.random.randn(128).tolist()

    mmr_filter = MMRDiversityFilter(lambda_param=0.7, top_k=10)
    final_results = mmr_filter.execute((sample_query, reranked))

    assert len(final_results) == 10

    # 检查 rank 连续性
    for i, result in enumerate(final_results):
        assert result.rank == i + 1


def test_end_to_end_reranking_pipeline(
    sample_joined_event, sample_vdb_results, sample_clustering_info, sample_query
):
    """测试完整的重排序流程"""
    # 1. 重排序（5 维评分）
    reranker = MultiDimensionalReranker(
        score_weights={
            "semantic": 0.35,
            "freshness": 0.25,
            "diversity": 0.15,
            "authority": 0.15,
            "coverage": 0.10,
        },
        top_k=12,
        enable_profiling=True,
    )

    reranked = reranker.execute((sample_joined_event, sample_vdb_results, sample_clustering_info))

    assert len(reranked) == 12
    print("\n重排序后 Top-3:")
    for result in reranked[:3]:
        print(f"  Rank {result.rank}: {result.doc_id} (Score: {result.final_score:.4f})")
        print(f"    Breakdown: {result.score_breakdown}")

    # 2. 添加 embedding
    for result in reranked:
        result.score_breakdown["embedding"] = np.random.randn(128).tolist()

    # 3. MMR 多样性过滤
    mmr_filter = MMRDiversityFilter(lambda_param=0.6, top_k=8, enable_profiling=True)
    final_results = mmr_filter.execute((sample_query, reranked))

    assert len(final_results) == 8
    print("\nMMR 过滤后 Top-3:")
    for result in final_results[:3]:
        print(f"  Rank {result.rank}: {result.doc_id} (Score: {result.final_score:.4f})")

    # 4. 可视化（可选）
    with tempfile.TemporaryDirectory() as tmpdir:
        radar_path = Path(tmpdir) / "radar.png"
        dist_path = Path(tmpdir) / "distribution.png"

        visualize_score_breakdown(final_results, str(radar_path))
        visualize_score_distribution(final_results, str(dist_path))

        print("\n可视化文件:")
        print(f"  雷达图: {radar_path}")
        print(f"  分布图: {dist_path}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
