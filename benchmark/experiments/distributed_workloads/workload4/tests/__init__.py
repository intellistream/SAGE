"""
测试 Workload 4 数据模型和配置
"""

import sys
import time
from pathlib import Path

# 添加父目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from workload4.config import (
    Workload4Config,
    get_cpu_optimized_config,
    get_default_config,
    get_extreme_config,
    get_light_config,
)
from workload4.models import (
    AggregateMetrics,
    BatchContext,
    ClusteringResult,
    DocumentEvent,
    GenerationResult,
    GraphMemoryResult,
    JoinedEvent,
    QueryEvent,
    RerankingResult,
    VDBRetrievalResult,
    Workload4Metrics,
)


def test_query_event():
    """测试 QueryEvent"""
    print("Testing QueryEvent...")

    query = QueryEvent(
        query_id="q001",
        query_text="What is the impact of AI on finance?",
        query_type="analytical",
        category="finance",
        timestamp=time.time(),
        embedding=[0.1] * 1024,
    )

    assert query.query_id == "q001"
    assert query.query_type == "analytical"
    assert query.category == "finance"
    assert len(query.embedding) == 1024
    print("✓ QueryEvent passed")


def test_document_event():
    """测试 DocumentEvent"""
    print("Testing DocumentEvent...")

    doc = DocumentEvent(
        doc_id="d001",
        doc_text="AI is transforming the financial industry...",
        doc_category="finance",
        timestamp=time.time(),
        embedding=[0.2] * 1024,
        metadata={"source": "paper", "year": 2024},
    )

    assert doc.doc_id == "d001"
    assert doc.metadata["source"] == "paper"
    print("✓ DocumentEvent passed")


def test_joined_event():
    """测试 JoinedEvent"""
    print("Testing JoinedEvent...")

    query = QueryEvent(
        query_id="q001",
        query_text="Test query",
        query_type="factual",
        category="general",
        timestamp=time.time(),
    )

    doc = DocumentEvent(
        doc_id="d001",
        doc_text="Test document",
        doc_category="general",
        timestamp=time.time(),
    )

    joined = JoinedEvent(
        joined_id="q001_1234567890.123",
        query=query,
        matched_docs=[doc],
        join_timestamp=time.time(),
        semantic_score=0.85,
    )

    assert joined.joined_id.startswith("q001")
    assert joined.semantic_score == 0.85
    assert len(joined.matched_docs) == 1
    print("✓ JoinedEvent passed")


def test_vdb_retrieval_result():
    """测试 VDBRetrievalResult"""
    print("Testing VDBRetrievalResult...")

    result = VDBRetrievalResult(
        doc_id="vdb001",
        content="Retrieved content from VDB1",
        score=0.92,
        source="vdb1",
        stage=1,
        metadata={"index_type": "HNSW"},
    )

    assert result.source == "vdb1"
    assert result.stage == 1
    assert result.score == 0.92
    print("✓ VDBRetrievalResult passed")


def test_graph_memory_result():
    """测试 GraphMemoryResult"""
    print("Testing GraphMemoryResult...")

    graph_result = GraphMemoryResult(
        node_id="node_123",
        content="Memory node content",
        depth=2,
        path=["root", "parent", "node_123"],
        relevance_score=0.78,
    )

    assert graph_result.depth == 2
    assert len(graph_result.path) == 3
    assert graph_result.path_str() == "root -> parent -> node_123"
    print("✓ GraphMemoryResult passed")


def test_clustering_result():
    """测试 ClusteringResult"""
    print("Testing ClusteringResult...")

    cluster = ClusteringResult(
        cluster_id=1,
        representative_doc_id="doc_123",
        cluster_docs=["doc_123", "doc_456", "doc_789"],
        cluster_size=3,
        centroid=[0.5] * 1024,
    )

    assert cluster.cluster_size == 3
    assert len(cluster.cluster_docs) == 3
    print("✓ ClusteringResult passed")


def test_reranking_result():
    """测试 RerankingResult"""
    print("Testing RerankingResult...")

    rerank = RerankingResult(
        doc_id="doc_001",
        content="Reranked document",
        final_score=0.88,
        score_breakdown={
            "semantic": 0.30,
            "freshness": 0.18,
            "diversity": 0.20,
            "authority": 0.10,
            "coverage": 0.10,
        },
        rank=1,
    )

    assert rerank.final_score == 0.88
    assert rerank.get_dimension_score("semantic") == 0.30
    assert rerank.rank == 1
    print("✓ RerankingResult passed")


