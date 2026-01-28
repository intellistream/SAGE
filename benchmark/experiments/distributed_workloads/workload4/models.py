"""
Workload 4 数据模型

定义整个工作流中流转的所有数据结构。
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class QueryEvent:
    """查询事件（双流之一）
    
    表示一个查询请求，包含查询文本、类型、类别等信息。
    """
    query_id: str
    query_text: str
    query_type: str  # "factual" | "analytical" | "exploratory"
    category: str    # "finance" | "healthcare" | "technology" | "general"
    timestamp: float
    embedding: list[float] | None = None
    
    def __post_init__(self):
        """验证字段合法性"""
        assert self.query_type in ["factual", "analytical", "exploratory"], \
            f"Invalid query_type: {self.query_type}"
        assert self.category in ["finance", "healthcare", "technology", "general"], \
            f"Invalid category: {self.category}"


@dataclass
class DocumentEvent:
    """文档事件（双流之二）
    
    表示一个文档片段，用于与查询进行语义匹配。
    """
    doc_id: str
    doc_text: str
    doc_category: str
    timestamp: float
    embedding: list[float] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class JoinedEvent:
    """Join 后的事件
    
    表示查询与文档的语义匹配结果。
    """
    joined_id: str  # f"{query_id}_{join_timestamp}"
    query: QueryEvent
    matched_docs: list[DocumentEvent]
    join_timestamp: float
    semantic_score: float  # Join 相似度
    
    # 扩展字段（后续算子填充）
    expanded_queries: list[str] = field(default_factory=list)
    entities: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)


@dataclass
class VDBRetrievalResult:
    """VDB 检索结果
    
    表示从向量数据库检索到的文档。
    """
    doc_id: str
    content: str
    score: float
    source: str  # "vdb1" | "vdb2"
    stage: int   # 1-4 (哪个 stage)
    query_id: str  # 关联的查询 ID（用于 join）
    metadata: dict[str, Any] = field(default_factory=dict)
    
    # 后续算子添加的字段
    filtered: bool = False
    rerank_score: float | None = None


@dataclass
class GraphMemoryResult:
    """图遍历结果
    
    表示从图记忆系统遍历得到的节点。
    """
    node_id: str
    content: str
    depth: int
    path: list[str]  # 遍历路径
    relevance_score: float
    node_type: str = "memory"  # "memory" | "entity" | "concept"
    
    def path_str(self) -> str:
        """返回路径字符串表示"""
        return " -> ".join(self.path)


@dataclass
class GraphEnrichedEvent:
    """携带 Graph 检索结果的事件
    
    用于在 graph → VDB 串行流中传递原始查询 + graph 结果。
    """
    query: QueryEvent  # 原始查询（包含 embedding）
    joined_event: JoinedEvent  # 原始 join 事件（可能后续需要）
    graph_results: list[GraphMemoryResult]  # Graph 检索结果
    
    @property
    def query_id(self) -> str:
        return self.query.query_id


@dataclass
class VDBResultsWrapper:
    """VDB 检索结果的包装器
    
    用于在流中传递一组 VDB 检索结果，同时保留 query 信息用于 join。
    """
    query_id: str  # 查询 ID（用于 join）
    vdb_name: str  # "vdb1" | "vdb2"
    results: list[VDBRetrievalResult]  # 检索结果列表
    stage: int  # 检索阶段
    source_event: GraphEnrichedEvent | None = None  # 保留原始 GraphEnrichedEvent


@dataclass
class ClusteringResult:
    """聚类去重结果
    
    表示聚类算法（如 DBSCAN）的输出。
    """
    cluster_id: int
    representative_doc_id: str
    cluster_docs: list[str]  # 簇内所有文档ID
    cluster_size: int
    centroid: list[float] | None = None
    similarity_matrix: list[list[float]] | None = None  # 簇内相似度矩阵


@dataclass
class RerankingResult:
    """重排序结果
    
    表示多维度评分后的最终排序结果。
    """
    doc_id: str
    content: str
    final_score: float
    score_breakdown: dict[str, float] = field(default_factory=dict)  # 5维评分详情
    rank: int = 0
    source_info: dict[str, Any] = field(default_factory=dict)  # 来源信息（VDB1/VDB2/Memory）
    
    def get_dimension_score(self, dimension: str) -> float:
        """获取指定维度的分数"""
        return self.score_breakdown.get(dimension, 0.0)


@dataclass
class BatchContext:
    """批处理上下文
    
    表示批量聚合的一组任务。
    """
    batch_id: str
    batch_type: str  # "category" | "global"
    items: list[JoinedEvent]
    batch_timestamp: float
    batch_size: int
    category: str | None = None  # 仅 category batch 有值
    
    def __post_init__(self):
        """验证批次大小"""
        assert len(self.items) == self.batch_size, \
            f"Batch size mismatch: {len(self.items)} != {self.batch_size}"
        if self.batch_type == "category":
            assert self.category is not None, "Category batch must have category"


@dataclass
class Workload4Metrics:
    """Workload 4 指标
    
    记录单个任务的端到端性能指标。
    """
    task_id: str
    query_id: str
    
    # === 时间戳 ===
    query_arrival_time: float = 0.0
    doc_arrival_time: float = 0.0
    join_time: float = 0.0
    vdb1_start_time: float = 0.0
    vdb1_end_time: float = 0.0
    vdb2_start_time: float = 0.0
    vdb2_end_time: float = 0.0
    graph_start_time: float = 0.0
    graph_end_time: float = 0.0
    clustering_time: float = 0.0
    reranking_time: float = 0.0
    batch_time: float = 0.0
    generation_time: float = 0.0
    end_to_end_time: float = 0.0
    
    # === 中间结果统计 ===
    join_matched_docs: int = 0
    vdb1_results: int = 0
    vdb2_results: int = 0
    graph_nodes_visited: int = 0
    clusters_found: int = 0
    duplicates_removed: int = 0
    final_top_k: int = 0
    
    # === 资源统计 ===
    cpu_time_ms: float = 0.0
    memory_peak_mb: float = 0.0
    
    # === 质量指标 ===
    semantic_join_score: float = 0.0
    final_rerank_score: float = 0.0
    diversity_score: float = 0.0
    
    def compute_latencies(self) -> dict[str, float]:
        """计算各阶段延迟"""
        return {
            "join_latency": self.join_time - self.query_arrival_time if self.join_time > 0 else 0,
            "vdb1_latency": self.vdb1_end_time - self.vdb1_start_time if self.vdb1_end_time > 0 else 0,
            "vdb2_latency": self.vdb2_end_time - self.vdb2_start_time if self.vdb2_end_time > 0 else 0,
            "graph_latency": self.graph_end_time - self.graph_start_time if self.graph_end_time > 0 else 0,
            "e2e_latency": self.end_to_end_time - self.query_arrival_time if self.end_to_end_time > 0 else 0,
        }
    
    def to_dict(self) -> dict[str, Any]:
        """转换为字典（用于日志输出）"""
        latencies = self.compute_latencies()
        return {
            "task_id": self.task_id,
            "query_id": self.query_id,
            **latencies,
            "join_matched_docs": self.join_matched_docs,
            "vdb1_results": self.vdb1_results,
            "vdb2_results": self.vdb2_results,
            "graph_nodes_visited": self.graph_nodes_visited,
            "clusters_found": self.clusters_found,
            "duplicates_removed": self.duplicates_removed,
            "final_top_k": self.final_top_k,
            "cpu_time_ms": self.cpu_time_ms,
            "memory_peak_mb": self.memory_peak_mb,
        }


@dataclass
class GenerationResult:
    """生成结果
    
    表示 LLM 生成的最终响应。
    """
    task_id: str
    query_id: str
    response: str
    references: list[dict[str, Any]] = field(default_factory=list)
    quality_score: float = 0.0
    token_count: int = 0
    generation_time_ms: float = 0.0
    
    def add_reference(self, doc_id: str, source: str, snippet: str):
        """添加引用文档"""
        self.references.append({
            "doc_id": doc_id,
            "source": source,
            "snippet": snippet[:200],  # 截取前200字符
        })


@dataclass
class AggregateMetrics:
    """聚合指标
    
    表示多个任务的统计结果。
    """
    num_tasks: int = 0
    
    # 延迟统计
    avg_e2e_latency: float = 0.0
    p50_e2e_latency: float = 0.0
    p95_e2e_latency: float = 0.0
    p99_e2e_latency: float = 0.0
    
    avg_join_latency: float = 0.0
    avg_vdb_latency: float = 0.0
    avg_graph_latency: float = 0.0
    
    # 吞吐量统计
    throughput_qps: float = 0.0
    
    # CPU 统计
    avg_cpu_utilization: float = 0.0
    max_cpu_utilization: float = 0.0
    
    # 内存统计
    avg_memory_mb: float = 0.0
    max_memory_mb: float = 0.0
    
    # 中间结果统计
    avg_join_docs: float = 0.0
    avg_vdb_results: float = 0.0
    avg_duplicates_removed: float = 0.0
    
    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "num_tasks": self.num_tasks,
            "throughput_qps": self.throughput_qps,
            "latency": {
                "avg_e2e": self.avg_e2e_latency,
                "p50_e2e": self.p50_e2e_latency,
                "p95_e2e": self.p95_e2e_latency,
                "p99_e2e": self.p99_e2e_latency,
                "avg_join": self.avg_join_latency,
                "avg_vdb": self.avg_vdb_latency,
                "avg_graph": self.avg_graph_latency,
            },
            "cpu": {
                "avg": self.avg_cpu_utilization,
                "max": self.max_cpu_utilization,
            },
            "memory": {
                "avg_mb": self.avg_memory_mb,
                "max_mb": self.max_memory_mb,
            },
            "intermediate": {
                "avg_join_docs": self.avg_join_docs,
                "avg_vdb_results": self.avg_vdb_results,
                "avg_duplicates_removed": self.avg_duplicates_removed,
            }
        }
