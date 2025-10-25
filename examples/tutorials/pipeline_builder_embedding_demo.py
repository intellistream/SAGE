#!/usr/bin/env python3
"""
SAGE Pipeline Builder - Embedding Integration 示例

演示如何使用不同的 embedding 方法来增强 Pipeline Builder 的知识检索能力。

@test:allow-demo
"""


from sage.tools.cli.commands.pipeline_knowledge import (
    PipelineKnowledgeBase,
    get_default_knowledge_base,
)


def example_1_basic_usage():
    """示例 1: 基本使用 - 默认 hash 方法"""
    print("=" * 80)
    print("示例 1: 使用默认的 hash embedding 方法")
    print("=" * 80)

    # 使用默认配置（hash 方法）
    kb = get_default_knowledge_base(max_chunks=100, allow_download=False)

    # 执行检索
    query = "如何构建 RAG pipeline"
    results = kb.search(query, top_k=3)

    print(f"\n查询: {query}")
    print("检索方法: hash")
    print(f"结果数量: {len(results)}\n")

    for idx, chunk in enumerate(results, 1):
        print(f"[{idx}] 得分: {chunk.score:.4f} | 类型: {chunk.kind}")
        print(f"    {chunk.text[:100]}...")
        print()


def example_2_custom_method():
    """示例 2: 使用自定义 embedding 方法"""
    print("=" * 80)
    print("示例 2: 使用 mockembedder 方法")
    print("=" * 80)

    # 使用 mockembedder（快速测试方法）
    kb = PipelineKnowledgeBase(
        max_chunks=100,
        allow_download=False,
        embedding_method="mockembedder",
    )

    query = "向量检索算法"
    results = kb.search(query, top_k=3)

    print(f"\n查询: {query}")
    print("检索方法: mockembedder")
    print(f"结果数量: {len(results)}\n")

    for idx, chunk in enumerate(results, 1):
        print(f"[{idx}] 得分: {chunk.score:.4f} | 类型: {chunk.kind}")
        print(f"    {chunk.text[:100]}...")
        print()


def example_3_compare_methods():
    """示例 3: 对比不同 embedding 方法的检索效果"""
    print("=" * 80)
    print("示例 3: 对比 hash vs mockembedder")
    print("=" * 80)

    query = "语义搜索"
    methods = ["hash", "mockembedder"]

    for method in methods:
        print(f"\n--- 方法: {method} ---")

        kb = PipelineKnowledgeBase(
            max_chunks=100,
            allow_download=False,
            embedding_method=method,
        )

        import time

        start = time.time()
        results = kb.search(query, top_k=3)
        elapsed = time.time() - start

        print(f"耗时: {elapsed*1000:.2f}ms")
        print(f"Top-3 得分: {[f'{r.score:.4f}' for r in results]}")

        if results and results[0].vector:
            print(f"向量维度: {len(results[0].vector)}")


def example_4_with_specific_model():
    """示例 4: 使用特定模型（需要 API key）"""
    print("=" * 80)
    print("示例 4: 使用 HuggingFace 模型 (需要模型已下载)")
    print("=" * 80)

    # 注意: 这需要模型已经下载到本地
    # 如果没有，会自动下载（需要网络）
    try:
        kb = PipelineKnowledgeBase(
            max_chunks=50,  # 减少数据量加快测试
            allow_download=False,
            embedding_method="hf",
            embedding_model="BAAI/bge-small-zh-v1.5",  # 中文优化模型
        )

        query = "RAG 系统架构"
        results = kb.search(query, top_k=3)

        print(f"\n查询: {query}")
        print("检索方法: HuggingFace")
        print("模型: BAAI/bge-small-zh-v1.5")
        print(f"结果数量: {len(results)}\n")

        for idx, chunk in enumerate(results, 1):
            print(f"[{idx}] 得分: {chunk.score:.4f}")
            print(f"    {chunk.text[:80]}...")
            print()

    except Exception as e:
        print(f"❌ HuggingFace 方法失败: {e}")
        print("💡 提示: 这通常是因为:")
        print("   1. 模型未下载")
        print("   2. 缺少依赖 (sentence-transformers)")
        print("   3. 需要指定正确的模型名称")


def example_5_environment_variables():
    """示例 5: 使用环境变量配置"""
    print("=" * 80)
    print("示例 5: 通过环境变量配置默认方法")
    print("=" * 80)

    import os

    # 设置环境变量
    os.environ["SAGE_PIPELINE_EMBEDDING_METHOD"] = "mockembedder"

    # 使用默认工厂（会读取环境变量）
    kb = get_default_knowledge_base(max_chunks=100, allow_download=False)

    query = "embedding 优化"
    results = kb.search(query, top_k=2)

    print("\n环境变量: SAGE_PIPELINE_EMBEDDING_METHOD=mockembedder")
    print(f"查询: {query}")
    print(f"结果数量: {len(results)}\n")

    for idx, chunk in enumerate(results, 1):
        print(f"[{idx}] {chunk.text[:100]}...")
        print()


def example_6_fallback_mechanism():
    """示例 6: 自动后备机制"""
    print("=" * 80)
    print("示例 6: 演示自动后备机制")
    print("=" * 80)

    # 尝试使用一个需要配置的方法（不提供配置）
    # 应该自动回退到 hash
    kb = PipelineKnowledgeBase(
        max_chunks=50,
        allow_download=False,
        embedding_method="hf",  # 不提供 model，会失败
        # embedding_model 缺失!
    )

    print("\n✓ 知识库创建成功（即使 hf 方法失败也会自动回退到 hash）")
    print("💡 这就是自动后备机制的作用")

    query = "测试后备"
    results = kb.search(query, top_k=2)
    print(f"\n查询仍然可以正常工作: {len(results)} 个结果")


if __name__ == "__main__":
    print("\n🎯 SAGE Pipeline Builder - Embedding Integration 示例\n")

    examples = [
        ("基本使用", example_1_basic_usage),
        ("自定义方法", example_2_custom_method),
        ("方法对比", example_3_compare_methods),
        ("特定模型", example_4_with_specific_model),
        ("环境变量", example_5_environment_variables),
        ("后备机制", example_6_fallback_mechanism),
    ]

    for title, example_func in examples:
        try:
            example_func()
        except Exception as e:
            print(f"❌ 示例失败: {e}")

        input("\n按 Enter 继续下一个示例...")
        print("\n")

    print("=" * 80)
    print("✅ 所有示例演示完成!")
    print("=" * 80)
    print("\n💡 CLI 使用提示:")
    print("   sage pipeline analyze-embedding '你的查询' -m hash -m mockembedder")
    print(
        "   sage pipeline build --embedding-method openai --embedding-model text-embedding-3-small"
    )
    print()
