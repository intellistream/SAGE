"""
Workload 4 VDB 检索示例

演示如何使用双路 4-stage VDB 检索流水线。
"""

import sys
from pathlib import Path

# 添加父目录到 sys.path
parent_dir = Path(__file__).resolve().parent.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

from models import DocumentEvent, JoinedEvent, QueryEvent
from vdb_retrieval import (
    LocalReranker,
    StageAggregator,
    VDBBranchRouter,
    VDBResultFilter,
    VDBResultMerger,
    VDBRetriever,
    build_vdb_4stage_pipeline,
)


def example_single_stage_retrieval():
    """示例 1: 单个 Stage 的检索流程"""
    print("=" * 80)
    print("示例 1: 单个 Stage 的检索流程")
    print("=" * 80)

    # 创建测试数据
    query = QueryEvent(
        query_id="q1",
        query_text="What are the applications of machine learning?",
        query_type="factual",
        category="technology",
        timestamp=1000.0,
        embedding=[0.1] * 1024,  # Mock embedding
    )

    doc = DocumentEvent(
        doc_id="d1",
        doc_text="Machine learning has many applications in various domains.",
        doc_category="technology",
        timestamp=1001.0,
        embedding=[0.2] * 1024,
    )

    joined_event = JoinedEvent(
        joined_id="j1", query=query, matched_docs=[doc], join_timestamp=1002.0, semantic_score=0.85
    )

    # Stage 1: VDB 检索
    print("\nStep 1: VDB 检索")
    retriever = VDBRetriever(vdb_name="vdb1", top_k=20, stage=1)

    # 注意: 实际使用需要注册 VDB Service
    # results = retriever.execute(joined_event)

    # Mock 结果用于演示
    from models import VDBRetrievalResult

    mock_results = [
        VDBRetrievalResult(
            doc_id=f"doc_{i}",
            content=f"Machine learning content {i}",
            score=0.9 - i * 0.05,
            source="vdb1",
            stage=1,
            metadata={"query_text": query.query_text},
        )
        for i in range(20)
    ]

    print(f"  检索到 {len(mock_results)} 个结果")
    print(f"  分数范围: {mock_results[-1].score:.2f} - {mock_results[0].score:.2f}")

    # Stage 2: 过滤
    print("\nStep 2: 过滤低分结果")
    filter_op = VDBResultFilter(threshold=0.6, adaptive=True)
    filtered_results = [r for r in mock_results if filter_op.execute(r)]

    print(f"  过滤后剩余 {len(filtered_results)} 个结果")
    print(f"  过滤率: {(1 - len(filtered_results) / len(mock_results)) * 100:.1f}%")

    # Stage 3: 重排序
    print("\nStep 3: BM25 重排序")
    reranker = LocalReranker(top_k=15)
    reranked_results = reranker.execute(filtered_results)

    print(f"  重排序后保留 {len(reranked_results)} 个结果")
    if reranked_results:
        print(
            f"  Top-1: doc_id={reranked_results[0].doc_id}, score={reranked_results[0].rerank_score:.3f}"
        )


def example_4stage_pipeline():
    """示例 2: 完整的 4-stage 检索流水线"""
    print("\n" + "=" * 80)
    print("示例 2: 完整的 4-stage 检索流水线")
    print("=" * 80)

    # 构建 4-stage 流水线
    stages = build_vdb_4stage_pipeline(vdb_name="vdb1")

    print(f"\n构建了 {len(stages)} 个 stage:")
    for i, (retriever, filter_op, reranker) in enumerate(stages, 1):
        print(f"  Stage {i}:")
        print(f"    - Retriever: top_k={retriever.top_k}")
        if filter_op:
            print(f"    - Filter: threshold={filter_op.threshold}")
        else:
            print("    - Filter: None")
        if reranker:
            print(f"    - Reranker: top_k={reranker.top_k}")
        else:
            print("    - Reranker: None")

    # Stage 汇聚
    print("\nStage 汇聚:")
    aggregator = StageAggregator(num_stages=4)
    print(f"  汇聚 {aggregator.num_stages} 个 stage 的结果")
    print("  自动去重并按分数排序")


