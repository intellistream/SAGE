"""
Workload 4 - Task 1 使用示例

演示如何使用数据模型和配置类。
"""

import time
import sys
from pathlib import Path

# 添加父目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from workload4.models import (
    QueryEvent,
    DocumentEvent,
    JoinedEvent,
    VDBRetrievalResult,
    Workload4Metrics,
)
from workload4.config import (
    get_default_config,
    get_light_config,
    get_cpu_optimized_config,
)


def example_1_basic_models():
    """示例 1: 创建基本数据模型"""
    print("=" * 60)
    print("示例 1: 创建基本数据模型")
    print("=" * 60)
    
    # 创建查询事件
    query = QueryEvent(
        query_id="q001",
        query_text="What is the impact of AI on financial industry?",
        query_type="analytical",
        category="finance",
        timestamp=time.time(),
        embedding=[0.1] * 1024,  # 1024维向量
    )
    print(f"Query ID: {query.query_id}")
    print(f"Query Type: {query.query_type}")
    print(f"Category: {query.category}")
    print(f"Embedding dim: {len(query.embedding)}")
    print()
    
    # 创建文档事件
    doc = DocumentEvent(
        doc_id="d001",
        doc_text="AI is revolutionizing the financial sector with automated trading...",
        doc_category="finance",
        timestamp=time.time(),
        embedding=[0.2] * 1024,
        metadata={"source": "research_paper", "year": 2024},
    )
    print(f"Document ID: {doc.doc_id}")
    print(f"Document source: {doc.metadata['source']}")
    print()


def example_2_joined_event():
    """示例 2: 创建 Join 后的事件"""
    print("=" * 60)
    print("示例 2: 创建 Join 后的事件")
    print("=" * 60)
    
    query = QueryEvent(
        query_id="q001",
        query_text="AI impact on finance",
        query_type="factual",
        category="finance",
        timestamp=time.time(),
    )
    
    docs = [
        DocumentEvent(
            doc_id=f"d{i:03d}",
            doc_text=f"Document {i} about AI and finance",
            doc_category="finance",
            timestamp=time.time(),
        )
        for i in range(1, 6)
    ]
    
    joined = JoinedEvent(
        joined_id="q001_1234567890.123",
        query=query,
        matched_docs=docs,
        join_timestamp=time.time(),
        semantic_score=0.85,
    )
    
    print(f"Joined ID: {joined.joined_id}")
    print(f"Matched documents: {len(joined.matched_docs)}")
    print(f"Semantic score: {joined.semantic_score}")
    print()


def example_3_vdb_results():
    """示例 3: VDB 检索结果"""
    print("=" * 60)
    print("示例 3: VDB 检索结果")
    print("=" * 60)
    
    # 模拟双路 VDB 检索
    vdb1_results = [
        VDBRetrievalResult(
            doc_id=f"vdb1_doc{i}",
            content=f"Professional knowledge from VDB1 - document {i}",
            score=0.9 - i * 0.05,
            source="vdb1",
            stage=1,
            metadata={"index_type": "HNSW", "ef_search": 200},
        )
        for i in range(5)
    ]
    
    vdb2_results = [
        VDBRetrievalResult(
            doc_id=f"vdb2_doc{i}",
            content=f"General knowledge from VDB2 - document {i}",
            score=0.88 - i * 0.05,
            source="vdb2",
            stage=1,
            metadata={"index_type": "IVF_HNSW", "nprobe": 50},
        )
        for i in range(5)
    ]
    
    print(f"VDB1 results: {len(vdb1_results)}")
    print(f"  Top result score: {vdb1_results[0].score:.3f}")
    print(f"  Source: {vdb1_results[0].source}")
    print()
    
    print(f"VDB2 results: {len(vdb2_results)}")
    print(f"  Top result score: {vdb2_results[0].score:.3f}")
    print(f"  Source: {vdb2_results[0].source}")
    print()


