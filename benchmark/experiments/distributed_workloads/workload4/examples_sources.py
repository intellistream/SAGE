"""
Workload 4 Sources 使用示例

演示如何使用双流源算子和 Embedding 预计算。
"""

import sys
import time
from pathlib import Path

# 添加当前目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from sources import (
    EmbeddingPrecompute,
    Workload4DocumentSource,
    Workload4QuerySource,
    create_query_source,
)

from config import Workload4Config


def example_1_basic_usage():
    """示例 1: 基本使用"""
    print("=" * 80)
    print("示例 1: 基本使用 - 生成 5 个查询和 5 个文档")
    print("=" * 80)

    # 创建查询源（高 QPS 以加快测试）
    query_source = Workload4QuerySource(
        num_tasks=5,
        qps=10.0,
        seed=42,
    )

    # 创建文档源
    doc_source = Workload4DocumentSource(
        num_docs=5,
        qps=10.0,
        seed=42,
    )

    print("\n生成的查询:")
    print("-" * 80)
    for query in query_source.execute():
        if query is not None:
            print(f"ID: {query.query_id}")
            print(f"Type: {query.query_type}, Category: {query.category}")
            print(f"Text: {query.query_text[:100]}...")
            print()

    print("\n生成的文档:")
    print("-" * 80)
    for doc in doc_source.execute():
        if doc is not None:
            print(f"ID: {doc.doc_id}")
            print(f"Category: {doc.doc_category}")
            print(f"Text: {doc.doc_text[:100]}...")
            print()


def example_2_with_config():
    """示例 2: 使用配置和工厂函数"""
    print("=" * 80)
    print("示例 2: 使用 Workload4Config 和工厂函数")
    print("=" * 80)

    # 创建配置
    config = Workload4Config(
        num_tasks=3,
        query_qps=10.0,
        doc_qps=10.0,
        query_type_distribution={
            "factual": 0.5,
            "analytical": 0.3,
            "exploratory": 0.2,
        },
        category_distribution={
            "finance": 0.4,
            "technology": 0.4,
            "general": 0.2,
            "healthcare": 0.0,  # 不生成 healthcare
        },
        seed=123,
    )

    # 使用工厂函数创建源
    query_source = create_query_source(config.__dict__)

    print("\n配置:")
    print(f"- num_tasks: {config.num_tasks}")
    print(f"- query_qps: {config.query_qps}")
    print(f"- query_type_distribution: {config.query_type_distribution}")
    print(f"- category_distribution: {config.category_distribution}")

    print("\n生成的查询（验证分布）:")
    print("-" * 80)
    for query in query_source.execute():
        if query is not None:
            print(f"{query.query_id}: {query.query_type} / {query.category}")


def example_3_embedding_mock():
    """示例 3: Embedding 预计算（Mock 测试）"""
    print("=" * 80)
    print("示例 3: Embedding 预计算（Mock API）")
    print("=" * 80)
    print("注意：此示例需要 Embedding 服务运行在 http://11.11.11.7:8090")
    print("      如果服务不可用，将使用零向量占位")
    print()

    # 创建查询源
    query_source = Workload4QuerySource(num_tasks=2, qps=10.0, seed=42)

    # 创建 embedding 预计算算子
    embedding_precompute = EmbeddingPrecompute(
        embedding_base_url="http://11.11.11.7:8090/v1",
        embedding_model="BAAI/bge-large-en-v1.5",
        max_retries=1,  # 快速失败
    )

    print("处理查询:")
    print("-" * 80)
    for query in query_source.execute():
        if query is not None:
            print(f"原始查询: {query.query_id}, embedding: {query.embedding}")

            # 计算 embedding
            start = time.time()
            query_with_emb = embedding_precompute.execute(query)
            elapsed = time.time() - start

            if query_with_emb.embedding is not None:
                emb_preview = query_with_emb.embedding[:5]  # 前 5 维
                print(f"计算后: embedding[:5] = {emb_preview}, 耗时: {elapsed:.3f}s")
            else:
                print("计算失败，使用占位向量")
            print()


def example_4_qps_control():
    """示例 4: QPS 控制测试"""
    print("=" * 80)
    print("示例 4: QPS 控制测试")
    print("=" * 80)

    qps = 5.0
    num_tasks = 10
    expected_duration = num_tasks / qps

    print(f"配置: {num_tasks} 个查询，{qps} QPS")
    print(f"预期耗时: {expected_duration:.2f}s")
    print()

    query_source = Workload4QuerySource(num_tasks=num_tasks, qps=qps, seed=42)

    start = time.time()
    count = 0
    for query in query_source.execute():
        if query is not None:
            count += 1
            elapsed = time.time() - start
            print(f"t={elapsed:.2f}s: 生成 {query.query_id}")

    total_elapsed = time.time() - start
    actual_qps = count / total_elapsed

    print()
    print(f"实际耗时: {total_elapsed:.2f}s")
    print(f"实际 QPS: {actual_qps:.2f}")
    print(f"误差: {abs(actual_qps - qps) / qps * 100:.1f}%")


def example_5_knowledge_base():
    """示例 5: 知识库集成"""
    print("=" * 80)
    print("示例 5: 知识库集成")
    print("=" * 80)

    # 自定义知识库
    knowledge_base = [
        {
            "title": "SAGE Framework",
            "content": "SAGE is a Python 3.10+ framework for building AI/LLM data processing pipelines with declarative dataflow.",
        },
        {
            "title": "Semantic Join",
            "content": "Semantic Join allows matching documents with queries based on embedding similarity in a time window.",
        },
        {
            "title": "Workload 4",
            "content": "Workload 4 is the most complex CPU-intensive distributed workflow in SAGE benchmark, featuring dual-stream join, VDB retrieval, and clustering.",
        },
    ]

    print(f"知识库包含 {len(knowledge_base)} 个文档")
    print()

    # 创建文档源（从知识库采样）
    doc_source = Workload4DocumentSource(
        num_docs=6,  # 生成 6 个文档（会重复采样）
        qps=10.0,
        knowledge_base=knowledge_base,
        seed=42,
    )

    print("生成的文档（来自知识库）:")
    print("-" * 80)
    for doc in doc_source.execute():
        if doc is not None:
            print(f"ID: {doc.doc_id}")
            print(f"Source: {doc.metadata.get('source')}")
            print(f"Title: {doc.metadata.get('title')}")
            print(f"Content: {doc.doc_text[:80]}...")
            print()


def main():
    """运行所有示例"""
    examples = [
        ("基本使用", example_1_basic_usage),
        ("配置和工厂函数", example_2_with_config),
        ("Embedding 预计算", example_3_embedding_mock),
        ("QPS 控制", example_4_qps_control),
        ("知识库集成", example_5_knowledge_base),
    ]

    print("\n" + "=" * 80)
    print("Workload 4 Sources 使用示例")
    print("=" * 80)
    print()
    print("可用示例:")
    for i, (name, _) in enumerate(examples, 1):
        print(f"  {i}. {name}")
    print()

    choice = input("选择示例 (1-5, 或 'all' 运行全部): ").strip().lower()
    print()

    if choice == "all":
        for name, func in examples:
            func()
            print("\n" + "=" * 80)
            print()
            time.sleep(1)
    elif choice.isdigit() and 1 <= int(choice) <= len(examples):
        idx = int(choice) - 1
        examples[idx][1]()
    else:
        print("无效选择，运行第一个示例...")
        examples[0][1]()


if __name__ == "__main__":
    main()
