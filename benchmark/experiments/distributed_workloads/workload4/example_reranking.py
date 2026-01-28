"""
Workload 4 重排序示例脚本。

展示如何使用 MultiDimensionalReranker 和 MMRDiversityFilter。
"""

import time
from pathlib import Path

import numpy as np

from workload4.models import (
    ClusteringResult,
    JoinedEvent,
    QueryEvent,
    DocumentEvent,
    RerankingResult,
    VDBRetrievalResult,
)
from workload4.reranking import (
    MMRDiversityFilter,
    MultiDimensionalReranker,
    visualize_score_breakdown,
    visualize_score_distribution,
)


def create_sample_data():
    """创建示例数据"""
    # 1. 创建查询
    query = QueryEvent(
        query_id="q1",
        query_text="What are the latest advances in deep learning for NLP",
        query_type="factual",
        category="technology",
        timestamp=time.time(),
        embedding=np.random.randn(128).tolist(),
    )
    
    # 2. 创建 joined event
    joined_event = JoinedEvent(
        joined_id=f"joined_{query.query_id}_{int(time.time())}",
        query=query,
        matched_docs=[
            DocumentEvent(
                doc_id="doc_match_1",
                doc_text="Matched document",
                doc_category="technology",
                timestamp=time.time(),
            )
        ],
        join_timestamp=time.time(),
        semantic_score=0.85,
    )
    
    # 3. 创建 VDB 检索结果
    vdb_results = []
    current_time = time.time()
    
    for i in range(20):
        vdb_results.append(
            VDBRetrievalResult(
                doc_id=f"doc_{i}",
                content=f"Document {i} about deep learning and NLP advances",
                score=0.95 - i * 0.03,
                source="vdb1" if i < 10 else "vdb2",
                stage=1 + (i // 5),
                metadata={
                    "timestamp": current_time - i * 3600,
                    "citations": max(0, 100 - i * 10),
                    "centrality": max(0.1, 0.95 - i * 0.04),
                    "source": "verified" if i < 5 else "general",
                },
            )
        )
    
    # 4. 创建聚类信息
    clustering_info = [
        ClusteringResult(
            cluster_id=0,
            representative_doc_id="doc_0",
            cluster_docs=["doc_0", "doc_1", "doc_5"],
            cluster_size=3,
        ),
        ClusteringResult(
            cluster_id=1,
            representative_doc_id="doc_2",
            cluster_docs=["doc_2", "doc_3", "doc_4", "doc_10"],
            cluster_size=4,
        ),
    ]
    
    return query, joined_event, vdb_results, clustering_info


def example_basic_reranking():
    """示例: 基本重排序"""
    print("\n" + "=" * 80)
    print("示例 1: 基本 5 维评分重排序")
    print("=" * 80)
    
    query, joined_event, vdb_results, clustering_info = create_sample_data()
    
    # 执行重排序
    print("\n执行 5 维评分重排序...")
    reranker = MultiDimensionalReranker(
        score_weights={
            "semantic": 0.35,
            "freshness": 0.25,
            "diversity": 0.15,
            "authority": 0.15,
            "coverage": 0.10,
        },
        top_k=10,
        enable_profiling=True,
    )
    
    data = (joined_event, vdb_results, clustering_info)
    results = reranker.execute(data)
    
    # 打印结果
    print(f"\n重排序结果 (Top-{len(results)}):")
    print("-" * 80)
    for result in results[:5]:
        print(f"\nRank {result.rank}: {result.doc_id}")
        print(f"  Final Score: {result.final_score:.4f}")
        print(f"  Score Breakdown:")
        for dim, score in result.score_breakdown.items():
            if dim != "embedding":
                print(f"    {dim:12s}: {score:.4f}")
    
    return results


def example_mmr_filtering():
    """示例: MMR 多样性过滤"""
    print("\n" + "=" * 80)
    print("示例 2: MMR 多样性过滤")
    print("=" * 80)
    
    # 创建测试数据
    query = QueryEvent(
        query_id="q2",
        query_text="Machine learning applications",
        query_type="analytical",
        category="technology",
        timestamp=time.time(),
        embedding=np.random.randn(128).tolist(),
    )
    
    # 创建重排序结果（带 embedding）
    reranking_results = []
    for i in range(15):
        embedding = np.random.randn(128)
        reranking_results.append(
            RerankingResult(
                doc_id=f"doc_{i}",
                content=f"ML application {i}",
                final_score=0.9 - i * 0.04,
                score_breakdown={
                    "semantic": 0.9 - i * 0.04,
                    "freshness": 0.7 + i * 0.02,
                    "diversity": 0.6,
                    "authority": 0.5,
                    "coverage": 0.75,
                    "embedding": embedding.tolist(),
                },
                rank=i + 1,
            )
        )
    
    # 高 lambda（重视相关性）
    print("\n高 lambda = 0.9 (重视相关性):")
    mmr_high = MMRDiversityFilter(lambda_param=0.9, top_k=8, enable_profiling=True)
    results_high = mmr_high.execute((query, reranking_results))
    print(f"  选择的文档: {[r.doc_id for r in results_high]}")
    
    # 低 lambda（重视多样性）
    print("\n低 lambda = 0.3 (重视多样性):")
    mmr_low = MMRDiversityFilter(lambda_param=0.3, top_k=8, enable_profiling=True)
    results_low = mmr_low.execute((query, reranking_results))
    print(f"  选择的文档: {[r.doc_id for r in results_low]}")
    
    return results_high, results_low


def example_end_to_end():
    """示例: 端到端重排序 + MMR"""
    print("\n" + "=" * 80)
    print("示例 3: 端到端重排序 + MMR 流程")
    print("=" * 80)
    
    query, joined_event, vdb_results, clustering_info = create_sample_data()
    
    # Step 1: 重排序
    print("\nStep 1: 5 维评分重排序")
    reranker = MultiDimensionalReranker(top_k=12, enable_profiling=True)
    reranked = reranker.execute((joined_event, vdb_results, clustering_info))
    print(f"  输入: {len(vdb_results)} 个文档 → 输出: {len(reranked)} 个文档")
    
    # Step 2: 添加 embedding
    print("\nStep 2: 为结果添加 embedding")
    for result in reranked:
        result.score_breakdown["embedding"] = np.random.randn(128).tolist()
    
    # Step 3: MMR 多样性过滤
    print("\nStep 3: MMR 多样性过滤")
    mmr_filter = MMRDiversityFilter(lambda_param=0.65, top_k=8, enable_profiling=True)
    final_results = mmr_filter.execute((query, reranked))
    print(f"  输入: {len(reranked)} 个文档 → 输出: {len(final_results)} 个文档")
    
    # 打印最终结果
    print("\n最终 Top-5 结果:")
    print("-" * 80)
    for result in final_results[:5]:
        print(f"Rank {result.rank}: {result.doc_id} (Score: {result.final_score:.4f})")
    
    return final_results


def example_visualization():
    """示例: 可视化"""
    print("\n" + "=" * 80)
    print("示例 4: 评分可视化")
    print("=" * 80)
    
    # 获取重排序结果
    results = example_basic_reranking()
    
    # 生成可视化
    output_dir = Path("/tmp/sage_workload4_reranking_viz")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    radar_path = output_dir / "score_breakdown_radar.png"
    dist_path = output_dir / "score_distribution.png"
    
    print(f"\n生成可视化:")
    print(f"  雷达图: {radar_path}")
    print(f"  分布图: {dist_path}")
    
    visualize_score_breakdown(results, str(radar_path))
    visualize_score_distribution(results, str(dist_path))
    
    print(f"\n✓ 可视化文件已保存到: {output_dir}")


def main():
    """运行所有示例"""
    print("\n" + "=" * 80)
    print("Workload 4 重排序模块示例")
    print("=" * 80)
    
    try:
        example_basic_reranking()
        example_mmr_filtering()
        example_end_to_end()
        example_visualization()
        
        print("\n" + "=" * 80)
        print("✓ 所有示例执行完成")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