def example_dual_vdb_branches():
    """示例 3: 双路 VDB 检索"""
    print("\n" + "=" * 80)
    print("示例 3: 双路 VDB 检索")
    print("=" * 80)

    # 创建测试数据
    from models import VDBRetrievalResult

    # VDB1 结果
    vdb1_results = [
        VDBRetrievalResult(
            doc_id=f"vdb1_doc_{i}",
            content=f"VDB1 content {i}",
            score=0.9 - i * 0.05,
            source="vdb1",
            stage=1,
        )
        for i in range(10)
    ]

    # VDB2 结果
    vdb2_results = [
        VDBRetrievalResult(
            doc_id=f"vdb2_doc_{i}",
            content=f"VDB2 content {i}",
            score=0.85 - i * 0.05,
            source="vdb2",
            stage=1,
        )
        for i in range(10)
    ]

    print(f"\nVDB1 检索到 {len(vdb1_results)} 个结果")
    print(f"  分数范围: {vdb1_results[-1].score:.2f} - {vdb1_results[0].score:.2f}")

    print(f"\nVDB2 检索到 {len(vdb2_results)} 个结果")
    print(f"  分数范围: {vdb2_results[-1].score:.2f} - {vdb2_results[0].score:.2f}")

    # 合并结果
    print("\n合并策略对比:")

    # 策略 1: 基于分数
    merger_score = VDBResultMerger(merge_strategy="score_based", top_k=15)
    merged_score = merger_score.execute(vdb1_results, vdb2_results)
    print(f"  - score_based: {len(merged_score)} 个结果")
    print(f"    Top-3 来源: {', '.join([r.source for r in merged_score[:3]])}")

    # 策略 2: 交替
    merger_interleave = VDBResultMerger(merge_strategy="interleave", top_k=15)
    merged_interleave = merger_interleave.execute(vdb1_results, vdb2_results)
    print(f"  - interleave: {len(merged_interleave)} 个结果")
    print(f"    Top-3 来源: {', '.join([r.source for r in merged_interleave[:3]])}")


def example_routing_strategies():
    """示例 4: 路由策略对比"""
    print("\n" + "=" * 80)
    print("示例 4: 路由策略对比")
    print("=" * 80)

    # 创建测试数据
    queries = [
        QueryEvent(
            query_id=f"q{i}",
            query_text=f"Query {i}",
            query_type="factual",
            category=["finance", "healthcare", "technology", "general"][i % 4],
            timestamp=1000.0 + i,
        )
        for i in range(8)
    ]

    from models import DocumentEvent

    doc = DocumentEvent(doc_id="d1", doc_text="Test doc", doc_category="general", timestamp=1000.0)

    joined_events = [
        JoinedEvent(
            joined_id=f"j{i}",
            query=q,
            matched_docs=[doc],
            join_timestamp=1001.0 + i,
            semantic_score=0.8,
        )
        for i, q in enumerate(queries)
    ]

    # 测试不同的路由策略
    strategies = ["round_robin", "category", "hash"]

    for strategy in strategies:
        print(f"\n{strategy} 路由:")
        router = VDBBranchRouter(routing_strategy=strategy)

        routes = [router.execute(event)[0] for event in joined_events]

        vdb1_count = routes.count("vdb1")
        vdb2_count = routes.count("vdb2")

        print(f"  VDB1: {vdb1_count} 个请求 ({vdb1_count / len(routes) * 100:.1f}%)")
        print(f"  VDB2: {vdb2_count} 个请求 ({vdb2_count / len(routes) * 100:.1f}%)")
        print(f"  路由分布: {routes}")


def main():
    """运行所有示例"""
    print("\n" + "=" * 80)
    print("Workload 4 VDB 检索算子示例")
    print("=" * 80)

    example_single_stage_retrieval()
    example_4stage_pipeline()
    example_dual_vdb_branches()
    example_routing_strategies()

    print("\n" + "=" * 80)
    print("所有示例完成")
    print("=" * 80)

    print("\n关键特性总结:")
    print("  ✓ 双路 VDB 检索（vdb1 + vdb2）")
    print("  ✓ 4-stage 级联检索流水线")
    print("  ✓ 自适应阈值过滤（减少 30-40% 负载）")
    print("  ✓ BM25 局部重排序")
    print("  ✓ Stage 结果去重和汇聚")
    print("  ✓ 多种路由策略（round_robin, category, hash）")
    print("  ✓ 多种合并策略（score_based, interleave）")


if __name__ == "__main__":
    main()
