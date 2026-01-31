"""
Workload 4 配置管理

定义 Workload 4 的所有可配置参数。
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class Workload4Config:
    """Workload 4 配置

    包含双流源、Join、VDB、图遍历、聚类、重排序、批处理、LLM等所有配置。
    """

    # === 基础配置 ===
    num_tasks: int = 100
    duration: int = 1200  # 20分钟
    use_remote: bool = True
    num_nodes: int = 8

    # === 双流配置 ===
    query_qps: float = 40.0  # 查询流QPS
    doc_qps: float = 25.0  # 文档流QPS

    # 查询类型分布（三种类型的比例）
    query_type_distribution: dict[str, float] = field(
        default_factory=lambda: {
            "factual": 0.4,  # 事实性查询 40%
            "analytical": 0.35,  # 分析性查询 35%
            "exploratory": 0.25,  # 探索性查询 25%
        }
    )

    # 类别分布（四个领域的比例）
    category_distribution: dict[str, float] = field(
        default_factory=lambda: {
            "finance": 0.30,
            "healthcare": 0.25,
            "technology": 0.25,
            "general": 0.20,
        }
    )

    # === Semantic Join 配置 ===
    join_window_seconds: int = 60  # 窗口大小
    join_threshold: float = 0.70  # 相似度阈值
    join_parallelism: int = 16  # Join并行度
    join_max_matches: int = 8  # 每个query最多匹配的doc数量

    # === VDB 检索配置 ===
    # VDB1: 专业知识库（4节点）
    vdb1_backend: str = "SageVDB"
    vdb1_corpus_size: int = 100_000_000  # 100M docs
    vdb1_index_type: str = "HNSW"
    vdb1_ef_search: int = 200
    vdb1_top_k: int = 25
    vdb1_nodes: list[int] = field(default_factory=lambda: [1, 2, 3, 4])

    # VDB2: 通用知识库（4节点）
    vdb2_backend: str = "SageVDB"
    vdb2_corpus_size: int = 500_000_000  # 500M docs
    vdb2_index_type: str = "IVF_HNSW"
    vdb2_nprobe: int = 50
    vdb2_top_k: int = 25
    vdb2_nodes: list[int] = field(default_factory=lambda: [5, 6, 7, 8])

    # 通用VDB配置
    vdb_filter_threshold: float = 0.6
    vdb_parallelism: int = 8

    # === 图遍历配置 ===
    graph_max_depth: int = 3
    graph_max_nodes: int = 200
    graph_bfs_beam_width: int = 10
    graph_edge_weight_threshold: float = 0.5
    graph_enable_pruning: bool = True

    # === 聚类去重配置 ===
    clustering_algorithm: str = "dbscan"  # "dbscan" | "hierarchical"

    # DBSCAN 参数
    dbscan_eps: float = 0.15
    dbscan_min_samples: int = 2
    dbscan_metric: str = "cosine"

    # 去重参数
    dedup_similarity_threshold: float = 0.95
    dedup_use_simhash: bool = True  # 启用 SimHash 粗筛
    dedup_simhash_bits: int = 64

    # === 重排序配置 ===
    rerank_top_k: int = 15

    # 5维度评分权重
    rerank_score_weights: dict[str, float] = field(
        default_factory=lambda: {
            "semantic": 0.30,  # 语义相似度
            "freshness": 0.20,  # 新鲜度（基于时间戳）
            "diversity": 0.20,  # 多样性（来源多样性）
            "authority": 0.15,  # 权威性（基于source）
            "coverage": 0.15,  # 覆盖度（关键词覆盖）
        }
    )

    # BM25 参数
    bm25_k1: float = 1.5
    bm25_b: float = 0.75

    # MMR 多样性过滤
    mmr_lambda: float = 0.7  # 相关性 vs 多样性权衡
    mmr_final_k: int = 10  # 最终保留数量

    # === 批处理配置 ===
    # Category-level batch
    category_batch_size: int = 5
    category_batch_timeout_ms: int = 300

    # Global batch
    global_batch_size: int = 12
    global_batch_timeout_ms: int = 800

    # === LLM 配置 ===
    llm_base_url: str = "http://11.11.11.7:8904/v1"
    llm_model: str = "Qwen/Qwen2.5-3B-Instruct"
    llm_max_tokens: int = 120
    llm_temperature: float = 0.7
    llm_top_p: float = 0.9
    llm_batch_size: int = 12  # 批量推理

    # === Embedding 服务配置 ===
    embedding_base_url: str = "http://11.11.11.7:8090/v1"
    embedding_model: str = "BAAI/bge-large-en-v1.5"
    embedding_dimension: int = 1024
    embedding_batch_size: int = 64  # 激进的批量（减少网络往返）

    # === Rerank 服务配置 ===
    rerank_base_url: str = "http://11.11.11.7:8905/v1"
    rerank_model: str = "BAAI/bge-reranker-v2-m3"
    rerank_batch_size: int = 32

    # === FAISS VDB 数据路径 ===
    vdb_index_dir: str = "/home/sage/data"  # FAISS 索引持久化目录
    vdb_dataset_name: str = "fiqa"  # 真实数据集名称（fiqa_faiss.index, fiqa_documents.jsonl）
    vdb_corpus_size_mock: int = 10000  # Mock 数据集大小（仅用于生成新索引时）

    # === 调度配置 ===
    scheduler_type: str = "load_aware"  # "fifo" | "load_aware" | "priority"
    scheduler_strategy: str = "adaptive"
    enable_task_stealing: bool = True
    enable_dynamic_parallelism: bool = True

    # === 监控配置 ===
    enable_profiling: bool = True
    enable_detailed_metrics: bool = True
    metrics_output_dir: str = "/tmp/sage_metrics_workload4"
    metrics_flush_interval: int = 10  # 秒

    # === 性能优化配置 ===
    enable_numpy_optimization: bool = True  # 启用 NumPy 向量化
    enable_caching: bool = True  # 启用结果缓存
    cache_size: int = 10000

    # === 调试配置 ===
    debug_mode: bool = False
    log_level: str = "INFO"
    save_intermediate_results: bool = False

    def __post_init__(self):
        """初始化后验证"""
        self.validate()
        self._ensure_metrics_dir()

    def validate(self) -> bool:
        """验证配置合法性"""
        # QPS
        assert self.query_qps > 0, "query_qps must be positive"
        assert self.doc_qps > 0, "doc_qps must be positive"

        # Join
        assert 0.0 < self.join_threshold <= 1.0, "join_threshold must be in (0, 1]"
        assert self.join_window_seconds > 0, "join_window_seconds must be positive"
        assert self.join_parallelism > 0, "join_parallelism must be positive"

        # 权重分布
        assert abs(sum(self.query_type_distribution.values()) - 1.0) < 1e-6, (
            "query_type_distribution must sum to 1.0"
        )
        assert abs(sum(self.category_distribution.values()) - 1.0) < 1e-6, (
            "category_distribution must sum to 1.0"
        )
        assert abs(sum(self.rerank_score_weights.values()) - 1.0) < 1e-6, (
            "rerank_score_weights must sum to 1.0"
        )

        # VDB
        assert self.vdb1_top_k > 0, "vdb1_top_k must be positive"
        assert self.vdb2_top_k > 0, "vdb2_top_k must be positive"

        # Batch
        assert self.category_batch_size > 0, "category_batch_size must be positive"
        assert self.global_batch_size > 0, "global_batch_size must be positive"

        # MMR
        assert 0.0 <= self.mmr_lambda <= 1.0, "mmr_lambda must be in [0, 1]"

        return True

    def _ensure_metrics_dir(self):
        """确保指标输出目录存在"""
        Path(self.metrics_output_dir).mkdir(parents=True, exist_ok=True)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典（用于序列化）"""
        return {
            "num_tasks": self.num_tasks,
            "duration": self.duration,
            "use_remote": self.use_remote,
            "num_nodes": self.num_nodes,
            "query_qps": self.query_qps,
            "doc_qps": self.doc_qps,
            "join_window_seconds": self.join_window_seconds,
            "join_threshold": self.join_threshold,
            "join_parallelism": self.join_parallelism,
            "vdb1_top_k": self.vdb1_top_k,
            "vdb2_top_k": self.vdb2_top_k,
            "clustering_algorithm": self.clustering_algorithm,
            "rerank_top_k": self.rerank_top_k,
            "category_batch_size": self.category_batch_size,
            "global_batch_size": self.global_batch_size,
            "llm_model": self.llm_model,
            "embedding_model": self.embedding_model,
            "scheduler_type": self.scheduler_type,
        }

    @classmethod
    def from_dict(cls, config_dict: dict[str, Any]) -> "Workload4Config":
        """从字典创建配置"""
        return cls(**config_dict)

    def get_performance_target(self) -> dict[str, Any]:
        """获取预期性能目标"""
        return {
            "cpu_utilization": "85-95%",
            "throughput_qps": "10-15",
            "p50_latency_ms": 1200,
            "p95_latency_ms": 2000,
            "p99_latency_ms": 3000,
            "join_window_memory_mb": 24,  # 1500 docs × 1KB × 16 partitions
        }

    def get_hardware_requirements(self) -> dict[str, Any]:
        """获取硬件需求"""
        return {
            "min_nodes": 8,
            "cpu_cores_per_node": 8,
            "memory_per_node_gb": 16,
            "total_cpu_cores": 128,
            "total_memory_gb": 256,
            "gpu": {
                "required": True,
                "min_vram_gb": 24,
                "recommended": "A6000 48GB",
            },
        }


