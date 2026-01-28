"""
Workload 4 Task 3 使用示例

展示如何使用 SemanticJoinOperator 进行双流语义 Join。
"""

import numpy as np
from workload4.models import QueryEvent, DocumentEvent
from workload4.semantic_join import SemanticJoinOperator


def example_basic_usage():
    """基本使用示例"""
    print("=" * 80)
    print("示例 1: 基本使用")
    print("=" * 80)
    
    # 1. 创建 Join 算子
    join_op = SemanticJoinOperator(
        window_seconds=60,      # 60秒窗口
        threshold=0.7,          # 相似度阈值
        embedding_dim=128,      # Embedding 维度
        top_k=5,                # Top-5 匹配
        enable_stats=True       # 启用统计
    )
    
    # 2. 模拟文档流（添加到窗口）
    print("\n添加文档到窗口...")
    for i in range(10):
        embedding = np.random.randn(128).tolist()
        doc = DocumentEvent(
            doc_id=f"doc{i}",
            doc_text=f"Document content {i}",
            doc_category="technology",
            timestamp=float(i),
            embedding=embedding
        )
        join_op.map1(doc)
    
    print(f"窗口大小: {join_op.window_state.size()}")
    
    # 3. 模拟查询流（触发 Join）
    print("\n处理查询...")
    for i in range(3):
        embedding = np.random.randn(128).tolist()
        query = QueryEvent(
            query_id=f"q{i}",
            query_text=f"Query {i}",
            query_type="factual",
            category="technology",
            timestamp=float(10 + i),
            embedding=embedding
        )
        
        result = join_op.map0(query)
        
        if result is not None:
            print(f"\nQuery {query.query_id} matched {len(result.matched_docs)} docs:")
            print(f"  Semantic score: {result.semantic_score:.3f}")
            print(f"  Matched doc IDs: {[doc.doc_id for doc in result.matched_docs[:3]]}")
        else:
            print(f"\nQuery {query.query_id} had no matches")
    
    # 4. 打印最终统计
    print("\n" + "=" * 80)
    print("最终统计:")
    stats = join_op.window_state.get_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")


def example_with_similar_docs():
    """高相似度示例"""
    print("\n\n" + "=" * 80)
    print("示例 2: 高相似度匹配")
    print("=" * 80)
    
    join_op = SemanticJoinOperator(
        window_seconds=60,
        threshold=0.8,  # 更高的阈值
        embedding_dim=128,
        enable_stats=False
    )
    
    # 创建一个基础 embedding
    base_embedding = np.random.randn(128)
    
    # 添加相似文档（小噪声）
    print("\n添加 5 个相似文档...")
    for i in range(5):
        # 添加小噪声
        doc_emb = base_embedding + np.random.randn(128) * 0.05
        doc = DocumentEvent(
            doc_id=f"similar_doc{i}",
            doc_text=f"Similar content {i}",
            doc_category="technology",
            timestamp=float(i),
            embedding=doc_emb.tolist()
        )
        join_op.map1(doc)
    
    # 使用相同基础 embedding 的查询
    print("\n查询（使用相同基础 embedding）...")
    query = QueryEvent(
        query_id="q1",
        query_text="Query for similar docs",
        query_type="factual",
        category="technology",
        timestamp=10.0,
        embedding=base_embedding.tolist()
    )
    
    result = join_op.map0(query)
    
    if result is not None:
        print(f"\n匹配到 {len(result.matched_docs)} 个文档")
        print(f"平均相似度: {result.semantic_score:.3f}")
        print(f"匹配文档: {[doc.doc_id for doc in result.matched_docs]}")
    else:
        print("\n无匹配文档")


def example_window_expiration():
    """窗口过期示例"""
    print("\n\n" + "=" * 80)
    print("示例 3: 窗口过期清理")
    print("=" * 80)
    
    join_op = SemanticJoinOperator(
        window_seconds=5,  # 5秒小窗口
        threshold=0.7,
        embedding_dim=128,
        enable_stats=False
    )
    
    # 添加早期文档
    print("\n添加早期文档（时间戳 0-4）...")
    for i in range(5):
        embedding = np.random.randn(128).tolist()
        doc = DocumentEvent(
            doc_id=f"early_doc{i}",
            doc_text=f"Early doc {i}",
            doc_category="technology",
            timestamp=float(i),
            embedding=embedding
        )
        join_op.map1(doc)
    
    print(f"窗口大小: {join_op.window_state.size()}")
    
    # 添加晚期文档
    print("\n添加晚期文档（时间戳 10-14）...")
    for i in range(10, 15):
        embedding = np.random.randn(128).tolist()
        doc = DocumentEvent(
            doc_id=f"late_doc{i}",
            doc_text=f"Late doc {i}",
            doc_category="technology",
            timestamp=float(i),
            embedding=embedding
        )
        join_op.map1(doc)
    
    print(f"窗口大小: {join_op.window_state.size()}")
    
    # 晚期查询（时间戳 15，窗口 5s，早期文档应该过期）
    print("\n晚期查询（时间戳 15）...")
    query = QueryEvent(
        query_id="q1",
        query_text="Late query",
        query_type="factual",
        category="technology",
        timestamp=15.0,
        embedding=np.random.randn(128).tolist()
    )
    
    result = join_op.map0(query)
    
    print(f"查询后窗口大小: {join_op.window_state.size()}")
    print(f"（早期文档已过期，只剩晚期文档）")


if __name__ == "__main__":
    # 运行所有示例
    example_basic_usage()
    example_with_similar_docs()
    example_window_expiration()
    
    print("\n\n" + "=" * 80)
    print("所有示例完成！")
    print("=" * 80)