def example_4_metrics():
    """示例 4: 性能指标"""
    print("=" * 60)
    print("示例 4: 性能指标")
    print("=" * 60)
    
    metrics = Workload4Metrics(
        task_id="task_001",
        query_id="q001",
    )
    
    # 模拟各阶段时间戳
    base_time = 1000.0
    metrics.query_arrival_time = base_time
    metrics.doc_arrival_time = base_time + 0.1
    metrics.join_time = base_time + 0.5
    metrics.vdb1_start_time = base_time + 0.5
    metrics.vdb1_end_time = base_time + 1.0
    metrics.vdb2_start_time = base_time + 0.5
    metrics.vdb2_end_time = base_time + 1.2
    metrics.graph_start_time = base_time + 1.2
    metrics.graph_end_time = base_time + 1.5
    metrics.clustering_time = 0.3
    metrics.reranking_time = 0.2
    metrics.end_to_end_time = base_time + 3.0
    
    # 填充统计
    metrics.join_matched_docs = 5
    metrics.vdb1_results = 25
    metrics.vdb2_results = 25
    metrics.graph_nodes_visited = 120
    metrics.clusters_found = 8
    metrics.duplicates_removed = 10
    metrics.final_top_k = 10
    
    # 计算延迟
    latencies = metrics.compute_latencies()
    print("延迟统计:")
    for key, value in latencies.items():
        print(f"  {key}: {value:.3f}s")
    print()
    
    # 导出为字典
    metrics_dict = metrics.to_dict()
    print("指标摘要:")
    print(f"  Task ID: {metrics_dict['task_id']}")
    print(f"  Join matched docs: {metrics_dict['join_matched_docs']}")
    print(f"  VDB1 results: {metrics_dict['vdb1_results']}")
    print(f"  VDB2 results: {metrics_dict['vdb2_results']}")
    print(f"  Graph nodes visited: {metrics_dict['graph_nodes_visited']}")
    print(f"  Duplicates removed: {metrics_dict['duplicates_removed']}")
    print()


def example_5_configs():
    """示例 5: 配置使用"""
    print("=" * 60)
    print("示例 5: 配置使用")
    print("=" * 60)
    
    # 默认配置
    config = get_default_config()
    print("默认配置（标准压测）:")
    print(f"  Query QPS: {config.query_qps}")
    print(f"  Doc QPS: {config.doc_qps}")
    print(f"  Join window: {config.join_window_seconds}s")
    print(f"  Join parallelism: {config.join_parallelism}")
    print(f"  VDB1 top-k: {config.vdb1_top_k}")
    print(f"  VDB2 top-k: {config.vdb2_top_k}")
    print()
    
    # 性能目标
    targets = config.get_performance_target()
    print("预期性能目标:")
    print(f"  CPU utilization: {targets['cpu_utilization']}")
    print(f"  Throughput: {targets['throughput_qps']} QPS")
    print(f"  P50 latency: {targets['p50_latency_ms']}ms")
    print(f"  P95 latency: {targets['p95_latency_ms']}ms")
    print(f"  P99 latency: {targets['p99_latency_ms']}ms")
    print()
    
    # 硬件需求
    hw_req = config.get_hardware_requirements()
    print("硬件需求:")
    print(f"  Nodes: {hw_req['min_nodes']}")
    print(f"  Total CPU cores: {hw_req['total_cpu_cores']}")
    print(f"  Total memory: {hw_req['total_memory_gb']} GB")
    print(f"  GPU: {hw_req['gpu']['recommended']}")
    print()


def example_6_config_comparison():
    """示例 6: 配置对比"""
    print("=" * 60)
    print("示例 6: 不同配置对比")
    print("=" * 60)
    
    configs = {
        "Light": get_light_config(),
        "Default": get_default_config(),
        "CPU Optimized": get_cpu_optimized_config(),
    }
    
    print(f"{'Config':<20} {'QPS (Q+D)':<15} {'Window':<10} {'Parallelism':<15} {'Duration':<10}")
    print("-" * 80)
    
    for name, cfg in configs.items():
        qps_str = f"{cfg.query_qps}+{cfg.doc_qps}"
        window_str = f"{cfg.join_window_seconds}s"
        parallel_str = f"{cfg.join_parallelism}"
        duration_str = f"{cfg.duration}s"
        print(f"{name:<20} {qps_str:<15} {window_str:<10} {parallel_str:<15} {duration_str:<10}")
    
    print()


def example_7_config_serialization():
    """示例 7: 配置序列化"""
    print("=" * 60)
    print("示例 7: 配置序列化")
    print("=" * 60)
    
    config = get_default_config()
    
    # 转为字典
    config_dict = config.to_dict()
    print("配置已序列化为字典")
    print(f"  包含 {len(config_dict)} 个字段")
    print()
    
    # 从字典恢复
    restored_config = config.from_dict(config_dict)
    print("配置已从字典恢复")
    print(f"  Query QPS: {restored_config.query_qps}")
    print(f"  LLM model: {restored_config.llm_model}")
    print()


def main():
    """运行所有示例"""
    print("\n" + "=" * 60)
    print("Workload 4 - Task 1 使用示例")
    print("=" * 60)
    print()
    
    example_1_basic_models()
    example_2_joined_event()
    example_3_vdb_results()
    example_4_metrics()
    example_5_configs()
    example_6_config_comparison()
    example_7_config_serialization()
    
    print("=" * 60)
    print("所有示例完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
