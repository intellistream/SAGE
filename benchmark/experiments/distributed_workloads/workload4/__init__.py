"""
Workload 4: 极致复杂的分布式CPU密集型工作流

架构特点:
- 双流输入（Query + Document）
- 60s 大窗口 Semantic Join
- 双路 4-stage VDB 检索分支
- DBSCAN 聚类去重
- 图遍历内存检索
- 5维评分重排序
- 双层 Batch 聚合
- MMR 多样性过滤

预期性能:
- CPU Utilization: 85-95%
- QPS: Query 40 + Doc 25
- P50 Latency: 1000-1500ms
- P99 Latency: 2500-3500ms
"""

from .models import (
    QueryEvent,
    DocumentEvent,
    JoinedEvent,
    VDBRetrievalResult,
    GraphMemoryResult,
    GraphEnrichedEvent,
    VDBResultsWrapper,
    ClusteringResult,
    RerankingResult,
    BatchContext,
    Workload4Metrics,
)

from .config import Workload4Config

from .sources import (
    Workload4QuerySource,
    Workload4DocumentSource,
    EmbeddingPrecompute,
    BatchedEmbeddingPrecompute,
    create_query_source,
    create_document_source,
    create_embedding_precompute,
)

from .generation import (
    BatchLLMGenerator,
    Workload4MetricsSink,
    create_mock_batch_context,
)

from .clustering import (
    DBSCANClusteringOperator,
    SimilarityDeduplicator,
    visualize_clusters,
    analyze_clustering_quality,
)

from .reranking import (
    MultiDimensionalReranker,
    MMRDiversityFilter,
    visualize_score_breakdown,
    visualize_score_distribution,
)

from .pipeline import (
    Workload4Pipeline,
    register_all_services,
    register_embedding_service,
    register_vdb_services,
    register_graph_memory_service,
    register_llm_service,
    create_workload4_pipeline,
    run_workload4,
)

# 🔧 临时添加：单源测试用工具
from .mappers import QueryToJoinedMapper

__all__ = [
    # 数据模型
    "QueryEvent",
    "DocumentEvent",
    "JoinedEvent",
    "VDBRetrievalResult",
    "GraphMemoryResult",
    "GraphEnrichedEvent",
    "VDBResultsWrapper",
    "ClusteringResult",
    "RerankingResult",
    "BatchContext",
    "Workload4Metrics",
    # 配置
    "Workload4Config",
    # 源算子（Task 2）
    "Workload4QuerySource",
    "Workload4DocumentSource",
    "EmbeddingPrecompute",
    "BatchedEmbeddingPrecompute",
    "create_query_source",
    "create_document_source",
    "create_embedding_precompute",
    # 生成和 Sink
    "BatchLLMGenerator",
    "Workload4MetricsSink",
    "create_mock_batch_context",
    # 聚类去重
    "DBSCANClusteringOperator",
    "SimilarityDeduplicator",
    "visualize_clusters",
    "analyze_clustering_quality",
    # 重排序
    "MultiDimensionalReranker",
    "MMRDiversityFilter",
    "visualize_score_breakdown",
    "visualize_score_distribution",
    # Pipeline (Task 10)
    "Workload4Pipeline",
    "register_all_services",
    "register_embedding_service",
    "register_vdb_services",
    "register_graph_memory_service",
    "register_llm_service",
    "create_workload4_pipeline",
    "run_workload4",
    # 🔧 临时工具
    "QueryToJoinedMapper",
]