# === 预定义配置 ===


def get_default_config() -> Workload4Config:
    """获取默认配置（标准压测）"""
    return Workload4Config()


def get_light_config() -> Workload4Config:
    """获取轻量配置（快速测试）"""
    return Workload4Config(
        num_tasks=50,
        duration=300,  # 5分钟
        query_qps=20.0,
        doc_qps=15.0,
        join_window_seconds=30,
        vdb1_top_k=15,
        vdb2_top_k=15,
        category_batch_size=4,
        global_batch_size=8,
    )


def get_extreme_config() -> Workload4Config:
    """获取极限配置（最大压力）"""
    return Workload4Config(
        num_tasks=200,
        duration=1800,  # 30分钟
        query_qps=50.0,
        doc_qps=30.0,
        join_window_seconds=90,  # 更大窗口
        join_parallelism=32,  # 更高并行度
        vdb1_top_k=30,
        vdb2_top_k=30,
        embedding_batch_size=128,  # 超大批量
    )


def get_cpu_optimized_config() -> Workload4Config:
    """获取 CPU 优化配置（适配实际硬件）"""
    return Workload4Config(
        # 降低 QPS 以匹配实际算力
        query_qps=30.0,
        doc_qps=20.0,
        # 减小窗口降低内存压力
        join_window_seconds=40,
        # 增加并行度利用 128 核心
        join_parallelism=32,
        vdb_parallelism=16,
        # 激进的批量减少网络往返
        embedding_batch_size=128,
        rerank_batch_size=64,
        # 启用所有优化
        enable_numpy_optimization=True,
        enable_caching=True,
        enable_task_stealing=True,
        enable_dynamic_parallelism=True,
    )