def test_batch_context():
    """测试 BatchContext"""
    print("Testing BatchContext...")

    query = QueryEvent(
        query_id="q001",
        query_text="Test",
        query_type="factual",
        category="finance",
        timestamp=time.time(),
    )

    doc = DocumentEvent(
        doc_id="d001",
        doc_text="Test",
        doc_category="finance",
        timestamp=time.time(),
    )

    joined = JoinedEvent(
        joined_id="test_001",
        query=query,
        matched_docs=[doc],
        join_timestamp=time.time(),
        semantic_score=0.8,
    )

    batch = BatchContext(
        batch_id="batch_001",
        batch_type="category",
        items=[joined] * 5,
        batch_timestamp=time.time(),
        batch_size=5,
        category="finance",
    )

    assert batch.batch_size == 5
    assert len(batch.items) == 5
    assert batch.category == "finance"
    print("✓ BatchContext passed")


def test_workload4_metrics():
    """测试 Workload4Metrics"""
    print("Testing Workload4Metrics...")

    metrics = Workload4Metrics(
        task_id="task_001",
        query_id="q001",
    )

    # 填充时间戳
    metrics.query_arrival_time = 1000.0
    metrics.join_time = 1001.0
    metrics.vdb1_start_time = 1001.5
    metrics.vdb1_end_time = 1002.0
    metrics.end_to_end_time = 1005.0

    # 填充统计
    metrics.join_matched_docs = 5
    metrics.vdb1_results = 20
    metrics.vdb2_results = 20

    # 计算延迟
    latencies = metrics.compute_latencies()
    assert latencies["join_latency"] == 1.0
    assert latencies["vdb1_latency"] == 0.5
    assert latencies["e2e_latency"] == 5.0

    # 转为字典
    metrics_dict = metrics.to_dict()
    assert metrics_dict["task_id"] == "task_001"
    print("✓ Workload4Metrics passed")


def test_generation_result():
    """测试 GenerationResult"""
    print("Testing GenerationResult...")

    result = GenerationResult(
        task_id="task_001",
        query_id="q001",
        response="This is a generated response.",
        quality_score=0.85,
    )

    result.add_reference("doc_001", "vdb1", "Reference snippet from VDB1...")
    result.add_reference("doc_002", "memory", "Reference snippet from memory...")

    assert len(result.references) == 2
    assert result.references[0]["doc_id"] == "doc_001"
    print("✓ GenerationResult passed")


def test_workload4_config():
    """测试 Workload4Config"""
    print("Testing Workload4Config...")

    # 默认配置
    config = get_default_config()
    assert config.query_qps == 40.0
    assert config.doc_qps == 25.0
    assert config.join_window_seconds == 60
    assert config.validate()

    # 轻量配置
    light_config = get_light_config()
    assert light_config.query_qps == 20.0
    assert light_config.duration == 300

    # 极限配置
    extreme_config = get_extreme_config()
    assert extreme_config.query_qps == 50.0
    assert extreme_config.join_window_seconds == 90

    # CPU优化配置
    cpu_config = get_cpu_optimized_config()
    assert cpu_config.join_parallelism == 32
    assert cpu_config.embedding_batch_size == 128

    print("✓ Workload4Config passed")


def test_config_serialization():
    """测试配置序列化"""
    print("Testing config serialization...")

    config = get_default_config()
    config_dict = config.to_dict()

    assert config_dict["query_qps"] == 40.0
    assert config_dict["llm_model"] == "Qwen/Qwen2.5-3B-Instruct"

    # 从字典恢复
    restored_config = Workload4Config.from_dict(config_dict)
    assert restored_config.query_qps == config.query_qps

    print("✓ Config serialization passed")


def test_performance_targets():
    """测试性能目标"""
    print("Testing performance targets...")

    config = get_default_config()

    targets = config.get_performance_target()
    assert targets["cpu_utilization"] == "85-95%"
    assert targets["p50_latency_ms"] == 1200

    hw_req = config.get_hardware_requirements()
    assert hw_req["min_nodes"] == 8
    assert hw_req["total_cpu_cores"] == 128

    print("✓ Performance targets passed")


def main():
    """运行所有测试"""
    print("=" * 60)
    print("Workload 4 - Task 1: 数据模型和配置测试")
    print("=" * 60)
    print()

    try:
        test_query_event()
        test_document_event()
        test_joined_event()
        test_vdb_retrieval_result()
        test_graph_memory_result()
        test_clustering_result()
        test_reranking_result()
        test_batch_context()
        test_workload4_metrics()
        test_generation_result()
        test_workload4_config()
        test_config_serialization()
        test_performance_targets()

        print()
        print("=" * 60)
        print("✅ 所有测试通过！Task 1 完成")
        print("=" * 60)

    except AssertionError as e:
        print(f"\n❌ 测试失败: {e}")
        raise
    except Exception as e:
        print(f"\n❌ 测试错误: {e}")
        raise


if __name__ == "__main__":
    main()
