"""
Workload 4 Pipeline Factory
============================

整合所有算子，构建完整的 Workload 4 分布式数据流。

Pipeline 结构:
1. 双流源（Query + Document）
2. Embedding 预计算
3. Semantic Join (60s 大窗口)
4. 双路 VDB 检索（4-stage each）
5. 图遍历内存检索
6. 结果汇聚
7. DBSCAN 聚类去重
8. 5维评分重排序
9. MMR 多样性过滤
10. 双层 Batch 聚合
11. 批量 LLM 生成
12. Metrics Sink
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

from sage.kernel.api.service import BaseService

if TYPE_CHECKING:
    from sage.kernel.api.local_environment import LocalEnvironment
    from sage.kernel.api.remote_environment import RemoteEnvironment

try:
    from .config import Workload4Config
    from .models import (
        QueryEvent,
        DocumentEvent,
        JoinedEvent,
        VDBRetrievalResult,
        GraphMemoryResult,
        ClusteringResult,
        RerankingResult,
        BatchContext,
        Workload4Metrics,
    )
    from .sources import (
        Workload4QuerySource,
        Workload4DocumentSource,
        EmbeddingPrecompute,
    )
    from .semantic_join import SemanticJoinOperator
    from .vdb_retrieval import (
        VDBRetriever,
        VDBResultFilter,
        LocalReranker,
        StageAggregator,
    )
    from .graph_memory import GraphMemoryRetriever
    from .clustering import DBSCANClusteringOperator
    from .reranking import MultiDimensionalReranker, MMRDiversityFilter
    from .batching import CategoryBatchAggregator, GlobalBatchAggregator
    from .generation import BatchLLMGenerator, Workload4MetricsSink
    from .union_operator import UnionCoMap
    # 🔧 临时添加：单源测试用的转换器
    from .mappers import QueryToJoinedMapper
except ImportError:
    from config import Workload4Config
    from models import (
        QueryEvent,
        DocumentEvent,
        JoinedEvent,
        VDBRetrievalResult,
        GraphMemoryResult,
        ClusteringResult,
        RerankingResult,
        BatchContext,
        Workload4Metrics,
    )
    from sources import (
        Workload4QuerySource,
        Workload4DocumentSource,
        EmbeddingPrecompute,
    )
    from semantic_join import SemanticJoinOperator
    from vdb_retrieval import (
        VDBRetriever,
        VDBResultFilter,
        LocalReranker,
        StageAggregator,
    )
    from graph_memory import GraphMemoryRetriever
    from clustering import DBSCANClusteringOperator
    from reranking import MultiDimensionalReranker, MMRDiversityFilter
    from batching import CategoryBatchAggregator, GlobalBatchAggregator
    from generation import BatchLLMGenerator, Workload4MetricsSink
    from union_operator import UnionCoMap
    # 🔧 临时添加：单源测试用的转换器
    from mappers import QueryToJoinedMapper


# =============================================================================
# Service Registration
# =============================================================================

def register_embedding_service(
    env: LocalEnvironment | RemoteEnvironment,
    config: Workload4Config,
) -> bool:
    """
    注册 Embedding 服务。
    
    使用远端 Embedding API（OpenAI 兼容）。
    """
    try:
        from .services import EmbeddingService
        
        env.register_service(
            "embedding",
            EmbeddingService,
            base_url=config.embedding_base_url,
            model=config.embedding_model,
        )
        
        print(f"✓ Registered embedding_service: {config.embedding_base_url}")
        return True
        
    except Exception as e:
        print(f"✗ Failed to register embedding_service: {e}")
        return False


def register_vdb_services(
    env: LocalEnvironment | RemoteEnvironment,
    config: Workload4Config,
) -> dict[str, bool]:
    """
    注册双路 VDB 服务（vdb1 和 vdb2）。
    
    使用真实的 FiQA 数据集（57,638 文档，1024 维）。
    vdb1 和 vdb2 共享相同的 FAISS 索引（fiqa_faiss.index）。
    索引和文档存储在 config.vdb_index_dir。
    
    **数据源**：/home/sage/data/fiqa_faiss.index + fiqa_documents.jsonl
    """
    results = {}
    
    # Import Service class from module
    from .services import FAISSVDBService
    
    for vdb_name in ["vdb1", "vdb2"]:
        try:
            env.register_service(
                vdb_name,
                FAISSVDBService,
                vdb_name=vdb_name,
                dimension=config.embedding_dimension,
                index_dir=config.vdb_index_dir,
                dataset_name=config.vdb_dataset_name,
            )
            
            results[vdb_name] = True
            print(f"✓ Registered {vdb_name} (FiQA dataset, shared index)")
            
        except Exception as e:
            results[vdb_name] = False
            print(f"✗ Failed to register {vdb_name}: {e}")
            import traceback
            traceback.print_exc()
    
    return results


def register_graph_memory_service(
    env: LocalEnvironment | RemoteEnvironment,
    config: Workload4Config,
) -> bool:
    """
    注册图内存服务。
    
    使用 Mock 图结构或 NeuroMem Graph backend。
    """
    # Import Service class from module
    from .services import GraphMemoryService
    
    try:
        env.register_service(
            "graph_memory",
            GraphMemoryService,
            max_depth=config.graph_max_depth,
            max_nodes=config.graph_max_nodes,
        )
        
        print(f"✓ Registered graph_memory_service")
        return True
        
    except Exception as e:
        print(f"✗ Failed to register graph_memory_service: {e}")
        return False


def register_llm_service(
    env: LocalEnvironment | RemoteEnvironment,
    config: Workload4Config,
) -> bool:
    """
    注册 LLM 服务。
    
    使用远端 LLM API（OpenAI 兼容）。
    """
    # Import Service class from module
    from .services import LLMService
    
    try:
        env.register_service(
            "llm",
            LLMService,
            base_url=config.llm_base_url,
            model=config.llm_model,
            max_tokens=config.llm_max_tokens,
        )
        
        print(f"✓ Registered llm_service: {config.llm_base_url}")
        return True
        
    except Exception as e:
        print(f"✗ Failed to register llm_service: {e}")
        return False


def register_all_services(
    env: LocalEnvironment | RemoteEnvironment,
    config: Workload4Config,
) -> dict[str, bool]:
    """
    注册所有必要的 services。
    
    Returns:
        服务注册结果字典
    """
    results = {}
    
    print("\n" + "=" * 80)
    print("Registering Workload 4 Services")
    print("=" * 80)
    
    # 1. Embedding Service
    results["embedding"] = register_embedding_service(env, config)
    
    # 2. VDB Services (vdb1, vdb2)
    vdb_results = register_vdb_services(env, config)
    results.update(vdb_results)
    
    # 3. Graph Memory Service
    results["graph_memory"] = register_graph_memory_service(env, config)
    
    # 4. LLM Service
    results["llm"] = register_llm_service(env, config)
    
    print("=" * 80)
    print(f"Service Registration Summary: {sum(results.values())}/{len(results)} successful")
    print("=" * 80)
    
    return results


# =============================================================================
# Pipeline Factory
# =============================================================================


class Workload4Pipeline:
    """
    Workload 4 Pipeline 工厂。
    
    整合所有算子，构建完整的分布式数据流。
    """
    
    def __init__(self, config: Workload4Config):
        """
        初始化 Pipeline。
        
        Args:
            config: Workload 4 配置
        """
        self.config = config
        self.env = None
        self.metrics = None
    
    def _create_environment(self, name: str):
        """创建执行环境（本地或远程）"""
        if self.config.use_remote:
            from pathlib import Path
            from sage.kernel.api.remote_environment import RemoteEnvironment
            
            # workload4 所在目录（当前文件的父目录的父目录）
            workload_dir = str(Path(__file__).parent.parent)
            
            # RemoteEnvironment 参数：name, config, host, port, scheduler, extra_python_paths
            env = RemoteEnvironment(
                name=name,
                scheduler=self.config.scheduler_type,  # "fifo" 或 "load_aware"
                extra_python_paths=[workload_dir],  # 让远程节点能找到 workload4 模块
            )
            return env
        else:
            from sage.kernel.api.local_environment import LocalEnvironment
            return LocalEnvironment(name=name)
    
    def build(self, name: str = "workload4_benchmark") -> Workload4Pipeline:
        """
        构建完整 pipeline。
        
        Pipeline 结构:
        1. 双流源（Query + Document）
        2. Embedding 预计算
        3. Semantic Join (60s 大窗口, parallelism=16)
        4. 图遍历内存检索
        5. 双路 VDB 检索（4-stage each）
        6. 汇聚所有检索结果
        7. DBSCAN 聚类去重
        8. 5维评分重排序
        9. MMR 多样性过滤
        10. 双层 Batch 聚合
        11. 批量 LLM 生成
        12. Metrics Sink
        
        Returns:
            self (支持链式调用)
        """
        print("\n" + "=" * 80)
        print("Building Workload 4 Pipeline")
        print("=" * 80)
        print(f"Pipeline Name: {name}")
        print(f"Use Remote: {self.config.use_remote}")
        print(f"Num Nodes: {self.config.num_nodes}")
        print(f"Num Tasks: {self.config.num_tasks}")
        print(f"Duration: {self.config.duration}s")
        print("=" * 80)
        
        # === 1. 创建环境 ===
        # CRITICAL: Create environment in a local scope and build pipeline immediately
        # This avoids storing RemoteEnvironment in self, which causes serialization issues
        env = self._create_environment(name)
        print(f"✓ Created {'Remote' if self.config.use_remote else 'Local'}Environment")
        if self.config.use_remote:
            print(f"  Scheduler: {self.config.scheduler_type}")
        
        # === 2. 注册所有 services ===
        service_results = register_all_services(env, self.config)
        
        if not all(service_results.values()):
            failed = [k for k, v in service_results.items() if not v]
            print(f"⚠️  Some services failed to register: {failed}")
            print("   Pipeline may not work correctly.")
        
        # === 3. 构建双流源 ===
        print("\n" + "=" * 80)
        print("Building Data Streams")
        print("=" * 80)
        
        # Query 流（传入类而非实例）
        query_stream = env.from_source(
            Workload4QuerySource,
            num_tasks=self.config.num_tasks,
            qps=self.config.query_qps,
            query_types=list(self.config.query_type_distribution.keys()),
            categories=list(self.config.category_distribution.keys()),
            use_fiqa=False,  # 可配置
        )
        print(f"✓ Created Query Stream (QPS={self.config.query_qps})")
        
        # Document 流（传入类而非实例）
        doc_stream = env.from_source(
            Workload4DocumentSource,
            num_docs=self.config.num_tasks * 20,  # 每个query对应20个doc
            qps=self.config.doc_qps,
            categories=list(self.config.category_distribution.keys()),
        )
        print(f"✓ Created Document Stream (QPS={self.config.doc_qps})")
        
        # === 4. Embedding 预计算 ===
        query_stream = query_stream.map(
            EmbeddingPrecompute,
            embedding_base_url=self.config.embedding_base_url,
            embedding_model=self.config.embedding_model,
            batch_size=32,
            field_name="query_text",
        )
        print("✓ Added EmbeddingPrecompute for Query Stream")
        
        doc_stream = doc_stream.map(
            EmbeddingPrecompute,
            embedding_base_url=self.config.embedding_base_url,
            embedding_model=self.config.embedding_model,
            batch_size=32,
            field_name="doc_text",
        )
        print("✓ Added EmbeddingPrecompute for Document Stream")
        
        # === 5. Semantic Join ===
        print("\n" + "=" * 80)
        print("Building Semantic Join")
        print("=" * 80)
        
        # SemanticJoinOperator 是 BaseCoMapFunction，使用 comap 而不是 join
        joined_stream = query_stream.connect(doc_stream).comap(
            SemanticJoinOperator,
            window_seconds=self.config.join_window_seconds,
            threshold=self.config.join_threshold,
            max_matches=self.config.join_max_matches,
            batch_compute=True,
        ).keyby(lambda x: hash(x.joined_id) % self.config.join_parallelism)
        
        print(f"✓ Added Semantic Join (window={self.config.join_window_seconds}s, "
              f"threshold={self.config.join_threshold}, "
              f"parallelism={self.config.join_parallelism})")
        
        # === 6. 图遍历内存检索 ===
        print("\n" + "=" * 80)
        print("Building Graph Memory Retrieval")
        print("=" * 80)
        
        graph_stream = joined_stream.map(
            GraphMemoryRetriever,
            max_depth=self.config.graph_max_depth,
            max_nodes=self.config.graph_max_nodes,
            beam_width=self.config.graph_bfs_beam_width,
        )
        print(f"✓ Added Graph Memory Retrieval (max_depth={self.config.graph_max_depth}, "
              f"max_nodes={self.config.graph_max_nodes})")
        
        # === 7. 双路 VDB 检索（4-stage each）===
        print("\n" + "=" * 80)
        print("Building VDB Retrieval Branches")
        print("=" * 80)
        
        # VDB1 分支 (4-stage cascade)
        vdb1_stream = joined_stream
        for stage in range(1, 5):
            top_k = self.config.vdb1_top_k // stage  # 递减 top-k
            filter_threshold = self.config.vdb_filter_threshold + (stage - 1) * 0.05
            
            vdb1_stream = vdb1_stream.map(
                VDBRetriever,
                vdb_name="vdb1",
                top_k=top_k,
                stage=stage,
            )
            
            if stage < 4:  # 最后一 stage 不过滤
                vdb1_stream = vdb1_stream.filter(
                    VDBResultFilter,
                    threshold=filter_threshold,
                )
                
                vdb1_stream = vdb1_stream.map(
                    LocalReranker,
                    top_k=max(5, top_k // 2),
                )
        
        print(f"✓ Added VDB1 Branch (4-stage cascade)")
        
        # VDB2 分支 (4-stage cascade)
        vdb2_stream = joined_stream
        for stage in range(1, 5):
            top_k = self.config.vdb2_top_k // stage
            filter_threshold = self.config.vdb_filter_threshold + (stage - 1) * 0.05
            
            vdb2_stream = vdb2_stream.map(
                VDBRetriever,
                vdb_name="vdb2",
                top_k=top_k,
                stage=stage,
            )
            
            if stage < 4:
                vdb2_stream = vdb2_stream.filter(
                    VDBResultFilter,
                    threshold=filter_threshold,
                )
                
                vdb2_stream = vdb2_stream.map(
                    LocalReranker,
                    top_k=max(5, top_k // 2),
                )
        
        print(f"✓ Added VDB2 Branch (4-stage cascade)")
        
        # === 8. 汇聚所有检索结果 ===
        print("\n" + "=" * 80)
        print("Building Result Aggregation")
        print("=" * 80)
        
        # 使用 connect + comap 来合并所有流（UnionCoMap 在文件顶部定义）
        all_results = vdb1_stream.connect(vdb2_stream).connect(graph_stream).comap(UnionCoMap)
        print("✓ Added Union of all retrieval results (VDB1 + VDB2 + Graph)")
        
        # === 9. DBSCAN 聚类去重 ===
        print("\n" + "=" * 80)
        print("Building Clustering & Deduplication")
        print("=" * 80)
        
        deduplicated_stream = all_results.map(
            DBSCANClusteringOperator,
            eps=self.config.dbscan_eps,
            min_samples=self.config.dbscan_min_samples,
            metric="cosine",
        )
        print(f"✓ Added DBSCAN Clustering (eps={self.config.dbscan_eps}, "
              f"min_samples={self.config.dbscan_min_samples})")
        
        # === 10. 5维评分重排序 ===
        print("\n" + "=" * 80)
        print("Building Reranking")
        print("=" * 80)
        
        reranked_stream = deduplicated_stream.map(
            MultiDimensionalReranker,
            score_weights=self.config.rerank_score_weights,
            top_k=self.config.rerank_top_k,
        )
        print(f"✓ Added MultiDimensional Reranking (5 dimensions, top_k={self.config.rerank_top_k})")
        
        # === 11. MMR 多样性过滤 ===
        reranked_stream = reranked_stream.map(
            MMRDiversityFilter,
            lambda_param=self.config.mmr_lambda,
            top_k=self.config.rerank_top_k,
        )
        print(f"✓ Added MMR Diversity Filter (lambda={self.config.mmr_lambda})")
        
        # === 12. 双层 Batch 聚合 ===
        print("\n" + "=" * 80)
        print("Building Batch Aggregation")
        print("=" * 80)
        
        # 第一层: Category Batch
        category_batched = reranked_stream.keyby(
            lambda x: x.query.category  # 按 category 分组
        ).map(
            CategoryBatchAggregator,
            batch_size=self.config.category_batch_size,
            timeout_ms=self.config.category_batch_timeout_ms,
        )
        print(f"✓ Added Category Batch (size={self.config.category_batch_size}, "
              f"timeout={self.config.category_batch_timeout_ms}ms)")
        
        # 第二层: Global Batch
        global_batched = category_batched.map(
            GlobalBatchAggregator,
            batch_size=self.config.global_batch_size,
            timeout_ms=self.config.global_batch_timeout_ms,
        )
        print(f"✓ Added Global Batch (size={self.config.global_batch_size}, "
              f"timeout={self.config.global_batch_timeout_ms}ms)")
        
        # === 13. 批量 LLM 生成 ===
        print("\n" + "=" * 80)
        print("Building LLM Generation")
        print("=" * 80)
        
        generated_stream = global_batched.map(
            BatchLLMGenerator,
            llm_base_url=self.config.llm_base_url,
            llm_model=self.config.llm_model,
            max_tokens=self.config.llm_max_tokens,
        )
        print(f"✓ Added Batch LLM Generator (model={self.config.llm_model})")
        
        # === 14. Metrics Sink ===
        print("\n" + "=" * 80)
        print("Building Metrics Sink")
        print("=" * 80)
        
        generated_stream.sink(
            Workload4MetricsSink,
            metrics_output_dir=self.config.metrics_output_dir,
            verbose=True,
        )
        print(f"✓ Added Metrics Sink (output_dir={self.config.metrics_output_dir})")
        
        print("\n" + "=" * 80)
        print("Pipeline Build Complete")
        print("=" * 80)
        
        # Store environment for run()
        self.env = env
        
        return self
    
    def run(self) -> Workload4Metrics:
        """
        执行 pipeline。
        
        Returns:
            Workload4Metrics: 汇总指标
        """
        if self.env is None:
            raise RuntimeError("Pipeline not built. Call build() first.")
        
        print("\n" + "=" * 80)
        print("Starting Workload 4 Execution")
        print("=" * 80)
        print(f"Duration: {self.config.duration}s")
        print(f"Expected Tasks: {self.config.num_tasks}")
        print("=" * 80)
        
        start_time = time.time()
        
        try:
            # 执行 pipeline
            self.env.submit(autostop=True)
            
            end_time = time.time()
            elapsed = end_time - start_time
            
            print("\n" + "=" * 80)
            print("Workload 4 Execution Complete")
            print("=" * 80)
            print(f"Elapsed Time: {elapsed:.2f}s")
            print("=" * 80)
            
            # 收集汇总指标
            # TODO: 从 Sink 收集详细指标
            self.metrics = Workload4Metrics(
                task_id="summary",
                query_id="summary",
                query_arrival_time=start_time,
                doc_arrival_time=start_time,
                join_time=0.0,
                vdb1_start_time=0.0,
                vdb1_end_time=0.0,
                vdb2_start_time=0.0,
                vdb2_end_time=0.0,
                graph_start_time=0.0,
                graph_end_time=0.0,
                clustering_time=0.0,
                reranking_time=0.0,
                batch_time=0.0,
                generation_time=0.0,
                end_to_end_time=elapsed,
                join_matched_docs=0,
                vdb1_results=0,
                vdb2_results=0,
                graph_nodes_visited=0,
                clusters_found=0,
                duplicates_removed=0,
                final_top_k=0,
                cpu_time=0.0,
                memory_peak_mb=0.0,
            )
            
            return self.metrics
            
        except Exception as e:
            print(f"\n✗ Pipeline execution failed: {e}")
            import traceback
            traceback.print_exc()
            raise


# =============================================================================
# Convenience Functions
# =============================================================================


def create_workload4_pipeline(
    config: Workload4Config | None = None,
    **config_overrides
) -> Workload4Pipeline:
    """
    创建 Workload 4 Pipeline（便捷函数）。
    
    Args:
        config: Workload4Config 实例（可选）
        **config_overrides: 覆盖配置项
    
    Returns:
        Workload4Pipeline 实例
    
    Example:
        >>> pipeline = create_workload4_pipeline(num_tasks=50, duration=600)
        >>> pipeline.build().run()
    """
    if config is None:
        config = Workload4Config()
    
    # 应用覆盖
    for key, value in config_overrides.items():
        if hasattr(config, key):
            setattr(config, key, value)
        else:
            print(f"⚠️  Unknown config key: {key}")
    
    return Workload4Pipeline(config)


def run_workload4(
    config: Workload4Config | None = None,
    **config_overrides
) -> Workload4Metrics:
    """
    一键运行 Workload 4（便捷函数）。
    
    Args:
        config: Workload4Config 实例（可选）
        **config_overrides: 覆盖配置项
    
    Returns:
        Workload4Metrics: 汇总指标
    
    Example:
        >>> metrics = run_workload4(num_tasks=100, use_remote=True)
    """
    pipeline = create_workload4_pipeline(config, **config_overrides)
    pipeline.build()
    return pipeline.run()
