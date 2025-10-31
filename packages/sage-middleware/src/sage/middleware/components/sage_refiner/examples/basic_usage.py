"""
基础使用示例
===========

演示RefinerService的基本用法。
"""

from sage.middleware.components.sage_refiner import (
    RefinerAlgorithm,
    RefinerConfig,
    RefinerService,
)


def basic_usage():
    """基础使用示例"""
    print("=" * 60)
    print("基础使用示例")
    print("=" * 60)

    # 1. 创建配置（使用简单算法，不需要模型）
    config = RefinerConfig(algorithm=RefinerAlgorithm.SIMPLE, budget=100, enable_cache=True)

    # 2. 创建服务
    service = RefinerService(config)

    # 3. 准备数据
    query = "什么是人工智能？"
    documents = [
        "人工智能（Artificial Intelligence, AI）是计算机科学的一个分支，致力于开发能够模拟人类智能的系统。",
        "机器学习是人工智能的一个子领域，它使计算机能够从数据中学习，而无需明确编程。",
        "深度学习是机器学习的一个分支，使用多层神经网络来处理复杂的模式识别任务。",
        "自然语言处理（NLP）是人工智能的一个应用领域，专注于使计算机能够理解和生成人类语言。",
        "计算机视觉是人工智能的另一个重要应用，使机器能够理解和解释视觉信息。",
    ]

    # 4. 执行精炼
    print(f"\n查询: {query}")
    print(f"原始文档数: {len(documents)}")
    print(f"Budget: {config.budget} tokens\n")

    result = service.refine(query=query, documents=documents)

    # 5. 查看结果
    print(f"精炼后文档数: {len(result.refined_content)}")
    print(f"原始tokens: {result.metrics.original_tokens}")
    print(f"精炼后tokens: {result.metrics.refined_tokens}")
    print(f"压缩率: {result.metrics.compression_rate:.2f}x")
    print(f"耗时: {result.metrics.refine_time:.3f}s")

    print("\n精炼后的内容:")
    for i, content in enumerate(result.refined_content):
        print(f"  {i + 1}. {content[:100]}...")

    # 6. 查看服务统计
    print("\n服务统计:")
    stats = service.get_stats()
    for key, value in stats.items():
        if key != "config" and key != "cache_stats":
            print(f"  {key}: {value}")

    # 7. 清理
    service.shutdown()
    print("\n✓ 完成\n")


def with_context_manager():
    """使用上下文管理器"""
    print("=" * 60)
    print("使用上下文管理器")
    print("=" * 60)

    config = RefinerConfig(algorithm=RefinerAlgorithm.SIMPLE, budget=50)

    with RefinerService(config) as service:
        query = "Python是什么？"
        documents = [
            "Python是一种高级编程语言，以其简洁和可读性而闻名。",
            "Python广泛用于Web开发、数据分析、人工智能等领域。",
        ]

        result = service.refine(query=query, documents=documents)

        print(f"\n压缩率: {result.metrics.compression_rate:.2f}x")
        print(f"精炼后内容: {result.refined_content}")

    print("\n✓ 服务自动关闭\n")


def batch_processing():
    """批量处理示例"""
    print("=" * 60)
    print("批量处理示例")
    print("=" * 60)

    config = RefinerConfig(algorithm=RefinerAlgorithm.SIMPLE, budget=50)
    service = RefinerService(config)

    queries = ["Python是什么？", "Java是什么？", "JavaScript是什么？"]

    documents_list = [
        ["Python是一种高级编程语言。", "Python用于Web开发和数据科学。"],
        ["Java是一种面向对象的编程语言。", "Java常用于企业级应用开发。"],
        ["JavaScript是Web开发的核心语言。", "JavaScript可在浏览器和服务器运行。"],
    ]

    print(f"\n处理 {len(queries)} 个查询...")

    results = service.refine_batch(queries=queries, documents_list=documents_list)

    for i, (query, result) in enumerate(zip(queries, results, strict=False)):
        print(f"\n查询 {i + 1}: {query}")
        print(f"  压缩率: {result.metrics.compression_rate:.2f}x")
        print(
            f"  原始/精炼 tokens: {result.metrics.original_tokens}/{result.metrics.refined_tokens}"
        )

    service.shutdown()
    print("\n✓ 完成\n")


def algorithm_switching():
    """动态切换算法"""
    print("=" * 60)
    print("动态切换算法")
    print("=" * 60)

    config = RefinerConfig(algorithm=RefinerAlgorithm.SIMPLE, budget=100)
    service = RefinerService(config)

    query = "什么是机器学习？"
    documents = [
        "机器学习是人工智能的一个分支，使计算机能够从数据中学习。",
        "监督学习是机器学习的一种方法，使用标记的训练数据。",
        "无监督学习不使用标记数据，而是寻找数据中的模式。",
    ]

    # 使用Simple算法
    result1 = service.refine(query=query, documents=documents)
    print(f"\nSimple算法: 压缩率 {result1.metrics.compression_rate:.2f}x")

    # 切换到NONE（不压缩）
    service.switch_algorithm(RefinerAlgorithm.NONE)
    result2 = service.refine(query=query, documents=documents)
    print(f"NONE算法: 压缩率 {result2.metrics.compression_rate:.2f}x")

    service.shutdown()
    print("\n✓ 完成\n")


if __name__ == "__main__":
    # 运行示例
    basic_usage()
    with_context_manager()
    batch_processing()
    algorithm_switching()

    print("=" * 60)
    print("所有示例完成!")
    print("=" * 60)
